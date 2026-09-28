"""Paths and constants. Everything anchors to repo root so notebooks and
scripts resolve identically regardless of working directory."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
RAW = DATA / "raw"
LETTERS = RAW / "shareholder_letters"
TRANSCRIPTS = RAW / "transcripts"
SWIGGY_RAW = RAW / "swiggy"
PROCESSED = DATA / "processed"
MANUAL = DATA / "manual"

OUTPUT = ROOT / "output"
CHARTS = OUTPUT / "charts"
TABLES = OUTPUT / "tables"

PANEL = PROCESSED / "eternal_quarterly.csv"
SWIGGY_PANEL = PROCESSED / "swiggy_quarterly.csv"
REVIEW_QUEUE = PROCESSED / "review_queue.csv"

BISTRO_TIMELINE = MANUAL / "bistro_timeline.csv"
EVENTS = MANUAL / "events_timeline.csv"
CM_BISTRO_COMPONENTS = MANUAL / "cm_bistro_components.csv"

# --- menu price study (H3) --------------------------------------------------
# The Bistro menu, hand transcribed from the app. matched_id is the join key
# that links one dish across all three platforms, and it is what carries the
# item fixed effect. Get it wrong and the main specification has nothing to
# hold constant.
BISTRO_MENU = MANUAL / "bistro_menu_delhi.csv"
MARKETPLACE_RAW = MANUAL / "marketplace_prices_raw.csv"
ZOMATO_PRICES = MANUAL / "zomato_prices_delhi.csv"
SWIGGY_PRICES = MANUAL / "swiggy_prices_delhi.csv"
CHECKOUT_FEES = MANUAL / "checkout_fees_delhi.csv"

# Human verdicts on product format, which token rules cannot see. Half
# portions, mini bowls, bulk boxes and two-dish combos all pass every
# automated check, so this file is a required input and not an optional one.
FORMAT_REVIEW = MANUAL / "format_review.csv"
INTERCODER_SAMPLE = MANUAL / "intercoder_sample.csv"

MENU_PRICES_LONG = PROCESSED / "menu_prices_long.csv"
PRICE_REVIEW_QUEUE = PROCESSED / "price_review_queue.csv"

# A quote this far above or below the dish median is queued for review, never
# dropped silently. The same dish ran Rs 289 to Rs 799 across six Zomato
# restaurants, so wide dispersion is real and is itself a finding.
PRICE_OUTLIER_MULTIPLE = 2.5

# Fewer usable quotes than this on a platform and the dish cannot support the
# median of five rule the methodology commits to.
MIN_QUOTES_PER_DISH = 3

# Superseded by BISTRO_MENU and the per platform price files above. Kept only
# so older notebooks do not break on import.
MENU_SAMPLE = MANUAL / "menu_price_sample.csv"

# --- the switching value model ---------------------------------------------
# Alpha is the share of Bistro orders that would otherwise have been Zomato
# food delivery orders. Run the pessimistic case to 95%: a result that survives
# near total cannibalisation is a much stronger claim than one that holds only
# at the baseline.
ALPHA_GRID = [0.20, 0.40, 0.60, 0.80, 0.95]

# Set this from the H3 price overlap work in 02_price_positioning, and defend
# it on the slide. Leaving it None is deliberate. A baseline picked before the
# evidence is a guess wearing a decimal point.
ALPHA_BASELINE = None

# Retention is the share of cannibalised orders Eternal would actually have
# kept, given Swiggy Bolt, Snacc and Zepto Cafe. 1.00 is the conservative case
# where every cannibalised order would have stayed on Zomato, and it gives the
# lowest threshold the evidence supports. Narrow the rest from H2.
RETENTION_GRID = [1.00, 0.75, 0.50]

# Share of food delivery revenue treated as fixed and added back to adjusted
# EBITDA to reach a contribution margin. Adjusted EBITDA per order is a floor,
# not a contribution margin. Set this from the segment P&L and record the
# reasoning in ASSUMPTIONS.md. Erring high is the conservative choice: it
# raises CM_zomato, lowers alpha*, and weakens the case for Bistro.
FD_FIXED_COST_ADDBACK = None

# Bistro entered the market during FY26. Quarters before this are the
# pre-treatment window for any before/after comparison.
BISTRO_START_QUARTER = "Q3FY25"

# Blinkit's shift to an inventory-led model broke revenue comparability.
# Confirm the exact quarter from the shareholder letters and update this.
# Any growth series spanning this break must use NOV, not revenue.
INVENTORY_MODEL_BREAK = "Q2FY26"  # quick commerce revenue jumps 2,400 -> 9,891 cr

# Plausible QoQ change per field. Anything outside is queued for review
# rather than silently accepted. Widen deliberately, never to silence a warning.
VALIDATION_BANDS = {
    "fd_nov": (-0.40, 0.60),
    "fd_adj_revenue": (-0.40, 0.60),
    "fd_contribution": (-0.40, 0.60),
    "fd_mtu": (-0.25, 0.40),
    "qc_nov": (-0.30, 1.00),
    "qc_contribution": (-0.40, 1.00),
    "qc_mtu": (-0.25, 0.60),
    "qc_naov": (-0.25, 0.35),
    "qc_stores": (-0.10, 0.60),
    "others_adj_ebitda": (-3.00, 3.00),  # small base, swings hard
    "consol_adj_revenue": (-0.40, 1.20),  # wide: spans the 1P accounting break
}


def ensure_dirs() -> None:
    for p in (PROCESSED, MANUAL, CHARTS, TABLES):
        p.mkdir(parents=True, exist_ok=True)
