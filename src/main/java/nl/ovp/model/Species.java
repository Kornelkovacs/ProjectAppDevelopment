package nl.ovp.model;

/**
 * The three large herbivore species modelled in the Oostvaardersplassen.
 * <p>
 * Ordinal order ({@code CATTLE}=0, {@code HORSES}=1, {@code DEER}=2) defines
 * how per-species arrays in {@link ModelParameters} are indexed, and matches
 * the state-vector order used by every {@link PopulationModel}: cattle,
 * horses, deer (optionally followed by a scalar wolf state).
 */
public enum Species {
    CATTLE,
    HORSES,
    DEER
}
