import pandas as pd

from pricing_engine.charges import PassThroughLibrary
from pricing_engine.schemas import Commodity, Market, Segment, TimeBand


def test_pass_through_select() -> None:
    df = pd.DataFrame(
        [
            dict(
                region="ROI",
                commodity="ELEC",
                segment="SME",
                year=2026,
                band="DAY",
                charge_type="NETWORK",
                name="DUoS",
                unit="EUR_MWH",
                value=40,
                effective_from="2026-01-01",
                effective_to="2026-12-31",
                version=1,
            ),
        ]
    )
    lib = PassThroughLibrary(df)
    selection = lib.select_for_band(
        Market.ROI,
        Commodity.ELEC,
        Segment.SME,
        2026,
        TimeBand.DAY,
    )
    assert selection.network_eur_per_mwh == 40
    assert selection.levies_eur_per_mwh == 0
