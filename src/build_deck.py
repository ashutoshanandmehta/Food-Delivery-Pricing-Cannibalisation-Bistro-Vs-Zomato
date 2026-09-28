"""Build the six slide board deck as one self contained HTML file.

No CDN, no external assets. Charts are embedded as base64 data URIs so the file
opens anywhere and cannot drift from the notebooks that produced it.
"""
import base64, json, pathlib, sys
sys.path.insert(0, ".")
from src import config

CH = {p.stem: "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
      for p in sorted(config.CHARTS.glob("*.png"))}

CSS = """
:root{
  --ink:#14161a; --muted:#6b7280; --line:#e3e6ea; --paper:#ffffff; --wash:#f6f7f9;
  --fd:#1f4e79; --qc:#c55a11; --pos:#2e7d32; --neg:#b03a2e; --accent:#1d5c22;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--wash);color:var(--ink);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Helvetica,Arial,sans-serif;}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 80px}
header.doc{padding:28px 0 20px;border-bottom:2px solid var(--ink);margin-bottom:8px}
header.doc h1{margin:0 0 6px;font-size:26px;letter-spacing:-.02em}
header.doc .sub{color:var(--muted);font-size:14.5px}
header.doc .meta{margin-top:14px;font-size:12.5px;color:var(--muted)}
.slide{background:var(--paper);border:1px solid var(--line);border-radius:10px;
  padding:30px 34px 34px;margin:22px 0;box-shadow:0 1px 2px rgba(20,22,26,.04)}
.slide-no{font-size:11.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);
  font-weight:700;margin-bottom:8px}
.slide h2{margin:0 0 6px;font-size:23px;line-height:1.25;letter-spacing:-.015em}
.deck{color:var(--muted);font-size:14.5px;margin:0 0 20px}
.rec{background:#f3f6fa;border-left:4px solid var(--fd);padding:16px 20px;
  border-radius:0 7px 7px 0;margin:0 0 22px;font-size:16.5px}
.rec strong{color:var(--fd)}
.nums{display:flex;gap:14px;flex-wrap:wrap;margin:20px 0}
.num{flex:1 1 190px;border:1px solid var(--line);border-radius:8px;padding:15px 17px;background:#fcfdfe}
.num .v{font-size:29px;font-weight:700;letter-spacing:-.02em;line-height:1.1}
.num .k{font-size:11.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);
  margin-bottom:7px;font-weight:700}
.num .n{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.4}
.num.pos .v{color:var(--pos)} .num.warn .v{color:var(--qc)} .num.key .v{color:var(--fd)}
figure{margin:22px 0 0}
figure img{width:100%;height:auto;display:block;border:1px solid var(--line);border-radius:7px}
figcaption{font-size:12.5px;color:var(--muted);margin-top:9px;line-height:1.5}
table{width:100%;border-collapse:collapse;margin:18px 0;font-size:14px}
th,td{text-align:left;padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
  border-bottom:1.5px solid var(--ink)}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr.hi td{background:#fdf6ef;font-weight:600}
.cols{display:flex;gap:22px;flex-wrap:wrap;margin:6px 0}
.col{flex:1 1 300px}
.col h3{font-size:14px;margin:0 0 9px;letter-spacing:.02em}
.col.a h3{color:var(--fd)} .col.b h3{color:var(--qc)}
.card{border:1px solid var(--line);border-radius:8px;padding:15px 17px;height:100%;background:#fcfdfe}
ul{margin:9px 0;padding-left:19px} li{margin:6px 0}
blockquote{margin:16px 0;padding:13px 18px;background:#f7f8fa;border-left:3px solid var(--muted);
  border-radius:0 6px 6px 0;font-size:14.5px;color:#33383f}
blockquote .src{display:block;margin-top:8px;font-size:12px;color:var(--muted)}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  padding:2.5px 8px;border-radius:11px;margin-right:6px}
.tag.hi{background:#e6f2e6;color:var(--pos)} .tag.md{background:#fdf1e3;color:var(--qc)}
.tag.lo{background:#fbe9e7;color:var(--neg)} .tag.none{background:#eceef1;color:var(--muted)}
.note{font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:13px;margin-top:20px}
.gate{background:#fbf7ec;border:1px solid #e8dcc0;border-radius:8px;padding:15px 18px;margin-top:18px;font-size:14.5px}
footer.doc{margin-top:34px;padding-top:18px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--muted)}
@media print{
  body{background:#fff} .wrap{max-width:none;padding:0}
  .slide{page-break-after:always;break-after:page;border:none;box-shadow:none;padding:0 0 20px;margin:0}
  header.doc{page-break-after:always}
}
"""

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bistro switching value: board deck</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header class="doc">
  <h1>Is Bistro creating or destroying value for Eternal?</h1>
  <div class="sub">A switching value analysis of self cannibalisation in quick commerce</div>
  <div class="meta">
    Six slide board deck &nbsp;·&nbsp; ECO507 Managerial Economics and Business Analysis &nbsp;·&nbsp;
    Data through Q1FY27 (quarter ended 30 June 2026)<br>
    Sources: 12 Eternal Ltd shareholders' letters and Swiggy Ltd's Q1FY27 letter, filed with BSE.
    Independent analysis of public filings. Not investment advice.
  </div>
</header>

<!-- ───────────────────────── 1 ───────────────────────── -->
<section class="slide">
  <div class="slide-no">Slide 1 · Executive summary</div>
  <h2>Cannibalisation was never the risk. Ask about the margin, and about the capital.</h2>

  <div class="rec">
    <strong>Recommendation.</strong> Do not price Bistro as a threat to Zomato. Migrating a rupee of
    order value from the marketplace to an owned kitchen is accretive as long as Bistro clears
    <strong>10.2% contribution</strong> on its own order value, and Bistro is currently too small to
    move the group either way. Monitor the margin, not the cannibalisation rate.
  </div>

  <div class="nums">
    <div class="num key">
      <div class="k">The bar, at total cannibalisation</div>
      <div class="v">10.2%</div>
      <div class="n">Contribution Bistro must earn on its own order value. It is the marketplace's own
      disclosed margin. At 60% cannibalisation the bar falls to 6.1%.</div>
    </div>
    <div class="num warn">
      <div class="k">Bistro's scale today</div>
      <div class="v">0.88%</div>
      <div class="n">Upper bound on Bistro as a share of food delivery NOV. The whole
      <em>Others</em> segment is ₹95 cr against ₹10,769 cr, and it also holds Nugget and Greening India.</div>
    </div>
    <div class="num pos">
      <div class="k">Food delivery NOV growth</div>
      <div class="v">13.1 → 20.1%</div>
      <div class="n">Year on year, Q1FY26 to Q1FY27. It <em>accelerated</em> straight through the
      Bistro scale up, while contribution margin rose from 9.9% to 10.2%.</div>
    </div>
  </div>

  <p>Even at total cannibalisation with zero Bistro margin, the contribution Eternal gives up is about
  <strong>₹10 crore a quarter</strong> against ₹1,097 crore of food delivery contribution. No plausible
  cannibalisation rate makes Bistro material today. What is material is that food delivery fell from
  63% to 35% of group order value while Blinkit added roughly 900 stores, and that Blinkit's CEO now
  runs the parent company.</p>

  <div class="note">
    <strong>Confidence, stated by component.</strong>
    <span class="tag hi">High</span> <code>CM_zomato</code> and all scale figures: read off filings,
    with definitions published in the same documents.
    <span class="tag none">Not estimated</span> <code>CM_bistro</code>: no standalone P&amp;L and no
    menu sample, so this deck reports the bar it must clear rather than a number.
    <span class="tag md">Medium</span> the cannibalisation rate itself: unobservable, which is why the
    analysis is built as a threshold.
  </div>
</section>

<!-- ───────────────────────── 2 ───────────────────────── -->
<section class="slide">
  <div class="slide-no">Slide 2 · Why this question, why now</div>
  <h2>Eternal already tried 10 minute food on the marketplace. It failed for a structural reason.</h2>
  <p class="deck">Bistro is the owned kitchen answer to that failure, launched into a market where
  three competitors were already live.</p>

  <blockquote>
    "We are actually shutting down both these initiatives&hellip; The current <strong>restaurant density
    and kitchen infrastructure is not set up for delivering orders in 10 minutes</strong>, which leads to
    inconsistent customer experience. As a result, <strong>we did not see any incrementality in demand</strong>
    while we ran Quick as an experiment for a few months."
    <span class="src">Deepinder Goyal on shutting Zomato Quick and Everyday. Q4FY25 shareholders' letter, Q15.</span>
  </blockquote>

  <p>A marketplace does not control the kitchen. That is why Quick could not work and it is exactly what
  an owned kitchen changes. The competitive sequence matters too: <strong>Bistro followed, it did not lead.</strong></p>

  <table>
    <tr><th>Date</th><th>Event</th></tr>
    <tr><td>2022</td><td>Zepto launches Cafe inside the Zepto app</td></tr>
    <tr class="hi"><td>5 Oct 2024</td><td>Swiggy launches <strong>Bolt</strong>, 10 minute delivery from 2,700+ restaurants across six metros</td></tr>
    <tr><td>Dec 2024</td><td>Zepto Cafe gets a separate app, expands to Delhi NCR, Bengaluru, Hyderabad, Chennai, Pune</td></tr>
    <tr class="hi"><td>Dec 2024</td><td><strong>Blinkit launches Bistro</strong> in parts of Gurugram, inside Delhi NCR</td></tr>
    <tr><td>Jan 2025</td><td>Swiggy launches SNACC, its own brand 15 minute app</td></tr>
    <tr><td>May 2025</td><td>Eternal shuts Zomato Quick and Everyday</td></tr>
  </table>

  <p>Bistro entered Delhi NCR after both Bolt and Zepto Cafe were live there. Within eight weeks of its
  own launch Bolt was already 5% of Swiggy's food delivery orders. Management now frames Bistro against
  Toing and Ownly explicitly: <em>"our answer to the question these platforms are pretending to solve&hellip;
  food delivery at INR 50-150 price points."</em></p>

  <div class="note"><strong>What this changes in the model.</strong> If a cannibalised order was heading
  to Bolt anyway, Eternal forfeits nothing by serving it from its own kitchen. That would raise the bar's
  slope in the company's favour. This deck does <em>not</em> take that credit: every figure assumes
  100% retention, the most conservative case.</div>
</section>

<!-- ───────────────────────── 3 ───────────────────────── -->
<section class="slide">
  <div class="slide-no">Slide 3 · The two business models</div>
  <h2>A cannibalised order is not a loss. It is an order that changed business model.</h2>
  <p class="deck">The same rupee of order value is worth different amounts depending on which model carries it.</p>

  <div class="cols">
    <div class="col a"><div class="card">
      <h3>Zomato · platform operator</h3>
      <ul>
        <li>Restaurants cook. Eternal takes a slice of the order.</li>
        <li>Asset light. No inventory, no kitchen, no staff.</li>
        <li><strong>Contribution: 10.19% of NOV</strong>, disclosed every quarter.</li>
        <li>Every order feeds restaurant selection, which is the moat.</li>
      </ul>
    </div></div>
    <div class="col b"><div class="card">
      <h3>Bistro · dealer</h3>
      <ul>
        <li>Eternal owns the kitchen and keeps the whole order value.</li>
        <li>Pays food COGS, kitchen cost, delivery, packaging.</li>
        <li><strong>Contribution: not disclosed.</strong> No standalone P&amp;L.</li>
        <li>Contributes nothing to restaurant selection.</li>
      </ul>
    </div></div>
  </div>

  <p style="margin-top:18px">There is no arithmetic reason the two must differ, which is precisely why the
  threshold is worth computing rather than asserting. Zomato takes a small slice of a large order. Bistro
  takes all of a small one and pays to produce it.</p>

  <p><strong>Why <code>CM_zomato</code> is a read, not an assumption.</strong> Eternal publishes food
  delivery Contribution every quarter <em>and</em> publishes its definition: Adjusted Revenue less last
  mile delivery, platform funded discounts, payment gateway and COD handling, customer support and
  appeasement, refunds, and delivery partner onboarding. Every line moves with order volume. None of it
  is fixed cost, overhead, brand marketing or technology. That is already the marginal cost base a
  switching value needs, so no fixed cost add back is required.</p>

  <figure>
    <img src="{CH['h1_cm_zomato_series']}" alt="Zomato food delivery contribution margin by quarter">
    <figcaption>Contribution has been stable in a 9.9% to 10.4% band for six quarters and has risen
    through the Bistro period. Source: Eternal shareholders' letters, BSE.</figcaption>
  </figure>
</section>

<!-- ───────────────────────── 4 ───────────────────────── -->
<section class="slide">
  <div class="slide-no">Slide 4 · Who actually substitutes</div>
  <h2>Bistro and Zomato serve different willingness to pay. That caps how high cannibalisation can go.</h2>
  <p class="deck">This is the slide that defends the baseline. Two products at different price points are
  not one market with a gap. They are two segments, sorted by self selection.</p>

  <table>
    <tr><th>Source</th><th>What management says Bistro is for</th></tr>
    <tr><td>Q3FY25, at launch</td><td>The in office market for snacks, meals and beverages in 10 to 15 minutes,
      <em>"currently addressed by on-site vendors and vending machines"</em></td></tr>
    <tr><td>Q1FY26</td><td><em>"Two demand pockets so far unaddressed by Zomato: customers looking for high
      quality but low cost meals (think customers who buy from home chefs), and customers looking for snacky
      food in 10 mins"</em></td></tr>
    <tr class="hi"><td>Q1FY27</td><td>Food delivery at <strong>"INR 50-150 price points"</strong>, which
      <em>"can't be done without supply chain innovation&hellip; a different segment, a different occasion,
      and a genuinely new market"</em></td></tr>
  </table>

  <p>A ₹50 to ₹150 ticket sits far below any plausible restaurant delivery order. For scale, Blinkit's
  net average order value is ₹518. And Eternal has already run the experiment that tests substitution
  directly: Quick offered 10 minute delivery from <em>Zomato's own restaurants</em> and produced
  <strong>no incrementality in demand</strong>. Restaurant supplied fast food did not expand the market.
  Bistro is a different bet on a different price point.</p>

  <div class="note"><strong>Gap, stated plainly.</strong> The overlap share between the two price
  distributions has not been measured. It needs a hand sampled menu comparison, which requires app access
  with a location and cannot be built from filings. Until it exists, this argument is directional and the
  deck runs the cannibalisation rate all the way to 100% rather than resting on a baseline.</div>
</section>

<!-- ───────────────────────── 5 ───────────────────────── -->
<section class="slide">
  <div class="slide-no">Slide 5 · Unit economics and the switching value</div>
  <h2>The bar Bistro has to clear</h2>
  <p class="deck">Bistro's own margin cannot be estimated honestly from public data, so the analysis
  inverts the threshold and states the bar instead of guessing the number.</p>

  <p style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:14px;background:#f6f7f9;
     padding:13px 16px;border-radius:7px;border:1px solid var(--line)">
    CM_net &nbsp;=&nbsp; CM_bistro &minus; (&alpha; × retention × CM_zomato)<br>
    required CM_bistro &nbsp;=&nbsp; &alpha; × retention × CM_zomato
  </p>

  <p>At &alpha; = 1 and retention = 1 the condition collapses to <strong>CM_bistro &gt; CM_zomato</strong>.
  Under total cannibalisation the entire question is whether an owned kitchen earns more per rupee of
  order value than the marketplace does. Nothing else in the model matters at that point.</p>

  <figure>
    <img src="{CH['h1_required_cm_bistro']}" alt="Required Bistro contribution margin by cannibalisation rate">
    <figcaption>Everything above a line is accretive at that retention assumption. The deck uses the
    100% retention line, the most conservative case, for every claim.</figcaption>
  </figure>

  <table>
    <tr><th>Cannibalisation &alpha;</th><th class="n">Bar at retention 100%</th><th class="n">at 75%</th><th class="n">at 50%</th></tr>
    <tr><td>20%</td><td class="n">2.04%</td><td class="n">1.53%</td><td class="n">1.02%</td></tr>
    <tr><td>40%</td><td class="n">4.07%</td><td class="n">3.06%</td><td class="n">2.04%</td></tr>
    <tr><td>60%</td><td class="n">6.11%</td><td class="n">4.58%</td><td class="n">3.06%</td></tr>
    <tr><td>80%</td><td class="n">8.15%</td><td class="n">6.11%</td><td class="n">4.07%</td></tr>
    <tr class="hi"><td>100% (total)</td><td class="n">10.19%</td><td class="n">7.64%</td><td class="n">5.09%</td></tr>
  </table>

  <p><strong>And the stake is small.</strong> Bistro sits inside an <em>Others</em> segment worth ₹95 crore
  a quarter, 0.88% of food delivery NOV, shared with Nugget and Greening India. The absolute worst case,
  total cannibalisation with zero Bistro margin, costs about ₹10 crore a quarter.</p>

  <figure>
    <img src="{CH['h1_materiality']}" alt="Bistro scale against food delivery">
    <figcaption>Bistro is still about 45 kitchens in two cities, up from 38 a year earlier. Over the same
    period Blinkit added roughly 900 dark stores.</figcaption>
  </figure>
</section>

<!-- ───────────────────────── 6 ───────────────────────── -->
<section class="slide">
  <div class="slide-no">Slide 6 · What to monitor, and named risks</div>
  <h2>The contest that was actually settled</h2>

  <p>While the cannibalisation question was being debated, food delivery went from
  <strong>63% to 35%</strong> of group order value and Blinkit's CEO became CEO of the parent company.</p>

  <table>
    <tr><th>Quarter</th><th class="n">Food delivery share of B2C NOV</th><th class="n">Quick commerce</th><th class="n">Blinkit stores</th><th class="n">Bistro kitchens</th></tr>
    <tr><td>Q4FY24</td><td class="n">63.3%</td><td class="n">29.4%</td><td class="n">526</td><td class="n">&mdash;</td></tr>
    <tr><td>Q1FY26</td><td class="n">44.4%</td><td class="n">45.6%</td><td class="n">1,544</td><td class="n">38</td></tr>
    <tr class="hi"><td>Q1FY27</td><td class="n">34.6%</td><td class="n">55.1%</td><td class="n">2,443</td><td class="n">~45</td></tr>
  </table>

  <p>On 21 January 2026 the board accepted Deepinder Goyal's resignation as MD and CEO and appointed
  <strong>Albinder Singh Dhindsa, then CEO of Blinkit, as Chief Executive Officer</strong> of Eternal.
  The company had already renamed itself away from the food delivery brand in March 2025, and food
  delivery's COO resigned that April. Food delivery does not retain independent capital authority in any
  meaningful sense.</p>

  <h3 style="font-size:15px;margin:24px 0 8px">Three risks, with mitigants</h3>
  <table>
    <tr><th>Risk</th><th>Why it bites</th><th>Mitigant</th></tr>
    <tr>
      <td><strong>Bistro scales before the margin is proven</strong></td>
      <td>The bar is only cheap while Bistro is small. At 10x the kitchens, a sub-10.2% margin becomes a real drag.</td>
      <td>Gate kitchen additions on disclosed <em>Others</em> segment contribution, not on order growth.</td>
    </tr>
    <tr>
      <td><strong>The order value framing is wrong</strong></td>
      <td>&alpha; here is measured on order value, not orders, because food delivery Orders and AOV are
      not disclosed. If one Bistro order displaces one whole Zomato order, the bar shown is too low.</td>
      <td>Sample Bistro and Zomato menu prices. It is the single missing input and it closes this directly.</td>
    </tr>
    <tr>
      <td><strong>Bistro erodes the moat, not the margin</strong></td>
      <td>Restaurant selection is the primary entry barrier. A Bistro order adds nothing to it, and a
      dealer typically supports lower volume and narrower selection than a platform operator.</td>
      <td>Track monthly active restaurant partners. It fell 344k to 328k in Q1FY27, the first
      material decline in a series that had otherwise risen every quarter since Q3FY23.</td>
    </tr>
  </table>

  <div class="gate">
    <strong>The gate.</strong> This is a conditional read, not a blank cheque. Revisit if <em>Others</em>
    segment revenue passes about 3% of food delivery NOV, or if food delivery contribution margin falls
    below 9.5% of NOV for two consecutive quarters. Both are disclosed quarterly, so the trigger is
    observable within 90 days of it firing.
  </div>

  <div class="note">
    <strong>What would change the answer, in order of impact.</strong>
    1. A menu price sample, which closes the substitution question and the order versus value framing.
    2. Bistro broken out of the <em>Others</em> segment, which would replace the entire threshold with a
    comparison. 3. City level food delivery NOV, which would allow a real difference in differences using
    Bistro's staged rollout. None of the three is public today.
  </div>
</section>

<!-- ───────────────────────── appendix ───────────────────────── -->
<section class="slide">
  <div class="slide-no">Appendix · Supporting evidence</div>
  <h2>What the observable data shows</h2>

  <figure>
    <img src="{CH['h4_nov_decomposition']}" alt="Food delivery NOV growth decomposition">
    <figcaption><strong>H4.</strong> Food delivery Orders and AOV have never been disclosed, so order
    frequency cannot be separated from ticket size. NOV per transacting customer carries both. Value per
    customer softened for three quarters while customer growth stayed strong, but at 0.88% of NOV, Bistro
    cannot mechanically produce a 2% to 4% decline. Rapid customer growth diluting the mix is the far more
    likely cause.</figcaption>
  </figure>

  <figure>
    <img src="{CH['h5_swiggy_control']}" alt="Zomato versus Swiggy food delivery contribution margin">
    <figcaption><strong>H5.</strong> Swiggy is the control, and a contaminated one since it runs Bolt and
    Snacc. Swiggy food delivery GOV grew 17.4% year on year in Q1FY27 against Eternal's 20.1% on NOV, and
    both marketplaces improved margin. There is no slowdown at Zomato for category maturity to explain.
    Levels are not comparable because Eternal states contribution against NOV and Swiggy against GOV.
    Directions are.</figcaption>
  </figure>

  <h3 style="font-size:15px;margin:26px 0 8px">Data integrity</h3>
  <p style="font-size:14.5px">Eternal's Annexure A tables are vector graphics with no text layer, so the
  panel was transcribed from rendered page images rather than parsed. Three controls: every quarter that
  appears in two overlapping letters matched exactly with no restatements; quick commerce NOV divided by
  Orders reproduces the separately disclosed net average order value within 2% in every quarter, which is
  asserted in the test suite; and any implausible quarter on quarter move is held by a validation gate
  until it carries a written explanation. One breach was raised and signed off.</p>

  <footer class="doc">
    Panel: 16 quarters, Q3FY23 to Q1FY27, from 12 Eternal Ltd shareholders' letters filed with BSE
    (scrip 543320), plus 5 quarters of Swiggy Ltd (scrip 544285) as a control. Every row carries its
    source document. Full working, assumptions and hypothesis verdicts in the accompanying repository:
    <code>docs/FINDINGS.md</code> and <code>docs/ASSUMPTIONS.md</code>.<br><br>
    Independent analysis using public filings. Not investment advice. No affiliation with Eternal Ltd,
    Blinkit, Zomato or Swiggy.
  </footer>
</section>

</div>
</body>
</html>
"""

out = pathlib.Path("output/bistro_board_deck.html")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(HTML, encoding="utf-8")
print(f"written: {out.resolve()}  ({len(HTML)//1024} KB)")
