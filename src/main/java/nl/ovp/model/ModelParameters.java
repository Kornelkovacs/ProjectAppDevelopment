package nl.ovp.model;

import java.util.Arrays;
import java.util.List;

/**
 * Single holder for every numeric parameter used by every {@link PopulationModel}
 * and by {@link GrassModel}. Keeping all parameters in one place makes it possible
 * for the GUI to expose them generically and for every model to share the same
 * calibration.
 * <p>
 * Per-species arrays are indexed by {@link Species#ordinal()} (cattle, horses,
 * deer). Fields are public and mutable so the GUI (and tests) can bind to them
 * directly; use {@link #copy()} to obtain an independent snapshot before handing
 * parameters to a simulation run.
 * <p>
 * Growth rates, carrying capacities and competition coefficients are fitted to
 * {@code data/clean/herbivores_counts.csv} by {@code scripts/fit_parameters.py}; wolf
 * mortality comes from {@code data/clean/wolf_rates.csv}; the temperature profile from KNMI
 * data (see Gotelli, "A Primer of Ecology", ch. 2 for logistic growth and ch. 5 for
 * competition). Values still unvalidated (climate sensitivities, grass width, wolf
 * predation, and all parameters of the seasonal grazing model) are marked with
 * {@code // TODO: fit/look up}.
 */
public final class ModelParameters {

    private static final int N = Species.values().length;

    // --- Initial state. Defaults = Staatsbosbeheer's policy target. ---

    /** Initial cattle count at t = 0. Default 300 (policy target: 600 cattle+horses). */
    public double initialCattle = 300.0;

    /** Initial horse count at t = 0. Default 300 (policy target: 600 cattle+horses). */
    public double initialHorses = 300.0;

    /** Initial deer count at t = 0. Default 500 (policy target). */
    public double initialDeer = 500.0;

    /** Number of wolves released at t = 0. Default 0 (no predator). */
    public double initialWolves = 0.0;

    // --- Logistic / competition growth parameters, per species. ---

    /*
     * growthRate, carryingCapacity and competitionAlpha are fitted jointly: least squares on log
     * counts of the competition ODE (deltaT = 0), 1983-2017 counts with reliable = True
     * (i.e. 1983-2015), scripts/fit_parameters.py, "constrained, chosen" model; results and
     * standard errors in docs/calibration_fit.csv and docs/CALIBRATION.md. R² on the counts:
     * cattle 0.95, horses 0.98, deer 0.97. Values rounded.
     */

    /** Intrinsic growth rate r_i (per year), indexed by {@link Species#ordinal()}. */
    public double[] growthRate = {
        0.21, // CATTLE  // fitted 0.213 ± 0.008, scripts/fit_parameters.py
        0.21, // HORSES  // fitted 0.211 ± 0.009, scripts/fit_parameters.py
        0.34  // DEER    // fitted 0.344 ± 0.037, scripts/fit_parameters.py
    };

    /**
     * Carrying capacity K_i (head count) of each species <em>alone</em>, indexed by
     * {@link Species#ordinal()}. With the other species present the reachable numbers are lower
     * (competition). K for cattle and deer are weakly determined by the data (see SE).
     */
    public double[] carryingCapacity = {
        1070.0, // CATTLE // fitted 1068 ± 410 (weakly determined), scripts/fit_parameters.py
        2500.0, // HORSES // fitted 2495 ± 401, scripts/fit_parameters.py
        5100.0  // DEER   // fitted 5093 ± 2570 (weakly determined), scripts/fit_parameters.py
    };

    /**
     * Lotka-Volterra competition coefficients alpha[i][j]: effect of species j
     * on species i's carrying capacity, indexed by {@link Species#ordinal()}.
     * Diagonal entries are 1.0 by convention (a species' own density counts at
     * full weight against its own carrying capacity). The brief fixes the
     * effect of deer on cattle and horses at 30%. The other four entries are
     * fitted with two shared values (four free values are not identifiable from
     * the counts): a = cattle&lt;-&gt;horses (same grazing guild, symmetric),
     * fitted 0.24 ± 0.55; b = effect of cattle or horses on deer, fitted 0.80 ± 1.28.
     * Both are weakly determined; treat them as scenario values for sensitivity runs.
     */
    public double[][] competitionAlpha = {
        // CATTLE  HORSES  DEER
        {  1.0,    0.24,   0.3 },  // a fitted; 0.3 from the brief
        {  0.24,   1.0,    0.3 },  // a fitted; 0.3 from the brief
        {  0.80,   0.80,   1.0 }   // b fitted
    };

    /**
     * Climate sensitivity s_i applied to carrying capacity as
     * {@code max(0, 1 + s_i * deltaT)}. Per the brief, warming benefits horses
     * (s_HORSES > 0) and harms cattle (s_CATTLE < 0); deer sensitivity is a
     * placeholder.
     */
    public double[] climateSensitivity = {
        -0.05, // CATTLE // TODO: fit/look up (must stay negative per brief)
         0.05, // HORSES // TODO: fit/look up (must stay positive per brief)
         0.0   // DEER   // TODO: fit/look up
    };

    /** Temperature rise relative to today, in degrees Celsius. GUI range: -2..+6, step 0.5. */
    public double deltaT = 0.0;

    // --- Grass / growth-potential model (Appendix 3 of the project brief). ---

    /** Optimum temperature t0 for C3 grass, in degrees Celsius. Fixed by the brief, not a placeholder. */
    public double grassOptimumTemperature = 20.0;

    /** Width (variance-like spread) of the growth-potential Gaussian. */
    public double grassVar = 8.0; // TODO: fit/look up

    /**
     * Mean annual temperature today, in degrees Celsius, used to build the monthly cosine profile.
     * Fitted: 9.96 °C, least squares on KNMI monthly means 1983–2017
     * ({@code data/clean/climate_monthly.csv}, Lelystad; De Bilt adjusted before 1990),
     * {@code scripts/fit_temperature_profile.py}. Same window as the herbivore fit, so
     * {@code deltaT = 0} is the climate in which the herds were observed.
     */
    public double meanAnnualTemperature = 10.0;

    /**
     * Seasonal temperature amplitude (half the peak-to-trough swing), in degrees Celsius; summer peaks mid-July.
     * Fitted: 7.39 °C, same fit as {@link #meanAnnualTemperature} (R² = 0.89; a free-phase
     * fit puts the peak at ~22 July, so the fixed mid-July peak is justified).
     */
    public double seasonalAmplitude = 7.4;

    /** Peak grass growth rate at optimum temperature, in kg/ha/month. Fixed by the brief. */
    public double grassMaxGrowthKgPerHaPerMonth = 60.0;

    /** Total grassland area of the Oostvaardersplassen, in hectares. Fixed by the brief. */
    public double areaHa = 5600.0;

    // --- Predator-prey (wolf) parameters, per prey species. ---

    /** Wolf attack rate a_i per prey species, indexed by {@link Species#ordinal()}. */
    public double[] attackRate = {
        0.001, // CATTLE // TODO: fit/look up
        0.001, // HORSES // TODO: fit/look up
        0.002  // DEER   // TODO: fit/look up
    };

    /**
     * Wolf prey preference w_i per species, in [0, 1], indexed by
     * {@link Species#ordinal()}. GUI-adjustable. Default: no preference.
     */
    public double[] preyPreference = {
        1.0, // CATTLE // TODO: fit/look up
        1.0, // HORSES // TODO: fit/look up
        1.0  // DEER   // TODO: fit/look up
    };

    /** Handling time h (years) in the multi-prey Holling type II functional response. */
    public double handlingTime = 0.02; // TODO: fit/look up

    /** Conversion efficiency e_i (wolves produced per prey killed), indexed by {@link Species#ordinal()}. */
    public double[] conversionEfficiency = {
        0.01, // CATTLE // TODO: fit/look up
        0.01, // HORSES // TODO: fit/look up
        0.01  // DEER   // TODO: fit/look up
    };

    /**
     * Wolf mortality rate m (per year), in the absence of sufficient prey.
     * From data: 0.23 = recorded deaths 0.141 + wolves lost without a recorded death
     * (dispersal or unrecorded deaths) 0.090 per wolf per year, means over both regions
     * 2010-2025 in {@code data/clean/wolf_rates.csv} ({@code scripts/clean_data.py}, measured
     * values only). Dispersal counts as a loss because the Oostvaardersplassen is far smaller
     * than a wolf pack's range. Reference area, not the Oostvaardersplassen: an indication only.
     * Ranges for sweeps: SD 0.057 (deaths) and 0.064 (lost).
     */
    public double wolfMortality = 0.23;

    // --- Seasonal grazing model (iteration 4, SeasonalGrazingModel). ---
    /*
     * Starting values are the provisional first estimates of the AgriculturalRiskFactors project
     * (ovp-model, params/base_v0.1.json, Team 7), with their source text. None is calibrated yet:
     * births, mortalities and the grass constants are to be fitted on the 1983-2015 counts
     * (with grazingAreaHa = 1880), and winter starvation checked against
     * data/clean/winter_mortality_nos.csv and the 2017-18 die-off.
     */

    /**
     * Grazing area (ha) the grass in {@link SeasonalGrazingModel} grows on. Default 1080 ha:
     * grassland left after rewetting and shelter woodland, Begeleidingscommissie beheer
     * Oostvaardersplassen (Van Geel Committee, 2018), ch. 5, i.e. the situation today.
     * Use 1880 ha (grazing area up to 2018, same report, ch. 2) when fitting on 1983-2017.
     * Separate from {@link #areaHa} (5600 ha, the brief's figure for the whole reserve).
     */
    public double grazingAreaHa = 1080.0;

    /** Maximum standing grass biomass, tonnes dry matter per ha. */
    public double grassCapacityTPerHa = 4.0; // TODO: fit/look up (ARF provisional first estimate)

    /**
     * Grass growth rate r at the optimum temperature (GP = 1), per year. ARF chose 12/yr so that
     * potential production is about 6 t DM/ha/yr.
     */
    public double grassGrowthRate = 12.0; // TODO: fit/look up (ARF provisional first estimate)

    /** Grass level at which intake is half of maximum (G_h), tonnes dry matter per ha. */
    public double grassHalfSaturationTPerHa = 0.6; // TODO: fit/look up (ARF provisional first estimate)

    /** Die-back of standing grass outside the growing season, per year (scaled by 1 - GP). */
    public double grassWinterDecay = 3.0; // TODO: fit/look up (ARF provisional first estimate)

    /** Standing grass at t = 0 (1 January), as a fraction of capacity. ARF scenario value. */
    public double initialGrassFraction = 0.3; // TODO: fit/look up

    /**
     * Maximum grass intake q_i per animal, tonnes dry matter per year, indexed by
     * {@link Species#ordinal()}. The deer/cattle and deer/horses ratios (0.28 and 0.30) match
     * the brief's 30 % effect of deer on cattle and horses.
     */
    public double[] intake = {
        3.6, // CATTLE // TODO: fit/look up (ARF: about 10 kg DM per day)
        3.3, // HORSES // TODO: fit/look up (ARF: about 9 kg DM per day)
        1.0  // DEER   // TODO: fit/look up (ARF: about 2.7 kg DM per day)
    };

    /**
     * Maximum per-capita birth rate b_i with ample food, per year, indexed by
     * {@link Species#ordinal()}. Births happen in the growing season.
     */
    public double[] maxBirthRate = {
        0.30, // CATTLE // TODO: fit/look up (ARF provisional first estimate)
        0.25, // HORSES // TODO: fit/look up (ARF provisional first estimate)
        0.40  // DEER   // TODO: fit/look up (ARF provisional first estimate)
    };

    /** Background mortality m_i, per year, indexed by {@link Species#ordinal()}. */
    public double[] backgroundMortality = {
        0.06, // CATTLE // TODO: fit/look up (ARF provisional first estimate)
        0.05, // HORSES // TODO: fit/look up (ARF provisional first estimate)
        0.08  // DEER   // TODO: fit/look up (ARF provisional first estimate)
    };

    /**
     * Maximum extra mortality w_i in winter at zero food, per year, indexed by
     * {@link Species#ordinal()}. To be calibrated on winter 2017-18 and the NOS winter deaths.
     */
    public double[] winterStarvationMortality = {
        0.8, // CATTLE // TODO: fit/look up (ARF provisional first estimate)
        0.8, // HORSES // TODO: fit/look up (ARF provisional first estimate)
        1.2  // DEER   // TODO: fit/look up (ARF provisional first estimate)
    };

    // --- Management events (culls, relocations, introductions, die-off). ---

    /**
     * Calendar year at simulation time t = 0, used to place {@link #events} in time.
     * Default 2026 (a run "from now"); a replay of history sets it to the first year.
     */
    public double startYear = 2026.0;

    /**
     * Known events that add or remove animals, from {@code data/clean/herbivore_events.csv}.
     * Default empty: policy scenarios start from the target numbers without past events.
     * Events are immutable records, so a copied list is an independent copy.
     */
    public List<ManagementEvent> events = List.of();

    // --- Simulation horizon/step defaults. ---

    /** Simulation horizon, in years. */
    public double horizonYears = 20.0;

    /** Integration step size, in years. Default = 1 month. */
    public double dtYears = 1.0 / 12.0;

    public ModelParameters() {
    }

    private ModelParameters(ModelParameters src) {
        this.initialCattle = src.initialCattle;
        this.initialHorses = src.initialHorses;
        this.initialDeer = src.initialDeer;
        this.initialWolves = src.initialWolves;

        this.growthRate = Arrays.copyOf(src.growthRate, N);
        this.carryingCapacity = Arrays.copyOf(src.carryingCapacity, N);
        this.competitionAlpha = deepCopy(src.competitionAlpha);
        this.climateSensitivity = Arrays.copyOf(src.climateSensitivity, N);
        this.deltaT = src.deltaT;

        this.grassOptimumTemperature = src.grassOptimumTemperature;
        this.grassVar = src.grassVar;
        this.meanAnnualTemperature = src.meanAnnualTemperature;
        this.seasonalAmplitude = src.seasonalAmplitude;
        this.grassMaxGrowthKgPerHaPerMonth = src.grassMaxGrowthKgPerHaPerMonth;
        this.areaHa = src.areaHa;

        this.attackRate = Arrays.copyOf(src.attackRate, N);
        this.preyPreference = Arrays.copyOf(src.preyPreference, N);
        this.handlingTime = src.handlingTime;
        this.conversionEfficiency = Arrays.copyOf(src.conversionEfficiency, N);
        this.wolfMortality = src.wolfMortality;

        this.grazingAreaHa = src.grazingAreaHa;
        this.grassCapacityTPerHa = src.grassCapacityTPerHa;
        this.grassGrowthRate = src.grassGrowthRate;
        this.grassHalfSaturationTPerHa = src.grassHalfSaturationTPerHa;
        this.grassWinterDecay = src.grassWinterDecay;
        this.initialGrassFraction = src.initialGrassFraction;
        this.intake = Arrays.copyOf(src.intake, N);
        this.maxBirthRate = Arrays.copyOf(src.maxBirthRate, N);
        this.backgroundMortality = Arrays.copyOf(src.backgroundMortality, N);
        this.winterStarvationMortality = Arrays.copyOf(src.winterStarvationMortality, N);

        this.startYear = src.startYear;
        this.events = List.copyOf(src.events);

        this.horizonYears = src.horizonYears;
        this.dtYears = src.dtYears;
    }

    private static double[][] deepCopy(double[][] m) {
        double[][] out = new double[m.length][];
        for (int i = 0; i < m.length; i++) {
            out[i] = Arrays.copyOf(m[i], m[i].length);
        }
        return out;
    }

    /** Returns an independent deep copy of this parameter set. */
    public ModelParameters copy() {
        return new ModelParameters(this);
    }
}
