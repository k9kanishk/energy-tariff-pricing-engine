from pricing_engine.config import load_settings
from pricing_engine.sanity import check_tariff_bounds
from pricing_engine.tariff_engine import TariffEngine
from pricing_engine.schemas import Commodity, ContractType, Market, Segment, TariffStructure


def test_tariff_bounds_check() -> None:
    engine = TariffEngine.from_config("config/base.yaml", ".")
    result = engine.build_tariff_from_archetype(
        market=Market.ROI,
        commodity=Commodity.ELEC,
        segment=Segment.SME,
        tariff_structure=TariffStructure.DAY_NIGHT,
        year=2026,
        contract_type=ContractType.FIXED,
    )
    settings = load_settings("config/base.yaml")
    warnings = check_tariff_bounds(
        result,
        min_bounds=settings.sanity["min_unit_rate_eur_per_kwh"],
        max_bounds=settings.sanity["max_unit_rate_eur_per_kwh"],
    )
    assert warnings == []
