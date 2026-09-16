---
name: peopleops-console-controls
description: Solve PeopleOps Console verification and reconciliation tasks that require collecting HR case, employee, leave, payroll, recruitment, document, message, policy, and audit evidence from the task environment, applying source-precedence and draft-exclusion rules, and returning strict JSON matching an answer template.
---

# PeopleOps Console Controls

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. The template is the output contract: preserve every key, use the declared scalar types, and use only the listed enum labels.
2. Extract target identifiers from the prompt, such as employee IDs, case IDs, opening IDs, candidate IDs, payroll or leave assignment IDs, policy IDs, audit IDs, attachment IDs, and relevant periods.
3. Gather evidence from the task environment before answering. Prefer API data over UI reading when available because the records are structured. Use the UI only as a cross-check or when the prompt requires it.
4. Build a short evidence table for yourself with: source endpoint, record ID, status, period/effective date, scope, and why the record is included or excluded.
5. Apply the precedence and exclusion rules below. Do not use case summaries, employee profile summaries, messages, or notifications as authoritative when assignment, ledger, folder, policy, offer, or audit detail exists for the same field.
6. Emit only the final JSON object. Do not include markdown, comments, citations, or explanatory fields.

## Evidence Collection

Use `scripts/peopleops_collect.py` to collect a filtered evidence bundle:

```bash
python3 skill/scripts/peopleops_collect.py --base-url "$TASK_ENV_BASE_URL" --employee-id "$EMPLOYEE_ID" --case-id "$CASE_ID" --opening-id "$OPENING_ID"
```

Omit identifiers that are not part of the prompt. If the script path differs after installation, run it from the skill directory or adjust the relative path. The script uses only Python standard-library modules and permitted GET endpoints.

If collecting manually, use these endpoint roles:

- `/api/manifest` and `/api/summary`: module inventory and broad counts only.
- `/api/employees`: employee profile summary and current profile balance; lower precedence than confirmed assignment or ledger records.
- `/api/cases` and `/api/cases/{case_id}`: case metadata, approvals, folder attachments, comments, policy references, and case-scoped audit snippets.
- `/api/policies` and `/api/policies/{policy_id}`: authoritative control rules for leave precedence, payroll source, folder readiness, and handoff gates.
- `/api/payroll-ledgers`: leave assignments, leave ledgers, salary assignments, payroll worksheets, and accrual batch fields. Filter by target employee and period.
- `/api/recruitment`: opening-specific candidates, committee outcomes, offers, costs, notices, and payroll prechecks.
- `/api/documents`, `/api/messages`, `/api/notifications`, `/api/audit`, `/api/audit/{audit_id}`, and `/api/attachments/{attachment_id}`: supporting folder, notice, message, and audit evidence.

## Source Rules

Apply these rules unless the current prompt or active policy record explicitly says otherwise:

- Leave policy and leave days: use the latest approved or submitted leave assignment for the requested period. Exclude draft, voided, obsolete, and superseded leave records. Employee profile leave fields are fallback or stale-profile evidence, not controlling evidence, when an approved/submitted assignment is confirmed by ledger, policy, or audit detail.
- Payroll and salary: use the current submitted salary or payroll assignment. Exclude draft planning assignments from salary, readiness, and accrual decisions. Superseded assignments may be listed as excluded when the template asks.
- Accrual readiness: use submitted payroll assignment evidence plus accrual batch and payroll-readiness audit scope. Draft assignments do not make an accrual batch ready.
- Case approval: final approval or approved-with-conditions status is not enough to close a case if required folder files, required tags, or formal notice quality fail.
- Folder readiness: compare required files and tags with present files and tags from case attachments, folder/document records, and the relevant policy. Missing required files or tags are blockers.
- Notice quality: inspect notice packets, attachment content, messages, and notification defects. Map defects to the template enum labels exactly; common checks include missing acknowledgement deadline, appeal instructions, waitlist status, or correct policy reference.
- Recruitment outcome: select the candidate with a committee selection and accepted offer. Waitlisted and rejected arrays contain candidate IDs only. Sum every recruiting campaign cost ledger line requested by the prompt. Payroll handoff is for the selected accepted offer only, and draft prechecks do not satisfy a submitted handoff gate.
- Audit scope: include audit events that directly support the requested control area. Exclude adjacent audit events for other scopes even if they share the same employee or case.

## Template Mapping

Use the answer template as the source of truth for exact labels. Choose labels by control outcome, not by free-text paraphrase:

- Source labels should identify where the controlling evidence came from, such as assignment history, profile summary fallback, case summary fallback, folder/notice audit, notice packet inspection, recruitment cost ledger, or submitted payroll source.
- Gate labels should reflect the business rule applied, such as approval being sufficient only when records are clean, accepted-offer-only payroll handoff, or submitted-assignment requirement.
- Scope labels should match the evidence scope actually reviewed: leave-source precedence, document/notice findings, or payroll assignment readiness.
- Final-result labels should summarize the control result: approve when all required records are clean, hold/block when folder or notice defects remain, and ready-with-monitoring when readiness is established but monitoring is still the control state.

Before finalizing, verify:

- Every required template key is present exactly once.
- Enum values are copied exactly from `allowed_values`.
- IDs and numbers come from authoritative records, not summaries, unless the template or prompt allows summary fallback.
- Excluded-record arrays contain only records actually considered and rejected by the stated rule.
- Candidate arrays contain candidate IDs only when the prompt asks for recruitment outcomes.
- The response parses as JSON and contains no extra text.
