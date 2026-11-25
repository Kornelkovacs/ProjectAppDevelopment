# Oostvaardersplassen Population Model

A modular Java application simulating the herbivore (and wolf) population dynamics
of the Oostvaardersplassen nature reserve, built for Staatsbosbeheer's policy
question: is 1,100 animals (500 deer, 600 cattle + horses) a stable target, what
happens if grey wolves are released, and how does a temperature rise change the
answer?

## Structure

Maven project, base package `nl.ovp`, split into layers so new models, solvers or
GUI elements can be added without touching the rest:

```
src/main/java/nl/ovp/
  model/   the mathematical models (logistic, competition, predator-prey, grass)
  solver/  numerical integration (Euler, RK4) + simulation runner/result
  data/    CSV readers for the cleaned data in data/clean/
  ui/      Swing GUI (parameter panel + custom Java2D chart)
  app/     Main entry point (GUI by default, --cli for headless runs)

src/test/java/nl/ovp/   JUnit 5 tests, mirroring the main package layout

data/
  raw/     original course spreadsheets (.xlsx), unmodified
  raw/knmi/  KNMI monthly + daily climate files (Lelystad, De Bilt)
  clean/   CSVs produced by scripts/clean_*.py; the only thing Java reads
  README.md   full log of every correction made to the raw data

scripts/
  clean_data.py   one-off pandas script: data/raw/*.xlsx -> data/clean/*.csv
                  (also herbivore_events.csv, winter_mortality_nos.csv, wolf_rates.csv)
  clean_climate.py   data/raw/knmi -> data/clean/climate_monthly.csv (checked against daily KNMI data)
  fit_temperature_profile.py   fits meanAnnualTemperature / seasonalAmplitude to the climate data
  fit_parameters.py   fits growthRate / carryingCapacity / competitionAlpha to the counts (docs/CALIBRATION.md)
  plot_validation.py   docs/figures/validation.png, model (via the jar) vs observed counts
  build_model_equations_pdf.py   rebuilds docs/MODEL_EQUATIONS.pdf from the current code (needs reportlab)
```

### Model layer

- `PopulationModel` — interface every model implements: `name()`, `stateNames()`,
  `initialState(ModelParameters)`, `derivatives(t, y, ModelParameters)`.
- `ModelRegistry` — lists every model so the GUI's dropdown and the CLI's
  `--model` index pick up new models automatically.
- `Species` — enum `{CATTLE, HORSES, DEER}`; its ordinal is the index into every
  per-species array in `ModelParameters`, and matches the state-vector order
  (cattle, horses, deer, optionally wolves) used throughout.
- `ModelParameters` — every tunable number, in one place, with a deep `copy()`.
  Defaults match the policy target (300 cattle, 300 horses, 500 deer, 0 wolves);
  everything else is a placeholder marked `// TODO: fit/look up`, to be
  calibrated against `data/clean/herbivores_counts.csv` and `grass_height.csv`.
- `LogisticModel` → `CompetitionModel` → `PredatorPreyModel` are the three
  iterations from the project brief (independent logistic growth; Lotka-Volterra
  competition for grass, climate-adjusted; the same plus wolves via a multi-prey
  Holling type II response). Each class's Javadoc gives the equation and the
  relevant chapter of Gotelli, *A Primer of Ecology*.
- `GrassModel` implements the grass growth-potential formula from Appendix 3 of
  the project brief and feeds `CompetitionModel`'s climate scaling.

### Solver layer

- `OdeSolver` — interface with a single `step(model, t, y, dt, p)`.
- `EulerSolver` / `RungeKutta4Solver` (default) — kept both so the report can
  compare their accuracy.
- `Simulator` — runs a model over `ModelParameters.horizonYears` at
  `ModelParameters.dtYears`, clamping any negative/NaN population to zero
  (extinction), and returns a `SimulationResult` (times, states, series names,
  `finalState()`, `maxValue()`, `toCsv()`).

### Data layer

`CsvDataLoader` reads `data/clean/herbivores_counts.csv` and
`data/clean/grass_height.csv` by column name (so extra columns like `reliable`
or `note` are ignored) into `HerbivoreCount` / `GrassHeightObservation` records
with nullable fields, and `data/clean/climate_monthly.csv` (monthly KNMI
temperature, rain and reference evaporation) into `ClimateObservation` records.
Java never touches the raw `.xlsx` files — only
`scripts/clean_data.py` does, and every correction it makes is logged in
`data/clean/corrections.csv` and summarised in `data/README.md`.

### UI layer

`MainWindow` lays out `ParameterPanel` (left) and `ChartPanel` (right).
Simulations run on a background `SimulationWorker` (a `SwingWorker`), never on
the Event Dispatch Thread, and failures surface as a dialog instead of a raw
stack trace. `ChartPanel` is a dependency-free Java2D line chart with a
colour-blind-safe palette, readable (auto-scaled) axis ticks, a legend showing
each series' final value, and an optional scatter overlay of observed herd
counts mapped onto the simulation's timeline via a start-year spinner.

## Build, run, test

Requires JDK 17+ (tested on 17 and 21) and Maven.

```
mvn test               # compile + run all JUnit 5 tests
mvn package             # build target/app.jar (runnable, Main-Class set)

java -jar target/app.jar                                  # launch the GUI
java -jar target/app.jar --cli --years 20 --wolves 10      # headless, prints CSV to stdout
```

CLI flags: `--model N` (index into `ModelRegistry.all()`, defaults to the most
general model so `--wolves` always takes effect), `--wolves N`, `--dt X`
(years), `--years N`, `--replay YEAR` (start from the counts observed on 1 January
of YEAR and apply the known culls, relocations and die-off from
`data/clean/herbivore_events.csv`; `t = 0` is that date).

To regenerate the cleaned CSVs from the raw spreadsheets:

```
pip install pandas openpyxl
python scripts/clean_data.py data/raw data/clean
python scripts/clean_climate.py data/raw/knmi data/clean
```

## Adding a new model

1. Implement `PopulationModel` in `nl.ovp.model` (see `LogisticModel` for the
   smallest example). Document the equation and its source in the class Javadoc.
2. Add any new parameters it needs to `ModelParameters`, defaulted and marked
   `// TODO: fit/look up` until calibrated, and include them in `copy()`.
3. Register an instance in `ModelRegistry.ALL` — the GUI dropdown and the CLI's
   `--model` index pick it up automatically, no other changes needed.
4. Add a JUnit test under `src/test/java/nl/ovp/model/`, ideally checking a
   known limiting case (e.g. a parameter that reduces the model to a simpler,
   already-tested one — see `PredatorPreyModelTest.withZeroWolvesReducesToCompetitionModel`).
