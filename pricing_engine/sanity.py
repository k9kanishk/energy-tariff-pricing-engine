from __future__ import annotations

from typing import Dict, List

from .schemas import TariffResult


def check_tariff_bounds(
    tariff_result: TariffResult,
    min_bounds: Dict[str, float],
    max_bounds: Dict[str, float],
) -> List[str]:
    seg = tariff_result.request.segment.value
    min_rate = float(min_bounds[seg])
    max_rate = float(max_bounds[seg])

    warnings: List[str] = []
    for comp in tariff_result.components:
        rate = comp.all_in_eur_per_kwh
        if rate < min_rate:
            warnings.append(
                f"{seg} {comp.band.value}: all-in {rate:.4f} €/kWh < configured min {min_rate:.4f} €/kWh"
            )
        if rate > max_rate:
            warnings.append(
                f"{seg} {comp.band.value}: all-in {rate:.4f} €/kWh > configured max {max_rate:.4f} €/kWh"
            )

    return warnings


def assert_tariff_bounds(
    tariff_result: TariffResult,
    min_bounds: Dict[str, float],
    max_bounds: Dict[str, float],
) -> None:
    warnings = check_tariff_bounds(tariff_result, min_bounds, max_bounds)
    if warnings:
        msg = "Tariff out of configured bounds:\n" + "\n".join(warnings)
        raise ValueError(msg)
