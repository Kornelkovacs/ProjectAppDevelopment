package nl.ovp.model;

/**
 * Iteration 3: {@link CompetitionModel} extended with grey wolves as a top
 * predator, used to answer research question B (effect of releasing wolves).
 * <p>
 * Wolves hunt all three prey species simultaneously via a multi-prey Holling
 * type II functional response. The rate at which species i is killed is
 * <pre>kills_i = a_i * w_i * N_i * W / (1 + h * sum_j(a_j * w_j * N_j))</pre>
 * where {@code a_i} is the attack rate, {@code w_i} the prey preference in
 * [0, 1], and {@code h} the handling time (all in {@link ModelParameters}).
 * Prey dynamics are the competition growth rate from {@link CompetitionModel}
 * minus predation losses; wolves grow from the biomass they convert from
 * kills and decline from natural mortality:
 * <pre>
 * dN_i/dt = competitionGrowth_i - kills_i
 * dW/dt   = sum_i(e_i * kills_i) - m * W
 * </pre>
 * See Gotelli, "A Primer of Ecology", ch. 6 ("Predator-prey systems") for the
 * single-prey Lotka-Volterra and Holling type II foundations that this
 * multi-prey functional response extends.
 */
public final class PredatorPreyModel implements PopulationModel {

    private final CompetitionModel competitionModel = new CompetitionModel();

    @Override
    public String name() {
        return "Predator-prey (wolves + cattle, horses, deer)";
    }

    @Override
    public String[] stateNames() {
        return new String[] {"Cattle", "Horses", "Deer", "Wolves"};
    }

    @Override
    public double[] initialState(ModelParameters p) {
        return new double[] {p.initialCattle, p.initialHorses, p.initialDeer, p.initialWolves};
    }

    @Override
    public double[] derivatives(double t, double[] y, ModelParameters p) {
        double[] preyState = {y[0], y[1], y[2]};
        double[] preyGrowth = competitionModel.derivatives(t, preyState, p);
        double wolves = y[3];

        double weightedPreySum = 0.0;
        for (int j = 0; j < preyState.length; j++) {
            weightedPreySum += p.attackRate[j] * p.preyPreference[j] * preyState[j];
        }
        double denominator = 1.0 + p.handlingTime * weightedPreySum;

        double[] dy = new double[4];
        double wolfGrowth = 0.0;
        for (int i = 0; i < preyState.length; i++) {
            double kill = p.attackRate[i] * p.preyPreference[i] * preyState[i] * wolves / denominator;
            dy[i] = preyGrowth[i] - kill;
            wolfGrowth += p.conversionEfficiency[i] * kill;
        }
        dy[3] = wolfGrowth - p.wolfMortality * wolves;
        return dy;
    }
}
