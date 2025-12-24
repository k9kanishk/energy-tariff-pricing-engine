from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List

import pandas as pd

from .schemas import Commodity, Market, Segment, TimeBand


@dataclass
class PassThroughSelection:
    network_eur_per_mwh: float
    levies_eur_per_mwh: float
    raw_rows: pd.DataFrame


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
