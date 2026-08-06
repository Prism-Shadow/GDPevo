---
name: atlas-ops-analytics
description: >-
  Produce the answer.json for an Atlas Commerce Operations workplace task — the
  request family that hands you a prompt.txt plus a payloads/ request contract and
  answer_template.json, and points at an authenticated Atlas service
  (GET /api/schema, GET /api/data-dictionary, POST /api/sql, POST /api/sql/transaction,
  GET /api/correction-audit). Use when a /work task asks for a fulfillment scorecard,
  refund/settlement reconciliation, carrier-quality correction, warehouse-productivity
  review, support-health review, or any similar cutoff-based operational scorecard,
  reconciliation, correction, or SLA/risk classification computed from the Atlas
  read-only SQL (and, when explicitly requested, the controlled transaction) endpoints.
---

# Atlas Commerce Operations analytics & correction tasks

## What this family looks like

Every task ships the same layout under `/work`:

```
input/prompt.txt                     # narrative + where to write the answer
input/payloads/<request>.json        # the authoritative business contract (scope, definitions, policy)
input/payloads/answer_template.json  # the exact output contract
environment_access.md                # base URL, bearer token, endpoint list
```

The prompt is prose; **the request payload JSON is the source of truth** for scope,
definitions, thresholds, ranking, rounding, and status rules. The answer template is
the exact output contract. Your job: translate the payload's business definitions into
SQL against the Atlas service, compute every required field, and write a single JSON
object to `answer.json` that conforms **exactly** to the template — no extra keys, no
commentary, correct types/precision/ordering/id formats.

Read `references/atlas-operations-reference.md` before writing SQL — it holds the API
mechanics (request/response shapes, restrictions, transactions, retries) and the
cross-cutting Atlas data-model semantics (effective/canonical overlays, logical refunds,
cutoff/as-of state, active-time SLA clocks, FX, production filtering) that recur in every
task and are the usual source of wrong numbers.

## Procedure

### 1. Confirm inputs, then read the whole contract
- List `input/payloads/`. Read `prompt.txt`, the request payload, and `answer_template.json`
  in full. If material beyond the declared inputs is present in a way the prompt does not
  account for, surface it rather than guessing.
- From `environment_access.md` take the **base URL** and **bearer token**. Send
  `Authorization: Bearer <token>` on every request. Do not hardcode a token from any
  example — always read it from the file present in the current task.
- Note whether the task is **read-only analysis** or asks for a **data correction**. Only
  correction tasks touch `POST /api/sql/transaction`; analytical tasks must not change data.

### 2. Discover the real schema — never guess table/column names
- `GET /api/schema` and `GET /api/data-dictionary` define the actual table and column
  names and the meaning of every field (which column is the raw source value, which is the
  canonical/corrected value, what flags mark production vs. test rows, how refunds/reversals
  link, how support active-time is recorded, how warehouse/region/team relate, etc.).
- These endpoints can return a transient `500 {"error":"service error"}`; retry a few times
  with a short backoff before concluding they are unavailable. Do not substitute guessed
  names — the SQL endpoint rejects unknown tables (as `{"error":"query rejected"}`), and a
  guessed column that *exists* but means the wrong thing produces a silently wrong answer.
- Map each business term in the request payload to concrete columns using the data
  dictionary. Resolve every "effective / canonical / logical / active-time / production"
  phrase to its columns **before** writing analysis SQL.

### 3. Build the scope (cohort) exactly as defined
Translate the payload's scope block literally: production-population filter, tier/segment/
region/warehouse filter, and the time window. Honor the stated boundary — windows are
typically **inclusive** on both ends and timestamps are **exact UTC** (`treat as exact UTC
boundaries`). Get the anchoring date right: created-window vs. service-date vs. opened-window
vs. as-of cutoff are different columns with different roles. Campaign tasks additionally
restrict to the campaign's official active window and attribution.

### 4. Compute each metric from the payload's definitions, not intuition
Work each `business_definitions` / `reporting_definitions` clause verbatim. Recurring shapes
(see the reference for the semantics):
- **Cutoff/as-of state**: evaluate completeness, open/reopened state, delivery, and "not
  completed by cutoff" *as of* the cutoff, ignoring anything after it.
- **Effective values over raw**: always analyze the canonical/effective value (raw value
  with any approved correction applied), never the raw source column.
- **Logical grouping**: count distinct *logical* units (e.g. logical refunds), and link
  reversals/offsets per the dictionary before counting or netting.
- **Active-time SLA clocks**: compare active elapsed time (not wall-clock) to the
  per-priority threshold; unresponded/still-active cases use active-elapsed-at-cutoff.
- **FX**: convert money to the reporting currency using the daily rate for each row's
  service_date and currency, then net after reversals.
- **Rates & ordered status rules**: compute each rate on its **stated denominator**
  (incomplete/ineligible items usually stay in the denominator). Evaluate status rule lists
  **top-down, first match wins**.

### 5. Rounding, ranking, and tie-breaks
- **Round only final reported values** to the template's precision (rate decimals, money =
  2 dp, counts = integers). Keep **full/unrounded** precision for every comparison, ranking,
  and tie-break — the payload often says "unrounded" explicitly.
- Apply ranking `order` clauses exactly, including secondary keys and the final id-ascending
  tie-break, then truncate to the stated `limit`/`result_size`. ID-list outputs are sorted
  ascending unless told otherwise.

### 6. Corrections (only when the task asks for one)
Identify the single raw/canonical contradiction named in the request. Apply the **minimal
canonical-field-only** change via `POST /api/sql/transaction` (leave raw source values,
source identity fields, and unrelated rows untouched), write the audit row using the exact
`audit_id`/`correction_key`/`reason_code`/`actor`/`corrected_at` from the request, and
**verify post-change** with a read query (and/or `GET /api/correction-audit`). Report
`APPLIED` only if the request's success rule is met (typically exactly one business row and
one audit row committed and the post-change value confirmed); otherwise `NOT_APPLIED` with
the values actually observed. Report pre- and post-correction metrics as the template asks.

### 7. Emit `answer.json`
- Output one JSON object with **exactly** the template's `required` keys and nothing else
  (`additionalProperties:false` ⇒ no extra fields; templates also use prose-y keys like
  `additional_properties`/`decimal_places`/`ordering` — read those as instructions).
- Match every declared type, enum, id `pattern` (e.g. `^ORD-[0-9]{6}$`), decimal precision,
  and array ordering. Empty arrays are valid when nothing qualifies.
- Write only the JSON document to `answer.json` — no prose, no trailing text.

## Self-check before finishing
- Numbers derived from **effective/canonical** values and **production** rows only; every
  cutoff/as-of condition evaluated at the right instant.
- Every rate uses the correct denominator; rounding applied only at the end; rankings/
  tie-breaks used unrounded values and the exact key order.
- Output has exactly the required keys, correct types/precision, id patterns, and array
  ordering; no commentary anywhere in `answer.json`.
- Analytical tasks changed no data; correction tasks changed exactly the approved field and
  wrote exactly one audit row, then verified it.
