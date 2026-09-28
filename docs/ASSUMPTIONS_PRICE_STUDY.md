# Assumptions: the Bistro menu price study (MBA753)

Every assumption below is stated with the direction it pushes the result. The
hypothesis is that Bistro prices a dish below the restaurant marketplaces, so the
expected sign on `OwnedKitchen` is negative. "Favours" means the assumption makes
beta more negative than the truth. "Against" means it makes beta less negative.

An assumption that favours the hypothesis is the dangerous kind. Those are listed
first.

---

## A. Price and discounts

Discounting on the marketplaces is not occasional. It is the normal state.

* **84 of 89 Zomato restaurants** in the sample carry at least one offer.
* **126 of 142 Swiggy restaurants** carry at least one offer.
* 634 offer strings were transcribed, 91 of them distinct.

The offers come in three shapes and only one of them can be attached to a dish.

| Shape | Example | Count | Attributable to one dish? |
|---|---|---|---|
| Order threshold | `Flat ₹150 OFF above ₹599` | 207 | **No.** Depends on basket value |
| Capped percentage | `70% off upto ₹140` | 219 | **No.** Cap binds at a basket size |
| Item strikethrough | `₹359` struck to `₹229` | 60 | Yes |

### A1. The reference basket is one item

**Assumed.** Each observation is a single dish bought alone. No order level or
restaurant level offer is applied to any price on any platform.

**Why.** A threshold offer is a function of basket value, not of dish price. To
allocate `Flat ₹150 OFF above ₹599` onto a ₹149 samosa you must first assume what
else is in the cart. Any allocation rule would be an invented number carrying the
result. Dropping the offers is the only choice that adds no information we do not
have.

**What it costs.** These offers are large. Where the basket lands exactly on the
threshold the implied discount runs:

| Platform | Offers parsed | Median discount at threshold | Max |
|---|---|---|---|
| Zomato | 46 | 27% | 70% |
| Swiggy | 17 | 40% | 63% |

Thresholds run ₹149 to ₹1999 with a median of ₹199. The capped percentage offers
have a median headline rate of 60% and a median cap of ₹120, so the full rate
applies on baskets below about ₹200.

**Direction: favours the hypothesis, and this is the largest single bias in the
study.** Only the marketplaces run these offers. Ignoring them overstates the
marketplace price at checkout.

**Size, honestly.** A single item order mostly does not trigger them anyway.

| Threshold | Share of Bistro items clearing it alone | Share of marketplace items |
|---|---|---|
| ₹149 | 51% | 65% |
| ₹199 | 18% | 44% |
| ₹399 | 2% | 9% |
| ₹599 | 1% | 3% |

So at a one item basket the assumption is close to true for Bistro and wrong for
roughly 44% of marketplace rows. The bias is real but bounded. It is not the case
that every marketplace price should be marked down by 33%.

### A2. Beta is a menu price claim, not a checkout claim

**Assumed.** Three price concepts are kept separate and only the first is
estimated.

| Concept | Definition | Where it appears |
|---|---|---|
| Menu list price | what the app shows on the card | **the main specification** |
| Item effective price | list minus item strikethrough | robustness specification |
| Delivered price | effective, plus fees, minus order discounts | discussed, never estimated |

**Why.** The delivered price is basket dependent on both sides. Estimating it
would mean assuming a basket, which is A1 again.

**Direction: none on beta.** This is a scope statement. The paper may not claim
Bistro is cheaper at checkout on the strength of beta alone.

### A3. Item strikethroughs are used, and they are roughly symmetric

**Assumed.** Where a card shows a struck price the lower figure is the effective
price. This is applied identically on all three platforms.

Strikethrough incidence is close to even, which is the useful part.

| Platform | Rows with a strikethrough | Mean depth |
|---|---|---|
| Zomato | 25 of 218 (11%) | 36% |
| Swiggy | 35 of 376 (9%) | 31% |
| Bistro | 8 of 87 (9%) | 27% |

**Direction: against the hypothesis, mildly.** Marketplaces discount at a similar
frequency but slightly deeper, so the effective price specification should move
beta a little toward zero. If it moves a lot, something else is wrong.

This also settles a claim worth stating carefully. Bistro discounting is rare on
frequency and not shallow on depth. "Bistro does not discount" is false.

### A4. No membership on any platform

**Assumed.** No Zomato Gold and no Swiggy One. The collector confirmed no active
membership on the accounts used.

**Why.** Membership changes the fee stack, not the menu price.

**Direction: favours the hypothesis on the fee comparison only.** The Zomato fee
wedge of 77% is the non member figure. A Gold member sees a smaller wedge. Beta
is unaffected.

### A5. GST differences out

**Assumed.** Menu prices are shown exclusive of GST on all three platforms, and
the same rate applies to Bistro and to a restaurant listing.

**Why.** Both are prepared food sold for delivery.

**Direction: none, if true.** If Bistro's owned kitchen attracts a different rate
the log difference carries a constant that beta would absorb. Worth one check
against a Bistro invoice before the paper is final.

### A6. Prices are a single snapshot

**Assumed.** Prices captured on 1 September 2026 between 15:40 and 19:05 are
representative. No surge pricing, no time of day menu, no weekday effect.

**Direction: ambiguous.** Collection ran through the evening peak on the
marketplaces and the mid afternoon lull on Bistro, which is a real difference and
not one we can sign.

---

## B. Quantity and normalisation

### B1. An unstated quantity means one serving

**Assumed.** Where a listing states no quantity and the dish basis is `serving`,
units are set to 1.

**This is the widest assumption in the study. 173 of 261 rows rest on it.**

**Why.** Restaurants do not routinely state portion size. The alternative is
dropping two thirds of the panel.

**Direction: ambiguous, and testable.** It is signed only if one platform states
quantity more often than the other. The `qty_source` field carries the answer, and
the paper reports beta on the stated only subsample of 70 rows beside the full
panel.

### B2. Quantity is never inferred from price

**Assumed.** Imputation uses the same restaurant across platforms first, then the
dish median. It never uses the price.

**Why.** Two real listings, both 300ml lemon iced tea: Chaayos ₹209, Theobroma ₹99.
The same volume at 2.1 times the price. Inferring volume from price would have
assigned Theobroma a smaller cup and manufactured the result.

**Direction: conservative.** Costs rows, invents nothing.

### B3. A volume dish with no stated volume is dropped, never defaulted

**Assumed.** Where the basis is millilitres and no volume is stated the row is
excluded. Seven rows were lost this way.

**Why.** The default of 1 ml turned a marketplace can into ₹66 per millilitre
against Bistro at ₹0.15, a factor of 440. The basis is now resolved from both
sides, so a dish where fewer than three marketplace listings state a volume falls
back to `serving`.

**Direction: conservative.**

### B4. One flagged dish leaves the per unit specification

**Assumed.** Where marketplace listings for a dish state piece counts spanning
more than a factor of two, "one serving" is not a comparable unit. Idli Sambar is
flagged on this rule. Listings ran 2, 3, 4 and 12 pieces at ₹14.58 to ₹78.57 each.

It stays in the raw specification and leaves the normalised one. 28 dishes and 250
rows remain per unit eligible.

**Direction: conservative.**

---

## C. Dish identity

### C1. The typed search term links a screen to a Bistro dish

**Assumed.** The term the collector typed, or the "Best in *dish*" header,
identifies which Bistro dish the screen is evidence about.

Three searches collapsed several Bistro products into one query. Tea and Chai each
cover three Bistro chais, Chaat covers three chaats. Those 30 rows are excluded
rather than arbitrarily assigned.

### C2. Token rules decide whether a listing is the same dish

**Assumed.** Required tokens, reject tokens and a bulk or combo veto, applied
identically by machine so a second coder reproduces them exactly.

**Known weakness.** The rules catch wrong ingredients and miss wrong **formats**.
Masala Dosa Pops are ten snack bites and the search returned full dosas. Mini
idlis are not idlis. `Hot Idli (2 Nos) + Medhu Vadai(1)` is a combo the token rule
let through. Three were rejected by hand.

**Direction: ambiguous and unresolved.** A format mismatch can run either way. This
needs an eyeball pass over the 239 matched rows before the regressions are final.

### C3. Bistro's menu is the sampling frame

**Assumed.** The 29 dishes are the ones Bistro chose to sell.

**Why it matters more than it looks.** Bistro's assortment is not random. An owned
kitchen stocks dishes it can produce cheaply at volume. Beta is therefore the
price gap **on Bistro's chosen assortment**, not on Indian food delivery generally.

**Direction: favours the hypothesis, structurally.** This limit cannot be removed
by better data. It has to be stated in the conclusion.

---

## D. Sampling

### D1. One city, one address, one day, one collector

All three platforms captured from the same Connaught Place address on 1 September
2026. No claim of national or cross city validity.

### D2. Capture method differs by platform

Zomato was captured by tapping into each restaurant and reading the "Best in
*dish*" block. Swiggy was captured from the Dishes result list. These select
different restaurants into the top five.

**Direction: ambiguous.** Test it. Estimate the Zomato and Swiggy coefficients
separately. If they differ by more than the Bistro gap, the method is driving more
than the platform.

### D3. Sponsored placement is flagged, not removed

36% of Swiggy rows carry an Ad badge. Zomato showed none, because tapping into a
restaurant bypasses the sponsored list.

**Direction: ambiguous.** Run the model with and without.

### D4. Screenshot count does not drive the estimate

**Assumed.** Each row is weighted by one over the number of rows in its dish and
platform cell, so a dish that happened to yield 12 Swiggy cards does not outvote
one that yielded 4.

---

## E. Identification

### E1. Item fixed effects hold the dish constant

Beta is identified from variation within a dish across platforms. Any dish level
difference in ingredients, brand or category is absorbed.

**What is not absorbed.** Anything that varies by platform within a dish. Kitchen
quality, portion generosity beyond the stated quantity, and packaging are the
obvious ones. Beta is a price gap and not a value for money gap.

### E2. Errors cluster by dish

Quotes for the same dish are correlated. With 29 clusters the standard errors are
in the range where the cluster count itself is a concern, so the nonparametric
result is reported alongside.

### E3. The rank test carries the headline

Bistro's mean percentile rank inside each dish's marketplace price distribution is
0.248 against a null of 0.50. Cheaper in 24 of 30 dishes. Wilcoxon p = 0.0003.

**Why this leads.** It survives every assumption in section B. It uses only the
ordering of prices within a dish, so no quantity decision can move it. Beta is the
more fragile number and should be read second.

---

## Summary: which way the thumb is on the scale

| Assumption | Direction |
|---|---|
| A1 order and restaurant discounts ignored | **favours** |
| A4 no membership | favours, fees only |
| C3 Bistro picks its own assortment | **favours** |
| A3 item strikethroughs used | against |
| B2, B3, B4 conservative quantity rules | against |
| A6, B1, C2, D2, D3 | ambiguous, all testable |

Two assumptions favour the hypothesis and neither can be removed with the data in
hand. Both belong in the limitations, stated in these terms rather than softened.
