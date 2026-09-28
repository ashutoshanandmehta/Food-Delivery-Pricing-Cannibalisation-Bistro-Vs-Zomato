"""Search term and dish name mapping from marketplace listings to Bistro dishes.

Two stages, because one is not enough.

**Stage one, the search term.** Every screenshot carries the term that was typed
or the "Best in <dish>" header, which links the screen to a Bistro ``matched_id``.

**Stage two, the dish name.** A search does not return only the dish searched.
"Best in Gulab Jamun" returned Kala Jamun and a samosa combo. "Kesar Rasmalai"
returned a Samosa Plate. So each dish carries required tokens the listing name
must contain, and reject tokens that disqualify it.

The rules live here as data rather than as judgement calls so a second coder can
apply them identically and so the rejections can be counted and reported, which
is what the paper's exclusion criteria section needs.
"""

from __future__ import annotations

import re

# --- stage one: what was typed, normalised, to a Bistro matched_id -----------

SEARCH_TO_ID: dict[str, int] = {
    # Zomato
    "chicken dum biryani": 1, "chicken keema and paratha lunchbox": 2,
    "chicken keema and paratha": 2, "paneer makhani biryani": 3,
    "chicken keema pav": 4, "rajma rice bowl": 5, "chole kulche": 7,
    "dal tadka and rice": 8, "crispy fried chicken": 10,
    "crispy chicken popcorn": 14, "veg spring rolls": 16, "veg sring rolls": 16,
    "mix veg pakoda": 17, "peri peri fries": 19, "masala dosa": 22,
    "cheese maggi": 25, "vada pav": 26, "boiled egg": 28, "cheese popcorn": 29,
    "aloo samosa": 32, "sandwich": 42, "mumbai veg grilled sandwich": 42,
    "chicken burger": 44, "veg burger": 45, "malai ghewar": 46,
    "kesar rasmalai": 52, "moong dal halwa": 53, "gulab jamun": 55,
    "sponge rasgulla": 57, "aloo pyaaj paratha": 59, "idli sambar": 60,
    "poha": 62, "samosa chaat": 68, "lemon ice tea": 71, "diet coke": 75,
    # Swiggy variants
    "veg spring roll": 16, "rajma rice": 5, "mix veg pakora": 17,
    "cheese vada pav": 26, "ombay veg grilled sandwich": 42,
    "bombay veg grilled sandwich": 42, "og veg burger": 45,
    "og chicken burger": 44, "aloo pyaaz paratha": 59, "vegetable poha": 62,
    "lemon iced tea": 71,
}

#: Searches that collapse several distinct Bistro products into one query and
#: therefore cannot be assigned a single matched_id. Bistro sells Masala Chai,
#: Desi Chai and Adrak Chai separately; the collector typed "Tea" once. Same for
#: the three chaats. These rows are excluded rather than arbitrarily assigned.
AMBIGUOUS_SEARCHES: dict[str, tuple[int, ...]] = {
    "tea": (65, 66, 67),
    "chai": (65, 66, 67),
    "chaat": (68, 69, 70),
}

# --- stage two: does the listing name actually name the dish? ----------------
# Each entry: every group must match at least one of its alternatives.
REQUIRE: dict[int, list[list[str]]] = {
    1:  [["chicken", "murgh"], ["biryani"]],
    2:  [["keema", "kheema"], ["paratha", "parantha", "paranthe"]],
    3:  [["paneer"], ["biryani"]],
    4:  [["keema", "kheema"], ["pav", "pao"]],
    5:  [["rajma"]],
    7:  [["chole", "choley", "cholay", "chana"], ["kulch"]],
    8:  [["dal", "daal"], ["rice", "chawal", "tadka"]],
    10: [["chicken"], ["fried", "crispy"]],
    14: [["popcorn"], ["chicken"]],
    16: [["spring roll"], ["veg"]],
    17: [["pakora", "pakoda"]],
    19: [["fries", "fry"], ["peri"]],
    22: [["dosa"]],
    25: [["maggi"], ["cheese"]],
    26: [["vada pav", "vada pao", "vadapav", "vada-pav"]],
    28: [["egg"], ["boiled", "uble"]],
    29: [["popcorn"]],
    32: [["samosa"]],
    42: [["sandwich"], ["grill", "toast"]],
    44: [["burger"], ["chicken"]],
    45: [["burger"]],
    46: [["ghewar"]],
    52: [["rasmalai", "ras malai", "rasmalayi"]],
    53: [["halwa"], ["moong", "mung", "dal"]],
    55: [["jamun"]],
    57: [["rasgulla", "rosogulla", "rasogolla"]],
    59: [["paratha", "parantha", "paranthe"], ["aloo"]],
    60: [["idli", "idly"]],
    62: [["poha"]],
    68: [["chaat", "chat"], ["samosa"]],
    71: [["iced tea", "ice tea", "lemon tea", "nimbu"]],
    75: [["coke", "pepsi", "diet"]],
}

#: Tokens that disqualify a listing for a specific dish even if REQUIRE passes.
REJECT: dict[int, list[str]] = {
    16: ["chicken", "prawn", "mutton"],
    29: ["chicken"],
    32: ["chaat", "chat"],
    45: ["chicken", "mutton", "fish", "egg"],
    55: ["kala jamun"],
    75: ["float", "shake", "mojito"],
}

#: Tokens meaning the listing is a bulk pack, box, platter or multi-dish combo
#: rather than a single serving. These fail the FORM check, which is an absolute
#: veto in the grading tree.
FORM_REJECT = [
    "kg", "box", "lunchbox", "mealbox", "party", "platter",
    "pack of", "combo", "thali", "family", "bucket", "hamper", "tray",
    "feast", "meal for", "share pack", "sharing",
]

#: Tokens meaning a separately-sold item is bundled in. These fail the COMP
#: check, which is gradable rather than an absolute veto.
COMP_BUNDLE = [" + ", " with curd", "aur ", " & rice", "with rice", " and rice"]

_WS = re.compile(r"[^a-z0-9/ ]+")


def _has_word(haystack: str, token: str) -> bool:
    """Whole-word containment.

    Substring matching silently drops valid rows: "The OG Veggie Burger" was
    rejected because "v-egg-ie" contains the reject token "egg". Multi-word
    tokens are matched as a phrase on word boundaries.
    """
    return re.search(rf"(?<![a-z0-9]){re.escape(token.strip())}(?![a-z0-9])", haystack) is not None


def norm(text) -> str:
    """Lowercase, strip punctuation, squeeze whitespace."""
    return re.sub(r"\s+", " ", _WS.sub(" ", str(text).lower())).strip()


def search_to_id(term) -> int | None:
    """Map a typed search term to a Bistro matched_id, or None."""
    return SEARCH_TO_ID.get(norm(term))


def is_ambiguous(term) -> tuple[int, ...] | None:
    """Return the Bistro ids a collapsed search covers, or None."""
    return AMBIGUOUS_SEARCHES.get(norm(term))


def core_ok(matched_id: int, dish_name, description="") -> bool:
    """Does the listing actually name this dish?"""
    groups = REQUIRE.get(matched_id)
    if groups is None:
        return False
    hay = norm(dish_name) + " " + norm(description)
    if any(_has_word(hay, tok) for tok in REJECT.get(matched_id, [])):
        return False
    return all(any(_has_word(hay, alt) for alt in group) for group in groups)


def form_ok(dish_name, quantity_text="") -> bool:
    """False for bulk packs, boxes, platters and multi-dish combos."""
    hay = norm(dish_name) + " " + norm(quantity_text)
    return not any(_has_word(hay, tok) for tok in FORM_REJECT)


def comp_ok(dish_name, description="") -> bool:
    """False when a separately-sold item is bundled into the listing."""
    hay = " " + norm(dish_name) + " " + norm(description) + " "
    return not any(tok in hay for tok in COMP_BUNDLE)
