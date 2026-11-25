package nl.ovp.model;

/**
 * Iteration 2: Lotka-Volterra competition between cattle, horses and deer for
 * shared food (grass), with carrying capacities adjusted for climate change.
 * <p>
 * For each species i:
 * <pre>dN_i/dt = r_i * N_i * (1 - sum_j(alpha_ij * N_j) / K_i')</pre>
 * where {@code alpha_ij} is the competition effect of species j on species i
 * ({@link ModelParameters#competitionAlpha}, diagonal = 1), and the climate-
 * adjusted carrying capacity is
 * <pre>K_i' = K_i * grassFactor(deltaT) * max(0, 1 + s_i * deltaT)</pre>
 * combining less/more available grass ({@link GrassModel#grassFactor}) with a
 * per-species climate sensitivity {@code s_i}
 * ({@link ModelParameters#climateSensitivity}: positive for horses, negative
 * for cattle, per the project brief). See Gotelli, "A Primer of Ecology",
 * ch. 5 ("Competition models and theory") for the underlying Lotka-Volterra
 * competition equations.
 */
public final class CompetitionModel implements PopulationModel {

    @Override
    public String name() {
        return "Competition (cattle, horses, deer)";
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
        double grassFactor = GrassModel.grassFactor(p, p.deltaT);
        double[] dy = new double[y.length];
        for (int i = 0; i < y.length; i++) {
            double climateFactor = Math.max(0.0, 1.0 + p.climateSensitivity[i] * p.deltaT);
            double adjustedK = p.carryingCapacity[i] * grassFactor * climateFactor;

            double competitionSum = 0.0;
            for (int j = 0; j < y.length; j++) {
                competitionSum += p.competitionAlpha[i][j] * y[j];
            }

            dy[i] = adjustedK > 0 ? p.growthRate[i] * y[i] * (1.0 - competitionSum / adjustedK) : -p.growthRate[i] * y[i];
        }
        return dy;
    }
}
