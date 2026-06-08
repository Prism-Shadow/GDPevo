---
name: peopleops-lifecycle-reconciliation
description: Use for Northwind PeopleOps Console tasks that require reconciling employee leave, payroll assignment, onboarding closeout, remote-work case folders/notices, recruitment outcomes, audit evidence, and JSON answers that must match an answer_template with normalized enum labels.
---

# PeopleOps Lifecycle Reconciliation

## Core Workflow

1. Read the task prompt and `input/payloads/answer_template.json` first. Treat the template as the contract: include every requested field, use the declared JSON type, and use enum values exactly as listed.
2. Identify the target IDs and scope: employee ID, case ID, opening ID, candidate IDs, period, and the business question. Write a field checklist before searching so no required output field is skipped.
3. Use the PeopleOps Console or direct JSON endpoints. Prefer direct endpoints for precision, then use the UI only when a modal or attachment view is easier to inspect.
4. Collect evidence from all relevant modules before deciding. Do not rely on case summaries, employee profile summaries, or messages alone when ledgers, approval history, documents, notice packets, policies, or audit detail exist.
5. Apply source precedence and exclusion rules. Record both the selected authoritative records and the IDs that were considered but excluded.
6. Build the final `answer.json` directly from the template keys. Return only JSON, with no markdown, comments, or explanatory text.

## Environment Usage

Use the task-provided base URL and credentials. If using the command line, bypass local proxy settings:

```bash
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/health'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/employees?q=<employee_id_or_name>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/cases/<case_id>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/recruitment?q=<opening_id>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/payroll-ledgers?q=<employee_id_or_name>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/documents?q=<case_or_employee_or_document_id>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/messages?q=<case_or_message_or_candidate_id>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/audit?q=<case_or_employee_or_opening_id>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/audit/<audit_id>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/policies?q=<policy_keyword>'
curl --noproxy '*' -sS 'http://127.0.0.1:<port>/api/policies/<policy_id>'
```

Useful UI modules mirror these endpoints: Employees, Recruitment, Leave, Payroll, Policy Cases, Documents, Messages, Audit Log, and Policy Viewer. Case detail tabs expose Overview, Approval History, Comments, Attachments, and Audit Detail. Avoid posting comments or changing workflow state unless the task explicitly asks for it.

## Evidence SOPs

### Employee Leave

- Query the employee profile for identity and profile summary, but do not let profile leave fields override assignment history.
- Query payroll ledgers for records whose `record_type` is `Leave assignment` and period matches the requested effective period.
- The authoritative leave source is the latest current-period approved or submitted leave assignment. Exclude Draft, Superseded, Voided, Obsolete, and stale-period records even when they are newer, larger, or match the profile better.
- Use `policy_name` as the effective leave policy and `approved_leave_days` as the authoritative days/balance when an assignment controls.
- If an approved assignment conflicts with the employee profile summary, mark profile summary fields as ignored/stale when the template asks for that distinction. Use leave-scope audit events to support the decision.

### Payroll Assignment And Accrual Readiness

- Query payroll ledgers for `Salary assignment` rows. The current submitted salary assignment controls base salary, effective period/date, and payroll readiness.
- Draft salary assignments are planning records only. Exclude them even if their salary is higher or their update timestamp is later. Superseded rows are exclusions too.
- If the selected row has an `accrual_batch_id`, use it. Otherwise, corroborate readiness with payroll-scope audit detail that ties the submitted assignment to the batch.
- `accrual_ready` should be true only when a submitted assignment and matching readiness evidence exist. Use `payroll_assignment_readiness` for payroll audit scope fields.

### Case Approval, Folder, And Notice Closeout

- Open the case detail for approvals, policy references, attachments, and audit events. Approval history establishes authority and decision, but approval alone is not enough for closeout.
- Query documents by case or folder ID. Compute `missing_files` as `required_files - files`; compute missing tags as `required_tags - tags`. A folder is ready only when all required files and required tags are present.
- Query messages and notice packets for formal notice quality. Treat a notice as defective when the record has a nonempty `defects` list or the relevant policy requires content that is absent.
- For remote-work or exception notices, verify policy-driven requirements such as appeal instructions, acknowledgement deadline, correct policy reference, and any required tax or compliance evidence.
- If any required folder evidence or formal notice requirement is missing, use the template labels for blocking closeout, records remediation, and notice reissue. If records are clean and authoritative source records are valid, use the template labels for approving closeout.

### Recruitment Reconciliation

- Query `/api/recruitment?q=<opening_id>` first; it returns candidates, offer register, cost ledger, notice packets, and payroll precheck records together.
- Candidate outcomes come from committee decisions plus offer evidence, not from messages alone. The selected candidate must have an accepted offer. Waitlisted and rejected outputs should contain candidate IDs only.
- Recompute `recruitment_cost_total` by summing every `cost_ledger[].amount`; return a JSON number, not a formatted string.
- Notice follow-up comes from notice packet status, quality, defects, and `required_action`. Waitlist notices and rejection notices must match the candidate outcome.
- Payroll handoff is only for the selected candidate with an accepted offer. A submitted handoff/precheck after acceptance satisfies the gate; missing or draft handoff evidence requires the template label that asks for creation or submitted assignment after acceptance. Draft payroll/precheck records do not satisfy the gate.

### Audit Scope

- Choose the primary `audit_event_id` from the event whose `event` or `detail` directly supports the requested decision.
- Put same-scope corroborating events in `supporting_audit_event_ids`.
- Put adjacent but wrong-scope events in `excluded_audit_event_ids` when the template asks for exclusions. Examples of wrong-scope exclusions: folder/notice audit events for leave-source decisions, leave-source events for document/notice decisions, and document events for payroll readiness.
- Match `audit_scope` to the decision being supported: leave source precedence, document/notice findings, or payroll assignment readiness.

## Output Field Guidance

- Always start from the answer template. Do not invent fields or omit keys unless the template itself omits them.
- Convert display statuses to template enums exactly. For example, UI `Submitted` usually becomes `submitted` when the enum is lowercase.
- `excluded_*_ids` fields should list record IDs that were found and rejected because of status, period, scope, or source precedence. Use an empty list only when no excluded records were relevant.
- `missing_files`, `notice_defects`, and `closeout_blockers` must use the exact enum/string labels from the template. Do not paraphrase file names or defect names.
- `*_source`, `*_gate`, `*_scope`, `*_owner`, `*_remediation`, and `*_control_result` fields are normalized business labels. Pick from the allowed enum values; do not write prose explanations.
- Candidate arrays must contain candidate IDs, not names.
- Preserve IDs, dates, salaries, and numeric totals exactly. Keep numbers as JSON numbers and booleans as JSON booleans.

## Common Pitfalls

- Do not choose the newest row unless it is also authoritative for status and period. Draft and superseded rows are common traps.
- Do not treat an employee profile summary as controlling when assignment history and audit evidence identify a stale profile.
- Do not let a clean approval override folder or notice defects. Closeout can still be blocked after approval.
- Do not count a draft payroll handoff or draft salary assignment as submitted readiness.
- Do not include audit events from a different business scope just because they share the same case or employee.
- Do not use message-only or case-summary-only labels when richer module evidence exists.
- Do not return markdown, trailing commentary, or enum labels outside the template's allowed values.
