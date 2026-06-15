# Field guide — normalized label inventory and role map

This reference lists the normalized enum vocabularies seen in this task family and
explains the **role** of each field so you pick the right sibling label. Always
defer to the actual `answer_template.json` for the task in front of you: it tells
you which fields exist and which `allowed_values` apply. Fields below are grouped
by area; not every task uses every field.

## Table of contents
1. Identity / scalar fields
2. Source & precedence labels
3. Status labels
4. Folder readiness labels
5. Notice quality / defect / source labels
6. Audit scope & result labels
7. Gate, action, escalation & remediation labels
8. Final-result labels
9. Recruitment labels
10. Field-role disambiguation (the easy-to-confuse pairs)

---

## 1. Identity / scalar fields

These are raw values copied from the controlling record, not enums:
- entity id (employee/case/opening), effective policy name, assignment id,
  payroll/salary assignment id, offer id, audit event id, accrual batch id.
- numeric: annual/balance days (integer), base salary (number), offer base salary
  (number), recruitment cost total (number).
- date: effective date as the stored string (use the controlling submitted record's
  effective period/date; emit the ISO form the record uses).
- boolean: folder_ready, required_tag_present, profile_policy_ignored,
  accrual_ready, draft_payroll_allowed.

## 2. Source & precedence labels

- `leave_source`: `leave_assignment_history` | `employee_profile_summary` |
  `case_summary_only`. Pick assignment-history when an approved/submitted
  assignment controls.
- `leave_precedence_source`: `approved_assignment_current_period` |
  `profile_summary_current_period` | `case_summary_only`.
- `precedence_source`: `approved_assignment_over_profile` |
  `employee_profile_summary` | `case_summary_only`.
- `candidate_status_source`: `interview_feedback_and_offer` | `case_summary_only` |
  `message_only`.
- `candidate_outcome_control`: `committee_decision_with_offer_confirmation` |
  `message_status_only` | `case_summary_only`.
- `cost_source`: `recruitment_cost_ledger` | `case_summary_only`.
- `evidence_source_order`: `approval_history_folder_notice_audit` |
  `folder_notice_audit` | `audit_only`. Pick the longest chain whose pieces are
  all present (e.g. include approval history only when an approval record exists).

## 3. Status labels

- `payroll_status` / `payroll_source_status`: `submitted` | `draft` | `superseded`.
  The controlling salary assignment is `submitted`.
- `selected_offer_status`: `accepted` | `draft` | `withdrawn` | `none`.
- `draft_exclusion_rule`: `exclude_draft_assignment` | `draft_allowed` |
  `exclude_superseded_only`. Payroll readiness excludes drafts.
- `payroll_assignment_status_required`: `submitted_after_acceptance` | `submitted`
  | `draft_allowed`.

## 4. Folder readiness labels

- `folder_required_tag_action`: `no_tag_action` | `add_required_tag`.
- `closeout_blockers` (set): `missing_required_files` | `missing_required_tags` |
  `defective_formal_notice`. Include exactly the ones that apply; independent
  checks.

## 5. Notice quality / defect / source labels

- `notice_quality`: `valid` | `defective`.
- `notice_defects` (set): `missing_ack_deadline` | `missing_appeal_instructions` |
  `missing_waitlist_status` | `missing_correct_policy`. Empty when valid.
- `notice_evidence_source` / `notice_quality_source`: `notice_packet_inspection` |
  `message_notice_inspection` | `case_summary_only`. Decide by artifact kind, not
  by endpoint: a structured notice record with quality/defects/status fields is a
  notice packet even if a messages-style endpoint serves it.
- `notice_remediation_action`: `reissue_defective_notices` | `no_notice_action` |
  `send_new_offer_notice`.

## 6. Audit scope & result labels

- `audit_scope`: `document_notice_findings_only` | `leave_source_precedence_only` |
  `payroll_assignment_readiness`. One per task; matches the task's subject.
- `audit_result`: `profile_summary_stale` | `ready_with_monitoring` | `block_close`.
- `supporting_audit_event_ids` (set): events on-scope for this task.
- `excluded_audit_event_ids` (set): adjacent off-scope events for the same entity;
  `[]` if none.

## 7. Gate, action, escalation & remediation labels

- `approval_closeout_gate`: `approval_sufficient_when_records_clean` |
  `approval_not_sufficient_when_folder_or_notice_defective`.
- `closeout_action` / `next_action`: `approve_onboarding_close` |
  `block_close_and_reissue_notice` | `open_records_remediation`.
- `escalation_action`: `open_records_remediation` |
  `block_close_and_reissue_notice` | `no_action`. With records defects this is
  `open_records_remediation` (a separate track from the notice next-action).
- `records_remediation_owner`: `Records` | `People Ops Compliance` | `Payroll QA`.
  The folder/records owner per the folder policy or folder record.
- `final_decision` (approval body's decision): `approved_with_conditions` |
  `approved` | `rejected` | `held`. Distinct from the gate.

## 8. Final-result labels

- `final_control_result` / `control_result`: `approve_closeout` |
  `hold_for_folder_and_notice_defects` | `ready_with_monitoring`.
  Clean records → approve; folder/notice defects → hold; readiness-with-conditions
  audit result → ready with monitoring.

## 9. Recruitment labels

- `onboarding_handoff`: `create_payroll_precheck` |
  `create_submitted_assignment_after_acceptance` | `no_payroll_handoff`.
  Recruitment-stage handoff action is `create_payroll_precheck`.
- `payroll_handoff_gate`: `accepted_offer_only` |
  `accepted_offer_and_submitted_assignment` | `all_interviewed_candidates`.
  Recruitment trigger is `accepted_offer_only`.
- `handoff_control_result`: `submitted_handoff_required_after_acceptance` |
  `submitted_handoff_required` | `no_handoff_required`.
- `waitlisted_followup_action`: `send_waitlist_notice` |
  `reissue_waitlist_notice_not_rejection` | `no_action`.
- `rejected_followup_action`: `send_rejection_notice` | `no_action` |
  `reissue_rejection_notice`.
- `offer_exclusion_reason_for_waitlisted`: `no_accepted_status_or_offer` |
  `waitlisted_not_selected` | `already_rejected`.

## 10. Field-role disambiguation (easy-to-confuse pairs)

- **notice evidence source vs the endpoint it came from.** The label names the
  artifact (structured packet vs plain message text vs summary), not the URL.
- **escalation_action vs next_action.** Escalation is the records-remediation
  track (`open_records_remediation`) when records are defective; next_action /
  notice_remediation handle the notice (`block_close_and_reissue_notice` /
  `reissue_defective_notices`). Don't duplicate one into the other.
- **recruitment trigger/action vs downstream payroll strictness.** The
  recruitment gate is `accepted_offer_only` and action is
  `create_payroll_precheck`. The "submitted, no drafts" requirement lives in
  `payroll_assignment_status_required` (`submitted_after_acceptance`),
  `draft_payroll_allowed` (false), and `handoff_control_result`
  (`submitted_handoff_required_after_acceptance`).
- **final_decision vs gate vs final_control_result.** The approval body's decision
  (e.g. approved-with-conditions) is independent of whether the gate permits
  closeout and of the final control result; a case can be approved yet held.
- **folder file check vs tag check.** Independent set differences; one can fail
  while the other passes. `required_tag_present` and `folder_required_tag_action`
  reflect only tags; `missing_files` and `missing_required_files` reflect only
  files.
- **supporting vs excluded audit events.** Supporting = on-scope; excluded =
  adjacent off-scope for the same entity; never put an off-scope event in support
  and never invent an excluded one.
