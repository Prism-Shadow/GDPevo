---
name: peopleops-reconcile
description: Reconcile PeopleOps Console records across employees, leave, payroll, recruitment, policy cases, documents, messages, and audit logs. Use when a task asks for authoritative source precedence, folder or notice readiness, payroll assignment readiness, recruitment outcome reconciliation, closeout control decisions, or a normalized JSON answer from the task environment.
---

# PeopleOps Reconcile

## Workflow
1. Open the runner manifest and summary first.
2. Read only the module records the prompt names.
3. Prefer the authoritative source for that module over profile summaries, drafts, superseded rows, or cross-module escalation notes.
4. Apply the rules in [references/api-map.md](references/api-map.md) for leave, payroll, folder, notice, recruitment, and audit evidence.
5. Match every requested field to the provided answer template and copy enum labels exactly.
6. Return JSON only.

## Decision Rules
- Treat approved or submitted assignment-history records as authoritative when they conflict with profile summaries or drafts.
- Treat current submitted salary assignments as authoritative for payroll readiness and accrual checks; exclude drafts and superseded assignments.
- Treat a folder as not ready until every required file and required tag is present.
- Treat a formal notice as defective when the notice or its audit detail omits a required element named in the prompt or template.
- Treat recruitment follow-up as driven by the committee decision plus the offer register; create payroll handoff only after acceptance and a submitted assignment or precheck.
- Use only the audit event ids that directly support the requested decision. Exclude adjacent or cross-module events when the template asks for exclusions.

## Output Rules
- Use the template keys exactly.
- Use ID-only arrays.
- Do not paraphrase enum labels.
- Do not include markdown, prose, or extra keys.
