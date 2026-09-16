---
name: peopleops-console
description: Inspect PeopleOps Console casework and return exact JSON for onboarding closeout, leave-source precedence, recruitment reconciliation, payroll readiness, and document or notice reviews. Use when prompts mention the PeopleOps Console, employee leave or payroll records, recruitment openings, case folders, notices, audits, or ask for normalized business labels from a provided answer template.
---

# PeopleOps Console

Use this skill to solve PeopleOps Console tasks that require reconciling multiple record types into one JSON answer.

## Workflow

1. Read the task prompt and the answer template first.
2. Open the PeopleOps Console at the supplied runner URL and log in with the provided credentials.
3. Inspect only the workspace areas the prompt names:
   - employee, leave, payroll, recruitment, document, message, policy, and audit views as needed
4. Treat the prompt as a source-order hint, then resolve conflicts with this rule:
   - prefer submitted or approved assignment-history records over drafts, superseded records, stale profile summaries, and case-summary-only text
   - use direct packet, ledger, policy, or audit evidence over inferred status
   - exclude adjacent audit events when the prompt asks for a narrower scope
5. Fill every field in the template with the exact type and label it requests.
   - copy enum values literally from the template
   - keep arrays to the requested identifier values only
   - sum totals directly from the relevant ledger when asked
6. Return only the JSON object. No markdown, prose, or code fences.

## Common decision patterns

- Onboarding closeout: approve only when leave and payroll evidence are both clean; otherwise keep the closeout on hold or open remediation.
- Folder and notice reviews: a missing required file or a defective formal notice blocks approval and usually requires remediation or reissue.
- Leave precedence: an approved current-period assignment overrides a stale profile summary when ledger, policy, and audit evidence agree.
- Recruitment reconciliation: derive selection from committee decision plus offer confirmation; put waitlisted and rejected candidate IDs in their arrays; use the recruitment ledger for the total cost.
- Payroll readiness: use the submitted payroll assignment, exclude draft records, and tie accrual readiness to the submitted record plus the batch evidence.

## Output discipline

- Use the answer template as the schema.
- Preserve key order when practical.
- Do not invent synonyms for normalized business labels.
- If evidence is incomplete, keep searching the app instead of guessing.
