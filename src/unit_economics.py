"""The switching value model.

The number the whole recommendation turns on is a single division, so it lives
here rather than in a notebook cell where a re-run could quietly change it.

The model
=========

    CM_net = CM_bistro - (alpha * retention * CM_zomato)

An incremental Bistro order, probability ``1 - alpha``, contributes CM_bistro in
full. A cannibalised order, probability ``alpha``, still contributes CM_bistro
but forfeits the marketplace contribution Eternal would have earned. It only
forfeits that contribution in the ``retention`` share of cases where Eternal
would have kept the order at all. Swiggy Bolt, Snacc and Zepto Cafe are the
reason that share is below one.

Setting ``CM_net`` to zero gives the switching value:

    alpha* = CM_bistro / (retention * CM_zomato)

Above 1, no cannibalisation rate makes Bistro value destructive on a per order
basis. Below 1, alpha* is the rate at which the recommendation flips.

``retention = 1`` is the conservative case where every cannibalised order would
have stayed on Zomato. It gives the lowest threshold the evidence supports, so
report it alongside the plausible range rather than instead of it.

Conventions
===========

* Contribution margins are rupees per order and positive.
* ``alpha`` and ``retention`` are fractions in [0, 1]. alpha* is a threshold and
  may exceed 1.
* Components of the CM_bistro stack carry their own sign. Order value is
  positive and every cost is negative, so the stack sums to the margin.

Everything above the IO section at the bottom is pure. It takes numbers and
returns numbers or frames. No file reads, no plotting, so every figure that
reaches the deck is unit testable.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DECK_COLUMNS = [
    "alpha",
    "cannibalised_orders",
    "retained_orders",
    "incremental_orders",
    "foregone_zomato_cm",
    "bistro_cm",
    "net_cm_total",
    "net_cm_per_order",
]


def _check_rate(name: str, value: float) -> float:
    v = float(value)
    if not np.isfinite(v) or not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be a fraction in [0, 1], got {value!r}.")
    return v


def switching_value(
    cm_bistro: float, cm_zomato: float, retention: float = 1.0
) -> float:
    """alpha* = CM_bistro / (retention * CM_zomato).

    The cannibalisation rate at which a Bistro order stops adding group
    contribution. A result above 1 means no rate makes Bistro value destructive
    per order, because every migrated order is a margin upgrade.

    ``retention`` below 1 raises the threshold, because part of the cannibalised
    volume was leaving Eternal anyway.

    Raises if ``cm_zomato`` is not positive. A zero or negative marketplace
    contribution makes the ratio meaningless rather than infinite, and silently
    returning inf would put a wrong number in the deck.
    """
    retention = _check_rate("retention", retention)
    if retention == 0.0:
        raise ValueError(
            "retention of zero means no cannibalised order was ever Eternal's, "
            "so there is no threshold. Report that finding instead."
        )
    if not np.isfinite(cm_zomato) or cm_zomato <= 0:
        raise ValueError(
            f"cm_zomato must be positive to form a threshold, got {cm_zomato!r}. "
            "If food delivery contribution is negative, the framing changes and "
            "the deck needs to say so."
        )
    return float(cm_bistro) / (retention * float(cm_zomato))


def net_contribution(
    cm_bistro: float, cm_zomato: float, alpha: float, retention: float = 1.0
) -> float:
    """Net group contribution per Bistro order at cannibalisation rate alpha.

    Zero exactly at ``alpha = switching_value(...)`` for the same inputs.
    """
    alpha = _check_rate("alpha", alpha)
    retention = _check_rate("retention", retention)
    return float(cm_bistro) - alpha * retention * float(cm_zomato)


def sensitivity_table(
    cm_bistro: float,
    cm_zomato: float,
    alphas: list[float],
    retention: float = 1.0,
    basis: int = 100,
) -> pd.DataFrame:
    """One row per alpha, in the column order the deck table uses.

    Counts and rupee totals are stated per ``basis`` Bistro orders so the
    columns read as whole quantities. ``net_cm_per_order`` is the number the
    recommendation rests on and it does not depend on the basis.

    ``retained_orders`` is the share of cannibalised orders Eternal would
    actually have kept. At ``retention = 1`` it equals ``cannibalised_orders``
    and the table collapses to the plain version.
    """
    if basis <= 0:
        raise ValueError(f"basis must be positive, got {basis!r}.")
    retention = _check_rate("retention", retention)

    rows = []
    for a in alphas:
        a = _check_rate("alpha", a)
        cannibalised = a * basis
        retained = cannibalised * retention
        rows.append(
            {
                "alpha": a,
                "cannibalised_orders": cannibalised,
                "retained_orders": retained,
                "incremental_orders": (1 - a) * basis,
                "foregone_zomato_cm": retained * cm_zomato,
                "bistro_cm": basis * cm_bistro,
                "net_cm_total": basis * cm_bistro - retained * cm_zomato,
                "net_cm_per_order": net_contribution(
                    cm_bistro, cm_zomato, a, retention
                ),
            }
        )
    return pd.DataFrame(rows, columns=DECK_COLUMNS)


def sensitivity_grid(
    cm_bistro_cases: dict[str, float],
    cm_zomato: float,
    alphas: list[float],
    retention: float = 1.0,
) -> pd.DataFrame:
    """The central exhibit. CM_bistro cases down, alpha across, net CM in cells.

    Alpha is not the only uncertain input. CM_bistro is the weakest number in
    the project and it sits in the numerator of alpha*, so holding it fixed
    while varying alpha tests one parameter and calls it a range.

    Cells are net contribution per Bistro order, in rupees. The sign change
    across the grid is the finding.
    """
    if not cm_bistro_cases:
        raise ValueError("Pass at least one CM_bistro case.")
    data = {
        f"alpha={a:.0%}": [
            net_contribution(cm, cm_zomato, a, retention)
            for cm in cm_bistro_cases.values()
        ]
        for a in alphas
    }
    return pd.DataFrame(data, index=list(cm_bistro_cases.keys()))


def switching_value_grid(
    cm_bistro_cases: dict[str, float],
    cm_zomato: float,
    retentions: list[float],
) -> pd.DataFrame:
    """alpha* for each CM_bistro case across a range of retention assumptions.

    Read the ``retention=100%`` column as the conservative floor. Cells at or
    above 1 mean no cannibalisation rate makes that case value destructive.
    """
    data = {
        f"retention={r:.0%}": [
            switching_value(cm, cm_zomato, r) for cm in cm_bistro_cases.values()
        ]
        for r in retentions
    }
    return pd.DataFrame(data, index=list(cm_bistro_cases.keys()))


def required_cm_bistro(
    cm_zomato: float, alphas: list[float], retention: float = 1.0
) -> pd.DataFrame:
    """The minimum CM_bistro that keeps net contribution non negative, by alpha.

    This is the switching value inverted, and it is the right exhibit when
    CM_bistro is too weakly evidenced to estimate honestly. Rather than guess
    the number and dress the guess in a sensitivity range, state the bar it has
    to clear and let the reader judge whether a 10 minute owned kitchen clears
    it.

        required CM_bistro = alpha * retention * CM_zomato

    Note what happens at ``alpha = 1`` and ``retention = 1``: the requirement
    collapses to CM_bistro > CM_zomato. Under total cannibalisation the whole
    question is simply whether the owned kitchen earns more per unit of order
    value than the marketplace does.
    """
    rows = []
    for a in alphas:
        a = _check_rate("alpha", a)
        rows.append(
            {
                "alpha": a,
                "required_cm_bistro": a * _check_rate("retention", retention) * cm_zomato,
                "as_multiple_of_cm_zomato": a * retention,
            }
        )
    return pd.DataFrame(rows)


def cm_zomato_from_contribution(
    panel: pd.DataFrame, basis: float = 100.0
) -> pd.DataFrame:
    """Zomato food delivery contribution per ``basis`` rupees of NOV, by quarter.

    **This is the primary path and it involves no assumption.** Eternal
    discloses food delivery Contribution directly, and publishes the
    definition:

        Contribution = Adjusted Revenue
                       (-) last mile delivery cost
                       (-) platform funded discounts
                       (-) payment gateway and COD handling charges
                       (-) customer support and appeasement cost
                       (-) customer and restaurant partner refunds
                       (-) delivery partner recruitment and onboarding cost
                       (-) other miscellaneous costs

    Every line in that subtraction moves with order volume. None of it is
    fixed cost, overhead, brand marketing or technology. That is exactly the
    marginal cost base a switching value needs, so CM_zomato is read off a
    filing rather than built from an add back assumption.

    Because food delivery Orders and AOV are not disclosed, the natural unit
    here is order value rather than orders. Alpha is then the share of Bistro
    **NOV** that would otherwise have been Zomato food delivery NOV. State that
    definition on the slide, because it differs from the order based alpha in
    the lecture and it is the one the disclosure supports.

    Units. ``fd_contribution`` and ``fd_nov`` are both in crore, so the ratio
    is unitless and ``basis`` sets the scale.
    """
    required = {"quarter", "fd_nov", "fd_contribution"}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise KeyError(f"Panel missing columns needed for CM_zomato: {missing}")
    if basis <= 0:
        raise ValueError(f"basis must be positive, got {basis!r}.")

    out = pd.DataFrame({"quarter": panel["quarter"]})
    out["cm_pct_nov"] = panel["fd_contribution"] / panel["fd_nov"]
    out["cm_zomato"] = out["cm_pct_nov"] * basis
    return out


def cm_zomato_from_filings(
    panel: pd.DataFrame, fixed_cost_addback: float
) -> pd.DataFrame:
    """Fallback path. Only use this where Contribution is not disclosed.

    Adjusted EBITDA per unit of NOV is a floor, not a contribution margin,
    because fixed cost sits inside that line. ``fixed_cost_addback`` is the
    share of food delivery Adjusted Revenue treated as fixed and added back.
    It is an assumption and it must be recorded in ASSUMPTIONS.md.

    Direction of the error: a generous add back raises CM_zomato, lowers
    alpha*, and weakens the case for Bistro. So erring high is conservative.

    Eternal discloses Contribution for every quarter in the panel, so in this
    project this function exists as a cross check on
    ``cm_zomato_from_contribution``, not as the source of the headline.
    """
    required = {"quarter", "fd_nov", "fd_adj_revenue", "fd_adj_ebitda"}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise KeyError(f"Panel missing columns needed for CM_zomato: {missing}")
    fixed_cost_addback = _check_rate("fixed_cost_addback", fixed_cost_addback)

    out = pd.DataFrame({"quarter": panel["quarter"]})
    out["ebitda_pct_nov"] = panel["fd_adj_ebitda"] / panel["fd_nov"]
    out["addback_pct_nov"] = (
        fixed_cost_addback * panel["fd_adj_revenue"]
    ) / panel["fd_nov"]
    out["cm_pct_nov"] = out["ebitda_pct_nov"] + out["addback_pct_nov"]
    out["cm_zomato"] = out["cm_pct_nov"] * 100.0
    return out


def cm_bistro_stack(components: dict[str, dict]) -> tuple[float, pd.DataFrame]:
    """Sum the bottom up CM_bistro stack and return the working alongside it.

    Each component is a dict with ``value``, ``source``, ``method`` and
    ``confidence``. Values carry their own sign, so order value is positive and
    every cost is negative.

    A component with a value of None raises rather than being dropped. A
    silently missing cost line inflates CM_bistro, inflates alpha*, and makes
    the recommendation look stronger than the evidence supports. That is the
    exact failure this project is meant to avoid.
    """
    if not components:
        raise ValueError("The CM_bistro stack is empty.")

    blank = [k for k, v in components.items() if v.get("value") is None]
    if blank:
        raise ValueError(
            f"{len(blank)} component(s) have no value yet: {sorted(blank)}. "
            "Fill them from a source, or drop the row and say why in "
            "ASSUMPTIONS.md. Do not run the model on a partial stack."
        )

    rows = [
        {
            "component": name,
            "value": float(spec["value"]),
            "source": spec.get("source", ""),
            "method": spec.get("method", ""),
            "confidence": spec.get("confidence", "unstated"),
        }
        for name, spec in components.items()
    ]
    stack = pd.DataFrame(rows)

    positives = stack.loc[stack["value"] > 0, "value"].sum()
    if positives <= 0:
        raise ValueError(
            "The stack has no positive component. Bistro order value should be "
            "positive and every cost negative."
        )
    stack["share_of_order_value"] = stack["value"] / positives

    total = float(stack["value"].sum())
    return total, stack


# ---------------------------------------------------------------------------
# IO. The only part of this module that touches disk.
# ---------------------------------------------------------------------------

COMPONENT_COLUMNS = ["component", "value", "source", "method", "confidence"]


def load_cm_bistro_components(path: Path) -> dict[str, dict]:
    """Read the hand filled component stack into the shape ``cm_bistro_stack``
    expects. A blank value stays None so the caller raises rather than guesses.
    """
    df = pd.read_csv(path)
    missing = [c for c in COMPONENT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")

    out: dict[str, dict] = {}
    for _, row in df.iterrows():
        name = str(row["component"]).strip()
        if not name or name.lower() == "nan":
            continue
        value = row["value"]
        out[name] = {
            "value": None if pd.isna(value) else float(value),
            "source": "" if pd.isna(row["source"]) else str(row["source"]),
            "method": "" if pd.isna(row["method"]) else str(row["method"]),
            "confidence": (
                "unstated" if pd.isna(row["confidence"]) else str(row["confidence"])
            ),
        }
    if not out:
        raise ValueError(f"{path.name} has no component rows.")
    return out
