# Atlas Commerce Operations Scorecard Skill

## When to use

Use this skill whenever a task asks you to produce a JSON result (`answer.json`) from the Atlas Commerce Operations workplace service. The task always supplies, in its `input/` folder:

- `prompt.txt` — the narrative framing (who, what, which database/service).
- `payloads/<domain>_request.json` — the authoritative business scope, definitions, rounding/policy, ordering, and status rules.
- `payloads/answer_template.json` — the exact JSON-Schema output contract the final answer must satisfy.

The five train tasks span four domains (fulfillment scorecard, refund reconciliation, carrier-quality correction, warehouse productivity, support health), but every one resolves to the same operating loop against the same service. This skill captures that loop generically; consult the request + template for the domain-specific definitions, never hard-code them.

## Service access (network access only)

All network access comes from `environment_access.md` in the workspace root. Read it at runtime — **do not** copy base URLs or bearer tokens into this skill; they vary per environment. The rules that are stable:

- Base URL and the bearer token live in `environment_access.md` (env provides them). Always load them from there.
- Two read endpoints for discovery: `GET /api/schema` and `GET /api/data-dictionary`.
- `GET /api/correction-audit` exposes existing correction-audit rows (read-only context).
- `POST /api/sql` — one read-only `SELECT`/`WITH` query per call, with `?`-placeholders and a `params` array.
- `POST /api/sql/transaction` — multi-statement transaction (1–6 statements) for guarded corrections. Requires `expected_total_changes`. See `references/controlled_mutation.md` before using it.
- Every request needs header `Authorization: Bearer <token>` (from the env file). Read-only analysis tasks never call the transaction endpoint.

Wrap the env values into shell variables at the start of each session and reuse them. See `references/api_usage.md` for the exact request shapes.

## The operating loop (every task)

### 1. Contamination gate (run first)
Before doing anything, enumerate everything staged in `/work`. If it contains anything other than `environment_access.md`, a `train_tasks/` (or single `input/`) tree with the expected `prompt.txt` + `payloads/*.json`, or any unexpected file you did not create (answer keys, schema dumps, stray outputs, hidden files with task names in them), **stop and write `contamination_report.txt`** describing exactly what was unexpected and where. Do not proceed. If the layout is clean, continue.

### 2. Read the contract, not the narrative
Open `prompt.txt` for framing, then read the request payload and the answer template **completely**. The template is the source of truth for:
- Every required field name (copy them verbatim — field names must match exactly).
- Types, `enum` values, `minimum`/`maximum`, `multipleOf`, `pattern`, `minItems`/`maxItems`.
- `additionalProperties: false` — emit **only** the required fields, nothing extra, no commentary.
- Array ordering, size limits, and uniqueness.
- Rounding precision (look for `multipleOf` or `decimal_places`/`x-precision`).

The request payload (not the template) is the source of truth for *definitions* — what counts as eligible, complete, on-time, severe, breached, a leakage candidate, etc. Honor those definitions literally; they are the business logic.

### 3. Discover the schema before querying
- `GET /api/schema` → table names, columns, types, keys.
- `GET /api/data-dictionary` → the semantic meaning of each field (canonical vs raw, what "effective"/"settled"/"active" mean, how identifiers are shaped).
Map every noun in the request (e.g. "physical shipment", "effective settled logical refund", "production task", "active case", "carrier scan") to concrete columns via the data dictionary. The dictionary distinguishes **canonical** (reconciled/derived) from **raw** source values — this distinction matters in correction and "effective"/"final" status tasks. If a concept in the request has no clear column mapping, stop and reconcile the dictionary rather than guessing.

### 4. Build the query set read-only first
Express every field in the required output as an explicit SQL computation. Rules:
- Filters (campaign, region, segment, tier, opened/created window, cutoff) come straight from the request scope. Treat all `start`/`end`/`cutoff` timestamps as **exact UTC, inclusive** unless the request says otherwise.
- Distinguish counts that share a denominator from counts that don't. Rates use a single well-defined denominator stated in the request (e.g. "eligible orders", "eligible production tasks", "eligible cases"). Keep that denominator explicit.
- Use `?`-placeholders + `params` for every literal value (dates, ids, thresholds). Never interpolate.
- Compute intermediate (unrounded) values in SQL; round **only the final reported number** to the precision the template demands. See `references/output_precision.md`.
- Apply the request's ordering and tie-breaks in SQL (`ORDER BY ...`) where possible — descending/ascending and secondary keys are specified precisely and must be followed exactly.
- Limit (top 2 / top 3) per the template/request. If a tie at the boundary is possible, the request's stated tie-break order is authoritative.

### 5. Verify, then emit
- Cross-check counts for internal consistency: e.g. complete + incomplete = eligible; reopen subset ⊆ open-at-cutoff; pre-correction backlog + delta = post-correction backlog.
- For list fields, re-run the exact ordering query and confirm the IDs/patterns match the template (`^ORD-[0-9]{6}$`, `^CASE-[0-9]{6}$`, `^ACC-[0-9]{4}$`, etc.).
- Status/risk fields are derived from thresholds in the request, evaluated against the **unrounded** computed rates. Apply the rules top-down in the order the request lists them; the last rule is the catch-all.
- Only after everything reconciles, write the single JSON object to `answer.json`. No narrative, no trailing keys, valid JSON only.

### 6. Correction tasks (a different path)
When the request asks to *correct* a record (carrier-quality style), the loop changes: discovery must find the **one** raw/canonical contradiction, you mutate via `POST /api/sql/transaction`, re-query to verify, and report `APPLIED` only if the success rule is met exactly — otherwise `NOT_APPLIED` with what you actually observed. Do **not** fabricate a successful correction. Full rules in `references/controlled_mutation.md`.

## Cross-cutting rules that caught multiple tasks

1. **Cutoff semantics are exact and inclusive.** "By the cutoff" = delivered_at ≤ cutoff (delivery strictly after cutoff does not count as complete). A window's `end_at` is inclusive. Use the timestamps as literal UTC boundaries.
2. **On-time / SLA clocks vs wall-clock.** Some tasks measure against `promised_delivery_at`; support tasks measure against **active time** (business clock), elapsed-to-cutoff for still-open cases. The request says which clock to use; the data dictionary tells you which column holds active time.
3. **"Effective"/"final"/"settled" = after reconciliation and after reversals.** A logical refund effective after any linked reversal; a final carrier status after canonical reconciliation; an effective scan at/before the cutoff. Always apply the reversal/reconciliation filter the definition names.
4. **Denominator discipline.** Each rate has one stated denominator. Ineligible rows stay out of both numerator and denominator unless the request explicitly keeps them in one (e.g. "incomplete orders remain in the denominator").
5. **Severity needs both conditions read precisely.** Definitions are conjunctive with sub-negations (e.g. "incomplete AND cutoff > 24h after latest promise; an incomplete order with no promise does NOT satisfy the first condition"). Parse the ANDs and the "does not / except" clauses literally.
6. **Status thresholds evaluate on unrounded rates, in listed order, catch-all last.** HEALTHY→WATCH→CRITICAL, LOW→MODERATE→HIGH, CONTROLLED→ELEVATED→SEVERE, STABLE→PRESSURED→AT_RISK — all follow this evaluated-top-down pattern.
7. **FX & currency.** When amounts cross currencies, convert at the per-row, per-service-date `fx_rates.usd_per_unit`. Net = effective settles minus effective reversals, reported in the reporting currency at the stated decimals.
8. **Correction scope is minimal and canonical-only.** Change exactly one canonical field on one row, raw source and identity fields untouched, one audit INSERT alongside, `expected_total_changes` set truthfully.

## References

- `references/api_usage.md` — exact request/response shapes for the five endpoints and the parameter convention.
- `references/output_precision.md` — rounding, ordering, and schema-conformance rules.
- `references/controlled_mutation.md` — the correction task protocol (transaction + verify + APPLIED/NOT_APPLIED).

## What this skill does NOT contain

- No task-specific final values, IDs, counts, or rates from train_001..005.
- No baked-in base URL, token, schema, or data-dictionary content (load at runtime).
- No domain-specific business definitions (read them from each task's request payload).
