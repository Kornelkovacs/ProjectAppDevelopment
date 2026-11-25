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
 * <p>
 * Known management events ({@link ModelParameters#events}: culls, relocations,
 * introductions, the 2017-18 die-off) enter as an extra flow {@code M_i(t)}:
 * <pre>
 * dN_i/dt = r_i * N_i * (1 - sum_j(alpha_ij * N_j) / K_i') + M_i(t)
 * M_i(t)  = sum over active events e affecting i of  flow_e * share_i
 * </pre>
 * with {@code flow_e = change_e / duration_e} (animals per year, negative for a
 * removal) and {@code share_i = 1} for a single-species event, or
 * {@code N_i / sum_j N_j} for an event on all species. Removals stop when a
 * species is extinct. With no active events {@code M_i = 0} and the model is the
 * plain competition model. This is the harvesting term of Gotelli ch. 2.
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
        addManagementFlows(t, y, p, dy);
        return dy;
    }

    /** Adds M_i(t) from {@link ModelParameters#events} to {@code dy}; see the class Javadoc. */
    static void addManagementFlows(double t, double[] y, ModelParameters p, double[] dy) {
        if (p.events.isEmpty()) {
            return;
        }
        double year = p.startYear + t;
        double total = 0.0;
        for (int i = 0; i < y.length; i++) {
            total += Math.max(0.0, y[i]);
        }
        Species[] species = Species.values();
        for (ManagementEvent e : p.events) {
            double flow = e.flowAt(year);
            if (flow == 0.0) {
                continue;
            }
            for (int i = 0; i < y.length; i++) {
                if (!e.affects(species[i])) {
                    continue;
                }
                double share = e.species() != null ? 1.0 : (total > 0 ? Math.max(0.0, y[i]) / total : 0.0);
                if (flow < 0 && y[i] <= 0.0) {
                    continue; // nothing left to remove
                }
                dy[i] += flow * share;
            }
        }
    }
}
