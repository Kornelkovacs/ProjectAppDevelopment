package nl.ovp.solver;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

import nl.ovp.model.LogisticModel;
import nl.ovp.model.ModelParameters;

/**
 * Validates RK4 against the closed-form logistic solution
 * N(t) = K / (1 + ((K - N0) / N0) * e^(-r t)), confirming the solver and
 * {@link LogisticModel} agree with the analytic result from Gotelli ch. 2.
 */
class RungeKutta4SolverTest {

    @Test
    void matchesAnalyticLogisticSolution() {
        ModelParameters p = new ModelParameters();
        p.growthRate[0] = 0.3;
        p.carryingCapacity[0] = 1000.0;
        p.initialCattle = 100.0;
        p.dtYears = 1.0 / 12.0;
        p.horizonYears = 10.0;

        LogisticModel model = new LogisticModel();
        RungeKutta4Solver solver = new RungeKutta4Solver();
        Simulator simulator = new Simulator();

        SimulationResult result = simulator.run(model, solver, p);

        double r = p.growthRate[0];
        double k = p.carryingCapacity[0];
        double n0 = p.initialCattle;
        double analytic = k / (1 + ((k - n0) / n0) * Math.exp(-r * p.horizonYears));

        assertEquals(analytic, result.finalState()[0], 0.5);
    }
}
