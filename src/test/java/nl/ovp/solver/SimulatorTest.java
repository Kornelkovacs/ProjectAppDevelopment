package nl.ovp.solver;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.PopulationModel;

class SimulatorTest {

    /** A model whose single species declines linearly, to verify extinction clamping. */
    private static final PopulationModel LINEAR_DECLINE = new PopulationModel() {
        @Override
        public String name() {
            return "linear decline";
        }

        @Override
        public String[] stateNames() {
            return new String[] {"X"};
        }

        @Override
        public double[] initialState(ModelParameters p) {
            return new double[] {1.0};
        }

        @Override
        public double[] derivatives(double t, double[] y, ModelParameters p) {
            return new double[] {-10.0};
        }
    };

    @Test
    void clampsNegativePopulationsToZero() {
        ModelParameters p = new ModelParameters();
        p.dtYears = 0.1;
        p.horizonYears = 1.0;

        SimulationResult result = new Simulator().run(LINEAR_DECLINE, new EulerSolver(), p);

        for (double[] state : result.states()) {
            assertTrue(state[0] >= 0.0, "population must never be negative");
        }
        assertEquals(0.0, result.finalState()[0]);
    }

    @Test
    void recordsOneStatePerStepPlusInitial() {
        ModelParameters p = new ModelParameters();
        p.dtYears = 0.5;
        p.horizonYears = 2.0;

        SimulationResult result = new Simulator().run(LINEAR_DECLINE, new EulerSolver(), p);

        assertEquals(5, result.times().length); // t = 0, 0.5, 1.0, 1.5, 2.0
    }
}
