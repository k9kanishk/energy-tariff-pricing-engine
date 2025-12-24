from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from .config import Settings
from .schemas import (
    Commodity,
    CustomerArchetype,
    Market,
    Segment,
    TariffStructure,
    TimeBand,
)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required input file not found: {path}")
    return pd.read_csv(path)


def load_wholesale_curve(
    settings: Settings, data_root: str | Path, market: Market, commodity: Commodity, year: int
) -> pd.DataFrame:
    data_root = Path(data_root)
    rel = settings.file_paths["wholesale"][commodity.value][market.value]
    df = _read_csv(data_root / rel)
    df = df[df["year"] == year].copy()
    df["band"] = df["band"].astype(str)
    return df


def load_shaping_adders(
    settings: Settings, data_root: str | Path, market: Market, commodity: Commodity, year: int
) -> pd.DataFrame:
    data_root = Path(data_root)
    rel = settings.file_paths["shaping_adders"]
    df = _read_csv(data_root / rel)
    mask = (
        (df["year"] == year)
        & (df["market"] == market.value)
        & (df["commodity"] == commodity.value)
    )
    return df[mask].copy()


def load_losses(
    settings: Settings,
    data_root: str | Path,
    market: Market,
    commodity: Commodity,
    segment: Segment,
    year: int,
) -> pd.DataFrame:
    data_root = Path(data_root)
    rel = settings.file_paths["losses"]
    df = _read_csv(data_root / rel)
    mask = (
        (df["year"] == year)
        & (df["market"] == market.value)
        & (df["commodity"] == commodity.value)
        & (df["segment"] == segment.value)
    )
    return df[mask].copy()


def load_pass_through(
    settings: Settings,
    data_root: str | Path,
    market: Market,
    commodity: Commodity,
    segment: Segment,
    year: int,
) -> pd.DataFrame:
    data_root = Path(data_root)
    rel = settings.file_paths["pass_through"]
    df = _read_csv(data_root / rel)
    mask = (
        (df["region"] == market.value)
        & (df["commodity"] == commodity.value)
        & (df["segment"] == segment.value)
        & (df["year"] == year)
    )
    return df[mask].copy()


def load_archetypes(settings: Settings, data_root: str | Path) -> pd.DataFrame:
    data_root = Path(data_root)
    rel = settings.file_paths["customer_archetypes"]
    return _read_csv(data_root / rel)


def get_archetype(
    settings: Settings,
    data_root: str | Path,
    market: Market,
    commodity: Commodity,
    segment: Segment,
    tariff_structure: TariffStructure,
) -> CustomerArchetype:
    df = load_archetypes(settings, data_root)
    mask = (
        (df["market"] == market.value)
        & (df["commodity"] == commodity.value)
        & (df["segment"] == segment.value)
        & (df["tariff_structure"] == tariff_structure.value)
    )
    sub = df[mask]
    if sub.empty:
        raise ValueError(
            f"No archetype found for {market.value}/{commodity.value}/{segment.value}/{tariff_structure.value}"
        )
    row = sub.iloc[0]

    band_split: Dict[TimeBand, float] = {}
    if row["flat_share"]:
        band_split[TimeBand.FLAT] = float(row["flat_share"])
    if row["day_share"]:
        band_split[TimeBand.DAY] = float(row["day_share"])
    if row["night_share"]:
        band_split[TimeBand.NIGHT] = float(row["night_share"])
    if row["peak_share"]:
        band_split[TimeBand.PEAK] = float(row["peak_share"])
    if row["offpeak_share"]:
        band_split[TimeBand.OFFPEAK] = float(row["offpeak_share"])

    return CustomerArchetype(
        archetype_id=row["archetype_id"],
        name=row["name"],
        market=Market(row["market"]),
        commodity=Commodity(row["commodity"]),
        segment=Segment(row["segment"]),
        tariff_structure=TariffStructure(row["tariff_structure"]),
        annual_consumption_kwh=float(row["annual_consumption_kwh"]),
        standing_charge_eur_per_year=float(row["standing_charge_eur_per_year"]),
        band_split=band_split,
    )
