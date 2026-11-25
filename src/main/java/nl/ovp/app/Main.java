package nl.ovp.app;

import javax.swing.SwingUtilities;

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
 * <pre>java -jar app.jar --cli [--model N] [--wolves N] [--dt X] [--years N]</pre>
 * {@code --model} is an index into {@link ModelRegistry#all()}; it defaults
 * to the most general (predator-prey) model so that {@code --wolves} always
 * takes effect.
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

        SimulationResult result = new Simulator().run(model, new RungeKutta4Solver(), parameters);
        System.out.print(result.toCsv());
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
