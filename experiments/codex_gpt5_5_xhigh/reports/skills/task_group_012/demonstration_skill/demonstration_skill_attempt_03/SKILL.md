---
name: task-group-012-fewshot-attempt-03
description: Use for Northwind PeopleOps Console tasks that require reconciling HR lifecycle records, leave/payroll source precedence, recruitment outcomes, folder/notice readiness, audit evidence, and writing evaluator-ready answer.json files from a provided answer_template.json.
---

# Northwind PeopleOps Console SOP

Use this skill when solving local PeopleOps Console tasks against the provided web/API URL. The job is evidence reconciliation, not workflow execution: inspect records, apply source-precedence rules, and return only JSON matching the task's `answer_template.json`.

## First pass

1. Read the task prompt and `input/payloads/answer_template.json` before using the app. Treat the template as the contract for keys, types, and exact enum strings.
2. Identify the target kind:
   - Employee/person task: employee ID such as `EMP-*`, often involving leave, payroll, onboarding, or profile summary conflicts.
   - Policy case task: case ID such as `CASE-*`, involving approvals, folders, notices, attachments, and audit.
   - Recruitment task: opening ID such as `REQ-*`, involving candidates, offers, cost ledgers, notice packets, and payroll handoff.
3. Open the provided URL. If a login screen appears, use `ops.lead@peopleops.local` / `PeopleOps#2026`; some local runs may already expose the console without auth.
4. Prefer direct API reads for completeness, using the UI to cross-check when helpful. Do not post comments or record actions unless the prompt explicitly asks.
5. Build a field-by-field evidence table before writing JSON: selected source, excluded source, policy rule, audit support, final control/action.

## API and UI Map

The same data is available through modules in the sidebar and JSON endpoints:

- Health: `GET /health`
- Employees: `GET /api/employees?q=<employee_id_or_name>`
- Cases list/detail: `GET /api/cases?q=<id_or_name>` and `GET /api/cases/<case_id_or_opening_id>`
- Leave and payroll ledgers: `GET /api/payroll-ledgers?q=<employee_id_or_name>` plus optional `status=<Submitted|Approved|Draft|Superseded>`
- Recruitment: `GET /api/recruitment?q=<opening_id>`
- Documents/folder checklist: `GET /api/documents?q=<case_id_or_document_id>`
- Messages/formal notices: `GET /api/messages?q=<case_id_or_message_id>`
- Audit list/detail: `GET /api/audit?q=<employee_id_or_case_id_or_opening_id>` and `GET /api/audit/<audit_id>`
- Policies: `GET /api/policies?q=<term>` and `GET /api/policies/<policy_id>`
- Attachments: `GET /api/attachments/<attachment_id>`

In the UI, use Policy Cases for overview/approvals/comments/attachments/audit detail, Documents for required files/tags, Messages for formal notice quality, Payroll for salary assignments and accrual data, Leave for leave assignments, Recruitment for candidate/offer/cost/notice panels, and Audit Log for evidence scope.

Search results can contain noisy neighboring records. Filter by exact employee/case/opening ID, record type, status, and period before selecting a source.

## Source Rules

### Leave

- The current approved or submitted leave assignment for the relevant period controls leave entitlement.
- Draft, voided, obsolete, and superseded leave records are excluded even if they are newer or have larger days.
- Employee profile summaries are secondary. If the approved/submitted assignment, policy, and audit show the profile is stale, set profile-ignored fields accordingly.
- Use assignment fields such as `policy_name`, `approved_leave_days`, `ledger_id`, `period`, and `status`. Do not choose unrelated HRMS ledger or adjustment rows when the task asks for the authoritative assignment.
- Common normalized labels:
  - Source: `leave_assignment_history` when assignment history is authoritative; `employee_profile_summary` only when no stronger current assignment controls; `case_summary_only` only when no direct records exist.
  - Precedence: `approved_assignment_current_period` or `approved_assignment_over_profile` when a current approved assignment overrides profile summary.
  - Audit scope: `leave_source_precedence_only`.

### Payroll and Accrual

- Current submitted salary assignment controls base salary, effective period/date, and payroll readiness.
- Draft planning assignments do not satisfy payroll readiness and should be listed in exclusion fields when the template asks.
- Superseded records are historical unless the prompt specifically asks for history.
- Accrual readiness normally requires a submitted salary assignment plus matching audit evidence. If a salary assignment row includes `accrual_batch_id`, verify it against a payroll readiness audit detail.
- For dates, use the API value or infer the first day of the assignment period only when the template expects an effective date and the record has no separate date field.
- Common normalized labels:
  - Payroll source/status: `submitted`, `draft`, `superseded`.
  - Draft rule: `exclude_draft_assignment`.
  - Audit scope: `payroll_assignment_readiness`.
  - Clean submitted payroll with monitoring audit: `ready_with_monitoring`.

### Case Folder and Notice Readiness

- A final approval does not make a case closable if required folder evidence or formal notices are defective.
- Folder readiness requires every `required_files` item to be present in `files` and every `required_tags` item to be present in `tags`.
- Missing files map to `missing_required_files`; missing tags map to `missing_required_tags` and often `add_required_tag`.
- Inspect message/notice records and notice packets for `quality`, `defects`, and required action. Do not rely only on case summary text.
- Common notice defects include `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, and `missing_correct_policy`; use only values present in the template.
- Common normalized labels:
  - Folder/notice evidence order: `approval_history_folder_notice_audit` when approvals, folder checklist, notices, and audit are all used.
  - Notice source: `notice_packet_inspection` for packet records; `message_notice_inspection` for message body/inspection.
  - Gate: `approval_not_sufficient_when_folder_or_notice_defective` if any folder/notice requirement fails; `approval_sufficient_when_records_clean` when all required evidence is clean.
  - Remediation/action: `block_close_and_reissue_notice`, `open_records_remediation`, `reissue_defective_notices`, `no_notice_action`.
  - Owner: usually the exact enum from the template, such as `Records`, `People Ops Compliance`, or `Payroll QA`.
  - Audit scope: `document_notice_findings_only`.

### Recruitment

- Use the recruitment opening record for candidate decisions, offer register, cost ledger, notice packets, and payroll precheck records.
- Candidate outcome arrays contain candidate IDs only.
- Select the candidate with a selected/accepted-offer outcome supported by the offer register. Waitlisted and rejected candidates are not selected, even if they remain in final committee records.
- `recruitment_cost_total` is the sum of all cost ledger line amounts, not a count or summary estimate.
- Notice follow-up is required for candidates whose notice packet says a waitlist/rejection notice is not sent, defective, or requires action.
- Payroll handoff is only for the selected candidate after an accepted offer. A draft precheck/assignment is not sufficient.
- Common normalized labels:
  - Status source: `interview_feedback_and_offer`.
  - Outcome control: `committee_decision_with_offer_confirmation`.
  - Cost source: `recruitment_cost_ledger`.
  - Payroll gate: `accepted_offer_only` or, if the template requires assignment status, `accepted_offer_and_submitted_assignment`.
  - Required status: `submitted_after_acceptance`; `draft_payroll_allowed` is usually `false`.
  - Handoff result: `submitted_handoff_required_after_acceptance` when accepted offer exists but submitted handoff/precheck must be created.

## Audit Handling

- Use audit detail records as corroboration, not as replacements for source records.
- Include only audit event IDs that support the requested scope.
- Exclude adjacent audit events from other scopes when the template has `excluded_audit_event_ids`; for example, folder/notice audit events do not support a leave-precedence decision.
- Match common event themes:
  - `leave.*` or detail mentioning profile mismatch/assignment control -> leave source precedence.
  - `payroll.*` or detail mentioning submitted salary assignment/accrual batch -> payroll readiness.
  - `notice.*`, `folder.*`, or document/tag/file detail -> document/notice findings.
- When a task asks for both a primary `audit_event_id` and `supporting_audit_event_ids`, use the strongest same-scope event as primary and include it in supporting IDs unless the template examples or prompt imply otherwise.

## Output Field Guidance

- Return exactly one JSON object. No markdown, comments, or explanatory text.
- Preserve every key from the template and do not add keys.
- Use exact enum strings from the template; never invent natural-language labels.
- Preserve identifier casing exactly as shown in records.
- Use JSON booleans and numbers, not strings. Salaries and totals should be numeric without commas.
- Use empty arrays when no records apply; do not omit array fields.
- Exclusion fields should contain the IDs of records excluded by the business rule, not explanations.
- Candidate arrays should contain candidate IDs only.
- Missing-file fields should contain filenames exactly as shown in `required_files`.
- Effective dates should be strings in the task/API format, commonly `YYYY-MM-DD`.

## Final Control Mapping

Use the template's enum values, but these mappings are common:

- Records clean and required submitted/approved sources are present -> `approve_closeout` or `approve_onboarding_close`.
- Folder files/tags or formal notice defects remain -> `hold_for_folder_and_notice_defects` and usually `block_close_and_reissue_notice`.
- Source records are incomplete or stale records need correction -> `open_records_remediation`.
- Submitted payroll assignment plus matching readiness audit, with no blocking defect -> `ready_with_monitoring`.
- Accepted recruitment offer without required submitted handoff/precheck -> create the payroll precheck/submitted assignment action specified by the template.

## Common Pitfalls

- Do not choose a Draft row just because it is newest or has a higher salary/days value.
- Do not use employee profile leave balance as authoritative when an approved/submitted assignment for the period controls.
- Do not treat a case approval event as sufficient if folder checklist or formal notice quality fails.
- Do not mix audit scopes; document/notice audits are exclusions for leave-only decisions, and leave audits are exclusions for notice/folder decisions.
- Do not use case summary text as the source when direct ledgers, folder checklists, notice packets, offer registers, policies, or audit details are available.
- Do not forget required tags when deciding folder readiness; files alone are not enough.
- Do not compute recruitment cost from selected candidate or offer data; sum all cost ledger lines.
- Do not include candidate names in candidate arrays.
- Do not include free-text explanations in normalized fields such as source, gate, remediation, scope, final result, or owner.
