# PeopleOps Console API Reference

Base URL: `<TASK_ENV_BASE_URL>` (from prompt, typically `http://task-env:9012/`)

Credentials: `ops.lead@peopleops.local` / `PeopleOps#2026`

## Endpoints

### GET /api/manifest

Returns business module list, entry points, and file counts.

```json
{
  "business_modules": ["Dashboard","Employees",...],
  "entry_points": {"api_cases":"/api/cases","api_summary":"/api/summary","web":"<TASK_ENV_BASE_URL>/"},
  "files": {"employees.json":44,"cases.json":7,...},
  "generated_at": "2026-...",
  "seed": 12012
}
```

### GET /api/summary

Returns case status counts, total row counts per collection, and department listing.

```json
{
  "cases_by_status": {"Approved":1,"In Review":2,...},
  "counts": {"audit_events":8,"cases":7,"documents":4,"employees":44,...},
  "departments": [{"department_id":"D-101","leader":"...","name":"People Ops"},...]
}
```

### GET /api/employees

Returns all 44 employees. Key fields:

| Field | Type | Description |
|---|---|---|
| employee_id | string | EMP-NNN format |
| name | string | Full name |
| department | string | Department name |
| department_id | string | D-NNN format |
| designation | string | Job title |
| division | string | Division name |
| email | string | Work email |
| employment_type | string | Full-time, etc. |
| hire_date | string | ISO date |
| leave_balance_days | number | Days shown in profile summary (may be stale) |
| location | string | City name |
| manager | string | Manager name |
| remote_profile | string | Hybrid, Office-first, Remote-US, Exception pending |
| salary_band | string | B3, B4, M1, etc. |
| status | string | Active, Onboarding |

### GET /api/cases

Returns all cases. Key fields:

| Field | Type | Description |
|---|---|---|
| case_id | string | CASE-RW-NNN, CASE-NNN, REQ-XX-NN format |
| case_type | string | Remote work exception, Leave policy setup, Salary structure change, Recruiting pipeline, Document correction |
| department | string | Department name |
| due_at | string | ISO datetime |
| employee_id | string | Owner employee or REQ-XX-NN |
| employee_name | string | Employee or candidate group name |
| opened_at | string | ISO datetime |
| owner | string | Legal Desk, People Ops Compliance, Payroll, Recruiting Desk, etc. |
| policy_refs | list[string] | Policy IDs applicable |
| priority | string | High, Medium |
| status | string | In Review, Submitted, Approved, Needs Info |
| summary | string | Short description |
| title | string | Human-readable title |

### GET /api/cases/{case_id}

Returns case detail including `approvals`, `attachments`, `audit_events`, and `comments`.

**approvals:**

| Field | Type | Description |
|---|---|---|
| approval_id | string | APP-NNN-XXXX format |
| approver | string | HR Director, VP People, People Ops |
| decided_at | string | ISO datetime |
| decision | string | Approved, Approved with conditions |
| note | string | Free-text note |
| step | string | Intake, Final approval |

**attachments:**

| Field | Type | Description |
|---|---|---|
| attachment_id | string | ATT-NNN-XXXX format |
| content | string | Description of content |
| kind | string | Checklist, Text |
| name | string | Filename |
| status | string | Missing tax equalization, Missing required evidence, Filed |
| uploaded_at | string | ISO datetime |
| uploaded_by | string | Records, People Ops |

**audit_events:** Array of audit event objects (same shape as GET /api/audit).

**comments:**

| Field | Type | Description |
|---|---|---|
| author | string | Comment author |
| body | string | Comment text |
| comment_id | string | CMT-NNN-N format |
| created_at | string | ISO datetime |
| visibility | string | Internal |

### GET /api/policies

Returns all 4 policies. Key fields:

| Field | Type | Description |
|---|---|---|
| policy_id | string | HR-POL-014, LEAVE-SRC-001, PAY-SRC-001, POL-DOCS-2026 |
| title | string | Human-readable title |
| owner | string | Legal Desk, People Ops, Payroll, Records |
| status | string | Active |
| effective_date | string | ISO date |
| summary | string | One-line summary |
| sections | list | Array of {heading, body} objects |

### GET /api/policies/{policy_id}

Returns a single policy with the same shape as the list entry.

### GET /api/payroll-ledgers

Returns all 61 payroll ledger records. Mixed record types: Leave assignment and Salary assignment.

**Leave assignment records:**

| Field | Type | Description |
|---|---|---|
| ledger_id | string | LA-NNN-YYYY-XX format |
| employee_id | string | EMP-NNN |
| employee_name | string | Full name |
| record_type | string | "Leave assignment" |
| policy_name | string | Policy display name |
| approved_leave_days | integer | Leave days |
| worksheet_leave_days | integer | Worksheet days |
| period | string | Year "2026" |
| status | string | Approved, Superseded, Draft |
| updated_at | string | ISO datetime |

**Salary assignment records:**

| Field | Type | Description |
|---|---|---|
| ledger_id | string | PAY-NNN-YYYY-XXX format |
| employee_id | string | EMP-NNN |
| employee_name | string | Full name |
| record_type | string | "Salary assignment" |
| base_salary | number | Salary amount |
| period | string | "2026-03", "2026-04", "2026-05" |
| status | string | Submitted, Draft |
| accredited_leave_days | integer | Always 0 |
| worksheet_leave_days | integer | Always 0 |
| accrual_batch_id | string | ACCR-YYYY-MM-X format (optional) |
| updated_at | string | ISO datetime |

### GET /api/recruitment

Returns recruitment openings with candidates, offer register, cost ledger, and notice packets.

**Top-level:**

| Field | Type | Description |
|---|---|---|
| opening_id | string | REQ-XX-NN format |
| title | string | Role title |
| status | string | Submitted |
| candidates | list | Candidate objects |
| offer_register | list | Offer objects |
| cost_ledger | list | Cost line items |
| notice_packets | list | Notice packet objects |
| payroll_precheck_records | list | Payroll precheck records |

**candidates:**

| Field | Type | Description |
|---|---|---|
| candidate_id | string | CAND-XX-NNNN format |
| name | string | Full name |
| committee_decision | string | Selected, Waitlisted, Rejected |
| notice_status | string | Offer package approved, Notice not sent, Sent; quality review flagged, Rejection notice sent |
| pipeline_stage | string | Final committee |
| rounds | list[integer] | Interview round scores |

**offer_register:**

| Field | Type | Description |
|---|---|---|
| offer_id | string | OFFER-XX-NNNN format |
| candidate_id | string | CAND-XX-NNNN |
| base_salary | number | Salary amount |
| status | string | accepted, draft, withdrawn |

**cost_ledger:**

| Field | Type | Description |
|---|---|---|
| line_id | string | REQ-XX-NN-COST-NN |
| label | string | Description |
| amount | number | Cost in currency units |

**notice_packets:**

| Field | Type | Description |
|---|---|---|
| candidate_id | string | CAND-XX-NNNN |
| notice_type | string | waitlist, rejection, offer |
| status | string | not_sent, sent |
| required_action | string | send_waitlist_notice, send_rejection_notice |

### GET /api/documents

Returns document folders. Key fields:

| Field | Type | Description |
|---|---|---|
| document_id | string | DOC-XXXX-XXX format |
| title | string | Folder title |
| ready | boolean | Whether folder meets requirements |
| files | list[string] | Files present |
| required_files | list[string] | Files that must be present |
| tags | list[string] | Tags present |
| required_tags | list[string] | Tags that must be present |

### GET /api/messages

Returns messages/notices. Key fields:

| Field | Type | Description |
|---|---|---|
| message_id | string | MSG-XXXX-XXX format |
| case_id | string | Associated case |
| channel | string | Email, HRMS inbox |
| recipient | string | Recipient name |
| subject | string | Message subject |
| body | string | Message body text |
| status | string | Draft |
| quality | string | valid, defective |
| defects | list[string] | Defect codes: missing_ack_deadline, missing_appeal_instructions, missing_waitlist_status, missing_correct_policy |
| sent_at | string | ISO datetime |

### GET /api/notifications

Same shape as /api/messages (mirrors message records).

### GET /api/audit

Returns all audit events. Key fields:

| Field | Type | Description |
|---|---|---|
| audit_id | string | AUD-XXXX-NN format |
| case_id | string | Associated case |
| employee_id | string | Target employee or candidate |
| actor | string | QA Bot, People Ops QA, Legal QA, Payroll QA, Recruiting QA, Records QA, People Ops Control Tower |
| event | string | leave.profile_mismatch, payroll.ready, notice.defect, case.close_blocked, payroll.draft_excluded, folder.tag_missing, cross_module.escalation_package |
| detail | string | Full description of finding |
| source | string | Audit Service |
| timestamp | string | ISO datetime |

### GET /api/audit/{audit_id}

Returns a single audit event with the same shape.

### GET /api/attachments/{attachment_id}

Returns attachment detail (may return 404 for some IDs).

### POST /api/cases/{case_id}/comments

Creates a comment on a case. Not needed for read-only verification tasks.
