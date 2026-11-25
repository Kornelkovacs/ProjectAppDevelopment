package nl.ovp.model;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.Test;

import nl.ovp.solver.RungeKutta4Solver;
import nl.ovp.solver.SimulationResult;
import nl.ovp.solver.Simulator;

/**
 * Verification of {@link SeasonalGrazingModel}: properties that must hold for any parameter values
 * (adapted from the AgriculturalRiskFactors {@code GrazerModelTest}), plus the direction of the
 * area and climate effects.
 */
class SeasonalGrazingModelTest {

    private static final SeasonalGrazingModel MODEL = new SeasonalGrazingModel();
    private static final int C = Species.CATTLE.ordinal();
    private static final int H = Species.HORSES.ordinal();
    private static final int D = Species.DEER.ordinal();
    private static final int G = SeasonalGrazingModel.GRASS;

    private static ModelParameters herd(double cattle, double horses, double deer, double years) {
        ModelParameters p = new ModelParameters();
        p.initialCattle = cattle;
        p.initialHorses = horses;
        p.initialDeer = deer;
        p.dtYears = 1.0 / 12.0;
        p.horizonYears = years;
        return p;
    }

    private static SimulationResult run(ModelParameters p) {
        return new Simulator().run(MODEL, new RungeKutta4Solver(), p);
    }

    private static double totalAnimals(double[] state) {
        return state[C] + state[H] + state[D];
    }

    @Test
    void withoutAnimalsGrassIsSeasonalAndBounded() {
        ModelParameters p = herd(0, 0, 0, 10);
        double capacity = SeasonalGrazingModel.grassCapacity(p);
        SimulationResult r = run(p);

        double summerMax = 0.0;
        double winterMin = Double.MAX_VALUE;
        for (int step = 0; step < r.times().length; step++) {
            double grass = r.states()[step][G];
            assertTrue(grass >= 0.0 && grass <= capacity * (1 + 1e-9), "grass " + grass);
            if (r.times()[step] > 5) {
                summerMax = Math.max(summerMax, grass);
                winterMin = Math.min(winterMin, grass);
            }
        }
        assertTrue(summerMax > 1.3 * winterMin, "grass should grow in summer and die back in winter");
        assertTrue(summerMax > 0.5 * capacity, "summer grass should be substantial");
    }

    @Test
    void statesStayNonNegativeAndGrassBelowCapacityFromThe2017Herd() {
        ModelParameters p = herd(230, 1050, 3950, 50);
        double capacity = SeasonalGrazingModel.grassCapacity(p);
        for (double[] state : run(p).states()) {
            for (double v : state) {
                assertTrue(v >= 0.0 && Double.isFinite(v), "state " + v);
            }
            assertTrue(state[G] <= capacity * (1 + 1e-9));
        }
    }

    @Test
    void absentSpeciesStaysAbsent() {
        SimulationResult r = run(herd(0, 0, 500, 20));
        for (double[] state : r.states()) {
            assertEquals(0.0, state[C]);
            assertEquals(0.0, state[H]);
        }
    }

    @Test
    void everySpeciesDeclinesWithoutGrass() {
        ModelParameters p = new ModelParameters();
        for (double t = 0; t < 1; t += 0.05) {
            double[] dy = MODEL.derivatives(t, new double[] {100, 100, 100, 0.0}, p);
            assertTrue(dy[C] < 0 && dy[H] < 0 && dy[D] < 0, "t = " + t);
        }
    }

    @Test
    void grassEatenEqualsFeedingLevelTimesIntake() {
        ModelParameters p = new ModelParameters();
        double grass = 0.5 * SeasonalGrazingModel.grassCapacity(p);
        double[] withAnimals = MODEL.derivatives(0.3, new double[] {10, 20, 100, grass}, p);
        double[] without = MODEL.derivatives(0.3, new double[] {0, 0, 0, grass}, p);

        double expected = SeasonalGrazingModel.feeding(grass, p)
            * (10 * p.intake[C] + 20 * p.intake[H] + 100 * p.intake[D]);
        assertEquals(expected, without[G] - withAnimals[G], 1e-9);
    }

    @Test
    void derivativesDoNotModifyTheState() {
        double[] y = {300, 300, 500, 2000};
        double[] copy = y.clone();
        double[] dy = MODEL.derivatives(0.4, y, new ModelParameters());
        assertTrue(dy != y);
        assertEquals(List.of(copy[0], copy[1], copy[2], copy[3]), List.of(y[0], y[1], y[2], y[3]));
    }

    /** Limiting case against a tested model: the event flow M_i(t) is exactly that of CompetitionModel. */
    @Test
    void managementFlowIsTheSameAsInCompetitionModel() {
        ModelParameters plain = new ModelParameters();
        plain.startYear = 2018.0;
        ModelParameters withCull = plain.copy();
        withCull.events = List.of(
            new ManagementEvent(Species.DEER, 2018.0, 2019.0, -1000.0),
            new ManagementEvent(null, 2018.0, 2018.5, -600.0));

        double[] animals = {200, 600, 2300};
        double[] grazing = {200, 600, 2300, 2000};
        double t = 0.3;
        double[] seasonalFlow = difference(MODEL.derivatives(t, grazing, withCull), MODEL.derivatives(t, grazing, plain));
        double[] competitionFlow = difference(new CompetitionModel().derivatives(t, animals, withCull),
            new CompetitionModel().derivatives(t, animals, plain));

        for (int i = 0; i < animals.length; i++) {
            assertEquals(competitionFlow[i], seasonalFlow[i], 1e-9);
        }
        assertEquals(0.0, seasonalFlow[G], 1e-9); // events move animals, not grass
    }

    private static double[] difference(double[] a, double[] b) {
        double[] d = new double[a.length];
        for (int i = 0; i < a.length; i++) {
            d[i] = a[i] - b[i];
        }
        return d;
    }

    /** The key new behaviour: a herd far above what the grass supports dies back in winter without any event. */
    @Test
    void winterDieOffFollowsFromFoodShortage() {
        ModelParameters p = herd(230, 1050, 3950, 1);
        p.grazingAreaHa = 1880.0; // grazing area in 2017
        p.initialGrassFraction = 0.15;
        SimulationResult r = run(p);

        int may = 4; // t = 4/12, 1 May
        assertTrue(totalAnimals(r.states()[may]) < 0.85 * totalAnimals(r.states()[0]),
            "expected a winter die-off of more than 15 %, got " + totalAnimals(r.states()[may]));
    }

    @Test
    void moreGrasslandSustainsMoreAnimals() {
        ModelParameters today = herd(300, 300, 500, 20);
        ModelParameters before2018 = today.copy();
        before2018.grazingAreaHa = 1880.0;

        assertTrue(totalAnimals(run(before2018).finalState()) > totalAnimals(run(today).finalState()));
    }

    @Test
    void warmingFavoursHorsesAndHarmsCattleThroughBirthRates() {
        ModelParameters neutral = herd(300, 300, 500, 20);
        neutral.deltaT = 2.0;
        neutral.climateSensitivity = new double[] {0.0, 0.0, 0.0};
        ModelParameters brief = neutral.copy();
        brief.climateSensitivity = new ModelParameters().climateSensitivity; // cattle < 0, horses > 0

        double[] a = run(neutral).finalState();
        double[] b = run(brief).finalState();
        assertTrue(b[H] > a[H], "horses should gain from warming");
        assertTrue(b[C] < a[C], "cattle should lose from warming");
    }

    @Test
    void noWarmingMeansNoClimateEffectOnBirths() {
        ModelParameters p = herd(300, 300, 500, 5);
        ModelParameters noSensitivity = p.copy();
        noSensitivity.climateSensitivity = new double[] {0.0, 0.0, 0.0};

        double[] a = run(p).finalState();
        double[] b = run(noSensitivity).finalState();
        for (int i = 0; i < a.length; i++) {
            assertEquals(a[i], b[i], 0.0);
        }
    }

    @Test
    void seasonFollowsTheCalendarStartDate() {
        ModelParameters january = new ModelParameters();
        january.startYear = 2017.0;
        ModelParameters october = january.copy();
        october.startYear = 2017.75;

        double[] y = {200, 600, 2300, 2000};
        // t = 0.25 after 1 October 2017 is the same moment as t = 1.0 after 1 January 2017.
        double[] a = MODEL.derivatives(1.0, y, january);
        double[] b = MODEL.derivatives(0.25, y, october);
        for (int i = 0; i < y.length; i++) {
            assertEquals(a[i], b[i], 1e-9);
        }
    }

    /** The internal daily steps make the result independent of the output step (convergence check). */
    @Test
    void resultDoesNotDependOnTheOutputStep() {
        ModelParameters monthly = herd(300, 300, 500, 20);
        ModelParameters fine = monthly.copy();
        fine.dtYears = 1.0 / 1460.0; // 4x finer than the internal step

        double[] a = run(monthly).finalState();
        double[] b = run(fine).finalState();
        for (int i = 0; i < a.length; i++) {
            assertEquals(b[i], a[i], 1e-3 * Math.max(1.0, Math.abs(b[i])), "state " + i);
        }
    }
}
