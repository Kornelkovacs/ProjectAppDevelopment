package nl.ovp.model;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;

import nl.ovp.data.ClimateObservation;
import nl.ovp.data.CsvDataLoader;

class GrassModelTest {

    /**
     * The temperature-profile defaults must stay in agreement with the KNMI data
     * they were fitted on (scripts/fit_temperature_profile.py, 1983–2017). Over whole
     * years the least-squares fit of {@code a + b cos(2π(t - 6.5/12))} reduces to
     * a = mean and b = (2/n) Σ T cos(...), which is what is recomputed here.
     */
    @Test
    void temperatureDefaultsMatchKnmiFit() {
        List<ClimateObservation> months = new CsvDataLoader()
            .loadClimate(Path.of("data", "clean", "climate_monthly.csv")).stream()
            .filter(o -> o.year() >= 1983 && o.year() <= 2017)
            .toList();

        double sum = 0.0;
        double cosSum = 0.0;
        for (ClimateObservation o : months) {
            double t = (o.month() - 0.5) / 12.0;
            sum += o.meanTempC();
            cosSum += o.meanTempC() * Math.cos(2 * Math.PI * (t - 6.5 / 12.0));
        }
        double mean = sum / months.size();
        double amplitude = 2.0 * cosSum / months.size();

        ModelParameters p = new ModelParameters();
        assertEquals(mean, p.meanAnnualTemperature, 0.05);
        assertEquals(amplitude, p.seasonalAmplitude, 0.05);
    }

    @Test
    void grassFactorIsOneWithoutWarming() {
        assertEquals(1.0, GrassModel.grassFactor(new ModelParameters(), 0.0), 1e-12);
    }
}
