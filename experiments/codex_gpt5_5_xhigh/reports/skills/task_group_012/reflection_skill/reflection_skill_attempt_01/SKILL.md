---
name: peopleops-control-reconciliation
description: Use for Northwind PeopleOps Console tasks that require reconciling onboarding, leave, payroll, remote-work, document/notice, recruitment, or audit evidence into a normalized JSON answer.
---

# PeopleOps Control Reconciliation

## Core Workflow

1. Read the prompt and answer template first. Treat enum values in the template as the only allowed normalized labels.
2. Use the local PeopleOps Console or its API as the evidence source. Prefer targeted queries by employee ID, case ID, opening ID, candidate ID, or audit ID.
3. Collect evidence from every module named by the prompt before deciding: employee profile, payroll/leave ledgers, case detail, approvals, documents, messages/notices, recruitment records, policy viewer, and audit detail.
4. Reconcile source precedence and control gates before filling JSON. Do not copy stale profile summaries, drafts, superseded rows, or adjacent audit events into authoritative fields.
5. Return only JSON matching the template. Use native booleans/numbers, exact enum strings, and arrays containing only the requested IDs or file names.

## Environment And API Usage

The app normally runs at the task-provided `http://127.0.0.1:<port>/` with the local PeopleOps credentials from the prompt. The served frontend exposes useful JSON routes:

- `/api/employees?q=<term>` for profile summaries.
- `/api/payroll-ledgers?q=<term>` for leave assignments, salary assignments, accrual batches, and payroll/leave status.
- `/api/cases?q=<term>` and `/api/cases/<case_id>` for case overview, approvals, attachments, comments, and case audit events.
- `/api/documents?q=<term>` for folder files, required files, tags, required tags, and readiness.
- `/api/messages?q=<term>` for formal notice/message inspection.
- `/api/recruitment?q=<opening_id>` for candidates, offers, cost ledger, notice packets, and payroll precheck records.
- `/api/policies/<policy_id>` for source-precedence and gate rules.
- `/api/audit?q=<term>` and `/api/audit/<audit_id>` for audit scope and detail.

Search narrowly, then cross-check by related IDs. For example, after finding a case, query documents, messages, and audit by the case ID and by the employee/opening ID if the prompt asks about adjacent events.

## Source Precedence Rules

### Leave

- The current approved or submitted leave assignment for the requested period controls over employee profile summary fields.
- Draft, voided, obsolete, and superseded leave assignments are excluded even if their dates or values look newer.
- If a profile policy/balance conflicts with an approved assignment and leave-source policy/audit confirms the assignment, mark the profile as ignored/stale and use assignment-scope labels such as `approved_assignment_over_profile` and `approved_assignment_current_period`.
- Leave audit support should include leave-source events only. Put nearby folder/document/notice audit IDs in excluded audit fields when the prompt asks to exclude adjacent events from the leave decision.

### Payroll

- The submitted salary assignment controls base salary, effective date, and payroll readiness. Draft planning assignments do not satisfy payroll or accrual gates.
- Excluded payroll fields should name draft or superseded salary assignment IDs, not leave ledger IDs.
- If no explicit effective date exists, use the submitted salary assignment's effective/update date as `YYYY-MM-DD`, not the draft date.
- Accrual readiness requires the submitted salary assignment to match the accrual batch evidence and payroll-readiness audit. Use payroll assignment audit scope labels for this path.

### Recruitment

- Candidate outcomes come from candidate review/committee decision, confirmed by accepted offer records for the selected candidate.
- Candidate arrays must contain candidate IDs only.
- `recruitment_cost_total` is the sum of all recruiting campaign cost ledger line amounts.
- Notice follow-up comes from notice packet inspection: include candidates whose waitlist or rejection notices are missing or defective, and choose the corresponding waitlist/rejection action.
- For accepted selected candidates, `onboarding_handoff` names the next artifact to create. If there is an accepted offer but no payroll precheck/assignment yet, use `create_payroll_precheck`; keep `submitted_after_acceptance` for assignment-status-required and handoff-control fields.
- For waitlisted candidates excluded from offer/payroll handoff, prefer `no_accepted_status_or_offer` when the reason is absence of an accepted offer, even though their candidate outcome is waitlisted.

## Folder, Notice, And Closeout Gates

- Approval history establishes the decision and approver, but approval is not enough when required folder files/tags or formal notices are defective.
- Folder readiness is computed from `required_files - files` and `required_tags - tags`; do not rely only on the summary text.
- Missing required files produce `missing_required_files`; missing required tags produce `missing_required_tags`. If required tags are present, use the no-tag-action label.
- Formal notice quality should use notice packet inspection when the workflow/prompt refers to notice packets or formal notice inspection. Use message inspection only when the message is the sole notice artifact and no notice-packet source is available.
- A defective notice usually drives `block_close_and_reissue_notice` for the immediate next action and `reissue_defective_notices` for notice remediation.
- Separate records remediation from notice remediation. Folder/file defects route records remediation to `Records` and usually use `open_records_remediation` for the escalation-action field, while the closeout result remains blocked/held.
- Final closeout is approved only when authoritative leave/payroll records are clean and no folder/notice gate is defective. Folder or notice defects should produce a hold/block final control result even if the underlying business decision was approved.

## Audit Scope Discipline

- Match the audit scope to the task: leave precedence, payroll readiness, or document/notice findings.
- `supporting_audit_event_ids` should include only audit events that support that scope.
- `excluded_audit_event_ids` should include adjacent events from the same case/employee/opening that are real but out of scope. Use an empty array only after checking related audit queries.
- Do not let a document/notice audit change a leave-source answer, or a leave/payroll audit change a folder/notice answer.

## Common Pitfalls

- Do not choose a draft or superseded row because it has a newer date or larger amount.
- Do not use profile summary leave balance as authoritative when an approved assignment exists.
- Do not confuse `onboarding_handoff` with `payroll_assignment_status_required`; one is the next operational artifact, the other is the gate standard.
- Do not assign folder remediation to People Ops Compliance when missing required files/tags are records defects; use the Records owner label when available.
- Do not mark `notice_evidence_source` as message-based merely because the API route is `/api/messages`; the business source may still be notice packet inspection.
