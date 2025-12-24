from pricing_engine.tariff_engine import TariffEngine
from pricing_engine.schemas import Commodity, ContractType, Market, Segment, TariffStructure


def test_build_tariff_from_archetype() -> None:
    engine = TariffEngine.from_config("config/base.yaml", ".")
    result = engine.build_tariff_from_archetype(
        market=Market.ROI,
        commodity=Commodity.ELEC,
        segment=Segment.SME,
        tariff_structure=TariffStructure.DAY_NIGHT,
        year=2026,
        contract_type=ContractType.FIXED,
    )
    assert result.weighted_all_in_eur_per_kwh > 0
    assert result.estimated_annual_bill_ex_vat > 0
