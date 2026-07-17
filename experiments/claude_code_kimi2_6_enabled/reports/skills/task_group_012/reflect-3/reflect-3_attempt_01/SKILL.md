# PeopleOps Lifecycle Closeout and Precedence Skill

## Goal
Answer structured closeout, precedence, and reconciliation tasks using the PeopleOps remote environment.

## Environment
- Base URL: `http://34.46.77.124:8012`
- API endpoints (no auth required for read):
  - `GET /api/employees`
  - `GET /api/cases` and `GET /api/cases/{case_id}`
  - `GET /api/policies` and `GET /api/policies/{policy_id}`
  - `GET /api/messages`
  - `GET /api/documents`
  - `GET /api/audit`
  - `GET /api/recruitment`
  - `GET /api/payroll-ledgers`
  - `GET /api/summary`

## Workflow
1. **Read the task prompt** in `prompt.txt` to identify the target employee, case, or opening.
2. **Read the answer template** in `input/payloads/answer_template.json` to see required fields and allowed enum values.
3. **Fetch all relevant data** from the API (case detail, employee, payroll-ledgers, recruitment, audit, messages, documents, policies).
4. **Apply the business rules below** and produce JSON matching the answer template exactly.
5. **Return only JSON** (no markdown, no explanatory text).

## Business Rules

### 1. Source Precedence (Leave / Payroll)
- **Approved or submitted assignments control** over employee profile summaries.
- **Draft, voided, and superseded records must be excluded** even when they conflict with profiles.
- For leave: use `approved_leave_days` and `policy_name` from the approved/submitted leave assignment in `payroll-ledgers`.
- For payroll: use the submitted salary assignment; exclude draft planning assignments.

### 2. Folder Readiness
- A folder is ready only when **all required files and all required tags** are present.
- Missing files are computed as `required_files - files`.
- Missing tags are computed as `required_tags - tags`.

### 3. Notice Quality
- Inspect messages and notice packets for defects:
  - `missing_ack_deadline`
  - `missing_appeal_instructions`
  - `missing_waitlist_status`
  - `missing_correct_policy`
- If any defect exists, `notice_quality` = `defective` and list the defects.
- Evidence source for notices should be `notice_packet_inspection` when inspecting formal notice packets; `message_notice_inspection` is only for informal messages.

### 4. Closeout Gate Logic
- Approval is **not sufficient** when the folder or notice is defective.
- `closeout_blockers` must include every applicable blocker:
  - `missing_required_files` (when folder lacks required files)
  - `missing_required_tags` (when folder lacks required tags)
  - `defective_formal_notice` (when notice has defects)
- `next_action` for a blocked closeout with notice defects is typically `block_close_and_reissue_notice`.
- `escalation_action` for cases with both folder and notice defects is `open_records_remediation`.
- `records_remediation_owner` for folder issues is `Records`; for cross-module escalations it may be `People Ops Compliance`.

### 5. Recruitment Reconciliation
- Selected candidate = candidate with committee decision "Selected" and accepted offer.
- `recruitment_cost_total` = sum of all `amount` values in the opening's `cost_ledger`.
- `notice_followup_required` includes candidates whose notice status is `not_sent` or `draft_reissue_required`.
- Waitlisted candidates get `send_waitlist_notice`; rejected candidates get `send_rejection_notice`.
- Payroll handoff is created only after a selected candidate has an accepted offer.
- `onboarding_handoff` for a new accepted offer with no existing payroll records is `create_payroll_precheck`.
- `handoff_control_result` is `submitted_handoff_required_after_acceptance` when an accepted offer exists but no submitted payroll assignment is present yet.
- `draft_payroll_allowed` is `true` only when draft prechecks are explicitly allowed by policy (default `false` for recruiting handoff).

### 6. Audit Scope and Event Selection
- Use the audit event that directly supports the business decision as `audit_event_id`.
- `supporting_audit_event_ids` are other audit events in the same scope.
- `excluded_audit_event_ids` are adjacent audit events outside the current scope (e.g., exclude folder/document audits when deciding leave precedence).
- `audit_scope` enum must match the task domain:
  - `leave_source_precedence_only`
  - `document_notice_findings_only`
  - `payroll_assignment_readiness`

### 7. Evidence Source Order
- Order should reflect what was actually examined:
  - `approval_history_folder_notice_audit` when all four sources exist
  - `folder_notice_audit` when approvals are not relevant
  - `audit_only` when only audit events were used

## Common Field Mappings
- `final_decision`: derive from the last approval note (e.g., "Approved with conditions" → `approved_with_conditions`).
- `approval_authority`: `approver` field from the final approval event.
- `approval_event_id`: the approval ID for the final approval step.
- `control_result` / `final_control_result`:
  - Use `ready_with_monitoring` when submitted assignment matches accrual batch and no defects exist.
  - Use `hold_for_folder_and_notice_defects` when either is defective.
  - Use `approve_closeout` when records are clean.
- `effective_date`: use the assignment/ledger `updated_at` date or the employee `hire_date`, truncated to date only (`YYYY-MM-DD`).
