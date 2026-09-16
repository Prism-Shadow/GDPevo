---
name: peopleops-console
description: Solve PeopleOps Console verification tasks across onboarding, leave, payroll, policy cases, recruitment, and cross-module lifecycle control. Use when a task involves the PeopleOps API, employee records, case review, leave/payroll assignment precedence, notice quality inspection, folder readiness checks, recruitment reconciliation, or audit-event scoping.
---

# PeopleOps Console Solver

Open the solver application at `<TASK_ENV_BASE_URL>` and log in with:

- email: `ops.lead@peopleops.local`
- password: `PeopleOps#2026`

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/employees` | Employee records: `employee_id`, `name`, `department`, `designation`, `leave_balance_days`, `status`, `hire_date`, `salary_band`, `remote_profile` |
| `GET /api/cases` | All cases indexed by `case_id`, `case_type`, `status`, `employee_id`, `policy_refs` |
| `GET /api/cases/{case_id}` | Single case with `approvals`, `attachments`, `audit_events`, `comments`, `policy_refs` |
| `GET /api/policies` | Policy documents: `policy_id`, `title`, `summary`, `sections` with `heading`/`body` |
| `GET /api/payroll-ledgers` | Leave and salary assignments. `record_type` distinguishes: `"Leave assignment"` (fields: `policy_name`, `approved_leave_days`, `worksheet_leave_days`, `ledger_id`, `status`) vs `"Salary assignment"` (fields: `base_salary`, `accrual_batch_id`, `ledger_id`, `status`, `period`). Statuses: `Approved`, `Superseded`, `Draft`, `Submitted`. |
| `GET /api/recruitment` | Recruitment openings: `opening_id`, `candidates` (with `committee_decision`, `notice_status`, `pipeline_stage`), `cost_ledger`, `offer_register`, `notice_packets`, `payroll_precheck_records` |
| `GET /api/documents` | Document folders: `document_id`, `ready`, `files`, `required_files`, `required_tags`, `tags` |
| `GET /api/messages` | Formal notices and messages: `message_id`, `case_id`, `subject`, `body`, `quality` (`valid`/`defective`), `defects` (list), `channel`, `status` |
| `GET /api/notifications` | Same schema as `/api/messages` |
| `GET /api/audit` | All audit events: `audit_id`, `case_id`, `employee_id`, `event`, `detail`, `actor`, `timestamp` |
| `GET /api/audit/{audit_id}` | Single audit event detail |
| `GET /api/attachments/{attachment_id}` | Attachment detail (checklists, summaries, etc.) |
| `GET /api/summary` | High-level counts, departments, case-status breakdown |
| `GET /api/manifest` | File inventory and business-module list |

## Business Rules

### 1. Leave Source Precedence (LEAVE-SRC-001 2.1)

The latest **approved** (or submitted) leave assignment for the period controls. Draft, voided, superseded, and obsolete records are **excluded** even when the employee profile summary conflicts. An **approved leave assignment overrides a stale employee profile summary**.

To determine the effective leave policy for an employee:
1. Query `/api/payroll-ledgers`, filter by `employee_id` and `record_type = "Leave assignment"`.
2. Sort by status priority: `Approved` > `Superseded` > `Draft`.
3. Select the highest-priority non-Draft record. Its `policy_name` is the effective policy, `approved_leave_days` is the balance.
4. The `ledger_id` is the `assignment_id`. All Draft records and superseded records go into `excluded_leave_ids`.

### 2. Payroll Assignment Source (PAY-SRC-001 3.4)

Use the current **submitted** salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks. Superseded assignments are historical and excluded.

To determine payroll assignment:
1. Query `/api/payroll-ledgers`, filter by `employee_id` and `record_type = "Salary assignment"`.
2. Sort by status priority: `Submitted` > `Superseded` > `Draft`.
3. Select the highest-priority non-Draft, non-Superseded record. Its `ledger_id` is the `payroll_assignment_id`, `base_salary` is the salary, `period` is the effective period.
4. Exclude all Draft records. If an `accrual_batch_id` field is present, use it for accrual readiness checks.

### 3. Recruiting Handoff Gate (PAY-SRC-001 4.2)

A payroll handoff is created only after a **selected** candidate has an **accepted** offer. The handoff must be **submitted**; draft prechecks do not satisfy the assignment gate. Waitlisted and rejected candidates cannot receive payroll handoff.

### 4. Lifecycle Folder Checklist (POL-DOCS-2026 5.1)

A folder is not ready unless **all** required files **and** all required tags shown in the folder checklist are present. Compare `files` against `required_files` and `tags` against `required_tags`. Any missing required file or tag is a blocker.

### 5. Remote Work Policy (HR-POL-014 7.1)

International remote-work exceptions require executive approval, time limits, tax equalization, VPN-only access, quarterly compliance review, **appeal instructions**, and **acknowledgement deadline** in the formal notice. A notice missing appeal instructions or acknowledgement deadline is defective.

## How to Solve a Task

### Step 1: Read the answer template

Every task comes with an `answer_template.json` in `input/payloads/`. It defines every field, its type, and its allowed enum values. **Always use the exact enum labels from the template**; never substitute free-text explanations.

### Step 2: Identify the task type from the prompt

The prompt names the records to verify (employee ID, case ID, opening ID). Use that to route the evidence collection.

### Step 3: Collect evidence

Query all relevant endpoints for the given `employee_id`, `case_id`, or `opening_id`:

- **Onboarding closeout** (employee-level): employees, payroll-ledgers, policies, audit events.
- **Policy case folder/notice review** (case-level): cases/{case_id} (for approvals, attachments, comments), documents, messages, audit events.
- **Recruitment reconciliation** (opening-level): recruitment (filter by opening_id), messages, cases, policies (PAY-SRC-001), audit events.
- **Leave source precedence** (employee-level): payroll-ledgers (leave assignments), employees, audit events, policies (LEAVE-SRC-001). Exclude document/notice audit events from the leave-scope decision.
- **Payroll assignment readiness** (employee-level): payroll-ledgers (salary assignments), audit events, policies (PAY-SRC-001).

### Step 4: Apply business rules deterministically

| Rule | How to apply |
|------|--------------|
| Leave source precedence | Approved assignment > employee profile summary. Exclude Drafts. |
| Payroll source | Submitted assignment only. Exclude Drafts. |
| Folder readiness | `files` must contain all `required_files`; `tags` must contain all `required_tags`. |
| Notice quality | Check `quality` field in messages; if `defective`, list the `defects` array. |
| Audit event scoping | For leave-only scope, include leave-related audit events, exclude document/notice audit events. For payroll-only scope, include payroll audit events, exclude document/notice events. For document/notice scope, include only those. |
| Recruitment outcomes | `committee_decision` determines: `Selected` -> selected candidate, `Waitlisted` -> waitlisted, `Rejected` -> rejected. |
| Recruitment costs | Sum every `amount` in `cost_ledger`. |
| Recruitment follow-up | Check `notice_packets` for unsent or defective notices per candidate. Waitlisted candidates need waitlist notices; rejected candidates need rejection notices. |
| Payroll handoff | Only for selected candidate with accepted offer. Draft prechecks are excluded; submitted assignment required. |

### Step 5: Fill the answer template

For every field in the template:
- Use exact enum values from `allowed_values`.
- Use string IDs from the data (not invented).
- Use integers for numeric fields.
- Use booleans for boolean fields.
- Empty lists when no items exist; empty strings only when allowed by the template.

### Step 6: Return JSON only

Return a single JSON object matching the template. Do not include markdown, explanatory text, or code fences.

## Cross-Cutting Rules

**Always exclude draft records.** Draft leave assignments, draft salary assignments, and draft payroll prechecks are never authoritative. The `exclude_draft_assignment` rule applies universally unless the template explicitly allows drafts.

**Audit events have scope.** When an audit scope is `leave_source_precedence_only`, include only leave-related audit events and exclude document/notice audit events. When it is `payroll_assignment_readiness`, include only payroll audit events. When it is `document_notice_findings_only`, include only those.

**Evidence source order matters.** For case review, evidence typically flows: approvals -> folder/attachments -> notice/messages -> audit events. Use the highest-fidelity source available.

**Normalized labels only.** Every field that maps to an enum must use the exact string from the answer template's `allowed_values`. Do not paraphrase, do not use free-text.

**Answer template drives output.** The template defines every required field and its type. Fill all fields. Do not add extra fields not in the template.

## Edge Cases

- **Multiple leave assignments for same employee**: Select Approved first, then Superseded; exclude all Drafts and any superseded records.
- **No recruitment notice packets found**: Notice follow-up lists may be empty.
- **Profile summary conflicts with approved assignment**: The approved assignment always wins per LEAVE-SRC-001.
- **Case has no approval history**: Use audit events and attachments as primary evidence.
- **A case has both leave and payroll audit events**: Scope to only the relevant events for the task at hand; exclude the others.
- **Accrual batch ID on a salary assignment**: If present and the assignment is Submitted, accrual is ready.
