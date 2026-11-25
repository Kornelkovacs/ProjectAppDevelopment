package nl.ovp.solver;

import java.util.ArrayList;
import java.util.List;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.PopulationModel;

/**
 * Runs a {@link PopulationModel} forward over its configured horizon
 * ({@link ModelParameters#horizonYears}) using a fixed step size
 * ({@link ModelParameters#dtYears}) and a chosen {@link OdeSolver}.
 * <p>
 * After every step, any population that went negative or became NaN
 * (numerical overshoot, or a genuine die-off) is clamped to zero: biologically,
 * a population cannot be negative, and once it reaches zero it is extinct and
 * stays at zero.
 */
public final class Simulator {

    public SimulationResult run(PopulationModel model, OdeSolver solver, ModelParameters p) {
        double dt = p.dtYears;
        int steps = (int) Math.round(p.horizonYears / dt);

        double[] y = model.initialState(p);
        clampExtinct(y);

        List<Double> times = new ArrayList<>(steps + 1);
        List<double[]> states = new ArrayList<>(steps + 1);
        double t = 0.0;
        times.add(t);
        states.add(y.clone());

        for (int i = 0; i < steps; i++) {
            y = solver.step(model, t, y, dt, p);
            clampExtinct(y);
            t += dt;
            times.add(t);
            states.add(y.clone());
        }

        return new SimulationResult(toArray(times), states.toArray(new double[0][]), model.stateNames());
    }

    private static void clampExtinct(double[] y) {
        for (int i = 0; i < y.length; i++) {
            if (Double.isNaN(y[i]) || y[i] < 0.0) {
                y[i] = 0.0;
            }
        }
    }

    private static double[] toArray(List<Double> values) {
        double[] out = new double[values.size()];
        for (int i = 0; i < out.length; i++) {
            out[i] = values.get(i);
        }
        return out;
    }
}
