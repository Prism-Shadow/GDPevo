# PeopleOps API Map

Use the configured task base URL from the prompt. In browser prompts this may be written as `<TASK_ENV_BASE_URL>`; in API work it is usually the same origin plus the paths below. Normalize trailing slashes before joining paths.

## Discovery

- `GET /api/manifest`: available modules, entry points, and file counts.
- `GET /api/summary`: counts, case status totals, departments, and high-level hints. Use it for orientation only.

## Entity Endpoints

- `GET /api/employees`
  - Common keys: `employee_id`, `name`, `department`, `department_id`, `designation`, `division`, `email`, `employment_type`, `hire_date`, `leave_balance_days`, `location`, `manager`, `remote_profile`, `salary_band`, `status`.
  - Treat profile summary fields as lower precedence when assignment history, ledgers, policies, or audit records indicate a newer approved state.

- `GET /api/cases`
  - Common keys: `case_id`, `case_type`, `employee_id`, `employee_name`, `owner`, `policy_refs`, `priority`, `status`, `summary`, `title`, `opened_at`, `due_at`.
  - Use this list to find the target case, then call the detail endpoint.

- `GET /api/cases/{case_id}`
  - Detail keys include the case list fields plus `approvals`, `attachments`, `audit_events`, and `comments`.
  - `approvals` commonly includes `approval_id`, `approver`, `decided_at`, `decision`, `note`, and `step`.
  - `attachments` commonly includes `attachment_id`, `name`, `kind`, `status`, `content`, `uploaded_at`, and `uploaded_by`.
  - Embedded `audit_events` use the same shape as the audit endpoint.

- `GET /api/policies` and `GET /api/policies/{policy_id}`
  - Common keys: `policy_id`, `title`, `status`, `effective_date`, `owner`, `summary`, `sections`.
  - Policy `sections` usually have `heading` and `body`. Use policy content to confirm leave entitlement, remote-work rules, document requirements, and notice requirements.

- `GET /api/payroll-ledgers`
  - This endpoint can contain leave assignments, payroll assignments, accrual batches, and worksheet-like records.
  - Common keys include `ledger_id`, `employee_id`, `employee_name`, `record_type`, `status`, `period`, `updated_at`, and record-specific fields such as policy name, approved leave days, worksheet leave days, salary, effective date, or batch readiness.
  - Filter by the requested employee and then by `record_type`, status, period/effective date, and audit support.

- `GET /api/recruitment`
  - Top-level keys commonly include `opening_id`, `title`, `status`, `candidates`, `offer_register`, `cost_ledger`, `notice_packets`, and `payroll_precheck_records`.
  - `candidates`: `candidate_id`, `name`, `pipeline_stage`, `committee_decision`, `notice_status`, `rounds`.
  - `offer_register`: `offer_id`, `candidate_id`, `status`, `base_salary`.
  - `cost_ledger`: `line_id`, `label`, `amount`; sum all recruiting campaign cost amounts when the template asks for the total.
  - `notice_packets`: `candidate_id`, `notice_type`, `status`, `required_action`, and sometimes `quality`, `defects`, or `message_id`.
  - `payroll_precheck_records`: `record_id`, `candidate_id`, `status`, `note` when present.

- `GET /api/documents`
  - Common keys: `document_id`, `title`, `files`, `required_files`, `tags`, `required_tags`, `ready`.
  - Folder readiness is usually computed from `ready` plus missing required files/tags.

- `GET /api/messages` and `GET /api/notifications`
  - Common keys: `message_id`, `case_id`, `recipient`, `subject`, `body`, `status`, `quality`, `defects`, `channel`, `sent_at`.
  - Use messages/notices for notice content and defects, but do not let a message-only status override structured approval, offer, assignment, or ledger records.

- `GET /api/audit` and `GET /api/audit/{audit_id}`
  - Common keys: `audit_id`, `case_id`, `employee_id`, `event`, `detail`, `actor`, `source`, `timestamp`.
  - Use audit records to confirm source precedence and scope. Include supporting audit IDs and exclude adjacent-scope audit IDs when the template asks.

- `GET /api/attachments/{attachment_id}`
  - Use when a case detail or document references an attachment and the prompt requires attachment contents.

## Practical Query Strategy

1. Fetch `manifest` and `summary` for orientation.
2. Fetch all list endpoints and save them before narrowing.
3. Search the snapshot for the target ID, target name, case ID, opening ID, candidate ID, policy ID, audit ID, offer ID, assignment ID, or batch ID.
4. Follow references from summary records into detail endpoints: case IDs to case details, policy IDs to policy details, audit IDs to audit details, attachment IDs to attachment detail.
5. Re-check the answer template before finalizing so field names guide which evidence matters.
