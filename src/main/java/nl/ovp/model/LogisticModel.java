package nl.ovp.model;

/**
 * Iteration 1: independent logistic growth for each species, ignoring any
 * interaction between cattle, horses and deer and ignoring predation.
 * <p>
 * For each species i:
 * <pre>dN_i/dt = r_i * N_i * (1 - N_i / K_i)</pre>
 * This is the simplest population model capable of showing self-limited
 * growth toward a carrying capacity; see Gotelli, "A Primer of Ecology",
 * ch. 2 ("Exponential and logistic population growth"). It serves as the
 * baseline before adding competition ({@link CompetitionModel}) and
 * predation ({@link PredatorPreyModel}).
 */
public final class LogisticModel implements PopulationModel {

    @Override
    public String name() {
        return "Logistic growth (independent species)";
    }

    @Override
    public String[] stateNames() {
        return new String[] {"Cattle", "Horses", "Deer"};
    }

    @Override
    public double[] initialState(ModelParameters p) {
        return new double[] {p.initialCattle, p.initialHorses, p.initialDeer};
    }

    @Override
    public double[] derivatives(double t, double[] y, ModelParameters p) {
        double[] dy = new double[y.length];
        for (int i = 0; i < y.length; i++) {
            double r = p.growthRate[i];
            double k = p.carryingCapacity[i];
            dy[i] = k > 0 ? r * y[i] * (1.0 - y[i] / k) : -r * y[i];
        }
        return dy;
    }
}
