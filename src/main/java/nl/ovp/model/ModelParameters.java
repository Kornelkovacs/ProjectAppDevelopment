package nl.ovp.model;

import java.util.Arrays;

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
 * Defaults for growth rates, carrying capacities, competition coefficients,
 * climate sensitivities and predation parameters are placeholders that must be
 * fitted against the historical data in {@code data/herbivores.csv} and
 * {@code data/grass_height.csv} (see Gotelli, "A Primer of Ecology", ch. 2 for
 * logistic growth and ch. 5 for competition). Each placeholder is marked with
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

    /** Intrinsic growth rate r_i (per year), indexed by {@link Species#ordinal()}. */
    public double[] growthRate = {
        0.25, // CATTLE  // TODO: fit/look up
        0.25, // HORSES  // TODO: fit/look up
        0.30  // DEER    // TODO: fit/look up
    };

    /** Carrying capacity K_i (head count), indexed by {@link Species#ordinal()}. */
    public double[] carryingCapacity = {
        600.0,  // CATTLE // TODO: fit/look up
        600.0,  // HORSES // TODO: fit/look up
        2500.0  // DEER   // TODO: fit/look up
    };

    /**
     * Lotka-Volterra competition coefficients alpha[i][j]: effect of species j
     * on species i's carrying capacity, indexed by {@link Species#ordinal()}.
     * Diagonal entries are 1.0 by convention (a species' own density counts at
     * full weight against its own carrying capacity). The brief fixes the
     * effect of deer on cattle and horses at 30%; all other off-diagonal
     * entries are placeholders.
     */
    public double[][] competitionAlpha = {
        // CATTLE           HORSES            DEER
        {  1.0,             0.2 /* TODO: fit/look up */, 0.3 },
        {  0.2 /* TODO: fit/look up */, 1.0,              0.3 },
        {  0.1 /* TODO: fit/look up */, 0.1 /* TODO: fit/look up */, 1.0 }
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

    /** Mean annual temperature today, in degrees Celsius, used to build the monthly cosine profile. */
    public double meanAnnualTemperature = 10.0; // TODO: fit/look up

    /** Seasonal temperature amplitude (half the peak-to-trough swing), in degrees Celsius; summer peaks mid-July. */
    public double seasonalAmplitude = 8.0; // TODO: fit/look up

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

    /** Wolf mortality rate m (per year), in the absence of sufficient prey. */
    public double wolfMortality = 0.2; // TODO: fit/look up

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
