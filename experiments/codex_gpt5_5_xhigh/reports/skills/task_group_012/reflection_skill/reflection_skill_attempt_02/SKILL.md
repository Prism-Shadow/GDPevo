---
name: peopleops-lifecycle-console
description: SOP for solving PeopleOps Console lifecycle tasks that require normalized JSON answers from the exposed local web/API. Use for task_group_012-style onboarding closeout, remote-work folder and notice readiness, recruitment reconciliation, leave source precedence, and payroll/accrual readiness tasks.
---

# PeopleOps Lifecycle Console SOP

## Environment Use

- Use only the exposed local app URL/API provided in the task. Do not inspect local environment source files.
- If the prompt shows `http://127.0.0.1:<port>/`, replace `<port>` with the provided port. Log in with the provided credentials if the UI prompts; the JSON API may already be readable.
- Query exact IDs first, then names if needed. Useful endpoints:
  - `/api/cases?q=...` and `/api/cases/{case_id}`
  - `/api/employees?q=...`
  - `/api/payroll-ledgers?q=...`
  - `/api/recruitment?q=...`
  - `/api/documents?q=...`
  - `/api/messages?q=...`
  - `/api/audit?q=...` and `/api/audit/{audit_id}`
  - `/api/policies` and `/api/policies/{policy_id}`
- Always read the answer template before deciding labels. Use template enum values exactly.

## Core Workflow

1. Identify the target employee, case, or opening from the prompt.
2. Pull all relevant modules, not just the summary row. Case detail carries approvals, attachments, and case-scoped audit events; module endpoints carry ledgers, folders, notices, policies, and recruitment registers.
3. Apply the business source hierarchy below. Do not let draft rows, stale summaries, or adjacent audit events override the controlling record.
4. Fill arrays with IDs only when the template asks for ID lists. Preserve numeric values as numbers, booleans as booleans, and dates in the format used by the controlling record or period start.
5. Before finalizing, verify every enum label is from the template and every required field is populated.

## Business Rules

### Leave and Onboarding

- The current approved or submitted leave assignment for the relevant period controls leave policy and annual/balance days.
- Exclude draft, superseded, voided, obsolete, or planning leave records even when they are newer or contain larger balances.
- Use `leave_assignment_history` when the answer comes from leave assignment/ledger records.
- Use `approved_assignment_current_period` for leave precedence when an approved/submitted current-period assignment controls.
- Employee profile summaries are fallback evidence only. If assignment, policy, and audit evidence show the profile is stale, set profile-stale fields accordingly and route to update the employee summary.
- For onboarding closeout, approve only when the controlling leave assignment and submitted payroll assignment are clean. Include excluded leave/payroll draft or superseded IDs.

### Payroll and Accrual Readiness

- Submitted salary assignments control payroll source, base salary, and accrual readiness.
- Draft payroll or salary planning records must be excluded; they do not satisfy payroll handoff or accrual gates.
- If an accrual batch ID appears on the submitted assignment and the audit detail confirms the assignment matches the batch, set accrual readiness to true and `ready_with_monitoring`.
- Use `payroll_assignment_readiness` for audit scope only when the audit event concerns payroll assignment/accrual readiness.
- For an effective date, prefer the explicit effective date; otherwise use the period start or submitted assignment timestamp date when the ledger only exposes a period/timestamp.

### Folder and Notice Readiness

- Approval history establishes the final decision and approval authority, but approval is not sufficient when folder or notice defects exist.
- A folder is ready only when all `required_files` are present in `files` and all `required_tags` are present in `tags`.
- Missing required files create `missing_required_files` blockers and normally route `escalation_action` to `open_records_remediation` with owner `Records`.
- Missing required tags create `missing_required_tags` blockers and require `add_required_tag`; if all required tags are present, use `no_tag_action`.
- Defective formal notices create `defective_formal_notice` blockers and require `reissue_defective_notices`.
- Keep `next_action` focused on the closeout result such as `block_close_and_reissue_notice`; keep `escalation_action` focused on records remediation when the folder is defective.
- Use `notice_packet_inspection` for formal notice quality source when inspecting the notice packet/formal notice evidence, even if the data is surfaced through the messages endpoint. Use `message_notice_inspection` only when the task is explicitly about message-only notice evidence.
- Use `document_notice_findings_only` for audit scope when the audit event supports folder or notice defects.

### Recruitment Reconciliation

- Determine candidate outcomes from committee/interview decision evidence, then confirm the selected candidate through the offer register.
- A selected candidate should have an accepted offer before payroll handoff begins. Waitlisted and rejected candidates belong only in their respective ID arrays.
- Sum every recruiting campaign cost ledger amount for `recruitment_cost_total`; do not use case summary estimates.
- Notice follow-up arrays contain candidate IDs whose notice packets require action, such as waitlist or rejection notices not sent.
- When an accepted offer exists but no payroll precheck/handoff record exists, set `onboarding_handoff` to `create_payroll_precheck`. Still set the payroll gate/status fields to require a submitted handoff after acceptance.
- Draft payroll is not allowed for recruitment handoff: use `draft_payroll_allowed: false` and `submitted_after_acceptance` where the template asks for the required status.
- For waitlisted candidates excluded from the selected offer, use `no_accepted_status_or_offer` when the reason is that they lack an accepted selected-offer status, even if their committee outcome is waitlisted.

## Field Label Patterns

- `approval_closeout_gate`: use `approval_sufficient_when_records_clean` only when the controlling records are clean; otherwise use `approval_not_sufficient_when_folder_or_notice_defective`.
- `final_control_result`: use `approve_closeout` for clean closeout, `hold_for_folder_and_notice_defects` for folder/notice blockers, and `ready_with_monitoring` for confirmed payroll/accrual readiness.
- `candidate_status_source`: use `interview_feedback_and_offer` when candidate review and offer register are both used.
- `candidate_outcome_control`: use `committee_decision_with_offer_confirmation` when committee decision plus offer status controls the selected outcome.
- `cost_source`: use `recruitment_cost_ledger` when summing ledger lines.
- `payroll_handoff_gate`: use `accepted_offer_only` when only the accepted selected offer should trigger handoff.
- `audit_scope`: choose the narrow scope of the evidence being used: leave precedence, document/notice findings, or payroll readiness. Put adjacent audit events from other scopes in `excluded_audit_event_ids`.

## Common Pitfalls

- Do not treat a clean approval as enough to close a case if required folder files/tags or formal notice fields are defective.
- Do not choose a newer draft assignment over a submitted/approved assignment.
- Do not let unrelated folder or notice audit events contaminate leave-precedence answers; exclude them explicitly.
- Do not answer recruitment handoff as a submitted assignment creation action when the immediate missing artifact is the payroll precheck/handoff record; the submitted-after-acceptance requirement belongs in the gate/status fields.
- Do not use `waitlisted_not_selected` for offer exclusion when the normalized reason expected by the template is absence of accepted offer status.
