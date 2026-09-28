"""Marketplace coupons, parsed into a discount that depends on basket size.

A menu price comparison ignores coupons, and for the coefficient that is the
only defensible choice: an offer of the form ``Flat Rs 150 OFF above Rs 599``
cannot be attached to one dish without first assuming the rest of the basket.
Any allocation rule would be an invented number carrying the result.

At checkout the assumption stops being defensible, because the customer really
does see the offer. This module parses the offer text captured with every
restaurant into a rule, so the discount can be evaluated at a stated basket size
and the delivered comparison reported as a function of it rather than assumed
away.

Two findings shape how the output should be read.

**Coupons shrink as a share of a growing basket.** Most are capped, of the form
``70% off upto Rs 140``, so the headline rate applies only below the basket at
which the cap binds. The median Zomato coupon is worth 25% of a Rs 200 basket
and 11% of a Rs 700 one.

**The best coupon is not freely available.** It is a maximum over restaurants,
and taking it means ordering from the restaurant that offers it rather than the
one selling the dish you wanted. It is reported as a bound on what a determined
customer could achieve, never as the typical case.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

#: Offer shapes seen in the captured text, most specific pattern first. Order
#: matters: a capped percentage with a threshold also matches the plain capped
#: percentage pattern, so it has to be tried first.
PATTERNS = [
    (r"(\d+)\s*%\s*off\s*(?:up ?to)\s*rs\s*(\d+)\s*above\s*rs\s*(\d+)", "pct_cap_thr"),
    (r"(\d+)\s*%\s*off\s*(?:up ?to)\s*rs\s*(\d+)", "pct_cap"),
    (r"rs\s*(\d+)\s*off\s*above\s*rs\s*(\d+)", "flat_thr"),
    (r"^(?:flat\s*)?(\d+)\s*%\s*off\s*$", "pct"),
]

#: Offer text that is an item level price and not a basket discount. These are
#: already carried by the strikethrough prices on individual cards, so counting
#: them here would double count.
ITEM_LEVEL = ("items at", "items up to", "items starting", "store")


def parse_offer(text) -> tuple[str, float, float, float] | None:
    """One offer string to ``(kind, rate, cap, threshold)``, or None.

    Returns None for anything unrecognised rather than guessing. An offer the
    parser cannot read is counted as no discount, which understates the
    marketplace's generosity, so the direction of that failure is stated
    wherever the output is reported.
    """
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return None
    t = str(text).lower().replace("₹", "rs ").strip()
    if any(k in t for k in ITEM_LEVEL):
        return None
    for pattern, kind in PATTERNS:
        m = re.search(pattern, t)
        if not m:
            continue
        g = m.groups()
        if kind == "pct_cap_thr":
            return (kind, int(g[0]) / 100, float(g[1]), float(g[2]))
        if kind == "pct_cap":
            return (kind, int(g[0]) / 100, float(g[1]), 0.0)
        if kind == "flat_thr":
            return (kind, 0.0, float(g[0]), float(g[1]))
        return (kind, int(g[0]) / 100, np.inf, 0.0)
    return None


def discount_at(rule, basket: float) -> float:
    """Rupees off a basket of this size under one parsed rule."""
    if rule is None:
        return 0.0
    kind, rate, cap, threshold = rule
    if basket < threshold:
        return 0.0
    if kind == "flat_thr":
        return min(cap, basket)
    if kind in ("pct_cap", "pct_cap_thr"):
        return min(rate * basket, cap)
    return rate * basket


def parse_all(raw: pd.DataFrame) -> pd.DataFrame:
    """Every distinct restaurant offer in the capture, parsed."""
    required = {"platform", "restaurant_name", "restaurant_offer_text"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise KeyError(f"parse_all missing columns: {missing}")

    o = (raw.assign(restaurant_offer_text=raw["restaurant_offer_text"].fillna(""))
            .query("restaurant_offer_text != ''")
            [["platform", "restaurant_name", "restaurant_offer_text"]]
            .drop_duplicates())
    o["rule"] = o["restaurant_offer_text"].map(parse_offer)
    return o


def discount_curve(offers: pd.DataFrame, baskets) -> pd.DataFrame:
    """Median and best available coupon, as a share of basket, by platform.

    The median is the typical restaurant's offer and is the case to quote. The
    maximum is a bound: reaching it means switching to whichever restaurant
    happens to run the best promotion, which is not the same as getting the dish
    you searched for.
    """
    rows = []
    for platform, g in offers.groupby("platform"):
        rules = list(g["rule"])
        n_parsed = sum(r is not None for r in rules)
        for x in baskets:
            d = np.array([discount_at(r, x) for r in rules])
            fires = d > 0
            # The plain median across all restaurants is zero wherever fewer
            # than half of them run a coupon that fires at this basket, which
            # hides a real discount available at many of them. Both are
            # reported: the share that fire, and the size where one does.
            rows.append({"platform": platform, "basket": x,
                         "share_firing": float(fires.mean()),
                         "median_pct": float(np.median(d)) / x,
                         "typical_pct": (float(np.median(d[fires])) / x
                                         if fires.any() else 0.0),
                         "best_pct": float(d.max()) / x,
                         "n_offers": len(rules), "n_parsed": n_parsed})
    return pd.DataFrame(rows)
