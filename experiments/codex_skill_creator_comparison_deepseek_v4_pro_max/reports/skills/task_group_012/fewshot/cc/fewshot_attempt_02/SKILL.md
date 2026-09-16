---
name: peopleops-console
description: Use when the task involves the PeopleOps Console, Northwind People Lifecycle Portal, HRMS verification, employee lifecycle reconciliation, onboarding closeout, leave source precedence, payroll assignment auditing, recruitment reconciliation, policy case review, or any HR operations workflow that requires pulling evidence from REST API endpoints and applying business policies to reach a structured decision. This skill is essential whenever you see TASK_ENV_BASE_URL, ops.lead@peopleops.local, PeopleOps#2026, or JSON answer templates with enum-driven business labels. Do not try to solve these tasks by reasoning alone; the API is the single source of truth.
---

# PeopleOps Console Solver

This skill covers the Northwind People Lifecycle Portal (HRMS) -- a REST API that
powers employee lifecycle verification, onboarding closeout, leave and payroll
auditing, recruitment reconciliation, and policy case review.

## Core principle

**The API is the single source of truth.** Every task answer must be built from
evidence returned by the API endpoints, not from assumptions or the task prompt
alone. The API holds the actual employee profiles, leave assignments, salary
records, case detail, approval history, documents, messages, audit events,
policies, and recruitment data.

## Environment setup

Every task provides a base URL (look for `<TASK_ENV_BASE_URL>` or an explicit
URL). The credentials are always:

```
ops.lead@peopleops.local / PeopleOps#2026
```

These are stated in the prompt. The API requires no authentication headers;
every endpoint is open once you know the URL.

## API discovery and navigation

Start with the summary endpoint to understand what data is available:

```bash
curl -s {BASE_URL}/api/manifest    # list of modules and file counts
curl -s {BASE_URL}/api/summary     # counts by status, departments
```

Then pull the collection endpoints for the modules relevant to the task.
These return arrays, not paginated:

| Endpoint | What it returns |
|---|---|
| `/api/employees` | All employee profiles (status, department, leave balance, salary band, etc.) |
| `/api/cases` | All cases (type, status, priority, owner, policy refs, summary) |
| `/api/cases/{case_id}` | Single case with approval history, attachments, audit events, comments |
| `/api/policies` | All policy documents with sections |
| `/api/policies/{policy_id}` | Single policy with full section text |
| `/api/payroll-ledgers` | All leave assignments AND salary assignments (mixed, identified by `record_type`) |
| `/api/recruitment` | Recruitment openings with candidates, cost ledger, notice packets, offer register, payroll precheck records |
| `/api/documents` | Document folders with files, required files, required tags, actual tags |
| `/api/messages` | Messages/notices with defects, quality, status |
| `/api/notifications` | Same structure as messages (the two endpoints return identical data) |
| `/api/audit` | All audit events (actor, event, detail, case, employee, timestamp) |
| `/api/audit/{audit_id}` | Single audit event detail |

You can also POST case comments:
```bash
curl -s -X POST {BASE_URL}/api/cases/{case_id}/comments \
  -H "Content-Type: application/json" \
  -d '{"body":"comment text"}' 
```

**Important**: The `notifications` and `messages` endpoints return the same
data in this environment. If you pull `/api/messages`, you already have
the notification set. Do not double-pull unless the task specifically
distinguishes them.

## How to approach any task

Follow this ordered workflow:

### 1. Read the answer template first

Every task provides an `answer_template.json` (or embeds it in the prompt). Read it
carefully before pulling any API data. The template defines:

- The exact field names you must return
- Enum sets for every controlled-vocabulary field
- Which fields are strings, integers, booleans, lists, or numbers

**You must use only the allowed enum values.** If the enum says `"submitted"`
and not `"Submitted"` or `"SUBMITTED"`, use `"submitted"` exactly. The answer
template is your schema; never free-text a value that has an enum option.

### 2. Identify the primary entity and pull its data

The prompt always centers on an employee (EMP-xxx), case (CASE-xxx or REQ-xxx),
or recruitment opening (REQ-xxx). Pull that entity's data first.

For an employee task, pull:
- `/api/employees` and filter to the employee_id
- `/api/payroll-ledgers` and grep for the employee_id

For a case task, pull:
- `/api/cases/{case_id}` for the case detail, approvals, attachments, audit events
- `/api/cases` for the summary to confirm policy refs

For a recruitment task, pull:
- `/api/recruitment` and find the opening by `opening_id`

### 3. Pull supporting evidence

Based on the task, pull the additional modules it references:

- **Leave questions** -> `/api/payroll-ledgers` (filter to leave assignments for the employee), `/api/policies/LEAVE-SRC-001`
- **Payroll questions** -> `/api/payroll-ledgers` (filter to salary assignments), `/api/policies/PAY-SRC-001`
- **Document/folder questions** -> `/api/documents` (match by document_id or employee), `/api/policies/POL-DOCS-2026`
- **Notice/message questions** -> `/api/messages` (match by case_id or recipient)
- **Audit questions** -> `/api/audit` (match by case_id, employee_id, or event type)
- **Recruitment questions** -> `/api/recruitment` (the full opening), `/api/policies/PAY-SRC-001` (for payroll handoff rules)

### 4. Read the relevant policies

Business rules live in the policies. The key policies are:

- **LEAVE-SRC-001**: "The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict."
- **PAY-SRC-001**: "Use the current submitted salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks." Section 4.2: "Recruiting payroll handoff is created only after a selected candidate has an accepted offer. The handoff must be submitted; draft prechecks do not satisfy the assignment gate."
- **HR-POL-014**: Remote work rules, exception requirements (executive approval, tax equalization, VPN-only, quarterly compliance, appeal instructions, acknowledgement deadline)
- **POL-DOCS-2026**: "A folder is not ready unless all required files and required tags shown in the folder checklist are present."

Always read the policy the case references (`policy_refs`). Policies contain
the ground rules for deciding what counts and what doesn't.

### 5. Apply record-exclusion rules

This is the most common mistake. Understand these rules:

- **Leave assignments**: Only Approved or Submitted status controls. Draft and Superseded records are excluded. An Approved assignment takes precedence over a Superseded one for the same employee/period, and both override the employee profile summary.
- **Salary assignments**: Only Submitted status controls. Draft salary assignments are excluded from payroll and accrual readiness.
- **Draft notices**: A draft notice with defects still counts as defective. Quality is assessed from the defects field regardless of status.
- **Draft/superseded ledger rows**: Ignore them for authoritative decisions but include them in excluded_*_ids lists.

### 6. Cross-check with audit events

Audit events provide authoritative determinations. When an audit event says
"profile_summary_stale" or "notice.defect" or "payroll.ready", that finding is
authoritative. Use the audit detail to confirm your reading of the raw data.

For example, if an audit event says "Approved assignment LA-EMP-APP-01 controls
leave policy" for a given employee, then that employee's profile summary data
is stale and the approved assignment should be used instead.

### 7. Build the answer JSON

Compile your findings into the JSON structure from step 1. Key rules:

- Enum values must match the template exactly (case-sensitive)
- List fields must contain IDs only (employee IDs, ledger IDs, audit event IDs, candidate IDs)
- Boolean fields must be `true` or `false` (JSON booleans, not strings)
- Integer fields must be whole numbers
- The `recruitment_cost_total` is the sum of all `amount` values in the `cost_ledger` for that opening

### 8. Sanity-check before returning

Before returning the final JSON, verify:

- Every field from the template is present
- Every enum value matches an allowed value exactly
- Supporting audit events used for leave scope do not include document/notice audit events (and vice versa: exclude document/notice events from leave-precedence decisions, and exclude leave/payroll events from document/notice decisions)
- Excluded IDs are IDs of records you explicitly decided to exclude, not speculation
- The final control result is consistent with the rest of the answer (e.g., you can't say `approve_closeout` if there are blockers listed)

## Common task patterns

### Onboarding closeout (employee-focused)

Pull employee profile, leave ledger, salary ledger. Filter to the employee.
Identify the approved/submitted leave assignment (exclude drafts and superseded).
Identify the submitted salary assignment (exclude drafts). Read applicable policies.
The closeout is approvable when records are clean (no draft-only records, submitted
records exist for both leave and payroll).

### Policy case review (case-focused)

Pull the case detail. Read approval history for final decision and approver.
Pull the document folder and check required files and tags against actual files
and tags. Pull messages for the case and check defects. Pull the audit events
for the case. Determine folder readiness, notice quality, and next action based
on evidence.

### Leave source precedence (employee-focused)

Pull employee profile summary. Pull leave ledger. Identify all leave assignments
for the employee. The approved/submitted assignment controls; the profile summary
is authoritative only when no approved/submitted assignment exists. Include
supporting audit events that confirm leave scope. Exclude document/notice audit
events from the leave decision.

### Payroll assignment readiness (employee-focused)

Pull salary ledger. Identify submitted assignment (exclude drafts). Check the
accrual batch. Verify readiness via audit events. The control result is
`ready_with_monitoring` when a submitted assignment exists and audit confirms it.

### Recruitment reconciliation (opening-focused)

Pull the recruitment opening. Examine candidate list with committee decisions.
Check offer register for accepted offers. Sum cost ledger. Check notice packets
for unsent notices to waitlisted/rejected candidates. Apply the payroll handoff
gate: only after an accepted offer. Exclude draft payroll precheck records.

## Evidence-source labels

When the template asks for source or gate fields, choose based on where the
evidence came from:

- `leave_assignment_history` -- decided from payroll-ledgers leave assignment rows
- `employee_profile_summary` -- decided from /api/employees profile data
- `case_summary_only` -- decided from /api/cases summary alone
- `approved_assignment_current_period` -- leave answer came from approved assignment
- `profile_summary_current_period` -- leave answer came from profile summary
- `approved_assignment_over_profile` -- approved assignment overrides stale profile
- `approval_history_folder_notice_audit` -- evidence came from all four sources
- `folder_notice_audit` -- evidence from folder, notice, and audit
- `audit_only` -- evidence from audit events alone
- `interview_feedback_and_offer` -- candidate status from candidate records and offer register
- `committee_decision_with_offer_confirmation` -- outcome confirmed by committee + offer
- `recruitment_cost_ledger` -- cost totals from cost_ledger
- `notice_packet_inspection` -- notice quality from notice_packets data
- `message_notice_inspection` -- notice quality from /api/messages data
- `document_notice_findings_only` -- audit scope limited to document + notice
- `leave_source_precedence_only` -- audit scope limited to leave precedence
- `payroll_assignment_readiness` -- audit scope limited to payroll assignment

## Boundaries on judgment

- Do not invent IDs, names, or values not present in the API response.
- Do not treat the employee profile leave_balance_days as authoritative when a submitted/approved leave assignment exists for the same period.
- "Exclude" means list the specific IDs of records you determined should not be used. Not all draft/superseded records in the system, only those relevant to the task employee.
- The `final_control_result` must be consistent: if there are missing files or defective notices, the result cannot be `approve_closeout`.
- When a task asks for supporting audit event IDs and excluded audit event IDs, inspect each audit event's type: include events matching the scope, exclude events from unrelated scopes.
