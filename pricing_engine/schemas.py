from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class Market(str, Enum):
    ROI = "ROI"
    NI = "NI"


class Segment(str, Enum):
    SME = "SME"
    IC = "IC"  # Industrial & Commercial


class Commodity(str, Enum):
    ELEC = "ELEC"
    GAS = "GAS"


class TariffStructure(str, Enum):
    FLAT = "flat"
    DAY_NIGHT = "daynight"
    PEAK_OFFPEAK = "peakoffpeak"


class ContractType(str, Enum):
    FIXED = "fixed"
    INDEXED = "indexed"


class TimeBand(str, Enum):
    FLAT = "FLAT"
    DAY = "DAY"
    NIGHT = "NIGHT"
    PEAK = "PEAK"
    OFFPEAK = "OFFPEAK"


TIME_BANDS_BY_TARIFF = {
    TariffStructure.FLAT: [TimeBand.FLAT],
    TariffStructure.DAY_NIGHT: [TimeBand.DAY, TimeBand.NIGHT],
    TariffStructure.PEAK_OFFPEAK: [TimeBand.PEAK, TimeBand.OFFPEAK],
}


class WholesalePrice(BaseModel):
    market: Market
    commodity: Commodity
    year: int
    band: TimeBand
    price_eur_per_mwh: float


class ShapingAdder(BaseModel):
    market: Market
    commodity: Commodity
    year: int
    band: TimeBand
    adder_eur_per_mwh: float = Field(..., description="Shape cost adder vs baseload")


class LossFactor(BaseModel):
    market: Market
    commodity: Commodity
    segment: Segment
    year: int
    band: TimeBand
    loss_factor: float = Field(..., description="Factor >= 1.0 applied to wholesale+shape")


class PassThroughCharge(BaseModel):
    region: Market
    commodity: Commodity
    segment: Segment
    year: int
    band: TimeBand
    charge_type: str  # "NETWORK" or "LEVY"
    name: str
    unit: str = Field(..., description="Assumed EUR_MWH for MVP")
    value: float
    effective_from: date
    effective_to: date
    version: int

    @validator("unit")
    def unit_must_be_eur_mwh(cls, v: str) -> str:
        if v != "EUR_MWH":
            raise ValueError("MVP only supports EUR_MWH pass-through units")
        return v


class CustomerArchetype(BaseModel):
    archetype_id: str
    name: str
    market: Market
    commodity: Commodity
    segment: Segment
    tariff_structure: TariffStructure
    annual_consumption_kwh: float
    standing_charge_eur_per_year: float
    band_split: Dict[TimeBand, float]

    @validator("band_split")
    def band_split_must_sum_to_one(cls, v: Dict[TimeBand, float]) -> Dict[TimeBand, float]:
        total = sum(v.values())
        if not (0.999 <= total <= 1.001):
            raise ValueError(f"Band split must sum to 1.0, got {total}")
        return v


class TariffRequest(BaseModel):
    market: Market
    commodity: Commodity
    segment: Segment
    tariff_structure: TariffStructure
    year: int
    contract_type: ContractType
    annual_consumption_kwh: float
    standing_charge_eur_per_year: float
    band_split: Dict[TimeBand, float]
    vat_rate: Optional[float] = None


class TariffComponent(BaseModel):
    band: TimeBand
    wholesale_eur_per_mwh: float
    shaping_eur_per_mwh: float
    losses_eur_per_mwh: float
    network_eur_per_mwh: float
    levies_eur_per_mwh: float
    margin_eur_per_mwh: float
    risk_eur_per_mwh: float

    @property
    def energy_only_eur_per_mwh(self) -> float:
        return self.wholesale_eur_per_mwh + self.shaping_eur_per_mwh + self.losses_eur_per_mwh

    @property
    def all_in_eur_per_mwh(self) -> float:
        return (
            self.energy_only_eur_per_mwh
            + self.network_eur_per_mwh
            + self.levies_eur_per_mwh
            + self.margin_eur_per_mwh
            + self.risk_eur_per_mwh
        )

    @property
    def energy_only_eur_per_kwh(self) -> float:
        return self.energy_only_eur_per_mwh / 1000.0

    @property
    def all_in_eur_per_kwh(self) -> float:
        return self.all_in_eur_per_mwh / 1000.0


class IndexedTariffInfo(BaseModel):
    index_name: str = "DA_ELEC_BASE"
    # Adder added on top of index in €/MWh
    band_adders_energy_only_eur_per_mwh: Dict[TimeBand, float]
    band_adders_all_in_eur_per_mwh: Dict[TimeBand, float]


class TariffResult(BaseModel):
    request: TariffRequest
    components: List[TariffComponent]
    weighted_energy_only_eur_per_kwh: float
    weighted_all_in_eur_per_kwh: float
    estimated_annual_bill_ex_vat: float
    estimated_annual_bill_inc_vat: float
    indexed_info: Optional[IndexedTariffInfo] = None  # populated for indexed products
