"""
Fit the seasonal temperature profile used by GrassModel to the KNMI monthly data.

Usage (from the repository root):
    python scripts/fit_temperature_profile.py data/clean/climate_monthly.csv [first_year last_year]

GrassModel approximates the monthly mean temperature as
    T(t) = meanAnnualTemperature + seasonalAmplitude * cos(2*pi*(t - 6.5/12))
with t the fraction of the year (0 = 1 January), i.e. a fixed peak in mid-July.
This script fits meanAnnualTemperature and seasonalAmplitude by ordinary least squares
(the model is linear in both once the phase is fixed), with each monthly mean placed
at the middle of its month, t = (month - 0.5) / 12. It also fits the phase freely, to
check the mid-July assumption. Default window: 1983-2017, the same window used to fit
the herbivore dynamics, so "deltaT = 0" means the climate in which the herds were observed.

Requires: pandas, numpy
"""
import sys

import numpy as np
import pandas as pd

PEAK = 6.5 / 12


def main(path, first, last):
    df = pd.read_csv(path)
    df = df[(df["year"] >= first) & (df["year"] <= last)]
    t = (df["month"].to_numpy() - 0.5) / 12
    y = df["t_mean_c"].to_numpy()

    # Fixed phase (as in GrassModel): y = a + b cos(2 pi (t - PEAK))
    X = np.column_stack([np.ones_like(t), np.cos(2 * np.pi * (t - PEAK))])
    (a, b), *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ np.array([a, b])
    r2 = 1 - resid.var() / y.var()

    # Free phase: y = a + c cos(2 pi t) + s sin(2 pi t)
    Xf = np.column_stack([np.ones_like(t), np.cos(2 * np.pi * t), np.sin(2 * np.pi * t)])
    (_, c, s), *_ = np.linalg.lstsq(Xf, y, rcond=None)
    peak_month = (np.arctan2(s, c) / (2 * np.pi) % 1) * 12 + 0.5  # 1-based, mid-month = .5

    print(f"Window {first}-{last}, {len(y)} months")
    print(f"meanAnnualTemperature = {a:.2f} degC")
    print(f"seasonalAmplitude     = {b:.2f} degC")
    print(f"R^2 = {r2:.3f}, residual sd = {resid.std(ddof=2):.2f} degC (month-to-month weather)")
    print(f"Free-phase fit: amplitude {np.hypot(c, s):.2f} degC, peak at month {peak_month:.2f} "
          f"(1 = mid-January; GrassModel assumes {PEAK * 12 + 0.5:.2f} = mid-July)")
    annual = df.groupby("year")["t_mean_c"].mean()
    print(f"Annual mean: min {annual.min():.2f} ({annual.idxmin()}), max {annual.max():.2f} ({annual.idxmax()})")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 4):
        sys.exit("Usage: python fit_temperature_profile.py <climate_monthly.csv> [first_year last_year]")
    first, last = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) == 4 else (1983, 2017)
    main(sys.argv[1], first, last)
