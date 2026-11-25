package nl.ovp.model;

/**
 * A known human intervention or mass event that adds or removes animals outside
 * the natural births and deaths: an introduction, a cull, a relocation or the
 * 2017-18 die-off. Read from {@code data/clean/herbivore_events.csv} (made by
 * {@code scripts/clean_data.py} from the footnotes of the Moodle herbivore sheet
 * and the NOS winter-mortality report).
 * <p>
 * The {@code change} is spread evenly over the window, so while the event is
 * active it contributes a constant flow of {@code change / (endYear - startYear)}
 * animals per year. Times are calendar years as decimals (1 Dec 2018 = 2018 + 11/12).
 *
 * @param species   the species affected, or {@code null} for all three species
 *                  (then shared in proportion to their current numbers)
 * @param startYear start of the window, inclusive, as a decimal calendar year
 * @param endYear   end of the window, exclusive, as a decimal calendar year
 * @param change    animals added (positive) or removed (negative) over the whole window
 */
public record ManagementEvent(Species species, double startYear, double endYear, double change) {

    /**
     * Tolerance (years, ~0.03 s) when comparing with the window edges, so that
     * rounding noise in the accumulated simulation time cannot flip an edge: the
     * solver always sees the start as inside and the end as outside the window.
     */
    private static final double EDGE_TOLERANCE = 1e-9;

    public ManagementEvent {
        if (!(endYear > startYear)) {
            throw new IllegalArgumentException("Event must end after it starts: " + startYear + " .. " + endYear);
        }
    }

    /** Animals per year added (positive) or removed (negative) at calendar time {@code year}; 0 outside the window. */
    public double flowAt(double year) {
        return year >= startYear - EDGE_TOLERANCE && year < endYear - EDGE_TOLERANCE ? change / (endYear - startYear) : 0.0;
    }

    /** True if this event applies to the given species. */
    public boolean affects(Species s) {
        return species == null || species == s;
    }
}
