---
name: peopleops-reconciliation
description: Reconcile PeopleOps Console tasks and produce exact JSON answers from provided answer templates for onboarding, leave, payroll, recruitment, approval, notice, and audit/source-precedence cases. Use when a prompt points to a task runner URL or task environment and asks for authoritative records, exclusion lists, normalized enum labels, or final control results.
---

# PeopleOps Reconciliation

## Procedure

1. Read the prompt, the answer template, and any payload files first. Treat `input/payloads/answer_template.json` as the schema contract for the run.
2. Identify the task family from the template fields and the evidence surfaces named in the prompt.
3. Open the runner URL from the prompt and inspect the live console or its structured data surfaces with the provided credentials.
4. Pull only the records that can decide that family. Prefer structured records over summaries when both exist.
5. Use authoritative sources:
   - submitted, approved, accepted, assigned, current-period, and audit-backed records
   - treat drafts, stale profile summaries, and message-only hints as secondary unless the template asks for them
6. Separate scope tightly. Include only audit events that directly support the requested decision. Put adjacent or out-of-scope audit IDs in excluded arrays when the template provides them.
7. Assemble one JSON object that matches the template exactly.
8. Validate the draft before answering. Check key names, types, enum labels, and array contents. Use `scripts/validate_answer.py` for a mechanical check when helpful.

## Task Cues

- Onboarding closeout and leave/payroll verification: follow assignment history and submitted payroll records; exclude draft records explicitly.
- Folder/notice approval: verify folder completeness, required tags, notice quality, approval authority/event, blocker labels, and remediation actions.
- Recruitment reconciliation: use interview feedback, offer register, recruitment cost ledger, notice packets, and accepted-offer status to choose the selected candidate and follow-up work.
- Leave precedence: let an approved assignment override a stale profile summary when the ledger, policy, and audit support it.
- Payroll readiness: use submitted assignments, exclude drafts, and verify accrual batch readiness and effective dates.

## Output Rules

- Copy field names and controlled labels exactly from the template.
- Use IDs only in list fields.
- Return one JSON object only.
- Do not add markdown, commentary, or free-form explanations.
