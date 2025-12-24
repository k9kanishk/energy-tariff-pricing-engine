from __future__ import annotations

from typing import List

import pandas as pd

from .schemas import TariffComponent, TariffResult


def tariff_components_to_dataframe(components: List[TariffComponent]) -> pd.DataFrame:
    rows = []
    for c in components:
        rows.append(
            {
                "band": c.band.value,
                "wholesale_eur_per_mwh": c.wholesale_eur_per_mwh,
                "shaping_eur_per_mwh": c.shaping_eur_per_mwh,
                "losses_eur_per_mwh": c.losses_eur_per_mwh,
                "network_eur_per_mwh": c.network_eur_per_mwh,
                "levies_eur_per_mwh": c.levies_eur_per_mwh,
                "margin_eur_per_mwh": c.margin_eur_per_mwh,
                "risk_eur_per_mwh": c.risk_eur_per_mwh,
                "energy_only_eur_per_mwh": c.energy_only_eur_per_mwh,
                "all_in_eur_per_mwh": c.all_in_eur_per_mwh,
                "energy_only_eur_per_kwh": c.energy_only_eur_per_kwh,
                "all_in_eur_per_kwh": c.all_in_eur_per_kwh,
            }
        )
    return pd.DataFrame(rows)


def waterfall_long_format(tariff_result: TariffResult) -> pd.DataFrame:
    """Return long format suitable for cost stack charts."""
    df = tariff_components_to_dataframe(tariff_result.components)
    comp_cols = [
        "wholesale_eur_per_mwh",
        "shaping_eur_per_mwh",
        "losses_eur_per_mwh",
        "network_eur_per_mwh",
        "levies_eur_per_mwh",
        "margin_eur_per_mwh",
        "risk_eur_per_mwh",
    ]
    long_df = df.melt(
        id_vars=["band"],
        value_vars=comp_cols,
        var_name="component",
        value_name="value_eur_per_mwh",
    )
    long_df["component"] = long_df["component"].str.replace("_eur_per_mwh", "", regex=False)
    return long_df
