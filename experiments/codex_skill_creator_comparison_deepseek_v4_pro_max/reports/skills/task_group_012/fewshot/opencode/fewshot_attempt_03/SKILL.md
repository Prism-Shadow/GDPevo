---
name: peopleops-hrms-solver
description: Solve People Ops HRMS lifecycle tasks for the Northwind People Lifecycle Portal. Use when the task involves onboarding closeout, leave/payroll verification, remote-work policy case review, recruitment reconciliation, leave source precedence, or payroll accrual readiness. The task will reference the PeopleOps Console, People Lifecycle Portal, or Northwind HRMS, and require querying REST API endpoints against a task environment. Always use this skill when the user mentions employees, cases, policies, leave assignments, payroll ledgers, recruitment openings, documents, messages, audit logs, or any lifecycle closeout task.
---

# People Ops HRMS Solver

Solve HR lifecycle verification and reconciliation tasks against the Northwind People Lifecycle Portal REST API. The system models a shared HR operations workspace with employees, policy cases, leave assignments, payroll records, recruitment pipelines, document folders, formal notices, and audit events.

The target solver reads a task prompt that names a specific employee, case, or opening, provides a base URL, credentials, and an answer template JSON schema. The solver queries the API, applies consistent business rules, and returns JSON matching the template using only the allowed enum labels.

## Required Credentials

Every task uses the same login:

```
ops.lead@peopleops.local
PeopleOps#2026
```

These are not secret; they are part of the task setup. The solver does not need to authenticate programmatically -- the REST API is open and the credentials are informational context for the business workflow.

## API Endpoints

All endpoints are rooted at the configured runner URL, typically `<TASK_ENV_BASE_URL>` or `http://task-env:9012/`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/summary` | Dataset overview: counts, departments |
| GET | `/api/employees` | All employee profiles (leave_balance_days, status, policy) |
| GET | `/api/cases` | All cases with status, type, policy refs, summary |
| GET | `/api/cases/{case_id}` | Case detail: approvals, attachments, audit events, comments |
| GET | `/api/policies` | All policy documents with sections |
| GET | `/api/policies/{policy_id}` | Single policy detail |
| GET | `/api/payroll-ledgers` | Leave assignments AND salary assignments (mixed records distinguished by `record_type`) |
| GET | `/api/recruitment` | Recruitment openings: candidates, offer register, cost ledger, notice packets |
| GET | `/api/documents` | Document folders: files, required_files, required_tags, tags, ready flag |
| GET | `/api/messages` | Formal notices: quality, defects, recipient, channel |
| GET | `/api/notifications` | System notifications |
| GET | `/api/audit` | All audit events with actor, event type, case_id, employee_id |
| GET | `/api/audit/{audit_id}` | Single audit event detail |
| GET | `/api/attachments/{attachment_id}` | Attachment content |
| POST | `/api/cases/{case_id}/comments` | Add a comment to a case |

**Key data shape notes:**

- The `/api/payroll-ledgers` endpoint returns both leave assignments (`record_type: "Leave assignment"`) and salary assignments (`record_type: "Salary assignment"`). Filter by `record_type` and `employee_id` to isolate the relevant records.
- Employee profiles in `/api/employees` contain `leave_balance_days` and `policy_name` fields that may be stale. Always cross-reference with the latest approved/submitted assignment from the payroll ledgers.
- Document folders in `/api/documents` have a `ready` boolean, but this flag may not reflect all required evidence. Always compare `files` against `required_files` and `tags` against `required_tags` yourself.
- Messages in `/api/messages` contain `quality`, `defects[]`, and `status` fields. Draft messages with defects are not valid formal notices.

## Core Business Rules

These rules apply across all task types. The solver must follow them consistently.

### Source Precedence Rule

The latest **approved** or **submitted** record controls. Draft and superseded records are excluded for all decision-making purposes. This applies to:
- Leave assignments: an approved leave assignment overrides a stale employee profile summary
- Salary/payroll assignments: submitted controls, draft is excluded
- The policy document `LEAVE-SRC-001` Section 2.1 codifies this: "The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict."

**How to apply:** When comparing an employee profile against leave assignment records, prefer the approved assignment with the most recent `updated_at` in the current period. If the profile shows a different policy or balance, mark the profile as stale.

### Draft Exclusion Rule

Any record with `status: "Draft"` must be ignored for current-state decisions. This applies to:
- Leave assignment drafts (record_type: "Leave assignment", status: "Draft")
- Salary assignment drafts (record_type: "Salary assignment", status: "Draft")
- Payroll precheck drafts

Drafts appear in lists and may have higher day counts or salaries, but they represent planning data, not committed records. Always exclude them from the effective answer and include their IDs in any `excluded_*_ids` field.

### Superseded Exclusion Rule

Records with `status: "Superseded"` are also excluded. A superseded record has been replaced by a newer approved or submitted record. Include superseded IDs in exclusion lists alongside drafts.

### Folder Readiness Rule

A document folder is ready only when **all** of these are true:
1. Every entry in `required_files` appears in `files`
2. Every entry in `required_tags` appears in `tags`

The `ready` boolean field on the folder may be precomputed but is not authoritative -- verify manually. If any required file or tag is missing, the folder is not ready and this constitutes a closeout blocker.

### Notice Quality Rule

A formal notice must be inspected for defects. The allowed defect types are:
- `missing_ack_deadline` -- acknowledgement deadline not specified
- `missing_appeal_instructions` -- appeal process not described
- `missing_waitlist_status` -- waitlist status omitted (recruitment-specific)
- `missing_correct_policy` -- references wrong/stale policy instead of approved assignment

A notice with any defect has `quality: "defective"` and blocks closeout. The policy `HR-POL-014` Section 7.1 requires all of these elements in exception formal notices.

### Payroll Handoff Gate Rule

Recruiting payroll handoff is created only after a selected candidate has an **accepted offer**. The handoff must be a submitted assignment; draft prechecks do not satisfy the assignment gate. This is codified in `PAY-SRC-001` Section 4.2.

### Audit Event Scoping

When an audit event covers a specific scope (leave, payroll, documents, notices), include only audit events relevant to that scope in the decision. Exclude adjacent audit events that cover different domains. For example:
- A leave source precedence review uses leave-scoped audit events and excludes document/notice audit events
- A payroll readiness review uses payroll-scoped audit events

Audit events that reference a different case_id or employee_id than the subject are not authoritative for the current decision.

## Task Type Patterns

The system supports several recurring task types. Each follows a consistent flow.

### Pattern A: Employee Onboarding Closeout

**Indicators:** The prompt names an employee (EMP-xxx), asks to verify leave and payroll setup, includes fields like `effective_leave_policy`, `annual_days`, `assignment_id`, `payroll_assignment_id`, `base_salary`, `closeout_action`.

**Flow:**
1. Fetch `/api/employees` and locate the employee by ID
2. Fetch `/api/payroll-ledgers` and filter for this employee
3. Separate leave assignments (record_type: "Leave assignment") from salary assignments (record_type: "Salary assignment")
4. Identify the approved/submitted leave assignment with the most recent `updated_at` in the current period -- this is authoritative
5. Identify the submitted salary assignment -- this controls payroll
6. Collect all draft and superseded records as exclusions
7. Fetch relevant policies from `/api/policies` for context
8. Determine `closeout_action`: if records are clean (approved leave + submitted payroll, no missing evidence), use `approve_onboarding_close`; if defective, use the appropriate blocker action

### Pattern B: Remote-Work Policy Case Review

**Indicators:** The prompt names a case (CASE-RW-xxx or CASE-xxx), mentions remote-work policy, folder readiness, formal notice, includes fields like `folder_ready`, `missing_files`, `notice_quality`, `notice_defects`, `approval_authority`.

**Flow:**
1. Fetch `/api/cases/{case_id}` for case detail including approvals and audit events
2. Fetch `/api/documents` and locate the folder associated with the case
3. Compare `files` against `required_files` and `tags` against `required_tags`
4. Fetch `/api/messages` and locate the formal notice for the case
5. Check notice `quality` and `defects`
6. Fetch `/api/audit` and locate audit events for this case
7. Determine closeout blockers from folder and notice findings
8. Set `evidence_source_order` to `approval_history_folder_notice_audit` when using all four sources

### Pattern C: Recruitment Reconciliation

**Indicators:** The prompt names an opening (REQ-xxx), mentions recruitment, candidates, offers, notices, includes fields like `selected_candidate`, `waitlisted_candidates`, `rejected_candidates`, `offer_id`, `recruitment_cost_total`, `notice_followup_required`.

**Flow:**
1. Fetch `/api/recruitment` and locate the opening by ID
2. From `candidates[]`, classify each by `committee_decision`: Selected, Waitlisted, Rejected
3. From `offer_register[]`, determine offer status for the selected candidate
4. Sum all amounts in `cost_ledger[]` for `recruitment_cost_total`
5. From `notice_packets[]`, determine which candidates need follow-up notices
6. For payroll handoff: only the selected candidate with accepted offer triggers `create_payroll_precheck`; waitlisted/rejected candidates never trigger payroll handoff
7. Waitlisted and rejected candidates with unsent notices require notice follow-up

### Pattern D: Leave Source Precedence

**Indicators:** The prompt names an employee, asks about leave source precedence, profile vs assignment, includes fields like `precedence_source`, `profile_policy_ignored`, `audit_result`.

**Flow:**
1. Fetch `/api/employees` and note the employee's profile policy and leave balance
2. Fetch `/api/payroll-ledgers` and filter leave assignments for this employee
3. Identify the approved leave assignment -- it controls if it exists and is more recent
4. Compare profile policy vs assignment policy; if they differ, the profile is stale
5. Fetch `/api/audit` for leave-scoped audit events confirming the assignment controls
6. Exclude document/notice audit events from the leave-scope decision
7. If profile is stale, set `audit_result` to `profile_summary_stale` and `next_action` to `update_employee_summary`

### Pattern E: Payroll Assignment and Accrual Readiness

**Indicators:** The prompt names an employee, asks about payroll assignment, accrual readiness, includes fields like `salary_assignment_id`, `accrual_ready`, `accrual_batch_id`, `effective_date`.

**Flow:**
1. Fetch `/api/payroll-ledgers` and filter salary assignments for this employee
2. Select the submitted assignment; exclude all draft assignments
3. Check the `accrual_batch_id` field on the submitted assignment
4. If a submitted assignment exists with an accrual batch, accrual is ready
5. Fetch `/api/audit` for payroll audit events confirming readiness
6. Set `control_result` to `ready_with_monitoring` when records are clean

## Answer Format Rules

Every task provides an answer template JSON schema in `input/payloads/answer_template.json`. Follow these rules:

1. **Match the template exactly.** Every field from the template must appear in the answer. Do not add extra fields.
2. **Use only allowed enum values.** Each enum field lists its `allowed_values`. The answer must use exactly one of those strings. Do not invent values or use free-text.
3. **No markdown, no explanatory text.** The final output must be raw JSON only, matching the template structure. Do not wrap in code fences.
4. **Array fields contain IDs only.** List fields like `excluded_leave_ids`, `waitlisted_candidates`, `notice_followup_required` contain identifiers from the data, not descriptions or names.
5. **Numeric fields are computed from data.** `annual_days` comes from the authoritative assignment's `approved_leave_days` (or `worksheet_leave_days`). `base_salary` comes from the salary assignment. `recruitment_cost_total` is the sum of all cost ledger amounts.

## Execution Strategy

When solving a task on this system:

1. **Start with `/api/summary`** to understand the dataset scope and confirm the environment is reachable.
2. **Identify the task pattern** from the prompt: which employee/case/opening is named, which template fields are present.
3. **Query the relevant endpoints in parallel** where possible. The data is small enough to fetch full collections and filter client-side.
4. **Apply the core business rules** consistently: source precedence, draft exclusion, folder readiness, notice quality.
5. **Cross-reference across endpoints.** A leave assignment in the ledger should be confirmed by audit events. A folder's readiness should be checked against both the documents endpoint and case detail.
6. **Build the answer from the data, not assumptions.** Every field value must trace back to a specific API response. If a field can't be determined from available data, it's better to flag a blocker than to guess.

## Reference

See [references/api-details.md](references/api-details.md) for field-level descriptions of each API response shape and common query patterns.
