package nl.ovp.solver;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.PopulationModel;

/**
 * Classic fourth-order Runge-Kutta integration (RK4). The default solver for
 * this application: fourth-order local accuracy gives a much better
 * speed/accuracy trade-off than {@link EulerSolver} at the monthly step size
 * used throughout, which matters once populations approach a carrying
 * capacity or wolves drive prey close to zero.
 */
public final class RungeKutta4Solver implements OdeSolver {

    @Override
    public String name() {
        return "Runge-Kutta 4";
    }

    @Override
    public double[] step(PopulationModel model, double t, double[] y, double dt, ModelParameters p) {
        int n = y.length;

        double[] k1 = model.derivatives(t, y, p);

        double[] y2 = new double[n];
        for (int i = 0; i < n; i++) {
            y2[i] = y[i] + 0.5 * dt * k1[i];
        }
        double[] k2 = model.derivatives(t + 0.5 * dt, y2, p);

        double[] y3 = new double[n];
        for (int i = 0; i < n; i++) {
            y3[i] = y[i] + 0.5 * dt * k2[i];
        }
        double[] k3 = model.derivatives(t + 0.5 * dt, y3, p);

        double[] y4 = new double[n];
        for (int i = 0; i < n; i++) {
            y4[i] = y[i] + dt * k3[i];
        }
        double[] k4 = model.derivatives(t + dt, y4, p);

        double[] next = new double[n];
        for (int i = 0; i < n; i++) {
            next[i] = y[i] + (dt / 6.0) * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
        }
        return next;
    }
}
