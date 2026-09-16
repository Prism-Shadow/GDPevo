# Northstar Workflows

## Prior Authorization (UM Nurse)

**Source precedence**: `current_clinical_records_over_stale_export`

**Tables involved**: cases, request_lines, members, plans, policies, policy_criteria, documents, document_facts, case_criteria, authorizations

### Workflow

1. Query the case: `SELECT * FROM cases WHERE case_id = '<CASE-ID>'`
2. Query request lines: `SELECT * FROM request_lines WHERE case_id = '<CASE-ID>'`
3. Query the member: `SELECT * FROM members WHERE member_id = '<member_id>'`
4. Query the plan: `SELECT * FROM plans WHERE plan_id = '<plan_id>'`
5. Query the policy: `SELECT * FROM policies WHERE policy_id = '<policy_id>'`
6. Query policy criteria: `SELECT * FROM policy_criteria WHERE policy_id = '<policy_id>'`
7. Query documents: `SELECT * FROM documents WHERE case_id = '<CASE-ID>'`
8. Query document facts: `SELECT * FROM document_facts WHERE case_id = '<CASE-ID>'`
9. Query case criteria results: `SELECT * FROM case_criteria WHERE case_id = '<CASE-ID>'`
10. Query authorizations: `SELECT * FROM authorizations WHERE case_id = '<CASE-ID>'`

### Decision Rules

- **Evidence documents**: All documents with `is_current = 1` that support criteria. List in ascending `document_id` order.
- **Excluded documents**: Documents with `is_current = 0` (stale) or documents that do not support any applicable criterion. List in ascending `document_id` order.
- **Criteria**: Check each PT-* criterion from policy_criteria against case_criteria results. A criterion is `met` when its result is `met`; `not_met` when `not_met`; `unclear` when the result is missing or ambiguous.
- **Recommendation**:
  - All criteria met, authorization exists with approved units → `approve`
  - One or more criteria not met → `deny` (or `escalate_to_md` if clinical judgment needed)
  - Missing evidence → `pend_for_information`
- **Route**:
  - `approve` → `nurse_approval`
  - `pend_for_information` → `pending_information`
  - `deny` / `escalate_to_md` → `medical_director_review`
- **Authorization**: Pull `auth_number`, `approved_units`, `approved_start`, `approved_end`, `approved_cpt` (split on commas, sort ascending), `approved_modifier` renamed to `modifier`.
- **Determination letter**: `approval` for approve, `information_request` for pend, `adverse_determination` for deny.
- **Next action**: `issue_approval` for approve, `request_more_information` for pend, `route_md_review` for escalate, `issue_denial` for deny.

### Basis Audit

- `controlling_record_ids`: Current clinical documents that drove the determination.
- `exception_record_ids`: Stale documents. If criteria gaps exist, list those first (by criterion ID), then stale docs.
- `precedence_record_order`: Current documents first, then stale documents. Within current docs, order by document date most-recent-first.

## Pharmacy Appeal + Manufacturer Assistance

**Source precedence**: `payer_appeal_before_manufacturer_assistance`

**Tables involved**: cases, appeals, drug_trials, assistance_screen, documents, policies, policy_criteria

### Workflow

1. Query the case: `SELECT * FROM cases WHERE case_id = '<CASE-ID>'`
2. Query the appeal: `SELECT * FROM appeals WHERE appeal_id = '<APPEAL-ID>'`
3. Query drug trials: `SELECT * FROM drug_trials WHERE case_id = '<CASE-ID>'`
4. Query assistance screen: `SELECT * FROM assistance_screen WHERE case_id = '<CASE-ID>'`
5. Query policy/criteria as needed.

### Decision Rules

- **Drug**: Determined from the task prompt or case summary.
- **Appeal path**: From `appeals.appeal_path`.
- **Expedited**: `appeals.expedited_attestation = 'yes'` → `true`, else `false`.
- **Appeal deadline**: From `appeals.appeal_deadline`.
- **Owner**: From `appeals.owner`.
- **Documented failures**: Drug trials with `documented = 1` and `outcome` indicating failure (e.g. `failed_efficacy`). List medication names lowercase, alphabetical.
- **Undocumented/insufficient failures**: Drug trials with `documented = 0` or `outcome` not clearly failure. List medication names lowercase, alphabetical.
- **Criteria results** (DRUG-*): From `case_criteria` joined with `policy_criteria`. `met` when result is `met`; `not_met` when `not_met`; `partial` when some but not all sub-evidence exists; `unclear` when missing.
- **Required packet items**: Operational order — payer appeal items first, then assistance items. Include `denial_notice`, `member_authorization`, `prescriber_rationale`, `formulary_failure_evidence`, then `household_income_proof` if assistance applies.
- **Missing packet items**: Appeal evidence gaps first (e.g. `lurasidone_fill_record`), then assistance gaps (e.g. `household_income_proof`).
- **Assistance**: From `assistance_screen`. `program_name` from the screen; `status` mapped from `assistance_status`; `missing_fields` split from the comma-separated field, sorted alphabetically.
- **Next action**: `request_more_information` if missing items exist; `file_appeal` if packet is complete; `submit_assistance_application` if assistance is ready; `close_not_eligible` if appeal not eligible.

### Basis Audit

- `controlling_record_ids`: Appeal record ID and documented drug trial IDs (ordered by priority — appeal first).
- `exception_record_ids`: Undocumented trial IDs, then missing field IDs.
- `precedence_record_order`: Appeal → documented trials → undocumented trials → missing fields.

## Payment Integrity (Claim Repricing)

**Source precedence**: `effective_benchmark_by_plan_modifier_and_date`

**Tables involved**: claims, claim_lines, payment_benchmarks, cases, authorizations

### Workflow

1. Query the claim: `SELECT * FROM claims WHERE claim_id = '<CLAIM-ID>'`
2. Query claim lines: `SELECT * FROM claim_lines WHERE claim_id = '<CLAIM-ID>' ORDER BY line_number`
3. Query the case for payer/plan context: `SELECT * FROM cases WHERE case_id = '<CASE-ID>'`
4. Query benchmarks for each line's CPT+modifier combination:
   - For each line, query `payment_benchmarks` where `cpt_code = '<cpt>'` and `modifier` matches (or `modifier IS NULL`).
   - Identify the effective benchmark: `effective_end >= service_date`.
   - Compare source names to identify the correct schedule vs. the stale one.
5. Determine `benchmark_source` and `benchmark_version` from the current effective benchmark.
6. Identify `stale_source_rejected` — the benchmark source that was used for payment but is expired or not applicable.

### Decision Rules

- **Correct allowed amount**: For each line, `units × benchmark allowed_amount`. Round to cents.
- **Recovery amount (line)**: `correct_allowed_amount - paid_amount`. Negative means overpayment (correct downward).
- **Recovery amount (total)**: Sum of line recovery amounts. Positive = underpayment owed to provider, negative = overpayment to recoup.
- **Disposition**:
  - Recovery > 0 → `correct_upward`
  - Recovery < 0 → `correct_downward`
  - Recovery = 0 → `no_change`
- **Resubmission route**: `payment_integrity_correction` when correction is needed; `provider_adjustment` when provider must act; `no_resubmission` when no change.
- **Priority**: `standard` by default; `expedited` if recovery is significant; `monitor_only` if no change.

### Basis Audit

- `controlling_record_ids`: Claim line IDs and current benchmark IDs (lines first, then benchmarks).
- `exception_record_ids`: Stale benchmark IDs.
- `precedence_record_order`: Current benchmarks → stale benchmarks.

## Peer-to-Peer (P2P) Authorization

**Source precedence**: `new_patient_specific_p2p_information`

**Tables involved**: cases, request_lines, p2p_events, documents, document_facts, case_criteria, policy_criteria, policies

### Workflow

1. Query the case: `SELECT * FROM cases WHERE case_id = '<CASE-ID>'`
2. Query request lines: `SELECT * FROM request_lines WHERE case_id = '<CASE-ID>'`
3. Query P2P events: `SELECT * FROM p2p_events WHERE case_id = '<CASE-ID>'`
4. Query documents: `SELECT * FROM documents WHERE case_id = '<CASE-ID>'`
5. Query case criteria: `SELECT * FROM case_criteria WHERE case_id = '<CASE-ID>'`
6. Query policy criteria to understand criterion text.

### Decision Rules

- **P2P outcome**: From `p2p_events.outcome`. Map to `overturn_to_approval` or `uphold_intended_adverse_decision`.
- **Final status**: `approved` if overturned; `denied` if upheld.
- **New information changed review**: From `p2p_events.new_information`. If non-null and material → `true`.
- **Criteria results**: Map each criterion (PET-IND, PET-FACTOR) from `case_criteria.result`. `met` / `not_met` / `unclear`.
- **Unresolved criteria**: Criteria where result is `not_met` or `unclear`, sorted ascending by criterion ID.
- **Missing PET factors**: List each factor from the domain-specific enum that is not supported by evidence (e.g. `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`). Use the order in the answer template.
- **Letter type**: `approval` if approved; `denial` if denied.
- **Recommended alternative**: `SPECT MPI` when PET is denied for cardiac imaging; `PET MPI` when SPECT is denied; `none` when no alternative applies.
- **Internal appeal deadline**: For adverse determinations, add 180 calendar days to the final determination date. Use `null` for approvals.

### Basis Audit

- `controlling_record_ids`: P2P event ID and key clinical documents.
- `exception_record_ids`: Unresolved criteria IDs, then missing factor enums.
- `precedence_record_order`: P2P event → clinical documents → unresolved criteria.

## Margin Queue (UM-Finance)

**Source precedence**: `margin_threshold_then_charge_sensitivity`

**Tables involved**: service_margin

### Workflow

1. Query service margin rows by the `queue_row_ids` from `task_context.json`:
   `SELECT * FROM service_margin WHERE month_id IN ('<id1>', '<id2>', '<id3>')`
2. Compute per row:
   - `total_cost = variable_cost + fixed_cost_allocated`
   - `margin = net_revenue - total_cost`
   - `revenue_to_cost_ratio = net_revenue / total_cost`
   - `below_threshold = revenue_to_cost_ratio < threshold`
   - `charge_sensitive = service_margin.charge_sensitive = 1`

### Decision Rules

- **Row ordering**: Same order as `queue_row_ids` in task context.
- **Threshold**: Use the `revenue_to_cost_threshold` from task context.
- **Recommended action**:
  - `below_threshold = true` → `payer_contract_review`
  - `charge_sensitive = true` → `monitor_charge_sensitive`
  - Neither → `monitor_no_action`
- **Below-threshold segments**: Payer segments where any row has `below_threshold = true`. Sorted alphabetically.
- **Charge-sensitive segments**: Payer segments where any row has `charge_sensitive = true`. Sorted alphabetically.
- **Top issue**: The below-threshold row with the lowest `revenue_to_cost_ratio`. Format as `{segment}_{cpt}`. If none below threshold → `none`.
- **Gap to 120%**: For the top below-threshold issue: `(total_cost × threshold) - net_revenue`. Round to cents. If no below-threshold → 0.

### Basis Audit

- `controlling_record_ids`: All queue row month IDs.
- `exception_record_ids`: The below-threshold row IDs.
- `precedence_record_order`: Below-threshold rows first (by ratio ascending), then charge-sensitive rows, then remaining rows.

## Currency and Precision Rules

- All dollar amounts: round to 2 decimal places.
- Revenue-to-cost ratios: round to 4 decimal places.
- Dates: ISO 8601 `YYYY-MM-DD`.
- Modifiers: use `null` (not empty string) when absent.
- CPT codes in lists: sort ascending.
