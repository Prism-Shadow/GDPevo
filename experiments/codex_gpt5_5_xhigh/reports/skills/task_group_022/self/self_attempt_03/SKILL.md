---
name: atlas-ops-request-analysis
description: Analyze Atlas Commerce Operations workplace requests and produce exact JSON answers from prompt, request payload, schema, data dictionary, SQL query endpoints, and optional controlled correction endpoints. Use when a task asks Codex to compute operational scorecards, reconciliations, SLA/health reviews, cutoff-based state, ranked exceptions, or apply an approved minimal canonical data correction with audit evidence against the Atlas workplace service.
---

# Atlas Ops Request Analysis

Use this skill for Atlas Commerce Operations tasks that provide a prompt, one or more request payloads, an answer template, and an authenticated workplace service. Produce the requested `answer.json` exactly; include no narrative in the answer file.

## Required Inputs

1. Read the task prompt first.
2. Read every file under `input/payloads/`, including the business request payload and `answer_template.json`.
3. Read `environment_access.md` only to obtain the allowed base URL, endpoints, headers, and transaction limits.
4. Treat all request timestamps as exact UTC business cutoffs or windows. Do not substitute the current date.
5. Use the answer template as the output contract, even when it uses nonstandard schema spellings such as `additional_properties`, `min_items`, or `decimal_places`.

## Service Access

- Fetch `/api/schema` and `/api/data-dictionary` before writing analysis SQL.
- Use `POST /api/sql` for read-only analysis. Send only `SELECT` or `WITH` queries unless the task explicitly requests a correction.
- Use `/api/correction-audit` only to inspect existing or post-change audit evidence.
- Never use undocumented network targets, credentials, or endpoints.
- Prefer parameterized SQL through the documented `params` field. Keep exploratory queries narrow and ordered.

## Analysis Workflow

1. Translate the request payload into explicit cohort predicates, metric definitions, ranking rules, rounding rules, and status/risk policies.
2. Inspect schema and dictionary names instead of guessing table or column names. Confirm join keys, state/status columns, effective/canonical fields, timestamp meanings, logical IDs, source-row IDs, and production/test flags.
3. Build the result with CTEs:
   - `params` for request constants.
   - cohort CTEs for eligible business entities.
   - state-at-cutoff CTEs for records whose effective timestamp is at or before the cutoff.
   - metric CTEs for counts, rates, rankings, and exception lists.
4. Count distinct business entities at the grain named by the request: orders, shipments, tasks, cases, accounts, logical refunds, reversals, employees, or teams.
5. Preserve missing related records when the definition makes absence meaningful. Use left joins for cases such as orders with no physical shipment, unresponded support cases, active unresolved cases, or tasks not completed by cutoff.
6. Validate intermediate row counts and sample IDs before trusting aggregate output. Check for accidental row multiplication after joins.
7. Compute status and risk classes from unrounded rates. Round only final reported numbers to the precision required by the template or request.
8. Sort every output list by the request's exact order. For ties, apply every stated tie-breaker before any final rounding.

## Common Business Patterns

### Fulfillment and Shipment Cutoffs

- Use eligible production orders from the requested campaign, warehouse, region, or active window.
- Treat an order as complete only if it has at least one relevant physical shipment and all relevant physical shipments are effectively delivered by the cutoff.
- Treat an order as on time only if it is complete and every relevant shipment was delivered no later than its promised delivery timestamp.
- For severe exceptions, compare lateness against the request threshold using the latest shipment promise for incomplete orders and each actual delivery timestamp for completed orders.
- Rank warehouse or regional rollups by the unrounded rate, then by the stated stable label.

### Refund Reconciliation

- Scope to production accounts and account attributes from the request, then to effective settled logical refunds in the service-date window.
- Use one logical refund grain for refund counts; use distinct linked reversal grain for reversal counts.
- Convert refund and reversal amounts to USD with the daily FX rate for each row's service date and currency.
- Net reversals against their linked logical refund before computing exposure, reason totals, and leakage candidates.
- For gross-order comparisons, value the order gross in USD at the settled refund service-date rate specified by the request.
- Normalize reason codes before ranking or identifying duplicate unreversed reasons. Rank reasons by effective net USD descending, then code ascending unless the request says otherwise.

### Warehouse Productivity

- Use task creation windows and state cutoffs exactly as stated. Honor inclusive and exclusive boundary wording.
- Completion rate denominator is eligible production tasks, not only completed tasks.
- Rework rate denominator is also eligible production tasks unless the request overrides it.
- Units per hour is completed units divided by productive minutes attached to those completed units, multiplied by 60.
- Rank employees by units per hour descending, then employee ID ascending. Rank teams by completion rate ascending, then team ID ascending unless instructed otherwise.
- A delayed high-priority task must satisfy both the priority/due rule and the not-completed-by-cutoff rule.

### Support Health and SLA Reviews

- Scope accounts by production status, segment, region, or tier before selecting eligible cases.
- Apply case-opened windows exactly, then evaluate case state at the cutoff.
- Open-at-cutoff includes cases in open or reopened active states; reopened is a subset of open-at-cutoff.
- First-response breaches use active time to first agent response. If no response exists by cutoff, use active elapsed time at the cutoff.
- Resolution breaches use active time to resolution for resolved cases and active elapsed time at cutoff for active cases.
- Severe active cases must satisfy the active-state, priority, and resolution-threshold conditions simultaneously.
- Compute medians over the eligible resolved-at-cutoff population; for even counts average the two central active-time values.

## Controlled Corrections

Only mutate data when the prompt and request payload explicitly ask for an approved correction.

1. Identify the exact contradiction from visible raw/canonical evidence and the request scope.
2. Restrict the target to the approved minimal canonical field. Do not change raw source values, source identity fields, unrelated rows, or derived business IDs.
3. Capture pre-correction metrics and the target's old canonical value with read-only SQL.
4. Build a guarded transaction containing:
   - one `UPDATE` constrained by source-row ID, business entity ID, old value, scope fields, and any batch/cutoff criteria needed to guarantee one business row;
   - one correction-audit `INSERT` using the request's approved audit fields.
5. Set `expected_total_changes` to the exact business-row plus audit-row count required by the success rule.
6. After the transaction, verify affected business rows, audit rows, the corrected canonical value, and post-correction metrics through read-only SQL or `/api/correction-audit`.
7. Report `APPLIED` only when every success condition is met. Otherwise report `NOT_APPLIED` with the actually observed mutation and verification results.

## Output Discipline

- Write exactly one JSON object to `answer.json`.
- Include only keys allowed by `answer_template.json`, with all required keys present.
- Match identifier formats and enum values exactly.
- Keep arrays unique when required and sorted by the requested order.
- Use JSON numbers, not strings, for numeric values. Round monetary and rate values to the required numeric precision.
- Validate the final file against the answer template structurally before finishing; at minimum check required keys, forbidden extra keys, enum membership, array sizes, uniqueness, and numeric rounding.
