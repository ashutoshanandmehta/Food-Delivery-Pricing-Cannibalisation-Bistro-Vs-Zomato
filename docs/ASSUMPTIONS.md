# Assumptions log

Every estimate, proxy and judgement call that is not read directly off a filing.
An interviewer probes assumptions harder than conclusions, so this file is an
asset rather than an admission. It is a deliverable, not internal scaffolding.

Rule: if a number is not traceable to a `source_url` in the panel, it belongs
here.

Every row carries a **direction**: which way the conclusion moves if the input
is wrong. A confidence label without a direction tells the reader you are unsure
but not what to do about it.

---

## What turned out not to be an assumption at all

The brief planned to derive `CM_zomato` from food delivery Adjusted EBITDA plus
an assumed fixed cost add back, and flagged that add back as one of the five
load bearing assumptions in the project.

**It is unnecessary.** Eternal discloses food delivery **Contribution** every
quarter and publishes the definition in the same document:

> Contribution = Adjusted Revenue (−) last mile delivery cost (−) platform
> funded discounts (−) payment gateway and COD handling charges (−) customer
> support and appeasement cost (−) customer and restaurant partner refunds (−)
> delivery partner recruitment and onboarding cost (−) other miscellaneous costs

Every line in that subtraction moves with order volume. None of it is fixed
cost, overhead, brand marketing or technology. That is precisely the marginal
cost base a switching value needs.

So `CM_zomato = 10.19% of NOV` (Q1FY27) is read, not assumed, and its confidence
is that of a filing. `FD_FIXED_COST_ADDBACK` survives in `config.py` only to
drive `cm_zomato_from_filings`, which the notebook now uses as a cross check:
the disclosed figure must sit between the Adjusted EBITDA floor (5.63) and the
floor plus a generous 40% add back (18.76). It does.

**This is the single biggest confidence upgrade in the project.** Read the
disclosure before building an estimate of it.

---

## The assumptions that remain

| # | Assumption | Status | Confidence | If it is too high |
|---|---|---|---|---|
| 1 | `alpha`, the cannibalisation rate | Unobservable, reported as a range | n/a | Understates Bistro |
| 2 | `CM_bistro` | **Not estimated.** Reported as a required threshold instead | n/a | n/a |
| 3 | `retention` absent Bistro | Not quantified. `retention = 1` used throughout | Conservative | Understates alpha* |
| 4 | Alpha is measured on order **value**, not orders | Forced by disclosure | Medium | See below |
| 5 | Others segment as a proxy for Bistro scale | Upper bound only | High as a bound | Overstates Bistro |
| 6 | Hand transcription of vector tables | Cross checked, see below | High | Either way |

### 1. The alpha baseline

Unobservable. Justify a range, never a point estimate. `config.ALPHA_BASELINE`
is still `None` because `02_price_positioning.ipynb` has not produced an overlap
share. A baseline picked before the evidence is a guess wearing a decimal point.

The exhibit runs the full 0 to 100% range rather than stopping at 95%, because
the result at `alpha = 1` is the cleanest statement in the deck: the bar
collapses to the marketplace's own margin.

### 2. CM_bistro is not estimated, and that is deliberate

Bistro has no standalone P&L. It sits inside an `Others` segment that also
carries Nugget, Greening India and, from Q1FY27, the community initiatives.
Menu prices have not been sampled, so the order value line of the stack is
empty.

Building a five line stack from benchmarks and presenting a sensitivity range
around it would give the number a false precision. The switching value inverts
cleanly, so the analysis states the bar instead:

```
required CM_bistro = alpha * retention * CM_zomato
```

`data/manual/cm_bistro_components.csv` remains as the template. It raises rather
than defaulting if run half filled, because a silently missing cost line
inflates CM_bistro, inflates alpha*, and flatters the recommendation.

### 3. Retention absent Bistro

The share of cannibalised order value Eternal would actually have kept, given
Swiggy Bolt, Snacc, Zepto Cafe, Toing and Ownly.

Every figure in the deck uses `retention = 1`, which assumes every cannibalised
rupee would have stayed on Zomato. That is the conservative floor and it gives
the highest bar for Bistro. The exhibit shows 75% and 50% lines so the reader
can see what the assumption is worth, but no claim rests on them until H2
produces a defensible range.

Direction: a lower retention lowers the bar, so assuming 1 is the choice that
can only understate Bistro.

### 4. Alpha is measured on order value, not on orders

The lecture defines alpha on orders. This project defines it on order value.

That is forced, not chosen. Eternal has never disclosed food delivery Orders or
AOV in the shareholders' letters, so contribution per order cannot be computed
for the marketplace side. Contribution per rupee of NOV can, and is disclosed
directly.

**The two definitions are not interchangeable.** A Bistro order at a ₹50 to
₹150 price point is much smaller than a restaurant delivery order. If one Bistro
order displaces one whole Zomato order, the value based alpha understates the
damage. If a Bistro purchase displaces part of a customer's Zomato spend, the
value based alpha is right.

Direction: if substitution is order for order rather than rupee for rupee, the
bar in the exhibit is too low and Bistro looks better than it is. State this on
the slide. It is the most criticisable modelling choice in the project.

Closing it needs food delivery AOV, which is not disclosed. A sampled Bistro AOV
plus a food delivery AOV estimate would let the order based version run as a
sensitivity.

### 5. The Others segment as a proxy for Bistro's scale

`others_adj_revenue` is used as an **upper bound** on Bistro, never as Bistro
itself. Others contains Nugget and Greening India as well, and from Q1FY27 the
community initiatives under Eternal General Services Foundation.

This only ever supports statements of the form "Bistro is at most X", which is
the direction the materiality argument needs. Do not use it to estimate Bistro
revenue.

Kitchen counts come from the letter text, not a table: 38 in Q1FY26, about 45 in
Q3FY26, both in two cities. Quarters in between are blank rather than
interpolated.

### 6. Hand transcription of the Annexure A tables

Eternal's Annexure A tables are vector graphics, not text. `pdftotext` returns
the surrounding notes and nothing from the tables themselves, so the panel was
transcribed from rendered page images rather than parsed.

Three controls on that risk.

1. **Overlap cross check.** Each letter reports five trailing quarters. The
   Q1FY26 letter overlaps the Q4FY25 letter on Q1FY25 to Q4FY25 and the Q1FY27
   letter on Q1FY26. Every overlapping figure matched exactly. No restatements.
2. **An arithmetic identity.** Quick commerce discloses NOV, Orders and net AOV
   independently. `NOV / Orders` reproduces the disclosed NAOV to within 2% in
   every quarter. That is asserted in `tests/test_metrics.py` and in notebook 00,
   so a transcription slip in those columns fails the build.
3. **The validation gate.** Any quarter on quarter move outside a plausible band
   is queued for written sign off before the analysis notebooks will run.

### Marginal versus fully loaded cost

Bistro shares rider fleet and delivery infrastructure with Blinkit's dark
stores. The relevant cost is the marginal cost of a Bistro order, not a fully
loaded allocation carrying kitchen buildout and shared overhead. Kitchen
buildout capex answers a different question and belongs in the capital
allocation section.

State the discipline both ways. Every Bistro order clearing its marginal cost
does not mean the kitchen network clears its capex. Marginal cost for marginal
decisions, full cost for the portfolio.

**Kitchen cost is a step function, not a rate.** A kitchen has a throughput
ceiling. The marginal cost of order N is near zero until the kitchen saturates,
then it jumps by a whole kitchen. Capacity is also perishable: a slot unused at
3pm is gone. Management's own Q3FY26 language points the same way, citing
"healthy throughput per outlet" as the sign of product market fit. Utilisation
drives CM_bistro more than any menu price does.

---

## Definitional breaks

| Quarter | Fields | What changed | How handled |
|---|---|---|---|
| Q2FY26 | `qc_revenue`, `consol_adj_revenue` | Blinkit's transition to inventory ownership. Quick commerce revenue jumps from ₹2,400 cr to ₹9,891 cr with NOV up only 27%. | NOV used for every growth comparison and every segment share. `qc_take_rate` is not comparable across this break. |
| Q2FY26 | food delivery `GOV` | Eternal stopped disclosing food delivery GOV | GOV series runs Q3FY23 to Q1FY26, NOV series runs Q4FY24 to Q1FY27. They overlap for six quarters. Never mix them in one growth series. |
| Q2FY25 | Going out | Entertainment ticketing acquisition consolidated from 27 Aug 2024 | Not used in any conclusion. Flagged in the letter's own notes. |

## Validation breaches reviewed

| Quarter | Field | QoQ change | Explanation | Accepted |
|---|---|---|---|---|
| Q4FY25 | `others_adj_ebitda` | −17.0x | Legitimate sign flip on a tiny base. Others adjusted EBITDA moved from +₹1 cr to −₹16 cr as Bistro investment began, against Others revenue of ₹1 cr that quarter, so any absolute swing is a large ratio. Verified against the Q4FY25 letter Annexure A. Not a parse error. | Yes |

`panel.validate()` now carries sign offs forward across re-runs. Before that fix
it rewrote the queue on every run and silently reopened breaches that had
already been explained, which would have trained everyone to ignore the gate.

## Other proxies and estimates

| Quantity | Source | Method | Confidence |
|---|---|---|---|
| Bistro kitchen count | Q1FY26 and Q3FY26 letters, Q&A text | Read from prose, not a table | Medium |
| Bistro price point | Q1FY27 letter, Q3 | Management statement: "INR 50-150 price points" | Medium |
| Bistro upper bound scale | Others segment adjusted revenue | Upper bound only, see item 5 | High as a bound |
| Swiggy contribution margin | Swiggy Q1FY27 letter | Stated against GOV, not NOV | High for Swiggy, not comparable to Eternal's level |

---

## Data we wanted and could not get

Naming these is part of the analysis, not a gap in it.

1. **Bistro menu prices.** The single remaining blocker. Closes H3's magnitude
   and gives the order value line in any CM_bistro estimate. Requires app access
   with a location, so it cannot come from filings.
2. **Food delivery Orders and AOV.** Never disclosed. Their absence forces both
   the value based alpha and the two way growth decomposition.
3. **City level food delivery NOV.** Would enable a real difference in
   differences using Bistro's staged rollout. Not disclosed.
4. **User level order history.** Would make alpha an observation rather than a
   parameter, and the switching value framing would become unnecessary.
5. **Bistro standalone P&L.** Folded into Others alongside Nugget and Greening
   India.

If asked "what would you need to answer this properly?", the answer is item 4.
Item 1 is the answer if the question is restricted to what an outside analyst
can actually obtain.
