# Task Domain Workflows

Step-by-step workflows for each of the five Northstar task domains.

## 1. UM Nurse Prior-Authorization Determination

**Trigger**: Task references a case_id in the physical_therapy service domain. The prompt asks for a "determination summary" or "UM nurse determination."

**Tables**: cases, request_lines, members, plans, providers, documents, document_facts, policy_criteria, case_criteria, authorizations

**Policy**: POL-PT-LUMBAR-2026

### Steps

1. **Load the case**:
   ```sql
   SELECT * FROM cases WHERE case_id = '<CASE_ID>';
   ```
   Confirm the case has `service_domain = 'physical_therapy'` and `policy_id = 'POL-PT-LUMBAR-2026'`.

2. **Load the member, plan, and provider**:
   ```sql
   SELECT m.*, p.* FROM members m JOIN plans p ON m.plan_id = p.plan_id WHERE m.member_id = '<MEMBER_ID>';
   SELECT * FROM providers WHERE provider_id = '<PROVIDER_ID>';
   ```

3. **Load the request lines**:
   ```sql
   SELECT * FROM request_lines WHERE case_id = '<CASE_ID>';
   ```
   Note: CPT codes, requested units, requested start/end dates, and modifier.

4. **Load documents and classify**:
   ```sql
   SELECT * FROM documents WHERE case_id = '<CASE_ID>' ORDER BY document_date;
   ```
   Separate into current (`is_current = 1`) and stale (`is_current = 0`).
   - Current documents become `evidence_documents`.
   - Stale documents become `excluded_documents`.

5. **Load document facts from current documents only**:
   ```sql
   SELECT * FROM document_facts WHERE case_id = '<CASE_ID>' AND document_id IN (<CURRENT_DOC_IDS>);
   ```
   These are the facts supporting criteria evaluation.

6. **Load criteria and case criteria results**:
   ```sql
   SELECT pc.*, cc.result, cc.evidence_fact_ids, cc.gap_description, cc.reviewer_scope
   FROM policy_criteria pc
   LEFT JOIN case_criteria cc ON pc.criterion_id = cc.criterion_id AND cc.case_id = '<CASE_ID>'
   WHERE pc.policy_id = 'POL-PT-LUMBAR-2026'
   ORDER BY pc.criterion_key;
   ```

7. **Evaluate criteria**: For each criterion key (PT-ACTIVE, PT-DEFICIT, PT-DX, PT-POC, PT-UNITS):
   - Use `case_criteria.result` as the primary evaluation.
   - Cross-check with document_facts whose `supports_criteria` references the same criterion_id.
   - Map to the answer template's `criteria_results` object.

8. **Determine recommendation**:
   - All criteria `met` → `approve`, `approved`, `nurse_approval`.
   - Any `unclear` with `reviewer_scope = md_required` → `escalate_to_md`, `md_review_required`, `medical_director_review`.
   - Any `not_met` → `deny`.
   - Mixed → `pend_for_information`.

9. **Build authorization** (when approving):
   - Query the `authorizations` table for the auth record:
   ```sql
   SELECT * FROM authorizations WHERE case_id = '<CASE_ID>';
   ```
   - Use `auth_number`, `approved_units`, `approved_start`, `approved_end`, `approved_cpt` (split on commas), `approved_modifier`.

10. **Build basis_audit**: Use `current_clinical_records_over_stale_export`.

## 2. Pharmacy Appeals and Assistance Intake

**Trigger**: Task references an appeal_id. The prompt mentions "pharmacy appeals coordinator," "coverage exception appeal," or "assistance screen."

**Tables**: appeals, cases, drug_trials, assistance_screen, documents, policy_criteria, members

**Policy**: POL-DRUG-EXC-2026

### Steps

1. **Load the appeal**:
   ```sql
   SELECT * FROM appeals WHERE appeal_id = '<APPEAL_ID>';
   ```

2. **Load the parent case**:
   ```sql
   SELECT * FROM cases WHERE case_id = '<CASE_ID>';
   ```

3. **Load drug trials**:
   ```sql
   SELECT * FROM drug_trials WHERE case_id = '<CASE_ID>' ORDER BY medication;
   ```
   Classify each trial:
   - `documented = 1` → `documented_failures` (alphabetical by medication name).
   - `documented = 0` → `undocumented_or_insufficient_failures`.

4. **Load assistance screen**:
   ```sql
   SELECT * FROM assistance_screen WHERE case_id = '<CASE_ID>';
   ```
   Use `program_name`, `assistance_status`, `missing_fields` (split on commas).

5. **Load policy criteria**:
   ```sql
   SELECT * FROM policy_criteria WHERE policy_id = 'POL-DRUG-EXC-2026' ORDER BY criterion_key;
   ```

6. **Evaluate criteria results**:
   - `DRUG-AUTH`: Check for member authorization (from appeal packet/docs).
   - `DRUG-DENIAL`: Check `appeals.denial_date` is present and denial notice exists.
   - `DRUG-RATIONALE`: Check for prescriber rationale documentation.
   - `DRUG-FAILURES`: From drug_trials — if all documented failures satisfy the requirement → `met`; if some are undocumented → `partial`.

7. **Determine packet requirements and gaps**:
   - Required items: denial_notice, member_authorization, prescriber_rationale, formulary_failure_evidence, household_income_proof (ordered: payer appeal items before assistance items).
   - Missing items: any required item not present in the environment records. Order appeal evidence gaps before assistance information gaps.

8. **Determine next action**:
   - Missing packet items → `request_more_information`.
   - Appeal ready and assistance eligible → `submit_assistance_application` or `file_appeal`.
   - Expedited with income proof missing → `complete_expedited_appeal_and_request_income_proof`.
   - Not eligible → `close_not_eligible`.

9. **Build basis_audit**: Use `payer_appeal_before_manufacturer_assistance`.

## 3. Payment Integrity Claim Repricing

**Trigger**: Task references a claim_id. The prompt mentions "payment integrity," "repricing," or "benchmark."

**Tables**: claims, claim_lines, payment_benchmarks, plans, members

**Policy**: POL-CLAIM-RATE-2026

### Steps

1. **Load the claim**:
   ```sql
   SELECT * FROM claims WHERE claim_id = '<CLAIM_ID>';
   ```

2. **Load claim lines**:
   ```sql
   SELECT * FROM claim_lines WHERE claim_id = '<CLAIM_ID>' ORDER BY line_number;
   ```

3. **Load member and plan**:
   ```sql
   SELECT m.plan_type FROM members m WHERE m.member_id = '<MEMBER_ID>';
   ```

4. **Load relevant benchmarks**:
   ```sql
   SELECT * FROM payment_benchmarks
   WHERE payer = '<PAYER>' AND plan_type = '<PLAN_TYPE>'
     AND service_domain IN (SELECT DISTINCT service_domain FROM cases WHERE case_id = '<CASE_ID>')
   ORDER BY cpt_code, effective_start DESC;
   ```
   Also query `/api/rate-schedules` for rate schedule listing.

5. **Match benchmarks per line**:
   For each claim line, find the benchmark matching `cpt_code` and `modifier` (null matches null). From the matches, select the one with the most recent `effective_start` that covers the line's `service_date`.

6. **Identify the benchmark source and stale source**:
   - Winning benchmark's `source_name` → `benchmark_source`.
   - Benchmark with older effective_end or from "Legacy Imaging Export" → `stale_source_rejected`.

7. **Compute corrections per line**:
   - `correct_allowed_amount` = `allowed_amount` × `units` (round to 2 decimals).
   - `recovery_amount` = `correct_allowed_amount` - `paid_amount`.
   - `disposition`: `correct_upward` if recovery positive, `correct_downward` if negative, `no_change` if zero, `deny_line` if line should be denied.

8. **Compute totals**:
   - `paid_total` = sum of line `paid_amount`.
   - `correct_allowed_total` = sum of line `correct_allowed_amount`.
   - `recovery_amount` = `correct_allowed_total` - `paid_total`.

9. **Build basis_audit**: Use `effective_benchmark_by_plan_modifier_and_date`.

## 4. Peer-to-Peer Coordinator Summary

**Trigger**: Task references a p2p event or case with "peer-to-peer" in the prompt.

**Tables**: p2p_events, cases, request_lines, documents, policy_criteria, case_criteria

**Policy**: POL-PET-MPI-2026

### Steps

1. **Load the P2P event**:
   ```sql
   SELECT * FROM p2p_events WHERE case_id = '<CASE_ID>';
   ```
   The `outcome` and `final_status` fields are the P2P determination.

2. **Load the case and request lines**:
   ```sql
   SELECT * FROM cases WHERE case_id = '<CASE_ID>';
   SELECT * FROM request_lines WHERE case_id = '<CASE_ID>';
   ```

3. **Load clinical documents**:
   ```sql
   SELECT * FROM documents WHERE case_id = '<CASE_ID>' ORDER BY document_date;
   ```

4. **Load criteria**:
   ```sql
   SELECT pc.*, cc.result, cc.gap_description
   FROM policy_criteria pc
   LEFT JOIN case_criteria cc ON pc.criterion_id = cc.criterion_id AND cc.case_id = '<CASE_ID>'
   WHERE pc.policy_id = 'POL-PET-MPI-2026'
   ORDER BY pc.criterion_key;
   ```

5. **Evaluate P2P outcome**:
   - `outcome = 'overturn_to_approval'` → `p2p_outcome = 'overturn_to_approval'`, `final_status = 'approved'`.
   - `outcome = 'uphold_intended_adverse_decision'` → `p2p_outcome = 'uphold_intended_adverse_decision'`, `final_status = 'denied'`.

6. **Check for new information**:
   - If `p2p_events.new_information` is "none" or empty → `new_information_changed_review = false`.
   - If the P2P event has substantive new information → `new_information_changed_review = true`.

7. **Resolve criteria**:
   - `PET-IND`: If met → `met`, otherwise `not_met`.
   - `PET-FACTOR`: If any PET-over-SPECT factor is supported → `met`, otherwise `not_met`.
   - Unresolved criteria: any criterion that is `not_met` or `unclear` → list in `unresolved_criteria` (ascending criterion ID).

8. **Determine missing PET factors**: When `PET-FACTOR` is `not_met`, list all three specific factors in `missing_pet_factors`:
   `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`.

9. **Determine letter and alternative**:
   - Approved → `approval` letter, `none` alternative.
   - Denied → `denial` letter, `SPECT MPI` recommended alternative.

10. **Compute internal appeal deadline**: When denied, add 180 days to the reporting date (or the final determination date from `task_context.local_memo`).

11. **Build basis_audit**: Use `new_patient_specific_p2p_information`.

## 5. UM-Finance Therapy Margin Queue

**Trigger**: Task references a queue_id. The prompt mentions "margin queue," "UM-finance," or "therapy margin."

**Tables**: service_margin

### Steps

1. **Load the queue rows** using the `queue_row_ids` from `task_context.json`:
   ```sql
   SELECT * FROM service_margin WHERE month_id IN (<QUEUE_ROW_IDS>);
   ```

2. **Compute per-row metrics**:
   - `total_cost` = `variable_cost` + `fixed_cost_allocated` (round to 2 decimals).
   - `margin` = `net_revenue` - `total_cost` (round to 2 decimals).
   - `revenue_to_cost_ratio` = `net_revenue` / `total_cost` (round to 4 decimals).

3. **Apply the threshold** (from `task_context.finance_memo.revenue_to_cost_threshold`, default 1.2):
   - If `revenue_to_cost_ratio` < 1.2 → `below_threshold = true`, `recommended_action = 'payer_contract_review'`.
   - If `revenue_to_cost_ratio` >= 1.2 → `below_threshold = false`.
   - If not below threshold but `charge_sensitive = 1` → `recommended_action = 'monitor_charge_sensitive'`.
   - If not below threshold and `charge_sensitive = 0` → `recommended_action = 'monitor_no_action'`.

4. **Build segment lists**:
   - `below_threshold_segments`: distinct payer_segments where any row is below threshold (alphabetical).
   - `charge_sensitive_segments`: distinct payer_segments where any row is charge sensitive (alphabetical).

5. **Determine top issue**:
   - Among below-threshold rows, compute the gap for each: `gap_to_120pct` = (`total_cost` × 1.2) - `net_revenue`.
   - The row with the largest gap → format as `{payer_segment}_{cpt_code}` (e.g., `medicaid_97110`).
   - `gap_to_120pct` = the largest gap value (round to 2 decimals).

6. **Build basis_audit**: Use `margin_threshold_then_charge_sensitivity`.
