---
name: reflection-skill-task-group-012
description: Use this skill for PeopleOps Console reconciliation tasks that require answering JSON templates from local HR lifecycle evidence: employees, cases, leave/payroll ledgers, recruitment packets, documents, notices, policies, and audit events.
---

# PeopleOps Reconciliation SOP

## Access Pattern

Use only the exposed local app/API. Do not inspect environment source files.

Start with the prompt and `input/payloads/answer_template.json`. The template is authoritative for field names, types, and enum labels; return only matching JSON.

The front-end uses these API surfaces:

- `/api/employees?q=...`
- `/api/cases?q=...` and `/api/cases/{case_id}`
- `/api/payroll-ledgers?q=...`
- `/api/recruitment?q=...`
- `/api/documents?q=...`
- `/api/messages?q=...`
- `/api/policies/{policy_id}`
- `/api/audit?q=...` and `/api/audit/{audit_id}`
- `/api/attachments/{attachment_id}` when case attachments must be opened

Search by the most specific ID first: employee ID, case ID, opening ID, document ID, message ID, or audit ID. Then broaden once to the related case/employee/opening if the prompt asks for adjacent audit events, policy support, notices, or folder readiness.

## Evidence Priority

Always prefer submitted/approved operational records and inspection artifacts over summaries.

- Leave policy and annual/balance days: use the current approved or submitted leave assignment for the period. Exclude drafts, superseded rows, voided rows, and stale profile or case summaries. When an approved assignment conflicts with the employee profile, use `approved_assignment_over_profile` and set the profile ignored flag when requested.
- Payroll salary assignment: use the current submitted salary assignment. Exclude draft planning assignments. Use the submitted assignment's salary and, if no explicit effective-date field exists, the date component of the submitted assignment timestamp.
- Recruitment outcomes: use the recruitment packet's candidate review plus offer register. Committee decision identifies selected, waitlisted, and rejected candidates; accepted offer confirms the selected candidate.
- Folder readiness: compute missing files as `required_files - files`; compute missing tags as `required_tags - tags`. Folder is ready only when both are empty.
- Notice quality: use structured notice inspection evidence carrying `quality`, `defects`, `notice_packets`, or formal-notice inspection fields. Do not rely on a case summary alone when notice artifacts exist.
- Audit events: use audit detail only for the scope requested. Include supporting audit IDs for that scope and exclude adjacent events from other scopes when the template asks.

## Field And Label Rules

Use normalized enum labels exactly as the answer template spells them.

- Clean onboarding closeout with authoritative leave and submitted payroll: `approve_onboarding_close`, `approval_sufficient_when_records_clean`, `approve_closeout`.
- Approval is not sufficient when folder or notice defects remain: `approval_not_sufficient_when_folder_or_notice_defective`, `block_close_and_reissue_notice`, `hold_for_folder_and_notice_defects`.
- Leave precedence from approved current-period assignment: `approved_assignment_current_period`; audit scope is `leave_source_precedence_only`.
- Payroll readiness from submitted assignment and matching accrual evidence: `submitted`, `exclude_draft_assignment`, `payroll_assignment_readiness`, `ready_with_monitoring`.
- Document/notice review scope: `document_notice_findings_only`.
- Candidate arrays must contain candidate IDs only, not names.
- Recruitment cost total is the numeric sum of every cost ledger line for the opening.

## Recruitment Handoff Rules

Separate the action to create from the status that will eventually satisfy the gate.

- If the selected candidate has an accepted offer and no payroll precheck/handoff exists, `onboarding_handoff` is `create_payroll_precheck`.
- The required assignment status can still be `submitted_after_acceptance`, and the final handoff control can still be `submitted_handoff_required_after_acceptance`.
- `payroll_handoff_gate` is `accepted_offer_only` when acceptance is the trigger for creating the handoff.
- `draft_payroll_allowed` is false when policy says draft prechecks or assignments do not satisfy the gate.
- For a waitlisted candidate's offer exclusion reason, use `no_accepted_status_or_offer` when the candidate has no accepted offer or offer register entry. Use candidate outcome labels separately for waitlist/rejection follow-up actions.

## Notice And Folder Pitfalls

Do not choose `message_notice_inspection` just because the evidence was fetched from `/api/messages`. If the row is a structured formal-notice inspection with quality/defects, or the recruitment record has `notice_packets`, use `notice_packet_inspection`.

A present required tag means `folder_required_tag_action` is `no_tag_action` even if files are missing. Missing files still create `missing_required_files` and usually route records remediation to `Records`.

Notice defects should map directly to template defect labels, for example missing appeal language to `missing_appeal_instructions`. Reissue defective formal notices with `reissue_defective_notices`.

## Audit Scope Pitfalls

Do not mix leave, payroll, and document/notice audit events into the same scope decision.

- For leave source precedence, include leave mismatch/source-precedence audit events and exclude folder or notice events.
- For document/notice findings, include notice/folder QA events and leave `excluded_audit_event_ids` empty if no adjacent out-of-scope events are present.
- For payroll assignment readiness, use payroll readiness events that identify the submitted assignment and accrual batch.

## Final Answer Checklist

Before writing `answer.json`:

1. Verify every enum value exists in the template.
2. Verify IDs are copied exactly and arrays contain the requested ID type only.
3. Verify drafts and superseded records are excluded rather than selected.
4. Verify folder, notice, audit, and payroll/leave decisions use separate scopes.
5. Return a single JSON object with no markdown or explanatory text.
