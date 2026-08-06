# Atlas Commerce Operations — Analytical Reporting Skill

Compute a cutoff- or window-scoped operational report from the **Atlas Commerce Operations** database and write it as a strict-JSON `answer.json`. The request payload (input contract) and the `answer_template.json` (output contract) define *what* to compute; this skill defines *how* to reach the data, read it correctly, and emit a conforming answer every time.

This skill is reusable across request families: fulfillment scorecards, refund reconciliation, carrier quality correction, warehouse productivity, and support health. It teaches the model to treat each request as **"interpret contract → map to schema → verify with SQL → emit exact JSON"**, and never to guess or reuse values from any prior answer.

## When to use

Apply this skill whenever the task environment is the Atlas workplace service and the task asks you to produce a JSON report conforming to a supplied `answer_template.json`, driven by a request payload in `input/payloads/`. This covers both **read-only analytical** answers and the single **controlled-correction** answer family that mutates one canonical field plus an audit row.

## How the environment is reached

All database access is over the network through a small HTTP API. Read `environment_access.md` (staged alongside the task) for the authoritative base URL, token, and endpoint list — **do not** invent a different host, port, or auth. The same file is the only source for the bearer token.

The endpoints, all requiring `Authorization: Bearer <token>`:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/schema` | GET | Table DDL (`CREATE TABLE …`) — column names, types, PK/FK, CHECK constraints |
| `/api/data-dictionary` | GET | Per-table/per-column business descriptions and conventions |
| `/api/sql` | POST | Read-only analytical SQL (`SELECT`/`WITH`) |
| `/api/sql/transaction` | POST | Controlled multi-statement transaction (SELECT + guarded UPDATE + audit INSERT) |
| `/api/correction-audit` | GET | Public view of committed correction audit rows |

Use `curl -sS …` (or equivalent) with `-H "Authorization: Bearer <token>"` and `-H "Content-Type: application/json"`. Send SQL as JSON `{"sql": "...", "params": [...]}`. Prefer parameterized `?` placeholders with a `params` array over string interpolation; `params` may contain string, number, boolean, or null.

## Universal workflow (every request family)

1. **Read the input + output contracts first.** Read `input/prompt.txt`, the request payload in `input/payloads/*_request.json`, and `input/payloads/answer_template.json`. The template's `required` array and `additionalProperties: false` are the law: emit exactly those keys, nothing more.
2. **Resolve the base URL and token** from `environment_access.md`. Set `GDPEVO_ENV_BASE_URL` (or the variable named there) accordingly.
3. **Fetch schema + dictionary once** (`/api/schema`, `/api/data-dictionary`) and cache them mentally for the run. Confirm the real column names before writing any SQL — request payloads use business prose ("effective final carrier status", "productive minutes"), which you must translate to actual columns (`carrier_scans.canonical_status`, `warehouse_task_events.productive_minutes`).
4. **Translate the business definitions to SQL, one clause at a time.** The request payload's `business_definitions` / `reporting_definitions` / `*_*_rules` sections are precise; implement them literally. See `references/business_logic.md` for the recurring interpretation pitfalls.
5. **Verify every quantitative result against the raw data** before trusting it. See the verification discipline below.
6. **Format and round exactly as specified** — rounding rules, decimal places, and sort orders are part of correctness, not cosmetics.
7. **Emit `answer.json`** — one JSON object, no commentary, no trailing commas, keys matching the template. Validate the final object against the template's constraints yourself (counts ≥ 0, rates in [0,1] with the right `multipleOf`, arrays of the right length/identity/uniqueness/order, enum membership).

## The query surface — what works and what bites you

- **Accepted forms:** `SELECT`, `WITH … AS (…)`, subqueries in `FROM`, `UNION ALL`, `GROUP BY`, window functions, and parameterized `?` placeholders all run on `/api/sql`.
- **Read-only.** `/api/sql` rejects any statement that is not a `SELECT`/`WITH`. Mutations belong only in `/api/sql/transaction` and only in the approved shapes (below).
- **Results are capped at 5000 rows.** A response with `"truncated": true` means rows were dropped. This is the single most common silent-correctness trap:
  - Never SELECT an unbounded ID list and assume it is complete. Filter to the eligible cohort first, or generate the list with a tightly-scoped `WHERE` that yields fewer than 5000 rows.
  - When you need an exhaustive sorted ID list that *could* exceed 5000, split it into bounded pages (e.g. range on the monotonically-increasing numeric suffix of the ID, or `WHERE order_id > ? ORDER BY order_id LIMIT N` repeated) until a page returns fewer than the page size. Concatenate; never rely on a single truncated call.
  - Use `COUNT(*)` for denominators — aggregates are never truncated.
- **Confirmed working shape:** `{"columns":[...], "rows":[[...],...], "row_count": N, "truncated": bool}`. Program against `rows` as positional arrays keyed by `columns`.
- **Large/complex single statements may be rejected** ("query rejected") even when syntactically valid. If a big query is rejected, decompose it: run the cohort-determining query first, materialize the resulting key set, and compute the metric against it in a smaller query. Prefer a few small, obviously-correct queries over one clever mega-query.

## Reading the data correctly (shared interpretation rules)

- **Timestamps are ISO-8601 UTC text ending in `Z`** (`2026-04-15T23:59:59Z`). Lexicographic string comparison of these timestamps is correct chronological comparison — use it for `created_at <= cutoff`, `due_at < cutoff`, etc. Calendar dates are `YYYY-MM-DD`.
- **`current_status` columns are lagging snapshots.** The data dictionary calls them out as "convenience snapshot that may lag append-only event history." For most metric definitions the snapshot is what the business rule keys on, but read each request's definitions to confirm. The append-only event tables (`order_events`, `case_events`, `warehouse_task_events`, `payment_events`) hold the full lifecycle; reach for them when a rule is event-driven (e.g. "first agent response", "resolved at the cutoff").
- **Money is stored in minor units** (`gross_amount_minor`, `amount_minor`) in the smallest unit of the row's `currency`. Convert to display currency via `fx_rates.usd_per_unit` keyed by `(rate_date, currency)` where `rate_date` is the row's service/effective date. FX is "**USD per one unit**" of the foreign currency; USD is its own unit (rate 1.0 / identity). Sum in minor units, scale to major at the end, round to the requested decimals last.
- **Raw vs canonical fields.** Canonical columns hold normalized operational values (the ones analytics and corrections target); raw columns preserve source text. Operational metrics use canonical; corrections touch canonical only. Raw source values, source identity fields, and unrelated rows must never change.
- **Production exclusion.** Accounts carry `is_internal` and `is_test` integer booleans (1 = true). "Production" populations exclude rows where `is_test = 1` (and typically `is_internal = 1`). Apply the production/in-scope filter the request names before any counting.
- **Units ending in `_each` are individual units** and are the canonical unit count; multiply by the matching `_uom_multiplier` only if a raw-equivalent figure is needed.

## The controlled-correction family (one request type mutates data)

Exactly one request family writes data: identifying a single raw/canonical contradiction and applying **one minimal canonical correction** plus its audit record, via `/api/sql/transaction`. Everything else is read-only.

The allowed transaction contents (from `environment_access.md`):
- `SELECT`/`WITH` statements — safe pre/post verification.
- **Guarded `UPDATE`** restricted to `carrier_scans` or `inventory_movements`. The guard inspects statement structure, not just row counts: self-assignment (`SET col = col`), artificial predicates (`WHERE 1=0`), or UPDATEs to non-allowlisted tables are rejected as `transaction rejected`. Set the canonical correction columns the request names (e.g. `carrier_scans.canonical_status`, plus `corrected_at` and `correction_reason`) and scope the `WHERE` to the single target row identifier.
- **`INSERT INTO correction_audit`** with all 11 audit columns populated.

Transaction mechanics you must respect:
- **`expected_total_changes` is enforced exactly.** Sum of changed rows across all UPDATE/INSERT statements must equal the integer you declare, or the server returns `expected change count mismatch` and **rolls the whole transaction back**. A correction of one business row + one audit row → `expected_total_changes: 2`, with both statements in one transaction.
- **Verify before committing.** Include a pre-correction `SELECT` (read the old canonical value + the raw contradiction) and a post-correction `SELECT` (confirm the new canonical value is persisted) within the same transaction's `statements`. `expected_total_changes` counts only mutations, not selects.
- **Correctness status is earned, not assumed.** Report `APPLIED` only when (a) exactly one business row and one audit row committed (the transaction returned `total_changes: 2` with no mismatch error) **and** (b) a post-change query confirms the corrected canonical value. Otherwise report `NOT_APPLIED` with the results actually observed. Query `/api/correction-audit` to confirm the audit row is publicly visible after commit.
- **Audit identity fields map 1:1** from the request's `approved_correction` block: `audit_id`, `correction_key`, `actor`, `reason_code`, `corrected_at`. Use the source row's stable id for `source_row_id` and the corrected field for `field_name`; carry `old_value`/`new_value` as text.
- **Never persist a change you did not intend.** During exploration you may learn endpoint behavior with `expected_total_changes: 0` paired with a mutation that would change rows — the mismatch rolls it back. The rollback is reliable: a mismatched INSERT left `correction_audit` at zero rows. Still, prefer non-mutating probes whenever possible.

## Verification discipline (apply before declaring done)

For each numeric output, prove it with an independent query rather than trusting one computation:
- **Counts:** cross-check `COUNT(*)` two ways — e.g. `complete = eligible − incomplete`, or `severe ⊆ incomplete`. A mismatch means a definition is misimplemented.
- **Rates:** derive numerator and denominator as separate counts; confirm `0 ≤ rate ≤ 1` and that the denominator matches the request's stated base (e.g. "all eligible orders" vs "eligible *refunded* orders" — these differ across request families).
- **Sorted top-N lists:** assert the exact length (`minItems`/`maxItems` are often *exactly* N), uniqueness, the specified tie-break order, and (for ID lists) that every returned ID satisfies the template's `pattern`.
- **Rounding & bounds:** the template's `multipleOf` (e.g. `0.0001` for a 4-dp rate, `0.01` for a 2-dp median) is enforced. Round only the *final reported* value, sort by the *unrounded* value (then by the secondary key), then store the rounded value. Watch for exactly-tied secondary keys producing non-deterministic order — add the stable tie-break the request names.
- **"Exactly two"/"exactly three":** when a request asks for a fixed-length ordering of regions/teams/accounts/employees, compute the full ranking on the unrounded metric, apply the stated secondary sort, and slice the first N. Re-verify the slice boundary against a query that returns rank N+1 to make sure it would not tie into the slice.
- **FX & sums:** when currency conversion is involved, recompute the headline total (e.g. net refund USD) by a second independent aggregation and confirm equality to the displayed precision.

## Emitting `answer.json`

- One JSON object. No prose, no code fences, no trailing text outside the object.
- Include exactly the template's `required` keys; the templates set `additionalProperties: false`, so extra keys fail.
- Match each field's type and constraint: integers vs numbers, integer `>= 0`, rates within `[0,1]` and on the `multipleOf` grid, strings matching stated `pattern`, arrays meeting `minItems`/`maxItems`/`uniqueItems` and the documented ordering, enum membership for statuses/risk levels.
- Where a template forbids arrays entirely (some correction outputs), emit only scalar/object fields.
- Write the object to `answer.json` at the location the prompt specifies (the task input directory). Re-read it after writing to confirm it parses and still conforms — one parse failure voids the whole answer.

## Do not

- Do not copy any value from a prior task's `answer.json`. Each cohort is request-specific; recompute from the live database.
- Do not hard-code counts, IDs, rates, or status labels you have not derived from a query on this run.
- Do not mutate data for a read-only request, and do not run a guarded UPDATE/audit INSERT outside the single correction request family.
- Do not trust a single large query or a truncated result set — decompose and page.
- Do not round before sorting, and do not invent tie-breaks beyond the ones the request specifies.

## Reference files

- `references/schema.md` — the Atlas table/field reference (real column names and the canonical status/event/priority vocabularies). Consult it before writing SQL.
- `references/business_logic.md` — the recurring per-family interpretation pitfalls and the SQL patterns that resolve them.
