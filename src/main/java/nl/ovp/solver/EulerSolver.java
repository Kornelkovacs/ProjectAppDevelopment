package nl.ovp.solver;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.PopulationModel;

/**
 * Explicit (forward) Euler integration: {@code y(t+dt) = y(t) + dt * f(t, y)}.
 * The simplest possible numerical ODE solver; kept for comparison against
 * {@link RungeKutta4Solver} in the project report, since its first-order
 * local error accumulates faster, especially near a carrying capacity or
 * when prey populations approach zero.
 */
public final class EulerSolver implements OdeSolver {

    @Override
    public String name() {
        return "Euler";
    }

    @Override
    public double[] step(PopulationModel model, double t, double[] y, double dt, ModelParameters p) {
        double[] dy = model.derivatives(t, y, p);
        double[] next = new double[y.length];
        for (int i = 0; i < y.length; i++) {
            next[i] = y[i] + dt * dy[i];
        }
        return next;
    }
}
