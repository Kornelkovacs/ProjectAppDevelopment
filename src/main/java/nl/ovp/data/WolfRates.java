package nl.ovp.data;

/**
 * Mean per-wolf rates per year in the wolf reference area (2010-2025), one row of
 * {@code data/clean/wolf_rates.csv}. Computed by {@code scripts/clean_data.py} from
 * measured values only. Not Oostvaardersplassen data: an order-of-magnitude indication.
 *
 * @param region        {@code North}, {@code South} or {@code All}
 * @param pupsPerWolf   pups born per wolf per year
 * @param deathsPerWolf recorded deaths per wolf per year
 * @param lostPerWolf   wolves that disappear without a recorded death (dispersal), per wolf per year
 * @param growthRate    observed growth rate ln(W(t+1)/W(t)), per year
 */
public record WolfRates(String region, double pupsPerWolf, double deathsPerWolf, double lostPerWolf,
                        double growthRate) {

    /** Total per-capita loss rate: recorded deaths plus wolves lost. */
    public double lossPerWolf() {
        return deathsPerWolf + lostPerWolf;
    }
}
