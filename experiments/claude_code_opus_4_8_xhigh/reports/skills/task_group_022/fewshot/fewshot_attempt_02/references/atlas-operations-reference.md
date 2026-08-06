# Atlas Commerce Operations — API mechanics & data-model semantics

Companion to `SKILL.md`. Section 1 is the wire contract for the workplace service.
Section 2 is the recurring business semantics that determine whether the numbers are right.

---

## 1. The workplace service (API contract)

`environment_access.md` in the task gives the **base URL** and a **bearer token**. Read them
from that file every time; never reuse a token or URL from a prior task. Send
`Authorization: Bearer <token>` on every request. The server is a plain HTTP/1.0 service;
match documented paths exactly (a stray query string can make it return `not found` or
mis-parse auth).

### Documented endpoints
- `GET  /api/schema` — table/column structure.
- `GET  /api/data-dictionary` — field meanings, flags, and relationships. **Start here.**
- `GET  /api/correction-audit` — the correction audit view (read).
- `POST /api/sql` — read-only analysis queries.
- `POST /api/sql/transaction` — controlled write transaction (corrections only).

### `POST /api/sql`
- Request body: `{"sql": "<one statement>"}`. The key **must** be `sql` (`query` → `invalid
  request`).
- Response: `{"columns": [...], "rows": [[...], ...], "row_count": N, "truncated": bool}`.
- **Always check `truncated`.** If true, the result set was capped — aggregate/paginate in
  SQL (COUNT/SUM/GROUP BY, or key-ranged batches) instead of pulling raw rows, and re-verify
  that totals are complete.
- Restrictions observed (all rejected as `{"error":"query rejected"}`):
  - Exactly **one** statement — no `;`-separated batches and **no trailing semicolon**.
  - Read-only only — `SELECT` / `WITH` / `UNION`; `UPDATE`/`DELETE`/`INSERT`/DDL are rejected.
  - Unknown table or column names, and syntactically invalid SQL, are rejected the same way —
    so `query rejected` means "fix the query" (wrong name, semicolon, or non-SELECT), and is
    your signal to re-derive names from the schema/dictionary.
  - Subqueries, CTEs, `UNION`, `WHERE`, `LIMIT`, aggregates, and column aliases all work.
- Prefer computing final numbers **in SQL** (counts, sums, medians via window/percentile,
  rate numerators/denominators, rankings) so you never depend on client-side re-derivation
  of a truncated pull. Pull explicit id lists only when the output requires them, and sort
  in SQL.

### `GET` discovery endpoints
May intermittently return `500 {"error":"service error"}`. Retry a few times with short
backoff before treating them as down. They are the only reliable source of real names — do
not fall back to guessing.

### `POST /api/sql/transaction` (corrections only)
Controlled write path for the single approved canonical correction. Use it **only** when the
task explicitly requests a data correction. It must change exactly the approved canonical
field on exactly the identified business row and write exactly one audit row; verify the
committed value with a follow-up read and/or `GET /api/correction-audit`. Never issue writes
through `POST /api/sql`.

---

## 2. Data-model semantics that decide correctness

These patterns recur across the task family. Each is a common source of a wrong-but-plausible
answer. Confirm the exact columns for each against the data dictionary — names below are
descriptions, not literal column names.

### Production vs. test population
The database mixes production and non-production (test/synthetic) rows. Scopes say
"production accounts/orders/shipments". Find the flag that marks production rows in the
dictionary and filter on it; forgetting it inflates every count.

### Effective / canonical value overlay (raw is not the answer)
Fields subject to correction exist as a **raw source value** and a **canonical/effective
value**. Approved corrections update the canonical layer while the raw value is preserved.
- For all **analysis**, use the **effective/canonical** value (raw + any applied correction).
- On a **correction write**, change only the canonical field; raw source values and source
  identity fields must stay unchanged.
- A raw/canonical *contradiction* (raw says one thing, canonical another, or vice-versa) is
  exactly what a carrier-quality correction task asks you to reconcile — find the one row
  where they disagree per the request's scope.

### Logical grouping (refunds/reversals)
A single business event can span multiple physical rows that roll up into one **logical**
unit. "Effective settled logical refund" = the deduplicated, settled logical refund after
applying any linked **reversals/offsets**. Count **distinct logical units**, link reversals
to their refund per the dictionary, and net amounts after reversals before comparing or
ranking. "Eligible refunded order" = a distinct in-scope order with ≥1 effective settled
logical refund.

### Cutoff / as-of state
Many metrics are evaluated **as of** a cutoff timestamp: "delivered by the cutoff",
"open/reopened at the cutoff", "not completed by the cutoff", "incomplete = no qualifying
shipment by cutoff". Reconstruct each entity's state **at the cutoff instant**, ignoring
events after it. "Effective final carrier status" is the canonical status as of the cutoff.
Complete/on-time/severe-exception style definitions layer promise-time comparisons on top of
this — read the exact wording (e.g. "> 24 hours after the promise", "no shipment promise
does not satisfy the first condition") and encode each clause literally.

### Active-time SLA clocks (support)
Support SLAs run on **active/support time**, not wall-clock — paused/waiting periods are
excluded. Compare active-time-to-first-response and active-time-to-resolution to the
**per-priority** thresholds from the request. For an unresponded or still-active case, use
the **active elapsed time at the cutoff**. "Severe active case", "open_at_cutoff" (open OR
reopened active state), and "reopened_at_cutoff" (its reopened subset) are defined in the
request's reporting_definitions — follow those definitions exactly. Medians: for an even
count, average the two central values.

### FX / money
Convert money to the reporting currency (USD) using the **daily fx rate for each row's
service_date and the row's currency**. Value order-gross comparisons at the rate stated for
the comparison. Net refunds = settled refunds minus linked reversals, in USD. Display money
at the template's precision (2 dp) but net at full precision first.

### Rates, denominators, and ordered status rules
Compute each rate on its **explicitly stated denominator** — incomplete/ineligible items
usually remain in the denominator (e.g. "incomplete eligible orders remain in the
denominator"; support rate denominator = eligible case count). Status/risk classifications
are **ordered rule lists** (HEALTHY→WATCH→CRITICAL, STABLE→PRESSURED→AT_RISK,
CONTROLLED→ELEVATED→SEVERE, LOW→MODERATE→HIGH): evaluate top-down and take the **first**
matching status.

### Rounding, ranking, tie-breaks
- Round **only final reported values** to the template's precision. Every comparison,
  ranking, and tie-break uses **full/unrounded** values.
- Ranking `order`/`ordering` clauses are literal: primary key direction, then each secondary
  key, then the final id-ascending tie-break; truncate to the stated `limit`/`result_size`.
- Id-list outputs sort ascending unless the contract says otherwise; arrays may be empty.

---

## 3. Output contract reminders
- `answer.json` is one JSON object with **exactly** the template's `required` keys and no
  others (`additionalProperties:false`). Some templates use prose keys
  (`additional_properties`, `min_items`, `decimal_places`, `ordering`, `order`) — read those
  as instructions, not schema you can ignore.
- Honor every `type`, `enum`, id `pattern`, decimal precision, and array ordering. Counts are
  integers; rates/money are numbers at the stated precision.
- No narrative or extra fields anywhere in the file.
