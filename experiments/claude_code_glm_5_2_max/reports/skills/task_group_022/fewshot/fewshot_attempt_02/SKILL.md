# Atlas Commerce Operations Reconciliation

Reuse this skill for any task that asks you to compute a business scorecard, reconciliation, quality review, productivity summary, or support-health review from the **Atlas Commerce Operations** workplace service and write a single JSON object to `answer.json`.

Every task in this family has the same anatomy:

1. **A business request** at `input/payloads/*_request.json` — defines scope, time windows, business definitions, classification/risk rules, rounding, and tie-breaks.
2. **An answer template** at `input/payloads/answer_template.json` — a JSON Schema that is the exact output contract (required fields, types, enums, min/max array lengths, ordering, precision).
3. **A prompt** at `input/prompt.txt` — names the stakeholder, the scenario, and the output file.
4. **A live workplace service** described in `environment_access.md` — reach it over the network with the documented endpoints and bearer token.

The work is the same every time: read the contract, map the business definitions onto real schema columns, run precise read-only SQL (and, only for correction tasks, one minimal guarded transaction), compute the metrics exactly as defined, and emit one JSON object that conforms to the template to the letter.

## When to use this skill

Use it whenever the prompt references the Atlas Commerce Operations workplace, points you at a `*_request.json` + `answer_template.json` pair, and asks for an analytical/reconciliation result in `answer.json`. Domain variants covered include: fulfillment scorecards, refund settlement reconciliation, carrier quality correction, warehouse productivity review, and enterprise support-health review. The procedure is identical across all of them; only the business definitions differ.

## Inputs you must read first

Before writing anything, open and read all of these in full:

- `environment_access.md` — base URL, auth token, and the exact request/response contract for every endpoint.
- `input/prompt.txt` — the scenario and any one-off instruction (e.g. "analytical only", "apply the approved minimal correction").
- `input/payloads/*_request.json` — **the source of truth for business semantics.** Read every definition, scope window, rule, rounding note, and tie-break verbatim.
- `input/payloads/answer_template.json` — **the source of truth for output shape.** Read every `required`, `additionalProperties`, `enum`, `pattern`, `minItems`/`maxItems`, `multipleOf`/`decimal_places`/`precision`, and `order`/`ordering` annotation.

Do not assume the shape of the data or the meaning of a metric from its name alone. The request replaces intuition; the template replaces any output format you might improvise.

## The workplace service (network access)

Reach the service exactly as documented in `environment_access.md`. Never hardcode a base URL or token from memory — read them from that file at the start of every run. Auth is `Authorization: Bearer <token>` on every call. Full endpoint reference is in `environment_api.md`.

- `GET /api/schema` — table/view names and columns.
- `GET /api/data-dictionary` — the canonical meaning, units, enums, and status model for each field. This is how you translate a business definition ("effectively DELIVERED", "effective settled logical refund", "active state") into exact column predicates.
- `POST /api/sql` — read-only analysis. Body `{"sql": "<SELECT or WITH>", "params": [...]}`. Use parameterized queries (`?`) for all literals.
- `POST /api/sql/transaction` — controlled multi-statement; **only for correction tasks.** Body `{"statements": [...], "expected_total_changes": <int>}`. Allowed SQL: SELECT/WITH, guarded `UPDATE` on `carrier_scans`/`inventory_movements`, and `INSERT INTO correction_audit` with all audit columns.
- `GET /api/correction-audit` — audit view, for verifying a correction after it commits.

Always confirm connectivity and token validity with a trivial query first (e.g. `SELECT 1 AS one`), then proceed. The environment is shared state — never run writes unless the prompt explicitly requests a correction, and even then only the approved minimal one.

## Procedure

Work these stages in order. Do not skip ahead.

### 1. Orient on the contract
From the template, list every required output field, its type, allowed enum values, array size constraints, ordering rule, and precision. This is your checklist — you are not done until each field is filled, correctly typed, and correctly ordered/rounded. Note `additionalProperties: false`: emit **only** the required keys, nothing extra.

### 2. Translate business definitions to schema predicates
Read `GET /api/schema` and `GET /api/data-dictionary`. For each business definition in the request, identify the exact columns and the canonical enum/status values that implement it. Watch for the recurring subtleties below — they appear across variants:

- **Effective vs. raw.** Many definitions say "effective" — meaning after reconciliation, reversal-netting, canonical normalization, or deduplication. Distinguish raw source values from canonical/effective values; reports use effective values.
- **Cutoff semantics.** A cutoff timestamp is an exact UTC boundary (typically `<...>T23:59:59Z`, inclusive). "By the cutoff" means `<= cutoff`. "Created during the window" uses the window's own boundary/inclusive flag. Use the timestamps as stated — do not adjust them.
- **Cohort/eligibility first.** Establish the eligible population exactly as scoped (campaign, account tier + segment + region, warehouse, batch, case-opened window, task-created window) before computing any metric. The denominator of every rate is the eligible population, not an unfiltered table.
- **Currency / FX.** When money crosses currencies, convert at the daily `fx_rates` rate for each row's service_date and currency, per the request's `fx_basis`. Do not assume a single rate or currency.
- **Normalization.** Reason codes, statuses, region labels, etc. often need normalization (trim/case/mapping). Rank/compare on the **normalized** value the request names.
- **"Every associated X" quantifiers.** "Complete only when *every* shipment is delivered", "on time only when *every* shipment was delivered by its promise" — these are `GROUP BY ... HAVING` / windowed conditions, not row-level filters. An order with no physical shipment is typically incomplete by definition.
- **Reversals and linkage.** Refund/reversal populations are linked by business keys; an "effective settled" refund may be partially or fully reversed. Net values are refund minus linked reversal, in the reporting currency.
- **Active time vs. wall clock.** Support/SLA metrics use *active* (business) elapsed time, not wall-clock time. An unresponded or still-open case uses active-elapsed-time at the cutoff, capped there.

### 3. Compute each metric directly from the data
Prefer one precise SQL query per metric over hand-rolling arithmetic in your head. Compute counts and sums in SQL; compute rates, medians, and sort keys there too when possible. Keep unrounded values for ranking and threshold checks; round only the final reported values.

### 4. Apply ordering and tie-breaks exactly
Every array field in the template carries an explicit ordering rule (e.g. "rate ascending, then region ascending"; "net USD descending, then reason_code ascending"; "<count> descending, then id ascending"). Sort on the **unrounded** sort keys, apply the stated tie-break, and only then round for display. Two regions with the same rounded rate must still be ordered by their unrounded rate first.

### 5. Apply rounding exactly as specified
Round only final reported rates/amounts, to the precision the template or request states (`multipleOf: 0.0001` → 4 decimals; `decimal_places: 2`/`precision: 2` → 2 decimals). Use round-half-up semantics consistent with the schema's `multipleOf`. Never round intermediate values used for ranking or thresholds.

### 6. Derive the classification/status from the request's rules
Status fields (`overall_status`, `cohort_risk`, `facility_status`, `support_risk`, `correction_status`) are computed from the **request's** rule table — never hardcode. Evaluate rules in the order given (typically best-tier-first with an "otherwise" fallback). Use the **unrounded** metric against the stated thresholds. Document which numeric values fed the chosen tier.

### 7. (Correction tasks only) Apply the minimal canonical correction
Only when the prompt requests a correction (carrier quality / raw-vs-canonical contradiction, or similar):

1. From the shared records, locate the **single** raw/canonical contradiction in scope. Identify the affected source row (stable row id), the shipment/entity id, the corrected canonical column, and the old→new canonical value.
2. Submit one `POST /api/sql/transaction` with: exactly one guarded `UPDATE` of the single canonical field on the single source row, and one `INSERT INTO correction_audit` carrying **all** audit columns (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code=SOURCE_RECONCILIATION, corrected_at, actor — all as given in the request).
3. Set `expected_total_changes` to the count of changed business rows **plus** the audit insert (typically `2`: one update + one audit row). The transaction commits only if actual changes match.
4. Re-query after the commit (read-only `POST /api/sql` or `GET /api/correction-audit`) to confirm the corrected canonical value is now live.
5. Compute pre- and post-correction backlog per the request's backlog definition, the delta (post − pre), and the post-correction delivered count.
6. Set `correction_status` to `APPLIED` **only if** exactly one business row and one audit row committed and the post-change verification confirms the new canonical value; otherwise `NOT_APPLIED` with the results actually observed.

Leave raw source values, source-identity fields, and all unrelated business rows untouched. If anything about the correction fails or is ambiguous, report `NOT_APPLIED` and say exactly what happened — do not force `APPLIED`.

### 8. Write and validate the answer
Write one JSON object to `answer.json`. Then validate it against the template before considering the task done — see `output_contract_checklist.md`. The file must contain **only** the JSON document: no prose, no markdown fences, no trailing commentary, no fields outside the template.

## Output discipline (non-negotiable)

- **One JSON object**, conforming to the template **exactly**. `additionalProperties: false` means no extra keys — not even "helpful" ones.
- **No commentary** inside `answer.json`. The prompt says it repeatedly for a reason.
- **Array ordering** must match the template's `order`/`ordering` annotation, on unrounded keys.
- **Types and precision** must match: integers are integers, numbers carry the required decimals, enums use the exact tokens, ids match the stated `pattern`.
- **Required arrays must be present even when empty** (unless the template forbids empty — some set `minItems`).
- When a metric is genuinely ambiguous from the request, choose the interpretation that follows the request wording most literally and is internally consistent across all fields (e.g. counts that sum correctly, a rate equal to numerator/denominator). Never invent data; never copy illustrative values from examples.

## Common failure modes to avoid

- Using wall-clock time instead of active/business time for SLA metrics.
- Putting incomplete/eligible orders in the numerator but forgetting them in the denominator.
- Rounding regional rates *before* ranking the "worst" regions, flipping the order on ties.
- Applying a single FX rate or assuming one currency across a multi-currency population.
- Treating "every shipment delivered" as a row filter instead of a per-order `HAVING`/window condition.
- Forgetting the reversal/linked set when netting refunds.
- Hardcoding a status instead of evaluating the request's rule table with unrounded inputs.
- Adding extra fields or prose to `answer.json`.
- On correction tasks: mutating more than the one approved field, omitting audit columns, or reporting `APPLIED` without a successful post-change verification.

## Reference files in this skill

- `environment_api.md` — full endpoint contract, request/response shapes, and worked curl forms.
- `output_contract_checklist.md` — the pre-submit validation checklist for `answer.json`.

## Notes on reuse

This skill is deliberately task-agnostic. It does not contain any answer values, request parameters, or computed results from specific runs — recompute everything from the live service and the request at hand. Read `environment_access.md`, the request, and the template fresh each time; do not trust remembered values for base URLs, tokens, schema columns, or business thresholds, because they change between variants.
