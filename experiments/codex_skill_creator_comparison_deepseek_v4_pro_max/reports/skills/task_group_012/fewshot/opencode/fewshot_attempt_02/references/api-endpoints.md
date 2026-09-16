# PeopleOps Console API Reference

All endpoints are read-only GET unless noted otherwise. No authentication headers are needed beyond the login step (the task environment is open once accessed).

The base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>`.

## Collection endpoints (pull full lists)

| Endpoint | Returns |
|----------|---------|
| `GET /api/summary` | Counts by entity type, departments, cases by status |
| `GET /api/manifest` | Business modules, file counts, seed metadata |
| `GET /api/employees` | All employee profiles (id, name, department, salary_band, leave_balance_days, status, etc.) |
| `GET /api/cases` | All cases (id, type, status, owner, priority, summary, policy_refs) |
| `GET /api/policies` | All policies with sections (id, title, summary, effective_date, status) |
| `GET /api/payroll-ledgers` | All ledger records: leave assignments, salary assignments, payroll worksheets, HRMS leave ledgers, People Ops adjustments |
| `GET /api/recruitment` | All recruitment openings with candidates, offer register, cost ledger, notice packets, payroll prechecks |
| `GET /api/documents` | All document folders with files, required_files, required_tags, tags, ready flag |
| `GET /api/messages` | All formal notices/messages with quality, defects, status |
| `GET /api/notifications` | All notifications (same shape as messages in this environment) |
| `GET /api/audit` | All audit events (id, case_id, employee_id, event, detail, actor, timestamp) |

## Detail endpoints (drill into single records)

| Endpoint | Returns |
|----------|---------|
| `GET /api/cases/{case_id}` | Full case detail with approvals array, attachments array, embedded audit_events, comments |
| `GET /api/policies/{policy_id}` | Full policy with all sections |
| `GET /api/audit/{audit_id}` | Single audit event detail |
| `GET /api/attachments/{attachment_id}` | Single attachment content |

## Write endpoint

| Endpoint | Purpose |
|----------|---------|
| `POST /api/cases/{case_id}/comments` | Add a comment to a case (rarely needed for verification tasks) |

## Ledger record types

The `/api/payroll-ledgers` endpoint returns records with a `record_type` field. Filter by this field to isolate what you need:

| record_type | Contains |
|-------------|----------|
| `Leave assignment` | `ledger_id`, `employee_id`, `policy_name`, `approved_leave_days`, `period`, `status` (Approved / Superseded / Draft / Submitted) |
| `Salary assignment` | `ledger_id`, `employee_id`, `base_salary`, `period`, `status` (Submitted / Draft / Superseded) |
| `Payroll worksheet` | Payroll processing data |
| `HRMS leave ledger` | HRMS-sourced leave balances |
| `People Ops adjustment` | Manual leave adjustments |

## Recruitment record structure

The `/api/recruitment` endpoint returns an array of openings. Each opening has:

- `opening_id` — matches the requisition/case ID
- `candidates[]` — each with `candidate_id`, `committee_decision` (Selected / Waitlisted / Rejected), `notice_status`
- `offer_register[]` — each with `offer_id`, `candidate_id`, `base_salary`, `status` (accepted / draft / withdrawn / none)
- `cost_ledger[]` — each with `line_id`, `label`, `amount`
- `notice_packets[]` — each with `candidate_id`, `notice_type`, `status`, `required_action`
- `payroll_precheck_records[]` — precheck entries if any exist

## Document structure

The `/api/documents` endpoint returns folders with:

- `document_id`, `title`
- `files[]` — files currently in the folder
- `required_files[]` — files that must be present for readiness
- `tags[]` — tags currently applied
- `required_tags[]` — tags that must be present for readiness
- `ready` — boolean, true only when all required files and tags are present

## Message / Notice structure

Messages (from `/api/messages` and `/api/notifications`) have:

- `message_id`, `case_id`, `subject`, `recipient`
- `quality` — `"valid"` or `"defective"`
- `defects[]` — array of defect labels when quality is defective; empty array when valid
- `status` — Draft, Sent, etc.

## Audit event structure

Audit events have:

- `audit_id` — unique identifier
- `case_id` — associated case
- `employee_id` — associated employee or candidate
- `event` — event type (e.g., `notice.defect`, `leave.profile_mismatch`, `payroll.ready`, `case.close_blocked`, `folder.tag_missing`, `payroll.draft_excluded`, `cross_module.escalation_package`)
- `detail` — human-readable description
- `actor` — who raised the event
- `timestamp` — ISO datetime
