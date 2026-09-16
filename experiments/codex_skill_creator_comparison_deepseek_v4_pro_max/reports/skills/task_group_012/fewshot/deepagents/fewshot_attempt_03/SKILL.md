---
name: peopleops-console
description: "Solver for Northwind People Lifecycle Portal (PeopleOps Console) tasks. Handles verification and reconciliation across employees, leave, payroll, recruitment, policy cases, documents, messages, and audit logs. Use when working with PeopleOps business tasks that involve determining leave source precedence, payroll assignment readiness, recruitment reconciliation, remote-work case review, onboarding closeout, or cross-module lifecycle control."
license: MIT
compatibility: designed for deepagents-code
---

# PeopleOps Console

## Overview

This skill covers the Northwind People Lifecycle Portal, a shared HR operations workspace. The console exposes a JSON REST API for nine business modules. No authentication tokens are needed when calling API endpoints directly.

## Quick Start

1. Read the prompt to identify the task type, target entity, and the answer template at `input/payloads/answer_template.json`.
2. Read [api_endpoints.md](references/api_endpoints.md) for the endpoint catalog and data shapes.
3. Read [business_rules.md](references/business_rules.md) for source-precedence, exclusion, notice-quality, folder-readiness, audit-scoping, and handoff rules.
4. Read [answer_schemas.md](references/answer_schemas.md) for normalized business labels and enum reference.
5. Call the relevant API endpoints, interpret data through the business rules, and produce a single JSON object matching the answer template. Return only JSON.

## Task Workflows

### Onboarding Closeout Verification

Verify leave and payroll setup before approving onboarding closeout using authoritative submitted or assignment-history records (not draft records).

1. Fetch `/api/employees`, find the target by `employee_id`.
2. Fetch `/api/payroll-ledgers`, filter by the employee. Separate leave assignments from salary assignments by `record_type`.
3. For leave: select the latest Approved (or Submitted if no Approved) record for the 2026 period. Exclude Draft and Superseded. Record `policy_name`, `approved_leave_days`, and `ledger_id`.
4. For payroll: select the Submitted salary assignment. Exclude Draft. Record `ledger_id`, `base_salary`, and `status`.
5. Set `leave_source` to `leave_assignment_history`, `payroll_status` / `payroll_source_status` to `submitted`.
6. If both are clean, set `closeout_action` to `approve_onboarding_close`, `approval_closeout_gate` to `approval_sufficient_when_records_clean`, and `final_control_result` to `approve_closeout`.

### Remote-Work Case Review

Review a remote-work policy case for folder readiness and formal notice quality.

1. Fetch `/api/cases/{case_id}` for case detail (approvals, attachments, audit_events).
2. Check `approvals` for the final decision and approval authority. The approval event ID is the `approval_id` of the final approval.
3. Match the case to its document folder via `/api/documents` or case attachments.
4. Compare `files` against `required_files`, `tags` against `required_tags`. Determine `folder_ready` and `missing_files`.
5. Fetch `/api/messages`, filter by `case_id`, inspect formal notices for defects.
6. The primary audit event is the one with `event` matching `notice.defect` for the case.
7. Scope audit events per [business_rules.md](references/business_rules.md).
8. Determine `next_action`: `block_close_and_reissue_notice` when notices defective; `open_records_remediation` when folder files missing.

### Recruitment Reconciliation

Reconcile a recruitment opening to determine candidate outcomes and follow-up.

1. Fetch `/api/recruitment`, find the target `opening_id`.
2. Inspect `candidates` (committee decisions), `offer_register`, `cost_ledger`.
3. Determine candidate status from `committee_decision` confirmed by offer register. Source is `interview_feedback_and_offer`.
4. Sum all `amount` values in `cost_ledger` for `recruitment_cost_total`. Source is `recruitment_cost_ledger`.
5. Inspect `notice_packets` for follow-up: waitlisted with unsent waitlist notices, rejected with unsent rejection notices.
6. For payroll handoff: only the accepted (selected) candidate qualifies. Handoff requires a submitted assignment after acceptance; draft prechecks do not satisfy the gate. Set `draft_payroll_allowed` to `false`.

### Leave Source Precedence Validation

Determine which leave policy is authoritative when profile and ledger conflict.

1. Fetch `/api/employees`, note `leave_balance_days` and department for the target employee.
2. Fetch `/api/payroll-ledgers`, filter by the employee's leave assignment records (record_type `Leave assignment`) for 2026.
3. Identify the latest Approved assignment. If its `policy_name` and `approved_leave_days` differ from the employee profile, the approved assignment controls.
4. Fetch case audit events. The leave-source audit event has `event` = `leave.profile_mismatch`. Include it as supporting.
5. Exclude adjacent document/notice audit events (event = `folder.tag_missing`, `notice.defect`) from the leave-scope decision.
6. Set `audit_scope` to `leave_source_precedence_only`, `precedence_source` to `approved_assignment_over_profile`.
7. If profile stale: `profile_policy_ignored` = `true`, `next_action` = `update_employee_summary`, `audit_result` = `profile_summary_stale`.

### Payroll Assignment and Accrual Readiness

Verify payroll assignment records and accrual readiness.

1. Fetch `/api/payroll-ledgers`, filter by the employee's salary assignment records (record_type `Salary assignment`).
2. Select the Submitted salary assignment. Exclude Draft. Record `ledger_id`, `base_salary`, `period` as `effective_date`.
3. The `accrual_batch_id` on the submitted assignment indicates the accrual batch. If present and assignment is submitted, `accrual_ready` is `true`.
4. Fetch the relevant audit event from `/api/audit` (event = `payroll.ready`). Record its `audit_id`.
5. Set `audit_scope` to `payroll_assignment_readiness`, `payroll_source_status` to `submitted`, `draft_exclusion_rule` to `exclude_draft_assignment`.
6. `control_result` = `ready_with_monitoring` when submitted assignment matches accrual batch.

## Answer Conventions

Every task provides an answer template at `input/payloads/answer_template.json`. Match it exactly.

- Use normalized business labels from [answer_schemas.md](references/answer_schemas.md) for all enum fields. No free-text explanations.
- ID-list arrays must contain only ID strings, not objects.
- `recruitment_cost_total` is the numeric sum of all cost ledger line items.
- `effective_date` is an ISO date string (YYYY-MM-DD).
- Return only JSON; no markdown fences or explanatory text.

## API Calling Pattern

The console base URL is `<TASK_ENV_BASE_URL>`. All endpoints return JSON arrays or objects. No authentication headers needed for API calls. Use `curl -s`.

Key endpoints: `/api/employees`, `/api/cases`, `/api/cases/{case_id}`, `/api/policies`, `/api/policies/{policy_id}`, `/api/payroll-ledgers`, `/api/recruitment`, `/api/documents`, `/api/messages`, `/api/audit`, `/api/audit/{audit_id}`. Full catalog in [api_endpoints.md](references/api_endpoints.md).

Fetch collection endpoints first, drill into detail endpoints only as needed.

## Ledger Record Interpretation

The `/api/payroll-ledgers` endpoint returns heterogeneous records distinguished by `record_type`:

- `Leave assignment` — leave policy assignments with `approved_leave_days`, `policy_name`, `status`, `period`
- `Salary assignment` — payroll assignments with `base_salary`, `status`, `period`, optionally `accrual_batch_id`
- `HRMS leave ledger`, `Payroll worksheet`, `People Ops adjustment` — secondary records

Status values: `Approved`, `Submitted`, `Draft`, `Superseded`.

For leave: latest Approved > Submitted > reject Draft/Superseded.
For payroll: Submitted only; reject Draft/Superseded.

## References

- [api_endpoints.md](references/api_endpoints.md) — API endpoint catalog and data structures
- [business_rules.md](references/business_rules.md) — Source precedence, exclusion, notice quality, folder readiness, audit scoping, and handoff rules
- [answer_schemas.md](references/answer_schemas.md) — Normalized business labels, enum values, and answer template conventions
