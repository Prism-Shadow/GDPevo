---
name: peopleops-console
description: HR operations verification in the PeopleOps Console. Use when the task involves onboarding closeout, policy case folder/notice review, recruitment reconciliation, leave source precedence, payroll assignment readiness, or any PeopleOps lifecycle verification that requires cross-referencing employees, cases, policies, payroll ledgers, recruitment packets, documents, messages, and audit events through the REST API. Triggers on PeopleOps, People Ops, employee onboarding, policy case review, recruitment reconciliation, leave policy, payroll assignment, HR verification, or closeout workflows.
---

# PeopleOps Console

Verify HR lifecycle records by fetching data from the REST API, applying business-policy rules, and returning structured JSON.

## Quick Start

1. Read the task prompt for the `<TASK_ENV_BASE_URL>` and credentials.
2. Fetch all relevant API collections in parallel: `/api/employees`, `/api/cases`, `/api/policies`, `/api/payroll-ledgers`, `/api/recruitment`, `/api/documents`, `/api/messages`, `/api/audit`.
3. Drill into specific records (single case, policy, audit event, attachment) only when needed.
4. Apply the business rules from [references/business_rules.md](references/business_rules.md) and use only the normalized enum values from [references/enum_catalog.md](references/enum_catalog.md).
5. Return a single JSON object matching the answer template in the payload.

## API Reference

All endpoints and data shapes are in [references/api_reference.md](references/api_reference.md). Fetch that file before making any API calls.

## Business Rules

Core decision rules for each domain are in [references/business_rules.md](references/business_rules.md). Read it after fetching data to map raw records to normalized conclusions.

## Enum Catalog

Every allowed enum value across all answer-template fields is listed in [references/enum_catalog.md](references/enum_catalog.md). Scan it before populating any enum field — never invent a label.

## Workflows

### Onboarding Closeout

Examine an employee's leave and payroll ledger records, then apply source-precedence rules.

**Steps:**

1. Fetch employee list and find the target employee by ID.
2. Fetch payroll-ledgers; filter by employee_id.
3. **Leave:** Pick the record with status `Approved` for the current period. Mark any `Superseded` or `Draft` leave records as excluded. Use the policy_name and approved_leave_days from the approved record.
4. **Payroll:** Pick the record where `record_type` is `Salary assignment` and status is `Submitted`. Mark any `Draft` salary assignment as excluded. Use base_salary from the submitted record.
5. Set `leave_source` to `leave_assignment_history`, `leave_precedence_source` to `approved_assignment_current_period`, `payroll_status` / `payroll_source_status` to `submitted`.
6. If leave and payroll records are clean (no draft/superseded contamination), set `approval_closeout_gate` to `approval_sufficient_when_records_clean`, `closeout_action` to `approve_onboarding_close`, and `final_control_result` to `approve_closeout`.

### Policy Case Folder and Notice Review

Review a case's folder checklist and formal notice for defects.

**Steps:**

1. Fetch the case detail: `GET /api/cases/{case_id}`. This returns approvals, attachments (checklist), and audit events.
2. From the folder checklist attachment (`kind: Checklist`): compare `files` against `required_files` to find missing entries. Compare `tags` against `required_tags`.
3. From messages (`GET /api/messages`): find the matching `case_id`, read `quality` and `defects`. If `quality` is `defective`, list the defect codes.
4. From approvals: identify the final approval step (largest `decided_at` or step named `Final approval`) and extract `decision` and `approver`.
5. From audit events with matching `case_id`: use the one whose scope matches documents/notices.
6. Set `evidence_source_order` to `approval_history_folder_notice_audit` when all sources are used. Set `notice_evidence_source` to `notice_packet_inspection` when using messages.
7. If any required file is missing, add `missing_required_files` to `closeout_blockers`. If any tag is missing, add `missing_required_tags`. If notice is defective, add `defective_formal_notice`.
8. When blockers exist: set `approval_closeout_gate` to `approval_not_sufficient_when_folder_or_notice_defective`, `final_control_result` to `hold_for_folder_and_notice_defects`, and choose the appropriate `next_action` and `escalation_action`.

### Recruitment Reconciliation

Reconcile a recruitment opening's candidates, offers, costs, and notices.

**Steps:**

1. Fetch recruitment data: `GET /api/recruitment`. Find the target `opening_id`.
2. From `candidates`: read `committee_decision` for each. `Selected` → selected_candidate. `Waitlisted` → waitlisted_candidates. `Rejected` → rejected_candidates.
3. From `offer_register`: find the offer with `candidate_id` matching the selected candidate. Extract `offer_id`, `base_salary`, and `status`.
4. From `cost_ledger`: sum all `amount` values across line items to compute `recruitment_cost_total`.
5. From `notice_packets`: identify candidates needing follow-up. Set `notice_followup_required` to their candidate_ids. Match `notice_type` to `waitlisted_followup_action` and `rejected_followup_action`.
6. For payroll handoff: if the selected candidate's offer is `accepted`, set `onboarding_handoff` to `create_payroll_precheck` and `payroll_handoff_gate` to `accepted_offer_only`. Set `draft_payroll_allowed` to `false`.
7. Set `candidate_status_source` to `interview_feedback_and_offer`, `candidate_outcome_control` to `committee_decision_with_offer_confirmation`, `cost_source` to `recruitment_cost_ledger`.

### Leave Source Precedence

Determine which leave policy controls when profile and assignment conflict.

**Steps:**

1. Fetch the employee and their payroll-ledger leave records.
2. Fetch the relevant policy: `GET /api/policies/LEAVE-SRC-001` confirms that latest approved/submitted assignment controls.
3. Compare the employee profile's `leave_balance_days` and implicit policy against the approved leave assignment's `policy_name` and `approved_leave_days`.
4. If the approved assignment exists for the current period: it controls. Set `precedence_source` to `approved_assignment_over_profile`, `leave_precedence_source` to `approved_assignment_current_period`, `profile_policy_ignored` to `true`.
5. Fetch audit events; find the one with matching `employee_id` and `event` in `leave.profile_mismatch`. That becomes the primary audit_event_id and supporting event.
6. Exclude any audit events whose scope is document/notice only (not leave-related) from `supporting_audit_event_ids`.
7. Set `audit_scope` to `leave_source_precedence_only`, `audit_result` to `profile_summary_stale`, `next_action` to `update_employee_summary`.

### Payroll Assignment Readiness

Verify which payroll assignment controls and whether accrual is ready.

**Steps:**

1. Fetch payroll-ledgers and find salary assignments for the employee.
2. Select the record with `status: Submitted`. Extract `ledger_id`, `base_salary`, `period` (use first day as effective_date). Mark the Draft assignment as excluded.
3. Check the submitted record for an `accrual_batch_id` field. If present, set `accrual_ready` to `true` and use the batch id.
4. Fetch audit events; find the one with matching `employee_id` and `event: payroll.ready`.
5. Set `payroll_source_status` to `submitted`, `draft_exclusion_rule` to `exclude_draft_assignment`, `audit_scope` to `payroll_assignment_readiness`, `control_result` to `ready_with_monitoring`.

## Important Rules

- **Never guess enum values.** Always look them up in [references/enum_catalog.md](references/enum_catalog.md).
- **Draft records are always excluded** from effective leave, payroll, and assignment decisions unless a policy explicitly allows them.
- **Superseded records are excluded** when a newer approved or submitted record exists for the same period.
- **Source precedence chain:** approved assignment > submitted assignment > profile summary > case summary only.
- **Evidence source order:** always prefer the richest chain: approval history + folder checklist + notice review + audit events. Narrow only when the task explicitly constrains scope.
- **Audit scope isolation:** when the task asks for leave-only or payroll-only findings, exclude document/notice audit events from the decision and their IDs from supporting lists.
- **All dollar amounts and day counts** come from the API data, not from the answer template or from inference.
