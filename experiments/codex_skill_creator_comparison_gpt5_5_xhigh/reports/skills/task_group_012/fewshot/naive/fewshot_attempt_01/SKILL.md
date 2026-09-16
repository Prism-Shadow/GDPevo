---
name: peopleops-lifecycle-reconciliation
description: Solve PeopleOps Console lifecycle verification tasks by reconciling authoritative HR, leave, payroll, recruitment, document, notice, policy, and audit evidence into exact-template JSON.
---

Use this skill for PeopleOps Console tasks that ask you to verify lifecycle readiness, source precedence, recruitment outcomes, leave setup, payroll assignment, folder readiness, formal notice quality, or scoped audit evidence.

## Core Rule

Build the answer from the current task's `input/payloads/answer_template.json`, not from memory. The template is the schema and the source of every allowed normalized label. Return exactly the template's fields, with no extra fields, no markdown, and no explanatory text.

## Access Pattern

1. Open the configured `<TASK_ENV_BASE_URL>`.
2. Log in with credentials from the prompt if the app asks for them. Some environments are already authenticated.
3. Prefer direct business JSON endpoints when available because they reduce UI transcription errors. Useful endpoints usually mirror the app modules:
   - `/api/manifest`
   - `/api/summary`
   - `/api/employees`
   - `/api/cases`
   - `/api/cases/{case_id}`
   - `/api/policies`
   - `/api/policies/{policy_id}`
   - `/api/payroll-ledgers`
   - `/api/recruitment`
   - `/api/documents`
   - `/api/messages`
   - `/api/audit`
   - `/api/audit/{audit_id}`
   - `/api/attachments/{attachment_id}`
4. If API access is unavailable, use the same evidence through the UI modules: Employees, Recruitment, Leave, Payroll, Policy Cases, Documents, Messages, and Audit Log.

## Evidence Hierarchy

Use source precedence deliberately:

1. Policy text defines the rule when records conflict.
2. Authoritative operational records control the answer: approved or submitted assignments, accepted offer registers, folder checklists, notice packets, payroll ledgers, and detailed case approval history.
3. Audit events confirm scoped control findings and often provide the normalized business result for that scope.
4. Employee profile summaries, case summaries, messages, and comments are secondary. Use them only when the template has a label such as `case_summary_only`, `employee_profile_summary`, or `message_only`, or when no stronger record exists.

Never let a draft, superseded, obsolete, voided, stale, or placeholder record override an approved/submitted current-period record. When the prompt asks for exclusions, include the IDs of those non-authoritative records.

## Answer Workflow

1. Read the prompt and extract the target entity: employee ID/name, case ID, opening ID, candidate IDs, period, requested control, and requested output categories.
2. Read the answer template and create a working answer object with exactly those keys.
3. Gather all records for the target from relevant modules. Search by every reliable identifier from the prompt because related evidence may be stored under employee ID, case ID, opening ID, candidate ID, document title, or audit event.
4. Open referenced policies and use them to resolve conflicts. Do not rely on case summary wording when policy plus records disagree.
5. Choose source records, fill values, then validate each enum against the template's `allowed_values`.
6. Before final output, re-check JSON types: numbers as numbers, booleans as booleans, arrays as arrays, and empty arrays as `[]`.

## Leave Source Precedence

For leave setup, annual entitlement, or balance validation:

- Use leave assignment records for the target employee and requested effective period.
- Prefer the current approved assignment. If policy and template allow submitted leave assignments, use the current submitted assignment only when there is no approved current assignment.
- Use the authoritative assignment's policy name and approved days or balance field. Do not use worksheet values when approved entitlement fields are present.
- Exclude draft, superseded, obsolete, voided, and stale assignments. Include their IDs in exclusion fields when requested.
- If an employee profile summary conflicts with the approved assignment and policy says assignment history controls, mark the profile summary as ignored/stale using the matching template label.
- For audit scope fields, include only leave-source precedence audit events. Adjacent document, notice, or payroll audit events belong in excluded-audit fields when the template asks for them.

When the template has multiple precedence labels, choose the label whose wording says the approved/current assignment controls over summaries. When the template has multiple next-action labels for stale summaries, choose the label that updates the stale summary unless the prompt asks for a remediation case instead.

## Payroll Assignment And Accrual Readiness

For payroll setup, salary assignment, handoff, or accrual readiness:

- Use salary assignment records for the target employee and effective period.
- The current submitted salary assignment controls base salary and payroll readiness.
- Draft planning assignments do not satisfy readiness or handoff gates. Superseded assignments are historical only.
- Fill excluded assignment fields with draft or superseded IDs that the prompt asks you to ignore.
- Use accrual batch IDs from the submitted salary assignment, payroll ledger, or scoped audit detail.
- Treat readiness as true only when the submitted assignment and accrual evidence agree. If audit detail says ready with monitoring, choose the matching control-result enum from the template.
- Set audit scope to the payroll-readiness label only for payroll assignment/accrual findings.

## Case Approval, Folder, And Notice Controls

For remote-work, onboarding closeout, policy exception, or folder/notice quality tasks:

- Get the final decision and approval authority from detailed approval history, not from case summary text.
- Folder readiness requires every required file and every required tag to be present. Compute missing files from `required_files - files` and missing tags from `required_tags - tags`.
- A present required tag means no tag action is needed. A missing required tag is a closeout blocker when the template includes tag blockers.
- Inspect notice packets, message records, attachments, and audit detail for notice quality. Use defect labels from the template, such as missing acknowledgement deadline, appeal instructions, waitlist status, or correct policy when those labels are available.
- Final approval is not enough to close when the folder is incomplete or the formal notice is defective. In that case choose the template's block/hold/remediation labels.
- If records, folder, and notice are clean, choose the approval/closeout-ready labels from the template.
- For document/notice audit fields, include only audit events whose event/detail addresses folder, tag, document, or formal-notice findings. Exclude adjacent leave or payroll audit events when requested.

## Recruitment Reconciliation

For recruiting pipeline or opening reconciliation tasks:

- Use the recruitment record for the opening as the primary source for candidate outcomes.
- The selected candidate must be supported by committee decision and an accepted offer register entry.
- Waitlisted and rejected outputs are arrays of candidate IDs only. Preserve source order unless the prompt specifies a different order.
- Sum every recruiting campaign cost ledger line for `recruitment_cost_total`. Do not use a summary total unless no ledger exists and the template permits summary-only sourcing.
- Notice follow-up is required for candidates with missing, unsent, defective, or draft-reissue notice packets. Use each packet's required action when it matches a template enum.
- Waitlisted candidates are not rejected candidates; if a waitlist notice is defective, use a waitlist reissue label rather than a rejection notice label.
- Payroll handoff is gated by accepted offer status. Draft precheck or placeholder records do not satisfy a submitted-assignment requirement.
- If there is an accepted offer but no submitted handoff/precheck yet, choose the template label that creates the required payroll precheck or submitted assignment after acceptance.

## Audit Handling

Audit events are evidence for the requested control, not a blanket override.

- Match by target case, employee, opening, candidate, and event category.
- Read audit detail for explicit QA result wording and referenced record IDs.
- Use the template's audit-scope enum to label the evidence category requested by the prompt, such as leave precedence, document or notice findings, payroll readiness, or another provided scope.
- Put relevant audit IDs in supporting fields. Put same-entity but wrong-scope audit IDs in excluded fields when requested.
- Do not include unrelated audit events just because they share a date or appear nearby in the log.

## JSON Validation Checklist

Before responding:

- The output is a single JSON object and nothing else.
- The key set matches the template exactly.
- Every enum value is copied exactly from the current template's `allowed_values`.
- All requested IDs come from authoritative records.
- Arrays contain the requested primitive type only, usually IDs or enum labels.
- Missing-file arrays follow the folder checklist order.
- Exclusion arrays contain records deliberately ignored by the applied source rule.
- Numeric totals are recomputed from ledger lines.
- The final action/control fields agree with the blockers: clean records can approve; folder, tag, notice, draft, or missing-handoff defects must hold, block, or remediate according to the template.
