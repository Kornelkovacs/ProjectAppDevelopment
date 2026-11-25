package nl.ovp.solver;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.PopulationModel;

/**
 * A numerical method for advancing a {@link PopulationModel}'s state vector
 * by one time step. Implementations must be stateless so a single instance
 * can be reused across simulation runs.
 */
public interface OdeSolver {

    /** Short, human-readable name shown in the GUI's solver dropdown. */
    String name();

    /**
     * Advances the state from {@code y} at time {@code t} to time
     * {@code t + dt}, using {@code model}'s derivatives under parameters
     * {@code p}.
     *
     * @return a new array, same length as {@code y}
     */
    double[] step(PopulationModel model, double t, double[] y, double dt, ModelParameters p);
}
