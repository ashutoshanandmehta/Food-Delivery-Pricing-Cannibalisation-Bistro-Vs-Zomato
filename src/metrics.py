"""Derived metrics and growth calculations.

This module is pure: it takes a DataFrame and returns a DataFrame. No IO,
no plotting. That makes every number in the notebooks testable.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

QUARTER_RE = re.compile(r"^Q([1-4])FY(\d{2})$")


def quarter_to_ordinal(q: str) -> int:
    """Map 'Q1FY26' to a sortable integer. Enables lag arithmetic."""
    m = QUARTER_RE.match(q.strip().upper())
    if not m:
        raise ValueError(f"Unrecognised quarter label: {q!r}. Expected e.g. 'Q1FY26'.")
    qtr, fy = int(m.group(1)), int(m.group(2))
    return fy * 4 + (qtr - 1)


def sort_by_quarter(df: pd.DataFrame, col: str = "quarter") -> pd.DataFrame:
    out = df.copy()
    out["_ord"] = out[col].map(quarter_to_ordinal)
    out = out.sort_values("_ord").reset_index(drop=True)
    return out


def add_growth(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Append QoQ and YoY growth for each column.

    YoY uses a 4-quarter lag and asserts the lag is actually 4 quarters
    apart, so a gap in the panel produces NaN rather than a wrong number.
    """
    out = sort_by_quarter(df)
    gap_ok_qoq = out["_ord"].diff() == 1
    gap_ok_yoy = out["_ord"].diff(4) == 4

    for c in cols:
        if c not in out.columns:
            continue
        out[f"{c}_qoq"] = np.where(gap_ok_qoq, out[c].pct_change(1), np.nan)
        out[f"{c}_yoy"] = np.where(gap_ok_yoy, out[c].pct_change(4), np.nan)
    return out


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the metrics Eternal does not disclose directly.

    What is available differs by segment, and the difference matters.

    Quick commerce discloses Orders and net average order value, so orders per
    customer per month is computable and NOV splits three ways into customers,
    frequency and ticket size.

    Food delivery has never disclosed Orders or AOV in the shareholders'
    letters. Only NOV, GOV and monthly transacting customers. So frequency
    cannot be separated from ticket size and the honest substitute is NOV per
    transacting customer, which carries both. Say this on the slide rather than
    inventing an AOV.

    Units. NOV and GOV are in crore, MTU is in millions, orders are in
    millions, AOV is in rupees. MTU is a monthly average and NOV is a quarterly
    total, hence the 3 in the frequency term.
    """
    out = df.copy()

    # Quick commerce: the full three way split.
    if {"qc_orders_mn", "qc_mtu"}.issubset(out.columns):
        out["qc_frequency"] = out["qc_orders_mn"] / (out["qc_mtu"] * 3)
    if {"qc_nov", "qc_orders_mn"}.issubset(out.columns):
        # Cross check against the disclosed NAOV. A gap means a units error.
        out["qc_naov_derived"] = (out["qc_nov"] * 1e7) / (out["qc_orders_mn"] * 1e6)

    # Food delivery: the two way split.
    for value_col in ("fd_nov", "fd_gov"):
        if {value_col, "fd_mtu"}.issubset(out.columns):
            out[f"{value_col}_per_mtu"] = (out[value_col] * 1e7) / (out["fd_mtu"] * 1e6)

    # Contribution margin as a share of order value. Disclosed by Eternal, not
    # derived here, so this carries the confidence of a filing.
    if {"fd_contribution", "fd_nov"}.issubset(out.columns):
        out["fd_cm_pct_nov"] = out["fd_contribution"] / out["fd_nov"]
    if {"fd_contribution", "fd_gov"}.issubset(out.columns):
        out["fd_cm_pct_gov"] = out["fd_contribution"] / out["fd_gov"]
    if {"qc_contribution", "qc_nov"}.issubset(out.columns):
        out["qc_cm_pct_nov"] = out["qc_contribution"] / out["qc_nov"]

    if {"fd_adj_revenue", "fd_nov"}.issubset(out.columns):
        out["fd_take_rate"] = out["fd_adj_revenue"] / out["fd_nov"]
    if {"qc_revenue", "qc_nov"}.issubset(out.columns):
        # Breaks at the inventory led transition. Read qc_cm_pct_nov instead.
        out["qc_take_rate"] = out["qc_revenue"] / out["qc_nov"]

    # Segment share on NOV, never on revenue. Revenue share is inflated by
    # Blinkit's inventory led accounting, which books full order value.
    nov_cols = [c for c in ("fd_nov", "qc_nov", "go_nov") if c in out.columns]
    if len(nov_cols) == 3:
        out["b2c_nov"] = out[nov_cols].sum(axis=1, min_count=3)
        out["qc_nov_share"] = out["qc_nov"] / out["b2c_nov"]
        out["fd_nov_share"] = out["fd_nov"] / out["b2c_nov"]

    if {"bistro_kitchens", "qc_stores"}.issubset(out.columns):
        out["bistro_penetration"] = out["bistro_kitchens"] / out["qc_stores"]

    return out


def decompose_growth(
    df: pd.DataFrame,
    value_col: str,
    driver_cols: list[str],
    periods: int = 4,
) -> pd.DataFrame:
    """Multiplicative decomposition of a value series into its drivers.

    The drivers must multiply to the value up to a constant factor, for example

        NOV = MTU x (NOV per MTU)                       food delivery
        NOV = MTU x frequency x net AOV                 quick commerce

    In log space the product becomes a sum, so each driver's log change is its
    additive contribution to total log growth. Contributions sum exactly, which
    an arithmetic decomposition does not guarantee. A constant scale factor
    between the product and the value cancels in the difference, so unit
    conventions do not matter here.

    Returns one row per quarter with each driver's contribution and share.
    """
    missing = [c for c in [value_col, *driver_cols] if c not in df.columns]
    if missing:
        raise KeyError(f"Run add_derived() first. Missing: {missing}")
    if len(driver_cols) < 2:
        raise ValueError("A decomposition needs at least two drivers.")

    out = sort_by_quarter(df)
    valid = out["_ord"].diff(periods) == periods

    res = pd.DataFrame({"quarter": out["quarter"]})
    total = np.log(out[value_col]).diff(periods)

    contrib_cols = []
    for driver in driver_cols:
        short = driver.split("_", 1)[1] if "_" in driver else driver
        contrib = np.log(out[driver]).diff(periods)
        res[f"{short}_log_contrib"] = np.where(valid, contrib, np.nan)
        res[f"{short}_share"] = np.where(valid, contrib / total, np.nan)
        contrib_cols.append(f"{short}_log_contrib")

    res["total_log_growth"] = np.where(valid, total, np.nan)
    res["value_yoy"] = np.where(valid, out[value_col].pct_change(periods), np.nan)

    # Residual should be ~0. Anything larger means a units or data problem.
    res["residual"] = res["total_log_growth"] - res[contrib_cols].sum(axis=1)
    return res


def growth_spread(
    treated: pd.DataFrame,
    control: pd.DataFrame,
    treated_col: str,
    control_col: str,
) -> pd.DataFrame:
    """H4 test statistic: treated growth minus control growth, by quarter.

    This is the approximate difference-in-differences. It is NOT a true DiD:
    there is no city-level randomisation and the two firms differ in scale and
    product mix. Report it as a descriptive spread, not a causal estimate.
    """
    t = sort_by_quarter(treated)[["quarter", "_ord", treated_col]]
    c = sort_by_quarter(control)[["quarter", "_ord", control_col]]
    m = t.merge(c, on=["quarter", "_ord"], how="inner", suffixes=("_t", "_c"))
    m = m.sort_values("_ord")

    valid = m["_ord"].diff(4) == 4
    m["treated_yoy"] = np.where(valid, m[treated_col].pct_change(4), np.nan)
    m["control_yoy"] = np.where(valid, m[control_col].pct_change(4), np.nan)
    m["spread"] = m["treated_yoy"] - m["control_yoy"]
    return m[["quarter", "treated_yoy", "control_yoy", "spread"]]


def pre_post_summary(
    df: pd.DataFrame, col: str, split_quarter: str
) -> pd.DataFrame:
    """Mean growth before vs after a cutoff quarter.

    Crude by design. With ~10 quarters there is no statistical power, so this
    is descriptive framing for a chart, not a hypothesis test. Do not attach
    a p-value to it.
    """
    out = sort_by_quarter(df)
    cut = quarter_to_ordinal(split_quarter)
    out["period"] = np.where(out["_ord"] < cut, "pre", "post")
    return (
        out.groupby("period")[col]
        .agg(["count", "mean", "std", "min", "max"])
        .reindex(["pre", "post"])
    )
