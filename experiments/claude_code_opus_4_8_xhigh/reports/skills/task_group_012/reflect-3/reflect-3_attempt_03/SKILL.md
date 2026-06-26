---
name: peopleops-console-case-resolution
description: Resolve ERP HR "PeopleOps Console" lifecycle/leave/payroll/policy-case/recruitment/documents/messages/audit tasks by applying record-source precedence, folder/notice readiness gates, and scoped audit correlation, then emitting normalized enum labels.
---

# PeopleOps Console — Case Resolution Skill

You answer HR lifecycle questions for a remote read-only HTTP API. Each task gives a
business prompt plus an `answer_template.json`. Your job: read the right records,
apply the business precedence rules below, and return ONE JSON object whose keys and
enum values exactly match the template. The grader scores PER FIELD and only marks a
task fully correct on an exact match, so every field matters and wrong precedence
choices are catastrophic.

## 1. The remote API (read-only, no auth)

Base URL is given in the environment doc. All responses are JSON. `curl` GETs only.
- `GET /api/summary`, `/api/manifest` — counts/departments/seed (orientation).
- `GET /api/employees?q=&status=` — employee profile (department, salary_band,
  leave_balance_days, status, manager, hire_date).
- `GET /api/cases?q=&status=&type=` — case SUMMARIES only.
- `GET /api/cases/{case_id}` — FULL case: approvals, attachments, comments, audit_events,
  policy_refs, status, owner. Always pull the full record for case tasks.
- `GET /api/policies` , `/api/policies/{id}` — the governing business rules (read these;
  they literally state the precedence rules you must apply).
- `GET /api/payroll-ledgers?q=&status=&type=` — BOTH "Leave assignment" and
  "Salary assignment" rows live here (not a separate /leave endpoint), plus monthly
  adjustment/HRMS ledger rows.
- `GET /api/recruitment?q=` — per-opening object: candidates, offer_register,
  cost_ledger, notice_packets, payroll_precheck_records.
- `GET /api/documents?q=` — folders with files, required_files, tags, required_tags, ready.
- `GET /api/messages?q=` — formal notices with quality + defects[].
- `GET /api/audit?q=&case_id=` , `/api/audit/{id}` — audit events. `case_id=` returns
  ONLY events tied to that case (use this to scope supporting/excluded audit IDs).
- `GET /api/attachments/{id}` — raw attachment/notice body text.

`q` is a case-insensitive substring match. Effective lookups: `q=EMP-###`, `q=CASE-###`,
`q=REQ-...`, `q=ACCR...`. Omit `q` to dump a whole collection. Cross-reference modules:
an employee's authoritative state is spread across employees, payroll-ledgers, policies,
cases, documents, messages, and audit. The audit detail text frequently NAMES the
controlling record (e.g. "Approved assignment LA-… controls leave policy", "Submitted
PAY-… matches accrual batch ACCR-…") — treat that as the authoritative anchor.

## 2. Governing business rules (source precedence)

These come from the policy records and were confirmed by grading. Apply them mechanically.

### Leave source precedence
- The LATEST **Approved** or **Submitted** leave assignment for the period controls.
- EXCLUDE **Draft**, **Superseded**, voided, and obsolete rows — even when the employee
  profile summary or a stale policy reference disagrees.
- `excluded_leave_ids` must list ALL non-authoritative leave rows (both superseded AND
  draft, etc.), not just one.
- An approved annual leave ASSIGNMENT overrides a stale employee profile summary and also
  overrides monthly "People Ops adjustment" / "HRMS leave ledger" rows. effective_leave_policy
  = the controlling assignment's policy_name; annual_days / balance_days = its approved (or
  worksheet) leave days.
- Labels: leave_source = `leave_assignment_history`;
  leave_precedence_source = `approved_assignment_current_period`;
  precedence_source = `approved_assignment_over_profile`; profile_policy_ignored = true.

### Payroll assignment / accrual source precedence
- Use the current **Submitted** Salary assignment. EXCLUDE **Draft** planning assignments
  (they never affect payroll readiness or accrual checks). `payroll_status` /
  `payroll_source_status` = `submitted`; draft_exclusion_rule = `exclude_draft_assignment`;
  draft_payroll_allowed = false.
- base_salary = the submitted assignment's base_salary; excluded_payroll/assignment_id = the draft.
- `effective_date` = the assignment's FULL ISO date (YYYY-MM-DD), NOT the period (YYYY-MM).
- Accrual: accrual_batch_id comes from the submitted assignment row and is corroborated by
  a `payroll.ready` audit event. accrual_ready = true when the audit QA result is
  "ready_with_monitoring" and the submitted assignment matches the accrual batch.

### Closeout / approval gate
- Approval alone is NOT sufficient if the folder or formal notice is defective.
  - Clean records (no folder/notice defect tied to the entity) =>
    approval_closeout_gate = `approval_sufficient_when_records_clean`,
    closeout/next action = `approve_onboarding_close` / `approve_closeout`,
    final_control_result = `approve_closeout`.
  - Folder OR notice defective =>
    gate = `approval_not_sufficient_when_folder_or_notice_defective`,
    next_action = `block_close_and_reissue_notice`,
    final_control_result = `hold_for_folder_and_notice_defects`,
    closeout_blockers lists each defect type present
    (`missing_required_files`, `missing_required_tags`, `defective_formal_notice`).

### Document folder readiness
- A folder is ready ONLY when EVERY required_file is present AND every required_tag is present.
- folder_ready = (required_files ⊆ files) AND (required_tags ⊆ tags).
- missing_files = required_files − files. required_tag_present = (required_tags ⊆ tags).
- folder_required_tag_action = `no_tag_action` if the tag is already present, else `add_required_tag`.
- A missing required FILE drives the records track: escalation_action = `open_records_remediation`,
  records_remediation_owner = `Records`. (This is distinct from the notice track below.)

### Formal-notice quality and defects
- Notice quality + defect codes come straight from the Messages record's `quality` and
  `defects[]` (corroborated by the case audit detail). Defect codes are a fixed vocabulary,
  e.g. `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`,
  `missing_correct_policy`.
- A defective notice => notice_quality = `defective`,
  notice_remediation_action = `reissue_defective_notices`,
  notice_evidence_source = `message_notice_inspection` (lifecycle notices live in Messages).
  For recruitment notice packets, notice_quality_source = `notice_packet_inspection`.

### Recruitment reconciliation
- selected_candidate = committee_decision "Selected" AND confirmed by an accepted offer in
  offer_register. waitlisted/rejected from committee_decision labels.
  candidate_status_source = `interview_feedback_and_offer`;
  candidate_outcome_control = `committee_decision_with_offer_confirmation`;
  selected_offer_status = the offer_register status (e.g. accepted).
- offer_id / offer_base_salary from the selected candidate's offer_register row.
- recruitment_cost_total = the SUM of THIS opening's cost_ledger `amount`s only (per-campaign;
  do NOT add other openings' ledgers). cost_source = `recruitment_cost_ledger`.
- notice_followup_required = candidate IDs whose notice is not yet sent / needs (re)issue.
  Arrays must contain candidate IDs ONLY. waitlisted_followup_action / rejected_followup_action
  come directly from notice_packets[].required_action (e.g. `send_waitlist_notice`,
  `send_rejection_notice`, `reissue_waitlist_notice_not_rejection`).
- Payroll handoff happens only AFTER an accepted offer, and the assignment must be SUBMITTED;
  draft prechecks do not satisfy the gate:
  onboarding_handoff = `create_submitted_assignment_after_acceptance`,
  payroll_handoff_gate = `accepted_offer_and_submitted_assignment`,
  payroll_assignment_status_required = `submitted_after_acceptance`,
  handoff_control_result = `submitted_handoff_required_after_acceptance`.
- offer_exclusion_reason_for_waitlisted = `no_accepted_status_or_offer` — frame the exclusion by
  the RULE (no accepted offer => excluded), NOT by the committee label (`waitlisted_not_selected`).

## 3. Audit correlation and scope (this cost the most points — get it right)

Each task has ONE audit scope; pick the matching enum:
- leave precedence task => audit_scope = `leave_source_precedence_only`
- payroll/accrual task => audit_scope = `payroll_assignment_readiness`
- folder/notice/case-close task => audit_scope = `document_notice_findings_only`

Then partition audit events by entity AND scope:
- audit_event_id / supporting_audit_event_ids = the in-scope event(s) tied to THIS case/employee.
  Get them with `GET /api/audit?case_id=...` (it returns only that case's events) — then keep the
  one(s) whose event type matches the current scope (e.g. `notice.defect` for a notice review,
  `leave.profile_mismatch` for a leave review, `payroll.ready` for accrual).
- excluded_audit_event_ids = the SAME-entity (same case/employee) audit events that belong to a
  DIFFERENT scope. Example: a leave-precedence review excludes that case's folder/document event;
  a notice review excludes that case's leave/payroll events.
- If the case/employee has no adjacent out-of-scope event, excluded_audit_event_ids = [] —
  do NOT dump unrelated OTHER cases' or cross-module escalation events into it. "Adjacent" means
  same entity, other scope — never every event in the log.
- audit_result mirrors the QA result stated in the audit detail (e.g. `profile_summary_stale`,
  `ready_with_monitoring`, `block_close`).

## 4. Output discipline

- Emit ONE JSON object. Keys = template keys exactly. No markdown, no commentary.
- For enum fields, choose a value from the template's `allowed_values` verbatim — never free text.
  When several labels look plausible, pick the one naming the RULE/mechanism, not the surface label.
- Copy IDs, policy names, and amounts exactly as the API returns them.
- For ID/amount/name fields, use the value the API gives; effective dates as full YYYY-MM-DD.
- excluded_* list fields: include EVERY excluded record (all drafts/superseded), or [] when none.
- Re-derive booleans from data (folder_ready, accrual_ready, required_tag_present,
  profile_policy_ignored, draft_payroll_allowed), don't guess.

## 5. Suggested workflow per task

1. Read the prompt + answer_template; note the focal entity (EMP-###, CASE-###, REQ-…) and the
   field set / enum vocabularies.
2. Dump the relevant module(s) by `q=<focal id>` and read the matching policy record(s).
3. Apply the precedence rule for the module (leave / payroll / closeout / folder / notice /
   recruitment) to pick the controlling record and the excluded records.
4. Pull `GET /api/cases/{id}` and `GET /api/audit?case_id=...` for approvals, folder/notice
   detail, and scoped audit IDs; partition supporting vs excluded by scope.
5. Fill every template field with normalized enum labels; double-check excluded_* lists, the
   full-ISO effective_date, per-campaign cost sums, and the clean-vs-defective closeout gate.

## 6. Common misjudgments that cost points (fix proactively)

- Using a Draft or Superseded record's value instead of the Approved/Submitted one — wrong on
  policy, days, salary, and IDs at once. Always exclude draft+superseded.
- Forgetting that leave AND salary assignments both live in /api/payroll-ledgers.
- Returning effective_date as the period (YYYY-MM) instead of the full date (YYYY-MM-DD).
- Summing every opening's recruitment cost instead of just the focal opening's ledger.
- offer_exclusion_reason_for_waitlisted = `waitlisted_not_selected` (wrong) instead of the
  rule-based `no_accepted_status_or_offer`.
- excluded_audit_event_ids: dumping all other audit events (wrong) instead of only the SAME-entity
  out-of-scope event, or [] when none exist.
- Treating a missing folder FILE as a notice problem: it is a Records-track item
  (escalation_action = open_records_remediation, owner = Records), separate from notice reissue.
- Marking a folder ready when a required tag is present but a required file is missing (or vice versa)
  — both must be fully satisfied.
