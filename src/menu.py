"""Menu price preprocessing for the H3 price positioning study.

The study asks whether Bistro, an owned kitchen, posts lower prices than
restaurant marketplaces for the same dish. The estimator is item fixed effects,
so the coefficient comes from variation *within* a dish across platforms.

The one thing that can invert the answer
========================================

Platforms sell the same dish in different quantities. Bistro sells chai in four
cup packs and samosas in twos. A marketplace sells one cup and one samosa. So::

    log(price / units) = log(price) - log(units)

``log(units)`` varies within a dish across platforms, which means the dish fixed
effect does **not** absorb it. Therefore::

    beta_normalised = beta_raw - delta,  where
    delta = E[log units | Bistro] - E[log units | marketplace]   (within dish)

For Aloo Pyaaz Paratha, Bistro sells 2 pieces and Haldiram's sells 1, so
``delta = log(2) = 0.69`` log points. That is larger than any plausible true
effect. **Delta is a parameter this module estimates by assumption**, so it is
reported as a number with its own uncertainty rather than buried in a pipeline.
``delta_by_section`` exists for exactly that.

Normalisation does not uniformly help the hypothesis. Parathas favour it.
Desserts cut against it: Swiggy lists Angoori Jamun at 4 pieces for Rs 35,
which is Rs 8.75 each against Bistro's Rs 49 Gulab Jamun. Both directions must
survive into the write up.

Conventions
===========

* Quantity that cannot be read stays ``None``. It is never coerced to 1 in a
  way the caller cannot see, and ``qty_source`` always records where the number
  came from.
* Photo inferred quantity is admitted as a sensitivity only. In this dataset
  Kaleva's Aloo Samosa photo shows two samosas while the description says
  "(1 Pc)", so the picture overstates.
* Everything above the IO section is pure.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

# --- vocabularies -----------------------------------------------------------

#: Comparison bases, most granular first. The basis for a dish is the most
#: granular one on which *both* sides state a quantity. Serving is the
#: universal fallback, so the denominator is never undefined.
BASIS_PREFERENCE = ("piece", "ml", "serving")

#: Where a quantity came from, best first. First hit wins, no exceptions.
#: ``name`` is the only field present on every platform: Swiggy dish cards
#: carry no description at all, and Zomato truncates its description at three
#: lines, so a description-first rule would fail on most rows.
QTY_SOURCES = ("name", "description", "basis_default", "photo", "assumed")

#: Sources admissible in the primary specification. ``photo`` is deliberately
#: absent, see the module docstring.
QTY_SOURCES_PRIMARY = ("name", "description", "basis_default")

#: Grades from the decision tree in ``grade_matches``.
GRADES = ("A_exact", "B_close", "C_loose", "D_reject")

#: Grades that enter the main sample.
GRADES_MAIN = ("A_exact", "B_close")

PLATFORMS = ("Bistro", "Zomato", "Swiggy")

#: A listing with no stated count whose price exceeds this multiple of the
#: within dish median of count-stated unit prices is treated as a bulk or box
#: listing, not a single serving. Zomato's Bikaner Sweets lists White Rasgulla
#: at Rs 300 with no count against Bistro's Rs 49 for one piece.
BULK_SUSPECT_MULTIPLE = 3.0

# Portion words with a defined ratio. "Half" is quantity, not composition, so
# it is normalised rather than excluded.
_PORTION_WORDS = {"quarter": 0.25, "half": 0.5, "full": 1.0}

# Ordered so the most specific pattern wins. Each yields (value, unit).
_QTY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"[\(\[]\s*(\d+(?:\.\d+)?)\s*(?:pc|pcs|piece|pieces|nos|no)\b[^\)\]]*[\)\]]", re.I), "piece"),
    (re.compile(r"[-–]\s*(\d+(?:\.\d+)?)\s*(?:pc|pcs|piece|pieces|nos)\b", re.I), "piece"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:pc|pcs|piece|pieces|nos)\b", re.I), "piece"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:cup|cups|glass|glasses)\b", re.I), "piece"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*ml\b", re.I), "ml"),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:l|ltr|litre|liter)\b", re.I), "ml_litre"),
    (re.compile(r"\bserves?\s*(\d+(?:\.\d+)?)\b", re.I), "serving"),
]

_RANGE_SERVES = re.compile(r"\bserves?\s*\d+\s*[-–]\s*\d+", re.I)


def parse_quantity(text: str | None) -> tuple[float | None, str | None]:
    """Pull a quantity out of a dish name, description or Bistro qty string.

    Returns ``(value, unit)`` where unit is one of ``piece``, ``ml`` or
    ``serving``. Returns ``(None, None)`` when nothing is stated, which is the
    signal for the caller to fall back down the ``QTY_SOURCES`` chain.

    Cups and glasses map to ``piece`` rather than ``ml`` on purpose.
    Marketplaces sell chai by the cup, so per cup is directly comparable and
    avoids inventing a millilitres-per-cup constant.

    A "Serves 3-4" range is refused rather than guessed at. Those are party
    packs with no marketplace analogue.
    """
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return None, None
    s = str(text).strip()
    if not s:
        return None, None

    if _RANGE_SERVES.search(s):
        raise ValueError(
            f"Ambiguous serving range in {s!r}. Party packs have no marketplace "
            "analogue and are excluded rather than guessed at."
        )

    for pattern, unit in _QTY_PATTERNS:
        m = pattern.search(s)
        if m:
            value = float(m.group(1))
            if value <= 0:
                raise ValueError(f"Non-positive quantity parsed from {s!r}.")
            if unit == "ml_litre":
                return value * 1000.0, "ml"
            return value, unit

    for word, ratio in _PORTION_WORDS.items():
        if re.search(rf"\b{word}\b", s, re.I):
            return ratio, "serving"

    return None, None


def assign_basis(bistro_qty_text: str | None) -> str:
    """The comparison basis for a dish, fixed from the Bistro side.

    Bistro states a quantity on every item, so the basis is always assignable
    from a source that is complete. That makes the choice deterministic rather
    than a coder judgement.

    The basis need not be comparable across dishes. The dish fixed effect
    absorbs that. Only within dish comparability matters.
    """
    value, unit = parse_quantity(bistro_qty_text)
    if unit in ("piece", "ml"):
        return unit
    return "serving"


def resolve_quantity(
    name: str | None,
    description: str | None = None,
    basis: str = "serving",
    photo_qty: float | None = None,
) -> tuple[float | None, str, str]:
    """Walk the precedence chain and return ``(units, unit, source)``.

    Order is name, then description, then a basis default, then photo, then a
    flat assumption of one. ``source`` records which rung was used so the
    robustness sample can be rebuilt by filtering on it.

    Defaulting to one rather than deleting is deliberate for countable and
    serving bases. Listings that state a count are systematically the small
    ones, so dropping the silent ones is the non random choice.

    **The volume basis gets no such default.** A drink with no stated volume is
    unknown, not one millilitre. Assuming 1 would price a can at rupees per
    millilitre against Bistro's 330 ml and produce a 440x error. Those rows
    return ``None`` so the caller must decide, and ``resolve_basis`` normally
    downgrades the whole dish to a serving comparison instead.
    """
    for field, source in ((name, "name"), (description, "description")):
        value, unit = parse_quantity(field)
        if value is not None and unit == basis:
            return value, unit, source
        if value is not None and basis == "serving" and unit == "piece":
            # A piece count on a serving-basis dish still describes one order.
            return 1.0, "serving", "basis_default"

    if photo_qty is not None:
        return float(photo_qty), basis, "photo"

    if basis == "ml":
        return None, "ml", "unknown"

    return 1.0, basis, "assumed"


def resolve_basis(bistro_qty_text: str | None,
                  marketplace_qty_texts: list[str | None],
                  min_stated: int = 3) -> str:
    """Pick the comparison basis for a dish using BOTH sides, not Bistro alone.

    The basis is the most granular unit on which enough of the marketplace side
    also states a quantity. Where it does not, the basis falls back to the
    serving, which compares one listing against one listing.

    Diet Coke is the case that forces this. Bistro states 330 ml. Not one of the
    marketplace listings states a volume, so a millilitre basis is unusable and
    the honest comparison is one can against one can: 50 against 66. Lemon Iced
    Tea keeps the millilitre basis because three marketplace listings do state
    a volume, which clears ``min_stated``.
    """
    preferred = assign_basis(bistro_qty_text)
    if preferred == "serving":
        return "serving"
    stated = 0
    for t in marketplace_qty_texts:
        try:
            value, unit = parse_quantity(t)
        except ValueError:
            continue
        if value is not None and unit == preferred:
            stated += 1
    return preferred if stated >= min_stated else "serving"


# --- price construction -----------------------------------------------------

def normalise_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``unit_price``, ``effective_price``, ``discount_pct``, ``log_*``.

    ``effective_price`` uses the item level strikethrough where one exists and
    the list price otherwise. Order level offers such as "Flat Rs 140 OFF above
    Rs 199" and restaurant level caps such as "70% off upto Rs 140" are
    deliberately ignored: attributing them to a single item needs a basket
    assumption, and inventing one would be fabrication.
    """
    required = {"list_price", "units"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"Cannot normalise, frame missing columns: {missing}")

    out = df.copy()
    if (out["units"] <= 0).any():
        bad = out.loc[out["units"] <= 0].index.tolist()
        raise ValueError(f"Non-positive units at rows {bad}. Fix the transcription.")

    strike = out.get("strikethrough_price", pd.Series(np.nan, index=out.index))
    out["effective_price"] = np.where(strike.notna(), strike, out["list_price"])
    # A strikethrough is the pre-discount reference, so the lower of the two is
    # what a customer pays.
    out["effective_price"] = np.minimum(out["list_price"], out["effective_price"])
    out["discount_pct"] = np.where(
        strike.notna(), 1.0 - out["effective_price"] / strike, 0.0
    )

    out["unit_price"] = out["list_price"] / out["units"]
    out["unit_effective_price"] = out["effective_price"] / out["units"]
    for col in ("list_price", "unit_price", "effective_price", "unit_effective_price"):
        out[f"log_{col}"] = np.log(out[col])
    return out


def add_cell_weights(df: pd.DataFrame) -> pd.DataFrame:
    """Weight each row by one over the count in its dish and platform cell.

    Without this a dish with six Zomato quotes and one Bistro price gives
    Bistro one twelfth of the within dish weight, and the estimate becomes a
    function of how many screenshots happened to be taken. With it, each
    platform cell inside a dish carries weight one and beta is a clean average
    of within dish platform gaps.
    """
    required = {"matched_id", "platform"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"Cannot weight, frame missing columns: {missing}")
    out = df.copy()
    n = out.groupby(["matched_id", "platform"])["platform"].transform("size")
    out["cell_weight"] = 1.0 / n
    return out


def impute_quantity(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing quantities from other listings, in two clearly-graded tiers.

    **Tier 1, same restaurant, same dish, other platform. High confidence.**
    Chaayos lists Lemon Iced Tea at Rs 209 on both platforms; the Zomato card
    says 300 ml and the Swiggy card says nothing. That is not inference, it is
    the same product read twice, so the volume carries across.

    **Tier 2, the median stated quantity within the dish. Low confidence.**
    Serving sizes for a given drink cluster tightly, 250 to 300 ml across every
    listing here, so the dish median is a reasonable stand-in. It is still an
    assumption and it is marked ``imputed_dish_median`` so the primary
    specification can exclude it and a sensitivity can include it.

    **What this never does is infer quantity from price.** That would be
    circular: price would set the quantity, and the quantity would then set the
    normalised price. The data also says it would not work. Chaayos charges
    Rs 209 for 300 ml and Theobroma Rs 99 for the same 300 ml, so price per
    millilitre varies by more than two to one at identical volume.
    """
    required = {"matched_id", "restaurant_name", "units", "qty_source"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"impute_quantity needs: {missing}")

    out = df.copy()
    stated = out["qty_source"].isin(("name", "description"))

    # Tier 1: the same restaurant stating it elsewhere.
    known = (out[stated].dropna(subset=["units"])
             .groupby(["matched_id", "restaurant_name"])["units"].median())
    for i in out.index[out["units"].isna()]:
        key = (out.at[i, "matched_id"], out.at[i, "restaurant_name"])
        if key in known.index:
            out.at[i, "units"] = float(known.loc[key])
            out.at[i, "qty_source"] = "same_restaurant"

    # Tier 2: the median stated quantity for that dish.
    dish_med = out[stated].dropna(subset=["units"]).groupby("matched_id")["units"].median()
    for i in out.index[out["units"].isna()]:
        mid = out.at[i, "matched_id"]
        if mid in dish_med.index:
            out.at[i, "units"] = float(dish_med.loc[mid])
            out.at[i, "qty_source"] = "imputed_dish_median"
    return out


def flag_unstandardised_servings(df: pd.DataFrame, max_spread: float = 2.0) -> pd.DataFrame:
    """Flag serving-basis dishes whose marketplace 'servings' are not one size.

    Bistro states ``Serves 1`` for Idli Sambar without a piece count. The
    marketplace listings state 2, 3, 4 and 12 pieces, which works out at
    Rs 14.58 to Rs 78.57 each, a 5.4x spread. Treating all of those as one
    serving and comparing them to Bistro is not a like for like comparison, and
    Bistro's own piece count is unknown so the dish cannot be normalised either.

    Such a dish is **not identified** on a per unit basis. It stays in the raw
    price specification with the flag reported, and leaves the per unit one.

    Requires a ``stated_pieces`` column holding any piece count read off the
    listing, even where the dish sits on the serving basis. Discarding that
    count is what hid the problem in the first place.
    """
    required = {"matched_id", "basis", "stated_pieces"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"flag_unstandardised_servings needs: {missing}")

    out = df.copy()
    out["serving_unreliable"] = False
    out["serving_piece_spread"] = np.nan
    for mid, g in out.groupby("matched_id"):
        if (g["basis"] != "serving").any():
            continue
        pc = g["stated_pieces"].dropna()
        pc = pc[pc > 0]
        if len(pc) < 2:
            continue
        spread = pc.max() / pc.min()
        out.loc[g.index, "serving_piece_spread"] = spread
        if spread >= max_spread:
            out.loc[g.index, "serving_unreliable"] = True
    return out


def flag_bulk_suspects(df: pd.DataFrame, multiple: float = BULK_SUSPECT_MULTIPLE) -> pd.DataFrame:
    """Flag count-silent listings priced like a box rather than a serving.

    Applies only on the piece basis. A per piece sweet price is bounded. A one
    kilogram box is not. The rule is numeric and auditable rather than a hand
    pick, and the threshold should be re-run at 2x and 5x for the write up.
    """
    out = df.copy()
    out["bulk_suspect"] = False
    if "basis" not in out.columns or "qty_source" not in out.columns:
        raise KeyError("flag_bulk_suspects needs 'basis' and 'qty_source'.")

    stated = out["qty_source"].isin(("name", "description"))
    for mid, g in out.groupby("matched_id"):
        if (g["basis"] != "piece").all():
            continue
        ref = g.loc[stated.loc[g.index], "unit_price"]
        if ref.empty:
            continue
        threshold = ref.median() * multiple
        silent = g.index[~stated.loc[g.index]]
        out.loc[silent, "bulk_suspect"] = out.loc[silent, "unit_price"] > threshold
    return out


# --- match grading ----------------------------------------------------------

def grade_matches(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the four sub-check decision tree and write ``match_grade``.

    Four binary checks rather than a holistic impression, because component
    checks are auditable and their individual agreement rates localise which
    rule is soft.

    ============  ==========================================================
    ``core_ok``   Same core ingredient and cooking format
    ``form_ok``   Not a bulk, box or party pack listing
    ``qty_ok``    Quantity stated, or the default is unambiguous, on both sides
    ``comp_ok``   No bundled add-on that the restaurant also sells standalone
    ============  ==========================================================

    ``core_ok`` and ``form_ok`` are absolute vetoes, because a different dish
    or a one kilogram box is not a price comparison at all. ``qty_ok`` and
    ``comp_ok`` are gradable because the estimator can correct them, the first
    by normalisation and the second by the bundle control.
    """
    needed = ["core_ok", "form_ok", "qty_ok", "comp_ok"]
    missing = sorted(set(needed) - set(df.columns))
    if missing:
        raise KeyError(f"grade_matches needs the sub-checks: {missing}")

    out = df.copy()
    for c in needed:
        out[c] = out[c].astype("boolean")
    if out[needed].isna().any().any():
        raise ValueError(
            "Ungraded sub-checks present. Every row must be coded before "
            "grading; a blank is not a pass."
        )

    veto = ~out["core_ok"] | ~out["form_ok"]
    soft = out["qty_ok"].astype(bool).astype(int) + out["comp_ok"].astype(bool).astype(int)

    grade = np.where(
        veto, "D_reject",
        np.where(soft == 2, "A_exact", np.where(soft == 1, "B_close", "C_loose")),
    )
    out["match_grade"] = grade
    return out


# --- the delta statistic ----------------------------------------------------

def delta_by_section(df: pd.DataFrame, bistro_platform: str = "Bistro") -> pd.DataFrame:
    """The quantity wedge that normalisation applies, per menu section.

    ``delta = mean(log units | Bistro) - mean(log units | marketplace)``,
    computed within dish then averaged. It is the exact amount by which
    normalisation moves the headline coefficient, so it belongs in the paper as
    a reported statistic with a standard error, not as a pipeline detail.
    """
    required = {"matched_id", "platform", "units", "section"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise KeyError(f"delta_by_section missing columns: {missing}")

    d = df.assign(log_units=np.log(df["units"]))
    per_dish = []
    for (mid, section), g in d.groupby(["matched_id", "section"]):
        b = g.loc[g["platform"] == bistro_platform, "log_units"]
        m = g.loc[g["platform"] != bistro_platform, "log_units"]
        if b.empty or m.empty:
            continue
        per_dish.append({"matched_id": mid, "section": section,
                         "delta": b.mean() - m.mean()})
    if not per_dish:
        return pd.DataFrame(columns=["section", "n_dishes", "delta_mean", "delta_se"])

    pd_df = pd.DataFrame(per_dish)
    agg = pd_df.groupby("section")["delta"].agg(["count", "mean", "std"])
    agg.columns = ["n_dishes", "delta_mean", "delta_sd"]
    agg["delta_se"] = agg["delta_sd"] / np.sqrt(agg["n_dishes"])
    return agg.reset_index().drop(columns="delta_sd")


def bistro_percentile_rank(df: pd.DataFrame, price_col: str = "unit_price",
                           bistro_platform: str = "Bistro") -> pd.DataFrame:
    """Where Bistro's price sits inside each dish's marketplace distribution.

    This is the insurance policy for the whole study. It is nonparametric,
    model free, and largely immune to the normalisation choice, so it survives
    even if the log-linear specification turns out fragile. Under the null the
    mean rank is 0.5, and a sign or Wilcoxon test on the 32 dish level ranks is
    the robustness result to quote beside the coefficient.
    """
    rows = []
    for mid, g in df.groupby("matched_id"):
        b = g.loc[g["platform"] == bistro_platform, price_col]
        m = g.loc[g["platform"] != bistro_platform, price_col].dropna()
        if b.empty or len(m) == 0:
            continue
        bp = float(b.iloc[0])
        rows.append({
            "matched_id": mid,
            "bistro_price": bp,
            "n_marketplace": len(m),
            "mkt_median": m.median(),
            "mkt_min": m.min(),
            "mkt_max": m.max(),
            "mkt_cv": m.std() / m.mean() if m.mean() else np.nan,
            "bistro_rank": float((m < bp).mean()),
        })
    return pd.DataFrame(rows)


# --- coverage and validation ------------------------------------------------

CORE_FIELDS = [
    "matched_id", "platform", "restaurant_name", "dish_name_raw",
    "list_price", "units", "qty_source", "basis", "match_grade",
]


def coverage_report(df: pd.DataFrame) -> pd.DataFrame:
    """Which fields are populated, in the shape ``panel.coverage_report`` uses."""
    rows = []
    for f in CORE_FIELDS:
        if f not in df.columns:
            rows.append({"field": f, "present": 0, "missing": len(df),
                         "coverage": 0.0, "status": "COLUMN ABSENT"})
            continue
        present = int(df[f].notna().sum())
        rows.append({
            "field": f, "present": present, "missing": len(df) - present,
            "coverage": round(present / len(df), 2) if len(df) else 0.0,
            "status": "ok" if present == len(df) else "GAPS",
        })
    return pd.DataFrame(rows).sort_values("coverage")


def validate_prices(df: pd.DataFrame, path: Path | None = None,
                    outlier_multiple: float | None = None,
                    min_quotes: int | None = None,
                    write: bool = True) -> pd.DataFrame:
    """Queue anything questionable for written sign off. Never drop silently.

    Mirrors ``panel.validate``: breaches are written to a review queue rather
    than raised, and a sign off already recorded is carried forward so that a
    re-run cannot quietly reopen a breach somebody already explained.
    """
    from . import config

    path = path or config.PRICE_REVIEW_QUEUE
    outlier_multiple = outlier_multiple or config.PRICE_OUTLIER_MULTIPLE
    min_quotes = min_quotes or config.MIN_QUOTES_PER_DISH

    breaches: list[dict] = []

    def add(row_id, mid, platform, kind, detail):
        breaches.append({"row_id": row_id, "matched_id": mid, "platform": platform,
                         "issue": kind, "detail": detail,
                         "reviewed": False, "explanation": ""})

    for mid, g in df.groupby("matched_id"):
        med = g["unit_price"].median()
        if med and np.isfinite(med):
            for i, r in g.iterrows():
                if r["unit_price"] > med * outlier_multiple or r["unit_price"] < med / outlier_multiple:
                    add(i, mid, r["platform"], "price_outlier",
                        f"unit_price {r['unit_price']:.2f} vs dish median {med:.2f}")
        for platform, gp in g.groupby("platform"):
            if platform == "Bistro":
                continue
            usable = gp[gp["match_grade"].isin(GRADES_MAIN)] if "match_grade" in gp else gp
            if len(usable) < min_quotes:
                add("", mid, platform, "thin_cell",
                    f"{len(usable)} usable quotes, minimum is {min_quotes}")

    for i, r in df.iterrows():
        if r.get("qty_source") in ("photo", "assumed"):
            add(i, r["matched_id"], r["platform"], "quantity_not_stated",
                f"qty_source={r['qty_source']}, units={r['units']}")
        if r.get("match_grade") == "D_reject":
            add(i, r["matched_id"], r["platform"], "grade_reject",
                str(r.get("exclude_reason", "")))
        if bool(r.get("is_sponsored", False)):
            add(i, r["matched_id"], r["platform"], "sponsored", "Ad badge on listing")
        if bool(r.get("bulk_suspect", False)):
            add(i, r["matched_id"], r["platform"], "bulk_suspect",
                f"count silent at unit_price {r['unit_price']:.2f}")

    result = pd.DataFrame(breaches)
    if len(result) and Path(path).exists():
        prior = pd.read_csv(path)
        keys = ["matched_id", "platform", "issue"]
        if set(keys + ["reviewed", "explanation"]).issubset(prior.columns):
            keep = prior[keys + ["reviewed", "explanation"]].drop_duplicates(keys)
            result = (result.drop(columns=["reviewed", "explanation"])
                            .merge(keep, on=keys, how="left"))
            result["reviewed"] = result["reviewed"].fillna(False).astype(bool)
            result["explanation"] = result["explanation"].fillna("")

    if write:
        from . import config as _c
        _c.ensure_dirs()
        result.to_csv(path, index=False)
    return result


def assert_reviewed(path: Path | None = None) -> None:
    """Guard for the analysis notebook. Refuses to run on unexplained breaches."""
    from . import config
    path = path or config.PRICE_REVIEW_QUEUE
    if not Path(path).exists():
        raise FileNotFoundError("Run menu.validate_prices() before analysis.")
    q = pd.read_csv(path)
    if q.empty:
        return
    unreviewed = q[~q["reviewed"].astype(bool)]
    if len(unreviewed):
        counts = unreviewed["issue"].value_counts().to_dict()
        raise AssertionError(
            f"{len(unreviewed)} unreviewed price breach(es) in {Path(path).name}: "
            f"{counts}. Inspect each, set reviewed=True and record the reason in "
            "ASSUMPTIONS.md before running analysis."
        )


# ---------------------------------------------------------------------------
# IO. The only part of this module that touches disk.
# ---------------------------------------------------------------------------

REQUIRED_PRICE_COLUMNS = [
    "matched_id", "platform", "dish_name_raw", "list_price",
]


def load_menu_prices(path: Path) -> pd.DataFrame:
    """Read a transcribed price file and enforce the schema."""
    df = pd.read_csv(path)
    missing = sorted(set(REQUIRED_PRICE_COLUMNS) - set(df.columns))
    if missing:
        raise KeyError(f"{Path(path).name} missing required columns: {missing}")
    bad = df.loc[df["platform"].notna() & ~df["platform"].isin(PLATFORMS), "platform"]
    if len(bad):
        raise ValueError(
            f"{Path(path).name} has unknown platform(s): {sorted(set(bad))}. "
            f"Expected one of {PLATFORMS}."
        )
    return df
