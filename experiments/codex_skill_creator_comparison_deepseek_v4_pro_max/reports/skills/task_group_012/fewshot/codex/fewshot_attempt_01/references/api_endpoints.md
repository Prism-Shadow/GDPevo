# API Endpoint Catalog

All endpoints are reachable at \\`<TASK_ENV_BASE_URL>/api/...\\`. No authentication required.

## List Endpoints

### GET /api/manifest
Metadata about the task environment. Returns business_modules, entry_points, files (record counts), generated_at, seed.

### GET /api/summary
Aggregate counts and department list. Returns cases_by_status, counts, departments.

### GET /api/employees
Returns an array of employee records. Filter by employee_id in code.

Fields per employee: employee_id, name, email, department, department_id, designation, division, employment_type, hire_date, leave_balance_days, location, manager, remote_profile, salary_band, status.

The leave_balance_days and salary_band on the employee profile may be STALE. Always cross-check against /api/payroll-ledgers before trusting profile values.

### GET /api/cases
Returns an array of case summaries. Fields: case_id, case_type, department, due_at, employee_id, employee_name, opened_at, owner, policy_refs, priority, status, summary, title.

Case types include: New hire onboarding, Recruiting pipeline, Remote work exception, Leave policy setup, Salary structure change, Final payroll clearance, Document correction.

### GET /api/cases/{case_id}
Detailed case view with approvals (approval_id, approver, decided_at, decision, note, step), attachments (attachment_id, content, kind, name, status, uploaded_at, uploaded_by), audit_events (actor, audit_id, case_id, detail, employee_id, event, source, timestamp), and comments (author, body, comment_id, created_at, visibility).

### GET /api/policies
Returns array of policies. Each has policy_id, title, summary, status, effective_date, owner, and sections (heading, body pairs).

Four policies: HR-POL-014 (Remote Work Policy, Legal Desk), LEAVE-SRC-001 (Leave Source Precedence, People Ops), PAY-SRC-001 (Payroll Assignment Source, Payroll), POL-DOCS-2026 (Lifecycle Folder Checklist, Records).

### GET /api/policies/{policy_id}
Single policy detail with full sections.

### GET /api/payroll-ledgers
Returns array of ledger entries. This is the AUTHORITATIVE source for leave assignments and salary assignments. Filter by employee_id and record_type in code.

Fields: ledger_id, employee_id, employee_name, period, record_type, status, policy_name (leave), base_salary (salary), approved_leave_days, worksheet_leave_days, updated_at, accrual_batch_id (salary).

Record types: Leave assignment, Salary assignment, HRMS leave ledger, Payroll worksheet, People Ops adjustment.
Status values: Approved, Submitted, Draft, Superseded.

For leave assignments: use Approved records. Exclude Draft and Superseded.
For salary assignments: use Submitted records. Exclude Draft.

### GET /api/recruitment
Returns array of recruitment openings. Each contains:
- opening_id, title, status
- candidates: each has candidate_id, name, committee_decision (Selected/Waitlisted/Rejected), notice_status, pipeline_stage, rounds
- offer_register: each has offer_id, candidate_id, base_salary, status (accepted/draft/withdrawn)
- cost_ledger: each has line_id, label, amount
- notice_packets: each has candidate_id, notice_type, status, required_action, defects, quality, message_id
- payroll_precheck_records: each has record_id, candidate_id, status, note

### GET /api/documents
Returns array of document folders. Each has document_id, title, ready (boolean), files (present), required_files, tags (present), required_tags.

### GET /api/messages
Returns array of formal notice messages. Each has message_id, case_id, subject, body, recipient, channel, sent_at, status, quality (valid/defective), defects (array).

Defect codes: missing_ack_deadline, missing_appeal_instructions, missing_waitlist_status, missing_correct_policy.

### GET /api/notifications
Returns array of notification records (same structure as messages).

### GET /api/audit
Returns array of audit events. Each has audit_id, case_id, employee_id, actor, event, detail, source, timestamp.

### GET /api/audit/{audit_id}
Single audit event detail.

### POST /api/cases/{case_id}/comments
Add a comment. Body: {"author": "...", "body": "..."}.

### GET /api/attachments/{attachment_id}
Fetch attachment content by ID.
