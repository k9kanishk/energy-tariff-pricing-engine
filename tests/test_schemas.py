from pricing_engine.schemas import CustomerArchetype, Market, Commodity, Segment, TariffStructure, TimeBand


def test_customer_archetype_band_split_sum() -> None:
    archetype = CustomerArchetype(
        archetype_id="TEST",
        name="Test",
        market=Market.ROI,
        commodity=Commodity.ELEC,
        segment=Segment.SME,
        tariff_structure=TariffStructure.FLAT,
        annual_consumption_kwh=1000.0,
        standing_charge_eur_per_year=100.0,
        band_split={TimeBand.FLAT: 1.0},
    )
    assert archetype.band_split[TimeBand.FLAT] == 1.0
