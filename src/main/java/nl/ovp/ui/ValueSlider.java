package nl.ovp.ui;

import java.awt.BorderLayout;
import java.awt.Dimension;
import java.util.Locale;

import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JSlider;
import javax.swing.SwingConstants;

/**
 * A horizontal slider for a decimal value with a fixed step, showing the
 * current value next to it. {@link JSlider} only handles integers, so the
 * value is stored internally as a whole number of steps.
 */
final class ValueSlider extends JPanel {

    private final JSlider slider;
    private final JLabel valueLabel;
    private final double step;
    private final String format;

    /**
     * @param min     smallest value
     * @param max     largest value
     * @param step    increment between neighbouring slider positions
     * @param initial starting value (rounded to the nearest step)
     * @param format  {@link String#format} pattern for the value label, e.g. "%.2f"
     */
    ValueSlider(double min, double max, double step, double initial, String format) {
        super(new BorderLayout(6, 0));
        this.step = step;
        this.format = format;
        slider = new JSlider(toTicks(min), toTicks(max), toTicks(initial));
        valueLabel = new JLabel("", SwingConstants.RIGHT);
        valueLabel.setPreferredSize(new Dimension(48, valueLabel.getPreferredSize().height));
        slider.addChangeListener(e -> updateLabel());
        updateLabel();
        setOpaque(false);
        add(slider, BorderLayout.CENTER);
        add(valueLabel, BorderLayout.EAST);
    }

    double getValue() {
        return slider.getValue() * step;
    }

    void setValue(double value) {
        slider.setValue(toTicks(value));
    }

    @Override
    public void setToolTipText(String text) {
        super.setToolTipText(text);
        slider.setToolTipText(text);
    }

    private int toTicks(double value) {
        return (int) Math.round(value / step);
    }

    private void updateLabel() {
        valueLabel.setText(String.format(Locale.ROOT, format, getValue()));
    }
}
