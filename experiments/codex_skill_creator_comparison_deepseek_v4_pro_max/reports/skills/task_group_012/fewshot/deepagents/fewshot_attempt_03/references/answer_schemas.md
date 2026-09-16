# Answer Schemas and Normalized Labels

This reference catalogs all normalized business labels used across PeopleOps Console answer templates. Always use these exact string values for enum fields.

## Leave Source Fields

| Field | Allowed Values |
|-------|---------------|
| `leave_source` | `leave_assignment_history`, `employee_profile_summary`, `case_summary_only` |
| `leave_precedence_source` | `approved_assignment_current_period`, `profile_summary_current_period`, `case_summary_only` |
| `precedence_source` | `approved_assignment_over_profile`, `employee_profile_summary`, `case_summary_only` |

Always use `leave_assignment_history` when the decision came from ledger records.
Always use `approved_assignment_over_profile` or `approved_assignment_current_period` when the approved assignment controls.

## Payroll Source Fields

| Field | Allowed Values |
|-------|---------------|
| `payroll_status` | `submitted`, `draft`, `superseded` |
| `payroll_source_status` | `submitted`, `draft`, `superseded` |
| `draft_exclusion_rule` | `exclude_draft_assignment`, `draft_allowed`, `exclude_superseded_only` |

Always use `submitted` for a chosen submitted payroll assignment.
Always use `exclude_draft_assignment` when draft assignments are excluded.

## Closeout Action Fields

| Field | Allowed Values |
|-------|---------------|
| `closeout_action` | `approve_onboarding_close`, `block_close_and_reissue_notice`, `open_records_remediation` |
| `next_action` | `block_close_and_reissue_notice`, `approve_onboarding_close`, `open_records_remediation`, `update_employee_summary`, `no_action` |
| `escalation_action` | `open_records_remediation`, `block_close_and_reissue_notice`, `no_action` |

- `approve_onboarding_close` — all records clean, closeout can proceed
- `block_close_and_reissue_notice` — formal notice defective, must be reissued
- `open_records_remediation` — folder files missing or tags missing
- `update_employee_summary` — employee profile is stale

## Approval Gate Fields

| Field | Allowed Values |
|-------|---------------|
| `approval_closeout_gate` | `approval_sufficient_when_records_clean`, `approval_not_sufficient_when_folder_or_notice_defective` |

## Final Control Result Fields

| Field | Allowed Values |
|-------|---------------|
| `final_control_result` | `approve_closeout`, `hold_for_folder_and_notice_defects`, `ready_with_monitoring` |
| `control_result` | `ready_with_monitoring`, `hold_for_folder_and_notice_defects`, `approve_closeout` |
| `audit_result` | `profile_summary_stale`, `ready_with_monitoring`, `block_close` |

## Case Review Fields

| Field | Allowed Values |
|-------|---------------|
| `final_decision` | `approved_with_conditions`, `approved`, `rejected`, `held` |
| `notice_quality` | `valid`, `defective` |
| `notice_defects` (list) | `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy` |
| `notice_evidence_source` | `notice_packet_inspection`, `message_notice_inspection`, `case_summary_only` |
| `notice_remediation_action` | `reissue_defective_notices`, `no_notice_action`, `send_new_offer_notice` |
| `folder_required_tag_action` | `no_tag_action`, `add_required_tag` |
| `records_remediation_owner` | `Records`, `People Ops Compliance`, `Payroll QA` |
| `evidence_source_order` | `approval_history_folder_notice_audit`, `folder_notice_audit`, `audit_only` |
| `closeout_blockers` (list) | `missing_required_files`, `missing_required_tags`, `defective_formal_notice` |

## Audit Scope Fields

| Field | Allowed Values |
|-------|---------------|
| `audit_scope` | `document_notice_findings_only`, `leave_source_precedence_only`, `payroll_assignment_readiness` |

## Recruitment Fields

| Field | Allowed Values |
|-------|---------------|
| `candidate_status_source` | `interview_feedback_and_offer`, `case_summary_only`, `message_only` |
| `candidate_outcome_control` | `committee_decision_with_offer_confirmation`, `message_status_only`, `case_summary_only` |
| `selected_offer_status` | `accepted`, `draft`, `withdrawn`, `none` |
| `cost_source` | `recruitment_cost_ledger`, `case_summary_only` |
| `notice_quality_source` | `notice_packet_inspection`, `message_notice_inspection`, `case_summary_only` |
| `waitlisted_followup_action` | `send_waitlist_notice`, `reissue_waitlist_notice_not_rejection`, `no_action` |
| `rejected_followup_action` | `send_rejection_notice`, `no_action`, `reissue_rejection_notice` |
| `payroll_handoff_gate` | `accepted_offer_only`, `accepted_offer_and_submitted_assignment`, `all_interviewed_candidates` |
| `payroll_assignment_status_required` | `submitted_after_acceptance`, `submitted`, `draft_allowed` |
| `offer_exclusion_reason_for_waitlisted` | `no_accepted_status_or_offer`, `waitlisted_not_selected`, `already_rejected` |
| `handoff_control_result` | `submitted_handoff_required_after_acceptance`, `submitted_handoff_required`, `no_handoff_required` |
| `onboarding_handoff` | `create_payroll_precheck`, `create_submitted_assignment_after_acceptance`, `no_payroll_handoff` |

## Answer Template Conventions

### ID Arrays
When a template field is `{"type": "list[string]"}`, provide an array of ID strings only. Example: `["LA-104-2026-A", "LA-104-2026-DRAFT"]`.

### Enum Fields
When a template defines `{"type": "enum", "allowed_values": [...]}`, use exactly one of the allowed values. Never use free-text.

### Numeric Fields
- `annual_days`, `balance_days`, `base_salary`, `offer_base_salary`: integer or number as specified.
- `recruitment_cost_total`: sum of all cost ledger `amount` values. Must be a number.

### Boolean Fields
Use JSON `true` or `false`.

### Date Fields
Use ISO format `YYYY-MM-DD`.

### Output Format
Return a single JSON object. Do not wrap in markdown fences. Do not include explanatory text.
