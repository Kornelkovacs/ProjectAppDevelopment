"""
Build docs/APPLICATION_GUIDE.pdf: what the application does, how it is used and built, how it changed,
and the decisions behind it. It does not explain the equations; it points to the equation numbers and
pages of docs/MODEL_EQUATIONS.pdf, which this script rebuilds first so the page references always match.

Usage (from the repository root, after `mvn package`):
    python3 scripts/build_application_guide_pdf.py

Requires: reportlab, matplotlib, numpy; a JDK (java, jshell) because MODEL_EQUATIONS.pdf is rebuilt.
"""
import csv
import glob
import io
import os
import re
import subprocess
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_model_equations_pdf as eqpdf  # noqa: E402

from reportlab.graphics.shapes import Drawing, Group, Line, Polygon, Rect, String  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import KeepTogether, PageBreak, Spacer  # noqa: E402

from build_model_equations_pdf import (BODY, CAPTION, H1, H2, H3, NAVY, BLUE, PALE, SMALL,  # noqa: E402
                                       TrackingDoc, code, fmt, note, para, table, box)

OUT = os.path.join("docs", "APPLICATION_GUIDE.pdf")
IDX = {}                       # index of MODEL_EQUATIONS.pdf, filled by build()
PREV_SECTIONS = {}             # section pages of this guide from the first pass
ME = "<i>Model Equations</i>"  # short name of docs/MODEL_EQUATIONS.pdf


# ----------------------------------------------------------------------------- references into MODEL_EQUATIONS.pdf
def EQ(first, last=None):
    a = IDX["equations"][first]
    if last is None:
        return f"eq. ({a['number']}), p. {a['page']}"
    b = IDX["equations"][last]
    pages = f"p. {a['page']}" if a["page"] == b["page"] else f"pp. {a['page']}-{b['page']}"
    return f"eq. ({a['number']})-({b['number']}), {pages}"


def SEC(n):
    return f"§{n}, p. {IDX['sections'][n]['page']}"


def PG(n):
    return str(PREV_SECTIONS.get(n, {}).get("page", "?"))


# ----------------------------------------------------------------------------- live facts
def test_counts():
    out = []
    for f in sorted(glob.glob("src/test/java/nl/ovp/*/*Test.java")):
        with open(f, encoding="utf-8") as fh:
            out.append((os.path.basename(f)[:-5], fh.read().count("@Test")))
    return out


def csv_rows(name):
    with open(os.path.join("data", "clean", name), encoding="utf-8") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def git_log():
    out = subprocess.run(["git", "log", "--reverse", "--format=%h|%ad|%s", "--date=format:%Y-%m-%d %H:%M"],
                         capture_output=True, text=True).stdout.strip().splitlines()
    return [l.split("|", 2) for l in out]


def ceiling_years():
    """Years until model 3, from the policy target with default parameters, first exceeds 1,500 animals."""
    _, rows = eqpdf.cli_rows("--model", "2", "--years", "50")
    return next(r[0] for r in rows if sum(r[1:4]) > 1500)


# ----------------------------------------------------------------------------- page decoration
def decorate(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    if doc.page > 1:
        canvas.drawString(2 * cm, A4[1] - 1.3 * cm, "Oostvaardersplassen population model: application guide")
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.3 * cm, "Project Application Development 2026-2027")
        canvas.setStrokeColor(colors.HexColor("#b8c4d4"))
        canvas.line(2 * cm, A4[1] - 1.45 * cm, A4[0] - 2 * cm, A4[1] - 1.45 * cm)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, str(doc.page))
    canvas.restoreState()


# ----------------------------------------------------------------------------- architecture diagram
def architecture_diagram():
    """Layer diagram. Coordinates in points; the drawing is 465 x 300 (16.4 cm wide)."""
    import math
    d = Drawing(465, 300)
    ink, muted, frame = NAVY, colors.HexColor("#5b6b80"), colors.HexColor("#b8c4d4")
    orange, orange_bg = colors.HexColor("#e69500"), colors.HexColor("#fff4e0")

    def boxed(x, y, w, h, title, lines_, fill=PALE, stroke=BLUE):
        d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill, strokeColor=stroke, strokeWidth=1))
        d.add(String(x + 5, y + h - 12, title, fontName="Helvetica-Bold", fontSize=8.5, fillColor=ink))
        for k, t in enumerate(lines_):
            d.add(String(x + 5, y + h - 24 - 9.5 * k, t, fontName="Helvetica", fontSize=6.8, fillColor=muted))

    def head(x1, y1, x2, y2):
        ang, s_ = math.atan2(y2 - y1, x2 - x1), 5
        d.add(Polygon([x2, y2, x2 - s_ * math.cos(ang - 0.4), y2 - s_ * math.sin(ang - 0.4),
                       x2 - s_ * math.cos(ang + 0.4), y2 - s_ * math.sin(ang + 0.4)],
                      fillColor=muted, strokeColor=muted, strokeWidth=0.5))

    def arrow(points, label=None, at=None):
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            d.add(Line(x1, y1, x2, y2, strokeColor=muted, strokeWidth=0.9))
        head(*points[-2], *points[-1])
        if label:
            d.add(String(at[0], at[1], label, fontName="Helvetica-Oblique", fontSize=6.5, fillColor=muted))

    def vlabel(x, y, text):
        g = Group(String(0, 0, text, fontName="Helvetica-Oblique", fontSize=6.5, fillColor=muted))
        g.transform = (0, 1, -1, 0, x, y)
        d.add(g)

    # Java application
    d.add(Rect(118, 2, 232, 296, rx=6, ry=6, fillColor=None, strokeColor=frame, strokeDashArray=[3, 2]))
    d.add(String(126, 287, "Java application (target/app.jar)", fontName="Helvetica-Bold", fontSize=8, fillColor=muted))
    bx, bw = 138, 189
    boxed(bx, 230, bw, 48, "app  -  Main", ["no arguments: GUI;  --cli: headless, CSV to stdout",
                                            "--model  --wolves  --dt  --years  --replay YEAR"])
    boxed(bx, 168, bw, 48, "ui  -  Swing", ["MainWindow, ParameterPanel, ChartPanel,",
                                            "ValueSlider, SimulationWorker (background run)"])
    boxed(bx, 86, 90, 68, "data", ["CsvDataLoader", "records: HerbivoreCount,", "GrassHeightObservation,",
                                   "ClimateObservation, ..."])
    boxed(bx + 99, 86, 90, 68, "solver", ["EulerSolver,", "RungeKutta4Solver", "Simulator (time loop,",
                                          "internal steps, clamp)"])
    boxed(bx, 8, bw, 64, "model  (lowest layer)", ["PopulationModel: Logistic, Competition,",
                                                   "SeasonalGrazing, PredatorPrey",
                                                   "ModelParameters, ModelRegistry, GrassModel,",
                                                   "ManagementEvent, Species"])
    arrow([(232, 230), (232, 216)], "uses", (236, 220))
    arrow([(183, 168), (183, 154)])
    arrow([(282, 168), (282, 154)])
    arrow([(183, 86), (183, 72)])
    arrow([(282, 86), (282, 72)])
    arrow([(bx, 254), (128, 254), (128, 120), (bx, 120)])          # app -> data (replay)
    vlabel(126, 150, "--replay: counts, events")
    arrow([(bx + bw, 254), (337, 254), (337, 120), (bx + bw, 120)])  # app -> solver (--cli)
    vlabel(346, 172, "--cli")

    # left: data pipeline (Python, offline)
    boxed(0, 228, 106, 50, "data/raw", ["KNMI climate files", "course spreadsheets", "(not in the repo yet)"],
          fill=colors.white, stroke=muted)
    boxed(0, 150, 106, 66, "scripts/ (Python)", ["clean_data, clean_climate", "fit_parameters,",
                                                 "fit_temperature_profile", "plot_validation, build_*_pdf"],
          fill=orange_bg, stroke=orange)
    boxed(0, 86, 106, 52, "data/clean/*.csv", ["the only files Java reads", "(by column name);",
                                               "never edited by hand"], fill=colors.white, stroke=muted)
    arrow([(53, 228), (53, 216)], "read", (57, 220))
    arrow([(53, 150), (53, 138)], "write", (57, 142))
    arrow([(106, 104), (bx, 104)], "read", (108, 107))

    # right: outputs
    boxed(359, 196, 106, 82, "outputs", ["chart (GUI)", "CSV export (GUI)", "CSV on stdout (--cli)",
                                         "figures and PDFs", "(made by the scripts)"], fill=colors.white, stroke=muted)
    boxed(359, 8, 106, 176, "docs/", ["MODEL_EQUATIONS.pdf", "APPLICATION_GUIDE.pdf", "CALIBRATION.md",
                                      "APPLICATION_REPORT.md", "NEW_DATA_OVERVIEW.md", "ARF_MERGE_OVERVIEW.md",
                                      "calibration_fit.csv", "figures/validation.png"], fill=colors.white, stroke=muted)
    arrow([(bx + bw, 192), (359, 225)])
    arrow([(bx + bw, 266), (359, 262)])
    return d


# ----------------------------------------------------------------------------- content
def story():
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    tests = test_counts()
    n_tests = sum(n for _, n in tests)
    P = eqpdf.P
    out = []

    # ---- title page
    out += [Spacer(1, 5 * cm),
            para("Application Guide", ParagraphStyle("t", parent=H1, fontSize=30, alignment=TA_CENTER, leading=36)),
            para("Oostvaardersplassen population model: what the application does, how it is built, how it has "
                 "changed so far, and the decisions behind it",
                 ParagraphStyle("st", parent=BODY, fontSize=13, leading=17, textColor=BLUE, alignment=TA_CENTER)),
            Spacer(1, 1.2 * cm),
            para("Project Application Development, Year 2, Semester 1 (2026-2027)",
                 ParagraphStyle("c", parent=BODY, alignment=TA_CENTER)),
            para(f"Status {date.today().isoformat()}: working tree on top of commit {commit}. Built by "
                 f"{code('scripts/build_application_guide_pdf.py')}. Equations are not explained here: every model "
                 f"points to its equation numbers and pages in {code('docs/MODEL_EQUATIONS.pdf')} ({ME}, "
                 f"{IDX['pages']} pages), which is rebuilt together with this guide.", CAPTION),
            Spacer(1, 1.4 * cm),
            table([["Section", "Contents", "Page"],
                   ["1", "Purpose: the client, the research questions and what the application must deliver", PG("1")],
                   ["2", "Using the application: GUI, command line, scripts", PG("2")],
                   ["3", "Architecture: layers, how a run flows, design rules", PG("3")],
                   ["4", "The models, with references to the equations", PG("4")],
                   ["5", "Data: sources, cleaning rules, files", PG("5")],
                   ["6", "Verification, calibration and validation", PG("6")],
                   ["7", "Change history", PG("7")],
                   ["8", "Decisions and the reasons behind them", PG("8")],
                   ["9", "Limitations, open questions and next steps", PG("9")],
                   ["A", "Repository map", PG("A")]], [1.6, 13.4, 1.4]),
            PageBreak()]

    # ---- 1 purpose
    out += [para("1. Purpose", H1),
            para("Staatsbosbeheer manages the Oostvaardersplassen, a fenced nature reserve of about 5,600 ha in "
                 "Flevoland with Heck cattle, Konik horses and red deer and no large predators. After the mass die-off "
                 "of winter 2017-18 the chosen policy is a herd of 1,100 animals: 500 deer and 600 cattle and horses "
                 "together. The project brief asks three research questions:"),
            table([["", "Research question (project brief §2.4)"],
                   ["A", "How stable is the situation of 1,100 animals (500 deer and 600 cattle and horses together)?"],
                   ["B", "What will happen to the deer, cattle and horses if several grey wolves are released (the number "
                    "of wolves being the free variable)?"],
                   ["C", "What is the effect of a rise in overall temperature (or climate change in general), and how "
                    "much rise forces Staatsbosbeheer into a really different policy?"]], [1.0, 15.4]),
            Spacer(1, 4),
            para("The client wants an <b>indication</b>, not a precise forecast, so the application uses simple, "
                 "explainable models whose every choice can be traced to a source: Gotelli, <i>A Primer of "
                 "Ecology</i>, the project brief, or the data. The application is graded together with a research "
                 "report."),
            para("1.1 What the application must deliver", H2),
            table([["Requirement (brief §2.5.2, §2.6)", "How the application meets it"],
                   ["Use the models to show the future populations, as numbers and graphically",
                    "Line chart of every population over time, legend with final values, CSV export; headless runs "
                    "print CSV"],
                   ["Options to change parameters: initial population sizes", "Spinners for cattle, horses, deer; "
                    "\"Policy target (1,100)\" button"],
                   ["... the number of grey wolves to release", "\"Wolves released\" (model 4)"],
                   ["... assumptions on the preferred prey of the wolves", "Prey preference per species, 0 to 1 (model 4)"],
                   ["Work in iterations, start simple", "Four models from logistic growth to wolves and grass "
                    "(Section 4); each selectable"],
                   ["Make sure the application can be modified easily; not monolithic",
                    "Layers with one interface per extension point; a new model is one class plus one registry line "
                    "(Section 3.4)"],
                   ["Take the data", "Cleaned course data and KNMI climate data; observed counts as dots on the chart; "
                    "replay of history with the known culls"],
                   ["Documentation for the team that takes over", f"README, this guide, {ME}, calibration and data "
                    "notes (Appendix A)"]], [6.0, 10.4]),
            para("1.2 Assessment criteria for the product (brief §2.9.2)", H2),
            table([["#", "Criterion", "Where", "Status"],
                   ["1", "Population growth including food supply", f"Models 1-3; grass explicit in model 3 "
                    f"({SEC('5')})", "Done; model 3 not calibrated"],
                   ["2", "Interaction between large herbivores", f"Model 2 ({SEC('4')}); model 3 through shared grass",
                    "Done, fitted (model 2)"],
                   ["3", "Prey-predator interactions", f"Model 4 ({SEC('6')})", "Done; kill rates still guesses"],
                   ["4", "Stakeholder needs in UML and use cases", "Not in the code base", "Not started"],
                   ["5", "Architecture in UML", "Section 3 of this guide is the starting point", "Not started"],
                   ["6", "Implementation of the mathematical models", f"Sections 3-4; {n_tests} tests", "Done"],
                   ["7", "Implementation of prioritised use cases", "GUI and CLI (Section 2)",
                    "Done; GUI not yet clicked through by hand"],
                   ["8", "Final report with conclusions", "Separate document", "Not started"]],
                  [0.7, 5.4, 6.5, 3.8]),
            PageBreak()]

    # ---- 2 using
    out += [para("2. Using the application", H1),
            para("Requirements: JDK 17 or newer and Maven. Python 3 (pandas, scipy, matplotlib, reportlab) is only "
                 "needed for the data and documentation scripts."),
            table([["Command (in the repository root)", "What it does"],
                   [code("mvn test"), f"Compiles and runs all {n_tests} JUnit 5 tests"],
                   [code("mvn package"), f"Builds {code('target/app.jar')}"],
                   [code("java -jar target/app.jar"), "Starts the GUI"],
                   [code("java -jar target/app.jar --cli [flags]"), "Runs one simulation headless, CSV on standard output"]],
                  [7.0, 9.4]),
            para("2.1 The graphical interface", H2),
            para("The window has the inputs on the left and the chart on the right; the three buttons stay visible "
                 "below the inputs. A run starts with <b>Run simulation</b> (or Enter) and happens in the background, "
                 "so the window never freezes; an error appears as a message, not a crash. The chart title shows the "
                 "model, the solver, the number of wolves and ΔT."),
            table([["Input", "Range (default)", "Used by"],
                   ["Model", "4 models (model 4, predator-prey)", "-"],
                   ["Solver", "Runge-Kutta 4 or Euler (RK4)", "all"],
                   ["Years", "1-200 (20)", "all"],
                   ["Initial cattle / horses / deer", "0-100,000 (300 / 300 / 500 = policy target)", "all"],
                   ["Wolves released", "0-500 (0)", "model 4"],
                   ["Prey preference - cattle / horses / deer", "0-1 in steps of 0.05 (1)", "model 4"],
                   ["Temperature rise (°C)", "−2 to +6 in steps of 0.5 (0)", "models 2, 3, 4"],
                   ["Grazing area (ha)", f"10-10,000 ({fmt(P['Ag'])})", "model 3"],
                   ["K per species (sliders)", "0-10,000 (fitted values)", "models 1, 2, 4"],
                   ["Competition α, six sliders", "0-2 (fitted values; diagonal fixed at 1)", "models 2, 4"],
                   ["Reset K and α to defaults", "button", "-"],
                   ["Show observed counts, overlay start year", "check box; 1900-2100 (1983)", "chart"],
                   ["Run simulation / Policy target (1,100) / Export CSV", "buttons; export after a run", "-"]],
                  [6.4, 6.6, 3.4]),
            para("The chart draws one line per population with a colour-blind-safe palette (Okabe and Ito), "
                 "auto-scaled axes and a legend with each final value. Grass (model 3, in tonnes) is not drawn on the "
                 "animal axis: its final value is listed in grey and the full series is in the CSV export. With "
                 "<b>Show observed counts</b> the herd counts appear as dots, placed using the overlay start year as "
                 "t = 0."),
            para("2.2 Command line", H2),
            table([["Flag", "Meaning (default)"],
                   [code("--model N"), "Counts from 0, so --model N is model N+1 of the dropdown: 0 logistic, 1 competition, "
                    "2 seasonal grazing, 3 predator-prey (default 3)"],
                   [code("--wolves N"), "Wolves released at t = 0 (0); only predator-prey (--model 3) uses it"],
                   [code("--years N"), "Horizon in years (20)"],
                   [code("--dt X"), "Output step in years (1/12); seasonal grazing (--model 2) still steps about daily inside"],
                   [code("--replay YEAR"), "Start from the counts of YEAR and apply the known culls, relocations, "
                    "introductions and die-off. Built for the competition model; not suited to seasonal grazing yet "
                    "(Section 9)"]], [3.4, 13.0]),
            para(f"Output: a header {code('t,Cattle,Horses,Deer[,Wolves | ,Grass (t DM)]')} and one row per output "
                 f"step. Example: {code('java -jar target/app.jar --cli --model 1 --years 50')}. Other inputs (ΔT, "
                 "initial numbers, area) are not command-line flags yet; the run-scenario skill adds them when a sweep "
                 "needs them."),
            para("2.3 Scripts", H2),
            table([["Script", "Input → output", "Purpose"],
                   [code("clean_data.py"), "data/raw/*.xlsx → data/clean/*.csv, corrections.csv",
                    "Cleans the course data; logs every change"],
                   [code("clean_climate.py"), "data/raw/knmi → climate_monthly.csv",
                    "KNMI monthly series, checked against the daily files"],
                   [code("fit_temperature_profile.py"), "climate_monthly.csv → printed fit",
                    "Mean temperature and amplitude for the grass model"],
                   [code("fit_parameters.py"), "herbivores_counts.csv → docs/calibration_fit.csv",
                    "Fits r, K and α of model 2"],
                   [code("plot_validation.py"), "app.jar → docs/figures/validation.png",
                    "Model 2 against the counts, run through the app itself"],
                   [code("build_model_equations_pdf.py"), "sources, app.jar → docs/MODEL_EQUATIONS.pdf",
                    "Every equation, numbers computed from the code"],
                   [code("build_application_guide_pdf.py"), "→ docs/APPLICATION_GUIDE.pdf (and the above)",
                    "This guide"]], [6.0, 5.6, 4.8]),
            PageBreak()]

    # ---- 3 architecture
    out += [para("3. Architecture", H1),
            para(f"A Maven project, base package {code('nl.ovp')}, in five layers. Each layer only uses layers below it: "
                 "app → ui → solver and data → model. The model layer depends on nothing else, so the equations can "
                 "be tested, and reused by another interface, without the GUI."),
            architecture_diagram(),
            para("Arrows inside the application mean \"uses\"; app also calls data (--replay) and solver (--cli) directly. "
                 "The Python scripts run offline; Java only reads their output in data/clean.", CAPTION),
            para("3.1 The layers", H2),
            table([["Package", "Classes", "Responsibility"],
                   [code("app"), "Main", "Entry point: GUI, or a headless run (--cli) that prints CSV; sets up a replay"],
                   [code("ui"), "MainWindow, ParameterPanel, ChartPanel, ValueSlider, SimulationWorker",
                    "Inputs → ModelParameters; runs the simulation in the background; draws the chart; exports CSV"],
                   [code("solver"), "OdeSolver, EulerSolver, RungeKutta4Solver, Simulator, SimulationResult",
                    "Steps any model forward in time; internal steps; extinction clamp; result as a table"],
                   [code("model"), "PopulationModel, LogisticModel, CompetitionModel, SeasonalGrazingModel, "
                    "PredatorPreyModel, GrassModel, ModelParameters, ModelRegistry, ManagementEvent, Species",
                    "The equations and every number they use"],
                   [code("data"), "CsvDataLoader, HerbivoreCount, GrassHeightObservation, ClimateObservation, WolfRates",
                    "Reads data/clean/*.csv by column name into records; empty cells become null, not 0"]],
                  [1.8, 6.6, 8.0]),
            para("3.2 How a run flows", H2),
            table([["Step", "What happens"],
                   ["1", f"{code('ParameterPanel.buildParameters()')} copies every input into a fresh "
                    f"{code('ModelParameters')}; the chosen model comes from {code('ModelRegistry')}."],
                   ["2", f"{code('SimulationWorker')} (a SwingWorker) calls {code('Simulator.run(model, solver, p)')} off "
                    "the event thread."],
                   ["3", f"The simulator asks the model for y(0) ({code('initialState')}), then repeats: "
                    f"{code('solver.step')} calls {code('model.derivatives(t, y, p)')} (four times for RK4), clamps "
                    "negative values to 0, and records one row per output step Δt."],
                   ["4", f"The {code('SimulationResult')} goes back to the event thread: {code('ChartPanel')} draws it and "
                    "Export CSV is enabled. In --cli mode it is printed as CSV instead."]], [1.2, 15.2]),
            para("3.3 Design rules", H2),
            table([["Rule", "Why"],
                   ["State vector order is fixed: cattle, horses, deer, then wolves or grass; it equals "
                    "Species.ordinal()", "Every per-species array in ModelParameters is indexed the same way, so a "
                    "model, the GUI and the tests can never mix up species"],
                   ["All tunable numbers live in ModelParameters; models are stateless; copy() is a deep copy",
                    "One calibration is shared by all models; the GUI can bind generically; what-if runs can branch "
                    "from one parameter set without interfering"],
                   ["derivatives() returns a new array and never changes y", "Solvers evaluate it several times per "
                    "step; changing y would corrupt RK4"],
                   ["New models are registered only in ModelRegistry; the most general model is last",
                    "The GUI dropdown and --model pick them up; the default model is the one where --wolves works"],
                   ["Simulations never run on the event thread", "The window stays responsive; errors become dialogs"],
                   ["No runtime dependencies (JUnit only, for tests); the chart is hand-drawn",
                    "Builds anywhere with only a JDK and Maven; easy hand-over; full control of the chart"],
                   ["Java reads only data/clean/*.csv, by column name", "Raw data are never changed; extra columns "
                    "(reliable, note, period) do not break the readers"],
                   ["Unvalidated numbers carry // TODO: fit/look up; replaced values carry their provenance",
                    "Every number in the report can be traced to a fit, a source or the brief"]], [7.2, 9.2]),
            para("3.4 Extending the application", H2),
            para(f"A new model: implement {code('PopulationModel')} (equation and source in the class Javadoc), add its "
                 f"parameters to {code('ModelParameters')} and its copy constructor, register it in "
                 f"{code('ModelRegistry')}, and add a test with a limiting case that reduces it to a tested model. "
                 f"If it needs small time steps it declares {code('maxStepYears()')}; the simulator handles the rest. "
                 f"A new solver implements {code('OdeSolver')}; a new data file gets a reader in "
                 f"{code('CsvDataLoader')} and is produced by a script in {code('scripts/')}."),
            PageBreak()]

    # ---- 4 models
    out += [para("4. The models", H1),
            para(f"The equations, their meaning and the line numbers in the code are in {ME}. This section only says "
                 "what each model is for and where to find it."),
            table([["Model (dropdown / --model)", "State", "Adds", "Question", f"Equations in {ME}"],
                   ["1. Logistic (0)", "cattle, horses, deer", "Growth limited by a carrying capacity, species alone",
                    "baseline", f"{EQ('logistic', 'logistic_safety')} ({SEC('2')})"],
                   ["2. Competition (1)", "cattle, horses, deer", "Competition for grass (fitted α), climate through "
                    "the grass factor, management events", "A, C; validation",
                    f"{EQ('competition', 'equilibrium')} ({SEC('4')})"],
                   ["3. Seasonal grazing (2)", "cattle, horses, deer, grass", "Grass as a stock that is eaten; "
                    "temperature-driven growing season; births in summer, starvation in winter",
                    "A, C with explicit food; winter die-offs", f"{EQ('calendar', 'grazer_ode')} ({SEC('5')})"],
                   ["4. Predator-prey (3, default)", "cattle, horses, deer, wolves", "Model 2 plus wolves "
                    "(multi-prey Holling type II, prey preference)", "B", f"{EQ('kills', 'wolf_growth')} ({SEC('6')})"]],
                  [3.0, 2.6, 4.6, 2.2, 4.0]),
            Spacer(1, 6),
            table([["Shared part", "Used by", f"In {ME}"],
                   ["Grass growth potential (brief Appendix 3) and the temperature curve", "2 (ratio g(ΔT)), 3 (season)",
                    f"{EQ('temperature', 'grass_factor')} ({SEC('3')})"],
                   ["Climate sensitivity per species (warming helps horses, harms cattle)", "2, 4 (on K); 3 (on births)",
                    f"{EQ('k_prime')}; {EQ('climate_births')}"],
                   ["Management events: culls, relocations, introductions, die-off", "2, 3, 4", EQ("mgmt")],
                   ["Solvers: Euler, RK4, internal steps, extinction clamp", "all", f"{EQ('euler', 'clamp')} ({SEC('7')})"],
                   ["Every parameter with value, unit, status and source", "all", SEC("8")],
                   ["Points to check before the report", "-", SEC("9")]], [7.4, 3.8, 5.2]),
            Spacer(1, 6),
            para("<b>How the models relate.</b> Models 1, 2 and 4 are nested: with one species model 2 is model 1, "
                 "and with zero wolves model 4 is model 2 (a test checks the second exactly). Model 3 is an "
                 "alternative to model 2 for the herbivores: they compete through a shared grass stock instead of "
                 "through fitted coefficients. Comparing the two is part of the report's conceptual model evaluation. "
                 "Model 3 was built fourth but is listed third, so that the most general model (4) stays the default."),
            para("<b>What the models say so far.</b> Model 2 (calibrated): left alone, the policy target grows to about "
                 f"{fmt(round(sum(eqpdf.cli('--model', '1', '--years', '200')[1:4]), -2))} animals and cattle are slowly squeezed out ({SEC('4.4')}), so 1,100 is not an equilibrium and "
                 "can only be held by yearly removals. Model 3 (provisional parameters): on today's 1,080 ha the target "
                 f"grows past the 1,500 winter ceiling after about {ceiling_years():.0f} years, and starting from the October 2017 herd it "
                 f"reproduces a winter die-off of about the observed size without being told about it ({SEC('5.3')}). "
                 f"Model 4: with the current guesses for the kill rates, released wolves die out ({SEC('6.3')}). None of "
                 "this is a final answer yet: see Section 9."),
            PageBreak()]

    # ---- 5 data
    data_rows = [
        ("herbivores_counts.csv", "Animals per species per year, 1983-2025, with reliable flag and period",
         "Moodle course data", "CsvDataLoader; fit, validation, overlay, replay"),
        ("herbivores_dynamics.csv", "Counts, births, deaths and balance gap per species and year",
         "Moodle course data", "Data checks (fit on counts instead)"),
        ("grass_height.csv", "Grass height on 1 August, 1990-2014", "Moodle course data", "CsvDataLoader"),
        ("herbivore_events.csv", "Introductions, culls, relocation, 2017-18 die-off as signed numbers with windows",
         "Footnotes of the course data; NOS", "Management events, --replay"),
        ("winter_mortality_nos.csv", "NOS winter deaths 2010-11 to 2017-18 next to the Moodle deaths", "NOS",
         "Explains the balance gap; validation target for model 3"),
        ("wolves.csv", "Wolves per region and year, 2010-2025", "Moodle (reference area, not the reserve)",
         "Wolf rates"),
        ("wolf_area_prey.csv", "Deer, grass biomass and deer weight in the wolf area", "Moodle (reference area)",
         "Order of magnitude only"),
        ("wolf_rates.csv", "Pups, deaths and lost wolves per wolf per year (mean, SD)", "Derived from wolves.csv",
         "Wolf mortality m = 0.23"),
        ("climate_monthly.csv", "Monthly temperature, rain and evaporation, 1983-2025", "KNMI (Lelystad, De Bilt)",
         "Temperature profile fit"),
        ("corrections.csv", "Every value changed or flagged during cleaning", "clean_data.py", "Audit trail"),
    ]
    out += [para("5. Data", H1),
            para("The course data are \"for education purposes only, do not distribute\". Raw files are never edited: "
                 "Python scripts produce data/clean, and Java reads only that folder."),
            table([["File (data/clean)", "Rows", "Content", "Source", "Used by"]] +
                  [[code(f), str(csv_rows(f)), c, s_, u] for f, c, s_, u in data_rows], [3.9, 1.1, 5.0, 3.1, 3.3]),
            para("5.1 Cleaning rules", H2),
            table([["Rule", "Reason"],
                   ["Nothing is imputed: a missing or impossible value becomes an empty cell and is logged",
                    "Interpolation is a modelling decision that has to be justified in the report, not hidden in "
                    "cleaning"],
                   ["Species not yet present are empty, not 0 (horses before 1984, deer before 1992)",
                    "A zero would be a wrong observation"],
                   ["Counts 2016-2024 are kept but flagged reliable = False", "The source marks them \"not always 100% "
                    "trustworthy\""],
                   ["Natural dynamics are fitted on 1983-2017 only (period column)", "From winter 2017-18 on there is "
                    "a die-off, culling and relocation"],
                   ["Fit on counts, not on the birth and death columns", "Births and deaths do not explain the change in "
                    "counts (deer: +4,630 unexplained over 2005-2013), and the NOS figures suggest the Moodle deaths "
                    "for 2010-2013 are too high"],
                   ["The wolf data are from another area", "Used only for per-wolf rates and orders of magnitude"],
                   ["KNMI series are used for the average seasonal cycle, not for trends", "KNMI warns these station "
                    "series are not homogenised"]], [7.6, 8.8]),
            para("Full details: data/README.md. The course spreadsheets themselves (data/raw/*.xlsx) are not yet in "
                 "the repository, so clean_data.py cannot be re-run from the repository alone.", SMALL),
            PageBreak()]

    # ---- 6 verification
    what = {"MainTest": "--replay starts from the observed counts and loads the events; absent species start at 0",
            "CsvDataLoaderTest": "Parsing of every CSV (synthetic and real files); empty cells as null; wolf "
                                 "mortality default matches wolf_rates.csv",
            "CompetitionModelTest": "Management events: window, single species, shared die-off, nothing removed "
                                    "from extinct species, exact cull size, introductions",
            "GrassModelTest": "Temperature defaults match the KNMI fit; grass factor = 1 without warming",
            "ModelParametersTest": "copy() is independent (also the new model 3 fields); policy-target defaults; "
                                   "events",
            "PredatorPreyModelTest": "Zero wolves reduces exactly to model 2; wolves reduce prey",
            "SeasonalGrazingModelTest": "Grass seasonal and bounded; non-negative for 50 years; absent species "
                                        "stay absent; decline without grass; grass eaten = intake; event flow equals "
                                        "model 2; winter die-off; area and warming effects; calendar start; "
                                        "independent of the output step",
            "RungeKutta4SolverTest": "RK4 matches the exact logistic solution",
            "SimulatorTest": "Extinction clamp; one row per output step; internal steps are taken",
            "ParameterPanelTest": "Sliders start at the defaults and reach ModelParameters; reset; grazing area"}
    out += [para("6. Verification, calibration and validation", H1),
            para("<b>Verification</b> checks that the code computes the equations correctly; <b>validation</b> checks "
                 f"the model against reality. All {n_tests} tests run with {code('mvn test')} and must pass before every "
                 "commit."),
            table([["Test class", "Tests", "What it checks"]] +
                  [[code(n), str(c), what.get(n, "")] for n, c in tests], [4.6, 1.2, 10.6]),
            para("6.1 Calibration and validation", H2),
            para(f"Model 2 is fitted to the 1983-2015 counts (R² 0.95 / 0.98 / 0.97 for cattle / horses / deer); "
                 f"its replay of 2018-2025 is poor, for reasons in the data rather than clearly in the model "
                 f"({ME} {SEC('8.1')} and {SEC('8.2')}; docs/CALIBRATION.md). The temperature profile is fitted to "
                 "KNMI data; wolf mortality comes from the reference-area data. Model 3 and the wolf kill rates are not "
                 "calibrated yet."),
            PageBreak()]

    # ---- 7 history
    log = git_log()
    what_commit = {
        "First commit": "The application as designed: the five layers; models 1, 2 and 4 with grass model; Euler and "
                        "RK4; Swing GUI with parameter panel, chart, observed-count overlay and CSV export; --cli; "
                        "CsvDataLoader for counts and grass height; clean_data.py; six test classes. All growth, "
                        "competition and predation numbers were placeholders.",
    }
    rows = []
    for h, d_, s_ in log:
        if s_ == "First commit":
            rows.append([f"{code(h)}<br/>{d_}", what_commit["First commit"]])
        else:
            rows.append([f"{code(h)}<br/>{d_}",
                         "<b>Data, calibration and history.</b> KNMI climate data cleaned and checked against the daily "
                         "files (clean_climate.py); temperature profile fitted (9.96 °C, 7.39 °C). The group's herbivore "
                         "and wolf cleaning scripts merged into clean_data.py, without their zero-filling and "
                         "interpolation: new herbivore_events.csv, winter_mortality_nos.csv, wolf_rates.csv. Management "
                         "events (ManagementEvent, M<sub>i</sub>(t)) and --replay YEAR. Model 2 calibrated "
                         "(fit_parameters.py, constrained α); validation figure; wolf mortality 0.23 from data. "
                         "MODEL_EQUATIONS.pdf builder. New tests for the CLI, events, grass model and data readers."])
    rows.append(["Working tree<br/>(not committed yet)<br/>" + date.today().isoformat(),
                 "<b>Merge with AgriculturalRiskFactors.</b> Comparison of the two projects "
                 "(docs/ARF_MERGE_OVERVIEW.md), including the evidence that the counts are autumn counts and the doubt "
                 "about the unit of the brief's grass yield. New model 3, SeasonalGrazingModel, adapted from ARF's "
                 "GrazerModel with the brief's temperature-driven growth. Simulator: internal steps "
                 "(PopulationModel.maxStepYears). Seasons follow calendar time. GUI: grazing-area input; grass left out "
                 "of the chart. 17 new tests. README, APPLICATION_REPORT, CLAUDE.md and skills updated. "
                 "MODEL_EQUATIONS.pdf rewritten (four models, numbering checked in two passes, page index) and this "
                 "guide added."])
    out += [para("7. Change history", H1),
            para("The git log is a graded deliverable. Development moved to this GitHub repository "
                 "(Kornelkovacs/ProjectAppDevelopment); the earlier GitLab repository is no longer maintained."),
            table([["Commit, date", "What changed"]] + rows, [3.4, 13.0]),
            Spacer(1, 6),
            para("Supporting notes written along the way, in docs/: APPLICATION_REPORT.md (status and open tasks), "
                 "NEW_DATA_OVERVIEW.md (what the group's new data files add), CALIBRATION.md (fit and validation), "
                 "ARF_MERGE_OVERVIEW.md (comparison with AgriculturalRiskFactors and merge options).", SMALL),
            PageBreak()]

    # ---- 8 decisions
    def dtable(rows_):
        return table([["Decision", "Instead of", "Why"]] + rows_, [5.0, 4.2, 7.2])

    out += [para("8. Decisions and the reasons behind them", H1),
            para(f"Each decision is listed with the obvious alternative and the reason for the choice. Where a decision is about an "
                 f"equation, the reference points to {ME}."),
            para("8.1 Application and architecture", H2),
            dtable([["Java 17 desktop application (Maven, Swing), no runtime dependencies; chart drawn with Java2D",
                     "JavaFX; JFreeChart; a web or Python app", "Runs anywhere with a JDK; nothing to install for the "
                     "next team; full control over the chart (palette, observed dots, legend)"],
                    ["Five layers with one interface per extension point (PopulationModel, OdeSolver) and a registry",
                     "One program with the models built into the GUI", "The brief asks for an application that can be "
                     "modified easily and is not monolithic; a new model never touches the solver or the GUI"],
                    ["All parameters in one ModelParameters object with a deep copy", "Parameters per model class",
                     "One calibration shared by every model; generic GUI binding; independent what-if runs"],
                    ["Simulations in a background worker; errors as dialogs", "Run on the event thread",
                     "Long runs (small steps, 200 years) never freeze the window"],
                    ["A headless --cli mode that prints CSV", "GUI only", "Sweeps for the report and figures are made "
                     "by the application itself, so figures show exactly what the app computes"],
                    ["Equation documents generated from the code", "Hand-written document", "Numbers are read from the "
                     "sources and the jar, so the documentation cannot drift from the code"]]),
            para("8.2 Mathematics", H2),
            dtable([["Equation-based models (ODEs)", "Agent-based simulation of every animal", "The brief: formulas "
                     "are good enough for decision making; the client wants an indication; easier to explain"],
                    ["Iterations: logistic → competition → predator-prey, each one tested against the previous",
                     "One large model", f"The brief asks to start simple and extend; Gotelli ch. 2, 5, 6 "
                     f"({EQ('logistic')}, {EQ('competition')}, {EQ('kills')})"],
                    ["RK4 as default, Euler kept; monthly output step", "Euler only; adaptive step", f"RK4 is accurate "
                     f"at monthly steps; Euler stays for the accuracy comparison in the report ({SEC('7')})"],
                    ["Negative or NaN populations set to 0 (extinct)", "Allow negative values; stop the run",
                     f"A population cannot be negative and cannot reappear from nothing ({EQ('clamp')})"],
                    ["Climate through the brief's grass growth potential plus a sensitivity per species",
                     "Temperature directly on growth rates", f"Follows Appendix 3 of the brief; signs of the "
                     f"sensitivities are fixed by the brief ({EQ('k_prime')})"],
                    ["Wolves hunt all prey at once (multi-prey Holling type II) with a preference per species",
                     "Separate predator-prey pairs; type I response", f"Wolves are limited by handling time; the brief "
                     f"suggests prey preference as a user option ({EQ('kills')})"],
                    ["Known events as a flow spread evenly over their window; a die-off of all species is shared in "
                     "proportion to their numbers", "Sudden jumps in the state", f"Smooth for the solver; the source gives "
                     f"no split or months ({EQ('mgmt')})"]]),
            para("8.3 Data and calibration", H2),
            dtable([["Nothing imputed; every correction logged in corrections.csv", "Fill gaps with 0 or by "
                     "interpolation", "Interpolation is a modelling choice to justify in the report"],
                    ["Fit on the counts, 1983-2015 (reliable, natural period); 2016-17 only as a sensitivity check",
                     "Fit on births and deaths; include 2016-2025", "Births and deaths do not balance; from 2017-18 on "
                     "the herds are managed; 2016-2024 are low-trust"],
                    ["Least squares on log counts", "Plain least squares", "Otherwise the deer (thousands) swamp the "
                     "cattle (hundreds)"],
                    ["Two shared competition coefficients (a, b); deer effect 0.3 fixed", "Four free coefficients",
                     f"Four are not identifiable (values on their bounds, SE larger than K); 0.3 is fixed by the brief "
                     f"({SEC('4.2')})"],
                    ["Temperature profile fitted on KNMI 1983-2017", "Textbook values", "Same window as the herd fit, so "
                     "ΔT = 0 means the climate in which the herds were observed"],
                    ["Wolf mortality 0.23 = recorded deaths + wolves lost (dispersal)", "Deaths only", "The reserve is "
                     "much smaller than a pack's range, so dispersing wolves leave"],
                    ["The group's cleaning scripts merged into clean_data.py", "Add their output files next to ours",
                     "One source of truth; both cleanings agree on every count"],
                    ["Rain and evaporation in the equations deferred; geese out of scope", "Model them now",
                     "Keep it simple (brief); first get temperature and food right"]]),
            para("8.4 Merging AgriculturalRiskFactors (model 3)", H2),
            dtable([["Port ARF's ideas into our architecture", "Import ARF's code base", "Its solver layer duplicates "
                     "ours and its state order breaks our invariants; we keep the GUI, data, calibration and wolves"],
                    ["Keep ARF's logistic grass but drive it with the brief's growth potential GP(T(t)) (option a)",
                     "Use the brief's yield formula directly (option b)", "Read per month, the brief's yield could not "
                     "have fed the observed herds; GP used as a 0-1 shape avoids the doubtful unit "
                     f"({EQ('grass_ode')})"],
                    ["GP for grass growth and die-back; a calendar season for births and starvation", "GP in all four "
                     "terms", "Breeding is timed by day length; GP for births would add 16-43% births under warming "
                     f"without a source ({EQ('season')}, {EQ('grazer_ode')})"],
                    ["Climate effect on births with the same sensitivities as model 2", "On mortality; leave it out",
                     f"Model 3 has no K per species; reusing s<sub>i</sub> keeps one value across models "
                     f"({EQ('climate_births')})"],
                    ["Grazing area as a separate parameter, 1,080 ha; 1,880 ha for fits on 1983-2017",
                     "The brief's 5,600 ha", "Van Geel Committee (2018): the grassland left today; 5,600 ha includes "
                     "3,600 ha of wetland"],
                    ["One shared grass pool, exclusion checked after calibration", "Add α on top; add browse for deer",
                     "α on top counts competition twice; browse adds parameters without data"],
                    ["ARF's provisional values as defaults, marked TODO", "Calibrate during the merge", "Keep the merge "
                     "and the calibration as separate, reviewable steps"],
                    ["Model 3 listed before predator-prey", "Append it last", "The default model and --wolves keep "
                     "working; the most general model stays last"],
                    ["Internal solver steps declared by the model", "A daily step for every model", "Monthly RK4 is about "
                     f"2% off for model 3; output size and the other models stay unchanged ({EQ('substep')})"],
                    ["Seasons follow calendar time (startYear + t)", "Time of year from t only", f"Allows a 1 October "
                     f"start, matching autumn counts ({EQ('calendar')})"],
                    ["Grass not drawn on the animal chart", "A second axis", "Different unit; the value is in the legend "
                     "and the CSV"]]),
            PageBreak()]

    # ---- 9 limitations
    out += [para("9. Limitations, open questions and next steps", H1),
            para(f"The modelling points to check before the report (eleven items) are in {ME} {SEC('9')}. The most "
                 "important for the application:"),
            table([["#", "Open point", "Next step"],
                   ["1", "Model 3 is not calibrated; its long run excludes cattle, opposite to model 2 and the data",
                    "Fit births, deaths and grass constants on 1983-2015 at 1,880 ha; check winter deaths against NOS and "
                    "2017-18"],
                   ["2", "--replay is not suited to model 3 (die-off counted twice, 1 January start, 1,080 ha)",
                    "Decide the count date, the area over time and whether the die-off is an input; then adapt the replay"],
                   ["3", "Wolf kill rates and conversion are guesses; released wolves always die out", "Literature values "
                    "(e.g. Jędrzejewski et al.); later put the wolves on top of model 3"],
                   ["4", "Climate only through temperature", "KNMI'23 scenarios as named ΔT presets; drought via "
                    "precipitation and evaporation (data in ARF)"],
                   ["5", "No GUI click-through test yet", "Click through every control once and record it"],
                   ["6", "UML deliverables (criteria 4-5) not started", "Use case diagram and descriptions; component "
                    "and class diagrams based on Section 3"],
                   ["7", "Course spreadsheets not in data/raw", "Add them and check that clean_data.py reproduces "
                    "data/clean"],
                   ["8", "Repository hygiene: target/ (build output), the Gotelli textbook PDF and ProjectDescription.pdf "
                    "are tracked in git", "Add target/ to the repository's .gitignore; decide about the PDFs (the "
                    "textbook is copyrighted)"]], [0.7, 7.3, 8.4]),
            para("9.1 Questions for the lecturer or Staatsbosbeheer", H2),
            table([["Question", "Why it matters"],
                   ["When in the year are the herd counts made?", "The 2017 count equals the October 2017 figure of the "
                    "Van Geel Committee; it moves every replay"],
                   ["What is the grazing area today, and what does it produce per hectare?", "Model 3 depends on it "
                    "directly"],
                   ["Is the brief's 60 kg/ha of grass per month or per day?", "Per month cannot feed the observed herds"],
                   ["What counts as \"stable\": a number, a range, or staying under the 1,500 winter ceiling?",
                    "Defines the answer to question A"],
                   ["May the wolf rates of the reference area be used for the reserve?", "Basis of the wolf mortality"],
                   ["Should the 2017-18 die-off (89% shot) count as natural mortality or management?",
                    "Decides whether it is an input or a validation target"]], [8.0, 8.4]),
            PageBreak()]

    # ---- appendix
    tree = [("pom.xml, README.md, ideas.md", "Build file, overview, idea list"),
            ("src/main/java/nl/ovp/app", "Main"),
            ("src/main/java/nl/ovp/ui", "Swing GUI"),
            ("src/main/java/nl/ovp/solver", "Solvers and simulator"),
            ("src/main/java/nl/ovp/model", "Models and parameters"),
            ("src/main/java/nl/ovp/data", "CSV readers and records"),
            ("src/test/java/nl/ovp/...", f"{n_tests} JUnit 5 tests, same layout as main"),
            ("data/raw/knmi", "KNMI climate files"),
            ("data/clean", "Cleaned CSVs (the only data Java reads); data/README.md documents every correction"),
            ("scripts", "Cleaning, fitting, validation figure, PDF builders"),
            ("docs/MODEL_EQUATIONS.pdf", "Every equation, its meaning and its place in the code"),
            ("docs/APPLICATION_GUIDE.pdf", "This guide"),
            ("docs/*.md, docs/calibration_fit.csv, docs/figures", "Status, calibration, data and merge notes; figures"),
            ("../.claude (outside the repo)", "Instructions and skills for the coding assistant (add-model, "
                                              "run-scenario, calibrate-parameters)")]
    out += [para("A. Repository map", H1),
            table([["Path", "Content"]] + [[code(p_), c_] for p_, c_ in tree], [6.6, 9.8])]
    return out


def _render(target):
    doc = TrackingDoc(target, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                      bottomMargin=2 * cm, title="Application Guide: Oostvaardersplassen population model",
                      author="Oostvaardersplassen project team",
                      subject="The application, its changes and the decisions behind them")
    doc.build(story(), onFirstPage=decorate, onLaterPages=decorate)
    return doc


def build():
    IDX.update(eqpdf.build())                  # rebuild MODEL_EQUATIONS.pdf and take its page index
    first = _render(io.BytesIO())              # pass 1: find this guide's section pages
    PREV_SECTIONS.update(first.sections)
    doc = _render(OUT)                         # pass 2: print them in the contents
    if {k: v["page"] for k, v in doc.sections.items()} != {k: v["page"] for k, v in first.sections.items()}:
        raise SystemExit("section pages changed between passes")
    print(f"Wrote {OUT} ({doc.page} pages)")


if __name__ == "__main__":
    build()
