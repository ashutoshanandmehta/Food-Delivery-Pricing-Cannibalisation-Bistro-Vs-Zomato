"""Tests for the derived metrics.

These exist because the frequency calculation involves a crore-to-rupee
conversion and a monthly-to-quarterly reconciliation. Both are easy to get
wrong in a way that produces plausible-looking but incorrect numbers.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import metrics


def test_quarter_ordinal_is_monotonic():
    seq = ["Q1FY25", "Q2FY25", "Q3FY25", "Q4FY25", "Q1FY26"]
    ords = [metrics.quarter_to_ordinal(q) for q in seq]
    assert ords == sorted(ords)
    assert all(b - a == 1 for a, b in zip(ords, ords[1:]))


def test_quarter_ordinal_rejects_garbage():
    with pytest.raises(ValueError):
        metrics.quarter_to_ordinal("FY26Q1")


def test_quick_commerce_frequency_units():
    """Quick commerce discloses Orders, so orders per customer per month is a
    real number rather than a derived one."""
    df = pd.DataFrame({
        "quarter": ["Q1FY27"],
        "qc_nov": [17132.0],       # crore
        "qc_orders_mn": [331.0],   # millions
        "qc_naov": [518.0],        # rupees
        "qc_mtu": [31.8],          # millions
    })
    out = metrics.add_derived(df)
    # 331mn orders / (31.8mn customers * 3 months) = 3.47 orders/customer/month
    assert out["qc_frequency"].iloc[0] == pytest.approx(331.0 / (31.8 * 3))
    # NOV / orders must reproduce the disclosed net AOV. A gap means a units bug.
    assert out["qc_naov_derived"].iloc[0] == pytest.approx(518.0, rel=0.01)


def test_food_delivery_uses_nov_per_customer_not_frequency():
    """Food delivery never disclosed Orders or AOV, so frequency cannot be
    separated from ticket size. NOV per transacting customer carries both."""
    df = pd.DataFrame({
        "quarter": ["Q1FY27"],
        "fd_nov": [10769.0],   # crore
        "fd_mtu": [27.2],      # millions
    })
    out = metrics.add_derived(df)
    assert "fd_frequency" not in out.columns
    # 10,769 cr / 27.2mn customers = Rs 3,959 of NOV per customer per quarter
    assert out["fd_nov_per_mtu"].iloc[0] == pytest.approx(3959.2, rel=0.01)


def test_contribution_margin_is_read_not_derived():
    df = pd.DataFrame({
        "quarter": ["Q1FY27"],
        "fd_nov": [10769.0],
        "fd_contribution": [1097.0],
    })
    out = metrics.add_derived(df)
    assert out["fd_cm_pct_nov"].iloc[0] == pytest.approx(1097 / 10769)


def test_decomposition_residual_is_zero():
    """Log-space contributions must sum exactly to total log growth."""
    n = 8
    df = pd.DataFrame({
        "quarter": [f"Q{q}FY{y}" for y in (25, 26) for q in (1, 2, 3, 4)],
        "fd_nov": np.linspace(8000, 12000, n),
        "fd_mtu": np.linspace(20, 25, n),
    })
    d = metrics.add_derived(df)
    dec = metrics.decompose_growth(d, "fd_nov", ["fd_mtu", "fd_nov_per_mtu"])
    assert dec["residual"].abs().max() < 1e-10


def test_decomposition_needs_two_drivers():
    df = pd.DataFrame({"quarter": ["Q1FY26"], "fd_nov": [1.0], "fd_mtu": [1.0]})
    with pytest.raises(ValueError):
        metrics.decompose_growth(df, "fd_nov", ["fd_mtu"])


def test_growth_returns_nan_across_gaps():
    """A missing quarter must produce NaN, not a wrong growth rate."""
    df = pd.DataFrame({
        "quarter": ["Q1FY25", "Q3FY25"],  # Q2 missing
        "fd_nov": [8000.0, 9000.0],
    })
    out = metrics.add_growth(df, ["fd_nov"])
    assert np.isnan(out["fd_nov_qoq"].iloc[1])


def test_real_panel_loads_and_reconciles():
    """The committed panel must load, sort, and reproduce the disclosed net AOV
    from NOV over Orders. This is the guard against a transcription error in a
    hand extracted table."""
    from src import panel as panel_mod

    df = metrics.add_derived(panel_mod.load_panel())
    assert len(df) >= 12
    chk = df.dropna(subset=["qc_naov", "qc_naov_derived"])
    assert len(chk) >= 5
    gap = (chk["qc_naov_derived"] / chk["qc_naov"] - 1).abs().max()
    assert gap < 0.02, f"NOV/Orders disagrees with disclosed NAOV by {gap:.1%}"
