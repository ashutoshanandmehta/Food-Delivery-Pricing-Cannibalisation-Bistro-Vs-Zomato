"""Tests for the switching value model.

The recommendation rests on one division and one subtraction. These tests exist
so that the two stay consistent with each other, so that the units in
CM_zomato survive a crore to rupee conversion, and so that a half filled
CM_bistro stack fails loudly instead of quietly producing a smaller cost base
and a better looking answer.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import unit_economics as ue


# --- the threshold itself ---------------------------------------------------

def test_switching_value_is_the_ratio():
    assert ue.switching_value(60.0, 40.0) == pytest.approx(1.5)


@pytest.mark.parametrize("retention", [1.0, 0.75, 0.6, 0.35, 0.30])
def test_net_contribution_is_zero_at_the_switching_value(retention):
    """The whole model in one assertion. If these two ever disagree, every
    number in the deck is wrong."""
    cm_bistro, cm_zomato = 12.0, 41.0
    alpha_star = ue.switching_value(cm_bistro, cm_zomato, retention)
    assert 0.0 <= alpha_star <= 1.0, "pick inputs where alpha* is a valid rate"
    assert ue.net_contribution(
        cm_bistro, cm_zomato, alpha_star, retention
    ) == pytest.approx(0.0, abs=1e-12)


def test_net_contribution_changes_sign_around_the_threshold():
    cm_bistro, cm_zomato = 30.0, 50.0
    a = ue.switching_value(cm_bistro, cm_zomato)
    assert ue.net_contribution(cm_bistro, cm_zomato, a - 0.05) > 0
    assert ue.net_contribution(cm_bistro, cm_zomato, a + 0.05) < 0


def test_lower_retention_raises_the_threshold():
    """Retention below 1 means part of the cannibalised volume was leaving
    anyway, so the rate the recommendation flips at must rise."""
    thresholds = [ue.switching_value(30.0, 50.0, r) for r in (1.0, 0.8, 0.5)]
    assert thresholds == sorted(thresholds)
    assert ue.switching_value(30.0, 50.0, 1.0) < ue.switching_value(30.0, 50.0, 0.5)


def test_switching_value_above_one_means_always_accretive():
    """If alpha* exceeds 1 then net contribution stays positive at alpha = 1,
    which is total cannibalisation."""
    cm_bistro, cm_zomato = 55.0, 40.0
    assert ue.switching_value(cm_bistro, cm_zomato) > 1
    assert ue.net_contribution(cm_bistro, cm_zomato, 1.0) > 0


def test_retention_one_reproduces_the_conservative_case():
    assert ue.switching_value(30.0, 50.0, 1.0) == pytest.approx(30.0 / 50.0)
    assert ue.net_contribution(30.0, 50.0, 0.4, 1.0) == pytest.approx(30.0 - 0.4 * 50.0)


# --- refusing to return a plausible wrong number ----------------------------

@pytest.mark.parametrize("bad", [0.0, -12.0, np.nan, np.inf])
def test_switching_value_rejects_non_positive_cm_zomato(bad):
    with pytest.raises(ValueError):
        ue.switching_value(30.0, bad)


@pytest.mark.parametrize("bad", [-0.1, 1.1, np.nan])
def test_rates_must_be_fractions(bad):
    with pytest.raises(ValueError):
        ue.net_contribution(30.0, 50.0, bad)
    with pytest.raises(ValueError):
        ue.net_contribution(30.0, 50.0, 0.4, retention=bad)


def test_zero_retention_is_refused_rather_than_returning_infinity():
    with pytest.raises(ValueError):
        ue.switching_value(30.0, 50.0, retention=0.0)


# --- the deck tables --------------------------------------------------------

def test_sensitivity_table_matches_net_contribution_row_by_row():
    alphas = [0.2, 0.4, 0.6, 0.8, 0.95]
    t = ue.sensitivity_table(30.0, 50.0, alphas, retention=0.7)
    assert list(t.columns) == ue.DECK_COLUMNS
    assert len(t) == len(alphas)
    for _, row in t.iterrows():
        assert row["net_cm_per_order"] == pytest.approx(
            ue.net_contribution(30.0, 50.0, row["alpha"], 0.7)
        )


def test_sensitivity_table_counts_add_to_the_basis():
    t = ue.sensitivity_table(30.0, 50.0, [0.2, 0.6, 0.95], basis=100)
    total = t["cannibalised_orders"] + t["incremental_orders"]
    assert np.allclose(total, 100.0)


def test_sensitivity_table_per_order_result_is_independent_of_basis():
    a = ue.sensitivity_table(30.0, 50.0, [0.6], basis=1)
    b = ue.sensitivity_table(30.0, 50.0, [0.6], basis=1000)
    assert a["net_cm_per_order"].iloc[0] == pytest.approx(
        b["net_cm_per_order"].iloc[0]
    )


def test_retained_orders_equal_cannibalised_when_retention_is_one():
    t = ue.sensitivity_table(30.0, 50.0, [0.4, 0.8], retention=1.0)
    assert np.allclose(t["cannibalised_orders"], t["retained_orders"])


def test_sensitivity_grid_shape_and_cells():
    cases = {"low": 20.0, "base": 30.0, "high": 42.0}
    alphas = [0.2, 0.6, 0.95]
    g = ue.sensitivity_grid(cases, 50.0, alphas)
    assert g.shape == (3, 3)
    assert list(g.index) == ["low", "base", "high"]
    assert g.loc["base", "alpha=60%"] == pytest.approx(
        ue.net_contribution(30.0, 50.0, 0.6)
    )


def test_switching_value_grid_matches_the_scalar_function():
    cases = {"low": 20.0, "high": 42.0}
    g = ue.switching_value_grid(cases, 50.0, [1.0, 0.5])
    assert g.loc["high", "retention=50%"] == pytest.approx(
        ue.switching_value(42.0, 50.0, 0.5)
    )


# --- CM_zomato from the panel -----------------------------------------------

def _panel_row():
    """Contribution 1,097 cr on NOV 10,769 cr is 10.19% of NOV, so 10.19 rupees
    of contribution per 100 rupees of order value. Q1FY27 actuals."""
    return pd.DataFrame(
        {
            "quarter": ["Q1FY27"],
            "fd_nov": [10769.0],
            "fd_adj_revenue": [3537.0],
            "fd_contribution": [1097.0],
            "fd_adj_ebitda": [606.0],
        }
    )


def test_cm_zomato_from_disclosed_contribution():
    out = ue.cm_zomato_from_contribution(_panel_row())
    assert out["cm_pct_nov"].iloc[0] == pytest.approx(1097 / 10769)
    assert out["cm_zomato"].iloc[0] == pytest.approx(10.19, abs=0.01)


def test_cm_zomato_basis_scales_linearly():
    a = ue.cm_zomato_from_contribution(_panel_row(), basis=100.0)
    b = ue.cm_zomato_from_contribution(_panel_row(), basis=1000.0)
    assert b["cm_zomato"].iloc[0] == pytest.approx(10 * a["cm_zomato"].iloc[0])


def test_contribution_path_needs_no_assumption_but_addback_path_does():
    """The disclosed path sits above the EBITDA floor and below the floor plus
    a generous add back. If it did not, one of the two is being misread."""
    disclosed = ue.cm_zomato_from_contribution(_panel_row())["cm_zomato"].iloc[0]
    floor = ue.cm_zomato_from_filings(_panel_row(), 0.0)["cm_zomato"].iloc[0]
    generous = ue.cm_zomato_from_filings(_panel_row(), 0.40)["cm_zomato"].iloc[0]
    assert floor < disclosed < generous


def test_addback_floor_is_ebitda_over_nov():
    out = ue.cm_zomato_from_filings(_panel_row(), fixed_cost_addback=0.0)
    assert out["cm_zomato"].iloc[0] == pytest.approx(100 * 606 / 10769)


def test_a_bigger_addback_weakens_the_case_for_bistro():
    """Direction of the error, asserted rather than only documented. A generous
    add back raises CM_zomato and therefore lowers alpha*."""
    low = ue.cm_zomato_from_filings(_panel_row(), 0.10)["cm_zomato"].iloc[0]
    high = ue.cm_zomato_from_filings(_panel_row(), 0.40)["cm_zomato"].iloc[0]
    assert high > low
    assert ue.switching_value(6.0, high) < ue.switching_value(6.0, low)


def test_cm_zomato_names_the_missing_column():
    bad = _panel_row().drop(columns=["fd_contribution"])
    with pytest.raises(KeyError, match="fd_contribution"):
        ue.cm_zomato_from_contribution(bad)


# --- the CM_bistro stack ----------------------------------------------------

def _stack():
    return {
        "order_value": {"value": 185.0, "source": "menu sample", "confidence": "low"},
        "food_cogs": {"value": -65.0, "source": "benchmark", "confidence": "low"},
        "kitchen_marginal": {"value": -30.0, "source": "benchmark", "confidence": "very low"},
        "delivery_marginal": {"value": -35.0, "source": "Blinkit", "confidence": "medium"},
        "packaging_and_waste": {"value": -12.0, "source": "benchmark", "confidence": "low"},
    }


def test_stack_sums_to_the_margin():
    total, frame = ue.cm_bistro_stack(_stack())
    assert total == pytest.approx(185.0 - 65.0 - 30.0 - 35.0 - 12.0)
    assert len(frame) == 5
    assert frame["value"].sum() == pytest.approx(total)


def test_stack_shares_are_relative_to_order_value():
    _, frame = ue.cm_bistro_stack(_stack())
    cogs = frame.loc[frame["component"] == "food_cogs", "share_of_order_value"]
    assert cogs.iloc[0] == pytest.approx(-65.0 / 185.0)


def test_a_blank_component_raises_and_names_itself():
    """A silently dropped cost line inflates CM_bistro, inflates alpha*, and
    makes the recommendation look stronger than the evidence supports."""
    s = _stack()
    s["kitchen_marginal"]["value"] = None
    with pytest.raises(ValueError, match="kitchen_marginal"):
        ue.cm_bistro_stack(s)


def test_stack_with_no_order_value_is_refused():
    s = {"food_cogs": {"value": -65.0}}
    with pytest.raises(ValueError):
        ue.cm_bistro_stack(s)


def test_empty_stack_is_refused():
    with pytest.raises(ValueError):
        ue.cm_bistro_stack({})


# --- the loader -------------------------------------------------------------

def test_loader_keeps_blank_values_as_none(tmp_path):
    p = tmp_path / "components.csv"
    p.write_text(
        "component,value,source,method,confidence\n"
        "order_value,185,menu sample,hand sample,low\n"
        "kitchen_marginal,,,,\n"
    )
    loaded = ue.load_cm_bistro_components(p)
    assert loaded["order_value"]["value"] == pytest.approx(185.0)
    assert loaded["kitchen_marginal"]["value"] is None
    with pytest.raises(ValueError, match="kitchen_marginal"):
        ue.cm_bistro_stack(loaded)


# --- the inverted threshold -------------------------------------------------

def test_required_cm_bistro_is_the_switching_value_inverted():
    """At the required margin, net contribution is exactly zero."""
    cm_z, alphas = 10.19, [0.2, 0.6, 1.0]
    req = ue.required_cm_bistro(cm_z, alphas, retention=0.8)
    for _, row in req.iterrows():
        assert ue.net_contribution(
            row["required_cm_bistro"], cm_z, row["alpha"], 0.8
        ) == pytest.approx(0.0, abs=1e-12)


def test_total_cannibalisation_requires_beating_the_marketplace():
    """At alpha = 1 and retention = 1 the bar collapses to CM_bistro > CM_zomato.
    This is the sentence the whole deck rests on, so it is asserted."""
    req = ue.required_cm_bistro(10.19, [1.0], retention=1.0)
    assert req["required_cm_bistro"].iloc[0] == pytest.approx(10.19)
    assert req["as_multiple_of_cm_zomato"].iloc[0] == pytest.approx(1.0)
