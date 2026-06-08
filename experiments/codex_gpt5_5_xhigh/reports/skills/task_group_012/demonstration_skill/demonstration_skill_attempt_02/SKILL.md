---
name: northwind-peopleops-verification
description: Execute Northwind PeopleOps Console verification tasks involving onboarding closeout, leave source precedence, payroll assignment readiness, policy-case folder and notice controls, and recruitment reconciliation. Use when a task asks Codex to inspect the local PeopleOps web/API environment and return normalized JSON matching an answer_template.
---

# Northwind PeopleOps Verification

## Core SOP

1. Read the task prompt and `input/payloads/answer_template.json` first. Extract the target IDs, required modules, field names, and every enum `allowed_values`; final JSON must use those labels exactly.
2. Query the local app by ID, not by broad browsing. Prefer the structured API over manual UI inspection, then use case/audit detail endpoints for evidence that list endpoints omit.
3. Decide authoritative records from source status and scope. Exclude drafts, superseded/obsolete records, and adjacent out-of-scope audit events even when they are newer or easier to find.
4. Fill every template field with the narrowest supported value. Use empty arrays for no evidence, booleans for actual computed state, numbers without commas, and JSON only.
5. Before finalizing, check that every enum value appears in the template and that each list contains the requested item type only, such as candidate IDs only or filenames only.

## Environment Use

Use the port from the task prompt:

```bash
BASE=http://127.0.0.1:<port>
curl --noproxy '*' -sS "$BASE/health"
```

The browser UI has left-nav modules for Dashboard, Employees, Recruitment, Leave, Payroll, Policy Cases, Documents, Messages, and Audit Log. If the UI prompts for login, use the provided PeopleOps credentials. In this environment the frontend API usually returns JSON directly and is faster than UI clicking.

Useful API patterns:

- `GET /api/employees?q=<employee_id_or_name>`: employee profile summary. Treat as corroborating evidence unless the task/template says profile summary is authoritative.
- `GET /api/payroll-ledgers?q=<employee_id>`: leave assignments, salary assignments, payroll/accrual evidence. Filter by `record_type`, `status`, `period`, and IDs.
- `GET /api/cases?q=<case_id_or_employee_id>`: case queue summary.
- `GET /api/cases/<case_id>`: approvals, attachments/checklists, comments, case audit events, policy refs.
- `GET /api/documents?q=<case_id_or_employee_id>`: folder readiness, files, required files, tags, required tags.
- `GET /api/messages?q=<case_id_or_candidate_or_opening>`: formal notices, message status, quality, body, defects.
- `GET /api/audit?q=<entity_id>` and `GET /api/audit/<audit_id>`: audit events and details.
- `GET /api/policies?q=<keyword>` or `/api/policies/<policy_id>`: source-precedence and control policies.
- `GET /api/recruitment?q=<opening_id>`: candidates, committee decisions, offer register, cost ledger, notice packets, payroll precheck/handoff records. Related recruitment cases are often available as `/api/cases/<opening_id>`.

Make HTTP requests sequentially. If a localhost request briefly returns connection refused, run `/health` and retry the same targeted request instead of changing strategy.

## Business Rules

### Leave Source Precedence

- The authoritative leave policy/days come from the current-period leave assignment ledger when an assignment is `Approved` or otherwise submitted/approved as a final source. Use the assignment `ledger_id` as the assignment ID.
- Draft, voided, obsolete, and superseded leave assignments are exclusions. Include their IDs in `excluded_leave_ids` or equivalent fields when the template asks.
- An approved current-period assignment overrides a stale employee profile summary. Use profile values only when no controlling assignment exists or when the template/evidence explicitly makes the profile current.
- Use assignment fields for leave days (`approved_leave_days`, annual entitlement, or balance as requested), not draft worksheet values. Treat profile balance as corroboration, not precedence.
- For leave audit questions, choose audit events whose detail is about leave source/profile mismatch. Put document, folder, or notice events in `excluded_audit_event_ids` when the prompt asks to exclude adjacent events.
- Common normalized labels:
  - `leave_source`: `leave_assignment_history` when the ledger assignment controls; `employee_profile_summary` only when the profile is the current source; `case_summary_only` only when no record evidence is available.
  - `precedence_source`: `approved_assignment_over_profile` when approved assignment conflicts with profile.
  - `leave_precedence_source`: `approved_assignment_current_period` for a current approved assignment; `profile_summary_current_period` only for current profile source.
  - `audit_scope`: `leave_source_precedence_only` for leave-source decisions.

### Payroll And Accrual Readiness

- Current submitted salary assignment controls base salary and payroll readiness. Use the submitted salary assignment ID and salary; exclude draft and superseded salary assignments.
- Draft planning payroll records never satisfy payroll readiness, closeout, accrual, or recruitment handoff gates.
- If the template asks for `effective_date` and the salary record has a period plus timestamp rather than a separate effective date, use the effective period start date when supported by the record.
- Accrual readiness requires submitted payroll assignment evidence plus an accrual batch/readiness signal or payroll-readiness audit evidence. Use `ready_with_monitoring` only for monitoring-ready states, not for case close approval.
- Common normalized labels:
  - `payroll_source_status`: `submitted` for the selected salary assignment; `draft` or `superseded` only when the selected source really has that status.
  - `draft_exclusion_rule`: `exclude_draft_assignment` when drafts are excluded.
  - `audit_scope`: `payroll_assignment_readiness` for payroll/accrual evidence.
  - `draft_payroll_allowed`: usually `false` unless the template or policy explicitly allows drafts.

### Folder, Notice, And Closeout Controls

- Approval history determines the approval decision and authority, but approval alone is not enough to close if required folder files/tags or formal notices are defective.
- Folder readiness is true only when every `required_files` item is present in `files` and every `required_tags` item is present in `tags`. Missing files/tags are blockers.
- Formal notice quality comes from notice packet/message inspection and audit details, not just case status. Map defects to template enum values such as `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, or `missing_correct_policy`.
- If folder or notice defects exist, use hold/block labels such as `block_close_and_reissue_notice`, `approval_not_sufficient_when_folder_or_notice_defective`, `hold_for_folder_and_notice_defects`, and include the relevant `closeout_blockers`.
- If all authoritative records are clean, approval-close labels should be the sufficient/approve variants from the template, not remediation labels.
- Set `folder_required_tag_action` to `add_required_tag` only when a required tag is missing; otherwise use `no_tag_action`.
- Use `notice_remediation_action: reissue_defective_notices` when a formal notice is defective; use `no_notice_action` only when the notice is valid or no notice action is required.
- For document/notice audit decisions, choose audit events about folder or notice findings and exclude leave/payroll audit events if the template asks.

### Recruitment Reconciliation

- Candidate outcomes should come from committee/interview decision evidence plus offer register confirmation. Do not rely on message status alone when committee/offer evidence exists.
- `selected_candidate` requires a selected committee decision and an accepted offer when the template asks for final outcome. Waitlisted and rejected arrays contain candidate IDs only.
- `offer_id`, selected offer status, and offer salary come from the accepted offer register, not from case summaries or messages.
- `recruitment_cost_total` is the sum of all recruiting campaign cost-ledger `amount` lines. Do not omit small chargeback/screening lines.
- `notice_followup_required` should include waitlisted/rejected candidates whose notice packet says not sent, defective, or requires a send/reissue action. Do not include the accepted selected candidate unless the packet requires a notice follow-up.
- Recruiting payroll handoff is gated by an accepted selected offer. The handoff/precheck must be submitted; draft handoffs do not satisfy the gate.
- If there is an accepted selected offer but no submitted handoff/precheck, use the template's create/submitted-after-acceptance labels, such as `create_payroll_precheck`, `submitted_after_acceptance`, and `submitted_handoff_required_after_acceptance` when those values are allowed.
- Common normalized labels:
  - `candidate_status_source`: `interview_feedback_and_offer` when candidate review and offer register are available.
  - `candidate_outcome_control`: `committee_decision_with_offer_confirmation` when committee decision and accepted offer align.
  - `cost_source`: `recruitment_cost_ledger` when summing cost lines.
  - `notice_quality_source`: `notice_packet_inspection` when notice packet records show follow-up.
  - `payroll_handoff_gate`: `accepted_offer_only` unless the template/evidence requires a submitted assignment gate.

## Field Normalization

- Use exact IDs from records: employee IDs, case IDs, assignment/ledger IDs, offer IDs, candidate IDs, message IDs, audit IDs, batch IDs, and document filenames.
- `excluded_*` fields should contain records actively considered and rejected because they are draft, superseded, obsolete, voided, non-current, or outside the requested audit scope.
- `supporting_audit_event_ids` contains only audit events supporting the requested decision. `excluded_audit_event_ids` contains adjacent events that are real but irrelevant to that decision.
- `audit_event_id` should be the primary event supporting the answer; when multiple events support the decision, also populate `supporting_audit_event_ids` if present in the template.
- `approval_event_id` and `approval_authority` come from case approval history, not comments or notice messages.
- `folder_ready`, `required_tag_present`, `accrual_ready`, and similar booleans must be computed from evidence, not copied from a high-level case status unless no lower-level evidence exists.
- For status/source/gate/control fields, never invent prose. Select one of the template enum labels even if several labels sound similar.

## Common Pitfalls

- Do not let a newer draft override an older approved/submitted record.
- Do not use employee profile leave policy when an approved assignment and audit/policy evidence say the profile is stale.
- Do not treat an approval as closeout-ready when a folder checklist or formal notice is defective.
- Do not count out-of-scope audit events as support. Leave audits, payroll audits, and document/notice audits answer different questions.
- Do not include names in candidate arrays when the prompt says arrays must contain candidate IDs only.
- Do not forget small recruitment cost ledger lines; sum every line under the opening.
- Do not use case summary alone when the task points to ledgers, policy viewer, notice packets, or audit detail.
- Do not return markdown, comments, trailing commas, or fields absent from the template.
