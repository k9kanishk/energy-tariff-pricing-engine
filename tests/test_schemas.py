from pricing_engine.schemas import CustomerArchetype, TimeBand


def test_band_split_sums_to_one() -> None:
    archetype = CustomerArchetype(
        archetype_id="TEST",
        name="Test",
        market="ROI",
        commodity="ELEC",
        segment="SME",
        tariff_structure="flat",
        annual_consumption_kwh=10000,
        standing_charge_eur_per_year=100,
        band_split={TimeBand.FLAT: 1.0},
    )
    assert abs(sum(archetype.band_split.values()) - 1.0) < 1e-6
