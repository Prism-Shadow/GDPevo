# PeopleOps Console API Endpoints

Base URL: `<TASK_ENV_BASE_URL>`

All endpoints return JSON. No authentication headers needed for API calls. Use `curl -s` to fetch data.

## Collection Endpoints

### GET /api/employees
Returns array of employee objects.

Each employee has: `employee_id`, `name`, `email`, `department`, `department_id`, `designation`, `division`, `employment_type`, `hire_date`, `leave_balance_days` (number, can be fractional), `location`, `manager`, `remote_profile`, `salary_band`, `status` (Active, Onboarding, Leave, Terminated).

### GET /api/cases
Returns array of case objects.

Each case has: `case_id`, `case_type`, `department`, `due_at`, `employee_id`, `employee_name`, `opened_at`, `owner`, `policy_refs` (array of policy IDs), `priority`, `status`, `summary`, `title`.

### GET /api/cases/{case_id}
Returns single case detail with additional fields: `approvals` (array of approval records with `approval_id`, `approver`, `decided_at`, `decision`, `note`, `step`), `attachments` (array with `attachment_id`, `content`, `kind`, `name`, `status`, `uploaded_at`, `uploaded_by`), `audit_events` (array of audit objects for this case), `comments` (array with `comment_id`, `author`, `body`, `created_at`, `visibility`).

### GET /api/policies
Returns array of policy objects.

Each policy has: `policy_id`, `title`, `summary`, `status`, `owner`, `effective_date`, `sections` (array with `heading` and `body`).

### GET /api/policies/{policy_id}
Returns single policy detail with the same structure.

### GET /api/payroll-ledgers
Returns array of heterogeneous ledger records. The primary discriminator is `record_type`.

Fields common to all records: `ledger_id`, `employee_id`, `employee_name`, `record_type`, `status`, `period`, `updated_at`, `approved_leave_days`, `worksheet_leave_days`.

Record types and their specific fields:

- **Leave assignment**: `policy_name` (string). Has meaningful `approved_leave_days` values. Used for leave policy decisions.
- **Salary assignment**: `base_salary` (number). Optionally `accrual_batch_id`. `approved_leave_days` and `worksheet_leave_days` are typically 0.
- **HRMS leave ledger**: Secondary leave records from HRMS system.
- **Payroll worksheet**: Secondary payroll records.
- **People Ops adjustment**: Manual adjustment records.

Status values across all record types: `Approved`, `Submitted`, `Draft`, `Superseded`.

### GET /api/recruitment
Returns array of recruitment openings.

Each opening has: `opening_id`, `title`, `status`, `candidates` (array with `candidate_id`, `name`, `pipeline_stage`, `committee_decision`, `notice_status`, `rounds`), `offer_register` (array with `candidate_id`, `offer_id`, `base_salary`, `status`), `cost_ledger` (array with `line_id`, `label`, `amount`), `notice_packets` (array with `candidate_id`, `notice_type`, `status`, `required_action`, `quality`, `defects`, `message_id`), `payroll_precheck_records` (array with `candidate_id`, `record_id`, `status`, `note`).

Candidate `committee_decision` values: `Selected`, `Waitlisted`, `Rejected`.
Offer register `status` values: `accepted`, `draft`, `withdrawn`.
Notice packet `notice_type` values: `offer`, `waitlist`, `rejection`.
Notice packet `status` values: `sent`, `not_sent`, `draft_reissue_required`.
Notice packet `quality` values: `valid`, `defective`.
Notice defect values: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.

### GET /api/documents
Returns array of document folders.

Each document has: `document_id`, `title`, `ready` (boolean), `files` (array of filenames), `required_files` (array), `tags` (array of tag strings), `required_tags` (array).

### GET /api/messages
Returns array of message/notice objects.

Each message has: `message_id`, `case_id`, `channel`, `recipient`, `subject`, `body`, `sent_at`, `status`, `quality`, `defects` (array of defect strings).

### GET /api/audit
Returns array of audit events.

Each audit event has: `audit_id`, `timestamp`, `case_id`, `employee_id`, `actor`, `event`, `source`, `detail`.

Common `event` values:
- `leave.profile_mismatch` — leave source precedence audit
- `payroll.ready` — payroll assignment readiness audit
- `notice.defect` — formal notice quality defect
- `case.close_blocked` — case closure blocked by defects
- `payroll.draft_excluded` — draft payroll exclusion notice
- `folder.tag_missing` — folder missing required tags
- `cross_module.escalation_package` — cross-module escalation

### GET /api/audit/{audit_id}
Returns single audit event detail with the same structure as collection entries.

### GET /api/manifest
Returns system manifest with business modules, entry points, file record counts, seed, and generation timestamp.

### GET /api/summary
Returns system summary with counts, case status breakdown, and department list.

### POST /api/cases/{case_id}/comments
Post a comment to a case. Body should include `body` and `visibility` fields.

## Data Extraction Patterns

### Filtering ledgers by employee and type
Fetch the full ledger collection, then filter in memory:

- Leave assignments for an employee: `record_type == "Leave assignment" AND employee_id == target`
- Salary assignments for an employee: `record_type == "Salary assignment" AND employee_id == target`

### Matching documents to cases
Document folders often reference the case in their `title`. The case detail's `attachments` may also reference a folder via `attachment_id` or `name`. When no explicit foreign key exists, match by title convention (e.g., a document titled "Exception-Case-ABC-123" belongs to CASE-ABC-123).

### Matching messages to cases
Messages carry a `case_id` field. Filter the messages array by the target `case_id`.

### Matching audit events to cases
Audit events carry a `case_id` field. Filter by the target case. A case detail response also includes a `audit_events` array.

### Matching recruitment entries
The recruitment array is keyed by `opening_id`. Iterate to find the target.
