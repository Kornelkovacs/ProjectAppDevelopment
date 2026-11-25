package nl.ovp.data;

/**
 * One row of observed herbivore counts on 1 January of {@code year}, as
 * published in "Number of large herbivores in the Oostvaardersplassen
 * 1983-2025". Counts are nullable: deer were only counted from 1992
 * onward, and some cells in the source are blank or flagged as unreliable
 * (see {@code data/README.md} for the full list of corrections applied by
 * {@code scripts/export_data.py}).
 */
public record HerbivoreCount(int year, Double cattle, Double horses, Double deer) {
}
