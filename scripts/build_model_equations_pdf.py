"""
Build docs/MODEL_EQUATIONS.pdf: every formula the application uses, what it means, and where it
lives in the code. Numbers (defaults, grass factors, equilibria, wolf growth, seasonal-model runs) are
computed from the current Java sources and the built jar, so the PDF cannot silently drift from the code.

Usage (from the repository root, after `mvn package` and `python3 scripts/plot_validation.py`):
    python3 scripts/build_model_equations_pdf.py

The document is built twice: the first pass numbers the equations and finds their pages, the second
pass prints the cross-references. build() returns that index (equation numbers and pages, section
pages), which scripts/build_application_guide_pdf.py uses to point at the right pages.

Requires: reportlab, matplotlib, numpy; a JDK (java, jshell) for the model runs.
"""
import functools
import io
import math
import os
import re
import subprocess
from datetime import date

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

OUT = os.path.join("docs", "MODEL_EQUATIONS.pdf")
SRC = os.path.join("src", "main", "java", "nl", "ovp")
NAVY, BLUE, PALE, AMBER_BG, AMBER = (colors.HexColor("#1f3a5f"), colors.HexColor("#2e6da4"),
                                     colors.HexColor("#eef2f7"), colors.HexColor("#fff4e0"),
                                     colors.HexColor("#e69500"))
GREEN = colors.HexColor("#2f8a4a")


# ----------------------------------------------------------------------------- read the code
def java(path):
    with open(os.path.join(SRC, path), encoding="utf-8") as f:
        return f.read()


def line_of(path, pattern, last=False):
    lines_ = java(path).splitlines()
    hits = [i + 1 for i, l in enumerate(lines_) if re.search(pattern, l)]
    if not hits:
        raise SystemExit(f"pattern {pattern!r} not found in {path}")
    return hits[-1] if last else hits[0]


def lines(path, start_pat, end_pat):
    return f"lines {line_of(path, start_pat)}-{line_of(path, end_pat)}"


def array(name):
    m = re.search(rf"double\[\] {name} = \{{(.*?)\}};", java("model/ModelParameters.java"), re.S)
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", m.group(1))
    return [float(v) for v in re.findall(r"-?\d+\.?\d*", body)]


def scalar(name):
    m = re.search(rf"double {name} = (-?[\d.]+)( / [\d.]+)?;", java("model/ModelParameters.java"))
    v = float(m.group(1))
    return v / float(m.group(2)[3:]) if m.group(2) else v


def matrix(name):
    m = re.search(rf"double\[\]\[\] {name} = \{{(.*?)\}};", java("model/ModelParameters.java"), re.S)
    rows = re.findall(r"\{([^{}]*)\}", re.sub(r"/\*.*?\*/|//[^\n]*", "", m.group(1)))
    return np.array([[float(v) for v in re.findall(r"-?\d+\.?\d*", r)] for r in rows])


P = dict(r=array("growthRate"), K=array("carryingCapacity"), alpha=matrix("competitionAlpha"),
         s=array("climateSensitivity"), a=array("attackRate"), w=array("preyPreference"),
         e=array("conversionEfficiency"), h=scalar("handlingTime"), m=scalar("wolfMortality"),
         t0=scalar("grassOptimumTemperature"), var=scalar("grassVar"),
         Tbar=scalar("meanAnnualTemperature"), A=scalar("seasonalAmplitude"),
         Gmax=scalar("grassMaxGrowthKgPerHaPerMonth"), area=scalar("areaHa"),
         N0=[scalar("initialCattle"), scalar("initialHorses"), scalar("initialDeer")],
         start=scalar("startYear"),
         # seasonal grazing model (model 3)
         Ag=scalar("grazingAreaHa"), kG=scalar("grassCapacityTPerHa"), rG=scalar("grassGrowthRate"),
         hG=scalar("grassHalfSaturationTPerHa"), dG=scalar("grassWinterDecay"), G0=scalar("initialGrassFraction"),
         q=array("intake"), b=array("maxBirthRate"), mu=array("backgroundMortality"),
         om=array("winterStarvationMortality"))
MAX_STEP_DAYS = round(1 / eval(re.search(r"MAX_STEP_YEARS = ([^;]+);",
                                         java("model/SeasonalGrazingModel.java")).group(1)))


# ----------------------------------------------------------------------------- the model maths
def temperature(t, dT):
    frac = t - math.floor(t)
    return P["Tbar"] + dT + P["A"] * math.cos(2 * math.pi * (frac - 6.5 / 12))


def gp(T):
    return math.exp(-0.5 * ((T - P["t0"]) / P["var"]) ** 2)


def season(t):
    return 0.5 * (1 - math.cos(2 * math.pi * t))


def annual_yield(dT):
    return sum(gp(temperature(m / 12, dT)) * P["Gmax"] * P["area"] for m in range(12))


def g(dT):
    return annual_yield(dT) / annual_yield(0)


def k_prime(dT):
    return [P["K"][i] * g(dT) * max(0.0, 1 + P["s"][i] * dT) for i in range(3)]


@functools.lru_cache(maxsize=None)
def cli_rows(*args):
    out = subprocess.run(["java", "-jar", "target/app.jar", "--cli", *args],
                         check=True, capture_output=True, text=True).stdout.strip().splitlines()
    return out[0].split(","), [[float(v) for v in row.split(",")] for row in out[1:]]


def cli(*args):
    return cli_rows(*args)[1][-1]


@functools.lru_cache(maxsize=None)
def october_2017_run():
    """Model 3 from the October 2017 herd on the 2017 grazing area, without the die-off event (via jshell)."""
    snippet = """
import nl.ovp.model.*; import nl.ovp.solver.*; import nl.ovp.data.*;
var p = new ModelParameters(); p.startYear = 2017.75; p.initialCattle = 230; p.initialHorses = 1050;
p.initialDeer = 3950; p.grazingAreaHa = 1880; p.initialGrassFraction = 0.15; p.horizonYears = 1; p.dtYears = 1.0 / 12;
p.events = new CsvDataLoader().loadEvents().stream().filter(e -> e.species() != null).toList();
var r = new Simulator().run(new SeasonalGrazingModel(), new RungeKutta4Solver(), p);
for (int k : new int[] {0, 6, 12}) { double[] s = r.states()[k]; System.out.println("ROW " + s[0] + " " + s[1] + " " + s[2] + " " + s[3]); }
/exit
"""
    out = subprocess.run(["jshell", "--class-path", os.path.join("target", "classes"), "-"], input=snippet,
                         check=True, capture_output=True, text=True).stdout
    rows = [[float(v) for v in l.split()[1:]] for l in out.splitlines() if l.startswith("ROW ")]
    if len(rows) != 3:
        raise SystemExit("jshell run of the seasonal model failed:\n" + out)
    return rows  # 1 Oct 2017, 1 Apr 2018, 1 Oct 2018


# ----------------------------------------------------------------------------- styles
ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=10, leading=14,
                      spaceAfter=6)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.5, leading=11)
CAPTION = ParagraphStyle("cap", parent=SMALL, textColor=colors.HexColor("#666666"), alignment=TA_CENTER)
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=19, textColor=NAVY,
                    spaceBefore=4, spaceAfter=10)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=BLUE,
                    spaceBefore=8, spaceAfter=4)
H3 = ParagraphStyle("h3", parent=BODY, fontName="Helvetica-Bold", textColor=NAVY, spaceBefore=6, spaceAfter=2)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=10.5, spaceAfter=0)
CELLH = ParagraphStyle("cellh", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
CODE = "<font face='Courier' color='#1f3a5f'>%s</font>"


def code(s):
    return CODE % s


def para(t, style=BODY):
    return Paragraph(t, style)


def table(rows, widths, header=True, zebra=True):
    data = [[c if not isinstance(c, str) else Paragraph(c, CELLH if (header and r == 0) else CELL)
             for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c4d4")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for r in range(1 if header else 0, len(rows)):
            if r % 2 == 0:
                st.append(("BACKGROUND", (0, r), (-1, r), PALE))
    t.setStyle(TableStyle(st))
    return t


def box(flowables, bg=PALE, bar=BLUE):
    t = Table([[f] for f in flowables], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def note(text):
    return box([para(text)], AMBER_BG, AMBER)


def where(rows):
    return KeepTogether(box([para("<b>Where it is in the code</b>", H3),
                             table([["What", "File and line"]] + rows, [5.6, 10.2])]))


# ----------------------------------------------------------------------------- equation numbering
_EQ = {"n": 0, "num": {}, "prev": {}, "page": {}, "prev_sections": {}}


def E(key):
    """Number of a labelled equation, as found in the previous build pass."""
    return str(_EQ["prev"].get(key, "?"))


def ER(first, last):
    return f"({E(first)})-({E(last)})"


def PG(section):
    """Page of a section, as found in the previous build pass."""
    return str(_EQ["prev_sections"].get(section, {}).get("page", "?"))


def eq(tex, key=None, size=15, number=True):
    """Render a mathtext formula to an image, centred, with an equation number."""
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=size)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight", pad_inches=0.04, transparent=True)
    plt.close(fig)
    buf.seek(0)
    w, h = plt.imread(io.BytesIO(buf.getvalue())).shape[1::-1]
    img = Image(buf, width=w / 300 * 72 * 0.9, height=h / 300 * 72 * 0.9)
    label = ""
    if number:
        _EQ["n"] += 1
        label = f"({_EQ['n']})"
        if key:
            _EQ["num"][key] = _EQ["n"]
    t = Table([["", img, Paragraph(label, ParagraphStyle("n", parent=SMALL, alignment=2))]],
              colWidths=[1.5 * cm, 13.4 * cm, 1.5 * cm])
    t.setStyle(TableStyle([("ALIGN", (1, 0), (1, 0), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    t._eq_key = key if number else None
    return t


def figure(fig, width_cm):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    w, h = plt.imread(io.BytesIO(buf.getvalue())).shape[1::-1]
    return Image(buf, width=width_cm * cm, height=width_cm * cm * h / w)


def fmt(v, d=0):
    return f"{v:,.{d}f}".replace("-", "−")


# ----------------------------------------------------------------------------- page decoration
class TrackingDoc(SimpleDocTemplate):
    """Records the page of every numbered equation and every section heading."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sections = {}

    def afterFlowable(self, flowable):
        key = getattr(flowable, "_eq_key", None)
        if key:
            _EQ["page"][key] = self.page
        if isinstance(flowable, Paragraph) and flowable.style.name in ("h1", "h2"):
            text = flowable.getPlainText()
            m = re.match(r"([0-9A-Z]+(?:\.\d+)?)\.?\s", text)
            if m:
                self.sections[m.group(1)] = {"title": text, "page": self.page}


def decorate(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    if doc.page > 1:
        canvas.drawString(2 * cm, A4[1] - 1.3 * cm, "Oostvaardersplassen population model: model equations")
        canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.3 * cm, "Project Application Development 2026-2027")
        canvas.setStrokeColor(colors.HexColor("#b8c4d4"))
        canvas.line(2 * cm, A4[1] - 1.45 * cm, A4[0] - 2 * cm, A4[1] - 1.45 * cm)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, str(doc.page))
    canvas.restoreState()


# ----------------------------------------------------------------------------- content
def story():
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    r, K, al, s = P["r"], P["K"], P["alpha"], P["s"]
    mp = "model/ModelParameters.java"
    sg = "model/SeasonalGrazingModel.java"
    out = []

    # ---- title page
    out += [Spacer(1, 5.5 * cm),
            para("Model Equations", ParagraphStyle("t", parent=H1, fontSize=30, alignment=TA_CENTER, leading=36)),
            para("Oostvaardersplassen population model: every formula the application uses, what it means, "
                 "and where it lives in the code",
                 ParagraphStyle("st", parent=BODY, fontSize=13, leading=17, textColor=BLUE, alignment=TA_CENTER)),
            Spacer(1, 1.4 * cm),
            para("Project Application Development, Year 2, Semester 1 (2026-2027)",
                 ParagraphStyle("c", parent=BODY, alignment=TA_CENTER)),
            para(f"Updated {date.today().isoformat()}: four models (new: model 3, seasonal grazing with grass as "
                 f"food), internal solver steps, calendar seasons. Built from the working tree on top of commit "
                 f"{commit} by {code('scripts/build_model_equations_pdf.py')}. The application and the decisions "
                 f"behind it are described in {code('docs/APPLICATION_GUIDE.pdf')}.", CAPTION),
            Spacer(1, 1.6 * cm),
            table([["Section", "Contents", "Equations", "Page"],
                   ["1", "How the models fit together, notation", "-", PG("1")],
                   ["2", "Model 1: logistic growth (each species alone)", ER("logistic", "logistic_safety"), PG("2")],
                   ["3", "Grass growth model (Appendix 3 of the brief)", ER("temperature", "grass_factor"), PG("3")],
                   ["4", "Model 2: competition between cattle, horses and deer, with climate and management events",
                    ER("competition", "equilibrium"), PG("4")],
                   ["5", "Model 3: seasonal grazing, grass as food (adapted from AgriculturalRiskFactors)",
                    ER("calendar", "grazer_ode"), PG("5")],
                   ["6", "Model 4: predator-prey (wolves)", ER("kills", "wolf_growth"), PG("6")],
                   ["7", "Numerical solvers: Euler, Runge-Kutta 4, internal steps, extinction rule",
                    ER("euler", "clamp"), PG("7")],
                   ["8", "All parameters: values, units, status; calibration and validation", "-", PG("8")],
                   ["9", "Points to check before writing the report", "-", PG("9")]], [1.6, 10.8, 2.6, 1.4]),
            PageBreak()]

    # ---- 1
    out += [para("1. How the models fit together", H1),
            para("The application follows the iterative approach the brief asks for: start simple, then extend. "
                 "There are four population models. The number of a model is its position in the GUI dropdown; on "
                 f"the command line it is {code('--model N-1')} (model 1 = {code('--model 0')}). Model 4 is the "
                 "default because it is the most general one."),
            table([["Model", "State variables", "Adds", "Answers"],
                   [f"<b>1. Logistic</b><br/>{code('LogisticModel')}", "Cattle, horses, deer",
                    "Growth limited by a carrying capacity, species do not interact", "Baseline / sanity check"],
                   [f"<b>2. Competition</b><br/>{code('CompetitionModel')}", "Cattle, horses, deer",
                    "Species compete for the same grass (fitted α); carrying capacity depends on climate through the "
                    "grass model; known culls, relocations and introductions as input",
                    "Research questions A (stability of 1,100 animals) and C (temperature rise); validation "
                    "against history"],
                   [f"<b>3. Seasonal grazing</b><br/>{code('SeasonalGrazingModel')}", "Cattle, horses, deer, grass",
                    "Grass as a stock that the animals eat; growth follows the temperature of each season; births in "
                    "summer, starvation in winter. Built fourth (iteration 4), listed third so that model 4 stays last",
                    "A and C with the food supply made explicit; winter die-offs such as 2017-18"],
                   [f"<b>4. Predator-prey</b><br/>{code('PredatorPreyModel')}", "Cattle, horses, deer, wolves",
                    "Model 2 plus wolves hunting all three species (Holling type II)",
                    "Research question B (releasing wolves)"],
                   [f"<b>Grass</b><br/>{code('GrassModel')}", "none (helper)", "Grass growth as a function of "
                    "temperature", "Scales K in model 2 (so also model 4); drives the seasons of model 3"]],
                  [3.5, 3.0, 5.2, 4.7]),
            Spacer(1, 6),
            para("Models 1, 2 and 4 build on each other: with one species model 2 reduces to model 1, and without "
                 "wolves model 4 reduces to model 2 (both checked by tests). Model 3 is a different way of writing "
                 "the competition between the herbivores: instead of a coefficient per pair of species (model 2) they "
                 "compete because they eat from the same stock of grass. The report can compare the two."),
            para("Every model is a system of <b>ordinary differential equations</b> (ODEs): it gives the <i>rate of "
                 "change</i> of each population, dN/dt, as a function of the current state. A <b>solver</b> "
                 "(Section 7) then steps these rates forward in time, one month at a time by default, for 20 years. "
                 f"In the code each model only implements a method {code('derivatives(t, y, p)')} that returns the "
                 "vector of rates; the solver does the rest. That is why adding a model never requires touching the "
                 "solver or the GUI."),
            para("1.1 Notation", H2),
            table([["Symbol", "Meaning", "Unit"],
                   ["<i>i, j</i>", "Species index: 1 = cattle, 2 = horses, 3 = deer (in the code: 0, 1, 2)", "-"],
                   ["N<sub>i</sub>(t)", "Number of animals of species <i>i</i> at time <i>t</i>", "animals"],
                   ["W(t)", "Number of wolves at time <i>t</i> (model 4)", "wolves"],
                   ["G(t)", "Standing grass on the grazing area (model 3)", "tonnes dry matter (t DM)"],
                   ["t", "Time since the start of the simulation", "years"],
                   ["τ", "Calendar time: τ = startYear + t (2017.75 = 1 October 2017)", "years"],
                   ["dN<sub>i</sub>/dt", "Rate of change of N<sub>i</sub>: positive = growing, negative = shrinking",
                    "animals per year"],
                   ["r<sub>i</sub>", "Intrinsic growth rate: growth per animal per year when there is plenty of food",
                    "1/year"],
                   ["K<sub>i</sub>", "Carrying capacity of species <i>i</i> alone: the largest population the food "
                    "supply can sustain (today's climate)", "animals"],
                   ["M<sub>i</sub>(t)", "Management flow: animals added (+) or removed (−) per year by known "
                    "events (culls, relocations, introductions, die-off)", "animals per year"],
                   ["ΔT", "Temperature rise relative to today", "°C"],
                   ["Δt", "Output step (default 1/12 year = 1 month); the solver may take smaller internal steps",
                    "years"]], [2.4, 11.2, 2.8]),
            Spacer(1, 6),
            para(f"Throughout this document, <b>default value</b> means the value currently in "
                 f"{code('ModelParameters.java')}. Growth rates, carrying capacities and competition coefficients of "
                 "model 2 are <b>fitted</b> to the herd counts 1983-2017 (Section 8.1); the remaining placeholders, "
                 f"including every parameter of model 3, are marked {code('// TODO: fit/look up')} in the code. "
                 "Section 8 lists every parameter and its status."),
            PageBreak()]

    # ---- 2
    out += [para("2. Model 1: logistic growth", H1),
            para("The simplest model that stops a population from growing forever. Each species grows on its own, "
                 "ignoring the other species and the wolves (Gotelli, <i>A Primer of Ecology</i>, ch. 2)."),
            eq(r"\frac{dN_i}{dt} \;=\; r_i\,N_i\,\left(1-\frac{N_i}{K_i}\right)", "logistic"),
            para("2.1 What each part means", H2),
            table([["Term", "Meaning"],
                   ["r<sub>i</sub> N<sub>i</sub>", "Exponential growth: every animal contributes r<sub>i</sub> new "
                    "animals per year (births minus deaths) when food is unlimited."],
                   ["1 − N<sub>i</sub>/K<sub>i</sub>", "The <b>brake</b>. Close to 1 when the population is small "
                    "(almost free growth), 0 when N<sub>i</sub> = K<sub>i</sub> (growth stops), negative when "
                    "N<sub>i</sub> &gt; K<sub>i</sub> (population shrinks back)."]], [3.5, 12.9]),
            para("2.2 Behaviour", H2),
            para("Setting dN/dt = 0 gives two <b>equilibria</b>: N = 0 (unstable: any small population grows) and "
                 "N = K (stable: the population always returns to K). This equation has an exact solution, which the "
                 f"test {code('RungeKutta4SolverTest')} uses to check that the solver is accurate:"),
            eq(r"N(t) \;=\; \frac{K}{1+\left(\frac{K-N_0}{N_0}\right)e^{-rt}}", "logistic_exact"),
            para("where N<sub>0</sub> is the starting population. The curve is S-shaped: slow at first, fastest at "
                 "N = K/2, then flattening out at K. The calibration script fits this closed form to each species as "
                 "a first comparison (Section 8.1); it fits horses and deer well but not cattle, which declined after "
                 "2005 because of competition, so the defaults come from model 2."),
            para("2.3 Safety rule in the code", H2),
            para("If a carrying capacity is set to zero or below (possible in model 2 under extreme warming), "
                 "dividing by K would fail. The code then uses pure decline instead:"),
            eq(r"\frac{dN_i}{dt} \;=\; -\,r_i\,N_i \qquad \mathrm{when}\;\; K_i \leq 0", "logistic_safety"),
            where([[f"Equation ({E('logistic')}), ({E('logistic_safety')})",
                    f"{code('src/main/java/nl/ovp/model/LogisticModel.java')} line "
                    f"{line_of('model/LogisticModel.java', 'growthRate')}"],
                   ["r, K defaults", f"{code('src/main/java/nl/ovp/model/ModelParameters.java')} "
                    f"{lines(mp, 'double.. growthRate', 'DEER   // fitted 5093')}"],
                   [f"Test against ({E('logistic_exact')})", code("src/test/java/nl/ovp/solver/RungeKutta4SolverTest.java")]]),
            Spacer(1, 8),
            table([["Default (fitted)", "Cattle", "Horses", "Deer"],
                   ["r (1/year)"] + [f"{v:.2f}" for v in r],
                   ["K, species alone (animals)"] + [fmt(v) for v in K]], [5.0, 3.0, 3.0, 3.0]),
            PageBreak()]

    # ---- 3
    gm = "model/GrassModel.java"
    gtab = [0, 1, 2, 3, 4, 6]
    out += [para("3. Grass growth model", H1),
            para("Implements Appendix 3 of the project brief (derived from Taube, 1990). It is not a population model "
                 "on its own. It has two jobs: it tells model 2 how much the food supply changes when the climate "
                 "warms (step 4 below), and it gives model 3 the growing season (steps 1 and 2 only, Section 5)."),
            para("Step 1: the temperature through the year", H3),
            para("The brief's formula needs an average temperature. The app approximates the monthly temperature as "
                 "a cosine wave around the annual mean, peaking in mid-July:"),
            eq(r"T(t) \;=\; T_{\mathrm{mean}} + \Delta T + A\cos\left(2\pi\left(\{t\} - \frac{6.5}{12}\right)\right)",
               "temperature"),
            para(f"T<sub>mean</sub> = mean annual temperature (default {P['Tbar']:.1f} °C), A = seasonal amplitude, half "
                 f"the summer-winter difference (default {P['A']:.1f} °C), {{t}} = the fraction of the current year "
                 "(0 = 1 January, 0.5 = 1 July). Both are <b>fitted</b> to KNMI monthly means 1983-2017 (Lelystad; "
                 f"De Bilt adjusted before 1990) by {code('scripts/fit_temperature_profile.py')}: 9.96 °C and "
                 "7.39 °C, R² = 0.89; a free-phase fit puts the peak at about 22 July, which justifies the "
                 "fixed mid-July peak. Climate change is modelled as the whole curve shifting up by ΔT."),
            para("Step 2: growth potential (the formula from the brief)", H3),
            eq(r"GP(T) \;=\; \exp\left(-\frac{1}{2}\left(\frac{T-t_0}{\mathrm{var}}\right)^2\right)", "gp"),
            para(f"A bell curve between 0 and 1: grass grows best (GP = 1) at the optimum temperature t<sub>0</sub> = "
                 f"{P['t0']:.0f} °C (C3 grass such as ryegrass, fixed by the brief) and slower the further the "
                 "temperature is from it. <b>var</b> sets how wide the curve is; the brief does not give a value, so "
                 f"the default of {P['var']:.0f} °C is still a placeholder. In model 3 it also sets how much grass "
                 "still grows in winter."),
            para("Step 3: grass yield for the whole reserve", H3),
            eq(r"Y_{\mathrm{month}}(t) \;=\; GP(T(t))\cdot G_{\max}\cdot \mathrm{Area}", "y_month"),
            eq(r"Y_{\mathrm{year}}(\Delta T) \;=\; \sum_{m=0}^{11} Y_{\mathrm{month}}\left(\frac{m}{12}\right)", "y_year"),
            para(f"G<sub>max</sub> = {P['Gmax']:.0f} kg/ha/month (peak growth, from the brief) and Area = "
                 f"{fmt(P['area'])} ha. The annual yield adds up 12 monthly values. With the defaults, today's annual "
                 f"yield is about {annual_yield(0) / 1e6:.1f} million kg."),
            para("Step 4: the grass factor passed to model 2", H3),
            eq(r"g(\Delta T) \;=\; \frac{Y_{\mathrm{year}}(\Delta T)}{Y_{\mathrm{year}}(0)}", "grass_factor"),
            para("A ratio: g = 1 means the same amount of grass as today, g = 1.2 means 20% more. Because it is a "
                 "<i>ratio</i>, G<sub>max</sub> and Area cancel out: they do not affect the simulation at all at the "
                 "moment.")]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.4))
    T = np.linspace(-5, 45, 300)
    ax[0].plot(T, [gp(x) for x in T], color="#2e6da4", lw=2)
    mt = [temperature(m / 12, 0) for m in range(12)]
    ax[0].scatter(mt, [gp(x) for x in mt], color="#f47230", zorder=3, s=18, label="the 12 monthly temps (ΔT = 0)")
    ax[0].axvline(P["t0"], color="grey", ls="--", lw=0.8)
    ax[0].set(xlabel="average temperature T (°C)", ylabel="growth potential GP",
              title=f"Eq. ({E('gp')}): growth potential vs temperature")
    ax[0].legend(frameon=False, fontsize=8)
    for dT, c in [(0, "#2e6da4"), (2, "#f47230"), (4, "#c0392b")]:
        ax[1].plot(range(12), [gp(temperature(m / 12, dT)) * P["Gmax"] for m in range(12)], "o-", ms=3, color=c,
                   label=f"ΔT = +{dT} °C" if dT else "ΔT = 0 (today)")
    ax[1].set_xticks(range(12), list("JFMAMJJASOND"))
    ax[1].set(ylabel="growth (kg/ha/month)", title=f"Eq. ({E('y_month')}): monthly grass growth, default parameters")
    ax[1].legend(frameon=False, fontsize=8)
    for a_ in ax:
        a_.spines[["top", "right"]].set_visible(False)
    yearly_kg_ha = sum(gp(temperature((m + 0.5) / 12, 0)) for m in range(12)) * P["Gmax"]
    demand = 3950 * P["q"][2] + 230 * P["q"][0] + 1050 * P["q"][1]
    out += [figure(fig, 16.4),
            para(f"Left: the bell curve of equation ({E('gp')}) with the 12 monthly temperatures of today's climate "
                 "marked. Every month is colder than 20 °C, so warming moves the points towards the peak. Right: "
                 "growth per month for 0, +2 and +4 °C.", CAPTION),
            table([["ΔT (°C)"] + [("+" if d else "") + str(d) for d in gtab],
                   ["g(ΔT)"] + [f"{g(d):.3f}" for d in gtab]], [2.6] + [2.3] * 6),
            Spacer(1, 6),
            note(f"<b>Consequence of the defaults:</b> with a mean temperature of {P['Tbar']:.0f} °C, warming "
                 f"<i>always</i> means more grass (about +{100 * (g(1) - 1):.1f}% per °C at first). Drought (the brief "
                 "mentions dry seasons) is not in this formula: it only looks at temperature. <b>The unit of "
                 "G<sub>max</sub> is doubtful:</b> the brief says 60 kg/ha \"during peak times\" without a time unit, "
                 f"and the code reads it as per month. That gives about {yearly_kg_ha:.0f} kg DM/ha/year, while the "
                 f"October 2017 herd ate about {fmt(demand)} t DM/year (model 3 intakes): even all "
                 f"{fmt(P['area'])} ha would cover only {100 * yearly_kg_ha * P['area'] / 1000 / demand:.0f}% of it. "
                 f"Read per day, it gives about {yearly_kg_ha * 30.4 / 1000:.1f} t DM/ha/year, normal for ryegrass. "
                 "Model 2 is unaffected (ratio); model 3 uses GP only as a shape between 0 and 1, so it is "
                 "unaffected too."),
            Spacer(1, 6),
            where([[f"Equation ({E('temperature')})", f"{code('src/main/java/nl/ovp/model/GrassModel.java')} line "
                    f"{line_of(gm, 'public static double temperatureAt')} ({code('temperatureAt')})"],
                   [f"Equation ({E('gp')})", f"{code('GrassModel.java')} line "
                    f"{line_of(gm, 'public static double growthPotential')} ({code('growthPotential')})"],
                   [f"Equations ({E('y_month')}), ({E('y_year')})", f"{code('GrassModel.java')} lines "
                    f"{line_of(gm, 'public static double monthlyYieldKg')}-"
                    f"{line_of(gm, 'public static double annualYieldKg')} ({code('monthlyYieldKg, annualYieldKg')})"],
                   [f"Equation ({E('grass_factor')})", f"{code('GrassModel.java')} line "
                    f"{line_of(gm, 'public static double grassFactor')} ({code('grassFactor')})"],
                   ["Fit of T<sub>mean</sub>, A", code("scripts/fit_temperature_profile.py")]]),
            PageBreak()]

    # ---- 4
    cm_ = "model/CompetitionModel.java"
    names = ["Cattle", "Horses", "Deer"]
    status = [["1", "0.24 (fitted, a)", "0.3 (brief)"], ["0.24 (fitted, a)", "1", "0.3 (brief)"],
              ["0.80 (fitted, b)", "0.80 (fitted, b)", "1"]]
    assert np.allclose(al, [[1, .24, .3], [.24, 1, .3], [.8, .8, 1]]), "update the alpha labels in the PDF script"
    n_star = np.linalg.solve(al, K)
    hd = np.linalg.solve(al[1:, 1:], K[1:])
    invasion = 1 - (al[0, 1] * hd[0] + al[0, 2] * hd[1]) / K[0]
    long_run = cli("--model", "1", "--years", "200")
    twenty = cli("--model", "1", "--years", "20")
    out += [para("4. Model 2: competition, with climate and management", H1),
            para("Cattle, horses and deer eat the same grass, so each species' growth is slowed not only by its own "
                 "numbers but also by the others. This is the Lotka-Volterra competition model (Gotelli, ch. 5), with "
                 "the carrying capacities adjusted for temperature and an extra term for known human interventions."),
            eq(r"\frac{dN_i}{dt} \;=\; r_i\,N_i\,\left(1-\frac{\sum_{j=1}^{3}\alpha_{ij}N_j}{K_i'}\right) \;+\; M_i(t)",
               "competition"),
            eq(r"K_i' \;=\; K_i\cdot g(\Delta T)\cdot \max(0,\;1+s_i\,\Delta T)", "k_prime"),
            eq(r"M_i(t) \;=\; \sum_{e\ \mathrm{active\ at}\ t} \frac{\Delta n_e}{\tau_e}\,\sigma_{e,i}", "mgmt"),
            para("4.1 What each part means", H2),
            table([["Term", "Meaning"],
                   ["Σ α<sub>ij</sub> N<sub>j</sub>", "The <b>effective crowding</b> felt by species <i>i</i>: "
                    "its own animals count fully, animals of another species <i>j</i> count with weight "
                    "α<sub>ij</sub>. With only one species this reduces exactly to model 1."],
                   ["α<sub>ij</sub>", "Competition coefficient: how many animals of species <i>i</i> one animal of "
                    "species <i>j</i> is \"worth\" in eating its food. α<sub>ii</sub> = 1 by definition."],
                   ["K<sub>i</sub>′", "Carrying capacity after climate change: today's K<sub>i</sub> times two "
                    "factors."],
                   ["g(ΔT)", f"Grass factor from equation ({E('grass_factor')}): more or less food for <i>all</i> "
                    "species."],
                   ["max(0, 1 + s<sub>i</sub>ΔT)", "Species-specific climate effect (heat stress, disease, ...). "
                    "s<sub>i</sub> &gt; 0 means warming helps, s<sub>i</sub> &lt; 0 means it hurts. The brief states "
                    "that warming benefits horses and harms cattle. max(0, ...) stops K from going negative."],
                   ["M<sub>i</sub>(t)", "<b>Management flow</b> (harvesting term, Gotelli ch. 2). Each event e (cull, "
                    "relocation, introduction, die-off) moves Δn<sub>e</sub> animals (negative = removed) evenly "
                    "over its window of τ<sub>e</sub> years. σ<sub>e,i</sub> = 1 if the event concerns only "
                    "species <i>i</i>; for the 2017-18 die-off, which concerns all species, σ<sub>e,i</sub> = "
                    "N<sub>i</sub>/ΣN<sub>j</sub> (shared in proportion to numbers). Nothing is removed from an "
                    f"extinct species. With no active events M<sub>i</sub> = 0 and equation ({E('competition')}) is "
                    "the plain competition model. Models 3 and 4 use the same term."]], [3.5, 12.9]),
            para("4.2 The competition matrix (fitted defaults)", H2),
            table([["Effect on ↓ of →"] + names] +
                  [[f"<b>{names[i]}</b>"] + status[i] for i in range(3)], [4.1, 4.1, 4.1, 4.1]),
            para("Read row by row: one deer takes as much food from cattle as 0.3 cattle would (fixed by the brief: "
                 "\"the influence of the deer on the other two herbivores is only 30%\"). The other four entries are "
                 "fitted with two shared values: a = cattle↔horses (same grazing guild, symmetric) = 0.24 ± "
                 "0.55 and b = effect of either grazer on deer = 0.80 ± 1.28. Four free values cannot be "
                 "separated by the data (Section 8.1); both a and b are weakly determined."),
            para("4.3 Climate sensitivity (defaults)", H2),
            table([["", "Cattle", "Horses", "Deer"],
                   ["s<sub>i</sub> (per °C)"] + [fmt(v, 2) if v else "0" for v in s]] +
                  [[f"K′ at ΔT = {('+' if d else '') + str(d)}"] + [fmt(v) for v in k_prime(d)]
                   for d in (0, 2, 4, 6)], [4.1, 4.1, 4.1, 4.1]),
            Spacer(1, 4),
            note(f"<b>Check:</b> with the current placeholders for s<sub>i</sub> and var the grass factor outweighs "
                 f"the cattle penalty, so the cattle carrying capacity still <i>rises</i> with warming "
                 f"({fmt(k_prime(0)[0])} → {fmt(k_prime(4)[0])} at +4 °C). The brief says warming should "
                 "eventually drive cattle to extinction. s<sub>cattle</sub> and var are still to be set."),
            para("4.4 Stability: the key tool for research question A", H2),
            para(f"The populations stop changing (without management, M = 0) when every bracket in equation "
                 f"({E('competition')}) equals zero. For a state where all three species survive, this gives a system "
                 "of three linear equations:"),
            eq(r"\sum_{j=1}^{3}\alpha_{ij}\,N_j^* \;=\; K_i' \qquad (i=1,2,3)", "equilibrium"),
            para(f"With the fitted defaults this gives N* ≈ ({fmt(n_star[0])}, {fmt(n_star[1])}, "
                 f"{fmt(n_star[2])}): a <b>negative</b> number of cattle, so no state exists where all three survive "
                 f"together. Without cattle, horses and deer settle at H* ≈ {fmt(hd[0])}, D* ≈ {fmt(hd[1])}. "
                 f"Cattle cannot re-invade that state: their bracket is 1 − (0.24 · {fmt(hd[0])} + 0.3 · "
                 f"{fmt(hd[1])}) / {fmt(K[0])} = {fmt(invasion, 2)} &lt; 0. The simulation confirms it: from the policy "
                 f"target (300, 300, 500) the herds reach {fmt(twenty[1])} cattle, {fmt(twenty[2])} horses and "
                 f"{fmt(twenty[3])} deer after 20 years, and {fmt(long_run[1])}, {fmt(long_run[2])}, {fmt(long_run[3])} "
                 "after 200 years. This matches the observed decline of the cattle after 2005, and every fitted "
                 "variant agrees on it."),
            para("<b>Consequence for question A:</b> 1,100 animals is far below what the reserve sustains in model 2, "
                 f"so it is not a natural equilibrium. It can only be held with yearly removals, which equation "
                 f"({E('mgmt')}) can express as a quota. The K values were fitted on 1983-2017, when the grazing area "
                 "was about 1,880 ha; the grassland left after the 2018 measures is 1,080 ha (Section 9). The "
                 "stability of an equilibrium can be checked formally with the Jacobian matrix (all eigenvalues "
                 "negative = stable)."),
            where([[f"Equation ({E('competition')})", f"{code('src/main/java/nl/ovp/model/CompetitionModel.java')} lines "
                    f"{line_of(cm_, 'double competitionSum')}-{line_of(cm_, 'addManagementFlows.t, y, p, dy')}"],
                   [f"Equation ({E('k_prime')})", f"{code('CompetitionModel.java')} lines "
                    f"{line_of(cm_, 'double grassFactor')}-{line_of(cm_, 'double adjustedK')}"],
                   [f"Equation ({E('mgmt')})", f"{code('CompetitionModel.java')} {code('addManagementFlows')} line "
                    f"{line_of(cm_, 'static void addManagementFlows')}; window and flow in "
                    f"{code('model/ManagementEvent.java')}"],
                   ["Event data", f"{code('data/clean/herbivore_events.csv')} (read by "
                    f"{code('CsvDataLoader.loadEvents')}; used by {code('--replay YEAR')})"],
                   ["α, s, events defaults", f"{code('ModelParameters.java')} "
                    f"{lines(mp, 'double.... competitionAlpha', 'double.. climateSensitivity')}, line "
                    f"{line_of(mp, 'List<ManagementEvent> events')}"],
                   ["Tests", code("CompetitionModelTest") + " (events), " + code("PredatorPreyModelTest")]]),
            PageBreak()]

    # ---- 5: seasonal grazing
    hdr, rows = cli_rows("--model", "2", "--years", "50")
    tot = [sum(rw[1:4]) for rw in rows]
    yrs = [rw[0] for rw in rows]
    i_max = int(np.argmax(tot))
    over = next((yrs[i] for i in range(len(tot)) if tot[i] > 1500), None)
    at20 = rows[240]
    excl = cli("--model", "2", "--years", "400")
    oct17, apr18, oct18 = october_2017_run()
    t_oct17, t_apr18, t_oct18 = sum(oct17[:3]), sum(apr18[:3]), sum(oct18[:3])
    out += [para("5. Model 3: seasonal grazing (grass as food)", H1),
            para("Models 1, 2 and 4 contain the food supply only indirectly, through the carrying capacity K. Model 3 "
                 "makes it explicit: grass is a stock that grows, dies back in winter and is eaten. The animals "
                 "reproduce in summer when they are well fed and starve in winter when grass runs short, so a winter "
                 "die-off such as 2017-18 can <i>follow</i> from the model instead of being an input. The structure is "
                 "adapted from the <i>GrazerModel</i> of the AgriculturalRiskFactors project (ovp-model v0.1.0, "
                 "Team 7). Our change: grass growth and die-back follow the brief's temperature-driven growth potential "
                 f"(equations ({E('temperature')})-({E('gp')})) instead of a fixed cosine."),
            para("5.1 Seasons and feeding", H2),
            eq(r"\tau \;=\; \mathrm{startYear} + t", "calendar"),
            eq(r"\varphi(\tau) \;=\; \frac{1}{2}\left(1-\cos 2\pi\tau\right)", "season"),
            eq(r"f(G) \;=\; \frac{G}{G + h_G\,A_g}", "feeding"),
            eq(r"c_i \;=\; \max(0,\; 1 + s_i\,\Delta T)", "climate_births"),
            table([["Term", "Meaning"],
                   ["τ", "Calendar time. The seasons follow the calendar, so a run may start on any date "
                    "(startYear = 2017.75 starts on 1 October 2017)."],
                   ["GP(T(τ))", f"Growth potential of equations ({E('temperature')})-({E('gp')}) at the temperature of "
                    "that moment: about 0.09 in January and 0.95 in July with today's climate. Drives grass growth and "
                    "(as 1 − GP) winter die-back. Warming raises it in every month."],
                   ["φ(τ)", "Calendar season: 0 on 1 January, 1 on 1 July (season(t) in the code). Drives births "
                    "and winter starvation. Kept as a calendar curve because breeding is timed by day length, not "
                    "by temperature."],
                   ["f(G)", "Feeding level (Holling type II, Gotelli ch. 6, applied to grazers and grass): the fraction "
                    "of maximum intake the animals achieve. Half of maximum at G = h<sub>G</sub>A<sub>g</sub>."],
                   ["c<sub>i</sub>", "Climate effect on births, with the same s<sub>i</sub> as model 2 (brief: warming "
                    "helps horses, harms cattle). Model 3 has no K<sub>i</sub> to scale, so births are scaled."]],
                  [2.6, 13.8]),
            para("5.2 The equations", H2),
            eq(r"\frac{dG}{dt} \;=\; r_G\,GP(\tau)\,G\left(1-\frac{G}{k_G A_g}\right) \;-\; d_G\,(1-GP(\tau))\,G"
               r" \;-\; f(G)\sum_{i=1}^{3} q_i N_i", "grass_ode", size=14),
            eq(r"\frac{dN_i}{dt} \;=\; N_i\left[\,2\,b_i\,c_i\,\varphi(\tau)\,f(G) \;-\; \mu_i \;-\; "
               r"\omega_i\,(1-\varphi(\tau))\,(1-f(G))\,\right] \;+\; M_i(t)", "grazer_ode", size=14),
            table([["Term", "Meaning"],
                   ["r<sub>G</sub> GP G (1 − G/k<sub>G</sub>A<sub>g</sub>)", "Logistic grass growth (Gotelli ch. 2), "
                    "fastest in summer, limited by the maximum standing biomass k<sub>G</sub> per hectare."],
                   ["d<sub>G</sub> (1 − GP) G", "Die-back of standing grass outside the growing season."],
                   ["f(G) Σ q<sub>i</sub>N<sub>i</sub>", "Grass eaten: each animal eats up to q<sub>i</sub> per year, "
                    "times the feeding level. The same amount appears as food in the animal equation (tested: grass "
                    "eaten = f · Σ q<sub>i</sub>N<sub>i</sub>)."],
                   ["2 b<sub>i</sub> c<sub>i</sub> φ f", "Births: only in the growing season and only when well fed. "
                    "The factor 2 makes the yearly mean b<sub>i</sub>c<sub>i</sub>f, because the mean of φ is 1/2."],
                   ["μ<sub>i</sub>", "Background mortality, all year."],
                   ["ω<sub>i</sub> (1 − φ)(1 − f)", "Winter starvation: extra deaths in winter, the larger the "
                    "shorter the food."],
                   ["M<sub>i</sub>(t)", f"Management flow of equation ({E('mgmt')}), the same code as model 2."]],
                  [4.0, 12.4]),
            para("The species interact <b>only through the grass</b>. Per animal a deer eats "
                 f"q<sub>deer</sub>/q<sub>cattle</sub> = {P['q'][2] / P['q'][0]:.2f} of a cow's grass and "
                 f"q<sub>deer</sub>/q<sub>horses</sub> = {P['q'][2] / P['q'][1]:.2f} of a horse's, consistent with the "
                 "brief's 30% effect of deer on cattle and horses.")]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.3))
    tt = np.linspace(0, 1, 366)
    ax[0].plot(tt * 12, [season(x) for x in tt], color="grey", ls="--", lw=1.5, label="φ: calendar season (births, starvation)")
    for dT, c in [(0, "#2e6da4"), (2, "#f47230"), (4, "#c0392b")]:
        ax[0].plot(tt * 12, [gp(temperature(x, dT)) for x in tt], color=c, lw=1.6,
                   label=f"GP(T), ΔT = +{dT} °C" if dT else "GP(T), today (grass growth)")
    ax[0].set_xticks(np.arange(12) + 0.5, list("JFMAMJJASOND"))
    ax[0].set(ylim=(0, 1.05), title="Seasonal drivers of model 3")
    ax[0].legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    i0 = 19 * 12
    sel = rows[i0:i0 + 13]
    months = [rw[0] - 19 for rw in sel]
    ax[1].plot([m * 12 for m in months], [sum(rw[1:4]) for rw in sel], color="#1f3a5f", lw=2, label="all animals")
    ax2 = ax[1].twinx()
    ax2.plot([m * 12 for m in months], [rw[4] / P["Ag"] for rw in sel], color="#2f8a4a", lw=2, ls="-.",
             label="grass (t DM/ha, right)")
    ax[1].set_xticks(range(13), list("JFMAMJJASOND") + ["J"])
    ax[1].set(ylabel="animals", title="One simulated year (year 20 from the policy target)")
    ax2.set_ylabel("grass, t DM/ha")
    h1, l1 = ax[1].get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax[1].legend(h1 + h2, l1 + l2, frameon=False, fontsize=7, loc="lower right")
    for a_ in (ax[0], ax[1], ax2):
        a_.spines[["top"]].set_visible(False)
    out += [figure(fig, 16.4),
            para("Left: grass grows with the temperature curve GP (it shifts up under warming), births and starvation "
                 f"follow the calendar season φ. Right: model 3 run by the app ({code('--model 2')}), year 20: animals "
                 "die from January to May, grass is lowest in April and highest in early autumn.", CAPTION),
            para("5.3 What it gives with the provisional parameters", H2),
            table([["Run", "Result", "Compare with"],
                   [f"Policy target 300 / 300 / 500 on {fmt(P['Ag'])} ha, no culling "
                    f"({code('--model 2 --years 50')})",
                    f"Total on 1 January: {fmt(tot[0])} → {fmt(sum(at20[1:4]))} after 20 years "
                    f"({fmt(at20[1])} / {fmt(at20[2])} / {fmt(at20[3])}); highest {fmt(tot[i_max])} in year "
                    f"{yrs[i_max]:.1f}; above 1,500 from year {over:.1f}." if over is not None else "-",
                    "Winter ceiling 1,500 (Van Geel, 2018). Model 2 reaches about 5,350 (Section 4.4)"],
                   ["October 2017 herd on 1,880 ha, from 1 October 2017, horse relocation as input, <b>no</b> die-off "
                    "event (via jshell)",
                    f"{fmt(t_oct17)} → {fmt(t_apr18)} on 1 April 2018 → {fmt(t_oct18)} on 1 October 2018 "
                    f"({fmt(oct18[0])} / {fmt(oct18[1])} / {fmt(oct18[2])})",
                    "Observed 2018 count 3,130 (200 / 610 / 2,320); NOS: about 3,226 deaths in winter 2017-18, 89% "
                    "shot before starving"],
                   [f"Policy target, 400 years ({code('--model 2 --years 400')})",
                    f"{fmt(excl[1])} cattle, {fmt(excl[2])} horses, {fmt(excl[3])} deer",
                    "Competitive exclusion: with one shared food the species that survives on the least grass wins. "
                    "Model 2 excludes cattle instead, as the data suggest"]],
                  [5.0, 6.0, 5.4]),
            Spacer(1, 4),
            note("<b>All parameters of model 3 are provisional</b> (AgriculturalRiskFactors first estimates). The "
                 "October 2017 run shows the mechanism works at about the right size; the numbers are not yet a "
                 "result. Do <b>not</b> combine model 3 with the 2017-18 die-off event: the model already produces that "
                 f"die-off, so it would be counted twice. {code('--replay')} still adds it, starts on 1 January and "
                 "keeps 1,080 ha, so it is not yet suited to model 3."),
            where([["Model 3", f"{code('src/main/java/nl/ovp/model/SeasonalGrazingModel.java')}"],
                   [f"Equations ({E('calendar')})-({E('season')})", f"{code('SeasonalGrazingModel.java')} lines "
                    f"{line_of(sg, 'double calendarTime')}-{line_of(sg, 'double s = season')}; "
                    f"{code('season')} line {line_of(sg, 'public static double season')}"],
                   [f"Equation ({E('feeding')})", f"{code('SeasonalGrazingModel.java')} line "
                    f"{line_of(sg, 'public static double feeding')} ({code('feeding')})"],
                   [f"Equations ({E('climate_births')}), ({E('grazer_ode')})", f"{code('SeasonalGrazingModel.java')} "
                    f"lines {line_of(sg, 'double climate =')}-{line_of(sg, 'addManagementFlows')}"],
                   [f"Equation ({E('grass_ode')})", f"{code('SeasonalGrazingModel.java')} lines "
                    f"{line_of(sg, 'double growth =')}-{line_of(sg, 'dy.GRASS. =')}"],
                   ["Defaults", f"{code('ModelParameters.java')} "
                    f"{lines(mp, 'public double grazingAreaHa', 'double.. winterStarvationMortality')}"],
                   ["Tests", code("SeasonalGrazingModelTest") + " (13 tests)"]]),
            PageBreak()]

    # ---- 6: predator-prey
    pp = "model/PredatorPreyModel.java"
    prey = np.array(P["N0"])
    s_aw = float(np.sum(np.array(P["a"]) * np.array(P["w"]) * prey))
    kills = s_aw / (1 + P["h"] * s_aw)
    growth = float(np.sum(np.array(P["e"]) * np.array(P["a"]) * np.array(P["w"]) * prey)) / (1 + P["h"] * s_aw) - P["m"]
    wolves20 = cli("--years", "20", "--wolves", "10")
    out += [para("6. Model 4: predator-prey (wolves)", H1),
            para("Model 2 plus grey wolves. Wolves hunt all three species at once; the more prey they kill, the more "
                 "wolves the reserve can feed (Gotelli, ch. 6, extended to several prey species). Putting the wolves on "
                 "top of model 3 instead is a planned next step."),
            para("6.1 How many animals do wolves kill?", H2),
            eq(r"P_i \;=\; \frac{a_i\,w_i\,N_i\,W}{1+h\sum_{j=1}^{3}a_j\,w_j\,N_j}", "kills"),
            para("P<sub>i</sub> is the number of animals of species <i>i</i> killed per year by all W wolves together. "
                 "This is the <b>Holling type II functional response</b>:"),
            table([["Term", "Meaning"],
                   ["a<sub>i</sub>", "Attack rate: how efficiently one wolf finds and kills species <i>i</i> (per animal "
                    "available, per year)."],
                   ["w<sub>i</sub>", "Prey preference between 0 and 1 (adjustable in the GUI). 0 = wolves never hunt "
                    "this species, 1 = full attack rate. The brief suggests this as a user option."],
                   ["h", f"Handling time: the time one kill takes (chasing, eating, resting), in years. Default "
                    f"{P['h']} year ≈ {P['h'] * 365:.0f} days."],
                   ["Denominator", "The time wolves spend handling kills cannot be spent hunting. With few prey it is "
                    "≈ 1, so kills grow in proportion to prey. With many prey, kills level off at a maximum of "
                    f"<b>1/h per wolf per year</b> ({1 / P['h']:.0f} with the default h). A wolf can only eat so "
                    "much."]], [3.0, 13.4])]
    fig, ax = plt.subplots(figsize=(8, 2.8))
    N = np.linspace(0, 50000, 300)
    a = P["a"][2]
    ax.plot(N / 1000, a * N / (1 + a * P["h"] * N), color="#2e6da4", lw=2, label="Holling type II: aN/(1+ahN)")
    ax.plot(N[:90] / 1000, a * N[:90], color="grey", ls="--", lw=1, label="no handling time (type I): aN")
    ax.axhline(1 / P["h"], color="#c0392b", ls=":", lw=1)
    ax.text(1, 1 / P["h"] + 1, f"ceiling 1/h = {1 / P['h']:.0f} prey per wolf per year", color="#c0392b", fontsize=8)
    ax.set(xlabel="prey available, N (thousands)  [deer only, default a and h]", ylabel="prey killed per wolf per year",
           ylim=(0, 1 / P["h"] * 1.2))
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    out += [figure(fig, 13),
            para("Kills per wolf per year as the number of prey grows. Without handling time (dashed) kills would "
                 "grow forever.", CAPTION),
            para("6.2 The population equations", H2),
            eq(r"\frac{dN_i}{dt} \;=\; r_i\,N_i\,\left(1-\frac{\sum_j\alpha_{ij}N_j}{K_i'}\right) + M_i(t) \;-\; P_i",
               "prey"),
            eq(r"\frac{dW}{dt} \;=\; \sum_{i=1}^{3} e_i\,P_i \;-\; m\,W", "wolves"),
            para(f"Prey: the competition model ({E('competition')}), including management events, minus the animals "
                 "killed. Wolves: new wolves are \"made\" from the prey they eat (e<sub>i</sub> = wolves produced per "
                 "animal killed, the conversion efficiency) and die or leave at rate m. Note there is no carrying "
                 "capacity for wolves: the wolf population is limited only by the prey."),
            para(f"<b>Wolf mortality m = {P['m']:.2f} per year is taken from data</b>: recorded deaths 0.141 plus "
                 "wolves that disappear without a recorded death (dispersal or unrecorded deaths) 0.090 per wolf per "
                 f"year, means over both regions 2010-2025 in {code('data/clean/wolf_rates.csv')}. Dispersal counts as "
                 "a loss because the reserve is far smaller than a pack's range. The same data give 0.32 pups per "
                 "wolf per year, an upper bound for the birth term Σe<sub>i</sub>P<sub>i</sub>/W. The data come "
                 "from a reference area, not the Oostvaardersplassen: an indication only."),
            para("6.3 When can wolves survive?", H2),
            para(f"Dividing equation ({E('wolves')}) by W gives the growth per wolf:"),
            eq(r"\frac{1}{W}\frac{dW}{dt} \;=\; \frac{\sum_i e_i\,a_i\,w_i\,N_i}{1+h\sum_j a_j\,w_j\,N_j} \;-\; m",
               "wolf_growth"),
            para(f"Wolves can only establish themselves if this is positive. With the defaults and the policy target "
                 f"(300 cattle, 300 horses, 500 deer), one wolf kills only about <b>{kills:.1f} animals per year</b>, "
                 f"giving a growth per wolf of {fmt(growth, 2)} per year. Negative, so released wolves die out, which "
                 f"matches the simulation (10 wolves → {wolves20[4]:.1f} after 20 years). Field studies report "
                 "roughly 15-25 large prey per wolf per year, so the default attack rates are probably far too low. "
                 "These are the parameters to look up first for question B."),
            para("6.4 Built-in check", H2),
            para(f"With W = 0, every P<sub>i</sub> = 0 and equations ({E('prey')})-({E('wolves')}) reduce exactly to "
                 f"model 2. The test {code('PredatorPreyModelTest.withZeroWolvesReducesToCompetitionModel')} checks this."),
            where([[f"Equation ({E('kills')})", f"{code('src/main/java/nl/ovp/model/PredatorPreyModel.java')} lines "
                    f"{line_of(pp, 'double weightedPreySum')}-{line_of(pp, 'double kill =')}"],
                   [f"Equation ({E('prey')})", f"{code('PredatorPreyModel.java')} line {line_of(pp, 'dy.i. = preyGrowth')} "
                    f"(growth incl. M<sub>i</sub> from {code('CompetitionModel')})"],
                   [f"Equation ({E('wolves')})", f"{code('PredatorPreyModel.java')} line {line_of(pp, 'dy.3. =')}"],
                   ["a, w, h, e, m defaults", f"{code('ModelParameters.java')} "
                    f"{lines(mp, 'double.. attackRate', 'double wolfMortality')}"],
                   ["m from data", f"{code('data/clean/wolf_rates.csv')}; test "
                    f"{code('CsvDataLoaderTest.defaultWolfMortalityMatchesWolfRatesCsv')}"]]),
            PageBreak()]

    # ---- 7: solvers
    sim = "solver/Simulator.java"
    out += [para("7. Numerical solvers", H1),
            para(f"Equations ({E('competition')})-({E('wolves')}) cannot be solved by hand, so the app approximates the "
                 "solution step by step. Write the whole state as one vector y (for example (N<sub>1</sub>, "
                 "N<sub>2</sub>, N<sub>3</sub>, W) or (N<sub>1</sub>, N<sub>2</sub>, N<sub>3</sub>, G)) and the model "
                 "as dy/dt = f(t, y). Each solver turns the current state y<sub>n</sub> at time t<sub>n</sub> into the "
                 "next state y<sub>n+1</sub> at t<sub>n</sub> + Δt."),
            para("7.1 Euler's method", H2),
            eq(r"y_{n+1} \;=\; y_n + \Delta t\, f(t_n,\, y_n)", "euler"),
            para("Take the current rate of change and assume it stays constant for the whole step. Simple, but the "
                 "error per year is proportional to Δt (a <i>first-order</i> method): halving the step only halves "
                 "the error. It is kept in the app so the report can compare it with RK4."),
            para("7.2 Runge-Kutta 4 (the default)", H2),
            eq(r"k_1=f(t_n,y_n),\;\; k_2=f\left(t_n+\frac{\Delta t}{2},\,y_n+\frac{\Delta t}{2}k_1\right),\;\; "
               r"k_3=f\left(t_n+\frac{\Delta t}{2},\,y_n+\frac{\Delta t}{2}k_2\right),\;\; "
               r"k_4=f(t_n+\Delta t,\,y_n+\Delta t\,k_3)", size=12, number=False),
            eq(r"y_{n+1} \;=\; y_n + \frac{\Delta t}{6}\,(k_1+2k_2+2k_3+k_4)", "rk4"),
            para("RK4 measures the rate of change four times within the step (at the start, twice in the middle, at "
                 "the end) and takes a weighted average. It is <i>fourth-order</i>: halving Δt reduces the error "
                 f"about 16 times. With monthly steps it matches the exact logistic solution ({E('logistic_exact')}) "
                 "closely, as the unit test checks. The management flow M<sub>i</sub>(t) switches on and off at event "
                 "edges; event windows start and end on month boundaries, which are step boundaries, so a cull removes "
                 f"exactly its number ({code('CompetitionModelTest.withoutGrowthACullRemovesExactlyItsNumber')})."),
            para("7.3 Internal steps (model 3)", H2),
            eq(r"h \;=\; \frac{\Delta t}{n}, \qquad n \;=\; \mathrm{ceil}\left(\frac{\Delta t}{h_{\max}}\right)", "substep"),
            para(f"Model 3 changes within weeks (seasons, grass), so it declares a maximum step h<sub>max</sub> = 1/"
                 f"{MAX_STEP_DAYS} year (about a day). The simulator then takes n equal solver steps of size h per "
                 "output step Δt, but still records one row per Δt: with the default monthly Δt that is 31 steps "
                 "per month, and the chart and CSV keep their size. With a plain monthly RK4 step the grass alone "
                 f"would already be about 2% off; {code('SeasonalGrazingModelTest.resultDoesNotDependOnTheOutputStep')} "
                 "checks that the result does not change when Δt is made 4 times finer than h<sub>max</sub>. The "
                 "other models declare no maximum, so n = 1 and nothing changes for them."),
            para("7.4 Extinction rule", H2),
            eq(r"y_{n+1} \;\leftarrow\; \max(0,\; y_{n+1}) \qquad (\mathrm{and}\;\; \mathrm{NaN}\rightarrow 0)", "clamp"),
            para("After every solver step (also every internal step), any population that has become negative (or is "
                 "not a number because of a numerical error) is set to zero. A population can't be negative, and once "
                 "it is zero it stays zero: apart from an introduction event, none of the equations can create animals "
                 "from nothing because every growth term is multiplied by N<sub>i</sub> or W. Grass is clamped the same "
                 "way. Populations are real numbers, not whole animals: the model can show 0.4 wolves. For the report, "
                 "a threshold such as \"fewer than 2 animals = extinct\" may be more realistic."),
            para("7.5 Step size, horizon and replay", H2),
            para(f"Default Δt = 1/12 year (one month), horizon = 20 years, so 240 output steps per run. Both can be "
                 f"changed with {code('--dt')} and {code('--years')} on the command line. {code('--replay YEAR')} "
                 "starts from the counts observed in YEAR, sets startYear = YEAR (so events land on the right dates) "
                 "and applies the known events; this is how model 2 is validated (Section 8.2)."),
            where([[f"Equation ({E('euler')})", f"{code('src/main/java/nl/ovp/solver/EulerSolver.java')} line "
                    f"{line_of('solver/EulerSolver.java', 'return', last=True)}"],
                   [f"Equation ({E('rk4')})", f"{code('src/main/java/nl/ovp/solver/RungeKutta4Solver.java')} lines "
                    f"{line_of('solver/RungeKutta4Solver.java', 'k1')}-"
                    f"{line_of('solver/RungeKutta4Solver.java', 'return', last=True)}"],
                   [f"Equation ({E('substep')})", f"{code('src/main/java/nl/ovp/solver/Simulator.java')} lines "
                    f"{line_of(sim, 'int substeps')}-{line_of(sim, 'for .int k')}; h<sub>max</sub> from "
                    f"{code('PopulationModel.maxStepYears()')}"],
                   [f"Equation ({E('clamp')})", f"{code('Simulator.java')} line "
                    f"{line_of(sim, 'private static void clampExtinct')} ({code('clampExtinct')})"],
                   ["Time loop", f"{code('Simulator.java')} line {line_of(sim, 'public SimulationResult run')}"
                    f" ({code('run')})"],
                   ["Replay", f"{code('src/main/java/nl/ovp/app/Main.java')} line "
                    f"{line_of('app/Main.java', 'static void applyReplay')} ({code('applyReplay')})"]]),
            PageBreak()]

    # ---- 8: parameters
    F, D, G, S, X = ("<font color='#2f8a4a'><b>Fitted</b></font>", "<font color='#2f8a4a'><b>Data</b></font>",
                     "<font color='#e69500'><b>Guess</b></font>", "Scenario", "Fixed")
    L = "<font color='#2f8a4a'><b>Literature</b></font>"
    arf = "AgriculturalRiskFactors first estimate"
    out += [para("8. All parameters", H1),
            para(f"Every number used in equations ({E('logistic')})-({E('clamp')}). Values given as three numbers are "
                 f"for cattle, horses and deer. All live in {code('src/main/java/nl/ovp/model/ModelParameters.java')}."),
            table([["Symbol", "Code field", "Default", "Unit", "Status", "Source"],
                   ["N<sub>i</sub>(0), W(0)", code("initialCattle/Horses /Deer/Wolves"),
                    ", ".join(fmt(v) for v in P["N0"]) + ", 0", "animals", X, "Policy target from the brief; user "
                    "input; --replay uses observed counts"],
                   ["r<sub>i</sub>", code("growthRate"), ", ".join(f"{v:.2f}" for v in r), "1/year", F,
                    "Competition ODE fit to counts 1983-2015 (SE 0.01-0.04)"],
                   ["K<sub>i</sub>", code("carryingCapacity"), ", ".join(fmt(v) for v in K), "animals", F,
                    "Same fit; cattle and deer weakly determined (SE 410, 2,570)"],
                   ["α<sub>ij</sub>", code("competitionAlpha"), "see §4.2", "-", F,
                    "Deer column 0.3 from brief; a, b fitted, weakly determined"],
                   ["s<sub>i</sub>", code("climateSensitivity"), ", ".join(fmt(v, 2) for v in s), "1/°C", G,
                    "Literature on heat stress; sign fixed by brief. Used by models 2 and 3"],
                   ["ΔT", code("deltaT"), "0", "°C", S, "User input (GUI −2 to +6)"],
                   ["t<sub>0</sub>", code("grassOptimumTemperature"), f"{P['t0']:.0f}", "°C", X,
                    "Brief, Appendix 3 (C3 grass)"],
                   ["var", code("grassVar"), f"{P['var']:.0f}", "°C", G,
                    "Not in brief; grass height data do not constrain it"],
                   ["T<sub>mean</sub>", code("meanAnnualTemperature"), f"{P['Tbar']:.1f}", "°C", F,
                    "KNMI monthly means 1983-2017 (9.96)"],
                   ["A", code("seasonalAmplitude"), f"{P['A']:.1f}", "°C", F, "KNMI monthly means 1983-2017"],
                   ["G<sub>max</sub>", code("grassMaxGrowthKgPerHaPerMonth"), f"{P['Gmax']:.0f}", "kg/ha/month", X,
                    "Brief (time unit doubtful, §3)"],
                   ["Area", code("areaHa"), fmt(P["area"]), "ha", X, "Brief (also says 2,000 ha dry). Models 1, 2, 4"],
                   ["A<sub>g</sub>", code("grazingAreaHa"), fmt(P["Ag"]), "ha", L,
                    "Van Geel Committee (2018): grassland after the measures; 1,880 ha before 2018. Model 3"],
                   ["k<sub>G</sub>", code("grassCapacityTPerHa"), f"{P['kG']:g}", "t DM/ha", G, arf],
                   ["r<sub>G</sub>", code("grassGrowthRate"), f"{P['rG']:g}", "1/year", G, arf + " (≈ 6 t DM/ha/yr)"],
                   ["h<sub>G</sub>", code("grassHalfSaturationTPerHa"), f"{P['hG']:g}", "t DM/ha", G, arf],
                   ["d<sub>G</sub>", code("grassWinterDecay"), f"{P['dG']:g}", "1/year", G, arf],
                   ["G(0)/k<sub>G</sub>A<sub>g</sub>", code("initialGrassFraction"), f"{P['G0']:g}", "-", G,
                    "AgriculturalRiskFactors scenario value"],
                   ["q<sub>i</sub>", code("intake"), ", ".join(f"{v:g}" for v in P["q"]), "t DM/animal/yr", G,
                    arf + " (10, 9, 2.7 kg DM/day)"],
                   ["b<sub>i</sub>", code("maxBirthRate"), ", ".join(f"{v:g}" for v in P["b"]), "1/year", G, arf],
                   ["μ<sub>i</sub>", code("backgroundMortality"), ", ".join(f"{v:g}" for v in P["mu"]), "1/year", G, arf],
                   ["ω<sub>i</sub>", code("winterStarvationMortality"), ", ".join(f"{v:g}" for v in P["om"]), "1/year",
                    G, arf + "; calibrate on winter 2017-18"],
                   ["a<sub>i</sub>", code("attackRate"), ", ".join(f"{v:g}" for v in P["a"]), "1/(animal·year)",
                    G, "Wolf kill-rate studies"],
                   ["w<sub>i</sub>", code("preyPreference"), ", ".join(f"{v:g}" for v in P["w"]), "0-1", S,
                    "User input; literature on wolf diet"],
                   ["h", code("handlingTime"), f"{P['h']:g}", "years", G, "Wolf kill-rate studies"],
                   ["e<sub>i</sub>", code("conversionEfficiency"), ", ".join(f"{v:g}" for v in P["e"]), "wolves/kill",
                    G, "Prey mass ÷ food per new wolf; births ≤ 0.32 per wolf (wolf_rates.csv)"],
                   ["m", code("wolfMortality"), f"{P['m']:.2f}", "1/year", D,
                    "wolf_rates.csv: deaths 0.141 + lost 0.090"],
                   ["startYear, events", code("startYear, events"), f"{P['start']:.0f}, none", "year, -", S,
                    "herbivore_events.csv via --replay"],
                   ["Δt, horizon", code("dtYears, horizonYears"), "1/12, 20", "years", X,
                    f"Numerical settings; model 3 steps internally at 1/{MAX_STEP_DAYS} year"]],
                  [1.9, 3.4, 2.1, 1.9, 1.9, 5.2]),
            para("8.1 Calibration", H2),
            para(f"{code('scripts/fit_parameters.py')} fits equation ({E('competition')}) at ΔT = 0 to the counts with "
                 "<i>reliable</i> = True in the natural period (1983-2015; 2016-17 are low-trust, and from winter "
                 "2017-18 on there is a die-off, culling and relocation). Each species starts at its first count; "
                 "horses and deer are introduced in 1984 and 1992. Least squares on log counts, so deer do not swamp "
                 "cattle. A fit with four free competition coefficients is not identifiable (three end on their bounds, "
                 "SE of K larger than K), so the chosen model shares them as a and b (§4.2). Result: R² = 0.95 "
                 "/ 0.98 / 0.97 for cattle / horses / deer. Including 2016-17 changes r by &lt; 0.01 and K by up to 18%. "
                 f"Details: {code('docs/CALIBRATION.md')}, {code('docs/calibration_fit.csv')}. Model 3 is not "
                 "calibrated yet.")]
    if os.path.exists(os.path.join("docs", "figures", "validation.png")):
        img = plt.imread(os.path.join("docs", "figures", "validation.png"))
        out += [Image(os.path.join("docs", "figures", "validation.png"), width=16.4 * cm,
                      height=16.4 * cm * img.shape[0] / img.shape[1]),
                para("Calibrated competition model run by the app (lines) against the counts (points; hollow = "
                     f"low trust). Left: {code('--replay 1983')}. Right: {code('--replay 2017')} with the die-off, culls "
                     f"and relocations as input. Made by {code('scripts/plot_validation.py')}.", CAPTION)]
    out += [para("8.2 Validation", H2),
            para("Model 2, fit period 1983-2017: mean absolute error 16% (cattle), 13% (horses), 7% (deer). Out of "
                 "sample 2018-2025: 55-74%. The out-of-sample test is inconclusive rather than a failure of the model: "
                 "the 2016-2024 counts are low-trust, deer <i>rose</i> by 875 in 2019-2020 while 1,785 were being shot "
                 "(more than r allows), and the counts are probably autumn counts, not 1 January counts: the 2017 count "
                 "(230 / 1,050 / 3,950) is exactly the Van Geel Committee's October 2017 figure, and 2016 → 2017 "
                 "(+730) matches its \"almost +700, November 2016 - November 2017\". Models 1, 2 and 4 have no winter "
                 "starvation of their own; model 3 does (Section 5.3)."),
            para("9. Points to check before writing the report", H1),
            table([["#", "Point", "Why it matters"],
                   ["1", "Weakly determined K (cattle, deer) and α (a, b).", "The fit reproduces 1983-2017 well, "
                    "but these values are not pinned down by the data. Run question A and C scenarios over their "
                    "ranges (± 1 SE) and report whether conclusions change."],
                   ["2", "No coexistence of all three species.", "In model 2 cattle are slowly excluded (§4.4), "
                    "consistent with the data. In model 3, with the provisional parameters, cattle win instead (§5.3). "
                    "Say that it depends on the parameters, and that management can change it."],
                   ["3", "Check that warming harms cattle.", "With the current s<sub>i</sub> and var the grass factor "
                    "wins and cattle K rises with temperature in model 2 (§4.3), contradicting the brief."],
                   ["4", "Wolf attack rates look far too low.", f"One wolf kills about {kills:.1f} animals per year at "
                    "the policy target (§6.3); real wolves kill around 15-25. Released wolves always die out "
                    "until this is fixed. m is from data (0.23)."],
                   ["5", "When are the counts made?", "Evidence points to autumn (§8.2). Ask the lecturer; it shifts "
                    "the start of every replay and the event timing."],
                   ["6", "Event assumptions.", "The die-off (Dec 2017 - Mar 2018) is shared over the species in "
                    "proportion to their numbers, and the 560 horses are spread evenly over 2018-2021; the source "
                    "gives no split or months. Do not use the die-off event with model 3 (§5.3)."],
                   ["7", "Model 3 is not calibrated.", "Fit b<sub>i</sub>, μ<sub>i</sub>, ω<sub>i</sub> and the grass "
                    "constants on the 1983-2015 counts with A<sub>g</sub> = 1,880 ha, and check ω<sub>i</sub> against "
                    "the NOS winter deaths 2010-2018 and the 2017-18 die-off."],
                   ["8", "Which grazing area?", "The brief gives 5,600 ha (Appendix 3) and 2,000 ha dry land (§2.5.1); "
                    "Van Geel gives 1,880 ha until 2018 and 1,080 ha after the measures. Model 3 depends on it directly."],
                   ["9", f"The time unit of G<sub>max</sub>.", "Per month (as coded) the grass could not have fed the "
                    "observed herds (§3); per day it is realistic. Models 2 and 3 are not affected as built, but any "
                    "use of absolute yields is."],
                   ["10", "Drought and water are not modelled.", "Research question C mentions dry seasons; the grass "
                    "formula only depends on temperature (KNMI'23 also projects summer drought)."],
                   ["11", "Fractional animals.", "The model works with real numbers (0.4 wolves). Consider an "
                    "extinction threshold when presenting results."]], [0.8, 5.0, 10.6])]
    return out


def _render(target):
    _EQ["n"], _EQ["num"], _EQ["page"] = 0, {}, {}
    doc = TrackingDoc(target, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                      bottomMargin=2 * cm, title="Model Equations: Oostvaardersplassen population model",
                      author="Oostvaardersplassen project team", subject="Explanation of the model equations")
    doc.build(story(), onFirstPage=decorate, onLaterPages=decorate)
    return doc


def build(out=OUT):
    """Builds the PDF and returns its index: equation numbers and pages, section pages."""
    first = _render(io.BytesIO())              # pass 1: number the equations, find the pages
    _EQ["prev"] = dict(_EQ["num"])
    _EQ["prev_sections"] = dict(first.sections)
    doc = _render(out)                         # pass 2: print the cross-references
    if _EQ["num"] != _EQ["prev"] or {k: v["page"] for k, v in doc.sections.items()} != \
            {k: v["page"] for k, v in first.sections.items()}:
        raise SystemExit("equation numbers or section pages changed between passes")
    print(f"Wrote {out} ({_EQ['n']} numbered equations, {doc.page} pages)")
    return {"equations": {k: {"number": n, "page": _EQ["page"][k]} for k, n in _EQ["num"].items()},
            "sections": doc.sections, "pages": doc.page}


if __name__ == "__main__":
    build()
