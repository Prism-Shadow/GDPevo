---
name: peopleops-console
description: Navigate and solve HR operations verification tasks using the PeopleOps Console REST API. Use when the user needs to verify employee onboarding closeout, review policy case folder and notice readiness, reconcile recruitment outcomes, validate leave source precedence, or inspect payroll assignment and accrual readiness — any task involving PeopleOps employee records, leave assignments, payroll, cases, recruitment, documents, messages, or audit evidence.
---

# PeopleOps Console Solver

Navigate the PeopleOps Console REST API to solve HR operations verification
tasks. The console exposes employee profiles, leave assignments, payroll
records, policy cases, recruitment pipelines, document folders, formal
notices/messages, and audit events through REST endpoints.

Present `<TASK_ENV_BASE_URL>` as the API root. No credentials are required for
API access — all endpoints return JSON without authentication.

Always inspect the API directly using HTTP requests (`curl`). Do not depend on
login forms or browser-based navigation; the API is the authoritative data
source.

---

## Workflow

### Step 1 — Orient via the manifest and summary

Start every task by reading these two endpoints to understand what data is
available:

```
GET <TASK_ENV_BASE_URL>/api/manifest
GET <TASK_ENV_BASE_URL>/api/summary
```

The manifest lists available business modules and approximate file sizes. The
summary gives counts, status breakdowns, and department details that help
narrow searches.

### Step 2 — Pull the entities referenced in the prompt

Every prompt names specific identifiers: an employee ID, a case ID, a
recruitment opening ID, or a combination. Pull the matching top-level
collections first, then drill into detail endpoints.

| What you need | Endpoint(s) to call |
|---|---|
| All employees | `GET /api/employees` |
| All cases | `GET /api/cases` |
| Single case detail | `GET /api/cases/{case_id}` |
| All policies | `GET /api/policies` |
| Single policy detail | `GET /api/policies/{policy_id}` |
| Payroll and leave ledger | `GET /api/payroll-ledgers` |
| Recruitment openings | `GET /api/recruitment` |
| Document folders | `GET /api/documents` |
| Formal notices / messages | `GET /api/messages` |
| Notifications | `GET /api/notifications` |
| All audit events | `GET /api/audit` |
| Single audit event | `GET /api/audit/{audit_id}` |

When the prompt references a specific case, pull both `/api/cases/{case_id}`
(for approvals, attachments, audit events embedded in the case) AND the
top-level `/api/audit` (for events that may cross-reference multiple cases).

### Step 3 — Apply the business rules

Read [references/business-rules.md](references/business-rules.md) for the
detailed rules governing leave precedence, payroll source, folder readiness,
notice quality, recruitment reconciliation, and audit scoping. Apply them in
the order that makes sense for the task.

The rules distill the policy documents available at `/api/policies`:
- **LEAVE-SRC-001** — Latest approved/submitted assignment controls leave
- **PAY-SRC-001** — Current submitted salary assignment controls base salary
- **HR-POL-014** — Remote-work jurisdiction, exception, and notice requirements
- **POL-DOCS-2026** — Required files and tags for lifecycle case folders

### Step 4 — Fill the answer template

The task always provides an `answer_template.json` under
`input/payloads/answer_template.json` in the task workspace. Read it first to
understand the required fields and their allowed values.

Every field in the template maps to a fact you can derive by applying the
business rules to the API data. Fill each field with the normalized label from
the template's `allowed_values` — never invent new labels or use free-form
explanatory text.

Return the filled-in JSON object as the final answer. Do not wrap it in
markdown code fences or add explanatory text outside the JSON.

---

## API Reference

Every endpoint returns a JSON array or object. The list endpoints return all
records; there is no pagination. Use `curl -s <url>` for all requests;
`python3 -m json.tool` can help with readability but is not required for
machine processing.

### /api/employees

Each employee record has:
- `employee_id`, `name`, `email`, `department`, `department_id`
- `designation`, `employment_type`, `hire_date`, `status`, `location`
- `manager`, `salary_band`, `leave_balance_days`, `remote_profile`, `division`

The `leave_balance_days` here is the *profile summary* value. It may be stale
relative to the authoritative leave ledger. Always cross-check against
`/api/payroll-ledgers` for the current period's leave assignments.

### /api/payroll-ledgers

This is a unified ledger containing both leave assignments and payroll/salary
assignments. Each record has:
- `ledger_id`, `record_type` ("Leave assignment" or "Salary assignment")
- `employee_id`, `employee_name`, `status`, `period`, `updated_at`
- Leave records: `approved_leave_days`, `worksheet_leave_days`, `policy_name`
- Salary records: `base_salary`, `accrual_batch_id` (when relevant)

Filter by `employee_id` and `record_type` to find the relevant records for a
given employee. The `status` field is critical: "Approved" for leave,
"Submitted" for salary — draft and superseded records must be excluded when
determining authoritative values.

### /api/cases and /api/cases/{case_id}

Case records link employees to policy workflows. The detail endpoint adds
`approvals`, `attachments`, `audit_events`, and `comments` sub-objects.

Approvals contain `approval_id`, `approver`, `decision`, `note`, `step`.
Audit events embedded in a case have `audit_id`, `actor`, `event`, `detail`,
`timestamp`.

### /api/documents

Document folders track required files and required tags for lifecycle cases.
Each document record has:
- `document_id`, `title`, `ready` (boolean)
- `files` (present files), `required_files` (expected files)
- `tags` (present tags), `required_tags` (expected tags)

A folder is `ready: true` only when every required file is present in `files`
and every required tag is present in `tags`.

### /api/messages

Messages represent formal notices sent to employees or candidates. Each has:
- `message_id`, `case_id`, `recipient`, `subject`, `body`, `channel`
- `status` ("Draft", "Sent", etc.)
- `quality` ("valid" or "defective")
- `defects` — array of defect labels

### /api/notifications

Notifications mirror the messages endpoint. Check both messages and
notifications when a task references formal notices, as defects may appear in
either collection.

### /api/recruitment

Each recruitment opening has:
- `opening_id`, `title`, `status`
- `candidates` array — each with `candidate_id`, `name`, `committee_decision`
  ("Selected"/"Waitlisted"/"Rejected"), `notice_status`, `pipeline_stage`
- `offer_register` — array of offers with `offer_id`, `candidate_id`,
  `base_salary`, `status` ("accepted"/"draft"/"withdrawn")
- `cost_ledger` — array of cost items with `line_id`, `label`, `amount`
- `notice_packets` — array with `candidate_id`, `notice_type`,
  `required_action`, `status`
- `payroll_precheck_records` — array (may be empty)

### /api/audit

The top-level audit collection may contain events not embedded in any case.
Each event has `audit_id`, `case_id`, `employee_id`, `event`, `actor`,
`detail`, `timestamp`, `source`.

Common event types and their meanings:
- `leave.profile_mismatch` — employee profile summary is stale
- `payroll.ready` — payroll assignment is ready with monitoring
- `payroll.draft_excluded` — draft payroll record must be ignored
- `notice.defect` — formal notice is defective
- `folder.tag_missing` — required tag is missing from document folder
- `case.close_blocked` — closeout blocked for folder/notice issues
- `cross_module.escalation_package` — multi-case audit wrapper; review related
  events before assigning entity-level issues

---

## Answer Format

Every task supplies an `answer_template.json` under the task workspace. Read it
to get the exact field names and allowed enumeration values. The template uses
`"type": "enum"` with `"allowed_values"` to define the normalized business
labels for each field.

Fill every field with one of the allowed values from the template. Derive each
value by applying the business rules in
[references/business-rules.md](references/business-rules.md) to the API data.
Return only the completed JSON — no markdown fences, no narrative.
