"""
Clean the monthly KNMI climate series and export it to data/clean/climate_monthly.csv.

Usage (from the repository root):
    python scripts/clean_climate.py data/raw/knmi data/clean

Input (in the raw folder):
  knmi_monthly_1983_2025.csv   monthly mean temperature, rain sum and Makkink reference
                               evaporation sum, 1983-2025; Lelystad (station 269, ~10 km
                               from the reserve) where available, De Bilt (260) before that
  result-DeBilt.txt            KNMI daily data, De Bilt, 1983-1989
  result-LELYSTAD AIRPORT.txt  KNMI daily data, Lelystad, 1990-2025

The monthly file is the source of truth (it contains De Bilt values for 1990-1991 that are
not in result-DeBilt.txt). The daily files are only used to *verify* it: every month that
can be recomputed from complete daily data is compared, and mismatches are printed.
Nothing is imputed or changed; columns are renamed to carry their units.

Requires: pandas
"""
import io
import os
import sys

import pandas as pd

MONTHLY = "knmi_monthly_1983_2025.csv"
DAILY = {"De Bilt": "result-DeBilt.txt", "Lelystad": "result-LELYSTAD AIRPORT.txt"}
RENAME = {"T_mean": "t_mean_c", "rain_sum": "rain_mm", "evap_sum": "evap_mm",
          "source_T": "source_t", "source_rain": "source_rain", "source_evap": "source_evap"}
# Physical plausibility for monthly values in the Netherlands.
RANGES = {"t_mean_c": (-10, 25), "rain_mm": (0, 300), "evap_mm": (0, 200)}
TOLERANCE = 0.06  # monthly file is rounded to 0.01 degC / 0.1 mm


def read_daily(path):
    """KNMI daily file -> monthly T mean (degC), rain sum and evap sum (mm), with day counts."""
    lines = [l for l in open(path, encoding="latin-1") if l.strip() and not l.startswith("#")]
    header = next(l for l in open(path, encoding="latin-1") if l.startswith("# STN,YYYYMMDD"))
    df = pd.read_csv(io.StringIO(header[2:] + "".join(lines)), skipinitialspace=True)
    df.columns = [c.strip() for c in df.columns]
    date = pd.to_datetime(df["YYYYMMDD"].astype(str))
    df["year"], df["month"], df["days"] = date.dt.year, date.dt.month, date.dt.days_in_month
    df["RH"] = df["RH"].clip(lower=0)  # -1 means < 0.05 mm
    g = df.groupby(["year", "month"])
    out = pd.DataFrame({
        "t": g["TG"].mean() / 10, "t_n": g["TG"].count(),
        "rain": g["RH"].sum() / 10, "rain_n": g["RH"].count(),
        "evap": g["EV24"].sum() / 10, "evap_n": g["EV24"].count(),
        "days": g["days"].first(),
    })
    return out


def verify(clean, raw_dir):
    """Compare each monthly value with the daily data of its source station, where complete."""
    daily = {name: read_daily(os.path.join(raw_dir, f)) for name, f in DAILY.items()}
    checked = mismatched = 0
    for col, src_col, d_col in [("t_mean_c", "source_t", "t"),
                                ("rain_mm", "source_rain", "rain"),
                                ("evap_mm", "source_evap", "evap")]:
        for (year, month), row in clean.set_index(["year", "month"]).iterrows():
            station = row[src_col]
            if station not in daily or (year, month) not in daily[station].index:
                continue  # e.g. "De Bilt (adjusted)", or De Bilt 1990-91 (no daily file)
            d = daily[station].loc[(year, month)]
            if d[d_col + "_n"] < d["days"]:
                print(f"  {year}-{month:02d} {col}: {station} daily data incomplete "
                      f"({int(d[d_col + '_n'])}/{int(d['days'])} days), not checked")
                continue
            checked += 1
            if abs(d[d_col] - row[col]) > TOLERANCE:
                mismatched += 1
                print(f"  {year}-{month:02d} {col}: monthly {row[col]} vs daily {d[d_col]:.2f}")
    print(f"Verified {checked} monthly values against daily KNMI data, {mismatched} mismatches")

    # 1983-1989 temperature is De Bilt shifted to the Lelystad level. Report the offset
    # per calendar month so the adjustment is documented.
    adj = clean[clean["source_t"] == "De Bilt (adjusted)"].set_index(["year", "month"])
    offset = (adj["t_mean_c"] - daily["De Bilt"]["t"].reindex(adj.index)).groupby(level="month")
    print("De Bilt -> Lelystad temperature offset per calendar month (mean, sd), degC:")
    print("  " + ", ".join(f"{m}: {o.mean():+.2f} ({o.std():.2f})" for m, o in offset))


def main(raw_dir, out_dir):
    df = pd.read_csv(os.path.join(raw_dir, MONTHLY)).rename(columns=RENAME)

    expected = pd.MultiIndex.from_product([range(1983, 2026), range(1, 13)], names=["year", "month"])
    actual = pd.MultiIndex.from_frame(df[["year", "month"]])
    if not actual.equals(expected):
        sys.exit("Monthly file is not exactly one row per month 1983-01 .. 2025-12 in order")
    for col, (lo, hi) in RANGES.items():
        if df[col].isna().any():
            sys.exit(f"Empty cells in {col}")
        bad = df[(df[col] < lo) | (df[col] > hi)]
        if len(bad):
            sys.exit(f"Implausible {col}:\n{bad}")
    if set(df["flag"]) != {"ok"}:
        print(f"Note: flags present: {sorted(set(df['flag']))}")

    verify(df, raw_dir)

    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "climate_monthly.csv")
    df.to_csv(path, index=False)
    print(f"Wrote {len(df)} rows to {path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python clean_climate.py <raw_knmi_dir> <out_dir>")
    main(sys.argv[1], sys.argv[2])
