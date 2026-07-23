---
name: northstar-payer-ops
description: Structured JSON workflows for Northstar payer-operations tasks in the shared environment. Use when a prompt asks for an authorization summary, appeal and assistance disposition, claim repricing packet, peer-to-peer summary, or margin queue report that must be answered as one schema-valid JSON object.
---

# Northstar Payer Ops

## Workflow
1. Read the prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` first.
2. Identify the task family from the template keys.
3. Use the base URL and bearer token from the task context or prompt.
4. Query the live Northstar environment with `POST /sql/query`; use business endpoints when they expose the needed record directly.
5. Build the answer only from live records plus the task memo for scope and dates. Treat the memo as a locator, not as evidence.
6. Follow the template exactly. Preserve list order rules, enum spellings, number precision, and date formats. Emit one JSON object only.
7. Write `basis_audit` from the records that directly controlled the result. Put controlling records first, then gaps, stale records, or exclusions.

## Shared Rules
- Prefer current clinical, appeal, or benchmark records over stale exports or old schedules.
- Keep `null` for absent modifiers.
- Use ISO dates (`YYYY-MM-DD`) and round currency to cents.
- Keep ratios at the precision requested by the template.
- When a task limits scope to explicit IDs or row IDs, ignore everything else.
- Do not add narrative, markdown fences, or extra keys.
- Use the environment endpoints listed in the task note when they are clearer than SQL: `GET /api/tables`, `GET /api/cases`, `GET /api/cases/{case_id}`, `GET /api/policies`, `GET /api/policies/{policy_id}`, `GET /api/documents/{document_id}`, `GET /api/rate-schedules`, and `GET /api/appeals`.

## Task Families

### Authorization summaries
- Use when the template requires `case_id`, `recommendation`, `final_status`, `route`, `authorization`, `criteria_results`, `evidence_documents`, `excluded_documents`, `determination_letter`, and `next_action`.
- Review the case, member and plan context, requested therapy lines, applicable policy criteria, clinical documents, and any authorization record.
- Map outcomes consistently: approve when the required criteria and authorization support the request; pend when key information is missing; escalate to medical director or peer-to-peer when physician review is needed; deny when criteria fail; use partial approval when only part of the request is supportable.
- Populate `criteria_results` for `PT-ACTIVE`, `PT-DEFICIT`, `PT-DX`, `PT-POC`, and `PT-UNITS`.
- Include only controlling evidence documents in `evidence_documents`; list stale or noncontrolling case documents in `excluded_documents`.
- Fill `authorization` with the auth number, approved units, approved date span, approved CPTs in ascending order, and the line modifier.
- Set `source_precedence` to `current_clinical_records_over_stale_export`.

### Appeal and assistance intake
- Use when the template requires `case_id`, `appeal_id`, `drug`, `appeal_path`, `expedited`, `appeal_deadline`, `owner`, medication failure lists, packet items, assistance, and next action.
- Resolve the appeal first, then the assistance screen. Let appeal records control over assistance facts when they conflict.
- Classify prior medication failures into `documented_failures` and `undocumented_or_insufficient_failures` using the evidence in the case.
- Order packet items so appeal evidence appears before assistance items; list gaps in the same operational order.
- Mark assistance `eligible_ready` only when the program is identified and no required fields are missing.
- Set `source_precedence` to `payer_appeal_before_manufacturer_assistance`.

### Claim repricing
- Use when the template requires `claim_id`, `case_id`, `auth_number`, benchmark fields, totals, line-level corrections, resubmission route, priority, and audit.
- Select the benchmark by plan, modifier, and date. Reject stale exports and note the rejected source.
- Keep claim lines in source claim order.
- Compute `paid_total`, `correct_allowed_total`, and `recovery_amount` from the line items. Use cents precision.
- Set each line disposition to `correct_upward`, `correct_downward`, `no_change`, or `deny_line` based on the corrected allowed amount.
- Set `source_precedence` to `effective_benchmark_by_plan_modifier_and_date`.

### Peer-to-peer summaries
- Use when the template requires `case_id`, `p2p_id`, `requested_cpt`, `p2p_outcome`, `final_status`, PET criteria, unresolved criteria, missing PET factors, `letter_type`, `recommended_alternative`, and `internal_appeal_deadline`.
- Decide whether the P2P added new patient-specific information that materially changed the review.
- Map `criteria_results` to `PET-IND` and `PET-FACTOR`.
- List only unresolved criteria in `unresolved_criteria`.
- When the final result is adverse, calculate the internal appeal deadline from the final adverse determination date using the plan window in the task memo.
- Set `source_precedence` to `new_patient_specific_p2p_information`.

### Margin queue summaries
- Use when the template requires `case_id`, `period`, threshold ratio, row summaries, segment lists, top issue, gap, and audit.
- Review only the row IDs listed in the task memo.
- Compute each row's ratio from the underlying revenue and cost figures, then flag `below_threshold` at the requested cutoff.
- Flag `charge_sensitive` from the queue facts, keep row order aligned with the supplied row IDs, and sort the segment summary lists alphabetically.
- Set `top_issue` to the worst below-threshold segment/CPT pair and compute `gap_to_120pct` against 120 percent of cost.
- Set `source_precedence` to `margin_threshold_then_charge_sensitivity`.

## Audit Format
- Put the directly controlling record IDs in `controlling_record_ids`.
- Put missing, stale, exception, or excluded records in `exception_record_ids`.
- List the combined record trail in `precedence_record_order`, highest priority first.
