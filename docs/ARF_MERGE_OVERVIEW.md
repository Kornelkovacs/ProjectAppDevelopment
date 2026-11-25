# AgriculturalRiskFactors (`ovp-model`) vs. our app: what's similar, what's new, and what to merge

*Written 2026-11-25. Compares `../../AgriculturalRiskFactors-main/ovp-model/` (outside this repo) (Team 7, "Wolves, Warmth &
Wild Herds", model v0.1.0, progress report weeks 1–3) with this repository.*

> **Status 2026-11-25:** step 2 is merged as `SeasonalGrazingModel` (model 2), using option (a):
> ARF's logistic grass with GP(T(t)) for growth and 1 − GP for die-back, a calendar season for births
> and winter starvation, births scaled by `max(0, 1 + s_i ΔT)`, `grazingAreaHa` = 1,080 ha, and the
> single shared grass pool kept for now (exclusion to be checked after calibration). All its parameters
> are still ARF's provisional values. Not done yet: steps 1 and 3, calibration, wolves on top of the
> seasonal model, and a replay suited to this model (October start, 1,880 ha until 2018, the
> 2017–18 die-off not given as an event).

All numbers below were re-run, not copied from the READMEs. ARF was built with its own `run_all.sh`
steps in a scratch copy: 16/16 tests pass and the three scenarios run. Our app was run with
`java -jar target/app.jar --cli`.

> **Authorship check before merging.** The ARF README lists Team 7: Mehedi Hasan, Paulo Rodriguez
> Calambrogio and Toofan Baradaran Azimi. If this is our own group's work, merge freely and keep the
> commit author or co-author. If it is another team's work, agree on reuse with them and the
> lecturer first, and credit them in the report. The git log and the report are graded.

---

## 1. Both projects at a glance

| | **Our app** (`nl.ovp`) | **ARF** (`nl.inholland.ovp`) |
|---|---|---|
| Purpose | Staatsbosbeheer research questions A/B/C | The same three questions (they call them SQ1–SQ3, with SQ4–5 for extreme events and tipping points) |
| Language / build | Java 17, Maven, JUnit 5, no runtime dependencies | Java 17, plain `javac` (Maven optional), JUnit 4 jars in `lib/`, no runtime dependencies |
| User interface | Swing GUI (parameter panel and Java2D chart) and `--cli` | Command line only (`run scenario.json`, `verify`); a JavaFX "model explorer" is planned |
| Models | Logistic → Lotka–Volterra competition (fitted) → predator–prey with wolves (Holling II, multi-prey) | One model: **grass as a state variable**, three grazers, seasons, winter starvation |
| Grass | Brief's Appendix 3 growth potential; used only as a ratio that scales K under ΔT | Logistic grass biomass (t DM) with seasonal growth and winter die-back; animals eat it (Holling II) |
| Climate | ΔT slider, KNMI 1983–2025 temperature profile fitted | Not yet; KNMI'23 scenario table added as data |
| Wolves | Yes (attack rate, preference, handling time, conversion, mortality 0.23 from data) | Not yet (planned for week 5; Isle Royale data planned for validation) |
| Data | Moodle counts 1983–2025, grass height, wolves (reference area), KNMI monthly, events, NOS winter deaths, wolf rates | Van Geel Committee reference points, KNMI'23 scenarios. No Moodle counts yet ("to add") |
| Calibration | r, K, α fitted on 1983–2015 (R² 0.95–0.98); replay of 2018–2025 | None: all 16 non-area parameters are "provisional" |
| Parameters | Java fields in `ModelParameters`, provenance in comments | JSON with **value, unit, source and status** per parameter |
| Reproducibility | Scripts per step, CSV export | `run_all.sh` rebuilds everything; each output CSV has a `.meta.json` (model version, all parameters, seed); scenarios are JSON files |
| Tests | 9 test classes (model, solver, data, UI, CLI) | 16 verification tests (solver accuracy, convergence order, mass balance, reproducibility) |

**In short:** our app is ahead on data, calibration, wolves, climate and the GUI. ARF is ahead on
**food supply as an explicit mechanism** (grass that runs out in winter) and on **reproducibility
and traceability infrastructure**. The two are mostly complementary.

### What both share already (no work needed)

- An RK4 fixed-step solver with an exact-logistic test.
- A clamp or `max(…, 0)` to keep populations non-negative.
- An Okabe–Ito colour-blind-safe palette with the same colour per species. ARF's figure script uses
  the same hex codes as our `ChartPanel`.
- No-dependency Java 17, and layering that keeps the model and core independent of the UI.
- Gotelli as the main source. Both name Holling type II, and both name the 2017–18 die-off as the
  validation target.
- An identical `.github/modernize/java-upgrade` tooling folder. This is tool output, not project
  content; ignore it.

---

## 2. What is new in ARF and missing from our app

### 2.1 Model: grass as a resource, with seasons and winter starvation (`GrazerModel`)

```
s(t)    = (1 − cos 2πt) / 2                                    growing season, 0 on 1 Jan, 1 on 1 Jul
f(G)    = G / (G + G_h)                                        feeding level (Holling type II)
dG/dt   = r s(t) G (1 − G/K) − d (1 − s(t)) G − f(G) Σ q_i N_i grass, tonnes dry matter
dN_i/dt = N_i [ 2 b_i s(t) f(G) − m_i − w_i (1 − s(t)) (1 − f(G)) ]
```

Species interact **only through the shared grass** (resource competition), not through an α matrix.
Births happen in summer and depend on food; extra deaths happen in winter when food is short.

**Why this matters for us.** It is exactly the piece our own documents list as missing:

- `docs/CALIBRATION.md`, validation point 4: *"The model has no winter starvation. It only
  reproduces the die-off because the die-off is given as an input event."*
- `ideas.md`: *"Build a seasonal model where grass runs out in winter."*
- `docs/NEW_DATA_OVERVIEW.md`, idea 6: seasonal / winter-bottleneck model.
- Assessment criterion **2.9.2 #1**, *"basic population growth including food supply"*. Our models
  carry food only implicitly, through K. ARF makes food a modelled quantity.

What it does today (provisional parameters, checked by re-running):

| Scenario | ARF result |
|---|---|
| 1,100 animals (500 deer, 160 cattle, 440 horses), from 1 April, no culling, 30 years | Grows to about **1,710** and levels off by year 20 (845 deer, 381 cattle, 482 horses). That is **above the 1,500 winter ceiling** from about year 8 |
| October 2017 herd (5,230) on 1,880 ha, no culling | Falls to 3,684 by spring 2018 (−30 %) and keeps declining in the second winter. The die-off **emerges** from the model; it is not an input |

### 2.2 Data that we don't have

| File | Content | Use in our app |
|---|---|---|
| `data/reference_points.csv` | Van Geel Committee (2018), with chapter references: Oct 2017 counts (3,950 deer / 1,050 horses / 230 cattle), net growth ≈ +700 (Nov 2016 → Nov 2017), ≈ 3,000 winter deaths, **winter ceiling 1,500**, 1,100 target, **1,080 ha grassland after the measures**, **1,880 ha grazing area (2018)**, reference density 1.4 animals/ha | A concrete threshold for "stable" (A) and for "forces a different policy" (C); the area for the grass model; validation figures |
| `data/knmi23_scenarios.csv` | KNMI'23 key figures vs. 1991–2020: annual ΔT **+0.9 (L 2050), +1.5–1.6 (H 2050), +4.1–4.4 (H 2100)**; winter/summer ΔT; precipitation; evaporation; maximum precipitation deficit Apr–Sep (up to +79 %) | Turns the ΔT slider into **named, sourced scenarios** for research question C; adds drought indicators (rain/evaporation, which `ideas.md` wants) |

Planned in ARF but not present: Isle Royale wolf–moose series (structural validation of a
predator–prey model) and daily KNMI Lelystad data. We already have KNMI data. Isle Royale would be
new and directly useful for research question B.

### 2.3 Code and infrastructure

| ARF piece | What it does | Our equivalent | Worth taking? |
|---|---|---|---|
| `model/Parameters` and `params/base_v0.1.json` | Every parameter has value, unit, source and **status** (literature / provisional / calibrated / scenario); a missing parameter is rejected | Fields plus `// TODO: fit/look up` comments | **The idea, yes.** Generate the report's parameter table from it. Keep the values in `ModelParameters` (project invariant) |
| `io/Scenario` and `scenarios/*.json` | A scenario = parameter file, overrides, initial state, start date (e.g. 1 October), years, dt, seed | CLI flags (`--wolves`, `--years`, `--replay`) | **Yes, for the report runs (A/B/C).** Each figure becomes one file you can reproduce |
| `.meta.json` per output | Model version, scenario, every parameter value, solver, dt, seed, Java version | — | **Yes**: cheap, and it makes every report figure traceable |
| `model/Version` | Version string stamped on outputs and figures | — | Yes (one constant) |
| `io/Json` | ~170-line dependency-free JSON reader/writer | — | Only if we adopt scenario files |
| `core/RK4Solver`, `OdeSystem`, `Trajectory` | In-place RK4, `outputEvery` thinning, start time ≠ 0 | `OdeSolver`, `RungeKutta4Solver`, `Simulator`, `SimulationResult` | **No.** Duplicate layer. Take only the *ideas*: output thinning (needed when dt = 0.001) and a start-of-year offset |
| `cli verify` and fig. 4 | RK4 error vs. dt on a log–log plot, fitted order 4.10 | We have Euler and RK4 "so the report can compare them", but no comparison yet | **Yes**: gives the report's verification chapter a figure |
| Verification tests | Convergence order, exponential decay, grass bounded, non-negative states over 50 years, no food → decline, grass eaten = f·q·N (mass balance), bit-identical reruns, input validation | RK4 vs. logistic, clamp test, limiting cases | **Yes**: port the generic ones to JUnit 5 now and the grass ones together with the model |
| `run_all.sh` | One command: compile → tests → all scenarios → all figures | Separate scripts | Yes: a `scripts/run_all.sh` around `mvn package`, the CLI and the plot scripts |
| `analysis/make_figures.py` | Every figure carries a footer with scenario, model version and parameter set | `plot_validation.py` | Adopt the footer convention |

### 2.4 Documentation and process

- **Progress report weeks 1–3**, written in the **ODD protocol** (Overview, Design concepts, Details),
  with a parameter table generated from the JSON.
- **Report structure following TRACE** (Grimm et al. 2014): Introduction → Model description →
  Data evaluation → Conceptual model evaluation → Verification → Calibration → Model analysis →
  Validation → Conclusions → Discussion. It keeps verification and validation separate. Our
  `APPLICATION_REPORT.md` has no report outline yet.
- **Literature we don't cite yet:** Holling (1959), Strogatz (2015) for stability and bifurcation,
  Torres-Porras et al. (2009) on drought × density in red deer, Grimm et al. (ODD/TRACE), Wilkinson
  et al. (2016, FAIR), Van Geel Committee (2018), Provincie Flevoland (2020), KNMI (2023).
- **Questions for the Staatsbosbeheer guest lecture**, for example: what counts as "stable" (a
  number, a range or a condition score)? What is the grazing area today? How does Staatsbosbeheer
  view wolves, given the fence?

---

## 3. Two findings from the comparison that affect our app now

### 3.1 The Moodle counts are autumn counts, not 1 January counts

Our `herbivores_counts.csv` row **2017 = 230 cattle / 1,050 horses / 3,950 deer**. That is
**identical** to Van Geel's **October 2017** figures in ARF's `reference_points.csv`. Our 2016 → 2017
change (4,500 → 5,230, **+730**) also matches Van Geel's *"almost +700, Nov 2016 – Nov 2017"*.

So the "count date unclear" problem in `docs/CALIBRATION.md` (validation point 3) has a likely
answer: the counts describe **autumn (Oct/Nov)**. We tested re-dating to 1 April and it did not
help; **October/November has not been tested**. Re-dating the replay (`--replay`, start ≈ year +
0.8) and the event windows accordingly could change the poor 2018–2025 out-of-sample result. It
also shifts the fit by most of a year for every species. This is still worth confirming with the
lecturer, but it is now based on a source, not a guess.

### 3.2 The two models disagree on research question A, mainly because of area and capacity

| | Our app (competition, fitted) | ARF (grass resource, provisional) |
|---|---|---|
| 1,100 animals, no culling | → **≈ 5,350** (1,267 horses, 4,081 deer, cattle → 0) | → **≈ 1,710** (all three species coexist) |
| Implied area | K fitted on 1983–2017, when the grazing area was ≈ **1,880 ha** | **1,080 ha** (grassland left after the 2018 measures) |

Both agree that **1,100 is not an equilibrium without culling**. Our K values describe the
pre-2018 reserve, though. If capacity scales with grassland area, today's K would be roughly
1,080 / 1,880 ≈ 0.57 × ours, giving about 3,000 animals. That is a modelling assumption to state in
the report, not a fact, but leaving it out probably overstates the herd for research question A.

ARF's provisional parameters also have **cattle rising and horses falling**. That is the opposite of
the observed decline of cattle after 2005, which our fitted α reproduce. ARF's numbers must be
calibrated before any of its results go into the report.

### 3.3 Warning for the merge: the brief's grass yield is far too low if grass becomes a state

Our `GrassModel` uses the brief's Appendix 3 with 60 kg/ha/**month** at peak. With our fitted
temperature profile that is **≈ 355 kg DM/ha/yr**. Today only the ratio is used (`grassFactor`), so
the absolute value never mattered. In an ARF-style model where animals eat the grass, it does:

| Area | Grass/yr at 60 kg/ha/month | Share of the Oct 2017 herd's demand (≈ 8,240 t DM/yr with ARF's intakes) |
|---|---|---|
| 1,080 ha | 383 t | 5 % |
| 1,880 ha | 667 t | 8 % |
| 5,600 ha | 1,987 t | 24 % |

The herd that was actually observed could not have existed on that much grass. Read as **per day**,
the same formula gives ≈ 10.8 t DM/ha/yr. That is in the normal range for ryegrass and of the same
order as ARF's ≈ 6 t DM/ha/yr. The unit in Appendix 3 needs a team decision, backed by the Taube
(1990) / New Zealand source, before the two grass models are combined. Add this to the questions for
the lecturer.

---

## 4. Mapping to the assignment (brief §2.9.2 product criteria)

| # | Criterion | Our app today | What ARF adds |
|---|---|---|---|
| 1 | Population growth **including food supply** | Implicit (K; ΔT scales K) | **Explicit grass resource, seasonal births, winter starvation**: the biggest gain |
| 2 | Interaction between large herbivores | Lotka–Volterra α, fitted, 0.3 from the brief | A second, mechanistic form (shared resource). The report can **compare** direct vs. resource-mediated competition (TRACE "conceptual model evaluation") |
| 3 | Prey–predator | Multi-prey Holling II wolves | Nothing yet. Isle Royale idea for validation |
| 4 | Stakeholder needs in UML / use cases | Not started | Staatsbosbeheer questions and ceiling/density criteria feed the use cases ("check whether a scenario stays under the 1,500 ceiling") |
| 5 | Architecture in UML | Not started | A clear "core/model/io independent of UI" story; reuse it in the component diagram |
| 6 | Implementation of the mathematical models | Solid | More verification tests, convergence figure |
| 7 | Implementation of prioritised use cases | GUI, CLI, replay, export | Scenario files and traceable outputs: "re-run the figure from the report" as a use case |
| 8 | Final report | `APPLICATION_REPORT`, `CALIBRATION` | ODD description, TRACE outline, literature list, auto-generated figures and tables |

Timeline (brief §2.7): we are in project week 5. **Mid-project assessment 2 Dec**, **draft final
models Mon 14 Dec 10:00**, draft report 4 Jan, final report 11 Jan, presentation 20 Jan.

---

## 5. Merge options, in priority order

**Recommended approach:** port ARF's ideas into our architecture. Don't import its code base. Our
app has the GUI, the data, the calibration and the wolves; ARF's `core/` would duplicate our solver
layer and break our invariants. Take its **model, data, tests and conventions**.

### Step 1: quick wins (≈ 1 day; useful for the mid-project assessment on 2 Dec)

1. **Add the two data tables.** Put `reference_points.csv` and `knmi23_scenarios.csv` in
   `data/raw/literature/`. Have `scripts/clean_data.py` copy and check them into `data/clean/`
   (the rule: Java reads only `data/clean`), and document them in `data/README.md`. Add readers to
   `CsvDataLoader` with tests.
2. **Policy thresholds in the analysis.** Use the 1,500 winter ceiling (and 1.4 animals/ha) as the
   operational definition of "stable / acceptable" for A, and of "forces a different policy" for C.
   Draw it as a dashed line in `ChartPanel`, as ARF does in its fig. 2.
3. **KNMI'23 presets for C.** ΔT = 0.9 / 1.6 (2050) and 4.1 / 4.4 (2100) as named presets in the
   GUI and in `/run-scenario`, so the answer to C cites KNMI (2023) instead of arbitrary slider
   values.
4. **Re-test the replay with autumn count dates** (§3.1). Add a short note to `CALIBRATION.md`.
5. **Port the generic verification tests** to JUnit 5: convergence order ≈ 4, exponential decay,
   bit-identical reruns. Add an Euler-vs-RK4 convergence figure.

### Step 2: the main merge, a new seasonal grazing model (before 14 Dec)

Use `/add-model` to add **iteration 4, `SeasonalGrazingModel`**, based on ARF's `GrazerModel` but
following our conventions:

- **State** `[cattle, horses, deer, grass]`. Grass goes *after* the species, so the invariant
  "state order = `Species.ordinal()`" holds; ARF uses `[grass, deer, cattle, horses]`.
- **Parameters** as fields in `ModelParameters`, included in `copy()`, with ARF's
  source/status text as comments and `// TODO: fit/look up` where provisional.
- **Grass growth driven by temperature instead of a fixed cosine.** Replace ARF's `s(t)` with
  `GrassModel.growthPotential(temperatureAt(t, ΔT))`. Then ΔT acts *mechanistically* on food
  (research question C) instead of only scaling K. This needs the unit decision in §3.3 and the
  area decision (1,080 vs. 5,600 ha).
- **Events** `M_i(t)` added in the same way as in `CompetitionModel`, so `--replay` works.
- **Tests**, the ARF set translated: no animals → grass seasonal and bounded; no grass → every
  species declines; grass eaten = f(G)·Σ q_i N_i; absent species stays absent.
- **Chart:** grass (tonnes) doesn't share an axis with head counts. Show the feeding level f(G)
  (0–1) in a small second panel, as ARF's fig. 2 does, or hide grass by default.
- **Solver step:** ARF needs dt ≈ 0.001 yr for the seasonal cycle. Add output thinning
  (`outputEvery`) to `Simulator`, so the GUI and CSV don't get 20,000 rows.

Then **iteration 5: wolves on top of the seasonal model** (reuse `PredatorPreyModel`'s
kill term). Register it last, because it is the most general model. Its test: with zero wolves it
reduces to `SeasonalGrazingModel`.

**Calibration** (`/calibrate-parameters`): fit b_i, m_i, w_i (and the grass constants) with the same
`fit_parameters.py` approach on 1983–2015. Use `winter_mortality_nos.csv` (2010–2018) and the
2017–18 die-off as **independent validation of winter starvation**. That data was always meant for
this, and ARF lists it as "to be calibrated on 2017–2018".

### Step 3: reproducibility and report infrastructure (during the report weeks)

- **Scenario JSON files and `.meta.json`** for the report runs: `scenarios/A_1100_unmanaged.json`,
  `B_wolves_sweep.json`, `C_knmi23_Hd2100.json`, … loaded by `--scenario FILE` (port `io/Json`).
  The GUI keeps working as it does.
- **A `Version` constant** stamped on CSV headers and figure footers.
- **`scripts/run_all.sh`**: `mvn test` → `mvn package` → all scenarios → all figures.
- **Parameter table** with unit, source and status, generated for the report appendix and for
  `MODEL_EQUATIONS.pdf`.
- **Report:** adopt the TRACE chapter structure, the ODD model description and the extra literature
  (§2.4).

### Optional / later

- Isle Royale wolf–moose series for structural validation of the predator–prey model (B).
- KNMI'23 summer precipitation and evaporation → a drought factor on grass growth (the "rain and
  evaporation" idea in `ideas.md`; Torres-Porras et al. 2009 as source).
- Extreme-event scenarios (one very wet or dry winter) and a bifurcation or tipping-point analysis
  (Strogatz). These are in ARF's roadmap and would strengthen C.

### Don't take

- ARF's `core/` (solver, trajectory, ODE interface): it duplicates ours.
- The JUnit 4 jars in `lib/`, ARF's `pom.xml`, and the `.github/modernize` folder.
- ARF's provisional parameter **values** as final numbers: they contradict our calibrated cattle
  trend (§3.2).

---

## 6. Decisions the team has to make

1. **Grazing area:** 5,600 ha (brief: whole reserve), 1,880 ha (grazing area up to 2018) or
   1,080 ha (grassland after the measures; Van Geel)? It matters directly once grass is a state.
2. **Grass yield unit** in Appendix 3: per month (as implemented) or per day (§3.3)?
3. **Count date:** treat the Moodle counts as autumn counts (§3.1)? Confirm with the lecturer.
4. **Definition of "stable"** for A: equilibrium, under the 1,500 ceiling, or a culling quota?
   This can be asked at the Staatsbosbeheer session.
5. **Which competition form leads** in the conclusions (α matrix vs. shared grass)? Or report both
   as a structural sensitivity check.
