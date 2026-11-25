"""
Fit the herbivore growth parameters of ModelParameters to the observed counts.

Usage (from the repository root):
    python3 scripts/fit_parameters.py            # prints tables, writes docs/calibration_fit.csv

Data: data/clean/herbivores_counts.csv, natural period 1983-2017 only (from winter 2017-18 on
there is a die-off, culling and relocation). Each species starts at its first real count
(cattle 1983, horses 1984, deer 1992); empty cells are gaps, never zeros. Two variants:
    "reliable"  - rows with reliable = False (2016, 2017) dropped   <- used for the defaults
    "all"       - 1983-2017 including 2016-2017                      <- sensitivity check

Step 1 - logistic, per species, closed form (Gotelli ch. 2):
    N(t) = K / (1 + ((K - N0)/N0) * exp(-r t)),  N0 = first count, t = years since that count.
Step 2 - Lotka-Volterra competition, the same ODE as CompetitionModel.java at deltaT = 0
    (then grassFactor = 1 and the climate factor = 1):
    dN_i/dt = r_i N_i (1 - sum_j alpha_ij N_j / K_i)
    alpha_ii = 1; alpha_cattle,deer = alpha_horses,deer = 0.3 are fixed by the brief.
    Full model (diagnostic): r (3), K (3) and four free off-diagonal alphas. It fits well but is
    NOT identifiable (three alphas end on their bounds, SE(K) > K), so the defaults use
    Constrained model (chosen): r (3), K (3) and two alphas:
        a = alpha_cattle,horses = alpha_horses,cattle   (cattle and horses: same grazing guild,
                                                          symmetric overlap)
        b = alpha_deer,cattle   = alpha_deer,horses     (effect of either grazer on deer)
    Horses (20) and deer (45) are added at the start of their first counted year, like the
    introduction events in data/clean/herbivore_events.csv. Residuals are on log counts so that
    the deer (thousands) do not swamp the cattle (hundreds).
Standard errors come from the Jacobian at the optimum (J^T J)^-1 * s^2; for the ODE fit they
are approximate (log residuals, autocorrelated counts) and mainly flag non-identifiability.

Requires: pandas, numpy, scipy
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit, least_squares

SPECIES = ["cattle", "horses", "deer"]
LAST_YEAR = 2017
ALPHA_FIXED = {(0, 2): 0.3, (1, 2): 0.3}                 # deer -> cattle, deer -> horses (brief)
ALPHA_FREE = [(0, 1), (1, 0), (2, 0), (2, 1)]           # fitted off-diagonal entries
NAMES = ["r_cattle", "r_horses", "r_deer", "K_cattle", "K_horses", "K_deer",
         "alpha_cattle_horses", "alpha_horses_cattle", "alpha_deer_cattle", "alpha_deer_horses"]


def load(variant):
    d = pd.read_csv(os.path.join("data", "clean", "herbivores_counts.csv"))
    d = d[d.year <= LAST_YEAR]
    if variant == "reliable":
        d = d[d.reliable.astype(str) == "True"]
    return d


# ----------------------------------------------------------------------------- logistic
def logistic(t, r, K, n0):
    return K / (1 + (K - n0) / n0 * np.exp(-r * t))


def fit_logistic(d):
    rows = []
    for sp in SPECIES:
        s = d[["year", sp]].dropna()
        y0, n0 = int(s.year.iloc[0]), float(s[sp].iloc[0])
        t, n = (s.year - y0).to_numpy(float), s[sp].to_numpy(float)
        (r, K), cov = curve_fit(lambda tt, r, K: logistic(tt, r, K, n0), t, n,
                                p0=[0.25, n.max()], bounds=([1e-6, 1.0], [5.0, 1e6]))
        se = np.sqrt(np.diag(cov))
        pred = logistic(t, r, K, n0)
        r2 = 1 - np.sum((n - pred) ** 2) / np.sum((n - n.mean()) ** 2)
        rows.append(dict(species=sp, years=f"{y0}-{int(s.year.iloc[-1])}", n=len(s),
                         r=r, r_se=se[0], K=K, K_se=se[1], R2=r2,
                         RMSE=np.sqrt(np.mean((n - pred) ** 2))))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- competition
def full_from_constrained(p):
    """8 constrained parameters -> the 10 of the full model."""
    return np.r_[p[:6], p[6], p[6], p[7], p[7]]


def unpack(theta):
    r, K = theta[0:3], theta[3:6]
    a = np.eye(3)
    for (i, j), v in ALPHA_FIXED.items():
        a[i, j] = v
    for (i, j), v in zip(ALPHA_FREE, theta[6:10]):
        a[i, j] = v
    return r, K, a


def rhs(_t, y, r, K, a):
    y = np.maximum(y, 0.0)
    return r * y * (1 - a @ y / K)


def simulate(theta, years):
    """State on 1 January of each year in `years` (sorted, starting 1983)."""
    r, K, a = unpack(theta)
    y = np.array([30.0, 0.0, 0.0])
    out = {}
    for year in range(1983, int(years[-1]) + 1):
        if year == 1984:
            y[1] += 20.0
        if year == 1992:
            y[2] += 45.0
        out[year] = y.copy()
        sol = solve_ivp(rhs, (0, 1), y, args=(r, K, a), method="LSODA", rtol=1e-8, atol=1e-6)
        y = sol.y[:, -1]
    return np.array([out[int(yr)] for yr in years])


def residuals(theta, d):
    years = d.year.to_numpy()
    sim = simulate(theta, years)
    res = []
    for k, sp in enumerate(SPECIES):
        obs = d[sp].to_numpy(float)
        ok = ~np.isnan(obs) & (obs > 0)
        res.append(np.log(np.maximum(sim[ok, k], 1e-3)) - np.log(obs[ok]))
    return np.concatenate(res)


CONSTRAINED_NAMES = NAMES[:6] + ["a (cattle<->horses)", "b (cattle,horses -> deer)"]


def fit_competition(d, start, constrained):
    k_alpha = 2 if constrained else 4
    to_full = full_from_constrained if constrained else (lambda p: p)
    names = CONSTRAINED_NAMES if constrained else NAMES
    lo = [1e-3] * 3 + [10.0] * 3 + [0.0] * k_alpha
    hi = [3.0] * 3 + [1e5] * 3 + [3.0] * k_alpha
    fit = least_squares(lambda p: residuals(to_full(p), d), start, bounds=(lo, hi), x_scale="jac")
    dof = max(len(fit.fun) - len(fit.x), 1)
    rss = np.sum(fit.fun ** 2)
    se = np.sqrt(np.diag(np.linalg.pinv(fit.jac.T @ fit.jac)) * rss / dof)
    aic = len(fit.fun) * np.log(rss / len(fit.fun)) + 2 * len(fit.x)
    at_bound = [names[k] for k in range(len(fit.x))
                if np.isclose(fit.x[k], lo[k], rtol=1e-3, atol=1e-4) or np.isclose(fit.x[k], hi[k], rtol=1e-3)]
    theta = to_full(fit.x)
    sim = simulate(theta, d.year.to_numpy())
    quality = []
    for k, sp in enumerate(SPECIES):
        obs = d[sp].to_numpy(float)
        ok = ~np.isnan(obs) & (obs > 0)
        e = obs[ok] - sim[ok, k]
        quality.append(dict(species=sp, n=int(ok.sum()),
                            R2=1 - np.sum(e ** 2) / np.sum((obs[ok] - obs[ok].mean()) ** 2),
                            RMSE=np.sqrt(np.mean(e ** 2))))
    return fit.x, theta, se, aic, at_bound, pd.DataFrame(quality), names


def equilibrium(theta):
    r, K, a = unpack(theta)
    return np.linalg.solve(a, K)


def jacobian_eigs(theta, n_star):
    r, K, a = unpack(theta)
    J = -np.diag(r * n_star / K) @ a
    return np.linalg.eigvals(J)


def main():
    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", lambda v: f"{v:.4g}")
    results = []
    for variant in ["reliable", "all"]:
        d = load(variant)
        print(f"\n=== variant: {variant}  (years {d.year.min()}-{d.year.max()}, {len(d)} rows) ===")
        lg = fit_logistic(d)
        print("\nLogistic, per species (closed form):")
        print(lg.to_string(index=False))

        base = list(lg.r.to_numpy()) + [600.0, 1500.0, 4000.0]
        for constrained in (False, True):
            label = "competition (constrained, chosen)" if constrained else "competition (full, diagnostic)"
            start = base + ([0.3, 0.2] if constrained else [0.2, 0.2, 0.1, 0.1])
            x, theta, se, aic, at_bound, q, names = fit_competition(d, start, constrained)
            print(f"\n{label}, log residuals, AIC {aic:.1f}")
            for name, v, e in zip(names, x, se):
                print(f"   {name:26s} {v:10.4g}  SE {e:10.3g}")
            print("   at a bound:", at_bound or "none")
            print(q.to_string(index=False))
            n_star = equilibrium(theta)
            eig = jacobian_eigs(theta, n_star)
            print(f"   coexistence equilibrium N* = {np.round(n_star, 0)}, "
                  f"Jacobian eigenvalues {np.round(eig.real, 3)} -> "
                  f"{'stable coexistence' if np.all(n_star > 0) and np.all(eig.real < 0) else 'no stable coexistence'}")
            model = "constrained" if constrained else "full"
            for name, v, e in zip(names, x, se):
                results.append(dict(variant=variant, model=model, parameter=name, value=v, se=e))
            results.append(dict(variant=variant, model=model, parameter="AIC", value=aic, se=np.nan))
            for _, row in q.iterrows():
                results.append(dict(variant=variant, model=model, parameter=f"R2_{row.species}", value=row.R2, se=np.nan))
                results.append(dict(variant=variant, model=model, parameter=f"RMSE_{row.species}", value=row.RMSE, se=np.nan))
            for k, sp in enumerate(SPECIES):
                results.append(dict(variant=variant, model=model, parameter=f"Nstar_{sp}", value=n_star[k], se=np.nan))

        for _, row in lg.iterrows():
            results.append(dict(variant=variant, model="logistic", parameter=f"r_{row.species}", value=row.r, se=row.r_se))
            results.append(dict(variant=variant, model="logistic", parameter=f"K_{row.species}", value=row.K, se=row.K_se))

    os.makedirs("docs", exist_ok=True)
    pd.DataFrame(results).to_csv(os.path.join("docs", "calibration_fit.csv"), index=False)
    print("\nWrote docs/calibration_fit.csv")


if __name__ == "__main__":
    if not os.path.exists(os.path.join("data", "clean", "herbivores_counts.csv")):
        sys.exit("Run from the repository root.")
    main()
