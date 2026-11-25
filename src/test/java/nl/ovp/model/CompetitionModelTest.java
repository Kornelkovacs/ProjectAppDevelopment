package nl.ovp.model;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;

import org.junit.jupiter.api.Test;

import nl.ovp.solver.RungeKutta4Solver;
import nl.ovp.solver.SimulationResult;
import nl.ovp.solver.Simulator;

class CompetitionModelTest {

    private static final double[] STATE = {300.0, 400.0, 900.0};

    private static ModelParameters withEvents(ManagementEvent... events) {
        ModelParameters p = new ModelParameters();
        p.startYear = 2018.0;
        p.events = List.of(events);
        return p;
    }

    @Test
    void eventOutsideItsWindowReducesToPlainCompetitionModel() {
        ModelParameters plain = new ModelParameters();
        ModelParameters withPastEvent = withEvents(new ManagementEvent(Species.DEER, 2010.0, 2011.0, -500.0));

        double[] expected = new CompetitionModel().derivatives(0.5, STATE, plain);
        double[] actual = new CompetitionModel().derivatives(0.5, STATE, withPastEvent);

        assertArrayEquals(expected, actual, 0.0);
    }

    @Test
    void singleSpeciesEventAddsItsFlowOnlyToThatSpecies() {
        ModelParameters plain = new ModelParameters();
        ModelParameters cull = withEvents(new ManagementEvent(Species.DEER, 2018.0, 2018.5, -1200.0));

        double[] base = new CompetitionModel().derivatives(0.25, STATE, plain);
        double[] dy = new CompetitionModel().derivatives(0.25, STATE, cull);

        assertEquals(base[0], dy[0], 1e-12);
        assertEquals(base[1], dy[1], 1e-12);
        assertEquals(base[2] - 2400.0, dy[2], 1e-9); // 1200 animals over half a year
    }

    @Test
    void eventOnAllSpeciesIsSharedInProportionToNumbers() {
        ModelParameters plain = new ModelParameters();
        ModelParameters dieOff = withEvents(new ManagementEvent(null, 2018.0, 2019.0, -1600.0));

        double[] base = new CompetitionModel().derivatives(0.5, STATE, plain);
        double[] dy = new CompetitionModel().derivatives(0.5, STATE, dieOff);

        assertEquals(-1600.0 * 300 / 1600, dy[0] - base[0], 1e-9);
        assertEquals(-1600.0 * 400 / 1600, dy[1] - base[1], 1e-9);
        assertEquals(-1600.0 * 900 / 1600, dy[2] - base[2], 1e-9);
    }

    @Test
    void nothingIsRemovedFromAnExtinctSpecies() {
        ModelParameters cull = withEvents(new ManagementEvent(Species.DEER, 2018.0, 2019.0, -1000.0));

        double[] dy = new CompetitionModel().derivatives(0.5, new double[] {300.0, 400.0, 0.0}, cull);

        assertEquals(0.0, dy[2]);
    }

    @Test
    void withoutGrowthACullRemovesExactlyItsNumber() {
        // The 2018-19 deer cull: 1785 animals, December 2018 up to and including October 2019.
        ModelParameters p = withEvents(new ManagementEvent(Species.DEER, 2018 + 11 / 12.0, 2019 + 10 / 12.0, -1785.0));
        p.growthRate = new double[] {0.0, 0.0, 0.0};
        p.initialCattle = 300.0;
        p.initialHorses = 400.0;
        p.initialDeer = 2320.0;
        p.horizonYears = 3.0;

        SimulationResult result = new Simulator().run(new CompetitionModel(), new RungeKutta4Solver(), p);

        assertArrayEquals(new double[] {300.0, 400.0, 2320.0 - 1785.0}, result.finalState(), 1e-6);
    }

    @Test
    void introductionAddsAnimalsToAnAbsentSpecies() {
        ModelParameters p = withEvents(new ManagementEvent(Species.HORSES, 2018 + 11 / 12.0, 2019.0, 20.0));
        p.growthRate = new double[] {0.0, 0.0, 0.0};
        p.initialHorses = 0.0;
        p.horizonYears = 2.0;

        SimulationResult result = new Simulator().run(new CompetitionModel(), new RungeKutta4Solver(), p);

        assertEquals(20.0, result.finalState()[Species.HORSES.ordinal()], 1e-6);
    }
}
