"""Tests for the estimation cascade.

The specification here is derived from diagnostics rather than chosen, so the
tests guard two different things. First that each estimator does what its name
says, checked against synthetic data with a known answer. Second that the
arithmetic pieces are arithmetic: the delta bridge is an identity and the fee
wedge is a deterministic shift, and neither may quietly grow a standard error.

Every test either recovers a planted number or asserts the direction an error
would push the estimate.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import estimate as E


TRUE_GAP = np.log(0.70)  # Bistro at 70% of the marketplace price, -0.357


def synthetic(n_dishes=30, n_mkt=6, gap=TRUE_GAP, seed=1, noise=0.10):
    """A panel with a planted within-dish gap and wide between-dish spread.

    Dish base prices span an order of magnitude, so a pooled model that ignores
    the dish would be swamped by composition while item fixed effects should
    still recover ``gap``.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_dishes):
        base = np.exp(rng.uniform(np.log(40), np.log(600)))
        rows.append({"matched_id": i, "platform": "Bistro", "section": "Quick Bites",
                     "unit_price": base * np.exp(gap + rng.normal(0, noise)),
                     "units": 1.0, "list_price": base * np.exp(gap),
                     "restaurant_name": "Bistro", "basis": "piece",
                     "qty_source": "name"})
        for j in range(n_mkt):
            rows.append({"matched_id": i, "platform": "Zomato", "section": "Quick Bites",
                         "unit_price": base * np.exp(rng.normal(0, noise)),
                         "units": 1.0, "list_price": base,
                         "restaurant_name": f"r{j}", "basis": "piece",
                         # Half the marketplace cards state a count, half stay
                         # silent, which is the pattern the real panel shows.
                         "qty_source": "name" if j % 2 else "assumed"})
    df = pd.DataFrame(rows)
    counts = df.groupby(["matched_id", "platform"])["unit_price"].transform("size")
    df["cell_weight"] = 1.0 / counts
    return df


# --- the estimators do what they say ----------------------------------------

def test_item_fixed_effects_recover_a_known_gap_on_synthetic_data():
    d = E.prepare(synthetic())
    beta = E.coef(E.fit_item_fe(d))["beta"]
    assert abs(beta - TRUE_GAP) < 0.03, f"planted {TRUE_GAP:.3f}, recovered {beta:.3f}"


def test_the_pooled_model_is_the_one_that_breaks_under_composition():
    """Give owned kitchens the cheap dishes and only the pooled model is fooled."""
    rng = np.random.default_rng(7)
    rows = []
    for i in range(30):
        base = 100.0 if i < 15 else 500.0   # Bistro sells only the cheap half
        for plat in (["Bistro", "Zomato"] if i < 15 else ["Zomato"]):
            for _ in range(3):
                rows.append({"matched_id": i, "platform": plat,
                             "section": "Quick Bites", "units": 1.0,
                             "list_price": base,
                             "unit_price": base * np.exp(rng.normal(0, 0.05))})
    df = pd.DataFrame(rows)
    df["cell_weight"] = 1.0 / df.groupby(["matched_id", "platform"])["unit_price"].transform("size")
    everything = E.prepare(df)
    within, _ = E.identified_dishes(everything)

    # Pooled sees the whole menu, including the dear dishes Bistro never sells.
    pooled = E.coef(E.fit_pooled(everything))["beta"]
    # Fixed effects only ever compare a dish against itself.
    fe = E.coef(E.fit_item_fe(within))["beta"]
    assert pooled < -0.5, "pooled OLS should be dragged down by the cheap assortment"
    assert abs(fe) < 0.05, "item fixed effects should find no within-dish gap"


def test_dishes_seen_on_one_side_only_are_dropped_and_named():
    df = synthetic(n_dishes=5)
    df = df[~((df.matched_id == 3) & (df.platform == "Bistro"))]
    kept, dropped = E.identified_dishes(E.prepare(df))
    assert dropped == [3]
    assert 3 not in set(kept["matched_id"])


def test_prepare_refuses_a_frame_without_the_columns_it_needs():
    with pytest.raises(KeyError, match="prepare missing columns"):
        E.prepare(pd.DataFrame({"platform": ["Bistro"], "matched_id": [1]}))


# --- inference ---------------------------------------------------------------

def test_clustering_widens_the_standard_error_when_errors_share_a_dish_shock():
    """A shock common to a dish's marketplace quotes is not new information."""
    rng = np.random.default_rng(3)
    rows = []
    for i in range(30):
        base, shock = 200.0, rng.normal(0, 0.35)
        rows.append({"matched_id": i, "platform": "Bistro", "section": "Quick Bites",
                     "units": 1.0, "list_price": base,
                     "unit_price": base * np.exp(TRUE_GAP)})
        for _ in range(6):
            rows.append({"matched_id": i, "platform": "Zomato", "section": "Quick Bites",
                         "units": 1.0, "list_price": base,
                         "unit_price": base * np.exp(shock + rng.normal(0, 0.02))})
    df = pd.DataFrame(rows)
    df["cell_weight"] = 1.0 / df.groupby(["matched_id", "platform"])["unit_price"].transform("size")
    d = E.prepare(df)

    naive = E.fit_item_fe(d, cluster=False).bse["owned_kitchen"]
    clustered = E.fit_item_fe(d, cluster=True).bse["owned_kitchen"]
    assert clustered > naive, (
        f"clustered {clustered:.4f} should exceed naive {naive:.4f}; treating "
        f"correlated quotes as independent understates uncertainty"
    )


def test_the_wild_cluster_bootstrap_is_reproducible_and_two_sided():
    d = E.prepare(synthetic(n_dishes=12, seed=5))
    a = E.wild_cluster_bootstrap(d, n_boot=199, seed=42)
    b = E.wild_cluster_bootstrap(d, n_boot=199, seed=42)
    assert a["p_boot"] == b["p_boot"], "a seeded bootstrap must be reproducible"
    assert 0.0 <= a["p_boot"] <= 1.0
    assert a["crit_lo"] < 0 < a["crit_hi"], "the null distribution straddles zero"


def test_leave_one_dish_out_returns_one_row_per_dish():
    d = E.prepare(synthetic(n_dishes=8))
    loo = E.leave_one_dish_out(d)
    assert len(loo) == 8
    assert set(loo["dropped_dish"]) == set(range(8))


# --- the arithmetic pieces stay arithmetic ----------------------------------

def test_the_delta_bridge_is_an_identity_not_an_estimate():
    """``beta_list = beta_unit + delta`` holds exactly, because logs are additive."""
    df = synthetic(n_dishes=20)
    rng = np.random.default_rng(11)
    df["units"] = rng.choice([1.0, 2.0, 4.0, 10.0], size=len(df))
    df["unit_price"] = df["list_price"] / df["units"]
    d = E.prepare(df)

    bridge = E.delta_bridge(d)
    assert abs(bridge["identity_gap"]) < 1e-9, (
        f"the bridge must close exactly, gap was {bridge['identity_gap']:.2e}"
    )


def test_the_delta_bridge_moves_beta_by_exactly_the_quantity_gap():
    """Give Bistro twice the units and the per-unit gap must widen by log 2."""
    df = synthetic(n_dishes=20, noise=0.0)
    df["units"] = np.where(df.platform == "Bistro", 2.0, 1.0)
    df["unit_price"] = df["list_price"] / df["units"]
    bridge = E.delta_bridge(E.prepare(df))
    assert abs(bridge["delta"] - np.log(2)) < 1e-6
    assert abs((bridge["beta_list"] - bridge["beta_unit"]) - np.log(2)) < 1e-6


def test_the_fee_wedge_shifts_beta_by_a_constant_and_reports_no_standard_error():
    out = E.fee_wedge_scenario(-0.30, {"Bistro": 0.038, "Zomato": 0.772,
                                       "Swiggy": 0.587})
    z = out.set_index("platform").loc["Zomato"]
    expected = np.log1p(0.038) - np.log1p(0.772)
    assert abs(z["log_shift"] - expected) < 1e-12
    assert abs(z["beta_delivered"] - (-0.30 + expected)) < 1e-12
    assert not {"se", "p", "pvalue", "ci_lo", "ci_hi"} & set(out.columns), (
        "the wedge is one observation per platform. Attaching a standard error "
        "to it would invent precision the data does not have"
    )


def test_the_fee_wedge_always_widens_the_gap_when_the_marketplace_charges_more():
    out = E.fee_wedge_scenario(-0.10, {"Bistro": 0.038, "Zomato": 0.772})
    assert out["beta_delivered"].iloc[0] < -0.10


# --- weighting ---------------------------------------------------------------

def test_weighting_stops_screenshot_count_driving_the_estimate():
    """Duplicating one dish's marketplace cards must not move the weighted beta."""
    df = synthetic(n_dishes=15, seed=9)
    d0 = E.prepare(df)
    beta_w0 = E.coef(E.fit_item_fe(d0, weighted=True))["beta"]
    beta_u0 = E.coef(E.fit_item_fe(d0, weighted=False))["beta"]

    extra = df[(df.matched_id == 0) & (df.platform == "Zomato")]
    fat = pd.concat([df] + [extra] * 5, ignore_index=True)
    fat["cell_weight"] = 1.0 / fat.groupby(["matched_id", "platform"])["unit_price"].transform("size")
    d1 = E.prepare(fat)
    beta_w1 = E.coef(E.fit_item_fe(d1, weighted=True))["beta"]
    beta_u1 = E.coef(E.fit_item_fe(d1, weighted=False))["beta"]

    assert abs(beta_w1 - beta_w0) < 1e-9, "cell weights should absorb the duplication"
    assert abs(beta_u1 - beta_u0) > abs(beta_w1 - beta_w0), (
        "the unweighted estimate should be the one that moves"
    )


# --- the rank test -----------------------------------------------------------

def test_the_rank_test_reads_a_planted_direction():
    cheap = pd.Series([0.0, 0.1, 0.15, 0.2, 0.05, 0.1, 0.0, 0.25, 0.1, 0.2])
    out = E.rank_test(cheap)
    assert out["mean_rank"] < 0.5
    assert out["wilcoxon_p"] < 0.05
    assert out["n_below_half"] == 10


def test_the_rank_test_finds_nothing_when_ranks_sit_at_the_null():
    out = E.rank_test(pd.Series([0.5] * 9))
    assert out["mean_rank"] == 0.5
    assert np.isnan(out["wilcoxon_p"])


# --- the cascade --------------------------------------------------------------

def test_the_cascade_reports_a_decision_for_every_gate():
    d = synthetic(n_dishes=20)
    ranks = pd.Series(np.full(20, 0.2))
    trail, chosen = E.run_cascade(d, ranks=ranks, n_boot=99)
    assert list(trail["step"]) == list(range(1, 11))
    assert trail["consequence"].str.len().gt(0).all(), "every gate must state a consequence"
    assert chosen["n_clusters"] == 20
    assert abs(chosen["coef"]["beta"] - TRUE_GAP) < 0.05


def test_the_cascade_sends_a_small_cluster_count_to_the_bootstrap():
    d = synthetic(n_dishes=12)
    trail, _ = E.run_cascade(d, n_boot=99)
    gate6 = trail[trail.step == 6].iloc[0]
    assert gate6["statistic"] == 12
    assert "bootstrap is the inference" in gate6["consequence"]


def test_the_real_panel_survives_the_whole_cascade():
    from src import config, menu
    panel = pd.read_csv(config.MENU_PRICES_LONG)
    ranks = menu.bistro_percentile_rank(panel, price_col="unit_price")["bistro_rank"]
    trail, chosen = E.run_cascade(panel, ranks=ranks, n_boot=99)

    assert len(trail) == 10
    assert chosen["n_clusters"] >= 20, "too few dishes left to cluster on"
    assert chosen["coef"]["beta"] < 0, "Bistro should price below the marketplaces"
    assert chosen["dropped_dishes"] == [], "every dish should identify the contrast"


def test_the_quantity_sensitivity_refuses_a_panel_without_quantity_provenance():
    """Without qty_source there is no way to know which quantities were assumed."""
    df = synthetic(n_dishes=6).drop(columns="qty_source")
    with pytest.raises(KeyError):
        E.quantity_sensitivity(df)


def test_the_quantity_gate_demotes_the_unit_price_when_the_rule_can_move_it():
    """The real panel is the case this gate exists for."""
    from src import config, menu
    panel = menu.load_menu_prices(config.MENU_PRICES_LONG)
    trail, chosen = E.run_cascade(panel, n_boot=99)
    gate9 = trail[trail.step == 9].iloc[0]

    qs = chosen["quantity_sensitivity"]
    unit = qs[qs.assumption != "none"]
    assert (unit.beta < 0).all(), "every quantity rule should keep the sign"
    assert not (unit.p < E.ALPHA).all(), (
        "this panel is the motivating case: at least one defensible quantity "
        "rule must fail significance, otherwise the gate is untested here"
    )
    assert chosen["primary_outcome"] == "list_price"
    assert "list price specification leads" in gate9["consequence"]


# --- coupons -----------------------------------------------------------------

def test_a_capped_coupon_stops_growing_once_the_cap_binds():
    from src import offers
    rule = offers.parse_offer("70% off upto ₹140")
    assert rule[0] == "pct_cap"
    assert offers.discount_at(rule, 100) == 70.0     # below the cap, full rate
    assert offers.discount_at(rule, 1000) == 140.0   # capped
    assert offers.discount_at(rule, 200) == 140.0    # binds at 140/0.70


def test_a_threshold_coupon_pays_nothing_below_its_threshold():
    from src import offers
    rule = offers.parse_offer("Flat ₹150 OFF above ₹599")
    assert offers.discount_at(rule, 598) == 0.0
    assert offers.discount_at(rule, 599) == 150.0


def test_item_level_offers_are_not_counted_as_basket_coupons():
    """Strikethrough prices already carry these. Counting both double counts."""
    from src import offers
    for t in ("Items at ₹59", "Items up to 50% off", "Items starting at ₹219"):
        assert offers.parse_offer(t) is None, t


def test_an_unreadable_offer_is_worth_nothing_rather_than_a_guess():
    from src import offers
    assert offers.parse_offer("Buy one get one on selected beverages") is None
    assert offers.discount_at(None, 500) == 0.0


def test_the_best_coupon_is_never_worse_than_the_median_one():
    from src import config, offers
    raw = pd.read_csv(config.MARKETPLACE_RAW)
    curve = offers.discount_curve(offers.parse_all(raw), (200, 500))
    assert (curve.best_pct >= curve.median_pct).all()
    assert (curve.n_parsed > 0).all(), "no offer parsed, the rules have drifted"


def test_a_coupon_narrows_the_checkout_gap_and_can_close_it():
    from src import config, offers
    fees = pd.read_csv(config.CHECKOUT_FEES).drop_duplicates(
        "platform", keep="first").set_index("platform")
    raw = pd.read_csv(config.MARKETPLACE_RAW)
    dc = offers.discount_curve(offers.parse_all(raw), E.BASKET_GRID)
    out = E.checkout_comparison(-0.206, fees, dc)

    for (plat, basket), g in out.groupby(["platform", "basket"]):
        g = g.set_index("coupon")
        assert g.loc["typical coupon", "gap"] >= g.loc["none", "gap"] - 1e-9, (
            f"a coupon must narrow the gap, not widen it ({plat} at {basket})")
        assert g.loc["best coupon", "gap"] >= g.loc["typical coupon", "gap"] - 1e-9


def test_the_owned_kitchen_may_discount_too():
    """Assuming Bistro never discounts is the same error in reverse."""
    fees = pd.DataFrame({
        "item_total": [100.0, 100.0], "delivery_fee": [0.0, 50.0],
        "platform_fee": [np.nan, 10.0], "convenience_fee": [3.0, np.nan],
        "packaging_fee": [np.nan, np.nan], "gst_and_other": [np.nan, 5.0],
        "order_discount": [np.nan, np.nan]},
        index=pd.Index(["Bistro", "Zomato"], name="platform"))
    plain = E.checkout_comparison(0.0, fees, baskets=(400,)).gap.iloc[0]
    promo = E.checkout_comparison(0.0, fees, baskets=(400,),
                                  owned_discount=0.40).gap.iloc[0]
    assert promo < plain, "a Bistro promotion should widen the gap in its favour"
