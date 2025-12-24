from pricing_engine.charges import PassThroughLibrary
from pricing_engine.config import load_settings
from pricing_engine.market_data import load_pass_through
from pricing_engine.schemas import Commodity, Market, Segment, TimeBand


def test_pass_through_selection() -> None:
    settings = load_settings("config/base.yaml")
    df = load_pass_through(settings, ".", Market.ROI, Commodity.ELEC, Segment.SME, 2026)
    lib = PassThroughLibrary(df)
    selection = lib.select_for_band(
        region=Market.ROI,
        commodity=Commodity.ELEC,
        segment=Segment.SME,
        year=2026,
        band=TimeBand.DAY,
    )
    assert selection.network_eur_per_mwh > 0
    assert selection.levies_eur_per_mwh > 0
