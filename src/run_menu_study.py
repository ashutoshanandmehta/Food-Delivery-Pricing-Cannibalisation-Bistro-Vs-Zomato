"""Run the whole menu price study and write every number the paper reports.

    python src/run_menu_study.py

Each output is a LaTeX fragment in ``output/tables`` that ``main.tex`` inputs,
so no result is ever typed into the paper by hand. Retyping is where a number
drifts from the code that produced it, and a drifted number in a results table
is the one mistake a reader cannot check.

Charts go to ``output/charts`` through :mod:`src.viz`, the same helpers the
ECO507 notebooks use.
"""

from __future__ import annotations

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config, menu, offers, viz
from . import estimate as E

#: Checkout wedges from data/manual/checkout_fees_delhi.csv. One capture each,
#: which is why H3 is reported as a scenario and never as an estimate.
WEDGES = {"Bistro": 0.038, "Swiggy": 0.587, "Zomato": 0.772}

TEX = config.TABLES


def _tex(name: str, body: str) -> None:
    (TEX / f"{name}.tex").write_text(body.rstrip() + "\n")


def _esc(s) -> str:
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def _num(x, dp=3):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{dp}f}"


# --- tables -----------------------------------------------------------------

def table_cascade(trail: pd.DataFrame) -> None:
    """The decision trail. This is the methodology section, not an appendix."""
    rows = []
    for _, g in trail.iterrows():
        rows.append(
            f"{g.step} & {_esc(g.question)} & {_esc(g.verdict)} & "
            f"{_esc(g.consequence)} \\\\"
        )
    _tex("cascade", "\n\\addlinespace\n".join(rows))


def table_specifications(specs: dict) -> None:
    rows = []
    for label, (desc, c, extra) in specs.items():
        stars = "***" if c["p"] < .01 else "**" if c["p"] < .05 else "*" if c["p"] < .1 else ""
        rows.append(
            f"{_esc(label)} & {_esc(desc)} & ${c['beta']:+.3f}^{{{stars}}}$ & "
            f"({c['se']:.3f}) & {c['pct']:+.1%} & {c['n']} & {extra} \\\\"
            .replace("%", r"\%")
        )
    _tex("specifications", "\n".join(rows))


def table_delta(bridge: dict, by_section: pd.DataFrame) -> None:
    body = [
        f"Coefficient on list price & ${bridge['beta_list']:+.3f}$ \\\\",
        f"Quantity gap $\\Delta$ & ${bridge['delta']:+.3f}$ "
        f"({bridge['delta_se']:.3f}) \\\\",
        f"Coefficient on unit price & ${bridge['beta_unit']:+.3f}$ \\\\",
        r"\addlinespace",
        "Identity residual & $<10^{-12}$ \\\\" if abs(bridge["identity_gap"]) < 1e-12
        else f"Identity residual & ${bridge['identity_gap']:.2e}$ \\\\",
    ]
    _tex("delta_bridge", "\n".join(body))

    rows = [f"{_esc(r.section)} & {int(r.n_dishes)} & ${r.delta_mean:+.3f}$ & "
            f"({r.delta_se:.3f}) \\\\" for _, r in by_section.iterrows()
            if not np.isnan(r.delta_se)]
    _tex("delta_by_section", "\n".join(rows))


def table_fee_wedge(scen: pd.DataFrame) -> None:
    rows = [f"{_esc(r.platform)} & {r.wedge:.1%} & ${r.log_shift:+.3f}$ & "
            f"${r.beta_delivered:+.3f}$ & {r.pct_delivered:+.1%} \\\\"
            .replace("%", r"\%") for _, r in scen.iterrows()]
    _tex("fee_wedge", "\n".join(rows))


def platform_contrast(d: pd.DataFrame) -> dict:
    """Do the two marketplaces differ, tested rather than eyeballed.

    Zomato was captured by tapping into each restaurant and Swiggy from the
    Dishes result list, which select different restaurants into the top five.
    Comparing two separately fitted coefficients is not a test of that. This
    puts both marketplaces in one regression and tests the difference directly.
    """
    import statsmodels.formula.api as smf

    x = d.assign(swiggy=(d["platform"] == "Swiggy").astype(int))
    f = smf.wls("y ~ owned_kitchen + swiggy + C(matched_id)", data=x,
                weights=x["cell_weight"]).fit(
        cov_type="cluster", cov_kwds={"groups": x["matched_id"]})
    return {"diff": float(f.params["swiggy"]), "se": float(f.bse["swiggy"]),
            "p": float(f.pvalues["swiggy"])}


def table_wedge_curve(curve) -> None:
    """The delivered gap across basket sizes, one column per platform."""
    piv = curve.pivot(index="basket", columns="platform", values="delivered_gap")
    wed = curve.pivot(index="basket", columns="platform", values="wedge")
    rows = []
    for x in piv.index:
        cells = " & ".join(f"{wed.loc[x, c]:.0%} & {piv.loc[x, c]:.0%}"
                           for c in sorted(piv.columns))
        rows.append(f"Rs {x:.0f} & {cells} \\\\".replace("%", r"\%"))
    _tex("wedge_curve", "\n".join(rows))


def chart_wedge_curve(curve) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for plat, g in curve.groupby("platform"):
        ax.plot(g.basket, g.delivered_gap, marker="o",
                color=viz.PALETTE["fd"] if plat == "Zomato" else viz.PALETTE["qc"],
                label=f"vs {plat}")
    ax.axhline(0, color=viz.PALETTE["control"], lw=1.0)
    ax.set_xlabel("basket size, rupees")
    ax.set_ylabel("what a Bistro order costs, against the marketplace")
    viz.pct_axis(ax)
    ax.legend(frameon=False)
    ax.set_title("The delivered gap shrinks with basket size but does not close")
    viz.caption(fig, "Delivery and platform fees are fixed per order, so they "
                     "spread over a larger basket. The proportional part does not.")
    viz.save(fig, "menu_wedge_curve")


def table_checkout(ch: pd.DataFrame, platform: str = "Zomato") -> None:
    """What you pay, by basket size and by which coupon you manage to use."""
    z = ch[ch.platform == platform]
    piv = z.pivot(index="basket", columns="coupon", values="gap")
    cp = z.pivot(index="basket", columns="coupon", values="coupon_pct")
    order = ["none", "typical coupon", "best coupon"]
    rows = []
    for x in piv.index:
        cells = " & ".join(
            (f"{piv.loc[x, c]:.0%}" if c == "none"
             else f"{cp.loc[x, c]:.0%} & {piv.loc[x, c]:.0%}")
            for c in order)
        rows.append(f"Rs {x:.0f} & {cells} \\\\".replace("%", r"\%"))
    _tex("checkout", "\n".join(rows))


def table_rank(rt: dict) -> None:
    _tex("rank_test", "\n".join([
        f"Dishes compared & {rt['n_dishes']} \\\\",
        f"Mean percentile rank & {rt['mean_rank']:.3f} \\\\",
        f"Median percentile rank & {rt['median_rank']:.3f} \\\\",
        f"Dishes where Bistro is below the marketplace median & "
        f"{rt['n_below_half']} of {rt['n_dishes']} \\\\",
        f"Wilcoxon signed rank, $p$ & {rt['wilcoxon_p']:.4f} \\\\",
        f"Sign test, $p$ & {rt['sign_p']:.4f} \\\\",
    ]))


def table_flow() -> None:
    f = pd.read_csv(config.PROCESSED / "menu_exclusion_flow.csv")
    prev, rows = None, []
    for _, r in f.iterrows():
        drop = "" if prev is None else f"$-{prev - r.rows_remaining}$"
        rows.append(f"{_esc(r.stage)} & {drop} & {r.rows_remaining} & "
                    f"{_esc(r.reason_dropped)} \\\\")
        prev = r.rows_remaining
    _tex("exclusion_flow", "\n".join(rows))


# --- charts ------------------------------------------------------------------

def chart_ranks(ranks: pd.DataFrame, panel: pd.DataFrame) -> None:
    names = panel[panel.platform == "Bistro"].set_index("matched_id")["dish_name_raw"]
    r = ranks.assign(name=ranks.matched_id.map(names)).sort_values("bistro_rank")
    fig, ax = plt.subplots(figsize=(9, 7.5))
    colours = [viz.PALETTE["qc"] if v < .5 else viz.PALETTE["negative"]
               for v in r.bistro_rank]
    ax.hlines(r.name, 0, r.bistro_rank, color=colours, lw=1.4, alpha=.65)
    ax.scatter(r.bistro_rank, r.name, color=colours, s=42, zorder=3)
    ax.axvline(.5, color=viz.PALETTE["control"], ls="--", lw=1.2)
    ax.text(.505, -.8, "null: 0.50", color=viz.PALETTE["control"], fontsize=9)
    ax.set_xlabel("Bistro's percentile rank in the dish's marketplace price distribution")
    ax.set_xlim(-.02, 1.02)
    ax.set_title("Where Bistro sits on price, dish by dish")
    viz.caption(fig, f"Below 0.50 means Bistro is cheaper than the median "
                     f"marketplace quote for that dish. Mean rank "
                     f"{r.bistro_rank.mean():.3f} over {len(r)} dishes.")
    viz.save(fig, "menu_bistro_ranks")


def chart_specs(specs: dict) -> None:
    labels = list(specs)[::-1]
    betas = [specs[k][1]["beta"] for k in labels]
    los = [specs[k][1]["ci_lo"] for k in labels]
    his = [specs[k][1]["ci_hi"] for k in labels]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    y = np.arange(len(labels))
    ax.hlines(y, los, his, color=viz.PALETTE["fd"], lw=2.2)
    ax.scatter(betas, y, color=viz.PALETTE["fd"], s=55, zorder=3)
    ax.axvline(0, color=viz.PALETTE["control"], lw=1.1)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Coefficient on owned kitchen, log points")
    ax.set_title("The estimate across every specification and robustness cut")
    viz.caption(fig, "Bars are 95% cluster robust intervals. A specification "
                     "whose interval crosses zero is reported as such.")
    viz.save(fig, "menu_specifications")


def chart_overlap(panel: pd.DataFrame) -> None:
    """Where the two price distributions sit, and where Bistro simply stops.

    The study samples the overlap by construction, so this chart is about the
    ceiling rather than the gap. Bistro's dearest item bounds how much of a
    marketplace it can reach at all.
    """
    b = panel[panel.platform == "Bistro"].list_price
    m = panel[panel.platform != "Bistro"].list_price
    fig, ax = plt.subplots(figsize=(9, 4.4))
    bins = np.linspace(0, 700, 36)
    ax.hist(m, bins=bins, alpha=.55, color=viz.PALETTE["fd"],
            label=f"marketplace quotes (n={len(m)})", density=True)
    ax.hist(b, bins=bins, alpha=.75, color=viz.PALETTE["qc"],
            label=f"Bistro (n={len(b)})", density=True)
    ax.axvline(b.max(), color=viz.PALETTE["negative"], ls="--", lw=1.6)
    ax.annotate(f"Bistro's dearest item, Rs {b.max():.0f}",
                xy=(b.max(), ax.get_ylim()[1] * .82),
                xytext=(b.max() + 40, ax.get_ylim()[1] * .82),
                color=viz.PALETTE["negative"], fontsize=9,
                arrowprops=dict(arrowstyle="->", color=viz.PALETTE["negative"]))
    ax.set_xlabel("list price, rupees")
    ax.set_ylabel("density")
    ax.set_yticks([])
    ax.legend(frameon=False)
    ax.set_title("The two price distributions, and the ceiling on Bistro's reach")
    viz.caption(fig, "Marketplace quotes here are only for dishes Bistro sells, "
                     "so this understates how far the marketplace extends.")
    viz.save(fig, "menu_overlap")


def chart_checkout(ch: pd.DataFrame, platform: str = "Zomato") -> None:
    """The whole checkout story in one picture: menu, then fees, then coupons."""
    z = ch[ch.platform == platform]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    styles = {"none": (viz.PALETTE["qc"], "-", "no coupon"),
              "typical coupon": (viz.PALETTE["fd"], "-", "typical coupon"),
              "best coupon": (viz.PALETTE["control"], "--", "best coupon on the platform")}
    for label, (c, ls, name) in styles.items():
        g = z[z.coupon == label].sort_values("basket")
        if len(g):
            ax.plot(g.basket, g.gap, marker="o", color=c, ls=ls, label=name)
    ax.axhline(0, color="black", lw=1.2)
    ax.text(z.basket.max(), .012, "parity", ha="right", fontsize=9)
    ax.fill_between([z.basket.min(), z.basket.max()], 0, .18, color=viz.PALETTE["negative"],
                    alpha=.07)
    ax.text(z.basket.min() + 20, .10, "Bistro dearer", fontsize=9,
            color=viz.PALETTE["negative"])
    viz.pct_axis(ax)
    ax.set_xlabel("basket size, rupees")
    ax.set_ylabel(f"Bistro against {platform}, delivered")
    ax.legend(frameon=False, loc="lower right")
    ax.set_title("What the gap survives: fees widen it, coupons close it")
    viz.caption(fig, "Same food value on both sides. The best coupon is a "
                     "maximum over restaurants, so it bounds what a determined "
                     "customer could reach rather than what a typical one gets.")
    viz.save(fig, "menu_checkout")


def chart_alpha(cm_zomato: float) -> None:
    """The switching value. Where partial cannibalisation starts to matter."""
    from . import unit_economics as U

    grid = np.linspace(0.01, 0.16, 80)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for ret, c in zip((1.00, 0.75, 0.50),
                      (viz.PALETTE["fd"], viz.PALETTE["qc"], viz.PALETTE["control"])):
        a = [min(U.switching_value(x, cm_zomato, ret), 1.05) for x in grid]
        ax.plot(grid, a, color=c, label=f"retention {ret:.2f}")
    ax.axhline(1.0, color="black", lw=1.1, ls=":")
    ax.text(0.012, 1.015, "no rate destroys value above this line", fontsize=9)
    ax.axvline(cm_zomato, color=viz.PALETTE["negative"], lw=1.4, ls="--")
    ax.annotate(f"Zomato CM, {cm_zomato:.1%}", xy=(cm_zomato, .35),
                xytext=(cm_zomato + .012, .30), fontsize=9,
                color=viz.PALETTE["negative"],
                arrowprops=dict(arrowstyle="->", color=viz.PALETTE["negative"]))
    viz.pct_axis(ax, "both")
    ax.set_xlabel("Bistro contribution margin, share of net order value")
    ax.set_ylabel(r"$\alpha^{*}$, cannibalisation the order can absorb")
    ax.set_ylim(0, 1.12)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Whether partial cannibalisation matters depends on one undisclosed number")
    viz.caption(fig, "Above Zomato's own contribution margin no cannibalisation "
                     "rate makes a Bistro order value destructive. Below it, the "
                     "share that is genuinely new demand decides the answer.")
    viz.save(fig, "menu_alpha")


def chart_quantity(qs: pd.DataFrame) -> None:
    """How far the per unit estimate moves on the quantity rule alone."""
    q = qs.iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    cols = [viz.PALETTE["control"] if a == "none" else
            (viz.PALETTE["negative"] if p >= 0.05 else viz.PALETTE["fd"])
            for a, p in zip(q.assumption, q.p)]
    ax.barh(range(len(q)), q.beta, color=cols, height=.6)
    for i, (bv, pv) in enumerate(zip(q.beta, q.p)):
        ax.text(bv - .012, i, f"{bv:+.3f}  p={pv:.3f}", va="center", ha="right",
                fontsize=9, color="white", fontweight="bold")
    ax.set_yticks(range(len(q)), q.treatment)
    ax.axvline(0, color="black", lw=1.1)
    ax.set_xlabel("coefficient on owned kitchen, log points")
    ax.set_title("The per unit estimate moves on the quantity rule alone")
    viz.caption(fig, "Red bars fail significance at 5%. The sign never changes "
                     "and the significance does, which is why list price leads.")
    viz.save(fig, "menu_quantity")


def chart_jackknife(loo: pd.DataFrame, beta: float) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.scatter(loo.dropped_dish.astype(str), loo.beta, s=40,
               color=viz.PALETTE["fd"], zorder=3)
    ax.axhline(beta, color=viz.PALETTE["qc"], lw=1.4, label="full sample")
    ax.axhline(0, color=viz.PALETTE["control"], lw=1.0)
    ax.set_xlabel("dish dropped")
    ax.set_ylabel("coefficient")
    ax.tick_params(axis="x", labelrotation=90, labelsize=7)
    ax.legend(frameon=False)
    ax.set_title("Leave one dish out. No single dish is the finding")
    viz.save(fig, "menu_jackknife")


def chart_wedge(scen: pd.DataFrame, beta: float) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.4))
    labels = ["menu price"] + [f"delivered,\n{r.platform}" for _, r in scen.iterrows()]
    vals = [beta] + list(scen.beta_delivered)
    cols = [viz.PALETTE["fd"]] + [viz.PALETTE["qc"]] * len(scen)
    ax.bar(labels, vals, color=cols, width=.55)
    for i, v in enumerate(vals):
        ax.text(i, v - .03, f"{np.exp(v) - 1:+.0%}", ha="center", va="top",
                fontsize=10, fontweight="bold", color="white")
    ax.axhline(0, color=viz.PALETTE["control"], lw=1.0)
    ax.set_ylabel("coefficient on owned kitchen, log points")
    ax.set_title("Adding the checkout wedge to the menu price gap")
    viz.caption(fig, "One checkout capture per platform. A deterministic shift, "
                     "so the standard error is unchanged and none is shown.")
    viz.save(fig, "menu_fee_wedge")


# --- the run -----------------------------------------------------------------

def main(n_boot: int = E.N_BOOT, verbose: bool = True):
    warnings.filterwarnings("ignore")
    viz.apply_style()
    config.ensure_dirs()

    panel = menu.load_menu_prices(config.MENU_PRICES_LONG)
    # No ranks passed. The cascade decides which price definition is primary at
    # gate 9 and takes its own ranks on that definition.
    trail, chosen = E.run_cascade(panel, n_boot=n_boot)
    d = chosen["sample"]
    main_c, boot = chosen["coef"], chosen["bootstrap"]
    ranks = menu.bistro_percentile_rank(panel, price_col=chosen["primary_outcome"])

    # Every specification the paper reports, in one place.
    unit = E.prepare(panel, outcome="unit_price")
    unit, _ = E.identified_dishes(unit)
    eff = E.prepare(panel, outcome="effective_price", drop_unreliable=False)
    eff, _ = E.identified_dishes(eff)
    stated = d[d.qty_source.isin(("name", "description"))]
    stated, _ = E.identified_dishes(stated)

    specs = {
        "M1":  ("pooled OLS, section dummies", E.coef(E.fit_pooled(d)), "no"),
        "M2":  ("item fixed effects, list price", main_c, "yes"),
        "M2n": ("item fixed effects, unit price", E.coef(E.fit_item_fe(unit)), "yes"),
        "M2e": ("after item discounts", E.coef(E.fit_item_fe(eff)), "yes"),
        "R1":  ("unweighted", E.coef(E.fit_item_fe(d, weighted=False)), "yes"),
        "R2":  ("sponsored rows dropped",
                E.coef(E.fit_item_fe(E.identified_dishes(d[~d.is_sponsored.fillna(False)])[0])), "yes"),
        "R3":  ("grade A matches only",
                E.coef(E.fit_item_fe(E.identified_dishes(d[d.match_grade == "A_exact"])[0])), "yes"),
        "R4":  ("quantity stated, not assumed", E.coef(E.fit_item_fe(stated)), "yes"),
    }
    for plat in ("Zomato", "Swiggy"):
        sub, _ = E.identified_dishes(d[d.platform.isin(["Bistro", plat])])
        specs[f"P:{plat}"] = (f"Bistro against {plat} only",
                              E.coef(E.fit_item_fe(sub)), "yes")

    inter = E.fit_interaction(d)
    bridge = E.delta_bridge(unit)
    by_section = menu.delta_by_section(unit)
    scen = E.fee_wedge_scenario(main_c["beta"], WEDGES)
    fees = pd.read_csv(config.CHECKOUT_FEES).drop_duplicates(
        "platform", keep="first").set_index("platform")
    curve = E.fee_wedge_curve(main_c["beta"], fees)
    off = offers.parse_all(pd.read_csv(config.MARKETPLACE_RAW))
    dcurve = offers.discount_curve(off, E.BASKET_GRID)
    checkout = E.checkout_comparison(main_c["beta"], fees, dcurve)
    # The one basket promotion Bistro was observed running, 439 struck to 239.
    checkout_promo = E.checkout_comparison(main_c["beta"], fees, dcurve,
                                           owned_discount=1 - 239 / 439)
    rt = E.rank_test(ranks["bistro_rank"])
    pc = platform_contrast(d)

    # Zomato food delivery contribution, read straight off the filings. This is
    # the number the whole cannibalisation question turns on, so it is pulled in
    # rather than assumed.
    from . import unit_economics as U
    cmz = U.cm_zomato_from_contribution(pd.read_csv(config.PANEL), basis=1.0)
    cm_zomato = float(cmz.dropna(subset=["cm_zomato"]).cm_zomato.iloc[-1])

    # How lopsided is the result? Where Bistro undercuts it undercuts by a lot,
    # and where it is dearer it is barely dearer. That asymmetry is why the
    # Wilcoxon test rejects while the sign test, which ignores magnitude, does not.
    cheap = ranks[ranks.bistro_rank < 0.5]
    dear = ranks[ranks.bistro_rank >= 0.5]
    gap_cheap = float(np.exp(np.log(cheap.bistro_price / cheap.mkt_median).median()) - 1)
    gap_dear = float(np.exp(np.log(dear.bistro_price / dear.mkt_median).median()) - 1)
    disp = float((ranks.mkt_max / ranks.mkt_min).median())
    _qb = by_section[by_section.section == "Quick Bites"]
    qb = float(_qb.delta_mean.iloc[0]) if len(_qb) else None

    table_cascade(trail)
    table_specifications(specs)
    table_delta(bridge, by_section)
    table_fee_wedge(scen)
    table_wedge_curve(curve)
    table_checkout(checkout)
    table_rank(rt)
    table_flow()

    qs = chosen["quantity_sensitivity"]
    _tex("quantity_sensitivity", "\n".join(
        f"{_esc(r.treatment)} & {_esc(r.assumption)} & ${r.beta:+.3f}$ & "
        f"({r.se:.3f}) & {r.p:.3f} \\\\" for _, r in qs.iterrows()))

    _tex("headline", "\n".join([
        rf"\newcommand{{\betaMain}}{{{main_c['beta']:+.3f}}}",
        rf"\newcommand{{\betaPct}}{{{abs(main_c['pct']):.1%}}}".replace("%", r"\%"),
        rf"\newcommand{{\betaSE}}{{{main_c['se']:.3f}}}",
        rf"\newcommand{{\betaP}}{{{main_c['p']:.3f}}}",
        rf"\newcommand{{\betaPboot}}{{{boot['p_boot']:.3f}}}",
        rf"\newcommand{{\nRows}}{{{main_c['n']}}}",
        rf"\newcommand{{\nDishes}}{{{chosen['n_clusters']}}}",
        rf"\newcommand{{\meanRank}}{{{rt['mean_rank']:.3f}}}",
        rf"\newcommand{{\rankP}}{{{rt['wilcoxon_p']:.4f}}}",
        rf"\newcommand{{\nBelowHalf}}{{{rt['n_below_half']}}}",
        rf"\newcommand{{\deltaMain}}{{{bridge['delta']:+.3f}}}",
        rf"\newcommand{{\betaUnitLo}}{{{qs.beta.min():+.3f}}}",
        rf"\newcommand{{\betaUnitHi}}{{{qs[qs.assumption!='none'].beta.max():+.3f}}}",
        rf"\newcommand{{\primaryOutcome}}{{{chosen['primary_outcome'].replace('_',' ')}}}",
        rf"\newcommand{{\interBeta}}{{{inter.params['owned_kitchen:snacky']:+.3f}}}",
        rf"\newcommand{{\interP}}{{{inter.pvalues['owned_kitchen:snacky']:.3f}}}",
        rf"\newcommand{{\betaCIlo}}{{{main_c['ci_lo']:+.3f}}}",
        rf"\newcommand{{\betaCIhi}}{{{main_c['ci_hi']:+.3f}}}",
        rf"\newcommand{{\signP}}{{{rt['sign_p']:.3f}}}",
        rf"\newcommand{{\mktDiff}}{{{pc['diff']:+.3f}}}",
        rf"\newcommand{{\mktDiffSE}}{{{pc['se']:.3f}}}",
        rf"\newcommand{{\mktDiffP}}{{{pc['p']:.3f}}}",
        rf"\newcommand{{\nDearer}}{{{(ranks.bistro_rank >= 0.5).sum()}}}",
        rf"\newcommand{{\gapCheaper}}{{{abs(gap_cheap):.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\gapDearer}}{{{gap_dear:.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\dispRatio}}{{{disp:.1f}}}",
        rf"\newcommand{{\deltaQuick}}{{{qb:+.3f}}}" if qb is not None else "",
        rf"\newcommand{{\nBoot}}{{{boot['n_boot']}}}",
        rf"\newcommand{{\wedgeBistro}}{{{WEDGES['Bistro']:.1%}}}".replace("%", r"\%"),
        rf"\newcommand{{\wedgeSwiggy}}{{{WEDGES['Swiggy']:.1%}}}".replace("%", r"\%"),
        rf"\newcommand{{\wedgeZomato}}{{{WEDGES['Zomato']:.1%}}}".replace("%", r"\%"),
        rf"\newcommand{{\gapSmallBasket}}{{{abs(curve[(curve.platform=='Zomato')&(curve.basket==149)].delivered_gap.iloc[0]):.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\gapBigBasket}}{{{abs(curve[(curve.platform=='Zomato')&(curve.basket==700)].delivered_gap.iloc[0]):.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\qcNaov}}{{518}}",
        rf"\newcommand{{\cmZomato}}{{{cm_zomato:.2%}}}".replace("%", r"\%"),
        rf"\newcommand{{\bistroCeiling}}{{{panel[panel.platform=='Bistro'].list_price.max():.0f}}}",
        rf"\newcommand{{\mktCeiling}}{{{panel[panel.platform!='Bistro'].list_price.max():.0f}}}",
        rf"\newcommand{{\nRestaurants}}{{{panel[panel.platform!='Bistro'].restaurant_name.nunique()}}}",
        rf"\newcommand{{\nBistroMenu}}{{{len(pd.read_csv(config.BISTRO_MENU))}}}",
        rf"\newcommand{{\shareCheaperThanBistro}}{{{ranks.bistro_rank.mean():.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\nUndercut}}{{{(ranks.bistro_price>ranks.mkt_min).sum()}}}",
        rf"\newcommand{{\gapTypicalCoupon}}{{{abs(checkout.query('platform==\"Zomato\" and basket==400 and coupon==\"typical coupon\"').gap.iloc[0]):.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\gapBestCoupon}}{{{checkout.query('platform==\"Zomato\" and basket==200 and coupon==\"best coupon\"').gap.iloc[0]:+.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\couponTypical}}{{{checkout.query('platform==\"Zomato\" and basket==400 and coupon==\"typical coupon\"').coupon_pct.iloc[0]:.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\bistroPromo}}{{{1-239/439:.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\shareFiring}}{{{dcurve.query('platform==\"Zomato\" and basket==400').share_firing.iloc[0]:.0%}}}".replace("%", r"\%"),
        rf"\newcommand{{\gapWithBistroPromo}}{{{abs(checkout_promo.query('platform==\"Zomato\" and basket==400 and coupon==\"typical coupon\"').gap.iloc[0]):.0%}}}".replace("%", r"\%"),
    ]))

    chart_ranks(ranks, panel)
    chart_specs(specs)
    chart_jackknife(chosen["loo"], main_c["beta"])
    chart_wedge(scen, main_c["beta"])
    chart_wedge_curve(curve)
    chart_overlap(panel)
    chart_checkout(checkout)
    chart_quantity(chosen["quantity_sensitivity"])
    chart_alpha(cm_zomato)

    if verbose:
        print(f"panel {len(panel)} rows -> estimation sample {main_c['n']} rows, "
              f"{chosen['n_clusters']} dishes\n")
        print(f"beta = {main_c['beta']:+.4f} ({main_c['pct']:+.1%}), "
              f"SE {main_c['se']:.4f}")
        print(f"  cluster p {main_c['p']:.4f}   bootstrap p {boot['p_boot']:.4f} "
              f"({boot['n_boot']} reps)")
        print(f"  rank test: mean {rt['mean_rank']:.3f}, "
              f"{rt['n_below_half']}/{rt['n_dishes']} cheaper, p {rt['wilcoxon_p']:.4f}")
        print(f"  H2 interaction {inter.params['owned_kitchen:snacky']:+.3f} "
              f"(p {inter.pvalues['owned_kitchen:snacky']:.3f})\n")
        print("specifications")
        for k, (desc, c, _) in specs.items():
            print(f"  {k:<9} {desc:<38} {c['beta']:+.3f} ({c['se']:.3f})  "
                  f"p {c['p']:.3f}  n {c['n']}")
        print(f"\nwrote {len(list(TEX.glob('*.tex')))} tex fragments to {TEX}")
        print(f"wrote 4 charts to {config.CHARTS}")
    return {"trail": trail, "specs": specs, "bridge": bridge, "rank": rt,
            "scenario": scen, "bootstrap": boot}


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
