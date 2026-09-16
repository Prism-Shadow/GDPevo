# PeopleOps Enum Label Reference

This reference lists every normalized business label that appears across the five task types, grouped by domain. When you find a domain outcome (e.g., "folder has missing files, notice is defective"), consult this list to pick the exact label the template expects.

The answer template you receive will show `allowed_values` for each enum field. This reference is a consolidated view to help you understand the label semantics before you even see the template.

## Leave domain

| Label | Meaning |
|-------|---------|
| `leave_assignment_history` | Leave data sourced from ledger leave assignments |
| `employee_profile_summary` | Leave data sourced from employee profile (stale when an approved assignment exists) |
| `case_summary_only` | Leave data sourced only from the case summary |
| `approved_assignment_current_period` | Precedence: approved assignment for the current period controls |
| `profile_summary_current_period` | Precedence: profile summary for the current period controls |
| `leave_source_precedence_only` | Audit scope limited to leave source precedence events |
| `approved_assignment_over_profile` | Approved assignment takes precedence over the profile summary |
| `profile_summary_stale` | Audit finding that the profile summary is outdated |

## Payroll domain

| Label | Meaning |
|-------|---------|
| `submitted` | Record is submitted and authoritative |
| `draft` | Record is a draft — exclude from authoritative answers |
| `superseded` | Record has been superseded by a later one |
| `exclude_draft_assignment` | Draft exclusion rule: exclude draft assignments |
| `draft_allowed` | Draft records are permissible in this context |
| `exclude_superseded_only` | Only superseded records should be excluded |
| `payroll_assignment_readiness` | Audit scope limited to payroll assignment readiness |
| `ready_with_monitoring` | Control result: system is ready with ongoing monitoring |
| `submitted_after_acceptance` | Payroll assignment must be submitted after offer acceptance |
| `submitted_handoff_required_after_acceptance` | Handoff result: submitted assignment is required after acceptance |

## Closeout / Control domain

| Label | Meaning |
|-------|---------|
| `approve_closeout` | Final result: closeout is approved |
| `hold_for_folder_and_notice_defects` | Final result: hold closeout due to folder/notice defects |
| `approve_onboarding_close` | Action: approve the onboarding close |
| `block_close_and_reissue_notice` | Action: block the close and reissue defective notice |
| `open_records_remediation` | Action: open a records remediation case |
| `approval_sufficient_when_records_clean` | Gate: approval is sufficient when all records are clean |
| `approval_not_sufficient_when_folder_or_notice_defective` | Gate: approval is not sufficient when folder or notice is defective |
| `no_action` | No action required |

## Case / Policy domain

| Label | Meaning |
|-------|---------|
| `approved_with_conditions` | Final decision: approved but with conditions |
| `approved` | Final decision: fully approved |
| `rejected` | Final decision: rejected |
| `held` | Final decision: held pending further review |
| `approval_history_folder_notice_audit` | Evidence source order: start with approvals, then folder, then notice, then audit |
| `folder_notice_audit` | Evidence source order: folder, notice, audit |
| `audit_only` | Evidence source order: audit only |

## Folder / Document domain

| Label | Meaning |
|-------|---------|
| `no_tag_action` | No action needed for required tags |
| `add_required_tag` | A required tag must be added |
| `missing_required_files` | Closeout blocker: required files are missing |
| `missing_required_tags` | Closeout blocker: required tags are missing |
| `defective_formal_notice` | Closeout blocker: formal notice is defective |

## Notice / Message domain

| Label | Meaning |
|-------|---------|
| `valid` | Notice has no defects |
| `defective` | Notice has one or more defects |
| `notice_packet_inspection` | Notice evidence sourced from notice packet inspection |
| `message_notice_inspection` | Notice evidence sourced from message inspection |
| `missing_ack_deadline` | Defect: acknowledgement deadline missing |
| `missing_appeal_instructions` | Defect: appeal instructions missing |
| `missing_waitlist_status` | Defect: waitlist status not mentioned |
| `missing_correct_policy` | Defect: incorrect policy referenced |
| `reissue_defective_notices` | Remediation: reissue defective notices |
| `no_notice_action` | Remediation: no notice action needed |
| `send_new_offer_notice` | Remediation: send new offer notice |

## Recruitment domain

| Label | Meaning |
|-------|---------|
| `interview_feedback_and_offer` | Candidate status source: interview feedback and offer register |
| `committee_decision_with_offer_confirmation` | Candidate outcome control: committee decision confirmed by offer |
| `message_status_only` | Candidate outcome control: message status only |
| `accepted` | Offer status: accepted |
| `withdrawn` | Offer status: withdrawn |
| `none` | Offer status: no offer exists |
| `recruitment_cost_ledger` | Cost source: recruitment cost ledger |
| `send_waitlist_notice` | Action: send waitlist notice to candidate |
| `reissue_waitlist_notice_not_rejection` | Action: reissue waitlist notice (not rejection) |
| `send_rejection_notice` | Action: send rejection notice to candidate |
| `reissue_rejection_notice` | Action: reissue rejection notice |
| `accepted_offer_only` | Handoff gate: only accepted offers qualify for payroll handoff |
| `accepted_offer_and_submitted_assignment` | Handoff gate: accepted offer plus submitted assignment |
| `all_interviewed_candidates` | Handoff gate: all interviewed candidates qualify |
| `create_payroll_precheck` | Onboarding handoff: create payroll precheck |
| `create_submitted_assignment_after_acceptance` | Onboarding handoff: create submitted assignment after acceptance |
| `no_payroll_handoff` | Onboarding handoff: no payroll handoff |
| `no_accepted_status_or_offer` | Exclusion reason: candidate has no accepted status or offer |
| `waitlisted_not_selected` | Exclusion reason: candidate is waitlisted, not selected |
| `already_rejected` | Exclusion reason: candidate was already rejected |
| `submitted_handoff_required` | Handoff result: submitted handoff is required |
| `no_handoff_required` | Handoff result: no handoff is required |

## Remediation / Escalation domain

| Label | Meaning |
|-------|---------|
| `Records` | Remediation owner: Records team |
| `People Ops Compliance` | Remediation owner: People Ops Compliance team |
| `Payroll QA` | Remediation owner: Payroll QA team |
| `update_employee_summary` | Next action: update the employee profile summary |

## Audit scope labels

| Label | Used in |
|-------|---------|
| `document_notice_findings_only` | Tasks reviewing case folder and notice quality |
| `leave_source_precedence_only` | Tasks resolving leave source precedence |
| `payroll_assignment_readiness` | Tasks verifying payroll assignment readiness |
