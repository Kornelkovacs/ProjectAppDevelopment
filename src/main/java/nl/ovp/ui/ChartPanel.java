package nl.ovp.ui;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.geom.Ellipse2D;
import java.awt.geom.Line2D;
import java.text.DecimalFormat;
import java.util.List;
import java.util.Map;

import javax.swing.JPanel;

import nl.ovp.data.HerbivoreCount;
import nl.ovp.model.SeasonalGrazingModel;
import nl.ovp.solver.SimulationResult;

/**
 * A minimal, dependency-free line chart drawn with Java2D: one line per
 * simulation series, a colour-blind friendly palette (Okabe &amp; Ito, 2008),
 * readable axis ticks, a legend showing each series' final value, and an
 * optional scatter overlay of observed herd counts.
 * <p>
 * The axis is in animals, so series in other units (the grass of
 * {@link SeasonalGrazingModel}, in tonnes) are not drawn. Their final value is
 * listed in the legend in grey, and the full series is in the CSV export.
 */
public final class ChartPanel extends JPanel {

    private static final Color AXIS_COLOR = new Color(90, 90, 90);
    private static final Color GRID_COLOR = new Color(225, 225, 225);
    private static final Font TITLE_FONT = new Font(Font.SANS_SERIF, Font.BOLD, 14);
    private static final Font LABEL_FONT = new Font(Font.SANS_SERIF, Font.PLAIN, 12);

    /** Okabe-Ito colour-blind safe palette, matched to series by name where possible. */
    private static final Map<String, Color> PALETTE_BY_NAME = Map.of(
        "Cattle", new Color(0xE6, 0x9F, 0x00),
        "Horses", new Color(0x56, 0xB4, 0xE9),
        "Deer", new Color(0x00, 0x9E, 0x73),
        "Wolves", new Color(0xCC, 0x79, 0xA7)
    );
    private static final Color[] FALLBACK_PALETTE = {
        new Color(0xF0, 0xE4, 0x42),
        new Color(0x00, 0x72, 0xB2),
        new Color(0xD5, 0x5E, 0x00)
    };

    private static final int MARGIN_LEFT = 70;
    private static final int MARGIN_RIGHT = 170;
    private static final int MARGIN_TOP = 40;
    private static final int MARGIN_BOTTOM = 50;

    private double[] times = new double[0];
    private double[][] states = new double[0][];
    private String[] seriesNames = new String[0];
    private String title = "No simulation run yet";

    private List<HerbivoreCount> observedCounts;
    private int observedStartYear;

    public void setResult(SimulationResult result, String title) {
        this.times = result.times();
        this.states = result.states();
        this.seriesNames = result.seriesNames();
        this.title = title;
        repaint();
    }

    public void setObservedOverlay(List<HerbivoreCount> counts, int startYear) {
        this.observedCounts = counts;
        this.observedStartYear = startYear;
        repaint();
    }

    public void clearObservedOverlay() {
        this.observedCounts = null;
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g.create();
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2.setColor(Color.WHITE);
        g2.fillRect(0, 0, getWidth(), getHeight());

        g2.setFont(TITLE_FONT);
        g2.setColor(Color.DARK_GRAY);
        g2.drawString(title, MARGIN_LEFT, 24);

        if (times.length == 0) {
            g2.dispose();
            return;
        }

        int plotLeft = MARGIN_LEFT;
        int plotTop = MARGIN_TOP;
        int plotWidth = Math.max(10, getWidth() - MARGIN_LEFT - MARGIN_RIGHT);
        int plotHeight = Math.max(10, getHeight() - MARGIN_TOP - MARGIN_BOTTOM);
        int plotRight = plotLeft + plotWidth;
        int plotBottom = plotTop + plotHeight;

        double xMax = times[times.length - 1];
        double yMax = maxAcrossAllSeries();
        if (yMax <= 0) {
            yMax = 1.0;
        }

        double xStep = niceNumber(xMax / 8.0, true);
        double yStep = niceNumber(yMax / 6.0, true);
        double xAxisMax = Math.ceil(xMax / xStep) * xStep;
        double yAxisMax = Math.ceil(yMax / yStep) * yStep;
        if (xAxisMax <= 0) {
            xAxisMax = 1;
        }

        g2.setFont(LABEL_FONT);
        DecimalFormat yFormat = new DecimalFormat(yStep < 1 ? "0.0" : "#,##0");

        // Horizontal gridlines + Y ticks.
        for (double yVal = 0; yVal <= yAxisMax + 1e-9; yVal += yStep) {
            int py = plotBottom - (int) Math.round(yVal / yAxisMax * plotHeight);
            g2.setColor(GRID_COLOR);
            g2.draw(new Line2D.Double(plotLeft, py, plotRight, py));
            g2.setColor(AXIS_COLOR);
            String label = yFormat.format(yVal);
            int labelWidth = g2.getFontMetrics().stringWidth(label);
            g2.drawString(label, plotLeft - labelWidth - 8, py + 4);
        }

        // Vertical gridlines + X ticks (years).
        DecimalFormat xFormat = new DecimalFormat(xStep < 1 ? "0.0" : "#,##0");
        for (double xVal = 0; xVal <= xAxisMax + 1e-9; xVal += xStep) {
            int px = plotLeft + (int) Math.round(xVal / xAxisMax * plotWidth);
            g2.setColor(GRID_COLOR);
            g2.draw(new Line2D.Double(px, plotTop, px, plotBottom));
            g2.setColor(AXIS_COLOR);
            String label = xFormat.format(xVal);
            int labelWidth = g2.getFontMetrics().stringWidth(label);
            g2.drawString(label, px - labelWidth / 2, plotBottom + 18);
        }

        g2.setColor(AXIS_COLOR);
        g2.draw(new Line2D.Double(plotLeft, plotBottom, plotRight, plotBottom));
        g2.draw(new Line2D.Double(plotLeft, plotTop, plotLeft, plotBottom));
        g2.drawString("years", plotRight - 30, plotBottom + 36);

        // Series lines.
        Color[] colorsBySeries = new Color[seriesNames.length];
        int fallbackIndex = 0;
        for (int s = 0; s < seriesNames.length; s++) {
            Color c = PALETTE_BY_NAME.get(seriesNames[s]);
            if (c == null) {
                c = FALLBACK_PALETTE[fallbackIndex % FALLBACK_PALETTE.length];
                fallbackIndex++;
            }
            colorsBySeries[s] = c;
        }

        g2.setStroke(new BasicStroke(2.2f));
        for (int s = 0; s < seriesNames.length; s++) {
            if (!isPlotted(seriesNames[s])) {
                continue;
            }
            g2.setColor(colorsBySeries[s]);
            int prevX = -1;
            int prevY = -1;
            for (int step = 0; step < times.length; step++) {
                int px = plotLeft + (int) Math.round(times[step] / xAxisMax * plotWidth);
                double value = states[step][s];
                int py = plotBottom - (int) Math.round(value / yAxisMax * plotHeight);
                if (prevX >= 0) {
                    g2.draw(new Line2D.Double(prevX, prevY, px, py));
                }
                prevX = px;
                prevY = py;
            }
        }

        // Observed data overlay (dots).
        if (observedCounts != null) {
            drawObservedDots(g2, plotLeft, plotBottom, plotWidth, plotHeight, xAxisMax, yAxisMax,
                "Cattle", HerbivoreCount::cattle);
            drawObservedDots(g2, plotLeft, plotBottom, plotWidth, plotHeight, xAxisMax, yAxisMax,
                "Horses", HerbivoreCount::horses);
            drawObservedDots(g2, plotLeft, plotBottom, plotWidth, plotHeight, xAxisMax, yAxisMax,
                "Deer", HerbivoreCount::deer);
        }

        drawLegend(g2, plotRight + 15, plotTop, colorsBySeries);

        g2.dispose();
    }

    private interface CountExtractor {
        Double extract(HerbivoreCount count);
    }

    private void drawObservedDots(Graphics2D g2, int plotLeft, int plotBottom, int plotWidth, int plotHeight,
                                   double xAxisMax, double yAxisMax, String seriesName, CountExtractor extractor) {
        Color color = PALETTE_BY_NAME.getOrDefault(seriesName, Color.GRAY).darker();
        g2.setColor(color);
        for (HerbivoreCount count : observedCounts) {
            Double value = extractor.extract(count);
            if (value == null) {
                continue;
            }
            double t = count.year() - observedStartYear;
            if (t < 0 || t > xAxisMax) {
                continue;
            }
            int px = plotLeft + (int) Math.round(t / xAxisMax * plotWidth);
            int py = plotBottom - (int) Math.round(value / yAxisMax * plotHeight);
            g2.fill(new Ellipse2D.Double(px - 3, py - 3, 6, 6));
        }
    }

    private void drawLegend(Graphics2D g2, int x, int y, Color[] colorsBySeries) {
        g2.setFont(LABEL_FONT);
        int lineHeight = 20;
        for (int s = 0; s < seriesNames.length; s++) {
            int ly = y + s * lineHeight;
            double endValue = states.length > 0 ? states[states.length - 1][s] : 0.0;
            String label = String.format("%s (%.0f)", seriesNames[s], endValue);
            if (isPlotted(seriesNames[s])) {
                g2.setColor(colorsBySeries[s]);
                g2.fillRect(x, ly, 12, 12);
                g2.setColor(Color.DARK_GRAY);
            } else {
                g2.setColor(Color.GRAY); // value only, not drawn (other unit)
            }
            g2.drawString(label, x + 18, ly + 11);
        }
    }

    /** True for series measured in animals; false for e.g. grass in tonnes. */
    static boolean isPlotted(String seriesName) {
        return !SeasonalGrazingModel.GRASS_SERIES.equals(seriesName);
    }

    private double maxAcrossAllSeries() {
        double max = 0.0;
        for (double[] state : states) {
            for (int s = 0; s < state.length; s++) {
                if (isPlotted(seriesNames[s])) {
                    max = Math.max(max, state[s]);
                }
            }
        }
        if (observedCounts != null) {
            for (HerbivoreCount count : observedCounts) {
                max = Math.max(max, nullToZero(count.cattle()));
                max = Math.max(max, nullToZero(count.horses()));
                max = Math.max(max, nullToZero(count.deer()));
            }
        }
        return max;
    }

    private static double nullToZero(Double value) {
        return value == null ? 0.0 : value;
    }

    /**
     * Rounds {@code range} to a "nice" step size (1, 2 or 5 times a power of
     * ten) for readable axis ticks. Classic algorithm, see Heckbert, "Nice
     * Numbers for Graph Labels", Graphics Gems I (1990).
     */
    private static double niceNumber(double range, boolean round) {
        if (range <= 0) {
            return 1.0;
        }
        double exponent = Math.floor(Math.log10(range));
        double fraction = range / Math.pow(10, exponent);
        double niceFraction;
        if (round) {
            if (fraction < 1.5) {
                niceFraction = 1;
            } else if (fraction < 3) {
                niceFraction = 2;
            } else if (fraction < 7) {
                niceFraction = 5;
            } else {
                niceFraction = 10;
            }
        } else {
            if (fraction <= 1) {
                niceFraction = 1;
            } else if (fraction <= 2) {
                niceFraction = 2;
            } else if (fraction <= 5) {
                niceFraction = 5;
            } else {
                niceFraction = 10;
            }
        }
        return niceFraction * Math.pow(10, exponent);
    }
}
