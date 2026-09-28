"""Estimation for the menu price study, driven by its own diagnostics.

The specification is not asserted. It is **derived**. Each modelling choice is a
gate: run a test, read the number, and the number decides the next step. The
sequence of gates is the audit trail, and it is what the paper reports as
methodology rather than a list of tests bolted on at the end.

The cascade
-----------

===  ==========================================  =============================
 1   Is the outcome linear in levels or logs?    picks the dependent variable
 2   Do dishes differ enough to need own means?  pooled OLS or item fixed effects
 3   Does every dish identify the contrast?      the effective estimation sample
 4   Is the error variance constant?             classical or robust errors
 5   Are errors correlated inside a dish?        cluster or do not
 6   Are there enough clusters for asymptotics?  analytic or bootstrap inference
 7   Are the residuals normal?                   confirms or overturns gate 6
 8   Does one dish carry the whole estimate?     report leave one dish out
 9   Is the per-unit result robust to the         list price or unit price as
     quantity rule?                               the primary specification
10   Does the rank test agree with the model?    which result leads the paper
===  ==========================================  =============================

A gate that fails is not a problem to hide. It is the reason the next step is
what it is. Gate 6 is the clearest case: 28 clusters is below every published
rule of thumb, so the bootstrap is not a robustness extra, it is the inference.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset

#: Below this many clusters the asymptotic cluster-robust variance is known to
#: over-reject. Cameron and Miller survey the evidence; 42 is the commonly cited
#: line and the study has 28, so the gate fails and the bootstrap takes over.
MIN_CLUSTERS_ASYMPTOTIC = 42

#: Conventional size for every diagnostic in the cascade. Fixed once here so no
#: test gets a threshold chosen after its result was seen.
ALPHA = 0.05

#: Replications for the wild cluster bootstrap. 9999 so the p value is stable in
#: the third decimal, which matters when the asymptotic p sits near 0.05.
N_BOOT = 9999

BOOT_SEED = 753


@dataclass(frozen=True)
class Gate:
    """One decision in the cascade, with the number that forced it."""

    step: int
    question: str
    test: str
    statistic: float | None
    pvalue: float | None
    threshold: str
    verdict: str
    consequence: str

    def as_row(self) -> dict:
        return asdict(self)


def _fmt_p(p: float | None) -> str:
    if p is None:
        return ""
    return "<0.001" if p < 0.001 else f"{p:.3f}"


# --- the estimation sample --------------------------------------------------

def prepare(df: pd.DataFrame, outcome: str = "unit_price",
            drop_unreliable: bool = True) -> pd.DataFrame:
    """Attach the regression variables and drop rows that cannot identify beta.

    ``owned_kitchen`` is the regressor of interest. ``snacky`` carries H2 and
    enters only through an interaction, because its main effect is collinear
    with the dish fixed effect.
    """
    required = {"platform", "matched_id", "section", outcome, "cell_weight"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"prepare missing columns: {missing}")

    d = df.copy()
    d["owned_kitchen"] = (d["platform"] == "Bistro").astype(int)
    d["snacky"] = (~d["section"].isin(["Meals", "All Day Breakfast"])).astype(int)
    if drop_unreliable and "serving_unreliable" in d.columns:
        d = d[~d["serving_unreliable"].fillna(False).astype(bool)]
    d = d[d[outcome].notna() & (d[outcome] > 0)].copy()
    d["y"] = np.log(d[outcome])
    return d


def identified_dishes(d: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """Keep only dishes carrying both an owned kitchen and a marketplace quote.

    A dish observed on one side contributes nothing to a within-dish contrast.
    Leaving it in inflates the row count and moves nothing, which flatters the
    reported sample size without adding information.
    """
    ok = d.groupby("matched_id")["owned_kitchen"].nunique() == 2
    dropped = sorted(ok.index[~ok])
    return d[d["matched_id"].isin(ok.index[ok])].copy(), dropped


# --- fitting ----------------------------------------------------------------

def _fit(d: pd.DataFrame, formula: str, weighted: bool, cluster: bool):
    w = d["cell_weight"] if weighted else None
    model = smf.wls(formula, data=d, weights=w) if weighted else smf.ols(formula, data=d)
    if cluster:
        return model.fit(cov_type="cluster", cov_kwds={"groups": d["matched_id"]})
    return model.fit()


def fit_pooled(d: pd.DataFrame, weighted: bool = True, cluster: bool = True):
    """Model 1. Section dummies only, no dish means. The weak baseline."""
    return _fit(d, "y ~ owned_kitchen + C(section)", weighted, cluster)


def fit_item_fe(d: pd.DataFrame, weighted: bool = True, cluster: bool = True):
    """Model 2. Dish fixed effects. The main specification."""
    return _fit(d, "y ~ owned_kitchen + C(matched_id)", weighted, cluster)


def fit_interaction(d: pd.DataFrame, weighted: bool = True, cluster: bool = True):
    """Model 3. H2. Snacky enters only interacted, its level is absorbed."""
    return _fit(d, "y ~ owned_kitchen + owned_kitchen:snacky + C(matched_id)",
                weighted, cluster)


def coef(fit, name: str = "owned_kitchen") -> dict:
    """Point estimate, standard error, t, p and interval, in one dict."""
    ci = fit.conf_int().loc[name]
    return {"beta": float(fit.params[name]), "se": float(fit.bse[name]),
            "t": float(fit.tvalues[name]), "p": float(fit.pvalues[name]),
            "ci_lo": float(ci[0]), "ci_hi": float(ci[1]),
            "pct": float(np.exp(fit.params[name]) - 1), "n": int(fit.nobs)}


# --- inference that does not lean on asymptotics ----------------------------

def wild_cluster_bootstrap(d: pd.DataFrame, formula: str = "y ~ owned_kitchen + C(matched_id)",
                           param: str = "owned_kitchen", weighted: bool = True,
                           n_boot: int = N_BOOT, seed: int = BOOT_SEED) -> dict:
    """Wild cluster bootstrap t, imposing the null, with Rademacher weights.

    With 28 clusters the analytic cluster-robust variance over-rejects. The
    restricted bootstrap resamples residuals from the model with beta forced to
    zero, so the reference distribution is built under the hypothesis actually
    being tested rather than under the estimate.
    """
    fit = _fit(d, formula, weighted, cluster=True)
    t_obs = float(fit.tvalues[param])

    restricted_formula = formula.replace(f"{param} + ", "").replace(f" + {param}", "")
    r = _fit(d, restricted_formula, weighted, cluster=True)
    y_hat, resid = r.fittedvalues.to_numpy(), r.resid.to_numpy()

    groups = d["matched_id"].to_numpy()
    uniq = np.unique(groups)
    idx = {g: np.flatnonzero(groups == g) for g in uniq}
    rng = np.random.default_rng(seed)

    work = d.copy()
    t_star = np.empty(n_boot)
    for b in range(n_boot):
        v = rng.choice((-1.0, 1.0), size=len(uniq))
        mult = np.empty(len(groups))
        for w_, g in zip(v, uniq):
            mult[idx[g]] = w_
        work["y"] = y_hat + mult * resid
        t_star[b] = float(_fit(work, formula, weighted, cluster=True).tvalues[param])

    p = float((np.abs(t_star) >= abs(t_obs)).mean())
    return {"t_obs": t_obs, "p_boot": p, "n_boot": n_boot,
            "crit_lo": float(np.quantile(t_star, ALPHA / 2)),
            "crit_hi": float(np.quantile(t_star, 1 - ALPHA / 2))}


def leave_one_dish_out(d: pd.DataFrame, weighted: bool = True) -> pd.DataFrame:
    """Refit dropping each dish in turn. With 28 clusters this is not optional."""
    rows = []
    for mid in sorted(d["matched_id"].unique()):
        sub = d[d["matched_id"] != mid]
        c = coef(fit_item_fe(sub, weighted=weighted))
        rows.append({"dropped_dish": mid, "beta": c["beta"], "p": c["p"]})
    return pd.DataFrame(rows)


# --- the delta identity -----------------------------------------------------

def delta_bridge(d: pd.DataFrame) -> dict:
    """``beta_list = beta_unit + Delta``, an identity, not a second estimate.

    Because ``log(p/u) = log(p) - log(u)``, running the model on unit price is
    the same as running it on list price with the log quantity gap subtracted.
    Delta is therefore the exact amount normalisation moves the headline, and it
    is a parameter chosen by assumption rather than a cleaning step.
    """
    if "units" not in d.columns:
        raise KeyError("delta_bridge needs a units column")
    lp = d.assign(y=np.log(d["list_price"]))
    up = d.assign(y=np.log(d["list_price"] / d["units"]))
    lu = d.assign(y=np.log(d["units"]))

    b_list = coef(fit_item_fe(lp))
    b_unit = coef(fit_item_fe(up))
    b_delta = coef(fit_item_fe(lu))
    return {"beta_list": b_list["beta"], "beta_unit": b_unit["beta"],
            "delta": b_delta["beta"], "delta_se": b_delta["se"],
            "identity_gap": b_list["beta"] - b_unit["beta"] - b_delta["beta"]}


# --- H3, arithmetic rather than estimation ----------------------------------

def fee_wedge_scenario(beta: float, wedges: dict[str, float],
                       owned: str = "Bistro") -> pd.DataFrame:
    """Shift beta by the observed checkout wedge. Deterministic, so the standard
    error is unchanged and reporting one would be a fabrication."""
    w_own = wedges[owned]
    rows = []
    for platform, w in wedges.items():
        if platform == owned:
            continue
        shift = np.log1p(w_own) - np.log1p(w)
        rows.append({"platform": platform, "wedge": w, "log_shift": shift,
                     "beta_list": beta, "beta_delivered": beta + shift,
                     "pct_delivered": np.exp(beta + shift) - 1})
    return pd.DataFrame(rows)


#: Basket sizes at which to evaluate the wedge, in rupees. The lower end is a
#: single Bistro item and the upper end is well above any plausible food
#: delivery average order value, so the reported range brackets reality rather
#: than assuming a point inside it.
BASKET_GRID = (149, 200, 300, 400, 500, 700)


def _fee_split(r) -> tuple[float, float]:
    """Rupees fixed per order, and the share of order value that scales."""
    fixed = sum(x for x in (r.get("delivery_fee"), r.get("platform_fee"),
                            r.get("convenience_fee")) if pd.notna(x))
    var = sum(x for x in (r.get("packaging_fee"), r.get("gst_and_other"))
              if pd.notna(x))
    disc = r.get("order_discount")
    var -= disc if pd.notna(disc) else 0.0
    return fixed, max(var, 0.0) / r["item_total"]


def checkout_comparison(beta: float, fees: pd.DataFrame,
                        discounts: pd.DataFrame | None = None,
                        owned: str = "Bistro", owned_discount: float = 0.0,
                        baskets=BASKET_GRID) -> pd.DataFrame:
    """What each platform actually charges for the same food, end to end.

    Combines three things the menu coefficient deliberately excludes: the fixed
    and proportional parts of the fee stack, the coupon available at that basket
    size, and any promotion the owned kitchen is itself running.

    ``discounts`` is the frame from :func:`offers.discount_curve`. Passing None
    reproduces the no coupon case. ``owned_discount`` is a share off the owned
    kitchen's basket, because Bistro was observed running a basket promotion of
    its own and assuming it never discounts would be the same error in reverse.
    """
    own_f, own_v = _fee_split(fees.loc[owned])
    rows = []
    for platform in fees.index:
        if platform == owned:
            continue
        f, v = _fee_split(fees.loc[platform])
        for x in baskets:
            d = {"none": 0.0}
            if discounts is not None:
                sel = discounts[(discounts.platform == platform)
                                & (discounts.basket == x)]
                if len(sel):
                    d["typical coupon"] = float(sel.typical_pct.iloc[0]) * x
                    d["best coupon"] = float(sel.best_pct.iloc[0]) * x
            for label, cut in d.items():
                own_pay = (x * np.exp(beta) * (1 - owned_discount)) * (1 + own_v) + own_f
                mkt_pay = (x - cut) * (1 + v) + f
                rows.append({"platform": platform, "basket": x, "coupon": label,
                             "coupon_pct": cut / x, "owned_pays": own_pay,
                             "marketplace_pays": mkt_pay,
                             "gap": own_pay / mkt_pay - 1})
    return pd.DataFrame(rows)


def fee_wedge_curve(beta: float, fees: pd.DataFrame, owned: str = "Bistro",
                    baskets=BASKET_GRID) -> pd.DataFrame:
    """The delivered gap as a function of basket size, not at one basket.

    A single checkout capture gives the wedge at one order value, and quoting
    that one number assumes every platform's basket is the same size. It is not.
    Bistro is positioned at low order values and a marketplace order is larger,
    so the single item wedge flatters Bistro by charging a whole fixed delivery
    fee to one dish.

    Fees split into a part that is fixed per order, delivery and platform, and a
    part that scales with order value, packaging and tax. The fixed part is what
    shrinks as a basket grows. Reporting the gap across a grid of baskets makes
    the reader's own view of average order value the input rather than the
    author's.
    """
    def split(r):
        fixed = sum(x for x in (r.get("delivery_fee"), r.get("platform_fee"),
                                r.get("convenience_fee")) if pd.notna(x))
        var = sum(x for x in (r.get("packaging_fee"), r.get("gst_and_other"))
                  if pd.notna(x))
        disc = r.get("order_discount")
        var -= disc if pd.notna(disc) else 0.0
        return fixed, max(var, 0.0) / r["item_total"]

    own_f, own_v = split(fees.loc[owned])
    rows = []
    for platform in fees.index:
        if platform == owned:
            continue
        f, v = split(fees.loc[platform])
        for x in baskets:
            w_own, w = own_f / x + own_v, f / x + v
            # The menu gap applies to the food, then each platform's fees go on.
            own_pay = x * np.exp(beta) * (1 + w_own)
            mkt_pay = x * (1 + w)
            rows.append({"platform": platform, "basket": x, "wedge": w,
                         "owned_wedge": w_own, "owned_pays": own_pay,
                         "marketplace_pays": mkt_pay,
                         "delivered_gap": own_pay / mkt_pay - 1})
    return pd.DataFrame(rows)


# --- the nonparametric check ------------------------------------------------

def rank_test(ranks: pd.Series) -> dict:
    """Wilcoxon signed rank and a sign test on within-dish percentile ranks.

    Uses only the ordering of prices inside a dish, so no quantity decision in
    the pipeline can move it. That is why it is the check the model is measured
    against and not the other way round.
    """
    r = pd.Series(ranks).dropna()
    d = r - 0.5
    nz = d[d != 0]
    w = stats.wilcoxon(nz) if len(nz) else None
    below = int((r < 0.5).sum())
    sign_p = float(stats.binomtest(below, len(r), 0.5).pvalue) if len(r) else np.nan
    return {"n_dishes": int(len(r)), "mean_rank": float(r.mean()),
            "median_rank": float(r.median()), "n_below_half": below,
            "wilcoxon_stat": float(w.statistic) if w else np.nan,
            "wilcoxon_p": float(w.pvalue) if w else np.nan,
            "sign_p": sign_p}


# --- how much of the answer is the quantity rule? ---------------------------

#: Piece counts to force onto unstated marketplace listings as a bound. A
#: listing that says nothing is rarely a ten piece box, and almost never one
#: piece either, so two and three bracket the plausible range.
WORST_CASE_PIECES = (2, 3)


def quantity_sensitivity(panel: pd.DataFrame) -> pd.DataFrame:
    """Refit under every defensible treatment of an unstated quantity.

    Two thirds of marketplace rows state no quantity. The pipeline reads that as
    one serving, which is the natural default and is also the treatment most
    favourable to the hypothesis, because a listing that is really two pieces
    gets its whole price charged to a single unit.

    The opposite correction is the median stated quantity within the same dish.
    That over-corrects, because a listing states its count precisely when it is
    a multi-pack and stays silent when it is a single serving. The truth is
    between the two, so both are reported as bounds rather than one being
    presented as the answer.
    """
    from . import menu as _menu

    def _beta(df, outcome):
        # The serving-comparability flag is a normalisation concern. It has no
        # bearing on a list price, so it must not shrink that sample.
        x = prepare(df, outcome=outcome, drop_unreliable=(outcome != "list_price"))
        x, _ = identified_dishes(x)
        c = coef(fit_item_fe(x))
        c["n"] = len(x)
        return c

    rows = []

    c = _beta(panel, "unit_price")
    rows.append({"treatment": "unstated read as one serving", "assumption": "favours",
                 **c})

    q = panel.copy()
    q.loc[q["qty_source"] == "assumed", "units"] = np.nan
    q = _menu.impute_quantity(q)
    q["unit_price"] = q["list_price"] / q["units"]
    rows.append({"treatment": "imputed from the dish median", "assumption": "against",
                 **_beta(q.dropna(subset=["unit_price"]), "unit_price")})

    for k in WORST_CASE_PIECES:
        z = panel.copy()
        m = (z["qty_source"] == "assumed") & (z["platform"] != "Bistro") & \
            (z["basis"] == "piece")
        z.loc[m, "units"] = k
        z["unit_price"] = z["list_price"] / z["units"]
        rows.append({"treatment": f"every unstated piece listing is {k} pieces",
                     "assumption": "against", **_beta(z, "unit_price")})

    rows.append({"treatment": "list price, quantity never used", "assumption": "none",
                 **_beta(panel, "list_price")})

    out = pd.DataFrame(rows)
    return out[["treatment", "assumption", "beta", "se", "p", "n"]]


# --- the cascade ------------------------------------------------------------

def run_cascade(panel: pd.DataFrame, outcome: str = "unit_price",
                ranks: pd.Series | None = None,
                n_boot: int = N_BOOT) -> tuple[pd.DataFrame, dict]:
    """Walk the nine gates and return the audit trail plus the chosen model.

    Every gate reads a number and hands the next one a decision. Nothing here is
    chosen by preference, which is the point: a reader can disagree with a
    threshold, see exactly which gate it feeds and follow the consequence.
    """
    gates: list[Gate] = []
    d = prepare(panel, outcome=outcome)

    # Gate 1. Levels or logs. Decided on residual behaviour, not on convention.
    lvl = smf.ols(f"{outcome} ~ owned_kitchen + C(matched_id)", data=d).fit()
    log = smf.ols("y ~ owned_kitchen + C(matched_id)", data=d).fit()
    sk_lvl, sk_log = float(stats.skew(lvl.resid)), float(stats.skew(log.resid))
    reset_log = linear_reset(log, power=2, use_f=True)
    gates.append(Gate(
        1, "Is the outcome linear in levels or in logs?",
        "residual skewness, levels against logs, and Ramsey RESET on the log fit",
        round(sk_log, 3), float(reset_log.pvalue),
        f"pick the form with less residual skew; RESET p > {ALPHA}",
        f"skew falls from {sk_lvl:.2f} in levels to {sk_log:.2f} in logs; "
        f"RESET p = {_fmt_p(float(reset_log.pvalue))}",
        "log price is the dependent variable, and beta reads as a percentage gap",
    ))

    # Gate 2. Poolability. Do dishes need their own intercepts?
    pooled = smf.ols("y ~ owned_kitchen + C(section)", data=d).fit()
    f_stat, f_p, _ = log.compare_f_test(pooled)
    b_pool = float(pooled.params["owned_kitchen"])
    b_fe = float(log.params["owned_kitchen"])
    gates.append(Gate(
        2, "Do dishes differ enough to need their own intercepts?",
        "F test on the joint significance of the dish dummies",
        float(f_stat), float(f_p), f"reject at {ALPHA} means pooled OLS is misspecified",
        f"F = {f_stat:.1f}, p = {_fmt_p(float(f_p))}; beta moves from "
        f"{b_pool:+.3f} pooled to {b_fe:+.3f} with dish effects",
        "item fixed effects, Model 2. The gap between the two betas is the "
        "assortment composition effect, and it is reported rather than hidden",
    ))

    # Gate 3. Is the contrast identified dish by dish?
    d_id, dropped = identified_dishes(d)
    gates.append(Gate(
        3, "Does every dish actually identify the contrast?",
        "count of dishes holding both an owned kitchen and a marketplace quote",
        float(d_id["matched_id"].nunique()), None,
        "a dish seen on one side only contributes nothing within",
        f"{d_id['matched_id'].nunique()} dishes identify beta, {len(dropped)} dropped"
        + (f" (ids {dropped})" if dropped else ""),
        f"the estimation sample is {len(d_id)} rows over "
        f"{d_id['matched_id'].nunique()} dishes",
    ))

    fit_plain = fit_item_fe(d_id, cluster=False)

    # Gate 4. Constant error variance.
    # White is not available here and saying so is more honest than printing the
    # number it returns. Its auxiliary regression adds squares and cross products,
    # and a dummy squared is the dummy, so with dish fixed effects the auxiliary
    # design is rank deficient by construction. Breusch-Pagan carries the gate.
    bp = het_breuschpagan(fit_plain.resid, fit_plain.model.exog)
    het = bp[1] < ALPHA
    gates.append(Gate(
        4, "Is the error variance constant?",
        "Breusch-Pagan. White is not identified once dish dummies are included",
        float(bp[0]), float(bp[1]), f"reject at {ALPHA} means classical errors are invalid",
        f"Breusch-Pagan p = {_fmt_p(float(bp[1]))}; "
        + ("heteroscedastic" if het else "no evidence against constant variance")
        + ". White is rank deficient in a fixed effects design and is not reported",
        "robust standard errors, which the clustered errors in gate 5 already are"
        if het else "classical errors would suffice, robust reported anyway",
    ))

    # Gate 5. Correlation inside a dish.
    resid = pd.Series(fit_plain.resid, index=d_id.index)
    grp = resid.groupby(d_id["matched_id"])
    icc = float(grp.mean().var(ddof=1) / resid.var(ddof=1)) if resid.var(ddof=1) else np.nan
    fit_cl = fit_item_fe(d_id, cluster=True)
    ratio = float(fit_cl.bse["owned_kitchen"] / fit_plain.bse["owned_kitchen"])
    gates.append(Gate(
        5, "Are errors correlated within a dish?",
        "intra-class correlation of residuals, and the cluster to classical error ratio",
        round(icc, 3), None, "an ICC above zero makes independent errors untenable",
        f"ICC = {icc:.3f}; clustering multiplies the standard error by {ratio:.2f}",
        "cluster by dish. Several quotes per dish are one draw of a dish, not "
        "several independent draws",
    ))

    # Gate 6. Are there enough clusters for the asymptotic argument?
    g = int(d_id["matched_id"].nunique())
    enough = g >= MIN_CLUSTERS_ASYMPTOTIC
    gates.append(Gate(
        6, "Are there enough clusters for asymptotic inference?",
        "cluster count against the published rule of thumb",
        float(g), None, f"at least {MIN_CLUSTERS_ASYMPTOTIC} clusters",
        f"{g} clusters, {'above' if enough else 'below'} the threshold of "
        f"{MIN_CLUSTERS_ASYMPTOTIC}",
        "asymptotic cluster p values are reportable on their own" if enough else
        "the wild cluster bootstrap is the inference, not a robustness extra. "
        "The asymptotic p value is reported beside it and over-rejects",
    ))

    # Gate 7. Residual normality, which feeds back into gate 6.
    sw = stats.shapiro(fit_plain.resid) if len(d_id) <= 5000 else None
    jb = float(sm.stats.stattools.jarque_bera(fit_plain.resid)[1])
    normal = (sw.pvalue if sw else jb) >= ALPHA
    gates.append(Gate(
        7, "Are the residuals normal?",
        "Shapiro-Wilk and Jarque-Bera",
        float(sw.statistic) if sw else np.nan, float(sw.pvalue) if sw else jb,
        f"reject at {ALPHA} means exact small sample inference is unavailable",
        f"Shapiro-Wilk p = {_fmt_p(float(sw.pvalue)) if sw else 'n/a'}, "
        f"Jarque-Bera p = {_fmt_p(jb)}; "
        + ("normal" if normal else "not normal"),
        "reinforces gate 6. Non-normal residuals over few clusters is exactly "
        "the case the bootstrap exists for" if not normal else
        "gate 6 still governs, because normality does not fix a small cluster count",
    ))

    boot = wild_cluster_bootstrap(d_id, n_boot=n_boot)
    main = coef(fit_cl)

    # Gate 8. Influence. One dish must not be the finding.
    loo = leave_one_dish_out(d_id)
    swing = float((loo["beta"] - main["beta"]).abs().max())
    flips = bool((np.sign(loo["beta"]) != np.sign(main["beta"])).any())
    gates.append(Gate(
        8, "Does a single dish carry the estimate?",
        "leave one dish out jackknife over all dishes",
        round(swing, 3), None, "no single dish should flip the sign",
        f"largest swing {swing:.3f} log points; sign "
        + ("flips" if flips else "never flips"),
        "the estimate is not a one dish artefact; the jackknife spread is "
        "plotted" if not flips else
        "the sign is fragile and the dish responsible is named in the results",
    ))

    # Gate 9. Does the headline survive the quantity rule that produced it?
    qs = quantity_sensitivity(panel)
    unit_rows = qs[qs["assumption"] != "none"]
    free = qs[qs["assumption"] == "none"].iloc[0]
    all_sig = bool((unit_rows["p"] < ALPHA).all())
    same_sign = bool((np.sign(unit_rows["beta"]) == np.sign(main["beta"])).all())
    lo, hi = unit_rows["beta"].min(), unit_rows["beta"].max()
    gates.append(Gate(
        9, "Is the per-unit result robust to how unstated quantities are read?",
        "refit under every defensible quantity rule, from one serving to the dish median",
        round(float(hi - lo), 3), None,
        "sign and significance must hold across every rule",
        f"beta ranges {lo:+.3f} to {hi:+.3f} across the rules; sign "
        f"{'holds' if same_sign else 'flips'}, significance "
        f"{'holds' if all_sig else 'does not hold'}",
        "the per-unit specification carries the headline"
        if (all_sig and same_sign) else
        f"the per-unit estimate is reported as a range, not a point. The list "
        f"price specification leads instead, at {free['beta']:+.3f} "
        f"(p = {_fmt_p(float(free['p']))}), because it uses no quantity "
        f"assumption at all",
    ))

    # Act on gate 9 rather than merely announcing it. If the quantity rule can
    # move significance then the specification that never touches quantity is
    # the one that carries the headline, and everything downstream refits on it.
    primary = outcome
    if not (all_sig and same_sign):
        primary = "list_price"
        d_id = prepare(panel, outcome=primary, drop_unreliable=False)
        d_id, dropped = identified_dishes(d_id)
        fit_cl = fit_item_fe(d_id)
        main = coef(fit_cl)
        boot = wild_cluster_bootstrap(d_id, n_boot=n_boot)
        loo = leave_one_dish_out(d_id)

    # Gate 10. Does the model agree with the assumption free test?
    # Ranks are taken on whatever price definition gate 9 promoted, so the two
    # results are answering the same question.
    if ranks is None:
        from . import menu as _menu
        ranks = _menu.bistro_percentile_rank(panel, price_col=primary)["bistro_rank"]
    if ranks is not None:
        rt = rank_test(ranks)
        agree = (rt["mean_rank"] < 0.5) == (main["beta"] < 0)
        gates.append(Gate(
            10, "Does the parametric estimate agree with the rank test?",
            "Wilcoxon signed rank on within-dish percentile ranks",
            rt["mean_rank"], rt["wilcoxon_p"],
            "the two should point the same way",
            f"mean rank {rt['mean_rank']:.3f} against a null of 0.500, "
            f"Wilcoxon p = {_fmt_p(rt['wilcoxon_p'])}; "
            + ("agrees with the model" if agree else "contradicts the model"),
            "the rank test leads the results because it assumes least, and the "
            "coefficient supplies the magnitude" if agree else
            "the rank test leads and the model is reported as failing to "
            "reproduce it, because the rank test assumes less",
        ))

    trail = pd.DataFrame([g.as_row() for g in gates])
    chosen = {"sample": d_id, "fit": fit_cl, "coef": main, "bootstrap": boot,
              # Recomputed, not carried from gate 6: if gate 9 refit on a
              # different price definition the cluster count moved with it.
              "loo": loo, "n_clusters": int(d_id["matched_id"].nunique()),
              "dropped_dishes": dropped,
              "quantity_sensitivity": qs, "primary_outcome": primary,
              "ranks": ranks}
    return trail, chosen

