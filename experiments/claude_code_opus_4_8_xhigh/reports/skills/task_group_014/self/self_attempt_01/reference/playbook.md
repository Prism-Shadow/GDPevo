# Per-archetype playbook

Each archetype maps to one `source_precedence`. Field names below refer to the answer
template for that task type — always re-read the actual `answer_template.json`, since
required keys and enums are authoritative and can vary. Never hardcode a prior task's
computed values; derive every value from the environment records for the current target.

---

## A. UM prior-auth determination — `current_clinical_records_over_stale_export`

**Pull:** `cases` (target), `members` + `plans` (active coverage on service dates),
`request_lines`, `policy_criteria` (for `cases.policy_id`), `case_criteria`, `documents`,
`document_facts`, `authorizations`.

**Decide:**
1. Read each required criterion result from `case_criteria` (e.g. active coverage,
   diagnosis, functional deficit, plan of care, unit limit).
2. If all required criteria `met` → recommend **approve**; `final_status` approved; route
   `nurse_approval`; letter `approval`; next_action `issue_approval`.
3. If a required criterion is `not_met`/`unclear`, use its `policy_criteria.result_if_missing`:
   `pend` → recommend `pend_for_information` / route `pending_information` / letter
   `information_request` / next_action `request_more_information`; `deny` → `deny` /
   `medical_director_review` or adverse letter as the template's route enums allow. Escalate
   to MD (`escalate_to_md` / `medical_director_review`) when clinical judgment beyond nurse
   scope is required.
4. **Authorization block** comes from the `authorizations` row: auth_number, approved_units,
   approved_start/end, approved_cpt (split the comma list into ascending CPT codes),
   modifier.
5. **evidence_documents** = `documents` with `is_current=1` (ascending document_id).
   **excluded_documents** = `documents` with `is_current=0` (stale exports/legacy),
   ascending document_id.

**basis_audit:** controlling = current documents + met criteria + auth record; exceptions =
stale/excluded documents (and any unmet-criterion gaps first if present).

---

## B. Pharmacy coverage appeal + assistance intake — `payer_appeal_before_manufacturer_assistance`

**Pull:** `appeals` (by case_id/appeal_id), `cases`, `drug_trials`, `case_criteria`,
`policy_criteria`, `documents`, `assistance_screen`.

**Decide:**
1. `appeal_path` from `appeals.appeal_path`; `expedited` = whether an expedited path/attestation
   is requested (`expedited_attestation != not_requested`); `appeal_deadline` from `appeals`;
   `owner` from `appeals.owner`.
2. **Failure classification** from `drug_trials`: `documented=1` → `documented_failures`;
   `documented=0` or "referenced without fill record" → `undocumented_or_insufficient_failures`.
   Emit lowercase medication names, alphabetical.
3. **criteria_results** from `case_criteria` filtered to the template keys (auth, denial,
   rationale, failures). A failures criterion with one documented + one unproven trial is
   typically `partial`.
4. **required_packet_items** — parse `appeals.notes`/policy; order payer-appeal items
   (denial_notice, member_authorization, prescriber_rationale, formulary_failure_evidence)
   before assistance items (household_income_proof). **missing_packet_items** = required items
   not evidenced (a referenced-but-unproven failure → the missing fill/formulary evidence),
   appeal-evidence gaps before assistance gaps.
5. **assistance** from `assistance_screen`: program_name, status (map
   `pending_missing_income_proof` → `eligible_missing_information`; ready → `eligible_ready`;
   ineligible → `not_eligible`; no program → `not_applicable`), missing_fields (alphabetical).
6. **next_action** from route + gaps (e.g. request_more_information when appeal evidence is
   incomplete; complete_expedited_appeal_and_request_income_proof only when expedited).

**basis_audit:** controlling = appeal record + on-file docs + met criteria; exceptions =
criteria/packet gaps first, then assistance information gaps.

---

## C. Claim repricing / payment-integrity correction — `effective_benchmark_by_plan_modifier_and_date`

**Pull:** `claims` (target), `claim_lines` (order by line_number), `members` (plan_type),
`payment_benchmarks` (service_domain), `authorizations` (auth_number if not on the claim).

**Decide:**
1. Determine plan_type via `claims.member_id → members.plan_type`.
2. For each claim line, choose the benchmark matching payer + plan_type + service_domain +
   cpt_code + modifier whose `[effective_start, effective_end]` contains the line's
   `service_date`. `benchmark_source` = its `source_name`; `benchmark_version` =
   `source_version`.
3. **`stale_source_rejected`** = the schedule whose window ended before the service date
   (the one the claim was mispaid against, e.g. a legacy export); ignore "distractor"
   schedules that don't match the CPT/plan. Use `none` only if nothing was rejected.
4. Line math: `correct_allowed_amount = allowed_amount * units`;
   `recovery_amount = correct_allowed_amount - paid_amount`;
   disposition = `correct_upward` if correct>paid, `correct_downward` if correct<paid,
   `no_change` if equal, `deny_line` if not payable. `modifier` → `null` when absent.
5. Totals: `correct_allowed_total` = sum of line correct allowed; `paid_total` from the
   claim; `recovery_amount` = correct_allowed_total − paid_total (an underpayment when
   positive). Round currency to 2 decimals.
6. `resubmission_route` (e.g. `payment_integrity_correction`) and `priority` per the enums.

**basis_audit:** controlling = claim, chosen benchmark IDs, claim lines, auth; exceptions =
the rejected stale/legacy benchmark ID (and distractor if noted).

---

## D. Peer-to-peer closure — `new_patient_specific_p2p_information`

**Pull:** `cases`, `request_lines` (requested_cpt), `policy_criteria`, `case_criteria`,
`p2p_events`, `documents`, `authorizations`.

**Decide:**
1. `requested_cpt` from the request line.
2. `p2p_outcome` and `final_status` from `p2p_events` (outcome
   `uphold_intended_adverse_decision` / `overturn_to_approval`; final_status e.g. `denied`).
3. **criteria_results** filtered to the template's PET keys (indication, over-SPECT factor)
   from `case_criteria`. `unresolved_criteria` = still `not_met`/`unclear` required criteria,
   ascending criterion ID.
4. `new_information_changed_review` = true only if the P2P `new_information` supplied
   patient-specific facts that changed the result; false when notes say none supplied.
5. `missing_pet_factors` = the PET-over-SPECT factors still unsupported
   (prior_equivocal_spect, bmi_limitation, attenuation_artifact), in choices order.
6. `letter_type` (`denial` when upheld adverse, `approval` when overturned),
   `recommended_alternative` (`SPECT MPI` when PET not justified; else `none`/`PET MPI`).
7. `internal_appeal_deadline` = final adverse determination date + plan window (e.g. 180
   calendar days) when adverse; `null` otherwise.

**basis_audit:** controlling = P2P event, criteria, auth, current clinical note; exceptions =
unmet criterion / missing-factor gaps.

---

## E. Therapy-margin queue analysis — `margin_threshold_then_charge_sensitivity`

**Pull:** `service_margin` rows for exactly the `queue_row_ids` in
`task_context.finance_memo` (do not add other rows). Threshold from task_context
(e.g. `revenue_to_cost_threshold` 1.2).

**Compute per row (keep queue_row_ids order):**
- `total_cost = variable_cost + fixed_cost_allocated`
- `margin = net_revenue - total_cost`
- `revenue_to_cost_ratio = net_revenue / total_cost` (precision per template, e.g. 4 dp)
- `below_threshold = ratio < threshold`
- `charge_sensitive` from the row flag (1→true)
- `recommended_action`: below_threshold → `payer_contract_review`; else charge_sensitive →
  `monitor_charge_sensitive`; else `monitor_no_action`.

**Aggregate:**
- `below_threshold_segments` / `charge_sensitive_segments` = payer_segments meeting each
  condition, alphabetical.
- `top_issue` = the `{segment}_{cpt}` for the worst below-threshold row (lowest ratio /
  largest gap); `none` if no row is below threshold.
- `gap_to_120pct = threshold * total_cost - net_revenue` for that top row (2 dp).

**basis_audit:** controlling = below-threshold row IDs (highest priority first); exceptions =
charge-sensitive-only rows.

---

## F. Mixed appeal-deadline-driven review — `appeal_deadline_then_clinical_then_payment_integrity`

Not represented in the training set but present in the `source_precedence` enum. Use it for
a task that spans appeal timeliness **and** clinical criteria **and** payment integrity.
Order records by appeal-deadline urgency first, then clinical evidence, then payment-integrity
records, and reflect that ordering in `precedence_record_order`. Otherwise combine the
relevant procedures above for the dimensions the task actually asks for.
