"""Panel loading, coverage reporting, and validation.

The validation step exists because the most likely way this project produces
a confident wrong answer is a silent parse error across Blinkit's shift to an
inventory-led accounting model. Revenue jumps, NOV does not, and every
downstream growth chart is quietly broken.
"""

from __future__ import annotations

import pandas as pd

from . import config
from .metrics import sort_by_quarter

REQUIRED = ["quarter", "source_url"]

CORE_FIELDS = [
    "fd_gov", "fd_nov", "fd_adj_revenue", "fd_contribution", "fd_adj_ebitda",
    "fd_mtu",
    "qc_gov", "qc_nov", "qc_revenue", "qc_contribution", "qc_adj_ebitda",
    "qc_orders_mn", "qc_naov", "qc_mtu", "qc_stores",
    "go_nov", "others_adj_revenue", "others_adj_ebitda",
    "consol_adj_revenue", "consol_adj_ebitda",
    "bistro_kitchens",
]


def load_panel(path=None) -> pd.DataFrame:
    path = path or config.PANEL
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Panel missing required columns: {missing}")
    if df["quarter"].duplicated().any():
        dupes = df.loc[df["quarter"].duplicated(), "quarter"].tolist()
        raise ValueError(f"Duplicate quarters in panel: {dupes}")
    return sort_by_quarter(df)


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """Which fields are populated in which quarters.

    Run this before any analysis. Fill gaps manually from the filings rather
    than letting pandas silently drop rows in a later merge.
    """
    rows = []
    for f in CORE_FIELDS:
        if f not in df.columns:
            rows.append({"field": f, "present": 0, "missing": len(df),
                         "coverage": 0.0, "status": "COLUMN ABSENT"})
            continue
        present = int(df[f].notna().sum())
        rows.append({
            "field": f,
            "present": present,
            "missing": len(df) - present,
            "coverage": round(present / len(df), 2),
            "status": "ok" if present == len(df) else "GAPS",
        })
    return pd.DataFrame(rows).sort_values("coverage")


def validate(df: pd.DataFrame, bands=None, write=True) -> pd.DataFrame:
    """Flag QoQ moves outside plausible bands.

    Breaches are written to a review queue, not raised. A definitional change
    is a legitimate breach that needs a note in ASSUMPTIONS.md, not a crash.
    Every row here must be signed off before the analysis notebooks are run.
    """
    bands = bands or config.VALIDATION_BANDS
    out = sort_by_quarter(df)
    contiguous = out["_ord"].diff() == 1

    breaches = []
    for field, (lo, hi) in bands.items():
        if field not in out.columns:
            continue
        chg = out[field].pct_change()
        flag = contiguous & chg.notna() & ((chg < lo) | (chg > hi))
        for i in out.index[flag]:
            breaches.append({
                "quarter": out.at[i, "quarter"],
                "field": field,
                "prev_value": out[field].shift(1).at[i],
                "value": out.at[i, field],
                "qoq_change": round(float(chg.at[i]), 4),
                "band": f"[{lo}, {hi}]",
                "reviewed": False,
                "explanation": "",
            })

    result = pd.DataFrame(breaches)

    # Carry forward any sign off already recorded for the same quarter and
    # field. Re-running validation must not silently reopen a breach that has
    # already been inspected and explained, or the gate becomes noise that
    # people learn to ignore.
    path = config.REVIEW_QUEUE
    if len(result) and path.exists():
        prior = pd.read_csv(path)
        if {"quarter", "field", "reviewed", "explanation"}.issubset(prior.columns):
            keep = prior[["quarter", "field", "reviewed", "explanation"]]
            result = (
                result.drop(columns=["reviewed", "explanation"])
                .merge(keep, on=["quarter", "field"], how="left")
            )
            result["reviewed"] = result["reviewed"].fillna(False).astype(bool)
            result["explanation"] = result["explanation"].fillna("")

    if write:
        config.ensure_dirs()
        result.to_csv(path, index=False)
    return result


def assert_reviewed(path=None) -> None:
    """Guard for analysis notebooks. Call at the top of each one.

    Refuses to proceed while unexplained validation breaches remain, so a
    known-bad panel cannot silently feed a chart that ends up in the deck.
    """
    path = path or config.REVIEW_QUEUE
    if not path.exists():
        raise FileNotFoundError("Run panel.validate() before analysis.")
    q = pd.read_csv(path)
    if q.empty:
        return
    unreviewed = q[~q["reviewed"].astype(bool)]
    if len(unreviewed):
        raise AssertionError(
            f"{len(unreviewed)} unreviewed validation breach(es) in {path.name}. "
            "Inspect each, set reviewed=True and record the reason in "
            "ASSUMPTIONS.md before running analysis."
        )
