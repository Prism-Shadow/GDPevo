# Atlas Commerce Operations Analytical Task Solver

This skill solves a class of analytical/operational tasks against the **Atlas Commerce Operations** workplace database. Each task presents a business request (prompt + JSON request payload) plus a strict JSON output contract (`answer_template.json`), and asks you to compute the answer from live database records and write a single `answer.json`.

The rules here are *reusable operating methodology*. They contain **no task-specific final values**, thresholds, IDs, or dates — those always come from the request payload of the specific task. Apply the rules to whatever request you are given.

## When to use

Use this skill when a task matches this shape:

- A prompt references the Atlas Commerce Operations workplace at `<TASK_ENV_BASE_URL>` and asks for a JSON result written to `answer.json`.
- An `input/payloads/<something>_request.json` supplies the business scope, definitions, scope windows, cutoffs, and classification/risk policy.
- An `input/payloads/answer_template.json` defines the exact output contract (required fields, types, enum values, array sizes, ordering, rounding).
- The prompt says the request is analytical / read-only, OR (one variant) asks for an approved minimal canonical correction with an audit record.

## The four-phase procedure

Run every task in this order. Do not skip phases.

### Phase 1 — Read everything before touching the API

1. Read the prompt and **every payload file** under `input/payloads/` (the request JSON **and** the answer template JSON). The answer template is a binding contract, not a suggestion.
2. From the request payload, extract in writing:
   - the **cohort / population / membership** definition (which rows are eligible),
   - every **scope window and cutoff** as exact UTC boundaries (note inclusive vs exclusive, start vs end),
   - every **business definition** (what counts as complete / on-time / breached / severe / candidate, etc.) — quoted from the payload,
   - every **formula** (rate numerators and denominators, per-unit/per-hour math, ratios),
   - every **ranking / ordering rule** (sort keys, ascending/descending, tie-breakers, result sizes),
   - every **rounding rule** (which fields round, to how many decimals, and whether ranks use rounded or unrounded values),
   - every **status / risk classification policy** (the ordered rules and their numeric thresholds).
3. From the answer template, extract:
   - the exact required field names and their JSON types,
   - array `minItems`/`maxItems` and ordering constraints,
   - enum value strings (must match exactly, including case),
   - any `multipleOf` / `precision` / `decimal_places` that encode rounding,
   - `additionalProperties: false` — the output must contain **only** the required fields, nothing extra.

The payload's prose definitions are authoritative. When a payload definition and the answer template description disagree on wording, follow the **payload definition** for the computation and the **template** for field shape/format only.

### Phase 2 — Ground yourself in the live schema (read-only)

Use the documented environment endpoints (see `environment_access.md` for the base URL and bearer token; use that file **only** for network access). All headers require `Authorization: Bearer <token>`.

- `GET /api/schema` — table DDL (column names, types, CHECK constraints, foreign keys).
- `GET /api/data-dictionary` — column descriptions and the global **conventions** (timestamps are ISO-8601 UTC ending in `Z`; dates are `YYYY-MM-DD`; monetary minor fields are the smallest unit of the **row currency**; FX rates are USD per currency unit; **raw** fields preserve source values, **canonical** fields hold normalized operational values).
- `POST /api/sql` — read-only analysis. Body `{"sql": "<SELECT or WITH>", "params": [...]}`.
- `GET /api/correction-audit` — the public audit view (columns + rows; starts empty).
- `POST /api/sql/transaction` — controlled writes, **only** for the correction variant (see Phase 4).

Before writing business SQL, `SELECT` the columns you will rely on and sample a few rows. **Confirm**:

- which columns are `*_minor` integers (money / amounts in the row currency's smallest unit) vs. `REAL` (FX rates),
- which timestamp/date columns bound the cohort and cutoffs,
- which `is_internal` / `is_test` flags exclude non-production rows (treat `1` as true, `0` as false),
- raw vs. canonical columns (analytics use **canonical**; raw is preserved as-is and never changes).

### Phase 3 — Compute with read-only SQL (analytical tasks)

Work in small verified queries. Build the result bottom-up: define the eligible cohort first, then derive counts, rates, rankings, and classifications from that same cohort so every output field is consistent with one another.

Operating rules that recur across every analytical task:

1. **Build the eligible set once, then reuse it.** Every count and every rate's denominator comes from the same eligible cohort defined by the payload. Express it as a CTE (`WITH eligible AS (...)`) and join back to it. A rate numerator that silently uses a different population than its denominator is the most common failure.
2. **Match the cohort exactly.** Apply the population filter (e.g. production accounts/orders, not test/internal), the scope window (inclusive boundaries unless the payload says otherwise), and any membership condition (e.g. "has at least one effective scan in the named batch at or before the cutoff"). Re-check membership predicates against the payload wording.
3. **Respect raw vs. canonical.** Use canonical fields for operational analytics. Raw fields are source-of-truth inputs that you do not alter.
4. **Money: convert via daily FX to USD.** For any USD amount, take the refund/reversal/payment **service date** (or the date the payload names) and the row **currency**, then join `fx_rates` on `(rate_date, currency)` and multiply the minor-unit amount by `usd_per_unit`. Divide minor amounts by 100 to get major units before/after FX as the payload's money policy dictates. Use the same FX basis for both sides of any comparison (e.g. refund value vs. order gross) so the comparison is apples-to-apples.
5. **Settle / net using linked reversals.** When a payload talks about "effective settled ... after reversals" or "net", follow the linkage column (`linked_event_id` / `linked_refund_id`) to subtract reversed rows from their parent rows. A row and its reversal are not independent.
6. **Rank exactly as specified.** Apply every sort key in order with the stated direction, and break ties with the stated tie-breaker. Return exactly the `result_size` / `limit` rows — no more, no fewer. Where a payload ranks by a rate, decide from its wording whether to rank on the **unrounded** rate (typical for "worst/lowest by rate") and round only the reported value.
7. **Round only where the payload says.** "Round only final reported rates to N decimals" means: compute and compare on full-precision values; round only at the moment you emit the field. Honor the template's `multipleOf` (e.g. `0.0001` = 4 decimals, `0.01` = 2 decimals) as the rounding grid.
8. **Classify with the first matching ordered rule.** Status/risk policies are ordered (e.g. HEALTHY → WATCH → CRITICAL, or LOW → MODERATE → HIGH, or CONTROLLED → ELEVATED → SEVERE). Evaluate in the listed order and take the **first** rule whose conditions all hold; fall through to the "otherwise/all other" bucket when none match. A "both conditions must hold" rule is satisfied only when *both* hold.
9. **Sort ID lists ascending and de-duplicate.** Where the template requires a sorted unique list of IDs (orders, cases, tasks, accounts), `DISTINCT` + ascending sort. Preserve the exact ID pattern; do not strip prefixes.
10. **Medians: handle even counts by averaging the two central values.** For a median over a resolved/closed population, sort ascending; for an even count average the two middle values; round the result to the decimals the template/payload specify.

### Phase 4 — Correction variant (only when the payload asks for an approved minimal canonical correction)

One task type asks you to apply a correction, not just analyze. The payload states there is exactly one raw/canonical contradiction and supplies an `approved_correction` block (reason_code, actor, audit_id, correction_key, corrected_at) plus a `correction_status_rule`.

1. **Identify the one contradiction.** Query the in-scope rows (named batch + warehouse + at/before cutoff as the payload defines) and find the single scan/shipment row whose `raw_*` value contradicts its `canonical_*` value in the way the payload describes. Do not "fix" any other row.
2. **Correct the minimal canonical field only.** The correction scope is `MINIMAL_CANONICAL_FIELD_ONLY`: change exactly one canonical column on exactly one business row so the canonical value becomes correct. Never change a raw/source value, a source identity field, or any unrelated business row.
3. **Use the controlled transaction endpoint.** Submit a single `POST /api/sql/transaction` with:
   - a guarded `UPDATE` on `carrier_scans` (or `inventory_movements`) limited to the one target row, setting the canonical field, `corrected_at`, and `correction_reason`;
   - an `INSERT INTO correction_audit` carrying **all** audit columns (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) exactly as the payload's `approved_correction` plus the observed old/new values;
   - `expected_total_changes` set to the business-rows-changed count the rule requires.
   Re-read `environment_access.md` for the exact allowed SQL shapes (`SELECT/WITH`; guarded `UPDATE` on `carrier_scans`/`inventory_movements`; `INSERT INTO correction_audit` with all audit columns) and the constraints on `statements` (1–6) and `expected_total_changes` (0–12).
4. **Verify post-change, then report what you actually observed.** Run a read-only query to confirm the canonical value now holds. The `correction_status` is `APPLIED` only when **both** (a) exactly one business row and one audit row committed and (b) a post-change query confirms the corrected canonical value — exactly the payload's success rule. If the transaction rejected, changed a different count, or the post-check fails, report `NOT_APPLIED` with the counts actually observed. Never claim `APPLIED` for a transaction you could not fully verify. `GET /api/correction-audit` should now contain your audit row.
5. **Report backlog/analysis around the correction as observed.** Compute pre- and post-correction backlog counts (and any delta/delivered counts the template wants) from the same cohort/membership definition the payload gave, using the cutoff exactly once each side of the correction.

### Phase 5 — Emit exactly the contract, nothing more

1. Produce a single JSON object. Field names, types, nesting, enums, and array sizes must match `answer_template.json` exactly. `additionalProperties: false` means no extra keys, no commentary, no trailing fields.
2. Round each numeric field to its template grid (`multipleOf` / `decimal_places` / `precision`).
3. Sort every ordered array exactly as the template specifies (note `x-list-ordering` / `ordering` / `order` constraints; some templates forbid arrays entirely).
4. Write the object to `answer.json` with **no text outside the JSON document** — no prose, no markdown fence, no explanation. The file is the answer.
5. Validate against the template before finishing: required fields present, types correct, enums matched, array lengths within bounds, additionalProperties satisfied. A well-formed but non-conforming object is a wrong answer.

## Notes & guardrails

- **Read-only unless explicitly correcting.** If the prompt says analytical/read-only (no data correction requested), use only `GET` and `POST /api/sql`. Never call the transaction endpoint.
- **Trust the payload's exact wording over assumption.** Edge cases ("an incomplete order with no shipment promise does not satisfy the first condition"; "an unresponded case uses active elapsed time at the cutoff") are deliberate and must be implemented literally.
- **Keep numbers consistent.** Derive counts and rates from the same cohort CTE. Cross-check that `complete + incomplete == eligible` (or the analogous decomposition) and that a status classification uses the same rate you reported.
- **Network only via `environment_access.md`.** Use the base URL and bearer token documented there; do not invent endpoints or credentials. If the env var form of the base URL is empty, use the literal URL printed in `environment_access.md`.
- **Don't hardcode task-specific values into shared logic.** Thresholds, windows, IDs, and result sizes are inputs read from the payload at runtime.

## Supporting references

- `skill/reference/endpoints.md` — endpoint bodies, headers, request/response shapes, and SQL allowed-lists, lifted from `environment_access.md`.
- `skill/reference/schema_map.md` — table inventory and the raw-vs-canonical / minor-money / FX conventions that recur across tasks.
- `skill/reference/task_patterns.md` — the five recurring analytical patterns (cohort rate scorecard, settlement reconciliation, carrier quality correction, warehouse productivity, support health) as checklists, without specific values.
