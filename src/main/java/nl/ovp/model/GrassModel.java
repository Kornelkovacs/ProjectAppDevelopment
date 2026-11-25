package nl.ovp.model;

/**
 * Grass growth-potential model, as given in Appendix 3 of the project brief
 * (derived from Taube, "Growth Characteristics of Contrasting Varieties of
 * Perennial Ryegrass", J. Agronomy &amp; Crop Science, 1990).
 * <p>
 * Growth potential on a 0..1 scale is a Gaussian in temperature, peaking at
 * the optimum temperature for C3 (cool-season) grass:
 * <pre>GP(t) = exp(-0.5 * ((t - t0) / var)^2)</pre>
 * Monthly yield is {@code GP(t) * maxGrowthKgPerHaPerMonth} (kg/ha/month);
 * multiplying by {@link ModelParameters#areaHa} gives the yield for the whole
 * Oostvaardersplassen grassland.
 * <p>
 * Monthly average temperatures are approximated as a cosine around the annual
 * mean, peaking in mid-July (day-of-year convention: t=0 is 1 January).
 * {@link #grassFactor} expresses how a temperature rise {@code deltaT}
 * changes the total annual yield relative to today's climate; this factor is
 * used by {@link CompetitionModel} to scale carrying capacities with climate
 * change (research question C).
 */
public final class GrassModel {

    /** Year-fraction at which the seasonal cosine peaks: mid-July, i.e. day ~196/365. */
    private static final double SUMMER_PEAK_YEAR_FRACTION = 6.5 / 12.0;

    private GrassModel() {
    }

    /**
     * Average temperature (degrees Celsius) at time {@code tYears} (fractional
     * years since 1 January of year 0), under a uniform warming of {@code deltaT}.
     */
    public static double temperatureAt(double tYears, ModelParameters p, double deltaT) {
        double yearFraction = tYears - Math.floor(tYears);
        double seasonal = p.seasonalAmplitude * Math.cos(2 * Math.PI * (yearFraction - SUMMER_PEAK_YEAR_FRACTION));
        return p.meanAnnualTemperature + deltaT + seasonal;
    }

    /** Growth potential GP in [0, 1] at the given temperature. */
    public static double growthPotential(double temperatureC, ModelParameters p) {
        double z = (temperatureC - p.grassOptimumTemperature) / p.grassVar;
        return Math.exp(-0.5 * z * z);
    }

    /** Grass yield for the whole reserve at time {@code tYears}, in kg/month. */
    public static double monthlyYieldKg(double tYears, ModelParameters p, double deltaT) {
        double temperature = temperatureAt(tYears, p, deltaT);
        double gp = growthPotential(temperature, p);
        return gp * p.grassMaxGrowthKgPerHaPerMonth * p.areaHa;
    }

    /** Total yield over one year (12 monthly samples starting at t=0), in kg. */
    public static double annualYieldKg(ModelParameters p, double deltaT) {
        double total = 0.0;
        for (int month = 0; month < 12; month++) {
            total += monthlyYieldKg(month / 12.0, p, deltaT);
        }
        return total;
    }

    /**
     * Ratio of annual grass yield at warming {@code deltaT} to annual yield
     * today ({@code deltaT = 0}). Used to scale carrying capacities: a value
     * below 1 means less food is available than today, above 1 means more.
     */
    public static double grassFactor(ModelParameters p, double deltaT) {
        double todayYield = annualYieldKg(p, 0.0);
        if (todayYield <= 0.0) {
            return 1.0;
        }
        return annualYieldKg(p, deltaT) / todayYield;
    }
}
