package nl.ovp.data;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

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
}
