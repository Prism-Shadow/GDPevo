## Base URL

Read the base URL from the task prompt (`<TASK_ENV_BASE_URL>`). If that token
appears unresolved, fall back to `http://task-env:9012/`.

The API does not require authentication headers. If the prompt supplies
credentials, they are for a frontend login; the REST endpoints are unsecured.

## Endpoints

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/manifest` | `business_modules`, `entry_points`, file counts |
| GET | `/api/summary` | Aggregate counts, departments, case statuses |
| GET | `/api/employees` | Array of employee objects |
| GET | `/api/cases` | Array of case objects (list view) |
| GET | `/api/cases/{case_id}` | Single case detail with approvals, attachments, audit_events, comments |
| GET | `/api/policies` | Array of policy objects with sections |
| GET | `/api/policies/{policy_id}` | Single policy detail |
| GET | `/api/payroll-ledgers` | Array of ledger entries (leave assignments, salary assignments, payroll worksheets, adjustments) |
| GET | `/api/recruitment` | Array of recruitment openings with candidates, cost_ledger, offer_register, notice_packets, payroll_precheck_records |
| GET | `/api/documents` | Array of document folders with files, required_files, required_tags, tags, ready |
| GET | `/api/messages` | Array of messages with quality, defects, case_id |
| GET | `/api/notifications` | Array (same shape as messages) |
| GET | `/api/audit` | Array of audit events |
| GET | `/api/audit/{audit_id}` | Single audit event detail |
| GET | `/api/attachments/{attachment_id}` | Single attachment detail |
| POST | `/api/cases/{case_id}/comments` | Submit a comment |

## Core Data Shapes

### Employee

```json
{
  "employee_id": "EMP-NNN",
  "name", "email", "department", "department_id",
  "designation", "division", "location", "manager",
  "employment_type", "hire_date", "status",
  "leave_balance_days", "salary_band", "remote_profile"
}
```

### Ledger Entry (from /api/payroll-ledgers)

Every entry carries `ledger_id`, `employee_id`, `employee_name`, `period`,
`record_type`, `status`, `approved_leave_days`, `worksheet_leave_days`,
`updated_at`. Additional fields vary by record_type:

- **Leave assignment**: `policy_name`
- **Salary assignment**: `base_salary`, sometimes `accrual_batch_id`
- **Payroll worksheet / HRMS leave ledger / People Ops adjustment**: only the base fields

Record statuses: `Approved`, `Submitted`, `Draft`, `Superseded`.

### Case (list from /api/cases)

```json
{
  "case_id", "case_type", "title", "status",
  "department", "employee_id", "employee_name",
  "owner", "priority", "policy_refs", "summary",
  "opened_at", "due_at"
}
```

### Case detail (from /api/cases/{case_id})

Adds `approvals[]`, `attachments[]`, `audit_events[]`, `comments[]` to the list
shape.

### Audit Event

```json
{
  "audit_id", "case_id", "employee_id",
  "event", "actor", "source",
  "detail", "timestamp"
}
```

### Policy

```json
{
  "policy_id", "title", "summary", "status",
  "effective_date", "owner",
  "sections": [{"heading", "body"}]
}
```

### Recruitment Opening

```json
{
  "opening_id", "title", "status",
  "candidates": [{
    "candidate_id", "name", "committee_decision",
    "pipeline_stage", "rounds", "notice_status"
  }],
  "offer_register": [{
    "offer_id", "candidate_id", "base_salary", "status"
  }],
  "cost_ledger": [{"line_id", "label", "amount"}],
  "notice_packets": [{
    "candidate_id", "notice_type", "status",
    "required_action", "defects", "quality", "message_id"
  }],
  "payroll_precheck_records": [{
    "candidate_id", "record_id", "status", "note"
  }]
}
```

### Document Folder

```json
{
  "document_id", "title", "ready",
  "files": [], "required_files": [],
  "tags": [], "required_tags": []
}
```

### Message / Notification

```json
{
  "message_id", "case_id", "subject", "body",
  "channel", "recipient", "status",
  "quality", "defects": [], "sent_at"
}
```

## Key Lookup Patterns

- Find an employee's ledger entries: fetch `/api/payroll-ledgers`, filter by `employee_id`.
- Find a case's full detail: GET `/api/cases/{case_id}` — includes audit_events and approvals embedded.
- Find audit events for an employee across cases: fetch `/api/audit`, filter by `employee_id` or `case_id`.
- Find a recruitment opening: fetch `/api/recruitment`, find by `opening_id`.
- Find a document folder: fetch `/api/documents`, find by `document_id` referenced in case attachments or audit details.
- Policy references in cases: the `policy_refs` array lists policy_id values; fetch `/api/policies` and match.
