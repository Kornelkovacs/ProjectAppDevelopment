# Application Report — Oostvaardersplassen Population Model

Status as of the initial commit (`b2b2734`). Written for the project team: this
covers what the application currently does, how the pieces fit together, and
what is still open before it can answer research questions A–C for real.

## 1. What the application does today

Given a model, a solver, a time horizon and a set of starting conditions, the
application integrates a system of ODEs describing cattle, horse and deer
populations (and, for the predator-prey model, wolves) forward in time and
shows the result as a line chart, or prints it as CSV in headless mode. All
three models from the brief exist and run; none of them are calibrated yet —
every growth/competition/predation number is a labelled placeholder. The
application answers "if these numbers were true, what would happen" — it
cannot yet answer "what will actually happen", because the numbers aren't
fitted to the historical data.

## 2. Layer-by-layer

### `nl.ovp.model` — the mathematics

Everything a model needs is bundled in `ModelParameters`
(`src/main/java/nl/ovp/model/ModelParameters.java`): initial populations,
growth rates, carrying capacities, the 3×3 competition matrix, climate
sensitivities, grass-model constants, and wolf predation parameters. Per-species
numbers are plain `double[]` arrays indexed by `Species.ordinal()` (cattle=0,
horses=1, deer=2); `ModelParameters.copy()` deep-copies everything, including
the 2D competition matrix, so one base parameter set can be branched for
several what-if runs without them interfering.

Four models implement `PopulationModel` (`name()`, `stateNames()`,
`initialState(p)`, `derivatives(t, y, p)`):

- **`LogisticModel`** — `dN_i/dt = r_i N_i (1 - N_i/K_i)` per species,
  independent of each other. The baseline sanity check (its JUnit test
  confirms RK4 matches the closed-form logistic solution).
- **`CompetitionModel`** — Lotka-Volterra competition for grass:
  `dN_i/dt = r_i N_i (1 - Σ_j α_ij N_j / K_i')`, where `K_i'` is the carrying
  capacity scaled by `GrassModel.grassFactor(ΔT)` (less/more food under
  warming) and a per-species climate sensitivity `max(0, 1 + s_i ΔT)`. This is
  the model needed for research question A (is 1,100 animals stable) and C
  (effect of warming).
- **`PredatorPreyModel`** — `CompetitionModel` plus wolves, hunting all three
  prey species via a shared multi-prey Holling type II response. It delegates
  the prey growth term to an internal `CompetitionModel` instance and then
  subtracts predation losses and adds wolf growth/mortality. This is the model
  for research question B (releasing wolves); a JUnit test confirms it reduces
  exactly to `CompetitionModel` when wolves = 0.
- **`SeasonalGrazingModel`** — iteration 4, adapted from the
  AgriculturalRiskFactors `GrazerModel` (see `docs/ARF_MERGE_OVERVIEW.md`).
  State `[cattle, horses, deer, grass]`; grass in tonnes dry matter on
  `grazingAreaHa` (default 1,080 ha, Van Geel 2018):
  `dG/dt = r GP(t) G (1 - G/K) - d (1 - GP(t)) G - f(G) Σ q_i N_i` and
  `dN_i/dt = N_i [2 b_i c_i s(t) f(G) - m_i - w_i (1 - s(t)) (1 - f(G))] + M_i(t)`,
  with `GP` the brief's temperature growth potential, `s(t)` a calendar season,
  `f` a Holling type II feeding level and `c_i = max(0, 1 + s_i ΔT)`. Food supply
  is explicit, so winter starvation (the 2017-18 die-off) comes out of the model:
  starting from the October 2017 herd on 1,880 ha, it falls to about 3,500 by
  October 2018 (observed: 3,130) with uncalibrated parameters. Its solver step is
  about daily (`maxStepYears()`). Known limit: with one shared food, only one
  species persists in the very long run (competitive exclusion, ~100 years with
  the provisional parameters). All its parameters are provisional.
- **`GrassModel`** — static helper implementing Appendix 3's growth-potential
  Gaussian, with monthly temperature approximated as a cosine around the
  annual mean (peak mid-July). Used by `CompetitionModel` (as a ratio) and by
  `SeasonalGrazingModel` (as the seasonal driver); not a `PopulationModel` itself.
- **`ModelRegistry`** lists all four models (0 logistic, 1 competition,
  2 seasonal grazing, 3 predator-prey, the default); the GUI dropdown and the CLI's
  `--model` index both read from it, so a new model only needs to be added
  there (see the "Adding a new model" section of the top-level README).

### `nl.ovp.solver` — numerical integration

`OdeSolver` is a one-method interface (`step`). `EulerSolver` and
`RungeKutta4Solver` (the default) both implement it; `Simulator` drives either
one over `ModelParameters.horizonYears` at `ModelParameters.dtYears` (default:
20 years, monthly steps; split into smaller internal steps when a model's
`maxStepYears()` requires it), clamping any negative or NaN population to zero after
every step so extinct species stay at zero instead of going negative or
oscillating through zero. `SimulationResult` holds the full time series plus
convenience methods (`finalState()`, `maxValue(seriesIndex)`, `toCsv()`).

### `nl.ovp.data` — reading the cleaned CSVs

`CsvDataLoader` reads `data/clean/herbivores_counts.csv` and
`data/clean/grass_height.csv` by column name (so the extra `total`/`reliable`/
`note` columns in the herbivore file are ignored) into `HerbivoreCount` and
`GrassHeightObservation` records with nullable fields. It also reads
`data/clean/climate_monthly.csv` (KNMI monthly temperature, rain and reference
evaporation, 1983–2025, made by `scripts/clean_climate.py`) into
`ClimateObservation` records. It never reads the raw
`.xlsx` files — those are converted once, offline, by `scripts/clean_data.py`
(pandas + openpyxl), which also writes `data/clean/corrections.csv`, a full log
of every value it changed or flagged, summarised in `data/README.md`. That
cleaning log matters for calibration: it documents, for instance, that the
birth/death columns don't balance against the year-over-year counts (deer are
undercounted or under-reported by 360–850 animals/year from 2005–2013), and
that 2018–2023 contain culling and relocation events rather than natural
dynamics — so growth rates should be fitted on 1983–2017 counts, not on the
birth/death columns or the post-2017 data.

### `nl.ovp.ui` — the Swing GUI

`MainWindow` places `ParameterPanel` on the left and `ChartPanel` on the right.
Every "Run simulation" click builds a `ModelParameters` from the panel's
current values, then runs the simulation on a background `SimulationWorker`
(a `SwingWorker`) so the EDT never blocks; results come back via callbacks that
update the chart and re-enable the Export button, and failures show a
`JOptionPane` dialog with a message, not a raw stack trace. `ChartPanel` is a
from-scratch Java2D line chart: Okabe-Ito colour-blind-safe palette matched by
series name (cattle/horses/deer/wolves), "nice number" auto-scaled axis ticks
(Heckbert's algorithm), a legend showing each series' final value, and an
optional scatter overlay of the observed herd counts, positioned on the
simulation's time axis via the start-year spinner.

### `nl.ovp.app` — entry point

`Main` launches the GUI by default, or runs headless with
`--cli [--model N] [--wolves N] [--dt X] [--years N] [--replay YEAR]`, printing
`SimulationResult.toCsv()` to stdout. Both paths have been smoke-tested: the
CLI produces correct CSV output, and the GUI starts and stays alive without
exceptions (tested at the terminal; an EDT interaction click-through hasn't
been done, see open tasks).

## 3. Test coverage

Nine JUnit 5 tests exist today:

- `ModelParametersTest` — `copy()` is independent of the original; defaults
  match the policy target.
- `RungeKutta4SolverTest` — RK4 matches the closed-form logistic solution.
- `SimulatorTest` — negative populations are clamped to zero; the recorded
  time series has the expected length.
- `PredatorPreyModelTest` — zero wolves reduces exactly to `CompetitionModel`;
  releasing wolves reduces total prey versus the no-wolf baseline.
- `SeasonalGrazingModelTest` — grass without animals is seasonal and stays
  between 0 and capacity; states stay non-negative for 50 years from the 2017
  herd; absent species stay absent; every species declines without grass;
  grass eaten = f(G)·Σ q_i N_i; the event flow equals `CompetitionModel`'s; a
  winter die-off follows from food shortage; more grassland sustains more
  animals; warming helps horses and harms cattle; the season follows the
  calendar start date; the result does not depend on the output step.
- `SimulatorTest` also checks that internal steps are taken but only output
  steps are recorded.
- `CsvDataLoaderTest` — parses synthetic CSVs correctly, and also loads the
  real `data/clean/herbivores_counts.csv` (43 rows) and `grass_height.csv`
  (25 rows) and checks a few known values.

Nothing in `ui` or `app` is unit-tested yet (Swing UI logic is thin — mostly
wiring — but see open tasks below).

## 4. What's left

Roughly in the order it blocks the research questions:

1. **Calibrate the remaining placeholder parameters.** Growth rates, carrying
   capacities and competition coefficients are now fitted (1983–2015 reliable
   counts, `scripts/fit_parameters.py`, see `docs/CALIBRATION.md`; K for cattle
   and deer and the two fitted α are weakly determined). Still guesses marked
   `// TODO: fit/look up`: climate sensitivity, `grassVar` and the wolf
   predation parameters. Original plan, for reference:
   Fit `growthRate`/`carryingCapacity` against `data/clean/herbivores_counts.csv`
   restricted to 1983–2017 (per the corrections log), fit `GrassModel`'s `var`
   against `data/clean/grass_height.csv` (the temperature profile,
   `meanAnnualTemperature` = 10.0 °C and `seasonalAmplitude` = 7.4 °C, is already
   fitted to the KNMI data by `scripts/fit_temperature_profile.py`), and decide a reasoned starting point for
   wolf attack rate/handling time/conversion efficiency since there
   is no direct Oostvaardersplassen wolf data (wolf mortality is set: 0.23/yr
   from `data/clean/wolf_rates.csv`) (`data/clean/wolves.csv` and
   `wolf_area_prey.csv` are a different reference area — use them for
   order-of-magnitude estimates only, as noted in `data/README.md`).
2. **Validate against `herbivores_counts.csv`/`herbivores_dynamics.csv`** once
   fitted — does `CompetitionModel` starting from the 1983 initial conditions
   roughly track the observed curve through 2017? This is the main evidence
   for the report's methodology section. `--replay 2017` then tests the
   managed period 2018–2025 out of sample, with the culls and relocations from
   `data/clean/herbivore_events.csv` as input (`ManagementEvent`, the `M_i(t)`
   term of `CompetitionModel`). With today's placeholders the replay collapses
   horses and deer by 2020: the placeholder K values are far below the observed
   2017 herds.
3. **Answer the three research questions with the calibrated model** and write
   up the findings (stability of 1,100 animals; wolf release scenarios across
   a range of wolf counts; temperature-rise sweep to find the threshold that
   forces a policy change) — this is report content, not application code, but
   the GUI/CLI should make it easy to generate the figures.
4. **UML deliverables** (domain model, use case diagrams, architectural
   design) — required by the course brief (assessment criteria 2.9.2, items
   4–5) but not part of the codebase; not started.
5. **GUI polish and manual verification**: click through every control in a
   real session (not just a startup smoke test) — confirm the "Policy target"
   button, CSV export, and the observed-overlay checkbox/start-year spinner
   all behave as expected together; currently only verified by reading the
   code and a headless startup check.
6. **`data/raw/*.xlsx` and a verification run of `scripts/clean_data.py`** —
   the raw spreadsheets aren't in the repo yet (per the plan, a teammate adds
   them); once they are, run the script and diff its output against the
   `data/clean/*.csv` already committed to confirm they match byte-for-byte.
7. **Geese** are mentioned in the brief as a complicating factor but are out
   of scope per the brief's own "keep it simple" framing — flagged here only
   so it's a deliberate decision, not an oversight, if it comes up in review.

## 5. How to pick this up

See the top-level `README.md` for build/run/test commands and the "Adding a
new model" checklist. The short version: `mvn test` to verify nothing's
broken, `mvn package && java -jar target/app.jar` for the GUI, `--cli` flags
for headless runs while calibrating.
