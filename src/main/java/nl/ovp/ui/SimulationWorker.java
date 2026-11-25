package nl.ovp.ui;

import java.util.concurrent.ExecutionException;
import java.util.function.Consumer;

import javax.swing.SwingWorker;

import nl.ovp.model.ModelParameters;
import nl.ovp.model.PopulationModel;
import nl.ovp.solver.OdeSolver;
import nl.ovp.solver.SimulationResult;
import nl.ovp.solver.Simulator;

/**
 * Runs a {@link Simulator} off the Event Dispatch Thread, so a long or
 * pathological run (e.g. a very small step size over a long horizon) never
 * freezes the GUI. Results (or failures) are delivered back on the EDT via
 * the given callbacks.
 */
final class SimulationWorker extends SwingWorker<SimulationResult, Void> {

    private final PopulationModel model;
    private final OdeSolver solver;
    private final ModelParameters parameters;
    private final Consumer<SimulationResult> onSuccess;
    private final Consumer<Exception> onError;

    SimulationWorker(PopulationModel model, OdeSolver solver, ModelParameters parameters,
                      Consumer<SimulationResult> onSuccess, Consumer<Exception> onError) {
        this.model = model;
        this.solver = solver;
        this.parameters = parameters;
        this.onSuccess = onSuccess;
        this.onError = onError;
    }

    @Override
    protected SimulationResult doInBackground() {
        return new Simulator().run(model, solver, parameters);
    }

    @Override
    protected void done() {
        try {
            onSuccess.accept(get());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            onError.accept(e);
        } catch (ExecutionException e) {
            Throwable cause = e.getCause() != null ? e.getCause() : e;
            onError.accept(cause instanceof Exception ? (Exception) cause : e);
        }
    }
}
