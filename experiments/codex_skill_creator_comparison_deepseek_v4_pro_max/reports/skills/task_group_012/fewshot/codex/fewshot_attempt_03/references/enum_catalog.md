# PeopleOps Enum Catalog

Every normalized business label that can appear in answer-template fields, organized by domain.
Use these exact strings. Do not invent variants.

---

## Onboarding Closeout

### leave_source

- `leave_assignment_history`
- `employee_profile_summary`
- `case_summary_only`

### leave_precedence_source

- `approved_assignment_current_period`
- `profile_summary_current_period`
- `case_summary_only`

### payroll_status / payroll_source_status

- `submitted`
- `draft`
- `superseded`

### approval_closeout_gate

- `approval_sufficient_when_records_clean`
- `approval_not_sufficient_when_folder_or_notice_defective`

### closeout_action

- `approve_onboarding_close`
- `block_close_and_reissue_notice`
- `open_records_remediation`

### final_control_result

- `approve_closeout`
- `hold_for_folder_and_notice_defects`
- `ready_with_monitoring`

---

## Policy Case Folder and Notice Review

### final_decision

- `approved_with_conditions`
- `approved`
- `rejected`
- `held`

### notice_quality

- `valid`
- `defective`

### notice_defects (list)

- `missing_ack_deadline`
- `missing_appeal_instructions`
- `missing_waitlist_status`
- `missing_correct_policy`

### audit_scope

- `document_notice_findings_only`
- `leave_source_precedence_only`
- `payroll_assignment_readiness`

### next_action

- `block_close_and_reissue_notice`
- `approve_onboarding_close`
- `open_records_remediation`

### closeout_blockers (list)

- `missing_required_files`
- `missing_required_tags`
- `defective_formal_notice`

### evidence_source_order

- `approval_history_folder_notice_audit`
- `folder_notice_audit`
- `audit_only`

### folder_required_tag_action

- `no_tag_action`
- `add_required_tag`

### notice_evidence_source

- `notice_packet_inspection`
- `message_notice_inspection`
- `case_summary_only`

### escalation_action

- `open_records_remediation`
- `block_close_and_reissue_notice`
- `no_action`

### records_remediation_owner

- `Records`
- `People Ops Compliance`
- `Payroll QA`

### notice_remediation_action

- `reissue_defective_notices`
- `no_notice_action`
- `send_new_offer_notice`

---

## Recruitment Reconciliation

### candidate_status_source

- `interview_feedback_and_offer`
- `case_summary_only`
- `message_only`

### candidate_outcome_control

- `committee_decision_with_offer_confirmation`
- `message_status_only`
- `case_summary_only`

### selected_offer_status

- `accepted`
- `draft`
- `withdrawn`
- `none`

### cost_source

- `recruitment_cost_ledger`
- `case_summary_only`

### notice_quality_source

- `notice_packet_inspection`
- `message_notice_inspection`
- `case_summary_only`

### waitlisted_followup_action

- `send_waitlist_notice`
- `reissue_waitlist_notice_not_rejection`
- `no_action`

### rejected_followup_action

- `send_rejection_notice`
- `no_action`
- `reissue_rejection_notice`

### onboarding_handoff

- `create_payroll_precheck`
- `create_submitted_assignment_after_acceptance`
- `no_payroll_handoff`

### payroll_handoff_gate

- `accepted_offer_only`
- `accepted_offer_and_submitted_assignment`
- `all_interviewed_candidates`

### payroll_assignment_status_required

- `submitted_after_acceptance`
- `submitted`
- `draft_allowed`

### offer_exclusion_reason_for_waitlisted

- `no_accepted_status_or_offer`
- `waitlisted_not_selected`
- `already_rejected`

### handoff_control_result

- `submitted_handoff_required_after_acceptance`
- `submitted_handoff_required`
- `no_handoff_required`

---

## Leave Source Precedence

### precedence_source

- `approved_assignment_over_profile`
- `employee_profile_summary`
- `case_summary_only`

### audit_result

- `profile_summary_stale`
- `ready_with_monitoring`
- `block_close`

### next_action (leave)

- `update_employee_summary`
- `open_records_remediation`
- `no_action`

---

## Payroll Assignment Readiness

### draft_exclusion_rule

- `exclude_draft_assignment`
- `draft_allowed`
- `exclude_superseded_only`

### control_result

- `ready_with_monitoring`
- `hold_for_folder_and_notice_defects`
- `approve_closeout`

### payroll_source_status

- `submitted`
- `draft`
- `superseded`
