# PeopleOps Console API Reference

Complete catalogue of every REST endpoint, the fields returned, and how to use
them.

Base URL: `<TASK_ENV_BASE_URL>`
Credentials: `ops.lead@peopleops.local` / `PeopleOps#2026`
Auth: None required; all GET endpoints are open.

---

## Discovery endpoints

### `GET /api/manifest`

```json
{
  "business_modules": ["Dashboard", "Employees", "Recruitment", "Leave", "Payroll", "Policy Cases", "Documents", "Messages", "Audit Log"],
  "entry_points": {
    "api_cases": "/api/cases",
    "api_summary": "/api/summary",
    "web": "<TASK_ENV_BASE_URL>/"
  },
  "files": {
    "audit_events.json": 8,
    "cases.json": 7,
    "documents.json": 4,
    "employees.json": 44,
    "messages.json": 4,
    "payroll_ledgers.json": 61,
    "policies.json": 4,
    "recruitment.json": 2
  },
  "generated_at": "...",
  "seed": 12012
}
```

Use this to confirm which modules and file counts are available.

### `GET /api/summary`

Returns aggregated counts and department list:

| Field | Description |
|---|---|
| `counts.employees` | Total employee records |
| `counts.cases` | Total case records |
| `counts.audit_events` | Total audit events |
| `counts.documents` | Total document folders |
| `counts.messages` | Total messages |
| `counts.notifications` | Total notifications |
| `counts.payroll_ledgers` | Total payroll ledger records |
| `counts.policies` | Total policy documents |
| `counts.recruitment` | Total recruitment openings |
| `departments` | Array of { department_id, name, leader } |
| `cases_by_status` | Count of cases grouped by status |

---

## Employee records

### `GET /api/employees`

Returns an array of all 44 employee profiles.

Each employee object:

| Field | Type | Example |
|---|---|---|
| `employee_id` | string | `EMP-104` |
| `name` | string | `Mira Chen` |
| `department` | string | `Engineering` |
| `department_id` | string | `D-103` |
| `designation` | string | `Platform Engineer` |
| `division` | string | `Product and Technology` |
| `email` | string | `mira.chen@northwind-people.example` |
| `employment_type` | string | `Full-time` |
| `hire_date` | string | `2026-03-01` |
| `leave_balance_days` | number | `18` |
| `location` | string | `Boston` |
| `manager` | string | `Alicia Ames` |
| `remote_profile` | string | `Hybrid` |
| `salary_band` | string | `B4` |
| `status` | string | `Onboarding` / `Active` |

Filter in your code: loop through the array and match by `employee_id`.

---

## Case records

### `GET /api/cases`

Returns an array of all 7 cases.

Each case object:

| Field | Type |
|---|---|
| `case_id` | string |
| `case_type` | string (e.g. `Remote work exception`, `Recruiting pipeline`, `Leave policy setup`) |
| `title` | string |
| `department` | string |
| `employee_id` | string |
| `employee_name` | string |
| `owner` | string |
| `priority` | string |
| `status` | string (`Submitted`, `In Review`, `Needs Info`, `Approved`) |
| `summary` | string |
| `policy_refs` | array of policy IDs |
| `opened_at` | ISO timestamp |
| `due_at` | ISO timestamp |

### `GET /api/cases/{case_id}`

Returns the expanded case detail with nested arrays:

| Field | Description |
|---|---|
| `approvals` | Array of approval records: { approval_id, approver, decision, decided_at, step, note } |
| `attachments` | Array: { attachment_id, name, kind, content, status, uploaded_by, uploaded_at } |
| `audit_events` | Array of audit events related to this case |
| `comments` | Array: { comment_id, author, body, created_at, visibility } |
| plus all top-level case fields |

### `POST /api/cases/{case_id}/comments`

The only write endpoint. Accepts a JSON body with a `body` field. Not needed
for read-only verification tasks.

---

## Policy documents

### `GET /api/policies`

Returns an array of all 4 policies.

### `GET /api/policies/{policy_id}`

Returns a single policy:

| Field | Description |
|---|---|
| `policy_id` | string (e.g. `LEAVE-SRC-001`) |
| `title` | string |
| `summary` | string |
| `owner` | string |
| `status` | string (`Active`) |
| `effective_date` | string |
| `sections` | array of { heading, body } |

The four policies and their key rules:

| Policy ID | Title | Key rule |
|---|---|---|
| `LEAVE-SRC-001` | Leave Source Precedence | Latest approved/submitted assignment controls; draft, voided, obsolete excluded. |
| `PAY-SRC-001` | Payroll Assignment Source | Current submitted salary assignment controls. Draft excluded. Recruiting handoff only after accepted offer. |
| `HR-POL-014` | Remote Work Policy | Domestic jurisdiction requirements; international exceptions need executive approval, tax equalization, appeal instructions, ack deadline. |
| `POL-DOCS-2026` | Lifecycle Folder Checklist | Folder not ready unless all required files and tags present. |

---

## Payroll ledgers

### `GET /api/payroll-ledgers`

Returns an array of all 61 payroll ledger records. These are mixed:
**leave assignments** and **salary assignments** in the same array.

Filter by `record_type`:
- `"Leave assignment"` → leave policy records
- `"Salary assignment"` → base salary records

**Leave assignment fields:**

| Field | Description |
|---|---|
| `ledger_id` | string (e.g. `LA-104-2026-B`) |
| `employee_id` | string |
| `employee_name` | string |
| `record_type` | `"Leave assignment"` |
| `period` | string (e.g. `2026`) |
| `policy_name` | string (e.g. `Engineering Flex Leave 2026`) |
| `status` | `Approved`, `Submitted`, `Draft`, `Superseded` |
| `approved_leave_days` | number |
| `worksheet_leave_days` | number |
| `updated_at` | ISO timestamp |

**Salary assignment fields:**

| Field | Description |
|---|---|
| `ledger_id` | string (e.g. `PAY-104-2026-SUB`) |
| `employee_id` | string |
| `employee_name` | string |
| `record_type` | `"Salary assignment"` |
| `period` | string (e.g. `2026-03`) |
| `status` | `Submitted`, `Draft` |
| `base_salary` | number |
| `accrual_batch_id` | string (e.g. `ACCR-2026-04-B`) — present when accrual is ready |
| `updated_at` | ISO timestamp |

---

## Documents (case folders)

### `GET /api/documents`

Returns an array of all 4 document folders.

Each document:

| Field | Description |
|---|---|
| `document_id` | string (e.g. `DOC-RW-221`) |
| `title` | string |
| `ready` | boolean |
| `files` | array of present file names |
| `required_files` | array of required file names |
| `tags` | array of present tags |
| `required_tags` | array of required tags |

---

## Messages

### `GET /api/messages`

Returns an array of all 4 formal notice messages.

Each message:

| Field | Description |
|---|---|
| `message_id` | string |
| `case_id` | string |
| `subject` | string |
| `body` | string |
| `channel` | string (`Email`, `HRMS inbox`) |
| `recipient` | string |
| `status` | string (`Draft`, `Sent`) |
| `quality` | `valid` or `defective` |
| `defects` | array of defect codes |
| `sent_at` | ISO timestamp |

---

## Notifications

### `GET /api/notifications`

Returns an array — identical structure to messages. Use the same field
descriptions as messages above.

---

## Audit events

### `GET /api/audit`

Returns an array of all audit events.

### `GET /api/audit/{audit_id}`

Returns a single audit event.

Each audit event:

| Field | Description |
|---|---|
| `audit_id` | string (e.g. `AUD-CASE221-09`) |
| `actor` | string (e.g. `Legal QA`, `Payroll QA`, `Records QA`) |
| `case_id` | string — the case this audit relates to |
| `employee_id` | string — the employee this audit relates to |
| `event` | string — domain classifier (see below) |
| `detail` | string — human-readable finding |
| `source` | string (`Audit Service`) |
| `timestamp` | ISO timestamp |

**Event type taxonomy for scoping:**

| Event value | Scope |
|---|---|
| `notice.defect` | document_notice_findings_only |
| `folder.tag_missing` | document_notice_findings_only |
| `folder.file_missing` | document_notice_findings_only |
| `case.close_blocked` | may span multiple; read detail carefully |
| `leave.profile_mismatch` | leave_source_precedence_only |
| `payroll.ready` | payroll_assignment_readiness |
| `payroll.draft_excluded` | payroll_assignment_readiness |
| `cross_module.escalation_package` | cross-cutting; inspect detail for related events |

---

## Recruitment

### `GET /api/recruitment`

Returns an array of all recruitment openings.

Each opening:

| Field | Description |
|---|---|
| `opening_id` | string (e.g. `REQ-DA-77`) |
| `title` | string |
| `status` | string |
| `candidates` | array of candidate records |
| `offer_register` | array of offer records |
| `cost_ledger` | array of cost line items |
| `notice_packets` | array of notice status records |
| `payroll_precheck_records` | array |

**Candidate record:**

| Field | Description |
|---|---|
| `candidate_id` | string (e.g. `CAND-DA-7701`) |
| `name` | string |
| `pipeline_stage` | string (e.g. `Final committee`) |
| `committee_decision` | `Selected`, `Waitlisted`, `Rejected` |
| `notice_status` | string |
| `rounds` | array of integers (interview scores) |

**Offer record:**

| Field | Description |
|---|---|
| `offer_id` | string |
| `candidate_id` | string |
| `base_salary` | number |
| `status` | `accepted`, `draft`, `withdrawn`, `none` |

**Cost ledger item:**

| Field | Description |
|---|---|
| `line_id` | string |
| `label` | string |
| `amount` | number |

**Notice packet:**

| Field | Description |
|---|---|
| `candidate_id` | string |
| `notice_type` | `waitlist`, `rejection` |
| `status` | `not_sent`, `sent` |
| `required_action` | `send_waitlist_notice`, `send_rejection_notice`, etc. |

---

## Attachments

### `GET /api/attachments/{attachment_id}`

Returns attachment content. Attachment IDs appear inside case detail
(`GET /api/cases/{case_id}`) under the `attachments` array.
