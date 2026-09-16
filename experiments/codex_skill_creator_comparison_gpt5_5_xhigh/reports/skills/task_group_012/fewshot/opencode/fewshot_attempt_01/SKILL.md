---
name: peopleops-console-reconciliation
description: Investigate PeopleOps Console tasks that reconcile employee, leave, payroll, recruitment, document, message, policy, and audit records, then return strict JSON matching the supplied answer template. Use this whenever the prompt asks you to open the task-env URL, compare authoritative vs draft or stale records, exclude irrelevant evidence, or fill a normalized business JSON answer for a PeopleOps case, employee, payroll, leave, or recruiting review.
---

# PeopleOps Console Reconciliation

These tasks are record-reconciliation exercises, not free-form analysis. Treat the answer template as the contract.

## Workflow

1. Read the prompt and answer template first.
   - List every required key, type, and allowed enum.
   - Note any fields that expect IDs, arrays, booleans, or numbers.
2. Open the provided task environment URL and log in with the prompt credentials.
3. Orient yourself with the top-level maps:
   - `/api/manifest`
   - `/api/summary`
   - `/api/cases`
   - Read the case detail early when it exists; it often exposes approvals, attachments, comments, and audit events that point to the authoritative IDs.
4. Pull only the module evidence the template needs:
   - Employees and leave: `/api/employees`, `/api/payroll-ledgers`, `/api/policies`, `/api/audit`
   - Folder and notice cases: `/api/cases/{case_id}`, `/api/documents`, `/api/messages`, `/api/audit`
   - Recruitment: `/api/cases/{case_id}`, `/api/recruitment`, `/api/messages`, `/api/audit`
   - Payroll readiness: `/api/cases/{case_id}`, `/api/payroll-ledgers`, `/api/policies`, `/api/audit`
5. Follow source precedence.
   - Treat approved or submitted assignment history as authoritative over profile summaries, drafts, placeholders, voided rows, superseded rows, and case summaries.
   - Use summaries to locate the right records, not as proof.
   - For leave, the latest approved or submitted assignment for the period controls.
   - For payroll, the current submitted salary assignment controls base salary and readiness.
   - For recruitment, the selected candidate must line up with the accepted offer; draft payroll prechecks do not satisfy the handoff gate.
   - For folders and notices, a folder is ready only when all required files and required tags are present, and a formal notice is defective if required content is missing.
   - For audit, include only the event IDs that directly support the scoped decision; keep adjacent or cross-module events out unless the template explicitly asks for exclusions.
6. Map prose to the template exactly.
   - Use the allowed enum labels verbatim.
   - Keep IDs verbatim from the records.
   - Keep arrays as ID lists only.
   - Keep numbers numeric and booleans boolean.
   - Do not invent keys or values that are not in the template.
7. Finalize only after a consistency pass.
   - Every required field should be sourced from a concrete record.
   - Every exclusion should be explainable by precedence or scope.
   - The final control result should match the evidence, not the case summary alone.
   - Output JSON only. No markdown, no explanation, no extra wrapper.

## Practical checks

- If the prompt says to use authoritative submitted or assignment-history records, ignore drafts unless you need them for an exclusion list.
- If the prompt says to use normalized business labels, copy the template's labels exactly instead of paraphrasing them.
- If multiple records disagree, trust the newest approved or submitted record in the relevant period unless the policy says otherwise.
- If a field asks for supporting or excluded audit IDs, prefer the direct QA event and exclude unrelated folder, payroll, or notice events that are only context.
