---
name: peopleops-console
description: Solve PeopleOps Console tasks that require reading employee, payroll, leave, policy, recruitment, audit, document, case, and message data from a REST API, applying business precedence rules to select authoritative records and exclude draft/superseded/stale sources, then returning structured JSON matching a provided answer template. Use this skill whenever the user mentions a PeopleOps Console, employee verification, onboarding closeout, leave or payroll reconciliation, recruitment reconciliation, policy case review, source precedence, or needs to navigate a task-environment REST API with HR business logic.
---

# PeopleOps Console Solver

Solve PeopleOps Console verification and reconciliation tasks by gathering structured data from the task environment REST API, applying the domain's record-precedence rules, and producing a JSON answer that conforms to the supplied answer template.

## How to approach a PeopleOps task

Every PeopleOps task follows the same pattern. Treat each step as a gather-then-decide phase; don't jump to conclusions before you have all the evidence.

### 1. Connect and orient

The task will give you:
- A base URL for the task environment (shown as `<TASK_ENV_BASE_URL>`)
- Login credentials (always `ops.lead@peopleops.local` / `PeopleOps#2026` in these tasks)
- A business goal describing what to verify and which employee or case to inspect

Start by reading `/api/summary` to confirm the environment is reachable and understand overall counts. Then pull the broad datasets you'll need (employees, cases, payroll ledgers, policies, audit events, documents, messages, recruitment) with the GET endpoints listed in [references/api-endpoints.md](references/api-endpoints.md). Don't read just one record at a time when the full list is small; pull the full collection and filter client-side.

### 2. Gather targeted detail

Once you know which employee ID, case ID, or requisition ID the task names, drill into the detail endpoints:

- Employee profile: `/api/employees` (filter by `employee_id`)
- Case detail with approvals, attachments, and embedded audit events: `/api/cases/{case_id}`
- Policy detail: `/api/policies/{policy_id}`
- Single audit event: `/api/audit/{audit_id}`
- Recruitment packet: `/api/recruitment` (filter by `opening_id`)

The ledger endpoint (`/api/payroll-ledgers`) returns leave assignments, salary assignments, payroll worksheets, HRMS leave ledgers, and People Ops adjustments in one flat list. Filter by `employee_id` and `record_type` to isolate what you need.

### 3. Apply business precedence rules

This is the core of every PeopleOps task. Read [references/business-rules.md](references/business-rules.md) for the full rule set. The essential ones:

| Rule | How to apply |
|------|--------------|
| **Submitted > Draft** | A record with `status: "Submitted"` controls over one with `status: "Draft"`. Draft records must be excluded from authoritative answers. |
| **Approved > Superseded** | When multiple leave/payroll assignments exist for the same employee and period, the latest `status: "Approved"` or `"Submitted"` record controls. Exclude `"Superseded"` and `"Draft"` records. |
| **Approved assignment > Profile summary** | When an approved leave assignment from the ledger conflicts with the employee profile's `leave_balance_days` or implied policy, the approved assignment controls. Mark the profile as stale/ignored. |
| **Folder readiness** | A folder is ready only when all `required_files` and all `required_tags` are present in the document record. |
| **Notice quality** | A formal notice is valid only when its `defects` array is empty. Each defect maps to a specific label from the answer template. |
| **Recruitment handoff** | Payroll handoff is created only for the selected candidate with an accepted offer. Draft payroll prechecks do not satisfy the gate. |

### 4. Scope audit evidence correctly

Many tasks ask you to identify supporting audit events and exclude irrelevant ones. Read all audit events for the target employee or case. Include only events whose `event` field and `detail` field are directly about the scope described in the task (e.g., leave source precedence, document/notice findings, payroll readiness). Exclude events about unrelated scopes even if they share the same employee or case ID.

### 5. Map to the answer template

The task supplies an `answer_template.json` in `input/payloads/`. Every field in that template has a `type` constraint and, for enums, an `allowed_values` list. Your JSON answer must:

- Include every key from the template (no missing fields)
- Use exactly the normalized labels from the template's `allowed_values` for every enum field — never invent free-text alternatives
- Match the declared types exactly (string, number, integer, boolean, list[string])
- For list fields, return plain arrays of string IDs or enum labels, never objects

Before finalizing, reread each template key and confirm your answer value exists in the `allowed_values` list for that key. If a template key has no `allowed_values` (it's a plain string or number), derive the value from the authoritative data you gathered.

### 6. Validate and return

Cross-check your answer against the raw API data one more time. Specifically verify:
- Every excluded record ID appears in the raw data with a status that justifies exclusion (Draft, Superseded, or stale)
- Every selected record ID appears in the raw data with a status that justifies selection (Approved, Submitted, or the controlling source)
- Sums (like recruitment cost total) are correct arithmetic on the source ledger items
- Boolean fields (folder_ready, required_tag_present, accrual_ready, profile_policy_ignored) are grounded in explicit data, not assumptions

Return only the JSON object. No markdown fences, no explanatory text — unless the task explicitly asks for something else.
