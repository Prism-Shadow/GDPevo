---
name: peopleops-console
description: Solve PeopleOps Console business-verification tasks. Use this skill whenever the user mentions PeopleOps, HR operations, employee onboarding, leave verification, payroll verification, lifecycle closeout, case folder review, formal notice inspection, recruitment reconciliation, candidate reconciliation, audit-based verification, or a `<TASK_ENV_BASE_URL>` with ops.lead@peopleops.local credentials. Also use it when a task references Northwind People entities, PeopleOps answer templates, or normalized business labels. Follow this skill even if the user does not explicitly name the PeopleOps Console.
---

# PeopleOps Console Solver

Complete business-verification tasks against the PeopleOps Console REST API. The
console models employee lifecycle, leave assignments, salary assignments,
policy cases, recruitment pipelines, document folders, formal notice messages,
and audit events for a fictional organization (Northwind People).

## Overall workflow

Every task follows this skeleton:

1. Read the task prompt to understand which business workflow is being
   exercised and which employee or case is the subject.
2. Read the answer template (`input/payloads/answer_template.json`) to learn
   the required output schema and the set of allowed enum values for every
   controlled field.
3. Call the PeopleOps Console REST API endpoints — always read data through the
   API, never guess — to collect all relevant records. The base URL is always
   `<TASK_ENV_BASE_URL>` and credentials are always `ops.lead@peopleops.local` /
   `PeopleOps#2026`. No authentication header is needed; the endpoints are open.
4. Apply the source-precedence and record-exclusion rules described below.
5. Map every finding to the correct normalized label from the answer template.
6. Return a single JSON object matching the answer template exactly. Do not
   include markdown fences, commentary, or explanatory text outside the JSON.

## API discovery

The console is self-describing. Start every task by calling:

- `GET <TASK_ENV_BASE_URL>/api/manifest` — lists available business modules and
  file counts.
- `GET <TASK_ENV_BASE_URL>/api/summary` — lists departments, case status
  counts, and record counts.

Then use the endpoints documented in [references/api.md](references/api.md),
which is a complete catalogue of every endpoint and the fields returned.

**Important:** The console is read-only except for `POST
/api/cases/{case_id}/comments`. All data retrieval is through GET requests.

## Business objects and how they relate

See [references/domain.md](references/domain.md) for the full object catalogue.
The key relationships to understand when cross-referencing:

- **employees** anchor all lifecycle records. Every leave assignment, salary
  assignment, case, message, and audit event links back to an `employee_id`.
- **payroll-ledgers** contain both *leave assignments* (`record_type: "Leave
  assignment"`) and *salary assignments* (`record_type: "Salary assignment"`).
  They are the authoritative source for leave policy and base salary.
- **cases** carry approvals, attachments, comments, and policy references.
- **documents** describe the case folder: required files, required tags,
  present files, present tags, readiness.
- **messages** carry formal notices for cases. Their `quality` field is either
  `valid` or `defective`, and defects are enumerated in the `defects` array.
- **audit events** are QA findings linked to employees and cases. They provide
  authoritative evidence for folder, notice, leave, and payroll decisions.
- **policies** encode business rules (leave source precedence, payroll source,
  folder checklist). Their `sections[].body` fields contain the rule text.
- **recruitment** contains candidate lists, committee decisions, offer
  registers, cost ledgers, and notice packets for an opening.
- **notifications** mirror the message set and include the same defect/quality
  fields.

## Core business rules

### Source precedence hierarchy

When multiple records exist for the same entity, use this order:

1. **Approved or Submitted ledger record** (leave assignment or salary
   assignment) is authoritative.
2. **Employee profile summary** is a fallback; it may be stale and should be
   overridden when a more current ledger record exists.
3. **Case summary** is the weakest source — use it only when no ledger or
   profile data is available.

This hierarchy comes from policy LEAVE-SRC-001: the latest approved or
submitted leave assignment for the period controls. The same principle extends
to salary data per PAY-SRC-001.

### Draft and superseded record exclusion

- **Draft** records (`status: "Draft"`) must **always** be excluded from
  authoritative decisions. They are planning artifacts that do not affect
  current payroll, leave entitlement, or onboarding readiness.
- **Superseded** records (`status: "Superseded"`) must be excluded in favor of
  the newer approved or submitted record for the same period.
- **Submitted** and **Approved** records are the only valid sources.

Apply this rule uniformly: when you find both a submitted and a draft salary
assignment for the same employee, keep only the submitted one for the
authoritative answer and list the draft ID in the excluded-records field.

### Folder readiness

A case folder (from `/api/documents`) is **not ready** unless:

- All entries in `required_files` are present in `files`.
- All entries in `required_tags` are present in `tags`.

When `ready` is `false`, inspect the delta between `required_files`/`files`
and `required_tags`/`tags` to identify what is missing.

### Formal notice quality

Inspect the message or notification for the case. If the `quality` field is
`defective`, the `defects` array lists each specific defect. Possible defects
are:

- `missing_ack_deadline` — no acknowledgement deadline in the notice
- `missing_appeal_instructions` — no appeal instructions in the notice
- `missing_waitlist_status` — waitlist status omitted (recruitment notices)
- `missing_correct_policy` — notice references stale or incorrect policy

### Audit event scoping

Audit events carry an `event` field that determines their domain:

- `notice.defect` → document/notice scope
- `folder.tag_missing` → document/notice scope
- `folder.file_missing` → document/notice scope
- `case.close_blocked` → may span multiple scopes; read the detail text
- `leave.profile_mismatch` → leave source precedence scope
- `payroll.ready` → payroll assignment readiness scope
- `payroll.draft_excluded` → payroll assignment readiness scope
- `cross_module.escalation_package` → cross-cutting; review related events

When a task asks you to scope audit events, include only events whose `event`
field matches the scope being verified and exclude events belonging to other
scopes even if they reference the same employee or case.

### Recruitment workflow

For a recruitment opening (from `/api/recruitment`):

- The `candidates` array provides committee decisions (Selected / Waitlisted /
  Rejected).
- The `offer_register` contains accepted offers (status `accepted`) for
  selected candidates.
- The `cost_ledger` array must be summed (all `amount` values) to produce
  `recruitment_cost_total`.
- The `notice_packets` array shows which notices are unsent and their
  `required_action`.
- Payroll handoff is only created after a selected candidate has an accepted
  offer (policy PAY-SRC-001 section 4.2).

### Leave source precedence verification

When verifying which leave policy is authoritative for an employee:

1. Retrieve the employee profile from `/api/employees` and note the
   `leave_balance_days` and policy name shown there.
2. Retrieve leave assignments from `/api/payroll-ledgers` filtered by
   `employee_id` and `record_type: "Leave assignment"`.
3. Select the approved (or submitted) assignment with the most recent
   period/date — ignore draft and superseded.
4. Retrieve relevant audit events from `/api/audit`.
5. Cross-check: if the approved assignment policy differs from the profile
   policy, the approved assignment controls, the profile is stale, and the
   supporting audit event confirms the mismatch.

### Payroll assignment and accrual readiness

When verifying payroll assignment and accrual readiness:

1. Retrieve salary assignments from `/api/payroll-ledgers` filtered by
   `employee_id` and `record_type: "Salary assignment"`.
2. Select the submitted assignment — exclude draft assignments.
3. Check for an `accrual_batch_id` on the submitted assignment (indicates
   accrual readiness).
4. Retrieve audit events to confirm payroll readiness.

### Onboarding closeout

When verifying onboarding closeout for an employee:

1. Retrieve the employee from `/api/employees` to confirm the profile.
2. Retrieve leave assignments and salary assignments from
   `/api/payroll-ledgers`.
3. Select the approved leave assignment with the most recent `updated_at` —
   exclude draft and superseded records.
4. Select the submitted salary assignment — exclude draft records.
5. Cross-check with audit events for the employee.
6. If all records are clean (submitted salary, approved leave, no draft records
   in use), closeout is `approve_onboarding_close`.

## How to read answer templates

Every task provides an `input/payloads/answer_template.json`. This defines:

- Required field names and types
- For enum fields, the exact set of `allowed_values`

When filling in the answer, always use a value from `allowed_values` verbatim.
Do not use free-text descriptions or invented labels. The enum values are the
normalized business labels.

## Output checklist

Before returning the final answer, verify:

- Every field from the answer template is present.
- Every enum field uses a value from `allowed_values` in the template.
- Draft and superseded records are excluded from authoritative values.
- Excluded record IDs are listed in the exclusion fields.
- Supporting audit events are correctly scoped.
- Numeric fields (base salary, annual days, cost totals) are computed from
  actual API data, not estimated.
- The output is a single JSON object with no markdown wrappers.

Read [references/api.md](references/api.md) for the complete endpoint catalogue
and [references/rules.md](references/rules.md) for the full policy rule set and
normalized label reference.
