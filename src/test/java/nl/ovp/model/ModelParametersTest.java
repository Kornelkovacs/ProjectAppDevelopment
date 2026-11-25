package nl.ovp.model;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotSame;

import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

class ModelParametersTest {

    @Test
    void copyIsIndependentOfOriginal() {
        ModelParameters original = new ModelParameters();
        ModelParameters copy = original.copy();

        copy.growthRate[Species.CATTLE.ordinal()] = 99.0;
        copy.competitionAlpha[0][1] = 42.0;
        copy.initialDeer = 12345.0;

        assertNotSame(original.growthRate, copy.growthRate);
        assertNotSame(original.competitionAlpha, copy.competitionAlpha);

        assertEquals(new ModelParameters().growthRate[Species.CATTLE.ordinal()], original.growthRate[Species.CATTLE.ordinal()]);
        assertEquals(500.0, original.initialDeer);
    }

    @Test
    void copiedEventListIsIndependentOfOriginal() {
        ModelParameters original = new ModelParameters();
        List<ManagementEvent> mutable = new ArrayList<>();
        mutable.add(new ManagementEvent(Species.DEER, 2018.0, 2019.0, -100.0));
        original.events = mutable;

        ModelParameters copy = original.copy();
        mutable.add(new ManagementEvent(Species.HORSES, 2018.0, 2019.0, -50.0));
        original.startYear = 1990.0;

        assertEquals(1, copy.events.size());
        assertEquals(2026.0, copy.startYear);
    }

    @Test
    void defaultsHaveNoEvents() {
        assertEquals(List.of(), new ModelParameters().events);
    }

    @Test
    void defaultInitialPopulationsMatchPolicyTarget() {
        ModelParameters p = new ModelParameters();
        assertEquals(300.0, p.initialCattle);
        assertEquals(300.0, p.initialHorses);
        assertEquals(500.0, p.initialDeer);
        assertEquals(0.0, p.initialWolves);
    }
}
