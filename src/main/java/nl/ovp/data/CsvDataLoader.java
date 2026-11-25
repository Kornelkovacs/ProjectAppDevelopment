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

/**
 * Reads the cleaned CSV files produced by {@code scripts/clean_data.py} from
 * the raw Oostvaardersplassen Excel sheets in {@code data/raw/} (see
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
