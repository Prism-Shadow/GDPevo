# Task-family decision recipes

Identify the family from the target-id prefix, `request_type`, and `service_domain`, then
apply its recipe. All values below are derived per case from the environment — nothing here
is a fixed answer.

---

## 1. UM nurse determination (prior authorization / nurse review)

Signals: `request_type = prior_authorization`, `current_stage = nurse_review`, a `CASE-…`
target, a determination template (recommendation / final_status / route / authorization /
criteria_results / evidence_documents / excluded_documents / determination_letter /
next_action).

Steps:
1. Read `case_criteria.result` for every criterion the template lists — these are the graded
   `criteria_results` values directly.
2. Split `documents`: `is_current = 1` → `evidence_documents`; `is_current = 0` (stale export)
   → `excluded_documents`. Sort each ascending by `document_id`.
3. Read the `authorizations` row for the approved fields (auth_number, approved_units,
   approved_start/end, `approved_cpt` split into an ascending-CPT list, modifier). `status`
   (e.g. `recommended_approval` / `denied`) confirms the disposition.
4. Decide the recommendation/route/status/letter/next_action from the criteria + auth status:
   - all approval_required criteria `met` → approve · nurse_approval · approved · approval
     letter · issue_approval.
   - a criterion `not_met` whose `result_if_missing = deny` → deny · adverse determination.
   - a gap (`unclear`/missing) whose `result_if_missing = pend` → pend_for_information ·
     pending_information · request_more_information.
   - `result_if_missing = uphold`/escalate, or reviewer_scope beyond nurse → escalate_to_md /
     medical_director_review, or peer_to_peer.
5. `source_precedence = current_clinical_records_over_stale_export`.

---

## 2. Pharmacy coverage appeal + manufacturer-assistance intake

Signals: `APPEAL-…` target with an `appeal_id`, `request_type = coverage_exception`,
specialty-drug domain, template with appeal_path / documented_failures / packet items /
assistance.

Steps:
1. `drug` — from the case summary / `assistance_screen.program_name` (e.g. the program names
   the drug), lowercased where the field asks for it.
2. `appeal_path`, `expedited` (`expedited_attestation` = `requested` → true, else false),
   `appeal_deadline`, `owner` — read straight from the `appeals` row.
3. Prior-medication failures from `drug_trials`: `documented = 1` → `documented_failures`;
   `documented = 0` (mentioned, no fill/record) → `undocumented_or_insufficient_failures`.
   Lowercase medication names, alphabetical.
4. `criteria_results` from `case_criteria.result` (met / not_met / partial / …).
5. Packet: `required_packet_items` from `appeals.notes` / policy_criteria, mapped to the
   template enum, **payer-appeal items before assistance items**. `missing_packet_items` =
   required items not yet evidenced (a `partial` failure → the missing fill record; a missing
   assistance field → its packet item), ordered **appeal-evidence gaps before assistance gaps**.
6. `assistance` object: `program_name`, `status` (`assistance_status` → e.g.
   pending_missing_income_proof ⇒ eligible_missing_information), `missing_fields`
   (`assistance_screen.missing_fields`, alphabetical).
7. `next_action` — resolve the payer appeal first, then assistance: outstanding appeal
   evidence and/or missing income proof → request_more_information (or the expedited-complete
   action only when the appeal is expedited).
8. `source_precedence = payer_appeal_before_manufacturer_assistance`.

---

## 3. Payment-integrity claim repricing

Signals: `CLAIM-…` target, `request_type = claim_payment_review`, currency + lines template
(benchmark_source / paid_total / correct_allowed_total / recovery_amount / lines).

Steps:
1. Read `claims` (paid_total, auth_number, case_id) and `claim_lines` in `line_number` order.
2. For each line, find the **controlling benchmark** in `payment_benchmarks`: same `payer`,
   member `plan_type`, `service_domain`, `cpt_code`, and `modifier` (null matches null), whose
   `[effective_start, effective_end]` window contains the line's `service_date`. That current
   schedule's `source_name`/`source_version` are `benchmark_source`/`benchmark_version`.
3. The expired/older schedule for the same code (window ended before the service date, e.g. a
   "Legacy"/stale export) is `stale_source_rejected`. A schedule that doesn't match the
   claim's cpt/modifier/plan_type (a "Distractor") is simply not selected.
4. Per line: `correct_allowed_amount = allowed_amount × units` (round to cents);
   `recovery_amount = correct_allowed_amount − paid_amount`; `disposition` =
   correct_upward (corrected > paid) / correct_downward (corrected < paid) / no_change /
   deny_line. Use `null` for an absent `modifier`, never `""`.
5. Totals: `correct_allowed_total = Σ line correct_allowed_amount`;
   `recovery_amount = correct_allowed_total − paid_total` (underpayment when corrected > paid).
6. `resubmission_route` (e.g. payment_integrity_correction) and `priority` per the enums.
7. `source_precedence = effective_benchmark_by_plan_modifier_and_date`.

---

## 4. Peer-to-peer close-out

Signals: `P2P-…` target, `request_type = peer_to_peer`, a completed `p2p_events` row.

Steps:
1. `p2p_id`, `p2p_outcome` (`overturn_to_approval` / `uphold_intended_adverse_decision`),
   `final_status` — from the `p2p_events` row. `requested_cpt` — from the `request_lines` row.
2. `criteria_results` from `case_criteria.result` for the template's criterion keys.
   `unresolved_criteria` = criterion ids not `met`, ascending id order (empty list if none).
3. `new_information_changed_review` — true only if `p2p_events.new_information` supplied
   material new patient-specific facts that changed the outcome; an "uphold" with "no new
   info" ⇒ false.
4. `missing_pet_factors` — the PET-over-SPECT factors still unsupported (read from the p2p
   note / document_facts), in the template's `choices` order.
5. `letter_type` (approval / denial / partial_denial / no_letter) and `recommended_alternative`
   (an adverse PET decision typically recommends the alternative modality, e.g. SPECT MPI;
   otherwise `none`) per the disposition.
6. `internal_appeal_deadline` — if the final result is adverse, compute
   `final_adverse_determination_date + N days` using the internal-appeal window the memo
   states (e.g. 180 days from the P2P/determination date). `null` when not adverse. Output
   ISO `YYYY-MM-DD`.
7. `source_precedence = new_patient_specific_p2p_information`.

---

## 5. UM-finance margin queue

Signals: `QUEUE-…` target, a finance memo with `queue_row_ids`, a `revenue_to_cost_threshold`,
and a `service_margin` source table.

Steps:
1. Pull only the `service_margin` rows named in `finance_memo.queue_row_ids`; keep the output
   `rows` in that same id order.
2. Per row: `total_cost = variable_cost + fixed_cost_allocated`;
   `margin = net_revenue − total_cost`;
   `revenue_to_cost_ratio = net_revenue / total_cost` (precision 4);
   `below_threshold = ratio < threshold` (threshold from the memo, e.g. 1.2);
   `charge_sensitive` from the row's flag.
3. `recommended_action`: below threshold → payer_contract_review; else charge-sensitive →
   monitor_charge_sensitive; else monitor_no_action.
4. `below_threshold_segments` and `charge_sensitive_segments` — the `payer_segment`s meeting
   each condition, alphabetical. Keep the two concerns separate (a row can be above threshold
   yet charge-sensitive → monitor, not contract review).
5. `top_issue` — the `<segment>_<cpt>` token for the worst below-threshold row (or `none`).
   `gap_to_120pct = threshold × total_cost − net_revenue` for that top row (round to cents).
6. `source_precedence = margin_threshold_then_charge_sensitivity`.

---

## Cross-cutting family: appeal-deadline-driven triage

If a task's controlling constraint is an imminent **appeal deadline** ranked ahead of
clinical and payment-integrity work, use
`source_precedence = appeal_deadline_then_clinical_then_payment_integrity`: order records so
the deadline-bearing appeal record controls first, then clinical evidence, then
payment-integrity records.
