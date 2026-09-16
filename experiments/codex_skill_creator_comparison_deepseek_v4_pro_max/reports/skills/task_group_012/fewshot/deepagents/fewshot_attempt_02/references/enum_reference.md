# Normalized Business Labels Reference

Every PeopleOps answer template uses fixed allowed values. Always match these
exact strings in JSON output. Do not use free-text or paraphrased values.

## Record Status Labels

- `submitted` — authoritative record, use for decisions.
- `draft` — non-authoritative, exclude from decisions unless task explicitly
  allows drafts.
- `superseded` — overtaken by a newer submitted record; exclude from
  decisions.

## Leave / Precedence

- `leave_assignment_history` — leave policy derived from assignment ledger
  records.
- `employee_profile_summary` — leave policy from the employee summary record.
- `case_summary_only` — leave policy sourced only from case summary text
  (lowest precedence).
- `approved_assignment_current_period` — approved assignment for the current
  period overrides the profile summary.
- `profile_summary_current_period` — no approved assignment exists; profile
  summary controls.
- `approved_assignment_over_profile` — precedence label: approved assignment
  trumps profile summary.

## Leave Audit Scope / Results

- `leave_source_precedence_only` — audit scope restricted to leave precedence
  decisions; exclude document/notice audit events.
- `document_notice_findings_only` — audit scope restricted to document and
  notice findings; exclude leave/payroll events.
- `payroll_assignment_readiness` — audit scope restricted to payroll
  assignment and accrual readiness.
- `profile_summary_stale` — audit result: profile summary is out of date.
- `ready_with_monitoring` — audit result: records are clean, proceed with
  monitoring.
- `block_close` — audit result: blocking defect prevents closeout.

## Closeout Actions

- `approve_onboarding_close` — records are clean; approve and complete.
- `block_close_and_reissue_notice` — defective notice requires reissue before
  closeout.
- `open_records_remediation` — records or folder have defects requiring
  remediation.

## Case Decision / Quality

- `approved` — unconditional approval.
- `approved_with_conditions` — approval with conditions attached.
- `rejected` — rejection.
- `held` — decision held pending further action.
- `valid` — notice or document passes quality inspection.
- `defective` — notice or document fails quality inspection.

## Notice Defects

- `missing_ack_deadline` — notice lacks an acknowledgement deadline.
- `missing_appeal_instructions` — notice lacks appeal instructions.
- `missing_waitlist_status` — notice lacks waitlist status information.
- `missing_correct_policy` — notice references an incorrect policy.

## Closeout Blockers

- `missing_required_files` — required documents are absent from the case
  folder.
- `missing_required_tags` — required tags are absent from the case.
- `defective_formal_notice` — the formal notice has quality defects.

## Evidence Source Order

- `approval_history_folder_notice_audit` — full chain: approval history,
  folder, notice, audit.
- `folder_notice_audit` — folder, notice, audit chain.
- `audit_only` — audit evidence only.

## Folder / Tag Actions

- `no_tag_action` — no tag change required.
- `add_required_tag` — the required tag must be added.

## Notice Evidence Source

- `notice_packet_inspection` — inspect the notice packet directly.
- `message_notice_inspection` — inspect notice content in messages.
- `case_summary_only` — rely on case summary text only.

## Escalation / Remediation

- `open_records_remediation` — escalate for records remediation.
- `block_close_and_reissue_notice` — block closeout and reissue.
- `no_action` — no escalation required.

Remediation owners:
- `Records` — records team remediation.
- `People Ops Compliance` — compliance team remediation.
- `Payroll QA` — payroll QA team remediation.

Notice remediation:
- `reissue_defective_notices` — reissue notice(s) with corrections.
- `no_notice_action` — no notice remediation required.
- `send_new_offer_notice` — send a new offer notice.

## Recruitment / Candidate

Candidate status source:
- `interview_feedback_and_offer` — sourced from interview feedback and offer
  records.
- `case_summary_only` — sourced from case summary text.
- `message_only` — sourced from messages only.

Candidate outcome control:
- `committee_decision_with_offer_confirmation` — confirmed by committee
  decision and offer.
- `message_status_only` — based on message status only.
- `case_summary_only` — based on case summary only.

Selected offer status:
- `accepted` — offer was accepted.
- `draft` — offer is still draft.
- `withdrawn` — offer was withdrawn.
- `none` — no offer exists for the candidate.

Cost source:
- `recruitment_cost_ledger` — cost from the recruitment cost ledger.
- `case_summary_only` — cost from case summary text.

Waitlisted followup:
- `send_waitlist_notice` — send a new waitlist notice.
- `reissue_waitlist_notice_not_rejection` — reissue waitlist notice (not a
  rejection).
- `no_action` — no waitlist followup needed.

Rejected followup:
- `send_rejection_notice` — send a new rejection notice.
- `no_action` — no rejection followup needed.
- `reissue_rejection_notice` — reissue the rejection notice.

## Payroll / Handoff

Payroll source status:
- `submitted` — submitted assignment is authoritative.
- `draft` — draft assignment (excluded by rule).
- `superseded` — superseded by a newer record.

Draft exclusion:
- `exclude_draft_assignment` — exclude any draft assignment record.
- `draft_allowed` — drafts are permitted.
- `exclude_superseded_only` — exclude superseded records but allow drafts.

Payroll handoff gates:
- `accepted_offer_only` — handoff based on accepted offer alone.
- `accepted_offer_and_submitted_assignment` — handoff requires accepted offer
  and submitted assignment.
- `all_interviewed_candidates` — handoff includes all interviewed candidates.

Assignment status required:
- `submitted_after_acceptance` — assignment must be submitted after acceptance.
- `submitted` — assignment must be submitted (any timing).
- `draft_allowed` — draft assignments are acceptable.

Offer exclusion reason:
- `no_accepted_status_or_offer` — waitlisted candidate lacks an accepted offer.
- `waitlisted_not_selected` — candidate was waitlisted, not selected.
- `already_rejected` — candidate was already rejected.

Handoff control result:
- `submitted_handoff_required_after_acceptance` — submitted assignment needed
  after acceptance.
- `submitted_handoff_required` — submitted assignment needed.
- `no_handoff_required` — no payroll handoff needed.

Onboarding handoff:
- `create_payroll_precheck` — create payroll precheck for onboarding.
- `create_submitted_assignment_after_acceptance` — create submitted assignment
  after offer acceptance.
- `no_payroll_handoff` — no payroll handoff action.

## Final Control Results

- `approve_closeout` — all checks pass; approve closeout.
- `hold_for_folder_and_notice_defects` — hold for folder or notice defects.
- `ready_with_monitoring` — records are clean; proceed under monitoring.

## Approval Closeout Gates

- `approval_sufficient_when_records_clean` — approval is sufficient when all
  records pass checks.
- `approval_not_sufficient_when_folder_or_notice_defective` — approval
  insufficient when folder or notice has defects.
