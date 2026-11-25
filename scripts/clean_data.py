"""
Clean the three Oostvaardersplassen course data sets and export them to CSV.

Usage (from the repository root):
    python scripts/clean_data.py data/raw data/clean

The raw folder must contain the three course spreadsheets (file names may carry a
prefix; they are matched on their distinctive part). Every correction is written to
data/clean/corrections.csv, one row per changed or flagged cell, so the cleaning is
fully traceable. Nothing is imputed: missing or wrong values become empty cells.

Besides the cleaned tables it derives three small files used by the models:
    herbivore_events.csv      introductions, die-off, culls and relocations (dated windows)
    winter_mortality_nos.csv  independent winter death totals (NOS) vs the Moodle deaths
    wolf_rates.csv            per-wolf birth, death and loss rates (measured values only)
The event, NOS and wolf-rate logic was merged in from the group's herbivore_clean.py and
predator_prey_clean.py, without their zero-filling and interpolation steps.

Requires: pandas, openpyxl
"""
import glob
import os
import sys

import numpy as np
import openpyxl
import pandas as pd

SPECIES = ["cattle", "horses", "deer"]
# Column letters in sheet "2025" of the herbivore workbook.
COUNT_COLS = {"cattle": "B", "horses": "C", "deer": "D"}
DEATH_COLS = {"cattle": "H", "horses": "I", "deer": "J"}
BIRTH_COLS = {"cattle": "N", "horses": "O", "deer": "P"}
FIRST_ROW, LAST_ROW = 6, 48  # years 1983..2025
BLUE_THEME = 8  # font colour of "not always 100% trustworthy" values
FOOTNOTES = {
    "1)": "Winter 2017-2018: a great part of the population died",
    "2)": "1785 deer shot between December 2018 and October 2019",
    "3)": "560 horses moved to other reserves between 2018 and 2021",
    "4)": "1800 deer shot between July 2022 and May 2023",
}

# Natural dynamics / mass die-off / culling and relocation (see data/README.md).
PERIODS = [(1983, 2017, "natural"), (2018, 2018, "crash"), (2019, 2025, "managed")]

# Events outside natural births and deaths. `start`/`end` are inclusive calendar months.
# `change` is signed: + animals added, - animals removed. Species "all" = shared by the
# three species in proportion to their numbers (a modelling assumption; no split is given).
NOS_URL = "https://nos.nl/artikel/2230763-ruim-3200-grote-grazers-oostvaardersplassen-dood-afgelopen-winter"
EVENTS = [
    ("introduction", "horses", "1983-12", "1983-12", +20,
     "first count with horses is 1984 (20); release month assumed: just before that count"),
    ("introduction", "deer", "1991-12", "1991-12", +45,
     "first count with deer is 1992 (45); release month assumed: just before that count"),
    ("die-off", "all", "2017-12", "2018-03", -3226,
     f"footnote 1) winter 2017-2018; number from NOS ({NOS_URL}); 89% shot as reactive culling;"
     " months assumed = winter"),
    ("cull", "deer", "2018-12", "2019-10", -1785, "footnote 2) 1785 deer shot Dec 2018 - Oct 2019"),
    ("relocation", "horses", "2018-01", "2021-12", -560,
     "footnote 3) 560 horses moved 2018-2021; spread evenly over the four years (assumption)"),
    ("cull", "deer", "2022-07", "2023-05", -1800, "footnote 4) 1800 deer shot Jul 2022 - May 2023"),
]

# Total winter deaths of all three species reported by NOS (winter starting in this year).
NOS_WINTERS = [(2010, 761), (2011, 1381), (2012, 1728), (2013, 204),
               (2014, 1374), (2015, 1613), (2016, 813), (2017, 3226)]

corrections = []


def log(dataset, year, region, field, original, cleaned, action, reason):
    corrections.append({
        "dataset": dataset, "year": year, "region": region, "field": field,
        "original": original, "cleaned": cleaned, "action": action, "reason": reason,
    })


def find(raw_dir, pattern):
    """Find a spreadsheet by part of its name; spaces, underscores and case are ignored."""
    def norm(s):
        return s.lower().replace(" ", "_")
    hits = [f for f in glob.glob(os.path.join(raw_dir, "*.xlsx"))
            if norm(pattern) in norm(os.path.basename(f))]
    if len(hits) != 1:
        sys.exit(f"Expected exactly one file matching '{pattern}' in {raw_dir}, found {hits}")
    return hits[0]


def as_number(value):
    """Return an int/float, or None for empty cells."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return value


# --------------------------------------------------------------------------- herbivores
def clean_herbivores(path):
    ws = openpyxl.load_workbook(path)["2025"]
    rows = []
    for r in range(FIRST_ROW, LAST_ROW + 1):
        year = int(ws[f"A{r}"].value)
        notes = []
        for sp in SPECIES:
            count_cell = ws[f"{COUNT_COLS[sp]}{r}"]
            count = as_number(count_cell.value)
            births = as_number(ws[f"{BIRTH_COLS[sp]}{r}"].value)
            deaths_cell = ws[f"{DEATH_COLS[sp]}{r}"]
            deaths = deaths_cell.value

            # Footnote markers such as "1)" are typed into the deer mortality column.
            if isinstance(deaths, str):
                marker = deaths.strip()
                note = FOOTNOTES.get(marker, f"unknown footnote {marker}")
                notes.append(note)
                log("herbivores", year, "", f"deaths_{sp}", deaths, "",
                    "removed", f"footnote marker, not a number; moved to 'note' column ({note})")
                deaths = None

            color = count_cell.font.color
            reliable = not (color is not None and color.type == "theme" and color.theme == BLUE_THEME)
            if not reliable:
                log("herbivores", year, "", f"count_{sp}", count, count, "flagged",
                    "blue font in source: 'not always 100% trustworthy'")
            if count is None:
                reason = ("deer introduced/counted only from 1992" if sp == "deer"
                          else "species not yet present (horses introduced 1984)")
                log("herbivores", year, "", f"count_{sp}", "", "", "kept empty", reason)

            rows.append({"year": year, "species": sp, "count": count, "births": births,
                         "deaths": deaths, "reliable": reliable})
        for row in rows[-3:]:
            row["note"] = "; ".join(dict.fromkeys(notes))

    long = pd.DataFrame(rows)
    for col in ["count", "births", "deaths"]:
        long[col] = long[col].astype("Int64")

    # Balance check: count(y+1) = count(y) + births(y) - deaths(y).
    long = long.sort_values(["species", "year"]).reset_index(drop=True)
    nxt = long.groupby("species")["count"].shift(-1)
    long["unexplained_change"] = (nxt - long["count"] - long["births"] + long["deaths"]).astype("Int64")
    for _, row in long[long["unexplained_change"].fillna(0) != 0].iterrows():
        log("herbivores", int(row.year), "", f"balance_{row.species}", "", int(row.unexplained_change),
            "flagged", "count(y+1) - count(y) - births(y) + deaths(y) is not zero")

    # The 'Total' columns in the sheet are formulas; they are recomputed, not copied.
    log("herbivores", "all", "", "total columns", "=SUM(...)", "", "dropped",
        "Excel formulas; totals are recomputed in herbivores_counts.csv")

    long = long.sort_values(["year", "species"]).reset_index(drop=True)
    wide = long.pivot(index="year", columns="species", values="count")[SPECIES].reset_index()
    wide["total"] = wide[SPECIES].sum(axis=1, min_count=1).astype("Int64")
    reliable = long.groupby("year")["reliable"].all().reset_index(drop=True)
    wide["reliable"] = reliable.values
    wide["note"] = long.groupby("year")["note"].first().values
    wide["period"] = ""
    for first, last, name in PERIODS:
        wide.loc[wide["year"].between(first, last), "period"] = name
    wide.columns.name = None
    return wide, long


# --------------------------------------------------------------------------- grass
def clean_grass(path):
    df = pd.read_excel(path, sheet_name="Blad1", header=None, skiprows=3, usecols=[0, 1])
    df.columns = ["year", "grass_height_cm"]
    df = df.dropna(how="all")
    df["year"] = df["year"].astype(int)
    log("grass", "all", "", "sheets Blad2, Blad3", "", "", "dropped", "empty sheets")
    log("grass", "all", "", "grass_height_cm", "", "", "note",
        "one measurement per year (1 August); height, not biomass; no data after 2014")
    return df


# --------------------------------------------------------------------------- wolves / prey
def clean_wolves(path):
    df = pd.read_excel(path, sheet_name="Predator_Data")
    df.columns = ["year", "region", "total_wolves", "pups_born", "mortality"]
    df["region"] = df["region"].str.strip()
    for col in ["pups_born", "mortality"]:
        numeric = pd.to_numeric(df[col], errors="coerce")
        for i in df.index:
            original = df.at[i, col]
            if pd.isna(numeric[i]):
                action = "set empty" if isinstance(original, str) else "kept empty"
                reason = f"text '{original}' instead of a number" if isinstance(original, str) else "missing in source"
                log("wolves", int(df.at[i, "year"]), df.at[i, "region"], col,
                    "" if pd.isna(original) else original, "", action, reason)
        df[col] = numeric.astype("Int64")

    df = df.sort_values(["region", "year"]).reset_index(drop=True)
    growth = df.groupby("region")["total_wolves"].shift(-1) - df["total_wolves"]
    df["unexplained_change"] = (growth - df["pups_born"] + df["mortality"]).astype("Int64")
    log("wolves", "all", "", "unexplained_change", "", "", "note",
        "total grows by less than pups - mortality in most years (dispersal or uncounted deaths?)")
    log("wolves", "all", "", "dataset", "", "", "note",
        "reference area with North/South regions, not the Oostvaardersplassen (which has no wolves)")
    return df.sort_values(["year", "region"]).reset_index(drop=True)


def clean_prey(path):
    df = pd.read_excel(path, sheet_name="Prey_Resource_Data")
    df.columns = ["year", "region", "total_deer", "grass_biomass_kg_ha", "avg_deer_weight_kg"]
    log("wolf_area_prey", "all", "", "Fiscal_Year", "", "year", "renamed",
        "same column as 'Year' in Predator_Data; assumed calendar year")
    df["region"] = df["region"].str.strip()

    for i in df.index[df["grass_biomass_kg_ha"].isna()]:
        log("wolf_area_prey", int(df.at[i, "year"]), df.at[i, "region"], "grass_biomass_kg_ha",
            "", "", "kept empty", "missing in source")

    weight = df["avg_deer_weight_kg"]
    median = weight.median()
    outliers = (weight - median).abs() > 20  # all valid values lie within 104-107 kg
    for i in df.index[outliers]:
        log("wolf_area_prey", int(df.at[i, "year"]), df.at[i, "region"], "avg_deer_weight_kg",
            weight[i], "", "set empty",
            f"impossible value; all other years lie between {weight[~outliers].min()} and {weight[~outliers].max()} kg")
    df.loc[outliers, "avg_deer_weight_kg"] = None
    return df


# --------------------------------------------------------------------------- derived files
def herbivore_events():
    rows = [{"event": e, "species": sp, "start": a, "end": b, "change": n, "source": src}
            for e, sp, a, b, n, src in EVENTS]
    for r in rows:
        assert "," not in r["source"], "the Java CSV reader does not support commas inside fields"
    return pd.DataFrame(rows)


def winter_mortality(long):
    """NOS winter deaths next to the Moodle deaths of the following year and the balance gap."""
    deaths = long.groupby("year")["deaths"].sum(min_count=1)
    gap = long.groupby("year")["unexplained_change"].sum(min_count=3)
    rows = []
    for start, nos in NOS_WINTERS:
        moodle = deaths.get(start + 1, pd.NA)
        rows.append({
            "winter": f"{start}-{start + 1}",
            "deaths_nos": nos,
            "deaths_moodle_next_year": moodle,
            "ratio_moodle_nos": round(moodle / nos, 2) if pd.notna(moodle) else pd.NA,
            "excess_moodle_minus_nos": moodle - nos if pd.notna(moodle) else pd.NA,
            "balance_gap_all_species": gap.get(start + 1, pd.NA),
            "note": "89% of these animals were shot (reactive culling)" if start == 2017 else "",
            "source": NOS_URL,
        })
    out = pd.DataFrame(rows)
    for c in ["deaths_moodle_next_year", "excess_moodle_minus_nos", "balance_gap_all_species"]:
        out[c] = out[c].astype("Int64")
    log("winter_mortality", "2010-2014", "", "deaths", "", "", "note",
        "Moodle deaths up to 2x the NOS winter deaths; the excess follows the balance gap,"
        " so the Moodle deaths (not the counts) are probably too high")
    return out


def wolf_rates(wolves):
    """Per-wolf rates from measured values only (empty cells stay out of the means)."""
    d = wolves.sort_values(["region", "year"]).copy()
    w = d["total_wolves"].astype(float)
    nxt = d.groupby("region")["total_wolves"].shift(-1).astype(float)
    d["pups_per_wolf"] = d["pups_born"].astype(float) / w
    d["deaths_per_wolf"] = d["mortality"].astype(float) / w
    d["lost_per_wolf"] = -d["unexplained_change"].astype(float) / w   # dispersal or unrecorded deaths
    d["growth_rate"] = np.log(nxt / w)                               # r = ln(W(t+1)/W(t))
    rows = []
    for region, g in list(d.groupby("region")) + [("All", d)]:
        row = {"region": region}
        for c in ["pups_per_wolf", "deaths_per_wolf", "lost_per_wolf", "growth_rate"]:
            s = g[c].dropna()
            row[f"{c}_mean"], row[f"{c}_sd"], row[f"{c}_n"] = round(s.mean(), 4), round(s.std(), 4), len(s)
        totals = g.groupby("year")["total_wolves"].sum()
        row["growth_rate_endpoints"] = round(
            np.log(totals.iloc[-1] / totals.iloc[0]) / (totals.index[-1] - totals.index[0]), 4)
        rows.append(row)
    log("wolf_rates", "all", "", "rates", "", "", "note",
        "computed from measured values only; reference area, not the Oostvaardersplassen")
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- main
def main(raw_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    wide, long = clean_herbivores(find(raw_dir, "large_herbivores"))
    grass = clean_grass(find(raw_dir, "height_of_grass"))
    pred_path = find(raw_dir, "Predator_Data")
    wolves, prey = clean_wolves(pred_path), clean_prey(pred_path)

    wide.to_csv(os.path.join(out_dir, "herbivores_counts.csv"), index=False)
    long.to_csv(os.path.join(out_dir, "herbivores_dynamics.csv"), index=False)
    grass.to_csv(os.path.join(out_dir, "grass_height.csv"), index=False)
    wolves.to_csv(os.path.join(out_dir, "wolves.csv"), index=False)
    prey.to_csv(os.path.join(out_dir, "wolf_area_prey.csv"), index=False)
    herbivore_events().to_csv(os.path.join(out_dir, "herbivore_events.csv"), index=False)
    winter_mortality(long).to_csv(os.path.join(out_dir, "winter_mortality_nos.csv"), index=False)
    wolf_rates(wolves).to_csv(os.path.join(out_dir, "wolf_rates.csv"), index=False)
    pd.DataFrame(corrections).to_csv(os.path.join(out_dir, "corrections.csv"), index=False)
    print(f"Wrote 8 data files and {len(corrections)} correction rows to {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python clean_data.py <raw_dir> <out_dir>")
    main(sys.argv[1], sys.argv[2])
