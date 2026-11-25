package nl.ovp.data;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import nl.ovp.model.ManagementEvent;
import nl.ovp.model.ModelParameters;
import nl.ovp.model.Species;

class CsvDataLoaderTest {

    @Test
    void parsesHerbivoreCountsWithEmptyCellsAsNull(@TempDir Path tempDir) throws IOException {
        Path csv = tempDir.resolve("herbivores_counts.csv");
        Files.writeString(csv, """
            year,cattle,horses,deer,total,reliable,note
            1983,30,,,30,True,
            1992,120,95,40,255,True,
            """);

        List<HerbivoreCount> rows = new CsvDataLoader().loadHerbivores(csv);

        assertEquals(2, rows.size());
        assertEquals(1983, rows.get(0).year());
        assertEquals(30.0, rows.get(0).cattle());
        assertNull(rows.get(0).horses());
        assertNull(rows.get(0).deer());

        assertEquals(1992, rows.get(1).year());
        assertEquals(40.0, rows.get(1).deer());
    }

    @Test
    void parsesGrassHeightObservations(@TempDir Path tempDir) throws IOException {
        Path csv = tempDir.resolve("grass_height.csv");
        Files.writeString(csv, """
            year,grass_height_cm
            1990,45.5
            1991,
            """);

        List<GrassHeightObservation> rows = new CsvDataLoader().loadGrassHeight(csv);

        assertEquals(2, rows.size());
        assertEquals(45.5, rows.get(0).heightCm());
        assertNull(rows.get(1).heightCm());
    }

    @Test
    void loadsRealProjectHerbivoresCsv() {
        List<HerbivoreCount> rows = new CsvDataLoader().loadHerbivores(
            Path.of("data", "clean", "herbivores_counts.csv"));

        assertEquals(43, rows.size());
        assertEquals(1983, rows.get(0).year());
        assertEquals(30.0, rows.get(0).cattle());
        assertNull(rows.get(0).horses()); // horses introduced 1984
        assertNull(rows.get(0).deer());   // deer only counted from 1992
    }

    @Test
    void loadsRealProjectGrassHeightCsv() {
        List<GrassHeightObservation> rows = new CsvDataLoader().loadGrassHeight(
            Path.of("data", "clean", "grass_height.csv"));

        assertEquals(25, rows.size());
        assertEquals(1990, rows.get(0).year());
        assertEquals(28.79, rows.get(0).heightCm());
    }

    @Test
    void parsesClimateObservations(@TempDir Path tempDir) throws IOException {
        Path csv = tempDir.resolve("climate_monthly.csv");
        Files.writeString(csv, """
            year,month,t_mean_c,rain_mm,evap_mm,source_t,source_rain,source_evap,flag
            1990,7,16.25,43.3,100.7,Lelystad,De Bilt,Lelystad,ok
            """);

        List<ClimateObservation> rows = new CsvDataLoader().loadClimate(csv);

        assertEquals(1, rows.size());
        ClimateObservation july = rows.get(0);
        assertEquals(7, july.month());
        assertEquals(16.25, july.meanTempC());
        assertEquals(-57.4, july.waterBalanceMm(), 1e-9);
        assertEquals(1990 + 6.5 / 12, july.midMonthYear(), 1e-12);
    }

    @Test
    void loadsRealProjectClimateCsv() {
        List<ClimateObservation> rows = new CsvDataLoader().loadClimate(
            Path.of("data", "clean", "climate_monthly.csv"));

        assertEquals(43 * 12, rows.size()); // every month 1983-2025
        assertEquals(1983, rows.get(0).year());
        assertEquals(1, rows.get(0).month());
        assertEquals(5.83, rows.get(0).meanTempC());
        assertEquals(94.6, rows.get(0).rainMm());
        assertEquals(7.6, rows.get(0).evapMm());
        assertEquals(2025, rows.get(rows.size() - 1).year());
        assertEquals(12, rows.get(rows.size() - 1).month());
    }

    @Test
    void parsesEventsAsInclusiveMonthWindows(@TempDir Path tempDir) throws IOException {
        Path csv = tempDir.resolve("herbivore_events.csv");
        Files.writeString(csv, """
            event,species,start,end,change,source
            cull,deer,2018-12,2019-10,-1785,footnote 2)
            die-off,all,2017-12,2018-03,-3226,NOS
            """);

        List<ManagementEvent> events = new CsvDataLoader().loadEvents(csv);

        ManagementEvent cull = events.get(0);
        assertEquals(Species.DEER, cull.species());
        assertEquals(2018 + 11 / 12.0, cull.startYear(), 1e-12);
        assertEquals(2019 + 10 / 12.0, cull.endYear(), 1e-12); // end of October
        assertEquals(-1785.0, cull.change());
        assertNull(events.get(1).species()); // "all"
        assertEquals(4 / 12.0, events.get(1).endYear() - events.get(1).startYear(), 1e-12);
    }

    @Test
    void loadsRealProjectEventsCsv() {
        List<ManagementEvent> events = new CsvDataLoader().loadEvents(
            Path.of("data", "clean", "herbivore_events.csv"));

        assertEquals(6, events.size());
        double removedDeer = events.stream()
            .filter(e -> e.species() == Species.DEER && e.change() < 0)
            .mapToDouble(ManagementEvent::change)
            .sum();
        assertEquals(-1785.0 - 1800.0, removedDeer);
    }

    @Test
    void defaultWolfMortalityMatchesWolfRatesCsv() {
        WolfRates all = new CsvDataLoader().loadWolfRates(Path.of("data", "clean", "wolf_rates.csv"))
            .stream().filter(r -> r.region().equals("All")).findFirst().orElseThrow();

        assertEquals(all.lossPerWolf(), new ModelParameters().wolfMortality, 0.005);
        // pups - deaths - lost should explain the observed growth (balance of the wolf data)
        assertTrue(Math.abs(all.pupsPerWolf() - all.lossPerWolf() - all.growthRate()) < 0.01);
    }
}
