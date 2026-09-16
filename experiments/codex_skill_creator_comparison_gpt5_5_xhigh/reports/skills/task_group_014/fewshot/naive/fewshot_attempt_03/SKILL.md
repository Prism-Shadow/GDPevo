---
name: northstar-payer-json-review
description: Solve Northstar payer-operations tasks that require structured JSON from an HTTP task environment for authorization, appeal, claim repricing, peer-to-peer, or margin queue work.
---

# Northstar Payer JSON Review

Use this skill when the task asks for a Northstar Health Plan or payer-operations JSON answer built from a shared task environment. The usual inputs are `prompt.txt`, `payloads/task_context.json`, and `payloads/answer_template.json`.

## Operating Boundary

- Return exactly one JSON object matching the provided answer template; include no markdown or explanatory prose.
- Use the task prompt and payloads for the target ID, reporting date/period, token, endpoint, row IDs, thresholds, and required output shape.
- If the prompt contains `<TASK_ENV_BASE_URL>`, read `environment_access.md` only to obtain the live base URL. Do not use it as business evidence.
- Use only environment HTTP endpoints such as `POST /sql/query` and documented business endpoints. Do not inspect source files, database files, generated data files, manifests, or setup scripts.
- Prefer SQL for broad discovery and exact joins; use business endpoints when they expose clearer case/document/policy records.
- For SQL discovery in SQLite-like environments, use the HTTP SQL endpoint to inspect table names and columns, then issue targeted queries. Keep the bearer token and base URL from the task input out of the final JSON unless the template asks for them.

## Environment Workflow

1. Parse the template first. Record required keys, enum choices, precision rules, null handling, and ordering rules.
2. Discover the relevant records from the environment. Start from the target business ID or queue row IDs, then query related case, member, plan, claim line, authorization, appeal, document, criterion, event, benchmark, or finance records as applicable.
3. Separate current controlling evidence from stale, superseded, missing, or exception evidence. Use dates, effective periods, plan/modifier applicability, request status, and document type to decide precedence.
4. Fill every required template key with values derived from environment records or deterministic calculations. Use `null` only where the template allows it.
5. Validate the answer before final output: schema keys present, enum strings copied exactly from the template, list order correct, currency and ratios rounded as requested, and `basis_audit` consistent with the business decision.

## Decision Patterns

**Authorization / UM determination**

- Review active member and plan context, requested service lines, diagnosis, units, policy criteria, current clinical documents, and authorization record.
- Current clinical records control over stale exports. Evidence documents should include current records relied on; excluded documents should include stale or non-current records.
- Approve through nurse review only when all applicable clinical and administrative criteria are met and requested units/dates/CPTs fit policy and authorization limits. Pend for missing information, route to medical director when nurse approval authority is exceeded or criteria are adverse/unclear, and deny only when the template and records support an adverse final status.

**Pharmacy appeal plus assistance intake**

- Payer appeal disposition controls before manufacturer assistance screening.
- Classify medication failures as documented only when record evidence supports the required medication, timing, and outcome; otherwise list them as undocumented or insufficient.
- Required packet items come from the appeal and assistance rules. Missing packet items should list appeal evidence gaps before assistance gaps.
- If required appeal evidence is missing, the next action is usually information gathering rather than filing or submitting assistance, even when the assistance program screen is otherwise eligible.

**Claim repricing / payment integrity**

- Select the effective benchmark by plan, service date, CPT/HCPCS, modifier, and schedule effective period. Reject stale or inapplicable schedules even if they appear on the paid claim.
- Preserve claim-line order. Use `null` for absent modifiers.
- Compute line allowed amount as effective benchmark rate times units. Compute totals from lines, then compute correction/recovery amounts according to the template wording. Round currency to cents after applying units; do not emit formatted strings.
- Route to payment integrity correction or the template's equivalent route when the effective benchmark changes the paid amount.

**Peer-to-peer final summary**

- The completed P2P event and any new patient-specific information have priority over earlier intended decisions.
- Mark whether new information changed the review. If it did not resolve an adverse factor, keep the unresolved criteria and missing factor lists in the template's requested order.
- For adverse final outcomes, calculate the internal appeal deadline from the final adverse determination date using the plan's appeal-window rule in the records or prompt. Use `null` only when no appeal deadline applies.
- Recommend an alternative modality only when the policy or P2P record supports one.

**Finance / margin queue**

- Use only the queue row IDs supplied by the task context, in that same order.
- Total cost is the configured sum, commonly variable cost plus allocated fixed cost. Margin is revenue minus total cost. Revenue-to-cost ratio is revenue divided by total cost.
- Rows below the configured revenue-to-cost threshold take payer contract review priority over charge-sensitivity monitoring. Rows above threshold but flagged charge sensitive should be monitored as charge sensitive; otherwise use no-action monitoring.
- The top issue is the below-threshold row with the largest dollar gap to the threshold target. The gap is `(threshold * total_cost) - revenue`, rounded as requested. If no row is below threshold, use the template's no-issue value and zero/null only as the template permits.

**Combined appeal, clinical, and payment integrity routing**

- When a task combines appeal timeliness, clinical merits, and payment integrity issues, resolve appeal eligibility or deadline routing first.
- If the appeal is timely and eligible, evaluate clinical criteria and evidence next. Payment integrity or claim-correction facts should not override the appeal deadline or clinical determination unless the template explicitly makes them controlling.
- Order audit records in the same hierarchy: deadline/appeal records, then clinical or policy evidence, then claim or payment integrity records. Put deadline misses, clinical gaps, and payment integrity exceptions in that business order.

## `basis_audit`

Every observed template uses `basis_audit` to explain the source-precedence rule and record trail. Build it last, after the business result is known.

- `source_precedence`: choose the enum from the template that names the controlling rule for the task family.
- `controlling_record_ids`: list the environment record IDs that directly determined the result, in operational evidence order.
- `exception_record_ids`: list gaps, stale records, unresolved criteria, missing packet items, or excluded records that explain pends, denials, exclusions, or route priority.
- `precedence_record_order`: list the priority trail in source-precedence order, highest priority first. It may be narrower than the full controlling/exception lists when low-level line IDs or repeated gap details are not themselves competing source records. Do not merely concatenate lists if a later exception should appear before lower-priority controlling evidence.

## Output Discipline

- Copy enum values exactly from `answer_template.json`.
- Respect all template ordering rules: source claim line order, task-provided queue order, alphabetical segment/medication order, ascending criterion/document IDs, or explicit choice order.
- Use JSON booleans, numbers, arrays, and `null` with their native JSON types.
- Do not include extra fields when the template disallows them. When extra fields are allowed, omit them unless the task explicitly asks for them.
