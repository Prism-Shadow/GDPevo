# Atlas Commerce Operations: Reusable Operating Rules

This is a self-contained operating skill for solving Atlas Commerce Operations
analytics tasks served from the `environment_access.md` workplace API. Each task
gives you a business request JSON, an output template JSON, and a free-text prompt;
the API exposes a relational database, a data dictionary, and (sometimes) a
controlled correction transaction. The five train tasks all share one shape, so
these rules are written once and reused per task.

This file is the entry point. It contains no task-specific final values, table names
beyond the documented schema, query results, or answers from any individual task.
Two supporting files live alongside it:
- `references/pipeline.md` — the end-to-end execution pipeline, step by step.
- `references/output_contract.md` — how to read a template and emit a conformant JSON.

Read this file first, then jump to `references/pipeline.md` when executing.

---

## 1. Inputs the task always gives you

Every task directory contains exactly:
1. `input/prompt.txt` — short business framing. Names the audience and the goal,
   points at the base URL `<TASK_ENV_BASE_URL>`, and says where to write the answer.
2. `input/payloads/<domain>_request.json` — the authoritative scope. Holds the
   cohort filters (population/tier/segment/region/window/cutoff), the exact business
   definitions for every metric, the ranking/sorting rules, the status/risk policy,
   and the list of required output fields.
3. `input/payloads/answer_template.json` — the JSON Schema output contract.

Treat the request payload as the source of truth for *what* to compute; treat the
template as the source of truth for *how* to shape and constrain the answer. When
the two disagree, the template's structural rules (field names, order, rounding,
array sizes, `additionalProperties:false`) win on shape; the request's definitions
win on meaning.

`environment_access.md` is the *only* file that grants network access. Take the base
URL and auth token from it verbatim. Do not invent endpoints or tokens.

---

## 2. The environment

Environment base URL and auth token come from `environment_access.md`. All
requests require `Authorization: Bearer <token>` (copy the exact token from that
file). Available endpoints:

- `GET /api/schema` — full DDL for every table (column names, types, checks,
  foreign keys). Call this before writing any query.
- `GET /api/data-dictionary` — per-column business descriptions plus `conventions`.
  Always read this; it tells you which columns are raw-source vs canonical, which
  flags mean production vs test/internal, how money and timestamps are encoded.
- `GET /api/correction-audit` — view of committed correction_audit rows. Use it to
  confirm audit state when a task involves corrections.
- `POST /api/sql` — run one read-only SELECT/WITH query. Body:
  `{"sql": "...", "params": [...]}`. `params` defaults to `[]`. Always parameterize
  literals (dates, IDs, thresholds) through `params` rather than string-interpolating.
- `POST /api/sql/transaction` — run 1–6 statements atomically. Allowed SQL:
  SELECT/WITH; *guarded* UPDATE on `carrier_scans` or `inventory_movements`; and
  INSERT INTO `correction_audit` supplying **all** audit columns. Body requires
  `expected_total_changes` (int 0–12). The server enforces the guards; malformed or
  out-of-scope SQL is rejected.

Timestamps are ISO-8601 UTC ending in `Z`; calendar dates are `YYYY-MM-DD`. Money
lives in the *minor* unit of the row currency; `fx_rates.usd_per_unit` is USD per
one unit of the row currency. Raw columns preserve source values; canonical columns
hold normalized operational values — metrics are computed on canonical values unless
the request explicitly says otherwise.

---

## 3. Core operating principles (apply to every task)

### A. Read definitions literally and exhaustively.
Every request payload carries a `business_definitions` / `reporting_definitions`
block. Each sentence is a rule; none are decorative. Common load-bearing clauses to
never skip:
- "at least one physical shipment AND every shipment DELIVERED by the cutoff" —
  completeness is conjunctive across *all* shipments, not the first one.
- "delivered no later than that shipment's `promised_delivery_at`" — on-time is
  per-shipment promise, not a single order-level date.
- "an order with no physical shipment is incomplete" — no-shipment ⇒ incomplete,
  never excluded from the denominator.
- "more than 24 hours after" / "strictly before" / "at or before" — honor the
  comparator exactly; `>` vs `>=` changes membership.
- "denominator includes incomplete orders" / "remains in the denominator" — the
  cohort is fixed first; only the numerator varies by status.

If a definition references another value (a cutoff, a promise, an SLA threshold),
resolve it from the same payload, not from your own assumption.

### B. Fix the cohort first, then compute everything inside it.
Most bugs come from a leaky cohort. Build the eligible population as an explicit,
named subquery bound by the payload's scope (population flag, tier/segment, region,
created/opened window, cutoff), and reuse that exact population as the denominator
for *every* downstream ratio. A row excluded from the cohort once must stay excluded
everywhere; a row in the cohort stays in denominators even when it fails the metric.

### C. Distinguish raw, canonical, and current-state correctly.
- Raw fields (e.g. `raw_status`, `raw_quantity`, `raw_event_at`) preserve the
  source; canonical fields (`canonical_status`, `canonical_quantity`, …) hold the
  normalized operational value. Compute on canonical unless told to use raw.
- "Current/denormalized" snapshot columns on header tables reflect the latest
  state, but a cutoff-based review must reconstruct state *as of the cutoff* from
  the append-only event tables filtered by `event_at <= cutoff` — do not trust a
  live snapshot column for a point-in-time question.
- Events inherit the row's lifecycle; `source_import_batches` tells you which batch
  a raw row came in on (matters for "named batch at or before cutoff" scopes).

### D. Round only at the very end, and only reported values.
Use unrounded intermediate values for all comparisons and rankings, then round
exactly the fields the template marks (note every `multipleOf` / `decimal_places` /
`precision`). Obey the template's tie-break ordering *independently* of the
rounding: e.g. "order by unrounded rate ascending, then label ascending" means sort
on the full-precision value and round only for display.

### E. Reproduce the exact ordering and array sizes the template demands.
Templates fix array sizes (`minItems`/`maxItems` equal → exact count) and a
specific sort order ("… descending, then ID ascending"). Build the ORDER BY to match
the stated keys and direction, apply the tie-breaks, then truncate to the required
size. Never free-sort or guess.

### F. Status / risk enums come from a cascading rule list.
The payload lists rules top-down (e.g. HEALTHY → WATCH → CRITICAL, or
CONTROLLED → ELEVATED → SEVERE). Evaluate the strongest condition first; the first
rule whose condition holds wins; "otherwise"/"all other outcomes" is the terminal
bucket. Each rule usually combines two metrics (a rate threshold AND a count/rate
threshold) — both sub-conditions must be met. Derive every input to the rule from
the same fixed cohort, with the same rounding policy.

### G. Corrections are opt-in, minimal, and audited — only when the task asks.
A correction task (write-back) differs from an analytical task:
- Only `POST /api/sql/transaction` mutates; `POST /api/sql` is read-only.
- Correct exactly the minimal canonical field the payload's `approved_correction`
  names, on exactly the one row the contradiction points to. Never touch raw
  columns, identity columns, or unrelated rows.
- Append one `correction_audit` INSERT with **all** audit columns (audit_id,
  correction_key, entity_type, entity_id, source_row_id, field_name, old_value,
  new_value, reason_code, corrected_at, actor) taking values from the payload's
  `approved_correction` block.
- Set `expected_total_changes` to 1 (business row) + 1 (audit row) = 2 for the
  approved minimal correction.
- Verify after the transaction by re-querying the corrected canonical value, then
  report `APPLIED` only if "exactly one business row and one audit row committed
  AND the post-change query confirms the new canonical value" — else `NOT_APPLIED`
  with the results actually observed. Do not back-fill `APPLIED` on faith.
- If the task is explicitly analytical ("no data correction is requested",
  "read-only"), never call the transaction endpoint.

### H. Validate against the template before writing the file.
The final artifact is a single JSON object saved to `answer.json`. Before writing:
every required field present; no extra fields (templates set
`additionalProperties:false`); integers vs numbers correct; rates within `[0,1]`
and stepping to the stated `multipleOf`; arrays at exact size with unique items and
the stated sort; enum values exactly as named; no narrative/key/comments outside the
JSON. If you can, json-schema-validate the object against the template you were given.

---

## 4. Failure modes to actively avoid (seen across the train shape)

- Leaky cohort: filtering the *numerator* instead of the *population*, then
  dividing filtered-by-filtered. Fix the population once; reuse it.
- Treating a snapshotted current-state column as point-in-time-at-cutoff.
- Using `>` where the definition says `>=` (or vice versa) on time/24h boundaries.
- Averaging/summing across shipments without the "every shipment must satisfy"
  quantifier — completeness and on-time are universal ("every"), not existential.
- Pre-rounding a regional rate, then ranking on the rounded value, disagreeing with
  a "unrounded … ascending" rule.
- Omitting a no-shipment order from the denominator because it "feels" out of scope.
- Emitting `APPLIED` without the post-change verification query actually confirming.
- Mutating a raw or identity column, or touching rows outside the named batch/cutoff.
- Inserting a correction_audit row that omits a required audit column.
- Writing extra fields or commentary into `answer.json`.

---

## 5. When to stop or escalate

- **Contamination / unexpected material:** if `/work` (or the task input dir)
  contains anything outside the canonical `prompt.txt` + `payloads/` layout — stray
  answer/solution/expected/key files, secrets, unrelated inputs — stop solving and
  write `contamination_report.txt` describing what was found. Do not proceed.
- **Environment unreachable:** if `GET /api/schema` fails after a verified correct
  base URL + token, stop and report; do not fabricate a schema from memory.
- **Ambiguity that the payload cannot resolve:** pick the interpretation the
  template's constraints make consistent, note the assumption, and proceed — but
  never invent data. The payload + schema are the only ground truth.

---

## Next step

To execute a task, open `references/pipeline.md` for the step-by-step procedure and
`references/output_contract.md` for the template-to-JSON conformance checklist.
