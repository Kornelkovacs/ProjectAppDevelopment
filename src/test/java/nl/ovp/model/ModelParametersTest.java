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
    void seasonalGrazingArraysAreCopiedIndependently() {
        ModelParameters original = new ModelParameters();
        ModelParameters copy = original.copy();
        int d = Species.DEER.ordinal();

        copy.intake[d] = 99.0;
        copy.maxBirthRate[d] = 99.0;
        copy.backgroundMortality[d] = 99.0;
        copy.winterStarvationMortality[d] = 99.0;
        copy.grazingAreaHa = 1.0;

        ModelParameters defaults = new ModelParameters();
        assertEquals(defaults.intake[d], original.intake[d]);
        assertEquals(defaults.maxBirthRate[d], original.maxBirthRate[d]);
        assertEquals(defaults.backgroundMortality[d], original.backgroundMortality[d]);
        assertEquals(defaults.winterStarvationMortality[d], original.winterStarvationMortality[d]);
        assertEquals(1080.0, original.grazingAreaHa);
    }

    @Test
    void copyKeepsSeasonalGrazingScalars() {
        ModelParameters original = new ModelParameters();
        original.grassCapacityTPerHa = 5.0;
        original.grassGrowthRate = 10.0;
        original.grassHalfSaturationTPerHa = 0.7;
        original.grassWinterDecay = 2.0;
        original.initialGrassFraction = 0.5;

        ModelParameters copy = original.copy();
        assertEquals(5.0, copy.grassCapacityTPerHa);
        assertEquals(10.0, copy.grassGrowthRate);
        assertEquals(0.7, copy.grassHalfSaturationTPerHa);
        assertEquals(2.0, copy.grassWinterDecay);
        assertEquals(0.5, copy.initialGrassFraction);
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
