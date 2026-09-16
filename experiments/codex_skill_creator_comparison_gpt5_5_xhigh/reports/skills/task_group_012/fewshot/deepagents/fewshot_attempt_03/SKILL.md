---
name: peopleops-console-controls
description: Solve PeopleOps Console evidence-control tasks that require logging into a task environment, reconciling HR records, and returning JSON matching an answer_template. Use for onboarding closeout, remote-work case readiness, recruitment reconciliation, leave source precedence, payroll assignment, accrual readiness, formal notice, audit-scope, and folder control reviews.
---

# PeopleOps Console Controls

## Workflow

1. Read the task prompt and `input/payloads/answer_template.json` before opening the app. Treat the template as the output contract: exact keys, exact enum labels, correct JSON types, no extra fields.
2. Open the configured task URL and log in with the credentials from the prompt. Search by the entity in scope: employee, case, requisition/opening, candidate, payroll assignment, batch, or audit event.
3. Collect source records before deciding. Prefer transactional records and documents over summaries: assignment history, ledgers, offer registers, folder contents, notice packets, policy documents, approval history, and audit event details. Use profile or case summaries only when stronger source records are absent or explicitly confirmed current.
4. Track every excluded record ID while reviewing. Exclude drafts, superseded records, stale profile summaries, prior-period assignments, wrong-scope audit events, and adjacent audit events that do not support the requested decision.
5. Fill the JSON with the normalized labels from the template, not prose. If several labels seem plausible, choose the one that states the authoritative evidence source and control outcome most specifically.
6. Validate the draft answer with `scripts/validate_answer.py` before finalizing.

## Evidence Rules

### Leave Precedence

- Use an approved current-period leave assignment as authoritative when it is supported by the ledger, policy document, or leave-scope audit detail.
- Use the employee profile summary only when it is current and not contradicted by an approved assignment. Mark the profile ignored/stale when an approved assignment overrides it.
- Derive policy name and day balance from the selected assignment and the corresponding policy/effective-period evidence.
- Set audit scope to the leave-precedence scope when the audit event is about leave source precedence. Include supporting leave audit events and exclude document/notice or payroll audit events from that decision.

### Payroll And Accrual Readiness

- Select submitted payroll assignments for salary, effective date, and payroll readiness. Exclude draft assignments and superseded assignments from the selected payroll source.
- Use accrual readiness only when the relevant batch/readiness evidence and payroll-scope audit detail support the requested period.
- Payroll handoff is gated by accepted offer or submitted assignment evidence as requested by the template. Draft payroll data is not enough unless the template and prompt explicitly allow drafts.
- Use the payroll-readiness audit scope for payroll assignment or accrual controls.

### Folder, Notice, And Closeout Controls

- Take final approval decision, authority, and approval event from approval history, not from a case summary alone when approval history is available.
- A folder is not ready when required files or required tags are missing. List missing file names exactly as shown in the app.
- Inspect notice packets first, then message notices, then case summary only as a fallback. A notice is defective when it is missing required policy, acknowledgement deadline, appeal instructions, waitlist status, or other template-listed requirements.
- Approval is insufficient for closeout when folder or notice defects remain. Use blocking/remediation labels for defective folders or notices; use approval/clean-record labels only when records, folders, and notices are clean.

### Recruitment Reconciliation

- Determine candidate outcomes from committee/interview evidence plus offer register status. The selected candidate must be supported by accepted/selected offer evidence; waitlisted and rejected candidates stay out of payroll handoff.
- Return candidate arrays with candidate IDs only when the prompt requires that format.
- Sum all recruiting campaign ledger items requested by the prompt, excluding non-recruiting or unrelated ledger lines.
- Require follow-up for missing or defective candidate notices. Distinguish waitlist notice follow-up from rejection notice follow-up using the notice type each candidate should have received.
- Gate onboarding/payroll handoff to the accepted candidate and use the template label that matches the required next state.

## Output Checks

- Preserve IDs, filenames, dates, names, salaries, and batch IDs exactly as shown in authoritative evidence.
- Use numbers as JSON numbers, booleans as JSON booleans, and empty arrays when no records apply.
- Do not add explanatory text, markdown, or comments to the final answer.
- Do not infer evaluator internals. Base each field on visible prompt, template, and application evidence.

## Validator

Use the bundled validator from this skill directory:

```bash
python scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

The script checks required keys, unexpected keys, JSON types, and enum values. It does not verify business correctness; use the evidence rules above for that.
