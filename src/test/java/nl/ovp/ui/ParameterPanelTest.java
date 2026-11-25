package nl.ovp.ui;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import org.junit.jupiter.api.Test;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.Species;

class ParameterPanelTest {

    private static final int C = Species.CATTLE.ordinal();
    private static final int H = Species.HORSES.ordinal();
    private static final int D = Species.DEER.ordinal();

    @Test
    void slidersStartAtModelDefaults() {
        ParameterPanel panel = new ParameterPanel();
        ModelParameters built = panel.buildParameters();
        ModelParameters defaults = new ModelParameters();
        for (int i = 0; i < 3; i++) {
            assertEquals(defaults.carryingCapacity[i], built.carryingCapacity[i], 1e-9);
            for (int j = 0; j < 3; j++) {
                assertEquals(defaults.competitionAlpha[i][j], built.competitionAlpha[i][j], 1e-9);
            }
        }
    }

    @Test
    void sliderValuesReachModelParameters() {
        ParameterPanel panel = new ParameterPanel();
        panel.carryingCapacitySliders[C].setValue(1200);
        panel.competitionSliders[C][D].setValue(0.15); // effect of deer on cattle

        ModelParameters p = panel.buildParameters();
        assertEquals(1200, p.carryingCapacity[C], 1e-9);
        assertEquals(0.15, p.competitionAlpha[C][D], 1e-9);
        assertEquals(0.3, p.competitionAlpha[H][D], 1e-9); // untouched entry keeps its default
        assertEquals(1.0, p.competitionAlpha[D][D], 1e-9); // diagonal stays fixed at 1
        assertNull(panel.competitionSliders[D][D]);
    }

    @Test
    void resetRestoresDefaults() {
        ParameterPanel panel = new ParameterPanel();
        panel.carryingCapacitySliders[D].setValue(100);
        panel.competitionSliders[H][C].setValue(1.5);
        panel.resetCompetitionToDefaults();

        ModelParameters p = panel.buildParameters();
        assertEquals(2500, p.carryingCapacity[D], 1e-9);
        assertEquals(0.2, p.competitionAlpha[H][C], 1e-9);
    }
}
