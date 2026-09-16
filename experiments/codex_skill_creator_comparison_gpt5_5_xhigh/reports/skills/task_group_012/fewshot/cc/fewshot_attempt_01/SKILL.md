---
name: peopleops-console-reconciliation
description: Solve PeopleOps Console reconciliation tasks that require verifying leave, payroll, recruitment, policy-case, folder, notice, or audit records and returning a normalized JSON answer from the provided template. Use this skill whenever the prompt mentions PeopleOps Console, employee leave precedence, payroll assignment readiness, recruitment outcome packets, case folder readiness, formal notice defects, audit evidence, or any task that asks you to choose authoritative submitted or approved records and exclude drafts or stale summaries.
---

# PeopleOps Console Reconciliation

These tasks are evidence-selection problems. The prompt names the entity and the answer template defines the exact JSON shape. Work from the template first, then collect only the records needed to justify each field.

## Compatibility

Use the task environment API or console available from the prompt. Prefer the API when it exposes the same record data, because it is easier to inspect exact fields and status values.

## Workflow

1. Read the prompt carefully and identify the entity type and identifier.
2. Open `input/payloads/answer_template.json` and copy the field names and allowed enum values exactly.
3. Inspect the smallest set of authoritative records needed to answer the prompt.
4. Resolve conflicts by source precedence, not by recency alone.
5. Fill the template exactly and return JSON only.

## Source map

- `api/summary`: quick orientation and counts.
- `api/cases/{case_id}`: case approvals, attachments, comments, case-level audit events, and closeout status.
- `api/employees`: employee profile summaries, current leave balance, and employment metadata.
- `api/payroll-ledgers`: leave assignments, salary assignments, accrual readiness, statuses, and draft/submitted/superseded records.
- `api/recruitment`: opening data, candidates, offer register, cost ledger, notice packets, and payroll precheck records.
- `api/documents`: folder readiness, required files, required tags, and current folder contents.
- `api/messages`: notice quality, defect text, and draft notice bodies.
- `api/audit`: corroborating audit events and adjacent events that may need exclusion.
- `api/policies`: authoritative source-precedence, payroll, notice, and folder rules.

## Decision rules

- If an approved assignment conflicts with a profile summary, treat the profile as stale and keep the approved assignment.
- If the prompt says to use submitted or assignment-history records, ignore draft and obsolete records unless the template explicitly asks for excluded IDs.
- For payroll work, use the current submitted salary assignment. Draft planning assignments do not control readiness.
- For recruitment work, a payroll handoff only follows a selected candidate with an accepted offer. Sum cost-ledger amounts exactly when requested.
- For folder work, all required files and required tags must be present before the folder is ready.
- For notice work, defects such as missing appeal instructions, missing acknowledgement deadlines, missing waitlist status, or missing correct policy should be named only when supported by the record.
- If an audit event references related or adjacent events, use it only when it directly supports the requested decision. Do not let unrelated module events override the target entity.

## Scenario guide

### Leave tasks

Use the leave assignment history or approved assignment as the source of truth for current-period leave policy and balance. Ignore stale profile summaries and draft leave ledgers unless the prompt explicitly asks you to list exclusions.

### Payroll tasks

Use submitted salary assignments for payroll readiness and accrual checks. Exclude draft payroll planning entries. If the prompt asks for an accrual batch or effective date, return the exact ledger values.

### Recruitment tasks

Use the selected candidate, accepted offer, cost ledger, notice packet, and payroll precheck evidence together. Return candidate IDs in arrays when requested. If the handoff is gated on acceptance, do not advance a draft precheck.

### Case, folder, and notice tasks

Use case approvals, folder attachments, required tags, messages, and audit events together. A single missing required file or tag makes the folder not ready. A defective notice blocks closeout even if the approval exists.

## Answer discipline

- Read the template before writing the answer.
- Use the exact field names from the template.
- Use allowed enum values exactly as written.
- Keep IDs in arrays as IDs only.
- Keep numbers numeric.
- Do not add markdown, headings, or explanatory text to the final response.

## Final check

Before answering, sanity-check that:

- Every required field in the template is filled.
- Every enum value matches the template vocabulary.
- Every excluded ID is a real draft, stale, or adjacent record.
- Every numeric field matches the source exactly.
- The final control field matches the evidence and the decision gate.
