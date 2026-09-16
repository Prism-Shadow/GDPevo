# API Endpoints Reference

## Base URL

The task environment provides a base URL, expressed as `<TASK_ENV_BASE_URL>` in
prompts. All endpoints are relative to that base.

No authentication headers are required for API calls. The web UI login uses the
credentials provided in the task prompt.

---

## GET /api/manifest

Returns available business modules, entry points, and file counts.

**Response fields:**

| Field | Description |
|---|---|
| `business_modules` | List of module names (Dashboard, Employees, Recruitment, Leave, Payroll, Policy Cases, Documents, Messages, Audit Log) |
| `entry_points.api_cases` | `/api/cases` |
| `entry_points.api_summary` | `/api/summary` |
| `entry_points.web` | Web UI URL |
| `files` | Object mapping data file names to record counts |
| `generated_at` | ISO timestamp of data generation |
| `seed` | Random seed used |

---

## GET /api/summary

Returns aggregate counts, departments, and status breakdowns.

**Response fields:**

| Field | Description |
|---|---|
| `counts` | Object: employees, cases, documents, messages, notifications, payroll_ledgers, policies, recruitment, audit_events |
| `cases_by_status` | Object mapping status labels to counts |
| `departments` | Array of `{department_id, name, leader}` |

---

## GET /api/employees

Returns all employee profiles. Filter client-side by `employee_id`.

**Response fields (each employee):**

| Field | Description |
|---|---|
| `employee_id` | Unique ID, e.g. `EMP-001` |
| `name` | Full name |
| `email` | Work email |
| `department` | Department name |
| `department_id` | Department ID, e.g. `D-103` |
| `designation` | Job title |
| `division` | Division name |
| `employment_type` | `Full-time`, etc. |
| `hire_date` | ISO date string |
| `leave_balance_days` | Number (float) — *note: this is the profile summary value, may be stale* |
| `location` | City |
| `manager` | Manager name |
| `remote_profile` | `Hybrid`, `Office-first`, `Remote-US`, `Exception pending` |
| `salary_band` | Band code, e.g. `B4`, `M1` |
| `status` | `Active`, `Onboarding`, `Leave` |

**Important**: The employee profile's `leave_balance_days` may be stale. Under
`LEAVE-SRC-001`, the approved leave assignment in the payroll-ledgers overrides
the profile summary when they conflict.

---

## GET /api/cases

Returns all cases. Also fetch individual case detail for embedded data.

**Response fields (each case):**

| Field | Description |
|---|---|
| `case_id` | Unique case ID |
| `case_type` | `Remote work exception`, `Leave policy setup`, `Salary structure change`, `Recruiting pipeline`, `Document correction` |
| `department` | Department name |
| `due_at` | ISO timestamp |
| `employee_id` | Primary employee or `REQ-*` for recruitment |
| `employee_name` | Employee or descriptive label |
| `opened_at` | ISO timestamp |
| `owner` | Responsible team |
| `policy_refs` | Array of policy IDs applicable to this case |
| `priority` | `Urgent`, `High`, `Medium` |
| `status` | `Approved`, `In Review`, `Needs Info`, `Submitted` |
| `summary` | One-line summary |
| `title` | Case title |

---

## GET /api/cases/{case_id}

Returns a single case with embedded detail not in the list endpoint.

**Additional fields (beyond list fields):**

| Field | Description |
|---|---|
| `approvals` | Array of `{approval_id, approver, decided_at, decision, note, step}` |
| `attachments` | Array of `{attachment_id, content, kind, name, status, uploaded_at, uploaded_by}` |
| `audit_events` | Array of audit events embedded in the case |
| `comments` | Array of `{author, body, comment_id, created_at, visibility}` |

Approvals are crucial for determining the final decision and approval authority.
Attachments of kind `Checklist` contain folder readiness information.

---

## GET /api/policies

Returns all policies.

**Response fields (each policy):**

| Field | Description |
|---|---|
| `policy_id` | Unique policy ID |
| `title` | Policy title |
| `summary` | One-line summary |
| `status` | `Active` |
| `effective_date` | ISO date |
| `owner` | Responsible team |
| `sections` | Array of `{heading, body}` |

Key policies:
- **HR-POL-014** (Remote Work Policy): jurisdiction and notice requirements
- **LEAVE-SRC-001** (Leave Source Precedence): approved/submitted assignment controls
- **PAY-SRC-001** (Payroll Assignment Source): submitted salary controls; recruiting handoff gate
- **POL-DOCS-2026** (Lifecycle Folder Checklist): required files and tags for folder readiness

---

## GET /api/policies/{policy_id}

Returns a single policy detail (same shape as the list entry).

---

## GET /api/payroll-ledgers

Returns all ledger entries. **This is the authoritative source for leave
assignments and salary assignments.**

**Response fields (each ledger entry):**

| Field | Description |
|---|---|
| `ledger_id` | Unique ledger ID, e.g. `LA-001-2026-APP`, `PAY-001-2026-SUB` |
| `employee_id` | Employee ID |
| `employee_name` | Employee name |
| `record_type` | `Leave assignment`, `Salary assignment`, `People Ops adjustment`, `Payroll worksheet`, `HRMS leave ledger` |
| `period` | Period string, e.g. `2026`, `2026-03` |
| `status` | `Approved`, `Submitted`, `Draft`, `Superseded` |
| `policy_name` | Policy name (for leave assignments) |
| `approved_leave_days` | Number (float); for non-leave records this is 0 |
| `worksheet_leave_days` | Number (float); for non-leave records this is 0 |
| `base_salary` | Number (for salary assignments; 0 for leave assignments) |
| `accrual_batch_id` | Accrual batch ID (for salary assignments with accrual data) |
| `updated_at` | ISO timestamp of last update |

**Filtering guidance:**
- Leave assignments: `record_type == "Leave assignment"`
- Salary assignments: `record_type == "Salary assignment"`
- Non-authoritative noise: `People Ops adjustment`, `Payroll worksheet`, `HRMS leave ledger` — these are NOT leave assignments or salary assignments

---

## GET /api/recruitment

Returns all recruitment openings.

**Response fields (each opening):**

| Field | Description |
|---|---|
| `opening_id` | Unique opening ID, e.g. `REQ-XX-01` |
| `title` | Position title |
| `status` | `Submitted` |
| `candidates` | Array of candidate objects |
| `offer_register` | Array of `{offer_id, candidate_id, base_salary, status}` |
| `cost_ledger` | Array of `{line_id, label, amount}` |
| `notice_packets` | Array of notice objects |
| `payroll_precheck_records` | Array of `{record_id, candidate_id, status, note}` |

**Candidate fields:**

| Field | Description |
|---|---|
| `candidate_id` | Unique candidate ID, e.g. `CAND-XX-0001` |
| `name` | Candidate name |
| `committee_decision` | `Selected`, `Waitlisted`, `Rejected` |
| `notice_status` | Notice delivery status |
| `pipeline_stage` | `Final committee` |
| `rounds` | Array of interview round scores |

**Notice packet fields:**

| Field | Description |
|---|---|
| `candidate_id` | Target candidate |
| `notice_type` | `waitlist`, `rejection`, `offer` |
| `status` | `not_sent`, `draft_reissue_required` |
| `required_action` | `send_waitlist_notice`, `send_rejection_notice`, `reissue_waitlist_notice_not_rejection` |
| `defects` | Array of defect strings (if any) |
| `quality` | `valid`, `defective` |
| `message_id` | Associated message ID |

**Offer register fields:**

| Field | Description |
|---|---|
| `offer_id` | Unique offer ID |
| `candidate_id` | Candidate |
| `base_salary` | Number |
| `status` | `accepted`, `draft`, `withdrawn` |

---

## GET /api/documents

Returns all document folders.

**Response fields (each folder):**

| Field | Description |
|---|---|
| `document_id` | Unique document ID |
| `title` | Folder title |
| `files` | Array of filenames present |
| `required_files` | Array of filenames required (per POL-DOCS-2026) |
| `tags` | Array of tags present |
| `required_tags` | Array of tags required |
| `ready` | Boolean: true only when all required files and all required tags are present |

---

## GET /api/messages

Returns all messages (formal notices).

**Response fields (each message):**

| Field | Description |
|---|---|
| `message_id` | Unique message ID |
| `case_id` | Associated case |
| `channel` | `Email`, `HRMS inbox` |
| `subject` | Subject line |
| `body` | Message body text |
| `recipient` | Recipient name |
| `sent_at` | ISO timestamp |
| `status` | `Draft` |
| `quality` | `valid` or `defective` |
| `defects` | Array of defect strings: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy` |

---

## GET /api/audit

Returns all audit events. **Audit events are the authoritative QA verdicts.**

**Response fields (each event):**

| Field | Description |
|---|---|
| `audit_id` | Unique audit event ID |
| `case_id` | Associated case |
| `employee_id` | Associated employee |
| `event` | Event type: `leave.profile_mismatch`, `payroll.ready`, `payroll.draft_excluded`, `notice.defect`, `case.close_blocked`, `folder.tag_missing`, `cross_module.escalation_package` |
| `actor` | QA actor name |
| `detail` | Human-readable detail |
| `source` | `Audit Service` |
| `timestamp` | ISO timestamp |

---

## GET /api/audit/{audit_id}

Returns a single audit event detail (same shape as list entry).

---

## GET /api/notifications

Returns all system notifications (same shape as messages, useful for
cross-module context).

---

## GET /api/attachments/{attachment_id}

Returns attachment detail. Useful for reading folder checklist content when it
isn't fully captured in the case detail.

---

## POST /api/cases/{case_id}/comments

Post a comment to a case. Not typically needed for verification tasks.
