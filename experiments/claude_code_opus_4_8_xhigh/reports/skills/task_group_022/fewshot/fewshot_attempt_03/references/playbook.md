# Atlas Commerce Operations — computation playbook

These are the recurring semantics behind Atlas operational-reporting requests.
The **request payload** is authoritative for every number, window, threshold,
and ordering — read it there, never hardcode. This file explains the *concepts*
those payloads refer to so you translate them into correct SQL.

## Discovering the real schema (do this first, every task)

1. `GET /api/schema` and `GET /api/data-dictionary` — canonical table names,
   column names, enum values, and the business meaning of each field. The data
   dictionary is where "effective", "logical", "canonical", "production", and
   "active time" get their precise definitions for this dataset.
2. If those endpoints are unavailable, fall back to
   `python3 scripts/atlas_client.py introspect` (tries `information_schema` /
   `sqlite_master`). The SQL validator may reject system catalogs; if so, keep
   retrying the schema endpoints — a 5xx there is usually the catalog warming
   up, and the client already retries with backoff.
3. Before trusting a filter, **probe distinct values** of the columns you will
   filter on (status enums, tier, region, priority, the production/environment
   flag, currency). Never assume a literal — confirm it exists in the data.

Query only through `POST /api/sql` (read-only). Reserve `POST /api/sql/
transaction` for the one task type that explicitly authorizes a correction.

## Cross-cutting rules (seen in every analytical task)

- **Production scope.** Requests say "production accounts / production
  shipments / PRODUCTION_*". There is a flag (e.g. an `is_production` /
  environment column) — include only production rows. Test/sandbox rows are
  excluded from both numerator and denominator.
- **Cutoff / as-of semantics.** Evaluate state *as of* the stated cutoff.
  Treat request timestamps as **exact UTC boundaries**; honor the stated
  inclusivity (usually inclusive, e.g. `...T23:59:59Z`). A delivery/response/
  resolution that happens after the cutoff has *not* happened for this report.
- **Windows vs cutoffs are different dates.** Membership is usually defined by
  a creation/opened window; status is evaluated at a separate, later cutoff.
  Keep them distinct in your SQL.
- **"Effective" / "canonical" / "logical".** The dataset carries raw source
  values alongside a reconciled canonical value, and refunds/reversals net into
  a single "logical" unit. Compute on the **effective/canonical** value as the
  data dictionary defines it; a later reversal can cancel an earlier refund.
- **Denominators stay whole.** Rates use the full eligible population as the
  denominator (e.g. "incomplete eligible orders remain in the denominator").
  Don't silently drop rows that lack a numerator event.
- **Rounding.** Round only final reported rates/amounts; sort and tie-break on
  unrounded values. (See output-contract.md.)
- **Tie-broken ordering.** Every "worst/top N" has explicit tie-breaks — apply
  all keys in order, then truncate to N.
- **Tier classification is first-match, top-down.** Evaluate the status/risk
  bands in listed order and take the first whose condition holds; the final
  band is the catch-all ("otherwise" / "all other outcomes"). Read the exact
  numeric thresholds and comparison operators (`>=` vs `>`, `<` vs `<=`) from
  the payload.

## Money / FX (refund-style tasks)

- Convert every amount to the reporting currency (USD) using the **daily**
  `fx_rates.usd_per_unit` for that row's `service_date` **and** its row
  currency. Value an order's gross at the rate for the settled refund's service
  date when comparing refund-vs-gross.
- "Effective settled logical refund" = a settled refund, netted against any
  linked reversals. Count distinct logical refunds and distinct linked
  reversals separately if the template asks for both.
- Leakage candidates: apply each `candidate_if_any` clause exactly (e.g. net
  refund USD > gross order USD, OR ≥2 unreversed settled refunds sharing a
  normalized reason code). Output the union, ordered `order_id` ascending.
- `net_refund_amount_usd` and reason rankings are on **effective net** values.

## Support active-time tasks

- The clock basis is **support active time** (elapsed minus paused/waiting
  time), not wall-clock — use the field the data dictionary designates.
- First-response breach: active time to first agent response exceeds the
  priority threshold; an unresponded case uses active elapsed time **at the
  cutoff**.
- Resolution breach: active time to resolution exceeds the priority threshold;
  an unresolved/active case uses active elapsed time at the cutoff.
- `open_at_cutoff` includes OPEN and REOPENED active states; `reopened_at_cutoff`
  is the reopened subset of those.
- Severe active case: open/reopened at cutoff AND priority in the specified set
  (e.g. URGENT/HIGH) AND beyond the resolution active-time threshold.
- Median: across cases resolved at the cutoff; for an even count, average the
  two central values. Round to the template's precision.
- Thresholds are per-priority — join each case to its priority's SLA row.

## Warehouse productivity tasks

- Units/hour per employee = total completed production units ÷ total productive
  minutes on those completed units × 60. Rank by units/hour desc, then
  employee_id asc; report the top employee's units/hour at the template's
  precision.
- completion_rate = completed eligible tasks ÷ eligible tasks;
  rework_rate = rework tasks ÷ eligible tasks (same denominator).
- Delayed high-priority task = HIGH or URGENT, `due_at` strictly before the
  cutoff, not completed by the cutoff. List task_ids ascending.
- Lowest-performing team = lowest completion_rate, tie-break team_id asc.
- Facility status: first-match band on completion_rate/rework_rate.

## Correction / mutation tasks (the controlled-write type)

Only when the request explicitly authorizes a correction (it will supply a
`reason_code`, `actor`, `audit_id`, `correction_key`, `corrected_at`, and a
success rule). Steps:

1. **Locate the single contradiction.** Find the row where the raw/source
   status and the canonical status disagree in the way described (there is
   exactly one in scope). Report `scan_row_id`/`shipment_id`/entity ids as
   stored.
2. **Compute the pre-correction backlog** at the cutoff (e.g. shipments whose
   effective final carrier status is not DELIVERED).
3. **Apply the minimal canonical correction** via `POST /api/sql/transaction`:
   update **only** the one canonical field (e.g. `canonical_status`). Never
   touch raw source values, source-identity fields, or unrelated rows. In the
   same transaction, insert **exactly one** audit row carrying the provided
   `audit_id`, `correction_key`, `reason_code`, `actor`, `corrected_at`,
   entity/source ids, and old/new values.
   - Confirm the transaction request shape from the schema/data dictionary
     before sending (list of SQL strings vs objects with params). Do a dry read
     first; keep the write minimal and idempotent-safe.
4. **Verify post-change**: a follow-up `SELECT` confirms the canonical value is
   now corrected, and that exactly one business row and one audit row changed.
5. **Report** pre/post backlog counts, their delta, the post-correction
   delivered count, the audit record, and set `correction_status` to `APPLIED`
   **only** if the success rule is fully satisfied; otherwise `NOT_APPLIED`
   with the values actually observed. `GET /api/correction-audit` shows the
   committed audit rows for confirmation.

Do **not** run any mutation for the purely analytical task types — those
requests state "analytical only; do not change workplace data."
