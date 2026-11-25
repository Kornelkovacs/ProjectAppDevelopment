# New datasets and scripts in `data/` — what they add and how to use them

> **Status 2026-11-25:** §4 is done (logic merged into `scripts/clean_data.py`, outputs in
> `data/clean/`), and ideas 1, 3 (event replay via `--replay YEAR`, no quota yet) and the
> wolf-mortality part of 5 are implemented. See `data/README.md`.

*Written 2026-11-25. Covers the files added to `data/` on that date:*
`herbivore_clean.py`, `predator_prey_clean.py`, `herbivores_clean.csv`,
`herbivore_events.csv`, `herbivore_log.txt`, `winter_mortality_nos.csv`,
`predator_prey_clean.csv`, `wolf_rates.csv`.

## 1. What arrived

| File | Made by | Content |
| --- | --- | --- |
| `herbivores_clean.csv` | `herbivore_clean.py` | 1983–2025, one row per year: counts, births, deaths, balance gap + flag per species, `period` (natural / crash / managed), `trust` (ok / low), `note` |
| `herbivore_events.csv` | `herbivore_clean.py` | 7 non-natural events: 3 introductions (cattle 1983, horses 1984, deer 1992), die-off 2017–18 (3,226 animals, NOS), deer culls 2018–19 (1,785) and 2022–23 (1,800), horse relocation 2018–21 (560). Each with the count years it affects |
| `winter_mortality_nos.csv` | `herbivore_clean.py` | Total winter deaths 2010–11 to 2017–18 from NOS, compared with the Moodle death column |
| `herbivore_log.txt` | `herbivore_clean.py` | Step-by-step cleaning log (ready for the assumption log) |
| `predator_prey_clean.csv` | `predator_prey_clean.py` | Wolf reference area 2010–2025, North/South, both sheets joined, per-wolf rates per year, gaps **interpolated** and flagged |
| `wolf_rates.csv` | `predator_prey_clean.py` | Mean ± SD per region and overall: pups/wolf, recorded deaths/wolf, "lost" wolves/wolf, observed growth rate |

## 2. Cross-check with what we already had

The new herbivore and wolf tables were compared with `data/clean/herbivores_counts.csv` and `data/clean/wolves.csv`:

- Herbivore counts: **identical** for every species and year (0 differences).
- Low-trust years: the new `trust = low` matches our `reliable = False` exactly (2016–2024).
- Wolf totals: identical; the new `wolves_lost` equals `−unexplained_change` in every year.
- Balance-gap totals (+210 cattle, +1,069 horses, +4,630 deer) match `data/README.md`.

So two independent cleanings agree. That is a useful sentence for the report's data section.

## 3. What is genuinely new (and what each piece helps with)

### 3.1 `herbivore_events.csv` — what humans and events did to the herds
Before this we only had the footnotes as free text in `note`. Now every removal is a number with a start/end year.

- **Validation (all questions):** we can replay 2018–2025 with the culls and relocations as model *input*, and check whether the calibrated model follows the managed period. Fitting stays on 1983–2017 (natural period), so 2018–2025 is a real out-of-sample test.
- **Research question A:** the events show the reserve was in practice *managed* down to ~1,570 animals (2025). A removal term in the model lets us ask "how many animals per year must be removed to hold 1,100?" instead of only "is 1,100 stable?".
- **Research question C:** "a different policy" can now be expressed concretely as a culling quota that changes with ΔT.

### 3.2 `winter_mortality_nos.csv` — an independent source for deaths
NOS reports winter deaths for 2010–2018. Where both sources exist, the Moodle death column is up to 2× higher than NOS (2010–2013), and the excess tracks our unexplained balance gap almost perfectly (r = 0.99, n = 4).

- **Explains the balance problem** documented in `data/README.md`: the counts are probably right and the Moodle *deaths* for 2011–2013 are too high. This strengthens our rule "fit on counts, not on births/deaths".
- **Shows that winter is the bottleneck:** 3,226 animals died in winter 2017–18 (89% shot as reactive culling). This motivates a seasonal model (see §5).
- **Caveat:** n = 4 overlapping winters, and the conclusion should be checked with the lecturer before the report relies on it (the log says so too).

### 3.3 `wolf_rates.csv` — first data-based numbers for the wolf model (question B)
All regions together (mean ± SD, per wolf per year):

| Rate | Value | Use in `ModelParameters` |
| --- | --- | --- |
| Pups born | 0.32 ± 0.05 | Upper bound for the wolf *birth* term at the reference area's prey level → constrains `conversionEfficiency` |
| Recorded deaths | 0.14 ± 0.06 | Part of `wolfMortality` |
| Lost (dispersal / unrecorded deaths) | 0.09 ± 0.06 | Part of `wolfMortality` — the OVP is small, so dispersing wolves would leave |
| Observed growth | 0.08 ± 0.04 | Check: 0.32 − 0.14 − 0.09 ≈ 0.08 ✓ |

- `wolfMortality` (placeholder 0.2) → **≈ 0.23/yr** (deaths + lost), with provenance `wolf_rates.csv` instead of `// TODO`.
- The SDs give a natural range for sensitivity sweeps in `/run-scenario` (e.g. mortality 0.17–0.29).
- Still **not** in this data: kill rates (attack rate, handling time) and prey preference. These must come from literature (the script suggests Jędrzejewski et al. 2000, 2002) — a job for the `ecology-literature` agent.
- Reminder: this is a different area with ~100–160 deer per region, not OVP. Rates per wolf are transferable as an indication; deer and grass levels are not.

### 3.4 Other useful details
- `period` column (natural / crash / managed) — a ready-made filter for fitting vs validation.
- Count precision: 99% of counts are multiples of 5 → about ±5 animals. Gives a minimum error band for fit residuals.
- `predator_prey_clean.py` notes that the grass column in the wolf area *falls together with deer*, so it is not deer-driven: do not use it to calibrate the grass model.

## 4. Conflicts with our project rules — fix before using in Java

| Issue | Rule it breaks | Suggested fix |
| --- | --- | --- |
| `herbivore_clean.py` writes 0 for species not yet present (deer 1983–91) and for empty birth/death cells | "Nothing is imputed in cleaning" | Keep empty, as `clean_data.py` does |
| `predator_prey_clean.py` linearly interpolates 8 cells (pups, wolf deaths, grass, deer weight) | Same; interpolation is a modelling decision | Drop the interpolation; the rates are already computed from measured values only, so `wolf_rates.csv` is unaffected |
| Scripts live in `data/` and write to the current folder; inputs are `.xlsx` paths not in `data/raw/`; the log references `/mnt/user-data/uploads/...` | Java reads only `data/clean/*.csv`; scripts in `scripts/`; reproducible | Move the logic into `scripts/clean_data.py` (or `scripts/clean_events.py`), read from `data/raw/`, write to `data/clean/` |
| `herbivores_clean.csv` and `predator_prey_clean.csv` duplicate existing clean files | One source of truth | Don't add them. Add only the new columns (`period`) to `herbivores_counts.csv` |
| Logs mention `herbivore_check.png` / `predator_prey_check.png` / `predator_prey_log.txt`, which are not in the folder | — | Regenerate or drop the references |

**Proposed end state of `data/clean/`:** existing files + `herbivore_events.csv` + `winter_mortality_nos.csv` + `wolf_rates.csv`, all produced by scripts in `scripts/`, documented in `data/README.md`.

## 5. How we can evolve the project — ideas in priority order

1. **Merge the pipeline** (§4). Small, one commit, no model changes. Add `HerbivoreEvent` / `WolfRates` readers to `CsvDataLoader` with tests.

2. **Calibrate the herbivores** (`/calibrate-parameters`) on 1983–2017 counts, and once more without 2016–17.
   Quick sanity check from the counts: early growth rates are cattle ≈ 0.26, horses ≈ 0.22, deer ≈ 0.28 /yr — close to the current placeholders (0.25/0.25/0.30). The observed peaks (cattle 680, horses 1,250, deer 3,950) are well above the current K placeholders (600/600/2,500), so K will change most.

3. **Add a removal (harvest) term.** `dN_i/dt = … − h_i(t)`, with `h_i(t)` = event number ÷ event duration during the event window, zero otherwise. Stored in `ModelParameters` (models stay stateless). Use it two ways:
   - *Replay*: events from `herbivore_events.csv` → validate against 2018–2025 counts.
   - *Policy*: a constant yearly quota per species → "what quota keeps 1,100 animals stable?" (A) and "how does the quota change with ΔT?" (C).
   Test: `h = 0` reduces exactly to `CompetitionModel`.

4. **Show the data in the chart.** Plot observed counts as dots on `ChartPanel`, hollow for low-trust years, with the natural/managed periods shaded. This makes fit quality visible to the client without extra explanation.

5. **Wolf parameters from data + literature.** Set `wolfMortality ≈ 0.23` from `wolf_rates.csv`; get kill rates and prey preference from literature; choose `conversionEfficiency` so that wolf births at the reference prey level are ≈ 0.32 per wolf. Then run the N-wolves sweep for B with a mortality range taken from the SD.

6. **Seasonal / winter-bottleneck model.** NOS shows deaths are concentrated in winter. A next model iteration (`/add-model`) could make grass a state variable with seasonal growth (KNMI temperature profile is already fitted), so starvation happens in winter, as observed. Winter deaths 2010–2018 are a validation target.

7. **Uncertainty bands.** Run each scenario several times with parameters drawn from their ranges (wolf-rate SDs, ±5 count precision, fit standard errors) and show min–max bands. The client asked for an *indication*; a band communicates that honestly.

8. **Later / optional:** relate NOS winter deaths to winter weather (KNMI) — only 8 winters, so an indication at best. (Rain and evaporation in the equations was deferred on 2026-11-25; this would revisit that.)

## 6. Open questions for the lecturer
- Are the Moodle deaths for 2011–2013 too high (NOS comparison), or do the NOS numbers count something different?
- May we use the wolf reference-area rates (pups, deaths, dispersal) directly for OVP, given it is a different area?
- Should the 2017–18 die-off (mostly reactive culling) count as natural mortality or as management?
