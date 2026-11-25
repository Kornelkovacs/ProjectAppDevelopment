package nl.ovp.data;

/**
 * One month of KNMI weather data, from {@code data/clean/climate_monthly.csv}
 * (Lelystad, station 269, ~10 km from the reserve; De Bilt, station 260, before
 * Lelystad records start, with De Bilt temperatures shifted to the Lelystad level).
 *
 * @param year      calendar year
 * @param month     1 = January .. 12 = December
 * @param meanTempC monthly mean of the daily mean temperature, in degrees Celsius
 * @param rainMm    monthly precipitation sum, in mm
 * @param evapMm    monthly Makkink reference evapotranspiration sum, in mm
 */
public record ClimateObservation(int year, int month, double meanTempC, double rainMm, double evapMm) {

    /** Time in fractional years with each month placed at its midpoint, e.g. July 1990 = 1990.54. */
    public double midMonthYear() {
        return year + (month - 0.5) / 12.0;
    }

    /** Climatic water balance (rain minus reference evaporation), in mm; negative means a deficit. */
    public double waterBalanceMm() {
        return rainMm - evapMm;
    }
}
