---
name: peopleops-console-reconciliation
description: Use this skill for PeopleOps Console reconciliation tasks that ask for JSON answers about onboarding closeout, leave source precedence, payroll assignment readiness, recruitment outcomes, document folder readiness, formal notice quality, audit scope, or normalized business labels. Trigger whenever a task mentions People Ops, HRMS, employee onboarding, payroll/leave assignments, recruitment packets, policy cases, folders, notices, or audit events.
---

# PeopleOps Console Reconciliation

## Core SOP

1. Read the prompt and `input/payloads/answer_template.json` before collecting data. The template is the contract: use its exact field names, enum labels, booleans, numbers, and array element types.
2. Use `environment_access.md` for the active base URL. When a prompt shows `127.0.0.1:<port>`, replace it with the remote base URL from the environment file.
3. Gather evidence by entity ID and by human name. Prefer the structured API behind the console over visual scraping when available.
4. Read policy documents referenced by the case or record before choosing normalized labels. Policy text often explains source precedence and draft exclusions.
5. Resolve source precedence, then fill the JSON. Do not narrate inside fields that expect normalized labels.
6. Before finalizing, check every array for the required element type. Candidate arrays should contain candidate IDs only when the prompt says so; file arrays should contain exact filenames.

## Useful Console Endpoints

The portal commonly exposes these JSON routes:

- `/api/employees?q=...`
- `/api/cases?q=...` and `/api/cases/{case_id}`
- `/api/recruitment?q=...`
- `/api/payroll-ledgers?q=...`
- `/api/policies?q=...` and `/api/policies/{policy_id}`
- `/api/documents?q=...`
- `/api/messages?q=...`
- `/api/audit?q=...` and `/api/audit/{audit_id}`
- `/api/attachments/{attachment_id}`

Use the case detail for approvals, attachments, comments, and case-scoped audit events. Use module endpoints for the full record set, because summaries can omit draft/superseded alternatives that must be excluded.

## Source Precedence

### Leave

- The approved or submitted leave assignment for the relevant period controls over an employee profile summary, case summary, worksheet value, draft, obsolete, or superseded record.
- If an audit event says the profile summary is stale and names the controlling assignment, use the assignment and set the profile-ignore fields accordingly.
- Use the assignment's policy name and approved days for the effective policy and balance.
- Use `approved_assignment_current_period` for leave precedence when the current approved assignment controls.
- Scope leave audit answers to `leave_source_precedence_only`; exclude adjacent folder/document/notice audit events from the leave decision.

### Payroll

- Use the current submitted salary assignment. Draft payroll assignments and draft prechecks do not establish payroll readiness.
- The submitted salary assignment supplies the salary, assignment ID, accrual batch, and effective date. If the record has a timestamp and no explicit effective-date field, use the ISO date portion of the submitted assignment timestamp.
- Use `submitted` for payroll source status when the selected assignment is submitted.
- Use `exclude_draft_assignment` when a draft payroll assignment is present but must not control.
- Scope payroll readiness audit answers to `payroll_assignment_readiness`; exclude document/notice or leave-precedence audits from that decision.

### Recruitment

- Candidate outcomes come from committee decision plus offer register confirmation, not from case summary or messages alone.
- A selected candidate should have an accepted offer before payroll handoff. Waitlisted and rejected candidates do not get payroll handoff.
- Recruiting cost total is the sum of all recruiting campaign cost-ledger line amounts only. Do not include salary, offer amounts, or payroll figures.
- Notice follow-up arrays should contain candidate IDs only. Use notice packets for missing or defective waitlist/rejection notices.
- For waitlisted candidates excluded from offer/payroll handoff, prefer the reason that they do not have accepted offer status or an offer, unless the template asks for a simpler waitlist-specific label.
- Draft payroll/precheck records do not satisfy the submitted handoff gate.

### Folder And Notice Readiness

- Approval is not enough when required folder evidence or formal notices are defective.
- A folder is ready only when every required file and every required tag in the checklist is present.
- Missing folder files should drive a records remediation path and usually a `Records` remediation owner.
- Missing required tags are separate from missing required files. Do not add a missing-tag blocker if the required tag is present.
- Formal notice defects should come from notice/message inspection or notice packets. Use the defects listed in the source; avoid inventing defects unless policy text and the notice body clearly show them.
- A defective formal notice generally maps to reissuing defective notices and a closeout hold/block.

## Audit Scope Rules

Audit events are authoritative only for their scope:

- `leave_source_precedence_only`: leave policy/balance source conflicts.
- `payroll_assignment_readiness`: submitted salary assignment and accrual readiness.
- `document_notice_findings_only`: folder, required evidence, tags, and formal notice quality.

Include supporting audit IDs that match the requested scope. Put adjacent but different-scope audit IDs in the excluded list when the prompt asks for exclusions. Examples of adjacent exclusions include folder/tag audits excluded from leave precedence, payroll-readiness audits excluded from document/notice decisions, and leave-precedence audits excluded from payroll readiness.

## Label Conventions

- Use `approval_sufficient_when_records_clean` only when folder, notice, leave, and payroll records are clean for closeout.
- Use `approval_not_sufficient_when_folder_or_notice_defective` when approval exists but required folder or notice evidence is defective.
- Use `approve_closeout` only for clean closeout controls.
- Use `hold_for_folder_and_notice_defects` when folder readiness or formal notice quality blocks closeout.
- Use `ready_with_monitoring` for a readiness state confirmed by audit, especially payroll/accrual readiness, rather than treating it as final closeout approval.
- Use `open_records_remediation` for folder/evidence repair; use `block_close_and_reissue_notice` when closeout must be stopped and notice reissue is required.
- Use `reissue_defective_notices` for defective notice remediation and `no_notice_action` only when notices are valid or irrelevant.

## Common Exclusions

- Exclude draft, superseded, obsolete, and voided assignments from effective leave/payroll decisions.
- Exclude employee profile summaries when an approved assignment and audit detail show the summary is stale.
- Exclude case summaries as the sole source when assignment history, offer registers, ledgers, notice packets, or audit details are available.
- Exclude unrelated audit events even if they share a case, employee, or lifecycle package, unless their scope matches the requested decision.
- Exclude waitlisted/rejected candidates from selected-offer and payroll handoff fields.
- Exclude salaries from recruitment cost totals.

## Pitfalls

- Do not confuse `period` with an effective date when a submitted assignment timestamp is present.
- Do not use worksheet days when approved days are available for authoritative leave balances.
- Do not treat a draft notice or draft payroll/precheck as submitted evidence.
- Do not let a clean approval override a defective folder or notice.
- Do not list names in arrays that require IDs.
- Do not collapse multiple action fields into one idea: next action, escalation/remediation action, owner, gate, and final control result can intentionally differ.
- Do not infer notice defects from generic policy requirements if the inspected notice already contains that required element.
