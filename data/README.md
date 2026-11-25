# Data – Oostvaardersplassen project

Cleaned versions of the three course spreadsheets. **For education purposes only – do not distribute** (condition stated in the source files).

Regenerate everything with:

```
pip install pandas openpyxl
python scripts/clean_data.py data/raw data/clean
```

and, for the climate data (needs only pandas):

```
python scripts/clean_climate.py data/raw/knmi data/clean
```

`data/raw/` holds the original spreadsheets, unchanged; `data/raw/knmi/` holds the KNMI climate files. Nothing in `data/clean/` is edited by hand.

## Files

| File | Rows | Content |
| --- | --- | --- |
| `herbivores_counts.csv` | 43 | Animals on 1 January, 1983–2025: `year, cattle, horses, deer, total, reliable, note, period` (`natural` 1983–2017, `crash` 2018, `managed` 2019–2025) |
| `herbivores_dynamics.csv` | 129 | One row per year × species: `count, births, deaths, reliable, note, unexplained_change` |
| `grass_height.csv` | 25 | Grass height (cm) on 1 August, 1990–2014 |
| `wolves.csv` | 32 | Wolves per year and region (North/South), 2010–2025: `total_wolves, pups_born, mortality, unexplained_change` |
| `wolf_area_prey.csv` | 32 | Deer, grass biomass (kg/ha) and average deer weight (kg) in the wolf reference area, 2010–2025 |
| `climate_monthly.csv` | 516 | KNMI monthly weather, Jan 1983 – Dec 2025: `year, month, t_mean_c, rain_mm, evap_mm, source_t, source_rain, source_evap, flag` |
| `herbivore_events.csv` | 6 | Non-natural changes: `event, species, start, end, change, source`. Months inclusive (`YYYY-MM`), `change` signed (+ added, − removed), species `all` = shared by all three. Read by the models via `--replay` |
| `winter_mortality_nos.csv` | 8 | NOS winter deaths 2010–11 to 2017–18 next to the Moodle deaths of the following year and the balance gap |
| `wolf_rates.csv` | 3 | Per-wolf rates per region and overall (mean, SD, n): pups, recorded deaths, wolves lost, growth rate. Measured values only |
| `corrections.csv` | 123 | Every changed or flagged value: dataset, year, region, field, original, cleaned, action, reason |

Rules used throughout: **nothing is imputed**. A missing or impossible value becomes an empty cell and is logged. Whether to interpolate is a modelling decision, made and justified later in the report.

## Corrections and flags

### Large herbivores (1983–2025)

| Issue | Where | Action |
| --- | --- | --- |
| Species not present / not counted | Horses 1983; deer 1983–1991 | Kept empty (not 0), logged |
| Values in blue font, "not always 100% trustworthy" | All counts 2016–2024 | Kept, `reliable = False` |
| Footnote markers `1)`–`4)` typed in the deer mortality column | 2018, 2019, 2021, 2022, 2023 | Removed from the number column; footnote text moved to `note` |
| `Total` columns are Excel formulas | All years | Dropped; `total` recomputed |
| No births/deaths after 2014; births missing in 2015 | 2015–2025 | Kept empty |

**Balance check.** Births and deaths in year *y* should explain the change from *y* to *y+1*. `unexplained_change = count(y+1) − count(y) − births(y) + deaths(y)` should be 0. It is not, in most years:

| Species | Years checked | Years ≠ 0 | Total unexplained | Largest |
| --- | --- | --- | --- | --- |
| Cattle | 31 | 23 | +210 | 60 |
| Horses | 30 | 25 | +1,069 | 340 (2012) |
| Deer | 23 | 19 | +4,630 | 850 (2012, 2013) |

Positive values mean the herd grew by more than births minus deaths, so births are under-reported, deaths over-reported, or counts are off. For deer the gap is 360–850 animals a year from 2005 to 2013. The reserve is fenced, so migration cannot explain it. **Consequence:** fit growth rates on the counts, not on the birth and death columns, and mention this in the report.

**Events, not natural dynamics.** The footnotes describe a mass die-off in winter 2017–2018, 1,785 deer shot (Dec 2018 – Oct 2019), 560 horses relocated (2018–2021) and 1,800 deer shot (Jul 2022 – May 2023). Use 1983–2017 for fitting natural growth.

### Grass height (1990–2014)

| Issue | Action |
| --- | --- |
| Empty sheets `Blad2`, `Blad3` | Dropped |
| One measurement per year (1 August); height in cm, not biomass; nothing after 2014 | No change, noted |

### Wolves (reference area, 2010–2025)

| Issue | Where | Action |
| --- | --- | --- |
| Text `Err` in `Pups_Born` | 2012 North, 2017 South, 2023 South | Set empty |
| Missing `Mortality` | 2013 South, 2021 South | Kept empty |
| Total grows by less than pups − mortality | 25 of 25 checkable years, by 1–4 wolves | Noted (`unexplained_change`, mean −1.8): dispersal or uncounted deaths |
| Not Oostvaardersplassen data | Whole sheet | Noted; use as order-of-magnitude estimate only |

### Prey resources in the wolf area (2010–2025)

| Issue | Where | Action |
| --- | --- | --- |
| Column named `Fiscal_Year` while the wolf sheet uses `Year` | Header | Renamed `year`; assumed calendar year |
| Average deer weight 500 kg (all others 104.3–106.3 kg) | 2012 North | Set empty |
| Missing grass biomass | 2012 North, 2021 South | Kept empty |

### Events, NOS winter deaths and wolf rates

Merged into `scripts/clean_data.py` from the group's `herbivore_clean.py` and `predator_prey_clean.py` (2026-11-25). Their outputs agree with ours: identical counts, low-trust years and wolf totals. Their zero-filling of empty cells and their linear interpolation of wolf/prey gaps were **not** taken over (rule: nothing is imputed); the wolf rates never used imputed values, so they are unchanged.

| Event | Window used | Change | Source / assumption |
| --- | --- | --- | --- |
| Horses introduced | 1983-12 | +20 | First count with horses is 1984; month assumed just before that count |
| Deer introduced | 1991-12 | +45 | First count with deer is 1992; month assumed just before that count |
| Die-off (all species) | 2017-12 – 2018-03 | −3,226 | Footnote 1); number from NOS; 89% shot as reactive culling. Months assumed = winter. Split over the species in proportion to their numbers (no split is given) |
| Deer cull | 2018-12 – 2019-10 | −1,785 | Footnote 2) |
| Horse relocation | 2018-01 – 2021-12 | −560 | Footnote 3) "between 2018 and 2021"; spread evenly (assumption) |
| Deer cull | 2022-07 – 2023-05 | −1,800 | Footnote 4) |

Cattle (30 in 1983) are the initial state, not an event.

**NOS vs Moodle deaths.** In 2010–2013 the Moodle death column is 1.7–2.1× the NOS winter deaths, and the excess follows the unexplained balance gap (4 winters where both exist). Likely the Moodle deaths, not the counts, are too high — one more reason to fit on counts. To be confirmed with the lecturer.

**Wolf rates (All, per wolf per year).** Pups 0.316 ± 0.054, recorded deaths 0.141 ± 0.057, lost 0.090 ± 0.064, growth 0.082 ± 0.043; pups − deaths − lost = 0.085 ≈ growth. `ModelParameters.wolfMortality = 0.23` = deaths + lost.

### Climate (KNMI, 1983–2025)

`t_mean_c` is the monthly mean of the daily mean temperature (°C), `rain_mm` the monthly rain sum and `evap_mm` the monthly Makkink reference evapotranspiration sum (mm). KNMI data are public, not course data.

| Item | Detail |
| --- | --- |
| Source | `data/raw/knmi/knmi_monthly_1983_2025.csv`, built from KNMI daily data. Lelystad (station 269, next to the reserve) where available; De Bilt (260, ~45 km south) before that |
| Station per column | Temperature: De Bilt 1983-01 – 1990-02, Lelystad from 1990-03. Rain: De Bilt to 1991-08, Lelystad from 1991-09. Evaporation: De Bilt to 1989-12, Lelystad from 1990-01. Columns `source_*` give the station per month |
| "De Bilt (adjusted)" temperature | De Bilt shifted to the Lelystad level by a fixed offset per calendar month, from −0.09 °C (Sep) to −0.44 °C (Mar). The cleaning script prints these offsets |
| Verification | `clean_climate.py` recomputes every month it can from the daily files (`result-DeBilt.txt` 1983–1989, `result-LELYSTAD AIRPORT.txt` 1990–2025): 1,436 values, 0 mismatches |
| Not verifiable | De Bilt values for 1990–1991 (no daily file). Months where the Lelystad daily file has missing days but the monthly file has a value: temperature and evaporation 1990-04 (28/30 days), rain 1992-09 (29/30) and 1993-10 (27/31). Kept as given |
| Homogeneity | KNMI warns that these station series are not homogenised and are not suited to trend analysis. They are used for the *average seasonal cycle*, not for a warming trend |

Gaps or impossible values make the script stop with an error; there are none.
