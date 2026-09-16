---
name: peopleops-console
description: "Navigate the PeopleOps Console REST API to complete HR operations workflows: onboarding closeout verification, leave-source precedence checks, payroll assignment and accrual readiness, policy-case folder and formal-notice review, and recruitment outcome reconciliation. Use when the task involves: (1) an employee lifecycle or onboarding closeout check, (2) leave policy or payroll assignment verification, (3) reviewing remote-work or policy-case folder readiness and formal notice quality, (4) reconciling a recruitment pipeline with candidate outcomes and costs, (5) cross-module audit inspection for PeopleOps, or when the prompt references the PeopleOps Console, employee IDs like EMP-\\d+, case IDs like CASE-\\w+, or recruitment openings like REQ-\\w+."
license: MIT
compatibility: designed for deepagents-code
---

# PeopleOps Console

## Quick Start

Every task in this domain follows the same pattern:

1. Read the prompt for the business task, the target identifiers (employee_id, case_id, opening_id), and credentials if provided.
2. Read the answer template (`answer_template.json`) to know the exact output schema.
3. Fetch the relevant API resources (see [api-catalog.md](references/api-catalog.md) for endpoint details).
4. Apply the business rules (see [business-rules.md](references/business-rules.md) for precedence, scoping, and classification rules).
5. Fill the answer template with values from `allowed_values` only — never invent enum values.
6. Return only the JSON object, no markdown or explanatory text.

## Core Workflow

### Step 1: Orient

Fetch `/api/manifest` and `/api/summary` to confirm the environment is
reachable. The manifest lists available modules; the summary shows department
and case counts for context.

### Step 2: Gather Data

Based on the task domain, fetch the relevant collections:

| Domain | Endpoints to fetch |
|--------|-------------------|
| Employee onboarding / leave + payroll | `/api/employees`, `/api/payroll-ledgers`, `/api/policies` |
| Policy case folder + notice review | `/api/cases`, `/api/cases/{case_id}`, `/api/documents`, `/api/messages`, `/api/policies` |
| Leave source precedence | `/api/employees`, `/api/payroll-ledgers`, `/api/cases/{case_id}`, `/api/audit`, `/api/policies` |
| Payroll assignment readiness | `/api/payroll-ledgers`, `/api/cases/{case_id}`, `/api/audit`, `/api/policies` |
| Recruitment reconciliation | `/api/recruitment`, `/api/cases/{case_id}`, `/api/messages`, `/api/audit` |

Fetch in parallel where the task spans multiple domains. Use filters on the
collection arrays (`employee_id`, `case_id`, `ledger_id`, `opening_id`) rather
than fetching individual items one at a time when possible.

For case detail, always use `/api/cases/{case_id}` — it embeds approvals,
attachments, and audit events that the list view omits.

### Step 3: Apply Business Rules

See [business-rules.md](references/business-rules.md) for the complete ruleset. The core principles:

- **Record precedence**: Approved > Submitted > Superseded (excluded) > Draft (excluded).
- **Leave**: Use the latest approved/submitted leave assignment from the ledger; ignore draft and superseded entries.
- **Payroll**: Use the submitted salary assignment; exclude drafts. Accrual readiness is indicated by an `accrual_batch_id` on the submitted record and a matching audit event.
- **Folder**: Compare `files`/`tags` against `required_files`/`required_tags` for the folder referenced in the case.
- **Notice**: Inspect message `quality` and `defects` fields.
- **Audit scoping**: Only include audit events matching the task's domain; exclude events from other domains.
- **Recruitment**: Classify candidates by `committee_decision`, sum the `cost_ledger`, and determine notice follow-up from `notice_packets`.

### Step 4: Fill the Answer Template

The `answer_template.json` in the task payload defines every field and every
allowed value. Match the computed values to the template:

- For enum fields, pick the closest matching `allowed_values` entry. If a field
  has multiple related enum fields (e.g., `leave_source` and
  `leave_precedence_source`), make sure they are consistent with each other.
- For list fields, include only the relevant IDs as strings.
- For integer/number fields, use the precise value from the data.
- For boolean fields, derive from record status/document readiness.

### Step 5: Validate and Return

Before returning, verify:

- Every required field from the template is present.
- All enum values are from the template's `allowed_values`, exactly as spelled.
- Numerical values match the source data (re-sum ledger totals if needed).
- No extra fields beyond the template schema.

Return the JSON object directly. Do not wrap in markdown fences unless the
prompt explicitly allows it, and prefer raw JSON when the prompt says "Return
only JSON."

## Common Task Patterns

### Onboarding Closeout (leave + payroll)

Target: an employee_id (e.g., EMP-104).

1. Fetch `/api/employees` and `/api/payroll-ledgers`.
2. For leave: filter ledger to Leave assignments for the employee, exclude Draft and Superseded, pick the latest Approved (or Submitted). Use its `policy_name`, `approved_leave_days`, and `ledger_id`.
3. For payroll: filter ledger to Salary assignments for the employee, exclude Draft, pick the Submitted entry. Use its `ledger_id` and `base_salary`.
4. Collect excluded ledger IDs (Draft, Superseded) for both leave and payroll.
5. Populate `leave_source`, `payroll_status`, `leave_precedence_source`, `payroll_source_status` from the data path actually used.
6. If records are clean (no draft-only reliance, no conflicts), set `closeout_action: "approve_onboarding_close"`, `approval_closeout_gate: "approval_sufficient_when_records_clean"`, `final_control_result: "approve_closeout"`.

### Case Folder + Notice Review

Target: a case_id (e.g., CASE-RW-221).

1. Fetch `/api/cases/{case_id}` for approvals, attachments, audit events.
2. Extract the document folder reference from attachments or from `/api/documents` matching the case.
3. Compare folder `files` and `tags` against `required_files` and `required_tags`.
4. Fetch `/api/messages` and filter by `case_id` for formal notice quality.
5. Check message `quality` and `defects`. Any non-empty defects → notice is defective.
6. Determine the approval decision from the case's `approvals` array (look for `step: "Final approval"`).
7. Set `folder_ready`, `missing_files`, `required_tag_present`, `notice_quality`, `notice_defects`.
8. If folder or notice has defects: `closeout_blockers` includes the relevant blockers, `next_action: "block_close_and_reissue_notice"`, `final_control_result: "hold_for_folder_and_notice_defects"`.

### Leave Source Precedence

Target: an employee_id (e.g., EMP-118).

1. Fetch `/api/employees` for the profile summary.
2. Fetch `/api/payroll-ledgers` and filter to Leave assignments for the employee.
3. Fetch `/api/cases` to find the case for this employee, then `/api/cases/{case_id}` for audit events.
4. Fetch `/api/audit` and filter to the employee's leave-scope events.
5. The approved assignment from the ledger controls when confirmed by audit. The profile summary is stale.
6. Set `precedence_source: "approved_assignment_over_profile"`, `profile_policy_ignored: true`, `audit_result: "profile_summary_stale"`, `next_action: "update_employee_summary"`.
7. Include only leave-scope audit events as supporting; exclude document/notice events.

### Payroll Assignment + Accrual Readiness

Target: an employee_id (e.g., EMP-122).

1. Fetch `/api/payroll-ledgers`, filter to Salary assignments for the employee.
2. Select the Submitted entry. Exclude Draft entries.
3. Check for an `accrual_batch_id` on the submitted salary assignment.
4. Fetch `/api/audit` and filter to payroll-scope events for the employee/case.
5. Confirm the audit event matches the submitted assignment and accrual batch.
6. Set `accrual_ready: true` when the submitted record has an accrual_batch_id and the audit confirms readiness.
7. Set `payroll_source_status: "submitted"`, `draft_exclusion_rule: "exclude_draft_assignment"`, `audit_scope: "payroll_assignment_readiness"`.

### Recruitment Reconciliation

Target: an opening_id (e.g., REQ-DA-77).

1. Fetch `/api/recruitment`, find the opening by `opening_id`.
2. Classify candidates from `committee_decision` into selected, waitlisted, rejected arrays (candidate IDs only).
3. Find the selected candidate's offer in `offer_register` for `offer_id` and `offer_base_salary`.
4. Sum all `amount` values in `cost_ledger` for `recruitment_cost_total`.
5. Check `notice_packets` for waitlisted/rejected candidates: if `status` is `"not_sent"`, add candidate to `notice_followup_required`.
6. If there's an accepted offer, set `onboarding_handoff: "create_payroll_precheck"`.
7. Set source fields: `candidate_status_source: "interview_feedback_and_offer"`, `cost_source: "recruitment_cost_ledger"`, `notice_quality_source: "notice_packet_inspection"`.
8. Set `selected_offer_status` from the offer register entry.

## Edge Cases

- **No authoritative record exists**: Fall back to the next-best source (profile summary, case summary). Document the fallback in the relevant source field.
- **Multiple records with same status**: Break ties by `updated_at` timestamp — latest wins.
- **Audit events cross-referencing multiple cases**: Check `case_id` on each event; only include events for the target case/employee.
- **Draft records with plausible values**: Always exclude. Draft means not authoritative regardless of content.
- **Defective notice but folder clean**: Still blocks closeout (`block_close_and_reissue_notice`).
- **Clean notice but folder missing files**: Still blocks closeout.
- **Accrual batch on submitted record but no matching audit**: Set `accrual_ready: false` unless the audit confirms it.
