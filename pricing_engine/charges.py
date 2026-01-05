from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import pandas as pd

from .schemas import Commodity, Market, Segment, TimeBand


@dataclass
class PassThroughSelection:
    network_eur_per_mwh: float
    levies_eur_per_mwh: float
    raw_rows: pd.DataFrame


@dataclass
class NonEnergyCharges:
    fixed_eur_per_year: float = 0.0  # e.g., €/cust/month → €/year
    capacity_eur_per_year: float = 0.0  # e.g., €/kVA/month * MIC * 12


class PassThroughLibrary:
    def __init__(self, df: pd.DataFrame):
        if df.empty:
            raise ValueError("Pass-through charge dataset is empty for requested slice.")
        self.df = df.copy()
        self.df["effective_from"] = pd.to_datetime(self.df["effective_from"]).dt.date
        self.df["effective_to"] = pd.to_datetime(self.df["effective_to"]).dt.date

    def select_for_band(
        self,
        region: Market,
        commodity: Commodity,
        segment: Segment,
        year: int,
        band: TimeBand,
        as_of: date | None = None,
    ) -> PassThroughSelection:
        as_of = as_of or date(year, 6, 30)
        mask = (
            (self.df["region"] == region.value)
            & (self.df["commodity"] == commodity.value)
            & (self.df["segment"] == segment.value)
            & (self.df["year"] == year)
            & (self.df["band"] == band.value)
            & (self.df["effective_from"] <= as_of)
            & (self.df["effective_to"] >= as_of)
        )
        subset = self.df[mask]
        if subset.empty:
            raise ValueError(f"No pass-through charges for band {band.value} @ {region.value} {year}")

        network = subset.loc[subset["charge_type"] == "NETWORK", "value"].sum()
        levies = subset.loc[subset["charge_type"] == "LEVY", "value"].sum()

        return PassThroughSelection(
            network_eur_per_mwh=float(network),
            levies_eur_per_mwh=float(levies),
            raw_rows=subset,
        )

    def select_non_energy(
        self,
        region: Market,
        commodity: Commodity,
        segment: Segment,
        year: int,
        as_of: date,
        mic_kva: Optional[float] = None,
    ) -> NonEnergyCharges:
        df = self.df

        # basic filters
        mask = (
            (df["region"] == region.value)
            & (df["commodity"] == commodity.value)
            & (df["segment"] == segment.value)
            & (df["year"] == year)
        )
        sub = df[mask].copy()

        # effective date filter
        sub["effective_from"] = sub["effective_from"].astype(str)
        sub["effective_to"] = sub["effective_to"].astype(str)

        # keep rows where as_of is inside [from, to]
        sub = sub[
            (pd.to_datetime(sub["effective_from"]) <= pd.Timestamp(as_of))
            & (pd.to_datetime(sub["effective_to"]) >= pd.Timestamp(as_of))
        ]

        fixed = 0.0
        cap = 0.0
        mic = float(mic_kva) if mic_kva is not None else 0.0

        for _, r in sub.iterrows():
            unit = str(r["unit"]).strip().upper()
            val = float(r["value"])

            # We treat NON-energy levy/network charges here (do NOT put into €/MWh waterfall)
            if unit == "EUR_PER_CUST_PER_MONTH":
                fixed += val * 12.0
            elif unit == "EUR_PER_YEAR" or unit == "EUR_PER_CUST_PER_YEAR":
                fixed += val
            elif unit == "EUR_PER_KVA_PER_MONTH":
                if mic <= 0:
                    # no MIC provided, skip but you can also raise/warn
                    continue
                cap += val * mic * 12.0
            elif unit == "EUR_PER_KVA_PER_YEAR":
                if mic <= 0:
                    continue
                cap += val * mic

        return NonEnergyCharges(fixed_eur_per_year=fixed, capacity_eur_per_year=cap)

    def find_overlaps(self) -> List[str]:
        """Detect overlapping effective date ranges for same charge key."""
        errors: List[str] = []
        group_cols = ["region", "commodity", "segment", "year", "band", "charge_type", "name"]
        for key, grp in self.df.groupby(group_cols):
            grp_sorted = grp.sort_values("effective_from")
            prev_end: date | None = None
            for _, row in grp_sorted.iterrows():
                start = row["effective_from"]
                end = row["effective_to"]
                if prev_end is not None and start <= prev_end:
                    errors.append(
                        f"Overlap for {key} between {prev_end} and {start} (version {row['version']})"
                    )
                prev_end = end
        return errors

    def detect_large_changes(self, threshold_pct: float = 0.2) -> List[str]:
        """Flag step changes > threshold_pct between sequential versions."""
        warnings: List[str] = []
        group_cols = ["region", "commodity", "segment", "year", "band", "charge_type", "name"]
        for key, grp in self.df.groupby(group_cols):
            grp_sorted = grp.sort_values("effective_from")
            prev_val: float | None = None
            prev_ver: int | None = None
            for _, row in grp_sorted.iterrows():
                val = float(row["value"])
                ver = int(row["version"])
                if prev_val is not None and prev_val != 0:
                    change = abs(val - prev_val) / abs(prev_val)
                    if change > threshold_pct:
                        warnings.append(
                            f"Large change for {key}: v{prev_ver}={prev_val} -> v{ver}={val} ({change:.0%})"
                        )
                prev_val = val
                prev_ver = ver
        return warnings
