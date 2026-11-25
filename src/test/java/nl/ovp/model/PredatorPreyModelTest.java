package nl.ovp.model;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

import nl.ovp.solver.RungeKutta4Solver;
import nl.ovp.solver.SimulationResult;
import nl.ovp.solver.Simulator;

class PredatorPreyModelTest {

    @Test
    void withZeroWolvesReducesToCompetitionModel() {
        ModelParameters p = new ModelParameters();
        p.initialWolves = 0.0;
        p.dtYears = 1.0 / 12.0;
        p.horizonYears = 5.0;

        SimulationResult competition = new Simulator().run(new CompetitionModel(), new RungeKutta4Solver(), p);
        SimulationResult predatorPrey = new Simulator().run(new PredatorPreyModel(), new RungeKutta4Solver(), p);

        double[] a = competition.finalState();
        double[] b = predatorPrey.finalState();
        for (int i = 0; i < a.length; i++) {
            assertEquals(a[i], b[i], 1e-6);
        }
        assertEquals(0.0, b[3]); // no wolves ever appear from nothing
    }

    @Test
    void releasingWolvesReducesPreyBelowNoWolfBaseline() {
        ModelParameters withWolves = new ModelParameters();
        withWolves.initialWolves = 20.0;
        withWolves.dtYears = 1.0 / 12.0;
        withWolves.horizonYears = 10.0;

        ModelParameters withoutWolves = withWolves.copy();
        withoutWolves.initialWolves = 0.0;

        SimulationResult withResult = new Simulator().run(new PredatorPreyModel(), new RungeKutta4Solver(), withWolves);
        SimulationResult withoutResult = new Simulator().run(new PredatorPreyModel(), new RungeKutta4Solver(), withoutWolves);

        double totalPreyWith = withResult.finalState()[0] + withResult.finalState()[1] + withResult.finalState()[2];
        double totalPreyWithout = withoutResult.finalState()[0] + withoutResult.finalState()[1] + withoutResult.finalState()[2];

        assertTrue(totalPreyWith < totalPreyWithout,
            "releasing wolves should reduce total prey compared to the no-wolf baseline");
    }
}
