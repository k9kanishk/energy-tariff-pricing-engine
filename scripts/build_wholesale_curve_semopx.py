from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# -------- Band rules (simple, auditable defaults) --------
# Day/Night:
#  - DAY   = 08:00–23:00
#  - NIGHT = 23:00–08:00
#
# Peak/Offpeak (simple):
#  - PEAK    = Mon–Fri 08:00–20:00
#  - OFFPEAK = everything else


def parse_time_to_minutes(t: str) -> int:
    hh, mm = t.split(":")
    return int(hh) * 60 + int(mm)


def band_daynight(dt: pd.Timestamp, time_str: str) -> str:
    m = parse_time_to_minutes(time_str)
    if (8 * 60) <= m < (23 * 60):
        return "DAY"
    return "NIGHT"


def band_peakoffpeak(dt: pd.Timestamp, time_str: str) -> str:
    m = parse_time_to_minutes(time_str)
    is_weekday = dt.weekday() < 5  # Mon=0
    if is_weekday and (8 * 60) <= m < (20 * 60):
        return "PEAK"
    return "OFFPEAK"


def load_semopx_folder(input_dir: Path) -> pd.DataFrame:
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSVs found in {input_dir}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        dfs.append(df)

    out = pd.concat(dfs, ignore_index=True)

    # normalize columns
    out.columns = [c.strip() for c in out.columns]
    if "Date" not in out.columns or "Time" not in out.columns:
        raise ValueError("Expected 'Date' and 'Time' columns in SEMOpx CSVs")

    # parse date
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    if out["Date"].isna().any():
        raise ValueError("Some Date values could not be parsed")

    # numeric columns
    for col in ["EUR", "GBP", "NI Volume (MWh)", "ROI Volume (MWh)"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def load_fx_table(fx_path: Path) -> pd.DataFrame:
    """
    Accepts fx file with ANY of these patterns:
    - date + GBP_PER_EUR
    - date + EUR_PER_GBP
    - Date + GBP_PER_EUR / EUR_PER_GBP
    - date + EURGBP (interpreted as GBP per EUR)
    - date + GBPEUR (interpreted as EUR per GBP)
    """
    fx = pd.read_csv(fx_path)
    fx.columns = [c.strip() for c in fx.columns]

    date_col = None
    for c in ["date", "Date", "DATE"]:
        if c in fx.columns:
            date_col = c
            break
    if not date_col:
        raise ValueError("FX file must have a date/Date column")

    fx[date_col] = pd.to_datetime(fx[date_col], errors="coerce")
    fx = fx.sort_values(date_col)
    fx = fx.dropna(subset=[date_col]).copy()
    fx = fx.rename(columns={date_col: "date"})

    # detect rate column
    rate_col = None
    mode = None

    if "GBP_PER_EUR" in fx.columns:
        rate_col = "GBP_PER_EUR"
        mode = "GBP_PER_EUR"
    elif "EUR_PER_GBP" in fx.columns:
        rate_col = "EUR_PER_GBP"
        mode = "EUR_PER_GBP"
    elif "EURGBP" in fx.columns:
        rate_col = "EURGBP"
        mode = "GBP_PER_EUR"
    elif "GBPEUR" in fx.columns:
        rate_col = "GBPEUR"
        mode = "EUR_PER_GBP"
    else:
        # fallback: first numeric column
        num_cols = [c for c in fx.columns if c != "date"]
        if not num_cols:
            raise ValueError("FX file has no rate column")
        rate_col = num_cols[0]
        # assume GBP per EUR (common)
        mode = "GBP_PER_EUR"

    fx[rate_col] = pd.to_numeric(fx[rate_col], errors="coerce")
    fx = fx.dropna(subset=[rate_col]).copy()

    # create eur_per_gbp
    if mode == "GBP_PER_EUR":
        fx["eur_per_gbp"] = 1.0 / fx[rate_col]
    else:
        fx["eur_per_gbp"] = fx[rate_col]

    return fx[["date", "eur_per_gbp"]]


def attach_fx(sem: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    # asof merge so we can handle missing weekend dates etc.
    sem = sem.sort_values("Date").copy()
    fx = fx.sort_values("date").copy()
    sem = pd.merge_asof(
        sem, fx,
        left_on="Date", right_on="date",
        direction="backward"
    )
    if sem["eur_per_gbp"].isna().any():
        raise ValueError("FX merge failed for some dates (missing FX coverage)")
    return sem


def volume_weighted_mean(price: pd.Series, vol: pd.Series) -> float:
    vol = vol.fillna(0.0)
    price = price.fillna(np.nan)
    mask = (vol > 0) & price.notna()
    if not mask.any():
        # fallback: simple average
        return float(price.mean())
    return float((price[mask] * vol[mask]).sum() / vol[mask].sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True, help="Folder of SEMOpx day-ahead CSVs")
    ap.add_argument("--market", required=True, choices=["ROI", "NI"])
    ap.add_argument("--year", required=True, type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--fx-path",
        default="sample_data/fx_rates.csv",
        help="FX file for NI GBP->EUR conversion",
    )
    ap.add_argument(
        "--ni-basis-eur-per-mwh",
        type=float,
        default=0.0,
        help="Add uplift to NI curve (€/MWh)",
    )
    ap.add_argument("--date-from", default=None, help="Filter start date YYYY-MM-DD (optional)")
    ap.add_argument("--date-to", default=None, help="Filter end date YYYY-MM-DD (optional)")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    out_path = Path(args.out)

    sem = load_semopx_folder(input_dir)

    # filter dates if provided (recommended: tariff year window)
    if args.date_from:
        sem = sem[sem["Date"] >= pd.to_datetime(args.date_from)]
    if args.date_to:
        sem = sem[sem["Date"] <= pd.to_datetime(args.date_to)]

    if sem.empty:
        raise ValueError("No SEMOpx rows after date filtering")

    market = args.market

    if market == "ROI":
        sem["price_eur_per_mwh"] = sem["EUR"]
        sem["vol_mwh"] = sem.get("ROI Volume (MWh)", np.nan)
    else:
        # NI: start from GBP, convert to EUR, then apply basis uplift
        fx = load_fx_table(Path(args.fx_path))
        sem = attach_fx(sem, fx)
        sem["price_eur_per_mwh"] = (
            sem["GBP"] * sem["eur_per_gbp"] + float(args.ni_basis_eur_per_mwh)
        )
        sem["vol_mwh"] = sem.get("NI Volume (MWh)", np.nan)

    # Build band prices
    sem["band_dn"] = sem.apply(lambda r: band_daynight(r["Date"], str(r["Time"])), axis=1)
    sem["band_po"] = sem.apply(
        lambda r: band_peakoffpeak(r["Date"], str(r["Time"])), axis=1
    )

    # Flat = volume-weighted across all half-hours
    flat = volume_weighted_mean(sem["price_eur_per_mwh"], sem["vol_mwh"])

    # Day/Night band averages
    day = volume_weighted_mean(
        sem.loc[sem["band_dn"] == "DAY", "price_eur_per_mwh"],
        sem.loc[sem["band_dn"] == "DAY", "vol_mwh"],
    )
    night = volume_weighted_mean(
        sem.loc[sem["band_dn"] == "NIGHT", "price_eur_per_mwh"],
        sem.loc[sem["band_dn"] == "NIGHT", "vol_mwh"],
    )

    # Peak/Offpeak band averages
    peak = volume_weighted_mean(
        sem.loc[sem["band_po"] == "PEAK", "price_eur_per_mwh"],
        sem.loc[sem["band_po"] == "PEAK", "vol_mwh"],
    )
    offpeak = volume_weighted_mean(
        sem.loc[sem["band_po"] == "OFFPEAK", "price_eur_per_mwh"],
        sem.loc[sem["band_po"] == "OFFPEAK", "vol_mwh"],
    )

    out = pd.DataFrame(
        [
            {
                "year": args.year,
                "market": market,
                "commodity": "ELEC",
                "band": "FLAT",
                "price_eur_per_mwh": flat,
            },
            {
                "year": args.year,
                "market": market,
                "commodity": "ELEC",
                "band": "DAY",
                "price_eur_per_mwh": day,
            },
            {
                "year": args.year,
                "market": market,
                "commodity": "ELEC",
                "band": "NIGHT",
                "price_eur_per_mwh": night,
            },
            {
                "year": args.year,
                "market": market,
                "commodity": "ELEC",
                "band": "PEAK",
                "price_eur_per_mwh": peak,
            },
            {
                "year": args.year,
                "market": market,
                "commodity": "ELEC",
                "band": "OFFPEAK",
                "price_eur_per_mwh": offpeak,
            },
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(out)


if __name__ == "__main__":
    main()
