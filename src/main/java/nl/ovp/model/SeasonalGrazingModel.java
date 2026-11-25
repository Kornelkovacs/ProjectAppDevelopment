package nl.ovp.model;

/**
 * Iteration 4: grass as a state variable that cattle, horses and deer eat, with
 * seasons and starvation in winter. Food supply is modelled explicitly instead of
 * through a carrying capacity per species, so a winter die-off can follow from a
 * shortage of grass instead of being given as an input event. Serves research
 * questions A (is 1,100 animals sustainable on today's grassland) and C (warming
 * acts on the grass through the temperature of every season).
 * <p>
 * Adapted from {@code GrazerModel} of the AgriculturalRiskFactors project
 * ({@code ovp-model} v0.1.0, Team 7). One change: grass growth and die-back follow the
 * brief's temperature-driven growth potential (Appendix 3, {@link GrassModel}) instead
 * of a fixed cosine. Births and winter mortality keep a calendar season, because
 * breeding is timed by day length, not by temperature.
 * <pre>
 * T(t)    = meanAnnualTemperature + deltaT + seasonalAmplitude cos(2 pi (t - 6.5/12))   {@link GrassModel#temperatureAt}
 * GP(t)   = exp(-0.5 ((T(t) - t0) / var)^2)                  growth potential in [0, 1]  {@link GrassModel#growthPotential}
 * s(t)    = (1 - cos 2 pi t) / 2                             calendar season, 0 on 1 January, 1 on 1 July
 * f(G)    = G / (G + G_h)                                    feeding level (Holling type II)
 * c_i     = max(0, 1 + s_i deltaT)                           climate effect on births (brief: cattle &lt; 0, horses &gt; 0)
 *
 * dG/dt   = r GP(t) G (1 - G/K) - d (1 - GP(t)) G - f(G) sum_i q_i N_i
 * dN_i/dt = N_i [ 2 b_i c_i s(t) f(G) - m_i - w_i (1 - s(t)) (1 - f(G)) ] + M_i(t)
 * </pre>
 * with {@code K = grassCapacityTPerHa * grazingAreaHa} and
 * {@code G_h = grassHalfSaturationTPerHa * grazingAreaHa}. The factor 2 makes the
 * yearly mean birth rate {@code b_i c_i f}, because the yearly mean of {@code s} is 1/2.
 * {@code M_i(t)} is the management-event flow of {@link CompetitionModel} (culls,
 * relocations, die-off), zero when there are no events.
 * <p>
 * The species interact only through the shared grass. Per animal, a deer eats
 * {@code q_deer/q_cattle ≈ 0.28} of a cow's grass and {@code q_deer/q_horses ≈ 0.30} of a
 * horse's, consistent with the brief's 30 % effect of deer on cattle and horses.
 * Known limit: with one shared food, in the long run only the species that survives on
 * the least grass persists (competitive exclusion). With the provisional parameters this
 * takes on the order of 100 years. Check it again after calibration.
 * <p>
 * Sources: Gotelli, "A Primer of Ecology", ch. 2 (logistic growth, here of the grass;
 * harvesting term {@code M_i}) and ch. 6 (Holling type II functional response, here for
 * grazers feeding on grass); Holling (1959); project brief Appendix 3 (growth potential).
 * <p>
 * State vector: [cattle, horses, deer, grass]. Grass is in tonnes of dry matter for the
 * whole grazing area. Time is in years since {@link ModelParameters#startYear}; the
 * season is read from the calendar time {@code startYear + t}, so a fractional start year
 * starts the run on that date (2017.75 = 1 October 2017). In the equations above,
 * {@code t} in {@code T}, {@code GP} and {@code s} means that calendar time.
 */
public final class SeasonalGrazingModel implements PopulationModel {

    /** Index of grass in the state vector (after the three species). */
    public static final int GRASS = Species.values().length;

    /** Series name of the grass state; the chart leaves it out (tonnes, not head counts). */
    public static final String GRASS_SERIES = "Grass (t DM)";

    /**
     * The calendar season and the temperature curve change within weeks, so the solver
     * needs steps of about a day. With a monthly step, RK4 is already about 2 % off on the
     * grass alone. {@link nl.ovp.solver.Simulator} takes as many internal steps per output
     * step as this requires.
     */
    private static final double MAX_STEP_YEARS = 1.0 / 365.0;

    @Override
    public String name() {
        return "Seasonal grazing (grass + cattle, horses, deer)";
    }

    @Override
    public String[] stateNames() {
        return new String[] {"Cattle", "Horses", "Deer", GRASS_SERIES};
    }

    @Override
    public double[] initialState(ModelParameters p) {
        return new double[] {p.initialCattle, p.initialHorses, p.initialDeer, p.initialGrassFraction * grassCapacity(p)};
    }

    @Override
    public double maxStepYears() {
        return MAX_STEP_YEARS;
    }

    /** Calendar season: 0 on 1 January, 1 on 1 July. */
    public static double season(double t) {
        return 0.5 * (1.0 - Math.cos(2.0 * Math.PI * t));
    }

    /** Grass capacity K of the whole grazing area, in tonnes dry matter. */
    public static double grassCapacity(ModelParameters p) {
        return p.grassCapacityTPerHa * p.grazingAreaHa;
    }

    /** Feeding level f(G) in [0, 1]: the fraction of maximum intake the animals achieve. */
    public static double feeding(double grass, ModelParameters p) {
        double g = Math.max(grass, 0.0);
        double halfSaturation = p.grassHalfSaturationTPerHa * p.grazingAreaHa;
        return g + halfSaturation > 0 ? g / (g + halfSaturation) : 0.0;
    }

    @Override
    public double[] derivatives(double t, double[] y, ModelParameters p) {
        int n = GRASS;
        double grass = Math.max(y[GRASS], 0.0);
        double capacity = grassCapacity(p);
        double calendarTime = p.startYear + t; // the season follows the calendar, so a run may start on any date
        double gp = GrassModel.growthPotential(GrassModel.temperatureAt(calendarTime, p, p.deltaT), p);
        double s = season(calendarTime);
        double f = feeding(grass, p);

        double[] animals = new double[n];
        double[] dAnimals = new double[n];
        double demand = 0.0;
        for (int i = 0; i < n; i++) {
            animals[i] = Math.max(y[i], 0.0);
            demand += p.intake[i] * animals[i];
            double climate = Math.max(0.0, 1.0 + p.climateSensitivity[i] * p.deltaT);
            double perCapita = 2.0 * p.maxBirthRate[i] * climate * s * f
                - p.backgroundMortality[i]
                - p.winterStarvationMortality[i] * (1.0 - s) * (1.0 - f);
            dAnimals[i] = animals[i] * perCapita;
        }
        CompetitionModel.addManagementFlows(t, animals, p, dAnimals);

        double[] dy = new double[y.length];
        System.arraycopy(dAnimals, 0, dy, 0, n);
        double growth = capacity > 0 ? p.grassGrowthRate * gp * grass * (1.0 - grass / capacity) : 0.0;
        dy[GRASS] = growth - p.grassWinterDecay * (1.0 - gp) * grass - f * demand;
        return dy;
    }
}
