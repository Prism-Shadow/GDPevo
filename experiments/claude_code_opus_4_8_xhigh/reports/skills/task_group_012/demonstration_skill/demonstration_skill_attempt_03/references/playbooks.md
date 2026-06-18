# Task-shape playbooks

The PeopleOps Console review family recurs in a few shapes. Each shape names a
subject (employee / case / opening), pulls a known set of endpoints, and fills a
template. Identify the shape from the prompt verb + subject, then follow the
matching playbook. All placeholders (`<EMP-ID>`, `<CASE-ID>`, `<owner-team>`,
`<N>` days, `<file>.pdf`, etc.) stand for values you read live; never hardcode.

| Prompt cue | Shape | Primary endpoints |
|---|---|---|
| "verify onboarding closeout", "leave + payroll setup before approving close" | **Onboarding closeout** | employees, payroll-ledgers, documents, messages, cases/audit |
| "validate leave source precedence", "which leave policy/balance is authoritative" | **Leave precedence** | employees, payroll-ledgers (leave rows), policies, audit |
| "payroll assignment and accrual readiness" | **Payroll readiness** | payroll-ledgers (salary rows), policies, audit |
| "review case ... folder readiness and formal notice quality" | **Folder + notice review** | cases/<id>, documents, messages, audit |
| "reconcile recruitment outcome packet for <opening>" | **Recruitment reconciliation** | recruitment, cases/<id>, policies, messages, audit |

---

## 1. Onboarding closeout

Goal: confirm the employee's effective leave setup and payroll setup using the
authoritative records, list what to exclude, and decide the closeout action.

1. `GET /api/employees?q=<EMP-ID>` — note `leave_balance_days` (corroboration
   only; the assignment, not the profile, is authoritative).
2. `GET /api/payroll-ledgers?q=<emp-number>` — returns leave + salary rows.
   - Leave: pick the *leave assignment* row with `status=Approved` for the
     period → `effective_leave_policy` = its `policy_name`, `annual_days` = its
     approved days, `assignment_id` = its `ledger_id`. Exclude the `Superseded`
     and `Draft` leave rows into `excluded_leave_ids`.
   - Salary: pick the `Submitted` salary row → `payroll_assignment_id`,
     `base_salary`, `payroll_status` = `submitted`. Exclude the `Draft` salary
     row into `excluded_payroll_ids`.
3. Check the folder (`GET /api/documents?q=<EMP-ID>`) and any notice
   (`GET /api/messages?q=<EMP-ID>`) for defects. If there are none and an
   approval exists, records are clean.
4. Decide:
   - Clean records → `closeout_action = approve_onboarding_close`,
     `approval_closeout_gate = approval_sufficient_when_records_clean`,
     `final_control_result = approve_closeout`.
   - Defective folder/notice → `block_close_and_reissue_notice` /
     `approval_not_sufficient_when_folder_or_notice_defective` /
     `hold_for_folder_and_notice_defects`.
   - Record inconsistencies needing fix → `open_records_remediation`.
5. Source labels: `leave_source = leave_assignment_history` (when the assignment
   history is authoritative, vs `employee_profile_summary` / `case_summary_only`);
   `leave_precedence_source = approved_assignment_current_period`;
   `payroll_source_status = submitted`.

## 2. Leave precedence

Goal: decide which leave policy + balance are authoritative for the period, and
whether the profile summary is stale.

1. `GET /api/employees?q=<EMP-ID>` — read the profile policy/balance (the thing
   that may be stale).
2. `GET /api/payroll-ledgers?q=<emp-number>` — find the formal *leave
   assignment* row with `status=Approved` for the period. That is authoritative:
   `effective_leave_policy` = its `policy_name`, `assignment_id` = its
   `ledger_id`, `balance_days` = its approved days. Ignore HRMS-ledger /
   adjustment rows.
3. `GET /api/policies?q=leave` (or the case's `policy_refs`) — the precedence
   clause states "approved/submitted assignment controls; drafts/obsolete
   excluded even when profile conflicts."
4. `GET /api/audit?q=<EMP-ID>` and `/api/audit/<id>` — the controlling event is
   the leave/profile-mismatch one; its `detail` states the result (e.g. the
   profile is stale and the approved assignment controls).
5. Fill: `precedence_source = approved_assignment_over_profile`;
   `profile_policy_ignored = true` (when the assignment overrides the profile);
   `audit_result = profile_summary_stale`; `next_action = update_employee_summary`;
   `leave_precedence_source = approved_assignment_current_period`;
   `audit_scope = leave_source_precedence_only`.
6. **Scope:** put the leave/profile audit event in `supporting_audit_event_ids`
   and put adjacent document/notice audit events in `excluded_audit_event_ids`
   (they are off-scope for a leave decision).

## 3. Payroll readiness

Goal: pick the submitted salary assignment, exclude the draft, and judge accrual
readiness.

1. `GET /api/payroll-ledgers?q=<emp-number>` — pick the `Submitted` salary row →
   `salary_assignment_id`, `base_salary`, `effective_date`,
   `payroll_source_status = submitted`. Put the `Draft` row in
   `excluded_assignment_id`; `draft_exclusion_rule = exclude_draft_assignment`.
2. The submitted row references the accrual batch → `accrual_batch_id`.
3. `GET /api/audit?q=<EMP-ID>` / `/api/audit/<id>` — the payroll-readiness event's
   `detail` states the QA result. Map it to `control_result` (commonly
   `ready_with_monitoring` when submitted matches the batch) and set
   `accrual_ready = true` accordingly.
4. `audit_scope = payroll_assignment_readiness`.

## 4. Folder + notice review

Goal: decide a policy case, judge folder readiness and notice quality, pick the
controlling audit event, and route remediation.

1. `GET /api/cases/<CASE-ID>` — read `approvals` (final approver + decision +
   note → `approval_authority`, `approval_event_id`, `final_decision`),
   `audit_events`, `policy_refs`.
   - "Approved with conditions" → `final_decision = approved_with_conditions`.
2. `GET /api/documents?q=<CASE-ID>` — set comparison:
   `folder_ready = required_files ⊆ files AND required_tags ⊆ tags`;
   `missing_files = required_files \ files`;
   `required_tag_present = required_tags ⊆ tags`.
3. `GET /api/messages?q=<CASE-ID>` (the notice packet) — `notice_quality` =
   `valid`/`defective`; `notice_defects` from the packet's `defects` (mapped to
   the allowed defect codes); `notice_evidence_source = notice_packet_inspection`.
4. Audit: the case's notice/document QA event is the controlling
   `audit_event_id` and goes in `supporting_audit_event_ids`; off-scope events go
   in `excluded_audit_event_ids`; `audit_scope = document_notice_findings_only`.
5. Gating + routing:
   - `approval_closeout_gate = approval_not_sufficient_when_folder_or_notice_defective`
     when anything is defective; else `approval_sufficient_when_records_clean`.
   - `closeout_blockers` ⊆ {`missing_required_files`, `missing_required_tags`,
     `defective_formal_notice`} — include exactly the ones that apply.
   - `next_action` / `escalation_action` / `final_control_result`:
     defects → `block_close_and_reissue_notice` (next),
     `open_records_remediation` (escalation), and
     `hold_for_folder_and_notice_defects` (final).
   - `records_remediation_owner` is read from the remediation/audit package
     owner (one of the template's allowed owner labels) — do not invent it.
   - `notice_remediation_action = reissue_defective_notices` when a notice is
     defective; `folder_required_tag_action = add_required_tag` only if a tag is
     missing, else `no_tag_action`.
   - `evidence_source_order = approval_history_folder_notice_audit` (approval
     first, then folder, then notice, then audit).

## 5. Recruitment reconciliation

Goal: determine candidate outcomes, the accepted offer, total cost, follow-ups,
and the payroll handoff.

1. `GET /api/recruitment?q=<OPENING-ID>` (corroborate with `GET /api/cases/<id>`):
   - Candidate outcomes from `committee_decision`: Selected →
     `selected_candidate`; Waitlisted → `waitlisted_candidates`; Rejected →
     `rejected_candidates`. Arrays hold **candidate IDs only**.
   - Offer: the selected candidate's row in `offer_register` →
     `offer_id`, `offer_base_salary`, `selected_offer_status` (must read
     `accepted` to be accepted).
   - `recruitment_cost_total` = sum of every `cost_ledger` line `amount`;
     `cost_source = recruitment_cost_ledger`.
   - `notice_followup_required` = candidate IDs whose notice is not sent (from
     `notice_packets` / `notice_status`); split into
     `waitlisted_followup_action = send_waitlist_notice` and
     `rejected_followup_action = send_rejection_notice` as applicable.
2. Handoff (from the recruiting payroll-handoff policy clause):
   - Accepted offer but no submitted assignment yet → `onboarding_handoff =
     create_payroll_precheck`; `payroll_handoff_gate = accepted_offer_only`;
     `payroll_assignment_status_required = submitted_after_acceptance`;
     `draft_payroll_allowed = false`;
     `handoff_control_result = submitted_handoff_required_after_acceptance`.
3. Sources: `candidate_status_source = interview_feedback_and_offer`;
   `candidate_outcome_control = committee_decision_with_offer_confirmation`;
   `notice_quality_source = notice_packet_inspection`;
   `offer_exclusion_reason_for_waitlisted = no_accepted_status_or_offer`
   (a waitlisted candidate has no accepted offer, so no handoff for them).
