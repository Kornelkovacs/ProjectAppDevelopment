package nl.ovp.model;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotSame;

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

        assertEquals(0.25, original.growthRate[Species.CATTLE.ordinal()]);
        assertEquals(500.0, original.initialDeer);
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
