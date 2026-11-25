# Data – Oostvaardersplassen project

Cleaned versions of the three course spreadsheets. **For education purposes only – do not distribute** (condition stated in the source files).

Regenerate everything with:

```
pip install pandas openpyxl
python scripts/clean_data.py data/raw data/clean
```

`data/raw/` holds the original spreadsheets, unchanged. Nothing in `data/clean/` is edited by hand.

## Files

| File | Rows | Content |
| --- | --- | --- |
| `herbivores_counts.csv` | 43 | Animals on 1 January, 1983–2025: `year, cattle, horses, deer, total, reliable, note` |
| `herbivores_dynamics.csv` | 129 | One row per year × species: `count, births, deaths, reliable, note, unexplained_change` |
| `grass_height.csv` | 25 | Grass height (cm) on 1 August, 1990–2014 |
| `wolves.csv` | 32 | Wolves per year and region (North/South), 2010–2025: `total_wolves, pups_born, mortality, unexplained_change` |
| `wolf_area_prey.csv` | 32 | Deer, grass biomass (kg/ha) and average deer weight (kg) in the wolf reference area, 2010–2025 |
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
