package nl.ovp.ui;

import java.awt.Component;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;

import javax.swing.BorderFactory;
import javax.swing.DefaultListCellRenderer;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JLabel;
import javax.swing.JList;
import javax.swing.JPanel;
import javax.swing.JSeparator;
import javax.swing.JSpinner;
import javax.swing.SpinnerNumberModel;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.ModelRegistry;
import nl.ovp.model.PopulationModel;
import nl.ovp.model.Species;
import nl.ovp.solver.EulerSolver;
import nl.ovp.solver.OdeSolver;
import nl.ovp.solver.RungeKutta4Solver;

/**
 * Left-hand input panel: model/solver choice, horizon, initial populations,
 * wolves released, per-species wolf prey preference, temperature rise, the
 * carrying capacities and competition coefficients (sliders), the
 * observed-data overlay controls. The action buttons are created here but
 * laid out by {@link MainWindow}, below the scrollable area. Values are
 * read by {@link MainWindow} to build a {@link ModelParameters} for each run.
 */
final class ParameterPanel extends JPanel {

    private static final double POLICY_CATTLE = 300.0;
    private static final double POLICY_HORSES = 300.0;
    private static final double POLICY_DEER = 500.0;

    final JComboBox<PopulationModel> modelCombo;
    final JComboBox<OdeSolver> solverCombo;
    final JSpinner yearsSpinner;
    final JSpinner cattleSpinner;
    final JSpinner horsesSpinner;
    final JSpinner deerSpinner;
    final JSpinner wolvesSpinner;
    final JSpinner preyPrefCattleSpinner;
    final JSpinner preyPrefHorsesSpinner;
    final JSpinner preyPrefDeerSpinner;
    final JSpinner deltaTSpinner;
    final JCheckBox showObservedCheckBox;
    final JSpinner startYearSpinner;
    final JButton runButton;
    final JButton policyTargetButton;
    final JButton exportCsvButton;

    /** Carrying capacity K per species, indexed by {@link Species#ordinal()}. */
    final ValueSlider[] carryingCapacitySliders = new ValueSlider[Species.values().length];
    /**
     * Competition coefficients alpha[i][j] (effect of species j on species i),
     * indexed by {@link Species#ordinal()}. Diagonal entries are null: alpha_ii
     * is fixed at 1 by definition and has no slider.
     */
    final ValueSlider[][] competitionSliders = new ValueSlider[Species.values().length][Species.values().length];
    final JButton resetCompetitionButton;

    private static final double K_MIN = 0.0;
    private static final double K_MAX = 10000.0;
    private static final double K_STEP = 10.0;
    private static final double ALPHA_MIN = 0.0;
    private static final double ALPHA_MAX = 2.0;
    private static final double ALPHA_STEP = 0.01;

    ParameterPanel() {
        setLayout(new GridBagLayout());
        setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        modelCombo = new JComboBox<>(ModelRegistry.all().toArray(new PopulationModel[0]));
        modelCombo.setRenderer(nameRenderer(PopulationModel::name));
        modelCombo.setSelectedIndex(ModelRegistry.all().size() - 1); // most general model by default

        solverCombo = new JComboBox<>(new OdeSolver[] {new RungeKutta4Solver(), new EulerSolver()});
        solverCombo.setRenderer(nameRenderer(OdeSolver::name));

        yearsSpinner = new JSpinner(new SpinnerNumberModel(20.0, 1.0, 200.0, 1.0));
        cattleSpinner = new JSpinner(new SpinnerNumberModel(POLICY_CATTLE, 0.0, 100_000.0, 10.0));
        horsesSpinner = new JSpinner(new SpinnerNumberModel(POLICY_HORSES, 0.0, 100_000.0, 10.0));
        deerSpinner = new JSpinner(new SpinnerNumberModel(POLICY_DEER, 0.0, 100_000.0, 10.0));
        wolvesSpinner = new JSpinner(new SpinnerNumberModel(0.0, 0.0, 500.0, 1.0));
        preyPrefCattleSpinner = new JSpinner(new SpinnerNumberModel(1.0, 0.0, 1.0, 0.05));
        preyPrefHorsesSpinner = new JSpinner(new SpinnerNumberModel(1.0, 0.0, 1.0, 0.05));
        preyPrefDeerSpinner = new JSpinner(new SpinnerNumberModel(1.0, 0.0, 1.0, 0.05));
        deltaTSpinner = new JSpinner(new SpinnerNumberModel(0.0, -2.0, 6.0, 0.5));
        showObservedCheckBox = new JCheckBox("Show observed counts");
        startYearSpinner = new JSpinner(new SpinnerNumberModel(1983, 1900, 2100, 1));
        startYearSpinner.setEditor(new JSpinner.NumberEditor(startYearSpinner, "#")); // show 1983, not 1,983
        startYearSpinner.setEnabled(false);
        showObservedCheckBox.addActionListener(e -> startYearSpinner.setEnabled(showObservedCheckBox.isSelected()));

        runButton = new JButton("Run simulation");
        policyTargetButton = new JButton("Policy target (1,100)");
        exportCsvButton = new JButton("Export CSV…");
        exportCsvButton.setEnabled(false);

        policyTargetButton.addActionListener(e -> resetToPolicyTarget());

        ModelParameters defaults = new ModelParameters();
        for (Species s : Species.values()) {
            int i = s.ordinal();
            carryingCapacitySliders[i] = new ValueSlider(K_MIN, K_MAX, K_STEP, defaults.carryingCapacity[i], "%.0f");
            carryingCapacitySliders[i].setToolTipText("Maximum number of " + plural(s)
                + " the grass can sustain in today's climate (K)");
            for (Species other : Species.values()) {
                int j = other.ordinal();
                if (i == j) {
                    continue;
                }
                competitionSliders[i][j] = new ValueSlider(ALPHA_MIN, ALPHA_MAX, ALPHA_STEP,
                    defaults.competitionAlpha[i][j], "%.2f");
                competitionSliders[i][j].setToolTipText("<html>How much food one " + singular(other)
                    + " takes from " + plural(s) + ",<br>counted in " + plural(s) + " (α)</html>");
            }
        }
        resetCompetitionButton = new JButton("Reset K and α to defaults");
        resetCompetitionButton.addActionListener(e -> resetCompetitionToDefaults());

        int row = 0;
        row = addRow(row, "Model", modelCombo);
        row = addRow(row, "Solver", solverCombo);
        row = addRow(row, "Years", yearsSpinner);
        row = addRow(row, "Initial cattle", cattleSpinner);
        row = addRow(row, "Initial horses", horsesSpinner);
        row = addRow(row, "Initial deer", deerSpinner);
        row = addRow(row, "Wolves released", wolvesSpinner);
        row = addRow(row, "Prey preference – cattle", preyPrefCattleSpinner);
        row = addRow(row, "Prey preference – horses", preyPrefHorsesSpinner);
        row = addRow(row, "Prey preference – deer", preyPrefDeerSpinner);
        row = addRow(row, "Temperature rise (°C)", deltaTSpinner);

        row = addSection(row, "Carrying capacity K (animals)");
        for (Species s : Species.values()) {
            row = addRow(row, "K – " + plural(s), carryingCapacitySliders[s.ordinal()]);
        }
        row = addSection(row, "Competition α (effect of one animal of → on ↓)");
        for (Species s : Species.values()) {
            for (Species other : Species.values()) {
                if (s != other) {
                    row = addRow(row, capitalize(plural(other)) + " → " + plural(s),
                        competitionSliders[s.ordinal()][other.ordinal()]);
                }
            }
        }
        row = addRow(row, "", resetCompetitionButton);
        row = addSeparator(row);
        row = addRow(row, "", showObservedCheckBox);
        addRow(row, "Overlay start year", startYearSpinner);
        // runButton, policyTargetButton and exportCsvButton are not added here:
        // MainWindow pins them below the scrollable panel so they stay visible.
    }

    private int addRow(int row, String label, Component field) {
        GridBagConstraints labelConstraints = new GridBagConstraints();
        labelConstraints.gridx = 0;
        labelConstraints.gridy = row;
        labelConstraints.anchor = GridBagConstraints.WEST;
        labelConstraints.insets = new Insets(4, 0, 4, 8);
        add(new JLabel(label), labelConstraints);

        GridBagConstraints fieldConstraints = new GridBagConstraints();
        fieldConstraints.gridx = 1;
        fieldConstraints.gridy = row;
        fieldConstraints.fill = GridBagConstraints.HORIZONTAL;
        fieldConstraints.weightx = 1.0;
        fieldConstraints.insets = new Insets(4, 0, 4, 0);
        add(field, fieldConstraints);

        return row + 1;
    }

    /** Adds a bold heading spanning both columns, preceded by a separator line. */
    private int addSection(int row, String title) {
        row = addSeparator(row);
        JLabel heading = new JLabel(title);
        heading.setFont(heading.getFont().deriveFont(Font.BOLD));
        GridBagConstraints c = new GridBagConstraints();
        c.gridx = 0;
        c.gridy = row;
        c.gridwidth = 2;
        c.anchor = GridBagConstraints.WEST;
        c.insets = new Insets(2, 0, 2, 0);
        add(heading, c);
        return row + 1;
    }

    private int addSeparator(int row) {
        GridBagConstraints c = new GridBagConstraints();
        c.gridx = 0;
        c.gridy = row;
        c.gridwidth = 2;
        c.fill = GridBagConstraints.HORIZONTAL;
        c.insets = new Insets(8, 0, 4, 0);
        add(new JSeparator(), c);
        return row + 1;
    }

    private static String plural(Species s) {
        return s == Species.DEER ? "deer" : s.name().toLowerCase();
    }

    private static String singular(Species s) {
        switch (s) {
            case CATTLE: return "cow";
            case HORSES: return "horse";
            default: return "deer";
        }
    }

    private static String capitalize(String text) {
        return Character.toUpperCase(text.charAt(0)) + text.substring(1);
    }

    private static <T> DefaultListCellRenderer nameRenderer(java.util.function.Function<T, String> namer) {
        return new DefaultListCellRenderer() {
            @Override
            @SuppressWarnings("unchecked")
            public Component getListCellRendererComponent(JList<?> list, Object value, int index,
                                                            boolean isSelected, boolean cellHasFocus) {
                String text = value == null ? "" : namer.apply((T) value);
                return super.getListCellRendererComponent(list, text, index, isSelected, cellHasFocus);
            }
        };
    }

    void resetToPolicyTarget() {
        cattleSpinner.setValue(POLICY_CATTLE);
        horsesSpinner.setValue(POLICY_HORSES);
        deerSpinner.setValue(POLICY_DEER);
    }

    /** Puts every K and α slider back to the value in {@link ModelParameters}. */
    void resetCompetitionToDefaults() {
        ModelParameters defaults = new ModelParameters();
        for (int i = 0; i < carryingCapacitySliders.length; i++) {
            carryingCapacitySliders[i].setValue(defaults.carryingCapacity[i]);
            for (int j = 0; j < carryingCapacitySliders.length; j++) {
                if (competitionSliders[i][j] != null) {
                    competitionSliders[i][j].setValue(defaults.competitionAlpha[i][j]);
                }
            }
        }
    }

    PopulationModel getSelectedModel() {
        return (PopulationModel) modelCombo.getSelectedItem();
    }

    OdeSolver getSelectedSolver() {
        return (OdeSolver) solverCombo.getSelectedItem();
    }

    boolean isShowObserved() {
        return showObservedCheckBox.isSelected();
    }

    int getStartYear() {
        return (Integer) startYearSpinner.getValue();
    }

    /** Builds a fresh {@link ModelParameters} with defaults overridden by the current UI values. */
    ModelParameters buildParameters() {
        ModelParameters p = new ModelParameters();
        p.horizonYears = asDouble(yearsSpinner);
        p.initialCattle = asDouble(cattleSpinner);
        p.initialHorses = asDouble(horsesSpinner);
        p.initialDeer = asDouble(deerSpinner);
        p.initialWolves = asDouble(wolvesSpinner);
        p.preyPreference[Species.CATTLE.ordinal()] = asDouble(preyPrefCattleSpinner);
        p.preyPreference[Species.HORSES.ordinal()] = asDouble(preyPrefHorsesSpinner);
        p.preyPreference[Species.DEER.ordinal()] = asDouble(preyPrefDeerSpinner);
        p.deltaT = asDouble(deltaTSpinner);
        for (int i = 0; i < carryingCapacitySliders.length; i++) {
            p.carryingCapacity[i] = carryingCapacitySliders[i].getValue();
            for (int j = 0; j < carryingCapacitySliders.length; j++) {
                if (competitionSliders[i][j] != null) {
                    p.competitionAlpha[i][j] = competitionSliders[i][j].getValue();
                }
            }
        }
        return p;
    }

    private static double asDouble(JSpinner spinner) {
        return ((Number) spinner.getValue()).doubleValue();
    }
}
