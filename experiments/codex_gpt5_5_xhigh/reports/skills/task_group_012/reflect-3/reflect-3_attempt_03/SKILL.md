---
name: peopleops-console-verification
description: Use this skill for PeopleOps Console verification tasks involving employee leave, payroll assignments, recruiting packets, remote-work cases, folders, notices, policies, or audit evidence. Always use it when a prompt asks for JSON matching an answer_template, normalized business labels, source precedence, exclusions, or final control/closeout decisions in the PeopleOps/Northwind HRMS environment.
---

# PeopleOps Console Verification

Use this skill to solve PeopleOps Console tasks that require evidence-backed JSON answers. The main failure mode is not finding the facts; it is returning the right facts with the wrong template keys or enum labels.

## Core Procedure

1. Read the prompt and `input/payloads/answer_template.json` before investigating.
2. Build an answer skeleton from the template:
   - Use every required key from the template.
   - Use only the listed enum values for enum fields.
   - Do not invent synonym keys, extra labels, or explanatory strings.
3. Read `environment_access.md` and replace any prompt URL like `127.0.0.1:<port>` with the provided remote base URL.
4. Use the console UI or app JSON endpoints to gather evidence. Helpful non-judge routes include:
   - `/api/cases` and `/api/cases/{case_id}`
   - `/api/employees?q=...`
   - `/api/recruitment?q=...`
   - `/api/payroll-ledgers?q=...`
   - `/api/documents?q=...`
   - `/api/messages?q=...`
   - `/api/audit?q=...`
   - `/api/policies` and `/api/policies/{policy_id}`
   - `/api/attachments/{attachment_id}`
5. Cross-check across the module named in the prompt and the case detail drawer. Case detail is useful for approvals, attachments, comments, audit events, and policy references.
6. Fill the exact template. Return JSON only when the prompt asks for JSON only.

## Template And Field Conventions

- Prefer exact identifiers from records: employee IDs, assignment IDs, audit IDs, message IDs, document IDs, offer IDs, batch IDs, and filenames.
- Keep ID arrays as IDs only. Do not add reasons or labels inside arrays unless the template explicitly asks for objects.
- Use booleans as JSON booleans, not strings.
- Use numbers as numbers for salary, days, and cost totals.
- Use filenames exactly as listed in folder checklists.
- For dates, prefer the explicit effective date when present. If only a timestamp supports the effective date, use the date part in `YYYY-MM-DD` form.
- If the template offers enum labels, copy one exactly. App display labels such as "Approved" or free-text audit summaries usually need to be converted to the template enum.
- Keep audit scope fields narrow. If the answer is about leave source precedence, do not let document/notice audit findings drive that field. If the answer is about folder or notice quality, do not let payroll or leave audit findings drive it.

## Source Precedence Rules

### Leave

- A current approved or submitted leave assignment is authoritative for the period when policy, ledger, and audit evidence support it.
- An approved assignment can override a stale employee profile summary.
- Exclude draft, voided, obsolete, superseded, or unrelated ledger rows from the effective leave answer.
- Employee profile summaries are useful for detecting mismatches, but they are lower authority than confirmed assignment history.
- Include supporting leave-scope audit events, and exclude adjacent document/notice audit events from leave-source decisions.

### Payroll

- The current submitted salary assignment controls payroll setup.
- Draft planning assignments do not control payroll readiness and should be explicitly excluded when the template asks for excluded assignments.
- Accrual readiness is supported by a submitted assignment matching the stated accrual batch and by payroll-readiness audit evidence.
- Use payroll-specific audit scope labels for salary assignment and accrual readiness fields.

### Recruiting

- Candidate outcomes should be based on committee/interview evidence plus the offer register, not case summary alone.
- A selected candidate needs accepted-offer confirmation before payroll/onboarding handoff.
- Waitlisted and rejected candidates should be handled by notice follow-up, not payroll handoff.
- Notice packet inspection controls missing waitlist/rejection notice actions.
- Recruiting cost total is the sum of all recruiting campaign cost ledger lines only. Do not include salaries or offer amounts.
- Draft payroll/precheck records do not satisfy a submitted handoff gate.

### Remote Work, Folders, And Notices

- Approval history can establish the decision, authority, and approval event, but approval alone is not sufficient for closeout when the folder or notice is defective.
- Folder readiness comes from the document checklist: all required files and required tags must be present.
- Missing required files and missing required tags are separate blockers.
- Formal notice quality comes from notice/message inspection and notice-scope audit evidence.
- Notice defects such as missing acknowledgement deadlines, missing appeal instructions, missing waitlist status, or wrong policy references should use the template's defect enum values.
- If folder or notice defects remain, use the template's hold/block/reissue labels rather than "approved" closeout labels.

## Audit Evidence Habits

- Query audit by the case ID, employee ID, and important record IDs.
- Use the case detail's audit list as a cross-check; it may include only the most relevant events.
- Put only decision-relevant audit IDs in supporting audit arrays.
- Put adjacent but out-of-scope events in excluded audit arrays when the template asks for exclusions.
- Adjacent exclusions commonly include:
  - Document/notice audit events when deciding leave source precedence.
  - Leave/payroll audit events when deciding folder or notice quality.
  - Events for another case, opening, employee, or candidate that mention similar defects.

## Common Pitfalls

- Missing the nested `input/payloads/answer_template.json` file and guessing the schema.
- Returning broad alias fields instead of the exact template keys.
- Using app display text or prose where the template requires lower_snake_case enum labels.
- Treating approved-with-conditions as closeout approval even when folder or notice blockers remain.
- Treating a stale profile summary as authoritative when an approved assignment and audit evidence contradict it.
- Including draft or superseded assignments as selected records.
- Adding explanations inside arrays that must contain IDs only.
- Counting offer salary as recruiting cost.
- Letting an audit event from a nearby case or different scope contaminate the current decision.

## Final JSON Checklist

Before returning the answer:

- Every key comes from the answer template.
- Every enum value is copied exactly from the template.
- IDs, filenames, dates, numbers, arrays, and booleans have the right JSON types.
- Source-precedence fields reflect authoritative records, not summaries or drafts.
- Exclusion fields contain the records or audit events the prompt asks to exclude.
- The final control or next action follows the unresolved blockers.
- The response contains only the JSON object unless the prompt explicitly asks for explanation.
