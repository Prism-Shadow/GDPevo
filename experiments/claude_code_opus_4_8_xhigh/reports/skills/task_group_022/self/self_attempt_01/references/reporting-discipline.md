# Reporting discipline — cross-cutting computation rules

These are the recurring failure points across Atlas reporting tasks. The specific numbers,
window dates, and thresholds always come from the task's `*_request.json`; the *method* below is
constant.

## Time boundaries
- Treat every timestamp in the request as an **exact UTC boundary**. Honor the declared
  inclusivity (`inclusive`, `INCLUSIVE`, `boundary: inclusive`) of window start and end.
- Distinguish the **creation/opening window** (which rows are eligible) from the
  **cutoff / `as_of`** (the point at which state is evaluated: complete, delivered, resolved,
  open/active, backlog). They are usually different timestamps.

## Cohort / eligibility gates
Apply every scope filter before computing any metric, exactly as written:
- population = production (exclude test/non-production),
- account tier / segment / region,
- campaign or batch attribution,
- "created / opened during the active window",
- entity-type membership (e.g. "has an effective scan in the named batch at/before cutoff").
An entity that fails any gate is out of the cohort entirely — it is not a zero, it is absent.

## Effective / canonical vs raw
When a row carries both a raw source value and a canonical/effective value, business metrics use
the **effective/canonical** value. Raw values are for reconciliation and audit only and must not
be mutated during analytical work.

## Denominators
Rates use the **full eligible population** as denominator unless the policy says otherwise:
- incomplete/unfinished members stay in the denominator (they are failures, not exclusions);
- an unresponded or still-active case contributes its **active-elapsed-time at the cutoff** to
  breach checks rather than being skipped;
- read the policy's named `rate_denominator` / `candidate_rate_denominator` and use exactly that.

## Rounding
- Round **only final reported values**, to the exact decimals stated (`multipleOf 0.0001` → 4 dp;
  `decimal_places: 2` / `x-precision: 2` → 2 dp; money nets → 2 dp).
- Use **unrounded** values for all ordering, tie-breaks, and threshold comparisons. Rounding
  before comparison changes results and is wrong.

## Ordering, tie-breaks, and list sizing
- Implement each sort key in the stated order (e.g. "rate ascending, then region ascending";
  "severe count desc, breach count desc, account id asc").
- Sort on the unrounded metric even when the reported field is rounded.
- Cut to the exact `minItems`/`maxItems`. Deduplicate when `uniqueItems`. Match every string
  `pattern` (IDs like `^ORD-[0-9]{6}$`, `^ACC-[0-9]{4}$`, `^CASE-[0-9]{6}$`).

## Status / risk classification
- Tiers are evaluated **top-down; first full match wins** (e.g. HEALTHY → WATCH → CRITICAL,
  STABLE → PRESSURED → AT_RISK, CONTROLLED → ELEVATED → SEVERE, LOW → MODERATE → HIGH).
- A tier's condition is a conjunction of *all* its stated sub-conditions (both a rate ceiling and
  a count/amount ceiling, etc.). If any sub-condition fails, fall through to the next tier.
- Compute each rate against the denominator the policy names.

## Aggregations with edges
- **Median:** sort the values; for an odd count take the middle; for an **even count average the
  two central values**. Round only at output.
- **Per-hour / per-unit rates:** follow the exact formula (e.g. completed units ÷ productive
  minutes × 60), not an approximation.
- **Money / FX:** convert each refund/reversal/gross row with the **daily rate for that row's
  service_date and currency**, aggregate in the reporting currency, subtract linked reversals as
  defined, and round the net only at the end.

## Internal consistency checks before emitting
- complete + incomplete = eligible; subset counts ≤ parent counts.
- Every count is ≥ 0; every rate is within its schema `[minimum, maximum]`.
- Array members satisfy their id pattern and the arrays are correctly ordered and sized.
- pre/post deltas equal (post − pre) where the schema defines a delta.
