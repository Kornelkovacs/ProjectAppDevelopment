package nl.ovp.model;

import java.util.List;

/**
 * Lists every available {@link PopulationModel} so the GUI's model dropdown
 * (and the CLI's {@code --model} index) can pick them up without being
 * changed whenever a new model is added. To add a new model: implement
 * {@link PopulationModel} and add an instance to {@link #ALL}.
 */
public final class ModelRegistry {

    private static final List<PopulationModel> ALL = List.of(
        new LogisticModel(),
        new CompetitionModel(),
        new SeasonalGrazingModel(),
        new PredatorPreyModel() // most general model last: it is the GUI/CLI default
    );

    private ModelRegistry() {
    }

    /** All registered models, in a stable order (used as the CLI/GUI index). */
    public static List<PopulationModel> all() {
        return ALL;
    }

    /** Looks up a registered model by its position in {@link #all()}. */
    public static PopulationModel byIndex(int index) {
        if (index < 0 || index >= ALL.size()) {
            throw new IllegalArgumentException(
                "No model at index " + index + "; valid range is 0.." + (ALL.size() - 1));
        }
        return ALL.get(index);
    }
}
