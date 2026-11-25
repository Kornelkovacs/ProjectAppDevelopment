package nl.ovp.model;

/**
 * Common contract for a population-dynamics model of the Oostvaardersplassen
 * herbivores (and, where applicable, their predators).
 * <p>
 * A model defines a state vector (one entry per {@linkplain #stateNames()
 * named series}, in a fixed order) and a system of ordinary differential
 * equations {@code dy/dt = derivatives(t, y, p)} that an {@link nl.ovp.solver.OdeSolver}
 * integrates forward in time. Implementations are stateless: all tunable
 * numbers live in {@link ModelParameters}, so the same model instance can be
 * reused across simulation runs with different parameters.
 * <p>
 * New models are picked up automatically by the GUI once registered in
 * {@link ModelRegistry}.
 */
public interface PopulationModel {

    /** Short, human-readable name shown in the GUI's model dropdown. */
    String name();

    /** Names of the state-vector entries, in the same order as {@link #initialState} and {@link #derivatives}. */
    String[] stateNames();

    /** Builds the initial state vector {@code y(0)} from the given parameters. */
    double[] initialState(ModelParameters p);

    /**
     * Evaluates the derivative {@code dy/dt} at time {@code t} (in years) for
     * state {@code y}, under parameters {@code p}.
     *
     * @return a new array, same length as {@code y}, that must not alias {@code y}
     */
    double[] derivatives(double t, double[] y, ModelParameters p);

    /**
     * Largest step (years) the solver may take for this model. If
     * {@link ModelParameters#dtYears} is larger, {@link nl.ovp.solver.Simulator} splits each
     * output step into equal internal steps no larger than this. The output stays at
     * {@code dtYears}. Default: no limit, so one solver step per output step.
     */
    default double maxStepYears() {
        return Double.POSITIVE_INFINITY;
    }
}
