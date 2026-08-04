
# PeopleOps Enum Catalog

## Leave & Payroll Scoped Enums

### leave_precedence_source / precedence_source
| Value | Meaning |
|-------|---------|
| `approved_assignment_current_period` | Authoritative leave assignment from the current approved period overrides profile |
| `approved_assignment_over_profile` | Approved assignment record supersedes employee profile summary |
| `profile_summary_current_period` | Only a profile summary exists; no approved assignment found |
| `employee_profile_summary` | Fallback when no assignment history is available |
| `case_summary_only` | No assignment or profile data; only case narrative available |

### leave_source
| Value | Meaning |
|-------|---------|
| `leave_assignment_history` | Determined from submitted/approved leave assignment records |
| `employee_profile_summary` | Determined from employee profile summary |
| `case_summary_only` | Determined from case narrative only |

### payroll_source_status
| Value | Meaning |
|-------|---------|
| `submitted` | Payroll assignment has been formally submitted — this is authoritative |
| `draft` | Payroll assignment is a draft — must be excluded |
| `superseded` | A newer submitted assignment replaces this one — must be excluded |

### draft_exclusion_rule
| Value | Meaning |
|-------|---------|
| `exclude_draft_assignment` | Exclude any assignment with draft status |
| `draft_allowed` | Draft records are acceptable (use only when explicitly permitted) |
| `exclude_superseded_only` | Exclude superseded but allow drafts (rare) |

### payroll_assignment_status_required
| Value | Meaning |
|-------|---------|
| `submitted_after_acceptance` | Submitted status required only after offer acceptance |
| `submitted` | Submitted status always required |
| `draft_allowed` | Draft status acceptable |

---

## Audit Scoped Enums

### audit_scope
| Value | Meaning |
|-------|---------|
| `leave_source_precedence_only` | Audit events related to leave policy/assignment precedence |
| `document_notice_findings_only` | Audit events related to document and formal notice review |
| `payroll_assignment_readiness` | Audit events related to payroll assignment and accrual readiness |

### audit_result
| Value | Meaning |
|-------|---------|
| `profile_summary_stale` | Employee profile summary is out of date vs. approved assignment |
| `ready_with_monitoring` | Records are clean; proceed with monitoring |
| `block_close` | Defects found; do not close |

---

## Case & Approval Scoped Enums

### final_decision
| Value | Meaning |
|-------|---------|
| `approved_with_conditions` | Approved but conditions must be met |
| `approved` | Fully approved without conditions |
| `rejected` | Rejected outright |
| `held` | Decision deferred |

### approval_closeout_gate
| Value | Meaning |
|-------|---------|
| `approval_sufficient_when_records_clean` | Approval can proceed when all records are clean |
| `approval_not_sufficient_when_folder_or_notice_defective` | Approval blocked if folder or notice has defects |

### closeout_action / next_action
| Value | Meaning |
|-------|---------|
| `approve_onboarding_close` | Close onboarding — all checks pass |
| `block_close_and_reissue_notice` | Block close; reissue the formal notice |
| `open_records_remediation` | Open a remediation workflow for record defects |
| `update_employee_summary` | Update the stale employee profile summary |
| `no_action` | No action required |

### final_control_result / control_result
| Value | Meaning |
|-------|---------|
| `approve_closeout` | Closeout approved |
| `hold_for_folder_and_notice_defects` | Hold — folder or notice has defects |
| `ready_with_monitoring` | Ready to proceed with ongoing monitoring |

### closeout_blockers
| Value | Meaning |
|-------|---------|
| `missing_required_files` | Required files not present in case folder |
| `missing_required_tags` | Required tag not present on case |
| `defective_formal_notice` | Formal notice has quality defects |

---

## Notice Scoped Enums

### notice_quality
| Value | Meaning |
|-------|---------|
| `valid` | Notice is complete and correct |
| `defective` | Notice has one or more defects |

### notice_defects
| Value | Meaning |
|-------|---------|
| `missing_ack_deadline` | Acknowledgement deadline not specified |
| `missing_appeal_instructions` | Appeal instructions not included |
| `missing_waitlist_status` | Waitlist status not communicated |
| `missing_correct_policy` | Policy reference is incorrect or missing |

### notice_quality_source
| Value | Meaning |
|-------|---------|
| `notice_packet_inspection` | Quality determined from inspecting the notice packet directly |
| `message_notice_inspection` | Quality determined from message-based notice records |
| `case_summary_only` | Quality inferred from case summary only |

### evidence_source_order
| Value | Meaning |
|-------|---------|
| `approval_history_folder_notice_audit` | Full chain: approval history → folder → notice → audit |
| `folder_notice_audit` | Folder → notice → audit |
| `audit_only` | Audit events only |

---

## Recruitment Scoped Enums

### candidate_status_source
| Value | Meaning |
|-------|---------|
| `interview_feedback_and_offer` | Candidate status from interview feedback and offer register |
| `case_summary_only` | Candidate status from case summary only |
| `message_only` | Candidate status from messages only |

### candidate_outcome_control
| Value | Meaning |
|-------|---------|
| `committee_decision_with_offer_confirmation` | Outcome confirmed by committee decision and offer status |
| `message_status_only` | Outcome from message status only |
| `case_summary_only` | Outcome from case summary only |

### selected_offer_status
| Value | Meaning |
|-------|---------|
| `accepted` | Offer accepted by candidate |
| `draft` | Offer still in draft |
| `withdrawn` | Offer withdrawn |
| `none` | No offer exists |

### onboarding_handoff
| Value | Meaning |
|-------|---------|
| `create_payroll_precheck` | Create a payroll precheck task for onboarding |
| `create_submitted_assignment_after_acceptance` | Create assignment after offer acceptance |
| `no_payroll_handoff` | No payroll handoff needed |

### payroll_handoff_gate
| Value | Meaning |
|-------|---------|
| `accepted_offer_only` | Handoff triggered by accepted offer alone |
| `accepted_offer_and_submitted_assignment` | Handoff requires both accepted offer and submitted assignment |
| `all_interviewed_candidates` | Handoff includes all interviewed candidates |

### handoff_control_result
| Value | Meaning |
|-------|---------|
| `submitted_handoff_required_after_acceptance` | Submitted handoff needed after offer acceptance |
| `submitted_handoff_required` | Submitted handoff always required |
| `no_handoff_required` | No handoff needed |

### waitlisted_followup_action
| Value | Meaning |
|-------|---------|
| `send_waitlist_notice` | Send initial waitlist notice |
| `reissue_waitlist_notice_not_rejection` | Reissue waitlist notice (not a rejection) |
| `no_action` | No followup needed |

### rejected_followup_action
| Value | Meaning |
|-------|---------|
| `send_rejection_notice` | Send rejection notice |
| `no_action` | No followup needed |
| `reissue_rejection_notice` | Reissue a previously sent rejection notice |

### offer_exclusion_reason_for_waitlisted
| Value | Meaning |
|-------|---------|
| `no_accepted_status_or_offer` | No accepted offer exists for this waitlisted candidate |
| `waitlisted_not_selected` | Candidate was waitlisted, not selected |
| `already_rejected` | Candidate was already rejected |

---

## Folder Scoped Enums

### folder_required_tag_action
| Value | Meaning |
|-------|---------|
| `no_tag_action` | Required tag is present; no action needed |
| `add_required_tag` | Required tag is missing; must be added |

### cost_source
| Value | Meaning |
|-------|---------|
| `recruitment_cost_ledger` | Costs from the recruitment cost ledger |
| `case_summary_only` | Costs from case summary only |
