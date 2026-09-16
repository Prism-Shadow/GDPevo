---
name: peopleops-console
description: "PeopleOps HR console solver for employee onboarding closeout, case folder/notice review, recruitment reconciliation, leave source precedence, and payroll assignment readiness. Use when the task references PeopleOps Console, TASK_ENV_BASE_URL, ops.lead@peopleops.local, onboarding, leave policy, payroll assignment, case review, recruitment reconciliation, notice quality, or audit scoping."
---

# PeopleOps Console

## Quick Start

Every task follows this sequence:

1. Open `<TASK_ENV_BASE_URL>` in the browser-style fetch tool. Login with
   `ops.lead@peopleops.local` / `PeopleOps#2026` if the application requires
   authentication.
2. Read the task prompt to identify the task type, target record ID, and which
   answer template fields are required.
3. Fetch records from the relevant API endpoints, working from list endpoints
   to detail endpoints.
4. Apply the business rules for the task type (below).
5. Produce a single JSON object matching the answer template. Every string
   field that names an enum must use the exact allowed value from the template.

## API Endpoints

See [references/api_reference.md](references/api_reference.md) for the full
endpoint catalog, record field descriptions, and task-type-to-endpoint mapping.

## Normalized Business Labels

See [references/enum_reference.md](references/enum_reference.md) for every
allowed value across all answer templates. Always match these exact strings.

## Core Business Rules

### Record Status Precedence

`submitted` > `draft` > `superseded`

- Only `submitted` records are authoritative for decisions.
- `draft` records must be excluded unless the task explicitly permits drafts.
- `superseded` records were replaced by a newer submitted record; exclude them.
- When multiple submitted records exist for the same entity, use the most
  recent.

### Audit Scoping

- Each audit event has a `scope` field and `related_event_ids`.
- When the task asks for leave-source decisions, use only audit events scoped
  to leave precedence. Exclude document/notice or payroll audit events from
  the leave decision, listing them in `excluded_audit_event_ids`.
- When the task asks for document/notice decisions, use only audit events
  scoped to document/notice findings. Exclude leave or payroll events.
- When the task asks for payroll readiness, use only payroll-scoped audit
  events.
- A single audit event that covers the relevant scope serves as both the
  primary `audit_event_id` and the sole entry in
  `supporting_audit_event_ids`.

## Task Types

### 1. Onboarding Closeout

Verify leave and payroll setup for a given employee ID before approving
onboarding completion.

**Leave verification:**
- Fetch the employee from `/api/employees` and the leave assignment ledger from
  `/api/payroll-ledgers`.
- Identify all leave assignment records for the employee. Classify each as
  submitted, draft, or superseded.
- The effective leave policy and annual days come from the most recent
  *submitted* leave assignment. List draft and superseded leave assignment IDs
  in `excluded_leave_ids`.
- If the submitted assignment matches the current period, set
  `leave_source` to `leave_assignment_history` and
  `leave_precedence_source` to `approved_assignment_current_period`.

**Payroll verification:**
- From `/api/payroll-ledgers`, identify all payroll assignment records for the
  employee.
- The authoritative record is the most recent submitted payroll assignment.
  Set `payroll_status` and `payroll_source_status` to `submitted`.
- List any draft or superseded payroll assignment IDs in
  `excluded_payroll_ids`.
- Extract `base_salary` from the submitted assignment.

**Closeout decision:**
- If both leave and payroll records are clean (no drafts in authoritative
  position, no missing records), set:
  - `closeout_action`: `approve_onboarding_close`
  - `approval_closeout_gate`: `approval_sufficient_when_records_clean`
  - `final_control_result`: `approve_closeout`
- If defects exist, choose the appropriate blocker action.

### 2. Case Folder and Notice Review

Review a case for folder readiness and formal notice quality.

**Folder inspection:**
- Fetch the case detail from `/api/cases/{case_id}`.
- Check `folder_status` for whether the folder is ready. Inspect listed
  documents for required files. Any required file not present goes in
  `missing_files`.
- Check `tags` for the required tag. Set `required_tag_present` accordingly.
  If the tag is already present, `folder_required_tag_action` is
  `no_tag_action`; otherwise `add_required_tag`.

**Notice inspection:**
- Fetch notices from `/api/notifications` and inspect the formal notice
  packet.
- Check for defects: missing acknowledgement deadline, missing appeal
  instructions, missing waitlist status, incorrect policy reference.
- Set `notice_quality` to `valid` or `defective` and list any defect labels
  in `notice_defects`.
- Set `notice_evidence_source` to `notice_packet_inspection`.

**Audit evidence:**
- Fetch audit events from `/api/audit` and `/api/audit/{audit_id}`.
- Find the audit event that covers document/notice findings. Use it for
  `audit_event_id` and `supporting_audit_event_ids`.
- Set `audit_scope` to `document_notice_findings_only`.

**Evidence order:** Follow `approval_history_folder_notice_audit`: read
approval history first, then folder, then notice packet, then audit detail.
Set `evidence_source_order` accordingly.

**Decision:**
- If both folder and notice are clean: `final_decision` is `approved` or
  `approved_with_conditions`.
- If folder has missing files or notice is defective: `final_decision` is
  `held` or `approved_with_conditions` (depending on approval record), and
  list blockers in `closeout_blockers`.
- If notice is defective, `next_action` is `block_close_and_reissue_notice`
  and `notice_remediation_action` is `reissue_defective_notices`.
- If folder has missing files, `escalation_action` is
  `open_records_remediation` with `records_remediation_owner` set to
  `Records`.
- `final_control_result` is `hold_for_folder_and_notice_defects` when defects
  exist.

### 3. Recruitment Reconciliation

Reconcile recruitment outcomes for an opening ID.

**Candidate determination:**
- Fetch `/api/recruitment` for the opening. Inspect interview feedback and
  offer records for each candidate.
- The selected candidate is the one with an accepted offer and committee
  decision confirmation. Set `selected_offer_status` to `accepted`.
- Waitlisted candidates: those with committee waitlist status but no accepted
  offer. Put their IDs in `waitlisted_candidates`.
- Rejected candidates: those with committee rejection. Put their IDs in
  `rejected_candidates`.
- Set `candidate_status_source` to `interview_feedback_and_offer` and
  `candidate_outcome_control` to
  `committee_decision_with_offer_confirmation`.

**Offer and cost:**
- Extract `offer_id` and `offer_base_salary` from the selected candidate's
  accepted offer.
- Sum all items from the recruitment cost ledger for `recruitment_cost_total`.
  Set `cost_source` to `recruitment_cost_ledger`.

**Notice followup:**
- Inspect notices from `/api/notifications`. Set
  `notice_quality_source` to `notice_packet_inspection`.
- For each waitlisted candidate without a valid waitlist notice, add to
  `notice_followup_required` and set `waitlisted_followup_action` to
  `send_waitlist_notice`.
- For each rejected candidate without a valid rejection notice, add to
  `notice_followup_required` and set `rejected_followup_action` to
  `send_rejection_notice`.

**Payroll handoff:**
- Only the selected candidate with an accepted offer triggers payroll handoff.
- Set `payroll_handoff_gate` to `accepted_offer_only`.
- Set `payroll_assignment_status_required` to
  `submitted_after_acceptance`.
- Set `draft_payroll_allowed` to `false`.
- Set `onboarding_handoff` to `create_payroll_precheck`.
- Set `handoff_control_result` to
  `submitted_handoff_required_after_acceptance`.
- For waitlisted candidates, set `offer_exclusion_reason_for_waitlisted` to
  `no_accepted_status_or_offer`.

### 4. Leave Source Precedence

Determine which leave policy is authoritative when both an employee profile
summary and a leave assignment ledger exist.

**Procedure:**
- Fetch the employee from `/api/employees`. Note the leave policy in the
  profile summary.
- Fetch leave assignment records from `/api/payroll-ledgers`.
- Fetch the policy document text from `/api/policies/{policy_id}`.
- Fetch audit events from `/api/audit` and inspect the leave-scope audit
  detail from `/api/audit/{audit_id}`.

**Rule:** An approved (submitted) leave assignment for the current period
overrides a stale employee profile summary when the ledger, policy document,
and audit detail all confirm the approved assignment.

- If the submitted leave assignment matches the current period, set:
  - `precedence_source`: `approved_assignment_over_profile`
  - `leave_precedence_source`: `approved_assignment_current_period`
  - `profile_policy_ignored`: `true`
  - `effective_leave_policy`: the policy name from the assignment
  - `assignment_id`: the submitted assignment ID
  - `balance_days`: the balance from the assignment
  - `audit_result`: `profile_summary_stale`
  - `next_action`: `update_employee_summary`
- If no approved assignment exists for the current period, fall back to the
  profile summary policy.

**Audit scoping:**
- Use only leave-scope audit events. Set `audit_scope` to
  `leave_source_precedence_only`.
- The primary leave-scope audit event becomes `audit_event_id` and the sole
  entry in `supporting_audit_event_ids`.
- List any document/notice or payroll-scope audit events in
  `excluded_audit_event_ids`.

### 5. Payroll Assignment Readiness

Verify payroll assignment and accrual batch readiness for an employee.

**Procedure:**
- Fetch payroll assignment records from `/api/payroll-ledgers`.
- Identify the most recent submitted assignment. Extract its ID, salary, and
  effective date.
- Identify any draft or superseded assignments. List the draft assignment ID
  in `excluded_assignment_id`.
- Set `payroll_source_status` to `submitted` and `draft_exclusion_rule` to
  `exclude_draft_assignment`.

**Accrual check:**
- From the payroll ledger, check whether the accrual batch for the relevant
  period is ready. Set `accrual_ready` to `true` or `false` and provide the
  `accrual_batch_id`.

**Audit evidence:**
- Fetch payroll-scope audit events. Set `audit_scope` to
  `payroll_assignment_readiness`.
- The payroll-scope audit event becomes `audit_event_id`.

**Control result:**
- If the submitted assignment is valid and accrual is ready:
  `control_result` is `ready_with_monitoring`.
- If defects exist, use the appropriate hold or block label.

## Output Format

Return a single JSON object. No markdown fences, no explanatory text. Match
the answer template field-by-field:

- String fields where the template specifies an enum: use exactly one of the
  allowed values.
- Integer/number fields: the numeric value from the API record.
- Boolean fields: `true` or `false`.
- List fields: JSON arrays of strings (IDs or defect labels).

If the task provides an `input/payloads/answer_template.json`, read it first
to confirm the exact field names and allowed values.
