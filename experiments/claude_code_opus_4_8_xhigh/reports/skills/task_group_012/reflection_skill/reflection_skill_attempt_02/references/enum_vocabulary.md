# Normalized enum vocabulary

The authoritative list of allowed values is always the per-task
`answer_template.json` — read it for the task at hand. This file collects the
recurring normalized label set seen across this task family so you can recognize
and snap to the right label. Use a value **only** if it appears in the current
template's `allowed_values` for that field.

Important: these labels and the defect codes are the ONLY concrete vocabulary you
should treat as fixed. Everything else (IDs, names, policy titles, salaries, SLA
numbers, file names) is per-entity and must be read at run time.

## Defect codes (formal-notice defects)
- missing_ack_deadline
- missing_appeal_instructions
- missing_waitlist_status
- missing_correct_policy

## Leave source / precedence
- leave_source: leave_assignment_history | employee_profile_summary | case_summary_only
- leave_precedence_source: approved_assignment_current_period | profile_summary_current_period | case_summary_only
- precedence_source: approved_assignment_over_profile | employee_profile_summary | case_summary_only
- profile_policy_ignored: boolean

## Payroll
- payroll_status / payroll_source_status: submitted | draft | superseded
- draft_exclusion_rule: exclude_draft_assignment | draft_allowed | exclude_superseded_only

## Folder / notice
- folder_ready / required_tag_present: boolean
- notice_quality: valid | defective
- folder_required_tag_action: no_tag_action | add_required_tag
- notice_evidence_source / notice_quality_source: notice_packet_inspection | message_notice_inspection | case_summary_only
- closeout_blockers (list): missing_required_files | missing_required_tags | defective_formal_notice
- notice_remediation_action: reissue_defective_notices | no_notice_action | send_new_offer_notice

## Approval / decision / gating
- final_decision: approved_with_conditions | approved | rejected | held
- approval_closeout_gate: approval_sufficient_when_records_clean | approval_not_sufficient_when_folder_or_notice_defective
- closeout_action / next_action: approve_onboarding_close | block_close_and_reissue_notice | open_records_remediation
  (note: leave-precedence next_action uses: update_employee_summary | open_records_remediation | no_action)
- escalation_action: open_records_remediation | block_close_and_reissue_notice | no_action
- records_remediation_owner: Records | People Ops Compliance | Payroll QA
- evidence_source_order: approval_history_folder_notice_audit | folder_notice_audit | audit_only
- final_control_result / control_result: approve_closeout | hold_for_folder_and_notice_defects | ready_with_monitoring

## Audit scope / result
- audit_scope: leave_source_precedence_only | document_notice_findings_only | payroll_assignment_readiness
- audit_result: profile_summary_stale | ready_with_monitoring | block_close

## Recruitment
- selected_offer_status: accepted | draft | withdrawn | none
- candidate_status_source: interview_feedback_and_offer | case_summary_only | message_only
- candidate_outcome_control: committee_decision_with_offer_confirmation | message_status_only | case_summary_only
- cost_source: recruitment_cost_ledger | case_summary_only
- onboarding_handoff: create_payroll_precheck | create_submitted_assignment_after_acceptance | no_payroll_handoff
- payroll_handoff_gate: accepted_offer_only | accepted_offer_and_submitted_assignment | all_interviewed_candidates
- payroll_assignment_status_required: submitted_after_acceptance | submitted | draft_allowed
- draft_payroll_allowed: boolean
- waitlisted_followup_action: send_waitlist_notice | reissue_waitlist_notice_not_rejection | no_action
- rejected_followup_action: send_rejection_notice | no_action | reissue_rejection_notice
- offer_exclusion_reason_for_waitlisted: no_accepted_status_or_offer | waitlisted_not_selected | already_rejected
- handoff_control_result: submitted_handoff_required_after_acceptance | submitted_handoff_required | no_handoff_required

## How to choose between near-synonym labels
- "submitted/approved record controls" -> the *_current_period / submitted /
  accepted family; never the draft / profile / case_summary_only family.
- Structured packet with quality+defects -> *_packet_inspection, not
  *_message_inspection.
- A folder/file defect that needs a records team -> open_records_remediation for
  escalation_action; the notice fix stays reissue_defective_notices.
- After an accepted offer -> the *_after_acceptance / accepted_offer_and_submitted_assignment
  family, never accepted_offer_only or create_payroll_precheck.
