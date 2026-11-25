package nl.ovp.app;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

import nl.ovp.model.ModelParameters;

class MainTest {

    @Test
    void replayStartsFromObservedCountsAndLoadsEvents() {
        ModelParameters p = new ModelParameters();

        Main.applyReplay(p, 2018);

        assertEquals(2018.0, p.startYear);
        assertEquals(200.0, p.initialCattle);
        assertEquals(610.0, p.initialHorses);
        assertEquals(2320.0, p.initialDeer);
        assertEquals(6, p.events.size());
    }

    @Test
    void replayBeforeIntroductionStartsAbsentSpeciesAtZero() {
        ModelParameters p = new ModelParameters();

        Main.applyReplay(p, 1983);

        assertEquals(30.0, p.initialCattle);
        assertEquals(0.0, p.initialHorses);
        assertEquals(0.0, p.initialDeer);
    }
}
