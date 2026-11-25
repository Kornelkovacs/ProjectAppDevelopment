package nl.ovp.ui;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.awt.GridLayout;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.List;

import javax.swing.BorderFactory;
import javax.swing.JFileChooser;
import javax.swing.JFrame;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JSplitPane;

import nl.ovp.data.CsvDataLoader;
import nl.ovp.data.HerbivoreCount;
import nl.ovp.model.ModelParameters;
import nl.ovp.model.PopulationModel;
import nl.ovp.solver.OdeSolver;
import nl.ovp.solver.SimulationResult;

/**
 * Main application window: a parameter panel on the left, the chart on the
 * right. Wires {@link ParameterPanel} input to {@link SimulationWorker}
 * (run off the EDT) and {@link ChartPanel} output, and handles CSV export
 * and the observed-data overlay.
 */
public final class MainWindow extends JFrame {

    /** Minimum width (px) of the parameter panel on the left. */
    private static final int MIN_PARAM_WIDTH = 460;

    private final ParameterPanel parameterPanel = new ParameterPanel();
    private final ChartPanel chartPanel = new ChartPanel();

    private SimulationResult lastResult;
    private List<HerbivoreCount> observedCache;

    public MainWindow() {
        super("Oostvaardersplassen Population Model");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        JScrollPane paramScroll = new JScrollPane(parameterPanel,
            JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED, JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
        paramScroll.getVerticalScrollBar().setUnitIncrement(16);

        // Size the left side to whatever the controls actually need (long model
        // names, labels), plus room for the vertical scrollbar, with a floor so
        // it never gets cramped. The divider can be dragged to resize further.
        int scrollbarWidth = paramScroll.getVerticalScrollBar().getPreferredSize().width;
        int paramWidth = Math.max(MIN_PARAM_WIDTH,
            parameterPanel.getPreferredSize().width + scrollbarWidth + 8);
        paramScroll.setPreferredSize(new Dimension(paramWidth, 600));
        paramScroll.setMinimumSize(new Dimension(MIN_PARAM_WIDTH, 200));

        // Action buttons sit below the scroll area so they are always visible,
        // however far the parameter list is scrolled.
        JPanel buttonBar = new JPanel(new GridLayout(1, 3, 6, 0));
        buttonBar.setBorder(BorderFactory.createEmptyBorder(8, 10, 8, 10));
        buttonBar.add(parameterPanel.runButton);
        buttonBar.add(parameterPanel.policyTargetButton);
        buttonBar.add(parameterPanel.exportCsvButton);
        getRootPane().setDefaultButton(parameterPanel.runButton);

        JPanel leftSide = new JPanel(new BorderLayout());
        leftSide.add(paramScroll, BorderLayout.CENTER);
        leftSide.add(buttonBar, BorderLayout.SOUTH);
        leftSide.setMinimumSize(new Dimension(MIN_PARAM_WIDTH, 200));

        JSplitPane split = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, leftSide, chartPanel);
        split.setResizeWeight(0.0); // extra window width goes to the chart
        split.setContinuousLayout(true);
        add(split, BorderLayout.CENTER);

        setPreferredSize(new Dimension(paramWidth + 850, 720));
        pack();
        setLocationRelativeTo(null);

        parameterPanel.runButton.addActionListener(e -> runSimulation());
        parameterPanel.exportCsvButton.addActionListener(e -> exportCsv());
        parameterPanel.showObservedCheckBox.addActionListener(e -> updateObservedOverlay());
        parameterPanel.startYearSpinner.addChangeListener(e -> updateObservedOverlay());
    }

    private void runSimulation() {
        PopulationModel model = parameterPanel.getSelectedModel();
        OdeSolver solver = parameterPanel.getSelectedSolver();
        ModelParameters params = parameterPanel.buildParameters();
        String title = String.format("%s — %s (wolves=%d, ΔT=%.1f°C)",
            model.name(), solver.name(), (int) params.initialWolves, params.deltaT);

        parameterPanel.runButton.setEnabled(false);
        new SimulationWorker(model, solver, params,
            result -> {
                lastResult = result;
                chartPanel.setResult(result, title);
                parameterPanel.exportCsvButton.setEnabled(true);
                updateObservedOverlay();
                parameterPanel.runButton.setEnabled(true);
            },
            error -> {
                parameterPanel.runButton.setEnabled(true);
                showError("Simulation failed", error);
            }
        ).execute();
    }

    private void updateObservedOverlay() {
        if (!parameterPanel.isShowObserved()) {
            chartPanel.clearObservedOverlay();
            return;
        }
        try {
            if (observedCache == null) {
                observedCache = new CsvDataLoader().loadHerbivores();
            }
            chartPanel.setObservedOverlay(observedCache, parameterPanel.getStartYear());
        } catch (RuntimeException e) {
            parameterPanel.showObservedCheckBox.setSelected(false);
            showError("Could not load observed data (data/clean/herbivores_counts.csv)", e);
        }
    }

    private void exportCsv() {
        if (lastResult == null) {
            return;
        }
        JFileChooser chooser = new JFileChooser();
        chooser.setSelectedFile(new File("simulation.csv"));
        int choice = chooser.showSaveDialog(this);
        if (choice != JFileChooser.APPROVE_OPTION) {
            return;
        }
        try {
            Files.writeString(chooser.getSelectedFile().toPath(), lastResult.toCsv());
        } catch (IOException e) {
            showError("Could not export CSV", e);
        }
    }

    private void showError(String title, Exception e) {
        String message = e.getMessage() != null ? e.getMessage() : e.toString();
        JOptionPane.showMessageDialog(this, message, title, JOptionPane.ERROR_MESSAGE);
    }
}
