package nl.ovp.solver;

/**
 * Output of a single {@link Simulator} run: a time series of state vectors,
 * together with the series names from {@link nl.ovp.model.PopulationModel#stateNames()}.
 */
public final class SimulationResult {

    private final double[] times;
    private final double[][] states; // states[step][seriesIndex]
    private final String[] seriesNames;

    public SimulationResult(double[] times, double[][] states, String[] seriesNames) {
        this.times = times;
        this.states = states;
        this.seriesNames = seriesNames;
    }

    public double[] times() {
        return times;
    }

    /** Raw state matrix: {@code states()[step][seriesIndex]}. */
    public double[][] states() {
        return states;
    }

    public String[] seriesNames() {
        return seriesNames;
    }

    /** The state vector at the last recorded time step. */
    public double[] finalState() {
        return states[states.length - 1].clone();
    }

    /** The maximum value reached by one series (by index) over the whole run. */
    public double maxValue(int seriesIndex) {
        double max = Double.NEGATIVE_INFINITY;
        for (double[] state : states) {
            max = Math.max(max, state[seriesIndex]);
        }
        return max;
    }

    /** Renders this result as CSV: a header row ("t", series names...) then one row per time step. */
    public String toCsv() {
        StringBuilder sb = new StringBuilder();
        sb.append("t");
        for (String name : seriesNames) {
            sb.append(',').append(name);
        }
        sb.append('\n');
        for (int step = 0; step < times.length; step++) {
            sb.append(times[step]);
            for (double value : states[step]) {
                sb.append(',').append(value);
            }
            sb.append('\n');
        }
        return sb.toString();
    }
}
