package nl.ovp.data;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import nl.ovp.model.ManagementEvent;
import nl.ovp.model.Species;

/**
 * Reads the cleaned CSV files produced by {@code scripts/clean_data.py} from
 * the raw Oostvaardersplassen Excel sheets in {@code data/raw/}, and by
 * {@code scripts/clean_climate.py} from the KNMI files in {@code data/raw/knmi/} (see
 * {@code data/README.md} for the exact corrections applied, e.g. dropping
 * "not always trustworthy" counts or an impossible 500 kg deer weight). Java
 * only ever reads these CSVs; it never touches the raw {@code .xlsx} files.
 * <p>
 * Columns are looked up by header name, so extra columns (e.g.
 * {@code total}, {@code reliable}, {@code note} in {@code herbivores_counts.csv})
 * are ignored; only the columns this loader needs are read.
 */
public final class CsvDataLoader {

    private static final Path DEFAULT_HERBIVORES_CSV = Path.of("data", "clean", "herbivores_counts.csv");
    private static final Path DEFAULT_GRASS_HEIGHT_CSV = Path.of("data", "clean", "grass_height.csv");
    private static final Path DEFAULT_CLIMATE_CSV = Path.of("data", "clean", "climate_monthly.csv");
    private static final Path DEFAULT_EVENTS_CSV = Path.of("data", "clean", "herbivore_events.csv");
    private static final Path DEFAULT_WOLF_RATES_CSV = Path.of("data", "clean", "wolf_rates.csv");

    /** Loads {@code data/clean/herbivores_counts.csv} relative to the working directory. */
    public List<HerbivoreCount> loadHerbivores() {
        return loadHerbivores(DEFAULT_HERBIVORES_CSV);
    }

    public List<HerbivoreCount> loadHerbivores(Path csvPath) {
        List<HerbivoreCount> rows = new ArrayList<>();
        CsvTable table = readCsv(csvPath);
        for (Map<String, String> row : table.rows()) {
            int year = Integer.parseInt(table.require(row, "year").trim());
            rows.add(new HerbivoreCount(
                year,
                parseNullableDouble(table.require(row, "cattle")),
                parseNullableDouble(table.require(row, "horses")),
                parseNullableDouble(table.require(row, "deer"))));
        }
        return rows;
    }

    /** Loads {@code data/clean/grass_height.csv} relative to the working directory. */
    public List<GrassHeightObservation> loadGrassHeight() {
        return loadGrassHeight(DEFAULT_GRASS_HEIGHT_CSV);
    }

    public List<GrassHeightObservation> loadGrassHeight(Path csvPath) {
        List<GrassHeightObservation> rows = new ArrayList<>();
        CsvTable table = readCsv(csvPath);
        for (Map<String, String> row : table.rows()) {
            int year = Integer.parseInt(table.require(row, "year").trim());
            rows.add(new GrassHeightObservation(year, parseNullableDouble(table.require(row, "grass_height_cm"))));
        }
        return rows;
    }

    /** Loads {@code data/clean/climate_monthly.csv} relative to the working directory. */
    public List<ClimateObservation> loadClimate() {
        return loadClimate(DEFAULT_CLIMATE_CSV);
    }

    /**
     * Reads monthly temperature, rain and evaporation. The cleaning script
     * ({@code scripts/clean_climate.py}) guarantees the series is complete, so
     * an empty cell here is an error rather than a gap.
     */
    public List<ClimateObservation> loadClimate(Path csvPath) {
        List<ClimateObservation> rows = new ArrayList<>();
        CsvTable table = readCsv(csvPath);
        for (Map<String, String> row : table.rows()) {
            rows.add(new ClimateObservation(
                Integer.parseInt(table.require(row, "year").trim()),
                Integer.parseInt(table.require(row, "month").trim()),
                Double.parseDouble(table.require(row, "t_mean_c").trim()),
                Double.parseDouble(table.require(row, "rain_mm").trim()),
                Double.parseDouble(table.require(row, "evap_mm").trim())));
        }
        return rows;
    }

    /** Loads {@code data/clean/herbivore_events.csv} relative to the working directory. */
    public List<ManagementEvent> loadEvents() {
        return loadEvents(DEFAULT_EVENTS_CSV);
    }

    /**
     * Reads introductions, culls, relocations and the die-off. {@code start} and
     * {@code end} are inclusive months ({@code YYYY-MM}); the event window runs from
     * the first day of {@code start} to the last day of {@code end}. Species
     * {@code all} becomes {@code null} (shared by all species).
     */
    public List<ManagementEvent> loadEvents(Path csvPath) {
        List<ManagementEvent> rows = new ArrayList<>();
        CsvTable table = readCsv(csvPath);
        for (Map<String, String> row : table.rows()) {
            String species = table.require(row, "species").trim();
            rows.add(new ManagementEvent(
                species.equals("all") ? null : Species.valueOf(species.toUpperCase()),
                monthStart(table.require(row, "start")),
                monthStart(table.require(row, "end")) + 1.0 / 12.0,
                Double.parseDouble(table.require(row, "change").trim())));
        }
        return rows;
    }

    /** Loads {@code data/clean/wolf_rates.csv} relative to the working directory. */
    public List<WolfRates> loadWolfRates() {
        return loadWolfRates(DEFAULT_WOLF_RATES_CSV);
    }

    public List<WolfRates> loadWolfRates(Path csvPath) {
        List<WolfRates> rows = new ArrayList<>();
        CsvTable table = readCsv(csvPath);
        for (Map<String, String> row : table.rows()) {
            rows.add(new WolfRates(
                table.require(row, "region").trim(),
                Double.parseDouble(table.require(row, "pups_per_wolf_mean").trim()),
                Double.parseDouble(table.require(row, "deaths_per_wolf_mean").trim()),
                Double.parseDouble(table.require(row, "lost_per_wolf_mean").trim()),
                Double.parseDouble(table.require(row, "growth_rate_mean").trim())));
        }
        return rows;
    }

    /** {@code "2018-12"} -> 2018 + 11/12, the first instant of that month as a decimal year. */
    private static double monthStart(String yyyyMm) {
        String[] parts = yyyyMm.trim().split("-");
        return Integer.parseInt(parts[0]) + (Integer.parseInt(parts[1]) - 1) / 12.0;
    }

    private static Double parseNullableDouble(String raw) {
        String trimmed = raw.trim();
        return trimmed.isEmpty() ? null : Double.parseDouble(trimmed);
    }

    /** A CSV file split into a header (column name -> index) and raw string rows, both by column name. */
    private record CsvTable(List<Map<String, String>> rows) {
        String require(Map<String, String> row, String column) {
            String value = row.get(column);
            if (value == null) {
                throw new IllegalStateException("Missing expected column '" + column + "'");
            }
            return value;
        }
    }

    /**
     * Reads a comma-separated file with a header row into a list of
     * column-name-to-value maps. No quoted-field support: the files this
     * loader reads never contain a comma inside a field.
     */
    private static CsvTable readCsv(Path csvPath) {
        List<String> lines;
        try {
            lines = Files.readAllLines(csvPath, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("Could not read CSV file: " + csvPath, e);
        }
        if (lines.isEmpty()) {
            throw new IllegalStateException("CSV file has no header row: " + csvPath);
        }

        String[] header = lines.get(0).split(",", -1);
        List<Map<String, String>> rows = new ArrayList<>();
        for (int i = 1; i < lines.size(); i++) {
            String line = lines.get(i);
            if (line.isBlank()) {
                continue;
            }
            String[] fields = line.split(",", -1);
            if (fields.length != header.length) {
                throw new IllegalStateException(
                    "Malformed row " + (i + 1) + " in " + csvPath + ": expected " + header.length
                        + " columns, got " + fields.length + " (" + line + ")");
            }
            Map<String, String> row = new HashMap<>();
            for (int c = 0; c < header.length; c++) {
                row.put(header[c].trim(), fields[c]);
            }
            rows.add(row);
        }
        return new CsvTable(rows);
    }
}
