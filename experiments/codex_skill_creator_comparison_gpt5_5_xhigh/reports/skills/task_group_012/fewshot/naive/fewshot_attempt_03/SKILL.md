---
name: peopleops-reconcile
description: Solve PeopleOps Console reconciliation and control tasks that require strict JSON answers from a task-provided answer template. Use when asked to verify onboarding closeout, remote-work or lifecycle folder readiness, leave source precedence, payroll assignment/accrual readiness, recruitment outcome packets, notice defects, audit scope, or cross-module People Ops controls against the running task environment.
---

# PeopleOps Reconciliation

Use this skill to solve PeopleOps Console tasks by reading the current prompt, the task's answer template, and the live read-only business evidence. Produce only the JSON object requested by the template.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the output schema and the only source for normalized enum labels.
2. Use the configured task environment base URL from the prompt or environment access file. Prefer direct API reads over UI inspection when endpoints are available.
3. Pull a broad evidence snapshot before deciding:
   - `GET /api/manifest`
   - `GET /api/summary`
   - `GET /api/employees`
   - `GET /api/cases`
   - `GET /api/policies`
   - `GET /api/payroll-ledgers`
   - `GET /api/recruitment`
   - `GET /api/documents`
   - `GET /api/messages`
   - `GET /api/notifications`
   - `GET /api/audit`
4. If the task names a case or opening, fetch `GET /api/cases/{case_id}` for approvals, attachments, comments, and case-scoped audit events.
5. Filter records to the named employee, case, opening, candidate, period, or control package. Do not let adjacent records drive the answer unless the prompt asks for related or cross-module evidence.
6. Fill every field in the template. Use exact IDs, names, numbers, dates, booleans, and arrays from evidence. Use enum values exactly as listed in the template.
7. Before finalizing, verify JSON syntax, field order if practical, required field coverage, array element type, and numeric type. Return no markdown or explanation when the prompt says JSON only.

## Evidence Precedence

Use authoritative records over summaries:

- Leave: for the effective period, use the latest `Leave assignment` with status `Approved` or `Submitted`. Exclude `Draft`, `Superseded`, voided, obsolete, and stale profile-summary records. Use profile summary only when no controlling assignment exists and the template permits that source.
- Payroll salary: use the current `Salary assignment` with status `Submitted`. Exclude draft planning assignments and superseded assignments unless the task explicitly asks to report them as excluded records.
- Recruitment outcomes: use committee decision plus accepted offer evidence, not messages alone. A selected candidate needs accepted offer confirmation before payroll handoff. Waitlisted and rejected candidates are not selected-offer holders.
- Folder readiness: compare `required_files` with filed `files`, and `required_tags` with present `tags`. A folder is not ready if any required file or tag is missing, even when the case has approval.
- Notice quality: inspect notice packets and messages for `quality`, `defects`, `required_action`, and status. A defective notice blocks closeout when the task asks for closeout readiness.
- Audit: use audit events whose `event`, `case_id`, `employee_id`, and detail match the requested decision scope. Report adjacent audit events as excluded when the prompt asks to exclude out-of-scope audit evidence.

## Common Decisions

Map evidence to normalized labels from the current template:

- Clean onboarding closeout: approve only when authoritative leave and payroll records are clean, no required folder/notice blocker is in scope, and the requested approval gate is satisfied.
- Folder or notice defect: approval alone is not sufficient. Use the blocker/remediation labels for missing required files, missing required tags, and defective formal notices.
- Leave profile mismatch: when an approved/submitted assignment controls over a stale profile summary, mark profile-summary fields as ignored/stale and choose the leave-source-precedence audit scope.
- Payroll readiness: when submitted salary assignment matches accrual-readiness evidence and draft assignments are excluded, choose payroll-readiness labels and ready-with-monitoring style control results if offered.
- Recruitment follow-up: sum every cost ledger item for the opening. Put candidate IDs only in candidate arrays. Notice follow-up arrays should include candidates whose packet/message says a notice is missing or defective. Payroll handoff is gated to the selected candidate with an accepted offer and must not be satisfied by draft precheck records for another candidate.
- Cross-module control packages: inspect the package audit event for related audit IDs, then fetch or correlate each related event. Assign owner, remediation, and final result by the entity-level issues actually present, not by the package summary alone.

## Field-Filling Rules

- For `excluded_*` fields, include IDs for records deliberately ignored because they are draft, superseded, obsolete, adjacent, or out of scope.
- For `supporting_*` fields, include only evidence IDs that directly support the requested scope.
- For `missing_files`, return exact required filenames absent from the folder.
- For `notice_defects`, return exact defect labels from packet/message evidence when they are allowed by the template.
- For salary, leave days, balances, and cost totals, copy numeric evidence as numbers, not strings.
- For dates, preserve the evidence date format expected by the template or prompt.
- If a template offers overlapping labels, choose the most specific label that matches the authoritative source named by the prompt.

## Sanity Checks

Before answering:

- Ensure every value is supported by a record, policy, audit event, packet, message, or explicit prompt instruction.
- Ensure no draft/superseded record has been used as authoritative unless the task explicitly asks for draft/superseded status.
- Ensure audit scope labels match the decision being made: leave source precedence, document/notice findings, payroll readiness, recruitment notice follow-up, or cross-module package handling.
- Ensure closeout-style fields are internally consistent: blockers imply hold/block/remediate; clean authoritative records imply approve; ready payroll/accrual evidence implies ready-with-monitoring when that is the offered control result.
