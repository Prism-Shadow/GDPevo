# PeopleOps Lifecycle Verification Skill

## Overview
Verify employee onboarding, leave, payroll, case folders, formal notices, and recruitment packets in the Northwind People Lifecycle Portal. Return structured JSON answers that match the task-specific schema.

## Environment Setup
1. Identify the application base URL from `GDPEVO_ENV_BASE_URL` or the prompt.
2. Cache all API data locally before drafting answers:
   - `GET /api/employees`
   - `GET /api/cases` and `GET /api/cases/{case_id}`
   - `GET /api/payroll-ledgers`
   - `GET /api/recruitment`
   - `GET /api/documents`
   - `GET /api/messages`
   - `GET /api/audit`
   - `GET /api/policies`
3. Read the task's `input/payloads/answer_template.json` **first**; every task uses a different schema.

## General Rules
- Use only **submitted** or **approved** records as authoritative.
- **Exclude draft records** unless the template explicitly allows drafts.
- **Exclude superseded records** when a newer approved/submitted record exists.
- Use exact string values from the API (IDs, policy names, dates) in answer fields.
- For enum fields, always use one of the exact allowed values from the template.

## Task-Type Workflows

### 1. Onboarding / Leave / Payroll Verification
Applies when the prompt asks to verify onboarding closeout, leave setup, or payroll readiness.

**Steps:**
1. Find the employee in `/api/employees`.
2. Fetch all their records from `/api/payroll-ledgers` (leave assignments and salary assignments).
3. Select the **latest approved or submitted** assignment as authoritative.
4. List all **draft** and **superseded** records in the exclusion arrays.
5. Read the case and audit events for that employee.
6. Map fields exactly to the template:
   - `leave_assignment_id` / `salary_assignment_id` → authoritative record ID
   - `effective_leave_policy` → `policy_name` from the authoritative leave assignment
   - `annual_leave_days` / `balance_days` → `approved_leave_days` or `worksheet_leave_days` from the authoritative record
   - `base_salary` → from the authoritative salary assignment
   - `payroll_status` / `payroll_source_status` → `"submitted"` or `"approved"`
   - `excluded_leave_ids` / `excluded_payroll_ids` / `excluded_assignment_id` → list the draft/superseded record IDs
   - `closeout_action` / `final_control_result` → `"approve_closeout"` or `"approve_onboarding_close"` when records are clean; `"hold_for_folder_and_notice_defects"` when defects exist
   - `draft_exclusion_rule` → `"exclude_draft_assignment"`
   - `audit_scope` → match the task domain (`"payroll_assignment_readiness"`, `"leave_source_precedence_only"`, etc.)

### 2. Case Folder & Formal Notice Review
Applies when the prompt asks to review a case (e.g., remote-work exception, document correction).

**Steps:**
1. Get the case from `/api/cases/{case_id}`.
2. Get the matching document from `/api/documents` (filter by document_id or title).
3. Get the formal notice from `/api/messages` (filter by `case_id`).
4. Get audit events from `/api/audit` (filter by `case_id`).
5. Evaluate:
   - `folder_ready` → document `ready` field.
   - `missing_files` → `required_files` minus `files`.
   - `required_tag_present` → check if all `required_tags` are in `tags`.
   - `notice_quality` → message `quality` field (`"valid"` or `"defective"`).
   - `notice_defects` → message `defects` array.
   - `approval_authority` / `approval_event_id` → from case `approvals` array.
   - `audit_event_id` → the audit event directly tied to the case.
   - `supporting_audit_event_ids` → include the primary audit event and any other case-relevant audit events.
   - `excluded_audit_event_ids` → include audit events from unrelated cases or cross-module packages that are not part of this case's scope.
   - `audit_scope` → `"document_notice_findings_only"` for folder/notice reviews.
   - `evidence_source_order` → `"approval_history_folder_notice_audit"` when all four sources exist; `"folder_notice_audit"` when approval history is absent.
   - `notice_evidence_source` → `"notice_packet_inspection"` when inspecting message or notice packet records; `"message_notice_inspection"` only when the evidence is purely a message.
   - `closeout_blockers` → list every applicable blocker (`"missing_required_files"`, `"missing_required_tags"`, `"defective_formal_notice"`).
   - `final_control_result` → `"hold_for_folder_and_notice_defects"` when any blocker exists; `"approve_closeout"` when clean.

### 3. Recruitment Reconciliation
Applies when the prompt asks to reconcile a recruitment opening.

**Steps:**
1. Get the opening from `/api/recruitment` (filter by `opening_id`).
2. Identify:
   - `selected_candidate` → candidate with `"Selected"` committee decision AND an accepted offer in `offer_register`.
   - `waitlisted_candidates` → candidates with `"Waitlisted"` decision.
   - `rejected_candidates` → candidates with `"Rejected"` decision.
   - `offer_id` / `offer_base_salary` → from `offer_register` for the selected candidate.
   - `recruitment_cost_total` → sum all `amount` values in `cost_ledger`.
   - `notice_followup_required` → candidate IDs with unsent or defective notices in `notice_packets`.
3. Payroll handoff rules (policy `PAY-SRC-001`):
   - Handoff is created only after a selected candidate has an accepted offer.
   - Draft prechecks do **not** satisfy the assignment gate.
   - `onboarding_handoff` → if no precheck records exist, use `"create_payroll_precheck"`; if a precheck exists but needs submission, use `"create_submitted_assignment_after_acceptance"`.
   - `payroll_assignment_status_required` → `"submitted"` or `"submitted_after_acceptance"`.
   - `draft_payroll_allowed` → `false`.
   - `offer_exclusion_reason_for_waitlisted` → `"no_accepted_status_or_offer"` (waitlisted candidates lack an accepted offer).
   - `handoff_control_result` → `"submitted_handoff_required_after_acceptance"` when an accepted offer exists but no submitted handoff is present yet.

## Important Gotchas
- **Never mix up answer templates.** Each train/test task has its own schema. Always read `input/payloads/answer_template.json` before constructing the answer.
- For fields like `supporting_audit_event_ids`, include the primary audit event ID when it directly supports the decision, even if it also appears in `audit_event_id`.
- When a task mentions "exclude adjacent document/notice audit events from that leave-scope decision," put document/notice audit events into `excluded_audit_event_ids` **only** when the current audit scope is **leave** (not document/notice).
- For recruitment, `offer_exclusion_reason_for_waitlisted` is about why waitlisted candidates are excluded from the offer register. The canonical reason is that they have no accepted offer (`"no_accepted_status_or_offer"`), not simply that they were waitlisted.
- For case reviews, `escalation_action` and `next_action` may both be the same value (e.g., `"block_close_and_reissue_notice"`) when the case has both folder and notice defects.
