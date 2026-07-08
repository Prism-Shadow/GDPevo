---
name: peopleops-lifecycle-reconciliation
description: Use this skill for PeopleOps Console tasks that ask Codex to reconcile HR lifecycle records across employees, cases, leave, payroll, recruitment, documents, messages, policies, and audit evidence. Trigger whenever the task mentions onboarding closeout, leave source precedence, payroll assignment readiness, accrual readiness, remote-work exception closeout, folder readiness, formal notices, recruitment reconciliation, candidate outcomes, or normalized PeopleOps answer templates.
---

# PeopleOps Lifecycle Reconciliation

Use this skill to produce JSON answers for PeopleOps Console reconciliation tasks. The recurring challenge is not finding one record; it is choosing the authoritative record when summaries, drafts, notices, folders, and audit events disagree.

## Operating Procedure

1. Read the prompt and the answer template first.
   - Treat the template as the schema of record.
   - Copy enum values exactly from the template; do not invent synonyms.
   - Keep arrays in the requested shape. If the prompt says candidate arrays contain IDs only, do not include names or explanations.

2. Open the environment using the provided remote base URL.
   - If the prompt shows `127.0.0.1:<port>`, replace it with the remote base URL from the environment access file.
   - The UI is useful for orientation, but the underlying JSON endpoints are the fastest way to verify records.
   - Query narrow terms first: employee ID, case ID, opening ID, document ID, message ID, and audit ID.

3. Gather all relevant modules before answering.
   - Employee/profile summary: `/api/employees?q=...`
   - Case summary and detail: `/api/cases?q=...` and `/api/cases/{case_id}`
   - Leave and payroll rows: `/api/payroll-ledgers?q=...`
   - Recruitment packet: `/api/recruitment?q=...`
   - Documents/folder checklist: `/api/documents?q=...`
   - Messages/formal notices: `/api/messages?q=...`
   - Audit list and detail: `/api/audit?q=...` and `/api/audit/{audit_id}`
   - Policy text: `/api/policies/{policy_id}`

4. Resolve the authoritative source, then fill the JSON.
   - Use policy documents to decide source precedence.
   - Use detail records and inspections over list summaries.
   - Use audit detail to confirm the scope of the finding.
   - Exclude drafts, superseded records, stale summaries, and adjacent audit events outside the requested scope.

5. Validate the final answer mechanically.
   - Ensure every field from the template is present.
   - Ensure booleans are booleans, numbers are numbers, and list fields are lists.
   - Ensure enum fields use exact allowed strings.
   - Return only JSON when the prompt asks for only JSON.

## Source Precedence

### Leave

Use the current approved or submitted leave assignment for the effective period when policy says assignment records control. Employee profile summaries can be stale, even when they show a leave balance that looks plausible.

Prefer:
- Approved/submitted leave assignment for the relevant period.
- Audit event whose scope is leave source precedence.
- Policy text stating assignment source precedence.

Exclude:
- Draft, voided, obsolete, or superseded leave records.
- Employee profile policy/balance when audit or policy says the profile summary is stale.
- Folder/document audit events when the task asks only for leave-source scope.

Common labels:
- `precedence_source`: `approved_assignment_over_profile`
- `leave_precedence_source`: `approved_assignment_current_period`
- `audit_scope`: `leave_source_precedence_only`
- `audit_result`: `profile_summary_stale`
- `next_action`: `update_employee_summary` when the profile needs correction

### Payroll and Accrual Readiness

Use the current submitted salary assignment for payroll readiness and accrual checks. Draft planning rows do not change base salary, readiness, or accrual status.

Prefer:
- Submitted salary assignment.
- Accrual batch ID on the submitted payroll row or confirmed in payroll audit detail.
- Payroll policy text that says submitted assignment controls.

Exclude:
- Draft salary assignments, even if the salary or date is newer.
- Superseded rows unless the prompt specifically asks about history.
- Document/notice or leave audit events when the task asks for payroll readiness.

Common labels:
- `payroll_source_status`: `submitted`
- `draft_exclusion_rule`: `exclude_draft_assignment`
- `audit_scope`: `payroll_assignment_readiness`
- `control_result`: `ready_with_monitoring` when audit confirms readiness but monitoring remains

Effective date convention:
- If a salary row has a period and an update timestamp, use the business effective date implied by the assignment period or hire/effective date, not necessarily the full update timestamp.

### Recruitment

Reconcile recruitment from the recruitment workspace, not from case summary alone. Candidate outcomes come from committee decisions and offer status; costs come from the cost ledger; notices come from notice packets or message inspection.

Prefer:
- Candidate review for selected, waitlisted, and rejected status.
- Offer register for selected candidate, offer ID, accepted/draft/withdrawn status, and salary.
- Cost ledger for `recruitment_cost_total`; sum every campaign ledger line.
- Notice packets for required waitlist or rejection follow-up when present.
- Payroll policy for handoff gates.

Exclude:
- Waitlisted or rejected candidates from selected-offer payroll handoff.
- Draft payroll prechecks as satisfying payroll handoff.
- Message-only status when candidate review and offer register are available.

Common labels:
- `candidate_status_source`: `interview_feedback_and_offer`
- `candidate_outcome_control`: `committee_decision_with_offer_confirmation`
- `cost_source`: `recruitment_cost_ledger`
- `notice_quality_source`: `notice_packet_inspection` when notice packets are present
- `payroll_handoff_gate`: use the template label that best captures accepted-offer gating; check whether the task asks for offer-only gating or submitted-assignment readiness
- `draft_payroll_allowed`: `false` when policy says drafts do not satisfy the gate

Recruitment pitfalls:
- `notice_followup_required` should include candidate IDs only, not notice IDs.
- Waitlist and rejection follow-up actions are different; do not reissue a notice that was never sent unless the record says the existing notice is defective.
- If an accepted offer exists but no submitted handoff exists, distinguish the action to create a handoff from the control result that a submitted handoff is required.

### Folder and Formal Notice Readiness

Approvals alone do not clear a lifecycle closeout when folder or notice evidence is defective. Always inspect folder checklist and notice/message detail.

Prefer:
- Approval history for decision and approver.
- Folder checklist for required files, filed files, required tags, and current tags.
- Notice packet or message inspection for notice quality and defects.
- Audit event whose detail matches document/notice findings.

Exclude:
- Leave-source or payroll-readiness audit events from a document/notice decision.
- Adjacent audit events for other cases or scopes unless the prompt asks for cross-module escalation.
- Case summary optimism when checklist or notice detail shows defects.

Common labels:
- `approval_closeout_gate`: `approval_not_sufficient_when_folder_or_notice_defective`
- `audit_scope`: `document_notice_findings_only`
- `evidence_source_order`: usually `approval_history_folder_notice_audit` when approval plus folder/notice/audit are all requested
- `folder_required_tag_action`: `add_required_tag` only when the required tag is missing; otherwise `no_tag_action`
- `notice_remediation_action`: `reissue_defective_notices` for defective sent/draft notices
- `final_control_result`: `hold_for_folder_and_notice_defects` when required files/tags or formal notice quality fail

Folder checklist rules:
- `folder_ready` is false if any required file or required tag is missing.
- Put only missing required files in `missing_files`.
- Set `required_tag_present` from checklist tags, not from case tags or policy title.

Notice rules:
- Use defect codes from message or notice packet records when available.
- Do not infer extra defects from policy text if the inspected notice record lists a narrower defect set.
- Use `message_notice_inspection` for ordinary formal messages; use `notice_packet_inspection` for recruitment notice packets.

## Audit Scope Habits

Audit events are scoped evidence, not a general truth source. Match the audit event to the business question:

- Leave precedence: `leave_source_precedence_only`
- Payroll readiness: `payroll_assignment_readiness`
- Folder and notice findings: `document_notice_findings_only`

Populate `supporting_audit_event_ids` with events that directly support the requested scope. Populate `excluded_audit_event_ids` with nearby or same-case events that are real but outside scope, such as a folder/tag audit excluded from a leave-precedence answer.

When uncertain about adjacent audit exclusions, inspect both case detail and the all-audit list. Prefer excluding events that are explicitly adjacent and same case but different scope. Be cautious about sweeping in unrelated cases unless the prompt asks for cross-module or package-level review.

## Final JSON Conventions

- Use exact IDs from source records.
- Use exact policy, assignment, offer, batch, document, message, and audit IDs.
- Use integers for day balances when the template expects integer days.
- Use plain `YYYY-MM-DD` dates when the answer asks for an effective date rather than an update timestamp.
- Preserve list order from the relevant source record unless the prompt implies another order.
- Empty arrays are acceptable only when the inspected source genuinely has no applicable records.

## Common Pitfalls

- Do not approve closeout just because an approval exists; folder and notice defects can still block.
- Do not use employee profile summaries when policy and audit say assignment history controls.
- Do not use draft salary assignments for payroll readiness.
- Do not use superseded leave or payroll rows as current evidence.
- Do not let case summaries override detailed records, checklists, notice packets, or audit detail.
- Do not mix audit scopes. A correct audit ID in the wrong scope can corrupt normalized fields.
- Do not include explanatory prose in JSON-only tasks.
