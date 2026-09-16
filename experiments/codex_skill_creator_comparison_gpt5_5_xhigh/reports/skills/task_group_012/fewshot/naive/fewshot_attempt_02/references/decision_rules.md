# PeopleOps Decision Rules

These rules summarize reusable evidence precedence for PeopleOps Console JSON tasks. They are not a substitute for the task's `answer_template.json`; always use the template's exact keys and enum labels.

## Source Precedence

Prefer authoritative operational records over summaries:

1. Assignment history, offer registers, folder checklists, notice packets, audit details, and policy text.
2. Employee profile summaries and case summaries.
3. Free-text comments or messages, only when they are the only direct evidence for a requested field.

Use case summaries to find the right entity, not to override detailed records. Treat draft, obsolete, superseded, or placeholder records as exclusions unless the prompt explicitly asks to report them.

## Leave Setup

For leave questions:

- Select the current-period leave assignment whose status is approved or submitted.
- Exclude draft, voided, obsolete, or superseded leave assignments from the effective policy and days.
- Use the assignment id from the selected leave record.
- Use assignment fields such as policy name and approved leave days for effective policy and annual or balance days.
- If an approved or submitted current-period assignment conflicts with the employee profile summary, the assignment controls and the profile summary is stale.
- Use the profile summary only when there is no authoritative current-period assignment.
- Use case summary only as a last resort.

Common label mapping:

- Assignment controls: use labels such as `leave_assignment_history`, `approved_assignment_over_profile`, and `approved_assignment_current_period` when those are allowed by the template.
- Profile controls: use labels such as `employee_profile_summary` or `profile_summary_current_period` only when no assignment record controls.
- Case summary fallback: use `case_summary_only` only when no stronger evidence exists.

## Payroll and Accrual Readiness

For payroll questions:

- Select the current submitted salary assignment.
- Exclude draft salary assignments from base salary, effective date, payroll readiness, and accrual readiness.
- Exclude superseded salary assignments unless the prompt asks for excluded records.
- Use `base_salary` from the selected salary assignment.
- If a record has a `period` like `YYYY-MM` but no explicit effective date, derive the effective date as `YYYY-MM-01`.
- Treat an accrual batch as ready when the submitted salary assignment is linked to the requested accrual batch and the relevant audit or record detail confirms readiness.

Common label mapping:

- Submitted payroll source: `submitted`.
- Draft exclusion: `exclude_draft_assignment`.
- Payroll audit scope: `payroll_assignment_readiness`.
- Ready but still monitored control result: `ready_with_monitoring`.

## Folder and Notice Readiness

For case folder questions:

- A folder is ready only when every required file is present and every required tag is present.
- `missing_files` is the set difference between required files and actual files.
- `required_tag_present` is true only when all required tags are present.
- Missing required files or tags block closeout even when an approval exists.

For formal notices:

- Prefer notice packets or message/notification records with explicit `quality` and `defects`.
- Mark notice quality defective if quality is `defective`, defects are present, or required notice sections are missing.
- Keep notice defect values exactly as the template allows, such as missing acknowledgement deadline, appeal instructions, waitlist status, or correct policy.
- If folder or notice defects exist, approval alone is not sufficient for closeout.

Common label mapping:

- Evidence source order for full case review: `approval_history_folder_notice_audit`.
- Folder/notice audit scope: `document_notice_findings_only`.
- Approval gate when defects exist: `approval_not_sufficient_when_folder_or_notice_defective`.
- No tag work needed: `no_tag_action`; missing required tags: `add_required_tag`.
- Defective notices usually require `reissue_defective_notices` and `block_close_and_reissue_notice`.
- Final result with folder or notice defects: `hold_for_folder_and_notice_defects`.

## Approval and Closeout

For final decisions:

- Use the latest final approval event or explicit final approval step.
- Normalize approval text to the template enum. For example, "approved with conditions" maps to `approved_with_conditions` when that label is allowed.
- Record the approver as approval authority and the approval id as approval event id.
- Approve onboarding close only when effective leave, payroll, folder, tags, and notice evidence are clean for the task's requested scope.
- Use records remediation when source records need correction, not merely when a notice needs reissue.

Common label mapping:

- Clean records closeout: `approve_onboarding_close`, `approval_sufficient_when_records_clean`, `approve_closeout`.
- Folder or notice defects: `block_close_and_reissue_notice`, `open_records_remediation` for records owner work, and `hold_for_folder_and_notice_defects`.
- Monitoring without blockers: `ready_with_monitoring`.

## Recruitment Reconciliation

For recruitment questions:

- Derive candidate outcomes from committee decision plus offer register evidence, not messages alone.
- The selected candidate must be the candidate with a selected committee decision and accepted offer when both are present.
- Waitlisted and rejected arrays contain candidate IDs only.
- Sum every recruiting campaign cost ledger amount for the opening to produce the cost total.
- Determine notice follow-up from notice packets or message quality. Include candidate IDs whose required notice is missing, defective, or requires reissue.
- Accepted offers create payroll handoff work for the selected candidate only. Waitlisted or rejected candidates must not satisfy payroll handoff gates.
- Draft payroll precheck or placeholder records do not satisfy submitted assignment requirements.

Common label mapping:

- Candidate status source: `interview_feedback_and_offer`.
- Outcome control: `committee_decision_with_offer_confirmation`.
- Cost source: `recruitment_cost_ledger`.
- Notice source: `notice_packet_inspection` when packets are available.
- Handoff gate: `accepted_offer_only`.
- Assignment status required after offer: `submitted_after_acceptance`.
- Draft payroll allowed: `false`.
- Waitlisted offer exclusion: `no_accepted_status_or_offer` or `waitlisted_not_selected`, depending on the template and evidence wording.
- Missing waitlist notice: `send_waitlist_notice`; defective waitlist notice: `reissue_waitlist_notice_not_rejection`.
- Missing rejection notice: `send_rejection_notice`; defective rejection notice: `reissue_rejection_notice`.

## Audit Scope

Audit events are scope-specific:

- Include audit events whose event type and detail directly support the requested decision.
- Exclude adjacent audit events about other scopes, even when they belong to the same employee or case.
- For leave precedence, include leave/profile mismatch audits and exclude folder, document, or notice audits.
- For payroll readiness, include payroll assignment or accrual readiness audits and exclude leave or document audits.
- For folder/notice readiness, include folder, document, notice, and closeout-blocking audits and exclude leave or payroll-only audits.
- For cross-module packages, inspect every related audit before assigning owners, blockers, and remediation clocks, then still map each final field to its requested scope.

Set `audit_event_id` to the primary event supporting the answer. Use `supporting_audit_event_ids` for all direct supporting audit ids and `excluded_audit_event_ids` for adjacent events intentionally left out of the scoped decision.
