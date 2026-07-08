# PeopleOps Control Task Skill

## 1. Access & Setup
- Open the solver application at `<TASK_ENV_BASE_URL>`.
- Login: `ops.lead@peopleops.local` / `PeopleOps#2026`.
- Identify the task type from the business task description and the fields in `input/payloads/answer_template.json`.
- Extract all stated identifiers, statuses, amounts, and dates from the application before applying any rules.

## 2. Universal Precedence Rules
Apply these hierarchies across all task types:
- **Status**: `submitted` > `draft` > `superseded`
- **Leave source**: Approved assignment (current period) > Employee profile summary > Case summary only
- **Payroll source**: Submitted assignment is authoritative; draft and superseded are excluded
- **Candidate/Offer**: Accepted offer is the only valid trigger for payroll handoff
- **Nulls**: Use JSON `null` for missing identifiers, never the string `"null"`. Use `[]` for empty exclusion lists.
- **Enums**: Always use exact allowed values from the answer template. Never paraphrase.

---

## 3. Template 1: Onboarding Closeout (Leave + Payroll)
**Identify by**: Fields `leave_source`, `payroll_assignment_id`, `closeout_action`, `final_control_result`.

**Data to collect**: Employee ID; all leave assignments (status, policy, days); profile summary; all payroll assignments (status, base salary).

**Field rules**:
- `leave_source`:
  - `leave_assignment_history` if approved assignment exists for current period **and** linked payroll is `submitted`
  - `employee_profile_summary` if (approved assignment exists but payroll is `draft`) or (no approved assignment but profile summary exists)
  - `case_summary_only` otherwise
- `annual_days`: From the actual leave source; `null` if `case_summary_only`
- `assignment_id`: Approved assignment ID if one exists for current period, else `null`
- `payroll_assignment_id`: The `submitted` payroll ID if available; otherwise the only available payroll ID (even if `draft`)
- `excluded_payroll_ids`: All payroll IDs with status `draft` or `superseded`
- `excluded_leave_ids`: All leave assignment IDs that are `draft`, `superseded`, or not the current effective approved assignment
- `leave_precedence_source`:
  - `approved_assignment_current_period` if approved assignment exists for current period
  - `profile_summary_current_period` if no approved assignment but profile summary exists
  - `case_summary_only` otherwise
- `payroll_source_status`: Status of the `payroll_assignment_id`
- `closeout_action`:
  - `approve_onboarding_close` if payroll is `submitted` AND leave source is NOT `case_summary_only`
  - `block_close_and_reissue_notice` if payroll is `draft` OR leave source is `case_summary_only`
- `approval_closeout_gate`:
  - `approval_sufficient_when_records_clean` if `closeout_action` is `approve_onboarding_close`
  - `approval_not_sufficient_when_folder_or_notice_defective` if `closeout_action` is `block_close_and_reissue_notice`
- `final_control_result`:
  - `approve_closeout` if approved assignment exists AND payroll is `submitted` AND leave sourced from assignment history
  - `ready_with_monitoring` if leave sourced from `employee_profile_summary` (no approved assignment) AND payroll is `submitted`
  - `hold_for_folder_and_notice_defects` if payroll is `draft` OR leave source is `case_summary_only`

---

## 4. Template 2: Case Document & Notice Review
**Identify by**: Fields `case_id`, `folder_ready`, `notice_quality`, `closeout_blockers`, `escalation_action`.

**Data to collect**: Case ID; approval history (decision, authority, event ID); folder contents and required tags; notice packet and defects; audit events.

**Field rules**:
- `folder_ready`: `false` if any required files are missing; `true` otherwise
- `missing_files`: List all missing required filenames
- `required_tag_present`: Boolean from folder metadata
- `notice_quality`: `defective` if any notice defects exist; `valid` otherwise
- `notice_defects`: List specific defects from the template allowed values
- `next_action`:
  - `block_close_and_reissue_notice` if folder not ready OR notice defective
  - `approve_onboarding_close` if fully clean
  - `open_records_remediation` for severe records issues
- `approval_closeout_gate`: `approval_not_sufficient_when_folder_or_notice_defective` if any defects; `approval_sufficient_when_records_clean` if clean
- `closeout_blockers`: Map defects to blockers (`missing_required_files`, `missing_required_tags`, `defective_formal_notice`)
- `evidence_source_order`:
  - `approval_history_folder_notice_audit` if approval history + folder + notice + audit all exist
  - `folder_notice_audit` if no approval history
  - `audit_only` if only audit events exist
- `folder_required_tag_action`: `no_tag_action` if tag present; `add_required_tag` if missing
- `notice_evidence_source`:
  - `notice_packet_inspection` for formal notice packets
  - `message_notice_inspection` for message-based notices
  - `case_summary_only` for case-only data
- `escalation_action`:
  - `open_records_remediation` for missing files/records issues
  - `block_close_and_reissue_notice` for notice defects
  - `no_action` if clean
- `records_remediation_owner`:
  - `Records` for file issues
  - `People Ops Compliance` for compliance gaps
  - `Payroll QA` for payroll issues
- `notice_remediation_action`: `reissue_defective_notices` if notice defective; `no_notice_action` if valid
- `final_control_result`:
  - `hold_for_folder_and_notice_defects` if any folder/notice defects
  - `approve_closeout` if fully clean
  - `ready_with_monitoring` for minor non-blocking issues

---

## 5. Template 3: Recruitment Selection & Offer Handoff
**Identify by**: Fields `opening_id`, `selected_candidate`, `waitlisted_candidates`, `onboarding_handoff`, `handoff_control_result`.

**Data to collect**: Opening ID; all candidates (selected, waitlisted, rejected); offer details (ID, base salary, status); recruitment cost ledger; interview feedback.

**Field rules**:
- `selected_candidate`: Candidate with accepted offer or highest committee ranking
- `waitlisted_candidates`: Candidates explicitly marked waitlisted
- `rejected_candidates`: Candidates explicitly marked rejected
- `offer_id` / `offer_base_salary`: From the accepted offer
- `recruitment_cost_total`: Sum from `recruitment_cost_ledger` if available
- `notice_followup_required`: Combine `waitlisted_candidates` + `rejected_candidates`
- `onboarding_handoff`: `create_payroll_precheck` if selected candidate has `accepted` offer; `no_payroll_handoff` otherwise
- `candidate_status_source`:
  - `interview_feedback_and_offer` if offer process completed
  - `message_only` if only messages
  - `case_summary_only` if only case data
- `candidate_outcome_control`:
  - `committee_decision_with_offer_confirmation` if committee decided with offer
  - `message_status_only` if based on messages
  - `case_summary_only` if based on case
- `selected_offer_status`: `accepted`, `draft`, `withdrawn`, or `none`
- `cost_source`: `recruitment_cost_ledger` if ledger data exists; `case_summary_only` if estimated
- `notice_quality_source`: `notice_packet_inspection` if formal packets exist
- `waitlisted_followup_action`: `send_waitlist_notice`
- `rejected_followup_action`: `send_rejection_notice`
- `payroll_handoff_gate`: `accepted_offer_only` if handoff triggered by accepted offer
- `payroll_assignment_status_required`: `submitted_after_acceptance` if assignment must be submitted post-acceptance
- `draft_payroll_allowed`: `false` for new-hire payroll (never allow draft)
- `offer_exclusion_reason_for_waitlisted`: `no_accepted_status_or_offer` if waitlisted never had accepted offer
- `handoff_control_result`:
  - `submitted_handoff_required_after_acceptance` if handoff required after acceptance
  - `submitted_handoff_required` if always required
  - `no_handoff_required` otherwise

---

## 6. Template 4: Leave Precedence Audit
**Identify by**: Fields `precedence_source`, `profile_policy_ignored`, `audit_result`, `leave_precedence_source`.

**Data to collect**: Employee ID; approved leave assignment (policy, balance days); employee profile summary leave policy; audit events.

**Field rules**:
- `effective_leave_policy`: From the approved assignment (authoritative source)
- `assignment_id`: The approved assignment ID
- `balance_days`: From the approved assignment
- `precedence_source`:
  - `approved_assignment_over_profile` if approved assignment exists and differs from profile
  - `employee_profile_summary` if no assignment
  - `case_summary_only` if neither
- `profile_policy_ignored`: `true` if approved assignment overrides profile; `false` if profile is used
- `audit_result`:
  - `profile_summary_stale` if profile differs from assignment
  - `ready_with_monitoring` if profile matches but no assignment
  - `block_close` for serious issues
- `next_action`:
  - `update_employee_summary` if profile is stale
  - `open_records_remediation` if records issue
  - `no_action` if clean
- `leave_precedence_source`:
  - `approved_assignment_current_period` if approved assignment exists
  - `profile_summary_current_period` if no assignment but profile exists
  - `case_summary_only` otherwise
- `supporting_audit_event_ids`: Relevant audit events that support the finding
- `excluded_audit_event_ids`: Irrelevant or superseded audit events
- `audit_scope`: `leave_source_precedence_only`

---

## 7. Template 5: Payroll Assignment Readiness
**Identify by**: Fields `salary_assignment_id`, `accrual_ready`, `draft_exclusion_rule`, `control_result`.

**Data to collect**: Employee ID; all payroll assignments (submitted, draft, superseded with base salary and effective date); accrual batch ID; audit event ID.

**Field rules**:
- `salary_assignment_id`: The `submitted` payroll assignment ID
- `base_salary` / `effective_date`: From the selected submitted assignment
- `excluded_assignment_id`: The `draft` payroll assignment ID if one exists and is being excluded
- `accrual_ready`: `true` if a submitted assignment exists AND accrual batch is provided
- `payroll_source_status`: `submitted`
- `draft_exclusion_rule`:
  - `exclude_draft_assignment` if a draft was excluded
  - `exclude_superseded_only` if only superseded was excluded
  - `draft_allowed` if no exclusion needed
- `audit_scope`: `payroll_assignment_readiness`
- `control_result`:
  - `ready_with_monitoring` if submitted selected but draft coexisted
  - `approve_closeout` if only clean submitted exists
  - `hold_for_folder_and_notice_defects` if issues

---

## 8. Common Pitfalls
- Do not confuse `leave_source` (where leave data came from) with `leave_precedence_source` (which source has authority for the current period).
- In Template 1, `assignment_id` always reflects the approved assignment ID (or `null`), even when `leave_source` falls back to `employee_profile_summary`.
- In Template 1, `payroll_assignment_id` may be a draft ID when no submitted payroll exists; it will simultaneously appear in `excluded_payroll_ids`.
- In Template 5, `excluded_assignment_id` is a single string, not a list.
- `final_control_result`, `control_result`, and `handoff_control_result` are template-specific and not interchangeable.
- Always verify that exclusion lists contain every draft/superseded record mentioned in the application, not just the obvious ones.
