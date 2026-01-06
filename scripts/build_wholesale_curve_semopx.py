from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_semopx_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Your export has Date, Time, EUR, GBP, volumes...
    required = ["Date", "Time", "EUR"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns {missing}. Found: {list(df.columns)}")

    out = df[["Date", "Time", "EUR"]].copy()
    out.columns = ["date", "time", "price_eur_per_mwh"]

    out["datetime"] = pd.to_datetime(
        out["date"].astype(str) + " " + out["time"].astype(str), errors="coerce"
    )
    out["price_eur_per_mwh"] = pd.to_numeric(out["price_eur_per_mwh"], errors="coerce")

    out = out.dropna(subset=["datetime", "price_eur_per_mwh"])
    return out[["datetime", "price_eur_per_mwh"]]


def add_bands(df: pd.DataFrame) -> pd.DataFrame:
    dt = df["datetime"]
    hour = dt.dt.hour + dt.dt.minute / 60.0
    weekday = dt.dt.weekday  # 0=Mon

    # Simple, defensible defaults (document in README)
    is_day = (hour >= 8.0) & (hour < 23.0)
    is_peak = (weekday <= 4) & (hour >= 17.0) & (hour < 20.0)
    is_offpeak = ~is_peak

    df = df.copy()
    df["DAY"] = is_day
    df["NIGHT"] = ~is_day
    df["PEAK"] = is_peak
    df["OFFPEAK"] = is_offpeak
    return df


def band_averages(df: pd.DataFrame) -> dict[str, float]:
    res = {}
    res["FLAT"] = float(df["price_eur_per_mwh"].mean())
    res["DAY"] = float(df.loc[df["DAY"], "price_eur_per_mwh"].mean())
    res["NIGHT"] = float(df.loc[df["NIGHT"], "price_eur_per_mwh"].mean())
    res["PEAK"] = float(df.loc[df["PEAK"], "price_eur_per_mwh"].mean())
    res["OFFPEAK"] = float(df.loc[df["OFFPEAK"], "price_eur_per_mwh"].mean())
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--market", required=True, choices=["ROI", "NI"])
    ap.add_argument("--year", required=True, type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSVs found in {input_dir}")

    frames = [parse_semopx_csv(f) for f in files]
    df = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["datetime"])
        .sort_values("datetime")
    )
    df = add_bands(df)

    avgs = band_averages(df)

    out_df = pd.DataFrame(
        [
            {
                "year": args.year,
                "market": args.market,
                "commodity": "ELEC",
                "band": k,
                "price_eur_per_mwh": v,
            }
            for k, v in avgs.items()
        ]
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)

    print(out_df)


if __name__ == "__main__":
    main()
