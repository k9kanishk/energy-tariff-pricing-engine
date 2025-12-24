from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schemas import TariffResult
from .waterfall import tariff_components_to_dataframe, waterfall_long_format


def export_tariff_to_excel(tariff_result: TariffResult, path: str | Path) -> None:
    path = Path(path)
    components_df = tariff_components_to_dataframe(tariff_result.components)
    waterfall_df = waterfall_long_format(tariff_result)

    band_split = tariff_result.request.band_split
    annual_kwh = tariff_result.request.annual_consumption_kwh
    band_consumption = {band.value: annual_kwh * share for band, share in band_split.items()}
    components_df["annual_consumption_kwh"] = components_df["band"].map(band_consumption)
    components_df["annual_cost_ex_vat"] = (
        components_df["all_in_eur_per_kwh"] * components_df["annual_consumption_kwh"]
    )

    quote_summary = pd.DataFrame(
        [
            {
                "market": tariff_result.request.market.value,
                "commodity": tariff_result.request.commodity.value,
                "segment": tariff_result.request.segment.value,
                "tariff_structure": tariff_result.request.tariff_structure.value,
                "contract_type": tariff_result.request.contract_type.value,
                "annual_consumption_kwh": annual_kwh,
                "standing_charge_eur_per_year": tariff_result.request.standing_charge_eur_per_year,
                "weighted_energy_only_eur_per_kwh": tariff_result.weighted_energy_only_eur_per_kwh,
                "weighted_all_in_eur_per_kwh": tariff_result.weighted_all_in_eur_per_kwh,
                "estimated_annual_bill_ex_vat": tariff_result.estimated_annual_bill_ex_vat,
                "estimated_annual_bill_inc_vat": tariff_result.estimated_annual_bill_inc_vat,
            }
        ]
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        components_df.to_excel(writer, sheet_name="Tariff_Build", index=False)
        waterfall_df.to_excel(writer, sheet_name="Cost_Stack_Data", index=False)
        quote_summary.to_excel(writer, sheet_name="Quote_Summary", index=False)

        # A light metadata sheet so Excel users know config
        meta = pd.DataFrame(
            [
                {
                    "key": "note",
                    "value": "Cost_Stack_Data is intended as the source for Excel cost stack charts.",
                }
            ]
        )
        meta.to_excel(writer, sheet_name="Inputs_Metadata", index=False)
