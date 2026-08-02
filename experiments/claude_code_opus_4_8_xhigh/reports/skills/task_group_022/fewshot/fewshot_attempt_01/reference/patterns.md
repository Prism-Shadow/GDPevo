# Recurring analytical patterns

These idioms recur across Atlas Ops reporting requests (fulfillment scorecards,
refund/settlement reconciliation, warehouse productivity, support-health
reviews). Every request restates its own exact definitions — always follow the
request payload's wording; this file only tells you what to look for and how the
pieces usually fit. Map each term to real columns via `/api/schema` and
`/api/data-dictionary` before writing SQL; never hard-code table/column names.

## 1. Eligibility / cohort filtering (do this first)

Requests define a population before any metric. Common gates, all ANDed:
- **Production only.** Every task restricts to production records — look in the
  data dictionary for an environment / `is_production` / account-population
  flag and exclude test/sandbox rows.
- **Segment / tier / region / warehouse / account scope** (e.g. a tier such as
  GOLD, a segment such as ENTERPRISE, a region list, a specific warehouse id).
- **A time window** on the relevant business date (order created, task created,
  case opened, refund/reversal service date). Boundaries are **inclusive UTC**
  unless the request says otherwise; treat the given timestamps as exact bounds.
- **Membership predicates** (e.g. "has an effective scan in the named batch at
  or before cutoff", "has at least one effective settled logical refund").

Compute and sanity-check the eligible count first; most other numbers are
subsets of it, and rate denominators are usually "eligible …" not "all rows".

## 2. Cutoff / "as of" state

A `cutoff_at` / `as_of_cutoff` / `state_cutoff_at` freezes the world:
- Only count events (deliveries, responses, resolutions, corrections) **at or
  before** the cutoff. A delivery/resolution after the cutoff does **not** count
  as done as-of the cutoff.
- Still-open items are measured by **elapsed time at the cutoff** (e.g. an
  unresponded case's first-response clock, or an undelivered shipment's promise
  breach) — not left null.
- "Complete/delivered/resolved by the cutoff", "open at cutoff", and
  "reopened at cutoff" are distinct states; read each definition precisely
  (e.g. an order may require **every** physical shipment delivered by cutoff and
  **at least one** shipment to exist at all).

## 3. Raw vs. canonical / "effective" values

The domain separates **raw source** values from **canonical/corrected**
("effective") values, and a correction audit can override a field.
- "Effective"/"canonical" = the value after applying approved corrections;
  "raw"/"source" = the untouched imported value. Use whichever the definition
  names — final business status usually means the canonical value.
- "Effective settled logical refund" style terms imply **deduping to a logical
  unit** and **netting reversals** (a refund whose linked reversal settled is
  no longer effective). Determine "settled" and "reversed" from the dictionary.
- The single contradiction targeted by a correction task is a raw-vs-canonical
  mismatch on one row (see `correction-procedure.md`).

## 4. Money / FX normalization

Reconciliations report in a single currency (usually USD):
- Convert each row using the **daily FX rate for that row's own service date and
  currency** (e.g. `fx_rates.usd_per_unit`), not a single global rate. When
  comparing a refund to an order's gross, value the order gross at the rate/date
  the request specifies for the comparison.
- Net refund = effective settled refunds minus effective linked reversals, per
  the request. Round money only at final display (typically 2 decimals).

## 5. Rates, rounding, and ordering

- **Rate = qualifying subset / stated denominator.** The denominator is whatever
  the request names ("all eligible orders", "eligible cases") — incomplete/failed
  items usually stay in the denominator.
- **Round only final reported values** to the stated precision (`multipleOf` /
  `decimal_places` in the template). Keep full precision for intermediate math,
  ordering, and tie-breaks — e.g. "worst two regions by **unrounded** rate".
- **Multi-key sorts:** apply the primary key, then each tie-break in order,
  ending with an id ascending. "Worst/lowest N" = sort ascending and take N;
  "top N" = sort descending and take N. Reproduce the request's key list exactly.
- **Id-list outputs:** sort ascending, keep unique, and match the template's id
  `pattern` (e.g. `^ORD-[0-9]{6}$`). Emit the full list unless a size is fixed.

## 6. Medians and other aggregates

- **Median:** sort the qualifying values; odd count → middle value; **even count
  → average of the two central values**. Confirm the qualifying set (e.g. "cases
  resolved at the cutoff") before taking the median.
- **Per-entity productivity** (e.g. units per hour) usually divides a summed
  numerator by a summed denominator across the entity's qualifying rows, then
  scales (×60 for per-minute→per-hour). Sum-then-divide, not average-of-ratios.

## 7. Status / risk classification ladders

Requests end with a tiered status (e.g. HEALTHY/WATCH/CRITICAL,
STABLE/PRESSURED/AT_RISK, LOW/MODERATE/HIGH, CONTROLLED/ELEVATED/SEVERE):
- Each tier is a compound condition on the computed rates/counts. Evaluate
  **top-down and stop at the first satisfied tier**; the last tier is the
  catch-all ("otherwise" / "all other outcomes").
- Use the same rate definitions (and denominators) the request specified above;
  compare against the exact thresholds (`>=`, `<`, `below`) as written.

## Working method

1. Confirm the eligible population count with one query.
2. Derive each required output as its own query or CTE, checked against the
   population.
3. Do rounding/ordering last, in code, from unrounded query results.
4. Cross-check internal consistency (subset counts ≤ population; rates within
   [0,1]; array sizes match `minItems/maxItems`).
