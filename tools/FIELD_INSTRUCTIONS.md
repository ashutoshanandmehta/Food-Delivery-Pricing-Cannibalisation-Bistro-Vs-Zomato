# Menu price collection: field instructions

Read this fully once before you start. Budget **90 minutes per city**.

**Your job is screenshots.** You are not typing prices into anything. Capture
clean screenshots in the right order and send them across. Someone else does the
transcription at a desk, carefully, where a mistake is cheap.

The one thing that ruins the dataset is a screenshot where the price is legible
but you cannot tell which item it belongs to, or which city it came from. Every
rule below exists to prevent exactly that.

The work comes in two parts.

* **Part A. The three small apps.** Bistro, Zepto Cafe, SNACC. About 30 minutes.
* **Part B. Zomato and Swiggy.** About 60 minutes.

**Do Part A first, always.** Part B may be cancelled at short notice, because we
are testing whether we can pull that half automatically instead. Do not start
Part B without checking that it is still on.

---

## 0. Before you leave

**Phone prep**

* At least **2 GB free storage**. You will take 200 to 300 screenshots.
* Battery above 80%, or carry a power bank.
* All five apps installed and updated.
* Turn **off** dark mode. Light screenshots are much easier to read.
* Silence notifications. A banner across a price costs you that row.

**Settings you fix once and never change during the session**

| Setting | What to do |
|---|---|
| Delivery address | One pincode for the whole session. Save it in all five apps before you start. |
| Date and time | All five apps on the **same day**, inside the **same two hour window**. |
| Sort and filters | **Never touch them.** Default order only. No sort by price, no veg filter, no offers filter. |
| Coupons | Apply none. We want the price before promotions. |

**Write this down now. Send it with your screenshots.**

* Your name
* City and exact pincode
* Date, session start time, session end time
* For each of the five apps: **are you logged in, and do you have a paid
  membership?** Zomato Gold, Swiggy One, Zepto Pass, Blinkit membership. This
  changes prices and fees, so we must know. If you can collect logged out, do
  that and say so.

If two of you are covering the same city, **split by app, not by item.** Two
people pricing the same item under different conditions is the error we cannot
detect afterwards.

---

## 1. Do a pilot first. Three dishes, then stop.

Before the full run, do **three dishes end to end** across all five apps and send
them. Wait for a reply confirming the format is right.

This takes ten minutes and it is the cheapest error check available. If you have
misread an instruction, we find out after three dishes instead of after two
hours.

---

# PART A. The small apps

Bistro (inside the Blinkit app), Zepto Cafe, SNACC. About 10 minutes each.

**These decide the whole study.** Their menus define which dishes we look up
later, so nothing here is optional.

For each of the three apps:

1. Open it and confirm the saved address is your session pincode.
2. **Screenshot the delivery address or pincode.** First file, every app, no
   exceptions. This is your proof of location.
3. Go to the food menu.
4. Screenshot the **entire menu, top to bottom**, section by section.
   * Scroll by about **two thirds of a screen** between shots, never a full
     screen. Consecutive screenshots must **overlap by two or three items** so
     nothing is lost at the seam.
   * Every item name and its price must be fully visible in at least one shot.
     If a name is cut off at the edge, retake it.
   * Include the section headers such as Snacks, Beverages, Meals. We need those
     for the category variable.
5. Add one mid priced item to the cart, go to checkout, and **screenshot the full
   fee breakdown**: delivery fee, platform fee, taxes, handling. One per app is
   enough. Then empty the cart.
6. If the app does not serve your pincode, or a whole section is unavailable,
   screenshot that message. A negative result is data.

## A2. Write the dish list

This is the only typing you do, and it is the bridge into Part B.

Scroll back through your own Part A screenshots and type out **just the dish
names**. No prices. Notes app or paper, either is fine.

* Combine all three apps into one list.
* Remove exact duplicates. If Bistro and SNACC both sell "Cold Coffee", it is
  one entry.
* Keep near duplicates separate. "Cold Coffee" and "Filter Coffee" are two.

**If your combined list is longer than 50 dishes, stop and send it to us before
starting Part B.** Do not choose which ones to drop. We will make that selection
centrally and in a way we can defend in writing. Choosing in the field, dish by
dish, is exactly the kind of decision that quietly biases a result.

---

# PART B. Zomato and Swiggy

**Check this part is still on before you start it.**

About 30 minutes per app. You are looking up the same dishes from your Part A
list.

1. Open the app. Confirm the address. **Screenshot the address or pincode.**
2. Take the dishes from your list one at a time. For each dish:
   * Type the dish name into the app's **search**.
   * **Change nothing.** No sort, no filter, no location tweak.
   * Screenshot the top of the results so the **first five results** are visible,
     each showing the **dish name, the restaurant name and the price**.
   * **The search box must be visible in the shot.** This is the single most
     important rule in Part B. Without it we cannot verify that those five
     results belong to that dish.
   * If five do not fit on one screen, take a second overlapping screenshot.
     Two shots for one dish is fine. Missing the fifth result is not.
3. If a dish returns fewer than five results, screenshot what it returns. Do not
   scroll on, and do not broaden or reword the search to reach five.
4. If a dish returns nothing, screenshot the empty result. That is a real finding.
5. Do the checkout fee screenshot once, as in step A5.

---

## 2. How to take the screenshot

* **Do not crop.** Full screen every time. The status bar carries the clock,
  which we use to reconstruct your sequence.
* **Do not zoom.** Default text size.
* Portrait only.
* One tap, one shot. **No scrolling or long screenshots.** They compress the
  image and the prices go soft.
* Glance at each one. A blurry price is a lost row.

---

## 3. Sending the files

One folder per app, named exactly:

```
DelhiNCR_Bistro          Bangalore_Bistro
DelhiNCR_ZeptoCafe       Bangalore_ZeptoCafe
DelhiNCR_SNACC           Bangalore_SNACC
DelhiNCR_Zomato          Bangalore_Zomato
DelhiNCR_Swiggy          Bangalore_Swiggy
```

**Do not rename the individual files.** The phone's own names carry the
timestamps and hold them in order.

Upload the folders to the shared drive. In the same message send your session
note from section 0, and your dish list from A2.

---

## 4. Edge cases

| What you hit | What to do |
|---|---|
| Item listed but greyed out or "currently unavailable" | Screenshot it anyway. We record it as unavailable. |
| Two sizes of one item, regular and large | Capture both. Do not pick one. |
| Item sold only in a combo or meal box | Screenshot it and write "combo" against it in your list. We exclude combos but we count how many. |
| Price struck through with a lower one beside it | That screenshot must show **both** numbers. Never capture only the discounted price. |
| App asks you to log in partway | Log in, then note in your session note exactly where that happened. |
| Address resets itself | Set it back, screenshot the address again, carry on, and note it. |
| Surge or peak pricing banner appears | Screenshot the banner and note the time. |
| You run past your two hour window | Stop. Note where you stopped. Do not finish the next day in the same file. |

**When in doubt, take the screenshot.** An extra one costs two seconds. A missing
one costs a return trip on a different day, and a different day is a different
dataset.

---

## 5. Before you leave the pincode, check all six

* [ ] Every app has an address or pincode screenshot as its first file.
* [ ] Every app has a checkout fee screenshot.
* [ ] Part A covers every menu section, top to bottom, with overlap between shots.
* [ ] Every Part B search screenshot shows the search box.
* [ ] Dish list written out and saved.
* [ ] Session note complete: name, city, pincode, date, time window, and login
      and membership status for all five apps.

If any box is unticked, fix it before you leave. Coming back later means a
different day, and that breaks the comparison.

---

## Why the fuss, in two lines

We are testing whether 10 minute owned kitchen services genuinely price below
restaurant marketplaces **for the same dish**. That only works if the same dish
is identified across all five apps, at the same location, in the same hour, under
the same account conditions. Every rule above protects one of those four.

Questions while you are in the field, ask immediately rather than guessing. A
five minute delay is cheaper than a rerun.
