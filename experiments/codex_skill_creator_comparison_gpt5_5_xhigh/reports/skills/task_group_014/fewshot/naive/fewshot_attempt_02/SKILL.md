---
name: northstar-payer-ops-json
description: Solve Northstar Health Plan payer-operations tasks that require querying the read-only task environment and returning strict JSON for prior authorization determinations, pharmacy appeals and assistance intake, peer-to-peer closures, claim repricing, or UM-finance margin queues. Use when prompts mention Northstar payer operations, CASE/APPEAL/P2P/CLAIM/QUEUE identifiers, the /sql/query endpoint, policy criteria, authorization records, payment benchmarks, or service_margin rows.
---

# Northstar Payer Ops JSON

Use this skill to produce the requested JSON object from the task prompt, `input/payloads/task_context.json`, `input/payloads/answer_template.json`, and the read-only Northstar environment.

## Non-Negotiables

- Return JSON only. Match the template's keys, nesting, enum values, numeric precision, date format, list ordering, and additional-property rule.
- Use the prompt and task context to identify the target IDs, report/as-of date, queue row IDs, threshold values, endpoint base URL, and bearer token.
- Query only the allowed business environment. Do not inspect environment source files, generated data files, SQLite files, manifests, setup scripts, judge APIs, test answers, or unrelated local paths.
- Keep environment queries scoped to the target IDs whenever possible. Avoid broad reads unless needed for schema discovery.
- Treat the environment as authoritative over local assumptions. The few-shot answers are pattern evidence only; do not reuse any prior case-specific value.

## Environment Access

- Replace `<TASK_ENV_BASE_URL>` with the base URL given in the prompt or environment access file.
- The SQL endpoint is `POST /sql/query` with `Authorization: Bearer <token>` and JSON body `{"sql": "select ..."}`.
- Use `GET /api/tables` first when table or column names are uncertain.
- Optional helper: run `python scripts/northstar_env.py --base-url "$TASK_ENV_BASE_URL" --token "$TOKEN" sql "select * from cases where case_id='...'"` from the skill directory, or use the absolute path to [scripts/northstar_env.py](scripts/northstar_env.py).

## One-Pass Workflow

1. Read the prompt, task context, and answer template completely.
2. Extract target identifiers:
   - Authorization/P2P/appeal work usually uses a `case_id`.
   - Appeal work may also provide an `appeal_id`.
   - Claim repricing uses `claim_id`, often also equal to `case_id`.
   - Finance queues use the explicit `queue_row_ids` from task context; do not substitute nearby rows.
3. Discover the schema with `/api/tables` if needed, then fetch the minimum scoped record set.
4. Reconcile facts under the source-precedence rule implied by the work type.
5. Calculate derived fields, assemble `basis_audit`, validate against the template, and emit exactly one JSON object.

## Scoped Record Sets

For authorization or clinical determinations, fetch:

- `cases`, `members`, `plans`, `providers`
- `request_lines`
- `authorizations`
- `policies`, `policy_criteria`, `case_criteria`
- `documents`, `document_facts`

For pharmacy appeal and assistance intake, fetch:

- `cases`, `appeals`
- `documents`, `document_facts`
- `case_criteria`, `policy_criteria`
- `drug_trials`
- `assistance_screen`

For peer-to-peer closure, fetch:

- `cases`, `request_lines`, `authorizations`
- `p2p_events`
- `case_criteria`, `policy_criteria`
- `documents`, `document_facts`

For claim repricing, fetch:

- `claims`, `claim_lines`
- `members`, `plans`
- `payment_benchmarks`
- case or policy records only if the template asks for them

For finance queue summaries, fetch:

- `service_margin` rows whose `month_id` appears in task context
- case/context records only if the template asks for queue-level routing beyond the listed rows

## Decision Patterns

### Clinical Authorization

- Current clinical documents control over stale exports. Use `documents.is_current = 1` and case-specific dates to identify relied-on documents; list stale/non-current case documents as excluded when the template asks.
- Copy criterion results from `case_criteria` only after confirming they align with current policy criteria and the relevant documents/facts.
- For a nurse approval, all required criteria should be `met`, the authorization record should support approval, and approved units/dates/CPT/modifier should come from `authorizations` or the request lines when the template directs.
- If required clinical facts are missing or unclear, prefer the template's pend or medical-director route choices according to policy `result_if_missing`, case stage, and prompt role.

### Pharmacy Appeal And Assistance

- Payer appeal facts take precedence over manufacturer assistance facts for appeal disposition.
- Use `appeals` for path, expedited flag, deadline, owner, and packet notes.
- Classify drug trials by `documented`: documented trials go in documented failures; undocumented or partial support goes in the insufficient list. Normalize medication names as the template requires, usually lowercase and alphabetical.
- Required packet items come from the template, appeal notes, policy criteria, and assistance requirements. Missing items come from absent documents/facts, undocumented trial records, and `assistance_screen.missing_fields`.
- Assistance program/status comes from `assistance_screen`; map pending missing-information statuses to the closest template enum for missing information, and list missing fields in the required ordering.

### Claim Repricing

- Select benchmarks by payer, member plan type, service domain, CPT, modifier, and service date within `effective_start`/`effective_end`.
- Modifier matching is exact, including `null` for absent modifiers. Do not use a distractor benchmark with the wrong modifier, plan type, service domain, or date.
- If multiple benchmark sources are present, the effective benchmark for the claim line controls; expired or wrong-source rows are exceptions.
- `correct_allowed_amount = benchmark.allowed_amount * units`, rounded to cents.
- `paid_total` comes from the claim. `correct_allowed_total` is the sum of corrected line amounts. `recovery_amount = correct_allowed_total - paid_total`; preserve the sign unless the template states otherwise.
- Line disposition: corrected amount greater than paid is `correct_upward`; less than paid is `correct_downward`; equal is `no_change`; denied lines use the template's denial choice when supported by claim data.

### Peer-To-Peer Closure

- New patient-specific P2P information controls over the earlier intended decision.
- Use `p2p_events` for `p2p_id`, outcome, final status, new-information text, and reviewer notes.
- Use request lines for the requested CPT.
- Map `case_criteria` into the required criterion result keys. Criteria with `not_met` or `unclear` usually remain unresolved unless the template says only unclear criteria count.
- For PET-over-SPECT tasks, missing factors are the unsupported factor names requested by the template or policy. Derive them from policy text, criteria gaps, document facts, and P2P new-information text.
- If the final result is adverse and the prompt provides an appeal window, calculate the internal appeal deadline from the final adverse determination date. Use `null` when no adverse deadline applies.

### Finance Margin Queue

- Use only queue row IDs from task context and preserve their order for row-level output.
- `total_cost = variable_cost + fixed_cost_allocated`.
- `margin = net_revenue - total_cost`.
- `revenue_to_cost_ratio = net_revenue / total_cost`, rounded to the template precision.
- `below_threshold` is true when the ratio is less than the task threshold.
- Recommended action: below-threshold rows route to payer contract review; rows that are not below threshold but charge-sensitive route to charge-sensitive monitoring; all others monitor with no action.
- Segment lists should follow the template ordering, often alphabetical by enum value.
- Top issue is the below-threshold row with the largest positive gap to threshold; encode it as the template expects. If none are below threshold, use the template's none value and a zero gap unless instructed otherwise.
- `gap_to_threshold = threshold * total_cost - net_revenue`, rounded to cents for the top below-threshold row.

## Basis Audit

Always populate `basis_audit` from the records and gaps that actually control the answer.

- Choose `source_precedence` by work type:
  - clinical current/stale document review: `current_clinical_records_over_stale_export`
  - pharmacy appeal with assistance: `payer_appeal_before_manufacturer_assistance`
  - claim repricing: `effective_benchmark_by_plan_modifier_and_date`
  - peer-to-peer: `new_patient_specific_p2p_information`
  - finance margin queue: `margin_threshold_then_charge_sensitivity`
  - mixed queues with multiple operational routes: `appeal_deadline_then_clinical_then_payment_integrity`
- `controlling_record_ids` should include the environment rows used directly for the result: current documents, appeal rows, trial rows, claim lines, benchmark rows, P2P rows, queue rows, or authorizations as applicable.
- `exception_record_ids` should include stale documents, expired/wrong benchmarks, missing packet fields, insufficient trial records, unmet criteria, or unresolved factor IDs.
- `precedence_record_order` should list controlling and exception records in the precedence order requested by the template, highest priority first. Do not sort blindly when the template gives operational order.

## Final Validation

- Re-read the template before final output.
- Confirm required keys are present and no forbidden extra keys are present.
- Confirm numeric precision: currency usually cents, ratios usually the template precision, service units integers.
- Confirm date precision: ISO calendar dates unless the template says otherwise.
- Confirm list ordering: document IDs ascending, claim lines by source line order, queue rows by provided row IDs, medications alphabetical, and enum-specific lists in template order.
