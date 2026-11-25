"""
Validation figure for the calibrated competition model, run through the Java application itself
(so the figure shows exactly what the app computes, and checks that the Python fit matches Java).

Usage (from the repository root, after `mvn package`):
    python3 scripts/plot_validation.py      # writes docs/figures/validation.png, prints error table

Panel 1: --replay 1983 over 1983-2017 (the fit period; introductions of horses 1984 and deer 1992
         come from data/clean/herbivore_events.csv).
Panel 2: --replay 2017 over 2017-2025 (out of sample: die-off, culls and relocations as input).
Observed counts are points (hollow = reliable False). Model = competition model (--model 1).

Requires: pandas, numpy, matplotlib, a built target/app.jar
"""
import io
import subprocess

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SPECIES = ["cattle", "horses", "deer"]
COLOURS = {"cattle": "#257de0", "horses": "#f47230", "deer": "#00b894"}


def replay(year, years):
    out = subprocess.run(["java", "-jar", "target/app.jar", "--cli", "--model", "1",
                          "--replay", str(year), "--years", str(years)],
                         check=True, capture_output=True, text=True).stdout
    d = pd.read_csv(io.StringIO(out))
    d.columns = ["t"] + SPECIES
    d["year"] = year + d.t
    return d


def errors(sim, obs, first, last):
    rows = []
    o = obs[(obs.year >= first) & (obs.year <= last)]
    for sp in SPECIES:
        s = o[["year", sp]].dropna()
        s = s[s[sp] > 0]
        model = np.interp(s.year, sim.year, sim[sp])
        rows.append(dict(period=f"{first}-{last}", species=sp, n=len(s),
                         RMSE=np.sqrt(np.mean((model - s[sp]) ** 2)),
                         mean_abs_pct=100 * np.mean(np.abs(model - s[sp]) / s[sp])))
    return pd.DataFrame(rows)


def main():
    obs = pd.read_csv("data/clean/herbivores_counts.csv")
    fit = replay(1983, 34)
    val = replay(2017, 8)
    table = pd.concat([errors(fit, obs, 1983, 2017), errors(val, obs, 2018, 2025)])
    print(table.to_string(index=False, float_format=lambda v: f"{v:.1f}"))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [3, 1.6]}, sharey=True)
    for ax, sim, title in [(axes[0], fit, "Fit period: replay from 1983"),
                           (axes[1], val, "Out of sample: replay from 2017 with culls/relocations")]:
        lo, hi = sim.year.min(), sim.year.max()
        o = obs[(obs.year >= lo) & (obs.year <= hi + 1e-9)]
        low = o.reliable.astype(str) != "True"
        for sp in SPECIES:
            ax.plot(sim.year, sim[sp], color=COLOURS[sp], lw=2, label=f"{sp} (model)")
            ax.scatter(o.year[~low], o[sp][~low], color=COLOURS[sp], s=20, zorder=3)
            ax.scatter(o.year[low], o[sp][low], facecolor="white", edgecolor=COLOURS[sp], s=26, zorder=3)
        ax.set_title(title, loc="left", fontsize=10)
        ax.set_xlabel("year")
        ax.grid(axis="y", color="#e6e6e6")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("animals on 1 January")
    axes[0].scatter([], [], color="grey", s=20, label="observed")
    axes[0].scatter([], [], facecolor="white", edgecolor="grey", s=26, label="observed, low trust")
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("Calibrated competition model vs observed counts (Oostvaardersplassen)", x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig("docs/figures/validation.png", dpi=130)
    print("Wrote docs/figures/validation.png")


if __name__ == "__main__":
    main()
