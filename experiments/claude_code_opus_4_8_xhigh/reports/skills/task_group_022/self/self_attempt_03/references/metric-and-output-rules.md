# Metric & output checklist

Reusable rules distilled from the Atlas Commerce Operations request family
(fulfillment scorecard, refund/FX reconciliation, carrier-quality correction,
warehouse productivity, support-health). Consult while building queries and
before writing `answer.json`.

## Precedence & contract

- Request payload = business truth (definitions, scope, rounding, thresholds).
  `prompt.txt` = framing only. `answer_template.json` = exact output shape.
- `additionalProperties:false` → emit only the `required` keys, nothing extra.
- Field-level constraints to honor literally: `enum` spellings, ID `pattern`
  (e.g. `^ORD-[0-9]{6}$`, `^ACC-[0-9]{4}$`, `^CASE-[0-9]{6}$`), array
  `minItems`/`maxItems`, and rounding via `multipleOf` / `decimal_places` /
  `precision` / `x-precision`.

## Cohort / eligibility

- Combine every filter: production-only, time window (exact UTC, stated
  inclusivity), as-of cutoff, and membership predicate (segment/region/tier/
  campaign/batch).
- Evaluate all states **as of the cutoff**; ignore events after it.
- Prefer the **canonical/effective** column over raw when both exist.
- Sanity identity: `eligible == passing + failing` (e.g. eligible = complete +
  incomplete). If it doesn't hold, the cohort filter is wrong.

## Rounding & precision

- Compute everything **unrounded**; round **only final reported values** to the
  stated decimals. Ordering, tie-breaks, and threshold tests use unrounded values.
- Rate fields commonly want 4 dp; money 2 dp; hours 2 dp; units-per-hour 2 dp.

## Specific metric shapes seen

- **On-time / completion rate**: qualifying orders ÷ *all* eligible orders;
  incomplete/failing stay in the denominator.
- **Units per hour**: Σ(completed units) ÷ Σ(productive minutes on those units)
  × 60 — sum then divide; never average per-row ratios.
- **Median active resolution hours**: sort resolved-case active times; even count
  → mean of the two central values.
- **FX / net refund USD**: convert each refund/reversal row at the daily
  `usd_per_unit` for that row's service_date & currency; net = settled refunds −
  linked reversals; compare an order's refund vs its gross order value both in
  USD before flagging leakage; round total to 2 dp.
- **Breach counts (active-clock SLAs)**: compare active-time-to-event against the
  priority threshold; for an unresolved/active case use active-elapsed-time at the
  cutoff.
- **Severe exception / severe active**: apply the exact compound predicate from
  the request (e.g. incomplete & cutoff > promise + 24h, or delivered > promise +
  24h; or open-at-cutoff & URGENT/HIGH & beyond resolution threshold).

## Ranking

- Sort on unrounded metrics using the full key list in order, ending with the id
  tie-break (usually ascending). Return exactly `minItems == maxItems` entries.
- "worst" = ascending metric; "top" = descending metric — read the request's
  direction, don't assume.

## Exact ID lists

- Derive from the same predicate as the corresponding count; unique; sorted as
  specified; each id must match the template regex.

## Tiered status

- Ordered best→worst; assign the first tier whose condition holds; last tier is
  the catch-all. Watch `>=`/"at least" (inclusive) vs `<`/"below" (strict).
- Rates in status conditions use the request's stated denominator (e.g.
  severe-rate = severe ÷ eligible).

## Correction / mutation (transaction) tasks

- Change the single approved **canonical** field only; leave raw/source-identity/
  unrelated rows untouched.
- Use request-supplied audit fields; confirm one business row + one audit row +
  post-change value → `APPLIED`, else `NOT_APPLIED` with observed values.
- Report pre- and post-correction metrics; `backlog_delta = post − pre`.

## SQL service reminders

- `POST /api/sql` `{"sql": "..."}` → `{columns, rows, row_count, truncated}`.
  Check `truncated`. SQLite dialect. Introspection & writes are rejected here.
- `POST /api/sql/transaction` for approved mutations only.
- `GET /api/correction-audit` reads audit rows.
- Retry transient `{"error":"service error"}` on the GET endpoints.

## Final pass before writing answer.json

1. Object validates against `answer_template.json` (keys, types, enums, patterns,
   array sizes, decimals).
2. Each headline number re-derived by an independent query.
3. Identity checks hold (eligible = pass + fail; counts ≤ eligible).
4. List orderings and sizes match the contract exactly.
5. File contains only the JSON object — no prose, no markdown fences.
