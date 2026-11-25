package nl.ovp.app;

import javax.swing.SwingUtilities;

import nl.ovp.data.CsvDataLoader;
import nl.ovp.data.HerbivoreCount;
import nl.ovp.model.ModelParameters;
import nl.ovp.model.ModelRegistry;
import nl.ovp.model.PopulationModel;
import nl.ovp.solver.RungeKutta4Solver;
import nl.ovp.solver.SimulationResult;
import nl.ovp.solver.Simulator;
import nl.ovp.ui.MainWindow;

/**
 * Application entry point. With no arguments, launches the Swing GUI
 * ({@link MainWindow}). With {@code --cli}, runs headless and prints the
 * simulation result as CSV to standard output:
 * <pre>java -jar app.jar --cli [--model N] [--wolves N] [--dt X] [--years N] [--replay YEAR]</pre>
 * {@code --model} is an index into {@link ModelRegistry#all()}; it defaults
 * to the most general (predator-prey) model so that {@code --wolves} always
 * takes effect.
 * <p>
 * {@code --replay YEAR} replays history: it starts from the counts observed on
 * 1 January of {@code YEAR} ({@code data/clean/herbivores_counts.csv}; a species
 * not yet present starts at 0) and applies the known culls, relocations,
 * introductions and die-off from {@code data/clean/herbivore_events.csv}.
 * Time {@code t = 0} in the output is 1 January of {@code YEAR}.
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) {
        if (hasFlag(args, "--cli")) {
            runCli(args);
        } else {
            SwingUtilities.invokeLater(() -> new MainWindow().setVisible(true));
        }
    }

    private static void runCli(String[] args) {
        int defaultModelIndex = ModelRegistry.all().size() - 1;
        int modelIndex = (int) doubleArg(args, "--model", defaultModelIndex);
        double wolves = doubleArg(args, "--wolves", 0.0);
        double dt = doubleArg(args, "--dt", 1.0 / 12.0);
        double years = doubleArg(args, "--years", 20.0);

        PopulationModel model = ModelRegistry.byIndex(modelIndex);
        ModelParameters parameters = new ModelParameters();
        parameters.initialWolves = wolves;
        parameters.dtYears = dt;
        parameters.horizonYears = years;
        if (hasFlag(args, "--replay")) {
            applyReplay(parameters, (int) doubleArg(args, "--replay", Double.NaN));
        }

        SimulationResult result = new Simulator().run(model, new RungeKutta4Solver(), parameters);
        System.out.print(result.toCsv());
    }

    /** Sets the start year, the observed initial counts of that year, and the known events. */
    static void applyReplay(ModelParameters p, int year) {
        CsvDataLoader loader = new CsvDataLoader();
        HerbivoreCount start = loader.loadHerbivores().stream()
            .filter(c -> c.year() == year)
            .findFirst()
            .orElseThrow(() -> new IllegalArgumentException("No herbivore counts for year " + year));
        p.startYear = year;
        p.initialCattle = orZero(start.cattle());
        p.initialHorses = orZero(start.horses());
        p.initialDeer = orZero(start.deer());
        p.events = loader.loadEvents();
    }

    private static double orZero(Double value) {
        return value == null ? 0.0 : value;
    }

    private static boolean hasFlag(String[] args, String flag) {
        for (String arg : args) {
            if (arg.equals(flag)) {
                return true;
            }
        }
        return false;
    }

    private static double doubleArg(String[] args, String flag, double defaultValue) {
        for (int i = 0; i < args.length - 1; i++) {
            if (args[i].equals(flag)) {
                return Double.parseDouble(args[i + 1]);
            }
        }
        return defaultValue;
    }
}
