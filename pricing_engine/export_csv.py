from __future__ import annotations

from pathlib import Path

import pandas as pd

from .schemas import TariffResult
from .waterfall import tariff_components_to_dataframe


def export_tariff_to_csv(tariff_result: TariffResult, path: str | Path) -> None:
    path = Path(path)
    df_components = tariff_components_to_dataframe(tariff_result.components)

    # Add band consumption + annual cost per band
    band_split = tariff_result.request.band_split
    annual_kwh = tariff_result.request.annual_consumption_kwh
    band_consumption = {band.value: annual_kwh * share for band, share in band_split.items()}
    df_components["annual_consumption_kwh"] = df_components["band"].map(band_consumption)
    df_components["annual_cost_ex_vat"] = (
        df_components["all_in_eur_per_kwh"] * df_components["annual_consumption_kwh"]
    )

    df_components.to_csv(path, index=False)
