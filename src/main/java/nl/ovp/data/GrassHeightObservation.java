package nl.ovp.data;

/**
 * One row of measured grass height (cm) on 1 August of {@code year}, from
 * "Measured height of grass Oostvaarderplassen 1990-2014".
 */
public record GrassHeightObservation(int year, Double heightCm) {
}
