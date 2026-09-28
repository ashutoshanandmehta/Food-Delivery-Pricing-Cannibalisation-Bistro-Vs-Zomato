"""Tests for the menu price preprocessing.

These exist because two decisions in this module can invert the headline
result. Quantity normalisation moves the coefficient by log(units), which for
the Aloo Pyaaz Paratha case is 0.69 log points, larger than any plausible true
effect. And a quantity that is silently coerced to 1 would do that invisibly.

Every test below either pins a real number read off a screenshot, or asserts
the direction a mistake would push the answer.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import menu


# --- quantity parsing -------------------------------------------------------

@pytest.mark.parametrize("text,value,unit", [
    ("Aloo Pyaz Parantha With Curd - 1 pc", 1.0, "piece"),
    ("Angoori Jamun (4 Nos)", 4.0, "piece"),
    ("Boiled Egg [2 Pieces]", 2.0, "piece"),
    ("(1 Pc) Crispy, golden-fried samosas", 1.0, "piece"),
    ("11 Pieces", 11.0, "piece"),
    ("4 cups", 4.0, "piece"),
    ("260 ml", 260.0, "ml"),
    ("330 ml", 330.0, "ml"),
    ("Serves 1", 1.0, "serving"),
    ("Serves 2", 2.0, "serving"),
])
def test_quantity_parses_the_forms_seen_in_the_wild(text, value, unit):
    assert menu.parse_quantity(text) == (value, unit)


def test_cups_are_pieces_not_millilitres():
    """Marketplaces sell chai by the cup. Mapping cups to ml would require
    inventing a millilitres-per-cup constant that nobody discloses."""
    assert menu.parse_quantity("4 cups") == (4.0, "piece")


def test_half_is_quantity_not_composition():
    """Half Chicken Dum Biryani is a portion word with a defined ratio, so it
    is normalised rather than thrown away."""
    assert menu.parse_quantity("Half Chicken Dum Biryani") == (0.5, "serving")


def test_unstated_quantity_returns_none_not_one():
    """The failure this guards: silently coercing a missing count to 1 applies
    a log(units) shift that nobody can see afterwards."""
    assert menu.parse_quantity("Moong Dal Halwa") == (None, None)
    assert menu.parse_quantity("") == (None, None)
    assert menu.parse_quantity(None) == (None, None)


def test_serving_range_is_refused_rather_than_guessed():
    with pytest.raises(ValueError, match="Party packs"):
        menu.parse_quantity("Serves 3-4")


# --- basis and precedence ---------------------------------------------------

@pytest.mark.parametrize("bistro_qty,basis", [
    ("2 Pieces", "piece"), ("11 Pieces", "piece"), ("4 cups", "piece"),
    ("260 ml", "ml"), ("330 ml", "ml"),
    ("Serves 1", "serving"), ("Serves 2", "serving"),
])
def test_basis_comes_from_the_bistro_side(bistro_qty, basis):
    """Bistro states a quantity on every item, so the basis is always
    assignable from a source that is complete."""
    assert menu.assign_basis(bistro_qty) == basis


def test_name_beats_description_in_the_precedence_chain():
    """Swiggy dish cards carry no description at all, so a description-first
    rule would fail on most marketplace rows."""
    units, unit, source = menu.resolve_quantity(
        name="Angoori Jamun (4 Nos)", description="(2 Pc) sweet", basis="piece")
    assert (units, source) == (4.0, "name")


def test_photo_inferred_quantity_never_enters_the_primary_spec():
    """Kaleva's Aloo Samosa photo shows two samosas while the description says
    (1 Pc). The picture overstates, so it is a sensitivity only."""
    _, _, source = menu.resolve_quantity(name="Aloo Samosa", basis="piece", photo_qty=2)
    assert source == "photo"
    assert source not in menu.QTY_SOURCES_PRIMARY


def test_silent_listing_defaults_to_one_and_says_so():
    """Defaulting is transparent and testable. Deleting silent listings is the
    non-random choice, because listings that state a count are systematically
    the small ones."""
    units, _, source = menu.resolve_quantity(name="Moong Dal Halwa", basis="piece")
    assert (units, source) == (1.0, "assumed")


# --- the number that can flip the result ------------------------------------

def test_normalisation_flips_the_aloo_paratha_comparison():
    """The real case. Bistro Rs 159 for 2 pieces, Haldiram's Rs 140 for 1.
    Raw, Bistro looks dearer. Per piece, Bistro is 43% cheaper. Both numbers go
    in the paper."""
    df = pd.DataFrame({
        "matched_id": [59, 59], "platform": ["Bistro", "Zomato"],
        "list_price": [159.0, 140.0], "units": [2.0, 1.0],
    })
    out = menu.normalise_prices(df)
    assert out.loc[0, "list_price"] > out.loc[1, "list_price"]      # raw: dearer
    assert out.loc[0, "unit_price"] < out.loc[1, "unit_price"]      # per unit: cheaper
    gap = 1 - out.loc[0, "unit_price"] / out.loc[1, "unit_price"]
    assert gap == pytest.approx(0.432, abs=0.01)


def test_normalisation_can_also_cut_against_the_hypothesis():
    """Desserts run the other way. Swiggy Angoori Jamun is Rs 35 for 4 pieces,
    Rs 8.75 each, against Bistro's Rs 49 Gulab Jamun for one. A pipeline that
    only ever helped the hypothesis would be the bug."""
    df = pd.DataFrame({
        "matched_id": [55, 55], "platform": ["Bistro", "Swiggy"],
        "list_price": [49.0, 35.0], "units": [1.0, 4.0],
    })
    out = menu.normalise_prices(df)
    assert out.loc[0, "unit_price"] > out.loc[1, "unit_price"]
    assert out.loc[1, "unit_price"] == pytest.approx(8.75)


def test_delta_is_the_exact_shift_normalisation_applies():
    """beta_normalised = beta_raw - delta. For a 2-vs-1 piece dish delta is
    log(2) = 0.69 log points, which is why it is reported, not buried."""
    df = pd.DataFrame({
        "matched_id": [59, 59], "section": ["All Day Breakfast"] * 2,
        "platform": ["Bistro", "Zomato"], "units": [2.0, 1.0],
    })
    d = menu.delta_by_section(df)
    assert d.loc[0, "delta_mean"] == pytest.approx(np.log(2), abs=1e-9)


def test_diet_coke_is_a_like_for_like_comparison():
    """Identical branded 330ml can on both sides. Zero composition confound,
    so the gap is pure platform margin. This is the calibration item."""
    df = pd.DataFrame({
        "matched_id": [75, 75], "platform": ["Bistro", "Zomato"],
        "list_price": [50.0, 66.0], "units": [330.0, 330.0],
    })
    out = menu.normalise_prices(df)
    ratio = out.loc[0, "unit_price"] / out.loc[1, "unit_price"]
    assert ratio == pytest.approx(50 / 66, abs=1e-9)
    assert 1 - ratio == pytest.approx(0.242, abs=0.01)


# --- price construction -----------------------------------------------------

def test_effective_price_uses_the_item_strikethrough_only():
    df = pd.DataFrame({
        "matched_id": [1, 2], "platform": ["Zomato", "Zomato"],
        "list_price": [224.50, 799.0], "strikethrough_price": [449.0, np.nan],
        "units": [1.0, 1.0],
    })
    out = menu.normalise_prices(df)
    assert out.loc[0, "effective_price"] == pytest.approx(224.50)
    assert out.loc[0, "discount_pct"] == pytest.approx(0.5)
    assert out.loc[1, "effective_price"] == pytest.approx(799.0)
    assert out.loc[1, "discount_pct"] == pytest.approx(0.0)


def test_non_positive_units_are_refused():
    df = pd.DataFrame({"list_price": [100.0], "units": [0.0]})
    with pytest.raises(ValueError, match="Non-positive units"):
        menu.normalise_prices(df)


def test_cell_weights_stop_screenshot_count_driving_the_estimate():
    """One Bistro price against six Zomato quotes must not give Bistro one
    twelfth of the within-dish weight."""
    df = pd.DataFrame({
        "matched_id": [1] * 7,
        "platform": ["Bistro"] + ["Zomato"] * 6,
    })
    out = menu.add_cell_weights(df)
    assert out.loc[0, "cell_weight"] == pytest.approx(1.0)
    assert out.loc[1, "cell_weight"] == pytest.approx(1 / 6)
    per_platform = out.groupby("platform")["cell_weight"].sum()
    assert per_platform["Bistro"] == pytest.approx(per_platform["Zomato"])


def test_bulk_listing_is_caught_by_a_numeric_rule():
    """Zomato's Bikaner Sweets lists White Rasgulla at Rs 300 with no count,
    against Bistro's Rs 49 for one piece. A per piece sweet price is bounded;
    a one kilogram box is not."""
    df = pd.DataFrame({
        "matched_id": [57] * 3, "basis": ["piece"] * 3,
        "qty_source": ["name", "name", "assumed"],
        "unit_price": [49.0, 55.0, 300.0],
    })
    out = menu.flag_bulk_suspects(df)
    assert list(out["bulk_suspect"]) == [False, False, True]


# --- grading ----------------------------------------------------------------

@pytest.mark.parametrize("core,form,qty,comp,grade", [
    (True,  True,  True,  True,  "A_exact"),
    (True,  True,  False, True,  "B_close"),
    (True,  True,  True,  False, "B_close"),
    (True,  True,  False, False, "C_loose"),
    (False, True,  True,  True,  "D_reject"),   # different dish
    (True,  False, True,  True,  "D_reject"),   # bulk or party pack
])
def test_grading_tree(core, form, qty, comp, grade):
    df = pd.DataFrame({"core_ok": [core], "form_ok": [form],
                       "qty_ok": [qty], "comp_ok": [comp]})
    assert menu.grade_matches(df).loc[0, "match_grade"] == grade


def test_core_and_form_are_absolute_vetoes():
    """A different dish or a one kilogram box is not a price comparison at all,
    however good the other checks look."""
    df = pd.DataFrame({"core_ok": [False], "form_ok": [True],
                       "qty_ok": [True], "comp_ok": [True]})
    assert menu.grade_matches(df).loc[0, "match_grade"] == "D_reject"


def test_ungraded_rows_are_refused_rather_than_passed():
    df = pd.DataFrame({"core_ok": [True], "form_ok": [None],
                       "qty_ok": [True], "comp_ok": [True]})
    with pytest.raises(ValueError, match="Ungraded"):
        menu.grade_matches(df)


# --- the nonparametric insurance policy -------------------------------------

def test_bistro_rank_is_model_free():
    """Rank of the Bistro price inside the dish's marketplace distribution.
    Under the null its mean is 0.5, and it survives even if the log-linear
    specification turns out fragile."""
    df = pd.DataFrame({
        "matched_id": [1] * 5,
        "platform": ["Bistro", "Zomato", "Zomato", "Swiggy", "Swiggy"],
        "unit_price": [100.0, 150.0, 200.0, 120.0, 90.0],
    })
    r = menu.bistro_percentile_rank(df)
    assert r.loc[0, "bistro_rank"] == pytest.approx(0.25)   # cheaper than 3 of 4
    assert r.loc[0, "n_marketplace"] == 4


# --- schema and IO ----------------------------------------------------------

def test_loader_names_the_missing_column(tmp_path):
    p = tmp_path / "prices.csv"
    p.write_text("matched_id,platform,dish_name_raw\n1,Zomato,Biryani\n")
    with pytest.raises(KeyError, match="list_price"):
        menu.load_menu_prices(p)


def test_loader_rejects_an_unknown_platform(tmp_path):
    p = tmp_path / "prices.csv"
    p.write_text("matched_id,platform,dish_name_raw,list_price\n1,Zepto,Biryani,99\n")
    with pytest.raises(ValueError, match="Zepto"):
        menu.load_menu_prices(p)


def test_bistro_menu_basis_assignment_covers_every_selected_dish():
    """Runs against the real committed Bistro menu. Every item must yield a
    basis, because the basis is what the marketplace side gets compared on."""
    from src import config
    d = pd.read_csv(config.BISTRO_MENU)
    party = d["serves_or_pieces"].astype(str).str.contains("3-4", na=False)
    for qty in d.loc[~party, "serves_or_pieces"]:
        assert menu.assign_basis(qty) in menu.BASIS_PREFERENCE
    assert party.sum() == 3          # the three Party Packs, excluded by design


# --- the volume basis, and why it needs both sides --------------------------

def test_missing_volume_is_unknown_not_one_millilitre():
    """A can with no stated volume is not 1 ml. Assuming it would price Bistro's
    330 ml can at Rs 0.15/ml against a marketplace can at Rs 66/ml, a 440x
    error."""
    units, unit, source = menu.resolve_quantity("Coke Diet Can", basis="ml")
    assert units is None
    assert source == "unknown"


def test_basis_downgrades_to_serving_when_the_marketplace_states_no_volume():
    """Diet Coke. Bistro states 330 ml; none of the marketplace listings state a
    volume. So the honest comparison is one can against one can."""
    assert menu.resolve_basis("330 ml", ["Diet Coke Can", "Coke Diet Can", "Coke"]) == "serving"


def test_basis_keeps_millilitres_when_enough_listings_state_volume():
    """Lemon Iced Tea. Three marketplace listings state a volume, which clears
    the minimum, so the per millilitre comparison is available."""
    texts = ["300 ml", "Lemon Ice Tea (250 mL)", "[300 ml]", "Lemon Iced Tea", "Lemon Ice Tea"]
    assert menu.resolve_basis("260 ml", texts) == "ml"


def test_one_stated_volume_is_not_enough_to_hold_the_millilitre_basis():
    assert menu.resolve_basis("260 ml", ["300 ml", "Lemon Iced Tea", "Lemon Ice Tea"]) == "serving"


def test_diet_coke_on_the_serving_basis_gives_the_sensible_comparison():
    """Rs 50 against Rs 66 for the same branded can, not Rs 0.15 against Rs 66."""
    df = pd.DataFrame({
        "matched_id": [75, 75], "platform": ["Bistro", "Zomato"],
        "list_price": [50.0, 66.0], "units": [1.0, 1.0],
    })
    out = menu.normalise_prices(df)
    assert out.loc[0, "unit_price"] == pytest.approx(50.0)
    assert 1 - out.loc[0, "unit_price"] / out.loc[1, "unit_price"] == pytest.approx(0.242, abs=0.01)


# --- servings that are not one size -----------------------------------------

def test_idli_sambar_serving_is_flagged_as_not_standardised():
    """The real case. Bistro says Serves 1 with no piece count. Marketplace
    listings say 2, 3, 4 and 12 pieces, Rs 14.58 to Rs 78.57 each. Calling all
    of those one serving is not a comparison, and Bistro's piece count is
    unknown so it cannot be normalised either."""
    df = pd.DataFrame({
        "matched_id": [60] * 5, "basis": ["serving"] * 5,
        "stated_pieces": [np.nan, 2.0, 3.0, 4.0, 12.0],
    })
    out = menu.flag_unstandardised_servings(df)
    assert out["serving_unreliable"].all()
    assert out["serving_piece_spread"].iloc[0] == pytest.approx(6.0)


def test_a_consistent_serving_is_not_flagged():
    df = pd.DataFrame({
        "matched_id": [7] * 3, "basis": ["serving"] * 3,
        "stated_pieces": [2.0, 2.0, np.nan],
    })
    assert not menu.flag_unstandardised_servings(df)["serving_unreliable"].any()


def test_one_stated_count_cannot_establish_a_spread():
    """A single listing stating a count says nothing about whether servings
    vary, so it must not trigger the flag."""
    df = pd.DataFrame({
        "matched_id": [26] * 4, "basis": ["serving"] * 4,
        "stated_pieces": [1.0, np.nan, np.nan, np.nan],
    })
    assert not menu.flag_unstandardised_servings(df)["serving_unreliable"].any()


def test_piece_counts_are_kept_even_on_a_serving_basis_dish():
    """Discarding the marketplace piece count is what hid the Idli Sambar
    problem. The column must survive into the panel."""
    df = pd.DataFrame({
        "matched_id": [60, 60], "basis": ["serving"] * 2,
        "stated_pieces": [2.0, 12.0],
    })
    out = menu.flag_unstandardised_servings(df)
    assert "stated_pieces" in out.columns
    assert out["stated_pieces"].tolist() == [2.0, 12.0]


# --- imputing a missing quantity, and what must never be used ---------------

def test_same_restaurant_volume_carries_across_platforms():
    """Chaayos lists Lemon Iced Tea at Rs 209 on both platforms. Zomato states
    300 ml, Swiggy states nothing. Same product read twice, so it carries."""
    df = pd.DataFrame({
        "matched_id": [71, 71],
        "restaurant_name": ["Chaayos Chai+Snacks=Relax"] * 2,
        "platform": ["Zomato", "Swiggy"],
        "units": [300.0, np.nan],
        "qty_source": ["name", "unknown"],
    })
    out = menu.impute_quantity(df)
    assert out.loc[1, "units"] == pytest.approx(300.0)
    assert out.loc[1, "qty_source"] == "same_restaurant"


def test_dish_median_fills_the_rest_but_is_labelled_low_confidence():
    df = pd.DataFrame({
        "matched_id": [71] * 3,
        "restaurant_name": ["Wendy's", "Theobroma", "Cha Bar"],
        "units": [250.0, 300.0, np.nan],
        "qty_source": ["name", "name", "unknown"],
    })
    out = menu.impute_quantity(df)
    assert out.loc[2, "units"] == pytest.approx(275.0)
    assert out.loc[2, "qty_source"] == "imputed_dish_median"
    assert out.loc[2, "qty_source"] not in menu.QTY_SOURCES_PRIMARY


def test_imputation_never_looks_at_price():
    """Two listings at the same price must not be given the same quantity.
    Chaayos charges Rs 209 for 300 ml and Theobroma Rs 99 for 300 ml, so price
    per ml varies more than two to one at identical volume. Using price to set
    quantity would be circular and wrong."""
    df = pd.DataFrame({
        "matched_id": [71] * 3,
        "restaurant_name": ["Wendy's", "Punjab Sweet Corner", "Theobroma"],
        "list_price": [89.0, 89.0, 99.0],
        "units": [250.0, np.nan, 300.0],
        "qty_source": ["name", "unknown", "name"],
    })
    out = menu.impute_quantity(df)
    # filled from the dish median 275, NOT from the price-matched 250
    assert out.loc[1, "units"] == pytest.approx(275.0)
    assert out.loc[1, "units"] != pytest.approx(250.0)
