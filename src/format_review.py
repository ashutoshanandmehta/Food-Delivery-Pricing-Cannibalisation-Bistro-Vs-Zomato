"""Build the manual format review sheets.

The token rules in :mod:`src.menu_mapping` decide whether a marketplace listing
names the same dish. They are good at ingredients and blind to **format**. A
listing can pass every token check and still be the wrong product:

* Bistro's Masala Dosa Pops are ten snack bites. The search returned full dosas.
* "Mini Idli" passes the ``idli`` rule and is not the same portion object.
* "Hot Idli (2 Nos) + Medhu Vadai(1)" is a combo the bundle rule let through.

No token rule can see this. It needs eyes. This module writes two sheets:

``data/manual/format_review.csv``
    Every matched row, for the full pass.

``data/manual/intercoder_sample.csv`` and ``output/intercoder_sample.html``
    A seeded random 30 for a second coder, so the agreement rate the methodology
    promises is measured rather than asserted.

Both are written from :func:`build_menu_panel.matched_rows`, so the review runs
on exactly the rows the panel is built from.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

from . import config
from .build_menu_panel import matched_rows

#: Fixed so the sample is reproducible and cannot be reshuffled until it flatters.
SEED = 753

N_INTERCODER = 30

VERDICTS = ("keep", "reject_format", "reject_dish", "unsure")

RULE = (
    "Is this marketplace listing the same product as the Bistro dish, so that "
    "comparing the two prices is meaningful?"
)

GUIDE = [
    ("keep", "Same dish and same format. Portion may differ, that is handled by "
             "normalisation later. Judge the product, not the size."),
    ("reject_format", "Same dish name, different product format. Mini or "
                      "snack-sized against full size, or a combo that bundles a "
                      "second dish the restaurant also sells alone."),
    ("reject_dish", "Not the same dish at all. The token rule matched on a shared "
                    "word."),
    ("unsure", "Cannot tell from the name and description. Use it freely, an "
               "unsure is more useful than a guess."),
]


def review_frame(raw_path=None, bistro_path=None) -> pd.DataFrame:
    """Matched marketplace rows beside the Bistro dish they are matched to."""
    bistro_path = bistro_path or config.BISTRO_MENU
    d, _ = matched_rows(raw_path, bistro_path, apply_manual=False)
    b = pd.read_csv(bistro_path).set_index("matched_id")

    out = pd.DataFrame({
        "row_id": range(1, len(d) + 1),
        "matched_id": d["matched_id"].values,
        "section": d["matched_id"].map(b["section"]).values,
        "bistro_item": d["matched_id"].map(b["bistro_item_name"]).values,
        "bistro_qty": d["matched_id"].map(b["serves_or_pieces"]).values,
        "bistro_price": d["matched_id"].map(b["list_price"]).values,
        "platform": d["platform"].values,
        "restaurant": d["restaurant_name"].values,
        "listing": d["dish_name_raw"].values,
        "listing_desc": d["dish_description"].fillna("").values,
        "listing_qty": d["quantity_text"].fillna("").values,
        "listing_price": d["list_price"].values,
        "already_manually_rejected": d["manual_reject"].values,
        "verdict": "",
        "reason": "",
    })
    return out.sort_values(["matched_id", "platform", "restaurant"]).reset_index(drop=True)


def _html(sample: pd.DataFrame) -> str:
    e = html.escape

    guide = "\n".join(
        f'<tr><td><code>{e(v)}</code></td><td>{e(t)}</td></tr>' for v, t in GUIDE
    )

    cards = []
    for _, r in sample.iterrows():
        desc = f'<div class="desc">{e(str(r.listing_desc))}</div>' if r.listing_desc else ""
        lqty = f' <span class="qty">{e(str(r.listing_qty))}</span>' if r.listing_qty else ""
        cards.append(f"""
    <article class="card">
      <div class="rid">{r.row_id}</div>
      <div class="pair">
        <div class="side bistro">
          <div class="lab">Bistro &middot; {e(str(r.section))}</div>
          <div class="name">{e(str(r.bistro_item))}</div>
          <div class="meta"><span class="qty">{e(str(r.bistro_qty))}</span>
            &middot; &#8377;{r.bistro_price:g}</div>
        </div>
        <div class="side mkt">
          <div class="lab">{e(str(r.platform))} &middot; {e(str(r.restaurant))}</div>
          <div class="name">{e(str(r.listing))}{lqty}</div>
          <div class="meta">&#8377;{r.listing_price:g}</div>
          {desc}
        </div>
      </div>
      <div class="verdicts">{"".join(f'<span class="v">{e(v)}</span>' for v in VERDICTS)}</div>
    </article>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Match review sample, MBA753</title>
<style>
  :root {{
    --ink: #16130f; --mid: #6b6255; --line: #e0d9cd; --bg: #faf7f2;
    --card: #fff; --bistro: #b4530a; --mkt: #2e5c8a;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 2.2rem 1.2rem 4rem; background: var(--bg);
    color: var(--ink); font: 15px/1.55 -apple-system, BlinkMacSystemFont,
    "Segoe UI", Helvetica, Arial, sans-serif; }}
  main {{ max-width: 800px; margin: 0 auto; }}
  h1 {{ font-size: 1.45rem; margin: 0 0 .35rem; letter-spacing: -.01em; }}
  .sub {{ color: var(--mid); margin: 0 0 1.6rem; }}
  .box {{ background: var(--card); border: 1px solid var(--line);
    border-radius: 10px; padding: 1.1rem 1.25rem; margin-bottom: 1.6rem; }}
  .box h2 {{ font-size: .95rem; margin: 0 0 .6rem; text-transform: uppercase;
    letter-spacing: .06em; color: var(--mid); }}
  .rule {{ font-size: 1.05rem; font-weight: 600; margin: 0 0 .9rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td {{ padding: .4rem .5rem .4rem 0; vertical-align: top;
    border-top: 1px solid var(--line); font-size: .92rem; }}
  td:first-child {{ width: 8.5rem; }}
  code {{ background: #f0ece4; padding: .1rem .35rem; border-radius: 4px;
    font-size: .85em; }}
  .card {{ background: var(--card); border: 1px solid var(--line);
    border-radius: 10px; padding: .95rem 1.1rem; margin-bottom: .8rem;
    position: relative; }}
  .rid {{ position: absolute; top: .8rem; right: 1rem; font-size: .8rem;
    font-weight: 700; color: var(--mid); }}
  .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.1rem; }}
  @media (max-width: 620px) {{ .pair {{ grid-template-columns: 1fr; }} }}
  .side {{ padding-left: .7rem; border-left: 3px solid var(--line); }}
  .bistro {{ border-left-color: var(--bistro); }}
  .mkt {{ border-left-color: var(--mkt); }}
  .lab {{ font-size: .74rem; text-transform: uppercase; letter-spacing: .06em;
    color: var(--mid); margin-bottom: .2rem; }}
  .name {{ font-weight: 600; }}
  .meta {{ font-size: .88rem; color: var(--mid); margin-top: .15rem; }}
  .qty {{ background: #f0ece4; padding: .05rem .3rem; border-radius: 4px;
    font-size: .85em; }}
  .desc {{ font-size: .85rem; color: var(--mid); margin-top: .35rem;
    font-style: italic; }}
  .verdicts {{ margin-top: .8rem; padding-top: .6rem;
    border-top: 1px dashed var(--line); display: flex; gap: .4rem;
    flex-wrap: wrap; }}
  .v {{ font-size: .78rem; color: var(--mid); border: 1px solid var(--line);
    border-radius: 999px; padding: .15rem .6rem; }}
</style>
</head>
<body>
<main>
  <h1>Match review sample</h1>
  <p class="sub">{len(sample)} rows drawn at random from the {{n_total}} matched
  listings, seed {SEED}. Grade these without looking at my pass, so the agreement
  rate means something.</p>

  <div class="box">
    <p class="rule">{e(RULE)}</p>
    <h2>Verdicts</h2>
    <table>{guide}</table>
  </div>

  <div class="box">
    <h2>How to return it</h2>
    <p style="margin:0">Fill the <code>verdict</code> column in
    <code>data/manual/intercoder_sample.csv</code>, or just tell me the row
    numbers you would reject and why. Either works.</p>
  </div>
{"".join(cards)}
</main>
</body>
</html>
"""


def write_sheets(raw_path=None, bistro_path=None, verbose: bool = True):
    df = review_frame(raw_path, bistro_path)
    sample = df.sample(n=min(N_INTERCODER, len(df)), random_state=SEED).sort_values("row_id")

    config.ensure_dirs()
    config.CHARTS.parent.mkdir(parents=True, exist_ok=True)
    full_path = config.MANUAL / "format_review.csv"
    samp_path = config.MANUAL / "intercoder_sample.csv"
    html_path = config.OUTPUT / "intercoder_sample.html"

    df.to_csv(full_path, index=False)
    sample.drop(columns="already_manually_rejected").to_csv(samp_path, index=False)
    html_path.write_text(_html(sample).replace("{n_total}", str(len(df))))

    if verbose:
        print(f"{len(df)} matched rows over {df.matched_id.nunique()} dishes")
        print(f"  full pass sheet     {full_path}")
        print(f"  inter-coder sample  {samp_path}  ({len(sample)} rows, seed {SEED})")
        print(f"  readable version    {html_path}")
    return df, sample


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    write_sheets()
