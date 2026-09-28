"""Build the analysis panel from the transcribed marketplace screenshots.

Run from the repo root::

    python src/build_menu_panel.py

Reads  data/manual/marketplace_prices_raw.csv   (831 transcribed rows)
       data/manual/bistro_menu_delhi.csv        (the anchor side)
Writes data/processed/menu_prices_long.csv      (the analysis panel)
       data/processed/menu_exclusion_flow.csv   (the CONSORT-style flow)

Every exclusion is counted and written out, because the paper's inclusion and
exclusion section needs the numbers by platform and the direction each drop
biases the estimate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config, menu
from . import menu_mapping as mm

NON_MATCHING_SECTIONS = (
    "recommended for you|most ordered|try new deals|items at|free dish"
)

#: Listings that pass the token rules but are a different product format.
#: Bistro's Masala Dosa Pops are ten snack-sized bites; the marketplaces return
#: full masala dosas. Token matching on "dosa" cannot see the difference. Kept
#: only to seed the review sheet; the verdict of record now lives in the
#: reviewed CSV that :func:`apply_format_review` reads.
MANUAL_CORE_REJECT = {22}

#: Columns identifying one reviewed listing. Verified unique on both sides, and
#: the merge asserts the row count is unchanged rather than trusting it.
REVIEW_KEYS = ["matched_id", "platform", "restaurant_name", "dish_name_raw",
               "list_price"]


def apply_format_review(d: pd.DataFrame, path=None) -> pd.DataFrame:
    """Drop listings a human graded as the wrong product format.

    Token rules see ingredients and are blind to format. Half portions, mini
    bowls, snack-sized versions, bulk boxes and two-dish combos all pass every
    automated check. The verdicts live in ``data/manual/format_review.csv`` so
    they are auditable and a second coder can disagree with them in writing.

    Missing file means the review has not been run, which is not the same as
    everything passing, so this raises rather than defaulting to keep.
    """
    path = path or config.FORMAT_REVIEW
    if not Path(path).exists():
        raise FileNotFoundError(
            f"No format review at {path}. Run src/format_review.py, grade the "
            f"rows, then rebuild. An ungraded row is not a passing row."
        )
    r = pd.read_csv(path).rename(columns={"restaurant": "restaurant_name",
                                          "listing": "dish_name_raw",
                                          "listing_price": "list_price"})
    if r["verdict"].isna().any() or (r["verdict"] == "").any():
        raise ValueError("Ungraded rows in the format review. Blank is not keep.")

    n0 = len(d)
    merged = d.merge(r[REVIEW_KEYS + ["verdict", "reason"]], on=REVIEW_KEYS,
                     how="left", validate="one_to_one")
    if len(merged) != n0:
        raise ValueError(f"Review merge changed the row count, {n0} to {len(merged)}")
    if merged["verdict"].isna().any():
        missing = merged.loc[merged["verdict"].isna(), "dish_name_raw"].tolist()
        raise ValueError(f"{len(missing)} listings are not in the review: {missing[:5]}")
    return merged


def matched_rows(raw_path=None, bistro_path=None, apply_manual: bool = True):
    """Rows that survive the search-term and token rules, with the audit flow.

    Split out of :func:`build` so the format review reads exactly the rows the
    panel is built from. A review that runs on a different filter than the build
    is not a review of anything.

    Set ``apply_manual`` False to see the rows :data:`MANUAL_CORE_REJECT` would
    remove, so a second coder can check those calls too rather than inheriting
    them.
    """
    raw_path = raw_path or config.MARKETPLACE_RAW

    a = pd.read_csv(raw_path)
    a["notes"] = a["notes"].fillna("")
    a["dish_description"] = a["dish_description"].fillna("")
    d = a[a["screen_type"] == "dish_listing"].copy()

    flow = [("dish rows transcribed", len(d), "")]

    def step(mask, label, why=""):
        nonlocal d
        d = d[mask].copy()
        flow.append((label, len(d), why))

    step(d["list_price"].notna(), "price readable", "unreadable price")
    step(d["restaurant_name"].notna(), "restaurant identifiable", "header off-screen")
    step(~d["notes"].str.contains("partial", case=False),
         "card fully in frame", "clipped by the scroll edge")
    step(~d["notes"].str.lower().str.contains(NON_MATCHING_SECTIONS),
         "under the matching section", "listed under Recommended/Most ordered")
    step(~d["search_term_typed"].map(lambda t: mm.is_ambiguous(t) is not None),
         "search not a collapsed query", "Tea/Chai/Chaat each cover 3 Bistro dishes")
    d["matched_id"] = d["search_term_typed"].map(mm.search_to_id)
    step(d["matched_id"].notna(), "search term maps to a Bistro dish", "unmapped or blank")
    d["matched_id"] = d["matched_id"].astype(int)

    d["core_ok"] = [mm.core_ok(m, n, x) for m, n, x
                    in zip(d.matched_id, d.dish_name_raw, d.dish_description)]
    d["form_ok"] = [mm.form_ok(n, q) for n, q
                    in zip(d.dish_name_raw, d.quantity_text.fillna(""))]
    d["comp_ok"] = [mm.comp_ok(n, x) for n, x
                    in zip(d.dish_name_raw, d.dish_description)]
    d["manual_reject"] = d["matched_id"].isin(MANUAL_CORE_REJECT)
    if apply_manual:
        d.loc[d["manual_reject"], "core_ok"] = False
    step(d["core_ok"] & d["form_ok"], "passes CORE and FORM veto",
         "wrong dish, or a bulk/box/combo listing")
    return d, flow


def build(raw_path=None, bistro_path=None, verbose: bool = True):
    bistro_path = bistro_path or config.BISTRO_MENU
    # apply_manual False, because the format review file is now the verdict of
    # record and it already carries those rows graded as rejects.
    d, flow = matched_rows(raw_path, bistro_path, apply_manual=False)

    def step(mask, label, why=""):
        nonlocal d
        d = d[mask].copy()
        flow.append((label, len(d), why))

    d = apply_format_review(d)
    step(d["verdict"] == "keep", "passes the manual format review",
         "wrong product format: half, mini, bulk or a two-dish combo")

    b = pd.read_csv(bistro_path).set_index("matched_id")

    # Basis is resolved per dish from BOTH sides, never from Bistro alone.
    basis = {
        mid: menu.resolve_basis(
            b.loc[mid, "serves_or_pieces"],
            list(g.quantity_text.fillna("") + " " + g.dish_name_raw),
        )
        for mid, g in d.groupby("matched_id")
    }
    d["basis"] = d["matched_id"].map(basis)

    def stated_pieces(r):
        for t in (r.dish_name_raw, r.quantity_text, r.dish_description):
            try:
                v, u = menu.parse_quantity(t)
            except ValueError:
                continue
            if v is not None and u == "piece":
                return v
        return np.nan

    d["stated_pieces"] = d.apply(stated_pieces, axis=1)
    d = menu.flag_unstandardised_servings(d)

    res = [menu.resolve_quantity(n, x, bs) for n, x, bs
           in zip(d.dish_name_raw, d.quantity_text.fillna(""), d.basis)]
    d["units"], d["qty_unit"], d["qty_source"] = zip(*res)
    step(d["units"].notna(), "quantity resolvable",
         "volume basis with no stated volume, never defaulted to 1 ml")

    d["qty_ok"] = d["qty_source"].isin(("name", "description"))
    d = menu.grade_matches(d)
    d = menu.normalise_prices(d)
    # Section travels from the Bistro side. A marketplace listing has no section
    # of its own, and the dish is what carries the category in this design.
    d["section"] = d["matched_id"].map(b["section"])

    bis = b.loc[sorted(d["matched_id"].unique())].reset_index()
    bis["basis"] = bis["matched_id"].map(basis)
    bis["units"] = [menu.resolve_quantity(q, "", bs)[0] or 1.0
                    for q, bs in zip(bis.serves_or_pieces, bis.basis)]
    bis["platform"] = "Bistro"
    bis["dish_name_raw"] = bis["bistro_item_name"]
    bis["restaurant_name"] = "Bistro"
    bis["qty_source"] = "name"
    bis["match_grade"] = "A_exact"
    bis["is_sponsored"] = False
    bis["stated_pieces"] = np.nan
    bis["serving_unreliable"] = bis["matched_id"].map(
        d.groupby("matched_id")["serving_unreliable"].max()).fillna(False)
    bis = menu.normalise_prices(bis)

    keep = ["platform", "matched_id", "section", "basis", "restaurant_name",
            "dish_name_raw", "list_price", "units", "stated_pieces", "qty_source",
            "unit_price", "effective_price", "match_grade", "is_sponsored",
            "serving_unreliable"]
    long = menu.add_cell_weights(pd.concat([bis[keep], d[keep]], ignore_index=True))

    config.ensure_dirs()
    long.to_csv(config.MENU_PRICES_LONG, index=False)
    pd.DataFrame(flow, columns=["stage", "rows_remaining", "reason_dropped"]).to_csv(
        config.PROCESSED / "menu_exclusion_flow.csv", index=False)

    if verbose:
        prev = None
        print("EXCLUSION FLOW")
        for lbl, n, why in flow:
            drop = f"  (-{prev - n:>3})" if prev is not None else "        "
            print(f"  {n:>4}{drop}  {lbl}" + (f"   [{why}]" if why else ""))
            prev = n
        print(f"\npanel: {len(long)} rows, {long.matched_id.nunique()} dishes")
        print("  by platform:", long.platform.value_counts().to_dict())
        print("  basis:", pd.Series(basis).value_counts().to_dict())
        print("  grade:", long.match_grade.value_counts().to_dict())
        print("  qty source:", long.qty_source.value_counts().to_dict())
        n_unrel = long.loc[long.serving_unreliable == True, "matched_id"].nunique()
        print(f"  flagged serving-not-standardised: {n_unrel} dish(es), "
              f"excluded from the per-unit spec")
    return long


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    build()
