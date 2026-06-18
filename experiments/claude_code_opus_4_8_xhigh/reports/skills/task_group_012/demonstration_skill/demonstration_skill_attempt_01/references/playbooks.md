# Task-Type Playbooks — Reference

The family has a few recurring shapes. Identify the shape from the prompt (it names
the entity and the question), then follow that playbook. In every case the final
output is JSON keyed exactly to that task's `answer_template.json`, with enum fields
emitting the template's normalized labels and list fields treated as sets.

Use `<...>` as placeholders — replace with the entity the prompt names.

## A. Onboarding closeout verification (leave + payroll for an employee)

Goal: pick effective leave + payroll records, list exclusions, decide closeout.

1. `GET /api/employees?q=<EMP-ID>` — note status and the (possibly stale) profile.
2. `GET /api/payroll-ledgers?q=<EMP-ID>` — get every leave + salary row.
3. Leave: choose the `Approved`/`Submitted` `Leave assignment` for the period →
   `effective_leave_policy`, `annual_days`, `assignment_id`; collect Draft/Superseded
   leave assignments into `excluded_leave_ids`. `leave_source` =
   `leave_assignment_history`; `leave_precedence_source` =
   `approved_assignment_current_period`.
4. Payroll: choose the `Submitted` `Salary assignment` → `payroll_assignment_id`,
   `base_salary`; Draft salary rows → `excluded_payroll_ids`. `payroll_status` /
   `payroll_source_status` = `submitted`.
5. If records are clean (authoritative leave + submitted payroll, nothing defective):
   `approval_closeout_gate` = `approval_sufficient_when_records_clean`,
   `closeout_action` = `approve_onboarding_close`,
   `final_control_result` = `approve_closeout`.

## B. Case folder + formal-notice review

Goal: approval, folder readiness, notice quality, controlling audit, next action.

1. `GET /api/cases/<CASE-ID>` — approvals, attachments, embedded audit_events,
   policy_refs.
2. `GET /api/documents?q=<CASE-ID>` — folder readiness via set comparison (Rule 4).
3. `GET /api/messages?q=<CASE-ID>` — notice quality + defects (Rule 5).
4. `GET /api/audit?case_id=<CASE-ID>` — choose the in-scope event (Rule 6); scope =
   `document_notice_findings_only`; off-scope events → `excluded_audit_event_ids`.
5. Approval: `final_decision` (e.g. `approved_with_conditions`),
   `approval_authority`, `approval_event_id` from the approvals array.
6. Apply the gate (Rule 7). Folder/notice defects →
   `approval_not_sufficient_when_folder_or_notice_defective`,
   `closeout_blockers` set, `next_action`/`escalation_action`
   (`block_close_and_reissue_notice` / `open_records_remediation`),
   `notice_remediation_action` = `reissue_defective_notices`,
   `records_remediation_owner` from the records owner,
   `final_control_result` = `hold_for_folder_and_notice_defects`.
7. `evidence_source_order` = `approval_history_folder_notice_audit`;
   `notice_evidence_source` = `notice_packet_inspection` (or `message_notice_inspection`).

## C. Leave source-precedence validation for an employee

Goal: prove the approved assignment overrides a stale profile; cite the audit.

1. `GET /api/employees?q=<EMP-ID>` — profile policy/balance (the summary).
2. `GET /api/payroll-ledgers?q=<EMP-ID>` — pick the `Approved` `Leave assignment`
   (Rule 2) → `effective_leave_policy`, `assignment_id`, `balance_days`.
3. `GET /api/audit?q=<EMP-ID>` (or `?case_id=<CASE>`) — the `leave.*` event is the
   supporting audit; read its result from `detail` (e.g. `profile_summary_stale`).
4. Set `precedence_source` = `approved_assignment_over_profile`,
   `leave_precedence_source` = `approved_assignment_current_period`,
   `profile_policy_ignored` = `true`, `audit_result` from the detail,
   `audit_scope` = `leave_source_precedence_only`,
   `supporting_audit_event_ids` = [the leave event],
   `excluded_audit_event_ids` = any adjacent `folder.*`/`notice.*` event,
   `next_action` typically `update_employee_summary`.

## D. Payroll assignment + accrual readiness for an employee

1. `GET /api/payroll-ledgers?q=<EMP-ID>` — pick `Submitted` `Salary assignment`
   (Rule 3) → `salary_assignment_id`, `base_salary`, `effective_date` from `period`;
   the `Draft` salary row → `excluded_assignment_id`.
2. `GET /api/audit?q=<EMP-ID>` (or `?case_id=<CASE>`) — the `payroll.*` event
   confirms readiness; its `detail` names the accrual batch and gives the result
   label (e.g. `ready_with_monitoring`). Take `accrual_batch_id` (from the salary row
   and/or audit detail), `accrual_ready` (true when the audit says ready),
   `audit_event_id`, `control_result` from the audit result.
3. `payroll_source_status` = `submitted`; `draft_exclusion_rule` =
   `exclude_draft_assignment`; `audit_scope` = `payroll_assignment_readiness`.

## E. Recruitment outcome reconciliation for an opening

1. `GET /api/recruitment?q=<REQ-ID>` — the whole packet (this single call usually
   has everything; recruitment notice/cost data lives here, not in /messages or
   /audit).
2. Apply Rule 8: selected/waitlisted/rejected, offer, cost total = sum of all
   `cost_ledger` amounts, `notice_followup_required` = `not_sent` candidates, handoff.
3. Optionally `GET /api/cases?q=<REQ-ID>` for related case detail and
   `GET /api/policies?q=...` if a policy must be cited, but base candidate outcomes
   on committee decision + offer (`interview_feedback_and_offer`).
