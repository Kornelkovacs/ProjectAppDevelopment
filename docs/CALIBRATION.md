# Calibration of the herbivore parameters

*2026-11-25. Reproduce with `python3 scripts/fit_parameters.py` (fit) and
`mvn package && python3 scripts/plot_validation.py` (validation figure). Full numbers:
`docs/calibration_fit.csv`.*

## Data and method

- **Data:** `data/clean/herbivores_counts.csv`, natural period only. Default variant: 1983–2017
  rows with `reliable = True`, which means 1983–2015 (2016–2017 are "not always 100%
  trustworthy"). Sensitivity variant: 1983–2017 including 2016–2017. From winter 2017–18 onwards
  there is a die-off, culling and relocation, so those years are not used for fitting.
- Each species starts at its first real count (cattle 30 in 1983, horses 20 in 1984, deer 45 in
  1992). Empty cells are gaps, not zeros.
- **Step 1, logistic per species** (Gotelli ch. 2), closed form
  `N(t) = K / (1 + ((K − N0)/N0) e^(−rt))`, fitted with `scipy.optimize.curve_fit`. This is only a
  comparison: it ignores competition, and for cattle it fits badly (R² = 0.71) because cattle
  *declined* after 2005 while the other two kept growing.
- **Step 2, Lotka–Volterra competition** (Gotelli ch. 5). This is the same ODE as
  `CompetitionModel.java` at ΔT = 0, integrated with `solve_ivp` and fitted with `least_squares`.
  The residuals are on log counts so that the deer (thousands) do not swamp the cattle (hundreds).
  The 0.3 effect of deer on cattle and on horses is fixed by the brief.
- **Standard errors** come from the Jacobian at the optimum. They are approximate, because the
  counts are autocorrelated. Their main use is to flag parameters the data cannot pin down.

## Which competition model

| Model | Free α | AIC | Problem |
| --- | --- | --- | --- |
| Full: four free off-diagonal α | 4 | −313.2 | **Not identifiable.** Three α end on their bounds (0 or 3), SE(K_cattle) = 5,000 on K = 3,100, SE(K_deer) = 27,500 |
| **Constrained (chosen)**: a = α_cattle,horses = α_horses,cattle; b = α_deer,cattle = α_deer,horses | 2 | −308.1 | No parameter on a bound; still weak for α and for K of cattle and deer |

Justification for the constraint:
- Cattle and horses are both bulk grazers of the same grass, so their overlap is taken as
  symmetric (one value a).
- Deer experience either grazer the same way (one value b).

The full model is better by 5 AIC units, but only by putting coefficients on their bounds,
including "one horse takes as much cattle food as three cattle". That is not defensible in the
report.

## Result (defaults now in `ModelParameters`)

| Parameter | Cattle | Horses | Deer |
| --- | --- | --- | --- |
| r (1/yr) | **0.21** (0.213 ± 0.008) | **0.21** (0.211 ± 0.009) | **0.34** (0.344 ± 0.037) |
| K, species alone | **1,070** (± 410) | **2,500** (± 400) | **5,100** (± 2,570) |
| R² on the counts | 0.95 | 0.98 | 0.97 |

| α (effect on row of column) | Cattle | Horses | Deer |
| --- | --- | --- | --- |
| Cattle | 1 | **0.24** (a, ± 0.55) | 0.3 (brief) |
| Horses | **0.24** (a) | 1 | 0.3 (brief) |
| Deer | **0.80** (b, ± 1.28) | **0.80** (b) | 1 |

**Well determined:**
- the growth rates;
- K for horses.

**Weakly determined (state this in the report and sweep them in scenarios):**
- K for cattle and deer;
- the competition coefficients a and b.

The 1983–2017 series simply does not contain enough independent variation to separate them.
They are reasonable values that reproduce the data, not measurements.

**Sensitivity check (including 2016–17):**
- r stays the same (0.215 / 0.210 / 0.339);
- K changes to 890 / 2,190 / 4,970;
- a drops to 0 (on its bound) and b changes to 0.69.

The qualitative behaviour is the same in both variants.

## What the calibrated model says

- **No stable coexistence of all three species.** The three-species equilibrium has a negative
  cattle number (N* ≈ (−600, 1,270, 4,560)), and every fitted variant agrees on this.
- **Cattle are slowly squeezed out by deer and horses.** In the long run the model settles at
  about 1,280 horses and 4,080 deer, with no cattle. Cattle cannot re-invade, because their
  growth bracket at that state is 1 − (0.24·1,276 + 0.3·4,079)/1,070 ≈ −0.43.
- This matches the observed decline of the cattle after 2005, and it is the
  data-driven version of §4.4 of `MODEL_EQUATIONS.pdf`.
- **Research question A:**
  - The policy target of 1,100 animals (300 / 300 / 500) is far below what the reserve sustains
    in the model.
  - Left alone, the herds grow to about 5,300 animals within 20–50 years, so 1,100 is **not**
    a natural equilibrium.
  - It can only be held by removing animals every year. The size of that culling quota is the
    next analysis step (`/run-scenario`).

## Validation (`docs/figures/validation.png`, computed by the Java app)

| Period | Species | Mean abs. error | RMSE |
| --- | --- | --- | --- |
| 1983–2017 (fit) | cattle / horses / deer | 16% / 13% / 7% | 49 / 92 / 210 |
| 2018–2025 (out of sample, `--replay 2017`) | cattle / horses / deer | 55% / 70% / 74% | 206 / 288 / 1,228 |

The 2018–2025 replay is poor. It cannot confirm or reject the model, because the managed-period
data are themselves inconsistent:

1. **Counts are low-trust** (blue in the source) for 2016–2024.
2. **The counts contradict the reported removals.** Deer rose by 875 from 2019 to 2020 while
   1,785 were shot between Dec 2018 and Oct 2019. That is a +57% jump, while even unlimited
   growth at r = 0.34 gives +40% per year.
3. **The count date is unclear.** The 2018 count already shows the 2017–18 die-off
   (5,230 → 3,130), so the counts are probably taken after winter, not on 1 January. Re-dating
   the counts to 1 April did not fix the replay (checked).
4. **The model has no winter starvation.** It only reproduces the die-off because the die-off
   is given as an input event.

Point 3 is a question for the lecturer: when in the year are the counts taken?

## Still placeholders (`// TODO: fit/look up`)

| Parameter | Why it is not fitted here |
| --- | --- |
| `climateSensitivity` | No temperature signal can be separated in 35 years of counts. Needs literature or a reasoned assumption (signs fixed by the brief) |
| `grassVar` | `grass_height.csv` is height on 1 August, not yield, and is a single point per year. It does not constrain the width of the growth curve |
| `attackRate`, `handlingTime`, `conversionEfficiency`, `preyPreference` | There is no wolf data for the Oostvaardersplassen. Needs kill-rate literature (e.g. Jędrzejewski et al. 2000, 2002); the `ecology-literature` agent can do this |

`wolfMortality` = 0.23 comes from `data/clean/wolf_rates.csv` (see `data/README.md`).
