# PeopleOps Lifecycle Inspector — GDPevo Skill

Inspect employee payroll, leave, recruiting, and case-closeout records in the Northwind People Lifecycle Portal and return structured JSON answers.

## 1. Environment Access

- **Base URL:** read from `GDPEVO_ENV_BASE_URL` or follow the `<TASK_ENV_BASE_URL>` placeholder in the task prompt.
- **App:** static SPA at `/` with REST APIs under `/api/*`. No login endpoint is exposed; use the APIs directly.
- **Scope:** read-only inspection. Do not post comments or mutate data.

## 2. API Endpoints & Query Patterns

All endpoints accept `?q=<text>` for free-text search (employee ID, name, case ID, etc.).

| Endpoint | Purpose | Key Fields |
|----------|---------|------------|
| `GET /api/employees` | Employee directory | `employee_id`, `name`, `hire_date`, `status`, `department`, `manager` |
| `GET /api/payroll-ledgers` | Salary & leave assignments | `ledger_id`, `record_type` (`Salary assignment` / `Leave assignment` / …), `status` (`Submitted`/`Draft`/`Approved`/`Superseded`), `period`, `base_salary`, `approved_leave_days`, `accrual_batch_id`, `updated_at` |
| `GET /api/cases` | Policy cases | `case_id`, `employee_id`, `status`, `priority`, `case_type`, `policy_refs` |
| `GET /api/cases/{case_id}` | Case detail (approvals, attachments, audit events, comments) | `approvals[].decision`, `attachments[].status`, `audit_events[].audit_id` |
| `GET /api/audit` | Audit log | `audit_id`, `employee_id`, `case_id`, `event`, `detail` |
| `GET /api/audit/{audit_id}` | Single audit event | same as above |
| `GET /api/documents` | Folder checklists | `document_id`, `ready`, `required_files[]`, `files[]`, `required_tags[]`, `tags[]` |
| `GET /api/messages` | Formal notices | `message_id`, `case_id`, `quality`, `defects[]`, `status` |
| `GET /api/recruitment` | Recruiting pipelines | `opening_id`, `candidates[]`, `offer_register[]`, `cost_ledger[]`, `notice_packets[]`, `payroll_precheck_records[]`, `status` |
| `GET /api/policies` | Policy documents | `policy_id`, `sections[].heading`, `sections[].body` |

**Always query by the specific employee ID / case ID / opening ID** to narrow results instead of scanning the full list.

## 3. Core Business Policies (derive answers from these)

- **PAY-SRC-001** (`Payroll Assignment Source`)
  - Use the **current submitted** salary assignment.
  - **Draft planning assignments do not affect** payroll readiness or accrual checks.
  - Recruiting payroll handoff is created only after a selected candidate has an accepted offer; the handoff itself must be **submitted**.
- **LEAVE-SRC-001** (`Leave Source Precedence`)
  - The **latest approved or submitted** leave assignment for the period controls.
  - **Draft, voided, and obsolete (superseded)** records are excluded even when profile summaries conflict.
- **POL-DOCS-2026** (`Lifecycle Folder Checklist`)
  - A folder is **not ready** unless *all* required files and required tags shown in the folder checklist are present.
- **HR-POL-014** (`Remote Work Policy`)
  - Formal notices for exceptions must contain appeal instructions and an acknowledgement deadline.

## 4. Task Taxonomy & Derivation Rules

### 4.1 Payroll Readiness (salary assignment + accrual)
1. Query `/api/payroll-ledgers?q={employee_id}` and filter `record_type == "Salary assignment"`.
2. **Select** the assignment whose `status == "Submitted"` and whose `period` matches the target month/year.
3. **Exclude** any `status == "Draft"` salary assignment for the same employee → record its `ledger_id` as `excluded_assignment_id`.
4. Read the `accrual_batch_id` field on the selected submitted record (may be absent).
5. Query `/api/audit?q={employee_id}` for payroll-related audit events (e.g., `event: "payroll.ready"`, `event: "payroll.draft_excluded"`).
6. Map the audit `detail` to `control_result`:
   - Phrases like *"ready_with_monitoring"* → `"ready_with_monitoring"`
   - Phrases like *"block close"* or folder/notice defects → `"hold_for_folder_and_notice_defects"`
   - All clear for final closeout → `"approve_closeout"`
7. Set `payroll_source_status: "submitted"`, `draft_exclusion_rule: "exclude_draft_assignment"`, `audit_scope: "payroll_assignment_readiness"`.
8. `effective_date` = first day of the assignment `period` (e.g., period `"2026-04"` → `"2026-04-01"`).

### 4.2 Leave Readiness (leave assignment + profile correction)
1. Query `/api/payroll-ledgers?q={employee_id}` and filter `record_type == "Leave assignment"`.
2. **Select** the `status == "Approved"` leave assignment (or the latest approved/submitted per LEAVE-SRC-001).
3. **Exclude** the draft or superseded leave assignment → record as `excluded_assignment_id`.
4. `leave_days` = `approved_leave_days` from the selected record.
5. Query `/api/audit?q={employee_id}` for leave-related events (e.g., `event: "leave.profile_mismatch"`, `event: "folder.tag_missing"`).
6. `profile_correction_needed` = `true` if audit detail contains *"profile_summary_stale"*, *"profile_mismatch"*, or similar.
7. `leave_source_status` = `"approved"` (or the actual status of the controlling record).
8. `draft_exclusion_rule` = `"exclude_draft_assignment"` (or `"exclude_superseded_only"` if only a superseded record is being excluded).
9. `audit_scope` = `"leave_source_precedence_only"`.

### 4.3 Recruiting Payroll Handoff
1. Query `/api/recruitment?q={opening_id}` (e.g., `REQ-DA-77`).
2. **Selected candidate:** `candidates[].committee_decision == "Selected"`.
3. **Accepted offer:** `offer_register[].candidate_id == selected_candidate_id && status == "accepted"`.
4. `cost_total` = sum of `amount` in `cost_ledger`.
5. `required_notice_actions` = concatenate `required_action` from every `notice_packets` entry whose `status` is not satisfied (e.g., `"not_sent"`, `"draft_reissue_required"`).
6. `payroll_precheck_records`: inspect for a submitted handoff record.
   - If absent or only `Draft`, `payroll_assignment_id` may be empty/null and `payroll_source_status` reflects the missing handoff.
7. `control_result`:
   - If any notice packet is unsent/defective or payroll precheck is missing/draft → `"hold_for_folder_and_notice_defects"`
   - If selected candidate has accepted offer, cost ledger is present, notices are complete, and payroll precheck is submitted → `"ready_with_monitoring"` or `"approve_closeout"` depending on the case type.

### 4.4 Lifecycle Closeout (cross-module)
1. Query `/api/cases/{case_id}` to load approvals, attachments, and embedded `audit_events`.
2. Verify **approvals**: all required steps show `"Approved"`.
3. Verify **folder** via `/api/documents?q={document_id}`:
   - `ready` must be `true`.
   - All `required_files` must be present in `files`.
   - All `required_tags` must be present in `tags`.
4. Verify **notice** via `/api/messages?q={case_id}`:
   - `quality` must not be `"defective"`.
   - `defects` array should be empty.
5. `control_result`:
   - Missing approvals, folder not ready, or notice defective → `"hold_for_folder_and_notice_defects"`
   - All checks pass and case status is final → `"approve_closeout"`
   - Submitted assignment ready but case still under monitoring → `"ready_with_monitoring"`

## 5. Answer Template Discipline

- The task provides `input/payloads/answer_template.json`. **Every key in the template must appear in the output JSON.**
- Use **exact enum strings** from the template; never paraphrase.
  - `control_result`: `["ready_with_monitoring", "hold_for_folder_and_notice_defects", "approve_closeout"]`
  - `payroll_source_status`: `["submitted", "draft", "superseded"]`
  - `leave_source_status`: `["approved", "submitted", "draft", "superseded"]`
  - `draft_exclusion_rule`: `["exclude_draft_assignment", "draft_allowed", "exclude_superseded_only"]`
  - `audit_scope`: `["payroll_assignment_readiness", "document_notice_findings_only", "leave_source_precedence_only"]`
- Use `null` or `""` for fields that are genuinely absent (no matching record, no audit event, no accrual batch), unless the task narrative explicitly implies a default.

## 6. Common Pitfalls

- **Do not trust the employee profile summary alone.** Per LEAVE-SRC-001, the approved/submitted assignment controls; profile summaries may be stale.
- **Do not include draft records** in readiness checks unless the task explicitly says "draft_allowed".
- **Payroll-ledgers mixes salary and leave records.** Always filter by `record_type` before selecting the controlling record.
- **Accrual batch IDs live on the submitted salary assignment record.** If the field is missing, there is no accrual batch.
- **Case detail endpoint (`/api/cases/{id}`) returns nested audit events.** Check there before falling back to the global `/api/audit` list.
- **Recruiting cost total is a simple sum** of the `cost_ledger` amounts for that opening.
- **Notice defects block closeout** even when approvals are present.

## 7. Execution Checklist

1. Read the task prompt to identify the employee / case / opening and the target period.
2. Read `input/payloads/answer_template.json` to know the exact output schema.
3. Query the relevant APIs (payroll-ledgers, cases, audit, documents, messages, recruitment, policies).
4. Apply the business rules from the policies to select/exclude records.
5. Derive enum values using the normalized labels from the template.
6. Write the final answer as JSON matching the template keys exactly.
