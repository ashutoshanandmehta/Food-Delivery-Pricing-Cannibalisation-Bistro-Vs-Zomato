# Findings

Each verdict references the kill condition stated before the analysis ran. None
was adjusted afterwards.

Panel: Q3FY23 to Q1FY27, sixteen quarters, from Eternal shareholders' letters
filed with BSE. Values cross checked across three overlapping letters with no
restatements found. Swiggy control: Q1FY26 to Q1FY27 from Swiggy's Q1FY27
letter.

---

## The headline

> Migrating a rupee of order value from Zomato's marketplace to Bistro's owned
> kitchen is accretive for Eternal as long as Bistro's contribution margin
> clears **10.2% of its own order value**. That is the marketplace's own
> disclosed margin, and it is the bar at *total* cannibalisation. At a 60%
> cannibalisation rate the bar is 6.1%. At 40% it is 4.1%.

And the number that frames the whole question:

> Bistro sits inside an 'Others' segment whose entire quarterly revenue is
> **₹95 crore, or 0.88% of food delivery NOV**, and that segment also contains
> Nugget and Greening India. Even at total cannibalisation with zero Bistro
> margin, the contribution Eternal forgoes is about ₹10 crore a quarter against
> ₹1,097 crore of food delivery contribution.

Cannibalisation is not currently a material risk at any rate. The threshold
matters for the scale up decision, not for today's P&L.

---

## Correction to the brief's premise

The brief states Bistro "has scaled from 38 to 100+ cloud kitchens". The filings
do not support that.

| Quarter | Kitchens | Cities | Source |
|---|---|---|---|
| Q1FY26 | 38 | 2 (Delhi NCR, Bangalore) | Q1FY26 letter, Q14 |
| Q3FY26 | ~45 | 2 (Delhi NCR, Bangalore) | Q3FY26 letter, Q14 |

Seven kitchens added over two quarters, still in two cities. The scale up the
brief assumes has not happened. Over the same period Blinkit added roughly 900
dark stores. Any framing built on "100+ kitchens" needs to be dropped.

---

## H1: Cannibalisation is margin accretive, not dilutive

Notebook: `01_unit_economics.ipynb`

* **Kill condition:** `alpha*` falls below 1 at `retention = 1`, and below the
  plausible range for actual alpha
* **`CM_zomato`: 10.19% of NOV** (₹1,097 cr on ₹10,769 cr, Q1FY27). Disclosed,
  not derived. Stable in a 9.9% to 10.4% band across the last six quarters.
* **`CM_bistro`: not estimable from public data.** Bistro has no standalone
  P&L and menu prices have not been sampled.
* **Verdict: the threshold is computed, the comparison is not.** Because
  CM_bistro cannot be estimated honestly, the analysis reports the bar rather
  than a false point estimate. See `output/charts/h1_required_cm_bistro.png`.

| alpha | Required CM_bistro, retention 100% | retention 75% | retention 50% |
|---|---|---|---|
| 20% | 2.04% | 1.53% | 1.02% |
| 40% | 4.07% | 3.06% | 2.04% |
| 60% | 6.11% | 4.58% | 3.06% |
| 80% | 8.15% | 6.11% | 4.07% |
| 95% | 9.68% | 7.26% | 4.84% |
| 100% | 10.19% | 7.64% | 5.09% |

**What makes this a strong result.** At total cannibalisation the condition
collapses to `CM_bistro > CM_zomato`. The entire question is whether an owned
kitchen earns more per rupee of order value than the marketplace does. Nothing
else in the model matters at that point.

* **Confidence, CM_zomato: high.** Read off a filing, with the definition
  published in the same document. No add back assumption is used.
* **Confidence, CM_bistro: none yet.** It has not been estimated.

## H2: Bistro is defensive, so the counterfactual is not Zomato

Notebook: `03_competitive_context.ipynb`

* **Kill condition:** Bistro launched first, into cities with no competitor
  presence, and management never frames it competitively
* **Launch sequencing. Bistro followed, it did not lead.**

| Date | Event |
|---|---|
| 2022 | Zepto launches Cafe inside the Zepto app |
| **5 Oct 2024** | **Swiggy launches Bolt**, 10 minute delivery from 2,700+ restaurants across Bangalore, Chennai, Hyderabad, Delhi, Mumbai, Pune |
| Dec 2024 | Zepto Cafe gets a separate app and expands to Delhi NCR, Bengaluru, Hyderabad, Chennai, Pune |
| **Dec 2024** | **Blinkit launches Bistro** in parts of Gurugram, inside Delhi NCR |
| Jan 2025 | Swiggy launches SNACC, its own brand 15 minute app |

* Bistro entered Delhi NCR after both Bolt and Zepto Cafe were already live
  there. Within eight weeks of its own launch Bolt was already 5% of Swiggy's
  food delivery orders.
* **Management frames it competitively and explicitly.** Q1FY27 letter, Q3, on
  Toing and Ownly: *"What we are spending energy on is Bistro, which is our
  answer to the question these platforms are pretending to solve. If you want to
  make food delivery work at INR 50-150 price points, you can't do it without
  supply chain innovation."*
* **Verdict: H2 survives. The kill condition fails on both limbs.** Bistro did
  not launch first and management does frame it competitively.
* **The nuance that still matters.** The framing is that Bistro answers a
  *segment* those platforms target, not that it defends existing Zomato volume.
  So the evidence supports a low alpha more strongly than it supports a low
  retention. Every figure in the deck therefore still uses `retention = 1`.
* **Confidence: medium.** Launch dates are from press, not filings. City level
  overlap is directional rather than counted.

## H3: Price points separate, bounding alpha from above

Notebook: `02_price_positioning.ipynb`

* **Kill condition:** the price distributions substantially overlap
* **Evidence, from the filings rather than the menu sample:**
  * Q1FY27: Bistro targets **"INR 50-150 price points"**.
  * Q1FY26: Bistro taps *"two demand pockets so far unaddressed by Zomato:
    a) customers looking for high quality but low cost meals (think customers
    who buy from home chefs) and b) customers looking for snacky food in
    10 mins."*
  * Q3FY25 at launch: the target was the in office market *"currently addressed
    by on-site vendors and vending machines"*.
* For scale, Blinkit's net AOV is ₹518 and Zomato food delivery AOV is not
  disclosed, but a ₹50-150 price point sits far below any plausible restaurant
  delivery ticket.
* **Verdict: not killed, and well supported qualitatively.** The overlap share
  still needs the hand sampled menu data, which requires app access and cannot
  be collected from filings.
* **Confidence: medium on direction, none on magnitude.**

## H4: Observable data is consistent with low to moderate alpha

Notebook: `04_observable_evidence.ipynb`

* **Kill condition:** the per customer contribution turns persistently negative
  while transacting customers stay positive
* **Method change, forced by disclosure.** Eternal has never disclosed food
  delivery Orders or AOV in the shareholders' letters, so the planned
  three way split into customers, frequency and ticket size is not computable.
  The honest substitute is a two way split into transacting customers and NOV
  per transacting customer, which carries frequency and ticket size together.

| Quarter | fd NOV YoY | MTU (mn) | NOV per customer YoY |
|---|---|---|---|
| Q1FY26 | 13.1% | 22.9 | +0.3% |
| Q2FY26 | 13.8% | 24.1 | −2.3% |
| Q3FY26 | 16.6% | 24.9 | −4.0% |
| Q4FY26 | 18.8% | 25.4 | −2.2% |
| Q1FY27 | 20.1% | 27.2 | +1.1% |

* **The kill condition's pattern does appear.** Per customer value contribution
  was negative for three consecutive quarters while customer growth stayed
  strongly positive.
* **But the attribution fails on magnitude.** Bistro is 0.88% of food delivery
  NOV. It cannot mechanically produce a 2% to 4% decline in NOV per customer.
  The far more likely cause is mix: customers grew 18.8% YoY and newly acquired
  cohorts spend less than mature ones.
* **Verdict: H4 survives, with the pattern explained by something other than
  Bistro.** Food delivery NOV growth *accelerated* from 13.1% to 20.1% straight
  through the Bistro scale up. Contribution margin rose from 9.9% to 10.2%.
* **Confidence: medium.** The direction is clear. The decomposition is coarser
  than planned because the disclosure is coarser than assumed.

## H5: Category maturity, not Bistro, explains the growth path

Notebook: `04_observable_evidence.ipynb`

* **Kill condition:** Swiggy food delivery grows materially faster than Zomato
  through the Bistro scale up
* **Evidence:** Swiggy food delivery GOV grew 17.4% YoY in Q1FY27 against
  Eternal food delivery NOV at 20.1%. Swiggy's B2C GOV growth decelerated from
  45.2% to 27.9% over the same five quarters. Both marketplaces improved
  contribution margin: Zomato 9.9% to 10.2% of NOV, Swiggy 7.3% to 7.6% of GOV.
* **Verdict: kill condition not met, but the hypothesis is moot.** H5 was
  written to explain a slowdown. There is no slowdown to explain. Zomato food
  delivery accelerated and outgrew its control.
* **Control contamination, as flagged:** Swiggy runs Bolt and Snacc, so it is
  not a clean control. It biases the two series toward looking alike, which
  makes Zomato's outperformance a conservative reading.
* **Not like for like:** Eternal states contribution against NOV, Swiggy against
  GOV, and NOV is roughly 83% of GOV. Compare directions, not levels.
* **Confidence: medium.** Five quarters, one control, incompatible bases.

## H6: The real conflict is capital allocation

Notebook: `05_capital_and_org.ipynb`

* **Kill condition:** food delivery holds steady capex and marketing share
* **Evidence:** share of B2C net order value, which is the honest measure
  because revenue share is inflated by Blinkit's inventory led accounting.

| Quarter | Food delivery | Quick commerce | Blinkit stores | Bistro kitchens |
|---|---|---|---|---|
| Q4FY24 | 63.3% | 29.4% | 526 | |
| Q4FY25 | 47.1% | 42.2% | 1,301 | |
| Q1FY26 | 44.4% | 45.6% | 1,544 | 38 |
| Q3FY26 | 38.3% | 51.7% | 2,027 | ~45 |
| Q1FY27 | 34.6% | 55.1% | 2,443 | |

* **Verdict: H6 survives, emphatically.** Food delivery went from roughly two
  thirds of B2C order value to roughly one third in ten quarters. Q1FY26 capex
  of ₹370 crore went ₹310 crore to quick commerce stores and warehouses, with
  the ₹60 crore balance covering Bistro kitchens *and* routine IT hardware
  across all businesses.
* **The contest is not Bistro against Zomato.** Bistro added 7 kitchens while
  Blinkit added around 900 stores. The capital contest is quick commerce against
  everything else, and Bistro is a rounding error inside it.
* **Confidence: high.** All figures disclosed.

## H7: The conflict is already resolved organizationally

Notebook: `05_capital_and_org.ipynb`

* **Kill condition:** food delivery retains independent capital authority
* **Evidence, all from BSE filings:**

| Date | Event |
|---|---|
| 6 Feb 2025 | Board approves renaming Zomato Limited to Eternal Limited |
| 20 Mar 2025 | Name change takes effect. The food delivery brand is no longer the group's name |
| 5 Apr 2025 | Rinshul Chandra resigns as Chief Operating Officer of the food delivery business |
| **21 Jan 2026** | **Board accepts Deepinder Goyal's resignation as Director, MD and CEO, and appoints Albinder Singh Dhindsa, then CEO of Blinkit, as Chief Executive Officer with effect from 1 February 2026** |
| 10 Feb 2026 | Board approves Goyal's appointment as Vice Chairman and Non-Executive Director |

* **Verdict: H7 survives, and it is the cleanest result in the project.** The
  quick commerce CEO runs the parent company. The founder who built food
  delivery moved to a non-executive seat. The company no longer carries the
  food delivery brand's name. Alongside quick commerce moving from 29% to 55%
  of B2C net order value, food delivery does not retain independent capital
  authority in any meaningful sense.
* **Confidence: high.** Primary sources, exact dates, named individuals.

## One more thing management said, and it reframes Bistro

The Q4FY25 letter, Q15, on shutting down Zomato Quick and Everyday:

> *"We are actually shutting down both these initiatives as we are not seeing
> the path to profitability... The current restaurant density and kitchen
> infrastructure is not set up for delivering orders in 10 minutes which leads
> to inconsistent customer experience. As a result, we did not see any
> incrementality in demand while we ran Quick as an experiment for a few
> months."*

Quick was the **marketplace** version of 10 minute delivery: Eternal's own
restaurant partners, curated menus, a dedicated fleet. It failed, and it failed
for a structural reason. A marketplace does not control the kitchen.

Bistro is the owned kitchen answer to precisely that constraint. That is the
strongest available argument that Bistro is a different product rather than a
cheaper Zomato, and it comes from management explaining a failure rather than
selling a success.

---

## What the per order model leaves out

Not hypotheses, because none is testable with public data. They belong on the
risks slide with the direction each moves the answer.

| Omission | Direction | Why it is not modelled |
|---|---|---|
| A Bistro order adds nothing to restaurant selection, which is the moat | Against Bistro | No public measure of selection value per order |
| A dealer tends to support lower volume than a platform operator | Against Bistro | Requires a counterfactual assortment, which does not exist |
| Owning kitchens weakens restaurant bargaining power | For Bistro | Commission terms are not disclosed per partner |
| Orders are compared, not lifetimes. Frequency and retention may differ | Unknown | No cohort data for either product |
| Hyperpure shortens Bistro's menu innovation cycle (Q3FY26 letter) | For Bistro | Group level benefit, not attributable per order |

---

## What is still needed

1. **Menu price sample.** The single remaining input. It closes H3's magnitude
   and gives the order value line in the CM_bistro stack. It requires app access
   and cannot be collected from filings.
2. **Comparator store economics.** Jubilant, Devyani, Sapphire, Westlife, to
   bound whether a 10 minute owned kitchen can clear 10.2% contribution on a
   ₹50-150 ticket after delivery cost.
