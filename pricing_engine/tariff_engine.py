from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

import numpy as np

from .charges import PassThroughLibrary
from .config import Settings, load_settings
from .market_data import (
    get_archetype,
    load_losses,
    load_pass_through,
    load_shaping_adders,
    load_wholesale_curve,
)
from .sanity import assert_tariff_bounds
from .schemas import (
    Commodity,
    ContractType,
    IndexedTariffInfo,
    Market,
    Segment,
    TariffComponent,
    TariffRequest,
    TariffResult,
    TariffStructure,
    TIME_BANDS_BY_TARIFF,
    TimeBand,
)


@dataclass
class TariffEngine:
    settings: Settings
    data_root: Path

    @classmethod
    def from_config(cls, config_path: str | Path = "config/base.yaml", data_root: str | Path = "."):
        return cls(settings=load_settings(config_path), data_root=Path(data_root))

    def build_tariff_from_archetype(
        self,
        market: Market,
        commodity: Commodity,
        segment: Segment,
        tariff_structure: TariffStructure,
        year: int,
        contract_type: ContractType,
        include_vat: bool = True,
    ) -> TariffResult:
        archetype = get_archetype(
            self.settings, self.data_root, market, commodity, segment, tariff_structure
        )
        vat_rate = self.settings.vat[market.value] if include_vat else 0.0

        request = TariffRequest(
            market=market,
            commodity=commodity,
            segment=segment,
            tariff_structure=tariff_structure,
            year=year,
            contract_type=contract_type,
            annual_consumption_kwh=archetype.annual_consumption_kwh,
            standing_charge_eur_per_year=archetype.standing_charge_eur_per_year,
            band_split=archetype.band_split,
            vat_rate=vat_rate,
        )
        return self.build_tariff(request)

    def build_tariff(self, request: TariffRequest) -> TariffResult:
        market = request.market
        commodity = request.commodity
        segment = request.segment
        year = request.year
        tariff_structure = request.tariff_structure

        bands: List[TimeBand] = TIME_BANDS_BY_TARIFF[tariff_structure]

        # Load inputs
        wholesale_df = load_wholesale_curve(self.settings, self.data_root, market, commodity, year)
        shaping_df = load_shaping_adders(self.settings, self.data_root, market, commodity, year)
        losses_df = load_losses(self.settings, self.data_root, market, commodity, segment, year)
        pass_df = load_pass_through(self.settings, self.data_root, market, commodity, segment, year)
        pass_lib = PassThroughLibrary(pass_df)

        margin_pct = float(self.settings.margin_pct[segment.value])
        risk_pct = float(self.settings.risk_pct[segment.value])

        components: List[TariffComponent] = []
        energy_only_band_rates: dict[TimeBand, float] = {}
        all_in_band_rates: dict[TimeBand, float] = {}

        for band in bands:
            wh_row = wholesale_df[wholesale_df["band"] == band.value]
            if wh_row.empty:
                raise ValueError(f"No wholesale price for band {band.value}")
            wholesale_price = float(wh_row.iloc[0]["price_eur_per_mwh"])

            sh_row = shaping_df[shaping_df["band"] == band.value]
            shaping_adder = float(sh_row.iloc[0]["adder_eur_per_mwh"]) if not sh_row.empty else 0.0

            loss_row = losses_df[losses_df["band"] == band.value]
            if loss_row.empty:
                raise ValueError(f"No loss factor for band {band.value}")
            loss_factor = float(loss_row.iloc[0]["loss_factor"])

            pt_sel = pass_lib.select_for_band(
                region=market,
                commodity=commodity,
                segment=segment,
                year=year,
                band=band,
                as_of=date(year, 6, 30),
            )

            # For INDEXED product, treat wholesale as 0 for the numeric stack and report it as an index.
            if request.contract_type == ContractType.INDEXED:
                wholesale_used = 0.0
            else:
                wholesale_used = wholesale_price

            energy_ex_losses = wholesale_used + shaping_adder
            losses_component = energy_ex_losses * (loss_factor - 1.0)

            subtotal_before_margin_risk = (
                wholesale_used
                + shaping_adder
                + losses_component
                + pt_sel.network_eur_per_mwh
                + pt_sel.levies_eur_per_mwh
            )

            margin_component = subtotal_before_margin_risk * margin_pct
            risk_component = subtotal_before_margin_risk * risk_pct

            comp = TariffComponent(
                band=band,
                wholesale_eur_per_mwh=wholesale_used,
                shaping_eur_per_mwh=shaping_adder,
                losses_eur_per_mwh=losses_component,
                network_eur_per_mwh=pt_sel.network_eur_per_mwh,
                levies_eur_per_mwh=pt_sel.levies_eur_per_mwh,
                margin_eur_per_mwh=margin_component,
                risk_eur_per_mwh=risk_component,
            )
            components.append(comp)
            energy_only_band_rates[band] = comp.energy_only_eur_per_mwh
            all_in_band_rates[band] = comp.all_in_eur_per_mwh

        # Weighted averages using band split
        band_split = request.band_split
        weights = np.array([band_split[b] for b in bands], dtype=float)

        energy_only_array = np.array([energy_only_band_rates[b] for b in bands], dtype=float)
        all_in_array = np.array([all_in_band_rates[b] for b in bands], dtype=float)

        weighted_energy_only_eur_per_mwh = float(np.dot(weights, energy_only_array))
        weighted_all_in_eur_per_mwh = float(np.dot(weights, all_in_array))

        weighted_energy_only_eur_per_kwh = weighted_energy_only_eur_per_mwh / 1000.0
        weighted_all_in_eur_per_kwh = weighted_all_in_eur_per_mwh / 1000.0

        # Annual bill estimate (using weighted all-in unit rate + standing charge)
        annual_kwh = request.annual_consumption_kwh
        standing = request.standing_charge_eur_per_year

        annual_energy_cost = weighted_all_in_eur_per_kwh * annual_kwh
        annual_bill_ex_vat = annual_energy_cost + standing

        vat_rate = request.vat_rate if request.vat_rate is not None else 0.0
        annual_bill_inc_vat = annual_bill_ex_vat * (1.0 + vat_rate)

        indexed_info: IndexedTariffInfo | None = None
        if request.contract_type == ContractType.INDEXED:
            # For indexed, compute adders vs wholesale curve (which we know from file)
            band_adders_energy_only: dict[TimeBand, float] = {}
            band_adders_all_in: dict[TimeBand, float] = {}
            for band in bands:
                wh_row = wholesale_df[wholesale_df["band"] == band.value]
                wholesale_price = float(wh_row.iloc[0]["price_eur_per_mwh"])
                energy_add = energy_only_band_rates[band]
                all_in_add = all_in_band_rates[band]
                band_adders_energy_only[band] = energy_add
                band_adders_all_in[band] = all_in_add
            indexed_info = IndexedTariffInfo(
                band_adders_energy_only_eur_per_mwh=band_adders_energy_only,
                band_adders_all_in_eur_per_mwh=band_adders_all_in,
            )

        result = TariffResult(
            request=request,
            components=components,
            weighted_energy_only_eur_per_kwh=weighted_energy_only_eur_per_kwh,
            weighted_all_in_eur_per_kwh=weighted_all_in_eur_per_kwh,
            estimated_annual_bill_ex_vat=annual_bill_ex_vat,
            estimated_annual_bill_inc_vat=annual_bill_inc_vat,
            indexed_info=indexed_info,
        )

        # Run sanity checks (raises if outside range)
        sanity_cfg = self.settings.sanity
        assert_tariff_bounds(
            result,
            min_bounds=sanity_cfg["min_unit_rate_eur_per_kwh"],
            max_bounds=sanity_cfg["max_unit_rate_eur_per_kwh"],
        )

        return result
