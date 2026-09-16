# Policies and Business Rules

## Extracted Policy Rules

### LEAVE-SRC-001: Leave Source Precedence

**Section 2.1 Assignment source**:
The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict.

**Application**: When an employee has multiple leave-assignment ledger entries for the same period, select the one with status Approved. If no Approved exists, use Submitted. Exclude Draft and Superseded records. The policy_name from the selected ledger entry is the effective_leave_policy. The approved_leave_days from that entry is the authoritative annual_days. Excluded ledger IDs go into excluded_leave_ids.

### PAY-SRC-001: Payroll Assignment Source

**Section 3.4 Submitted salary source**:
Use the current submitted salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks.

**Application**: For an employee, select the salary-assignment ledger entry with status Submitted. Its base_salary is authoritative. Exclude Draft entries into excluded_payroll_ids. The payroll source status is submitted.

**Section 4.2 Recruiting handoff gate**:
Recruiting payroll handoff is created only after a selected candidate has an accepted offer. The handoff must be submitted; draft prechecks do not satisfy the assignment gate.

**Application**: Only the candidate with committee_decision Selected AND an accepted offer triggers a payroll handoff. The handoff must be submitted. Draft payroll_precheck_records are excluded. The onboarding_handoff is create_payroll_precheck when there is no submitted assignment yet; create_submitted_assignment_after_acceptance when a submitted assignment follows acceptance; no_payroll_handoff when not applicable.

### POL-DOCS-2026: Lifecycle Folder Checklist

**Section 5.1 Required evidence**:
A folder is not ready unless all required files and required tags shown in the folder checklist are present.

**Application**: Compare the document folder files array against required_files. Compare tags array against required_tags. Missing files go into missing_files. If all tags present, required_tag_present is true and folder_required_tag_action is no_tag_action; otherwise add_required_tag.

### HR-POL-014: Remote Work Policy

**Section 4.2 Domestic jurisdiction**:
Remote work is limited to approved domestic tax jurisdictions unless an exception is approved.

**Section 7.1 Executive exceptions**:
International exceptions require executive approval, time limits, tax equalization, VPN-only access, quarterly compliance review, appeal instructions, and acknowledgement deadline in the formal notice.

**Application**: Formal notices for remote-work cases must include appeal instructions and acknowledgement deadline. Missing either is a defect. Approved with conditions but defective notice means the gate is approval_not_sufficient_when_folder_or_notice_defective and next action is block_close_and_reissue_notice.

## Enum Value Definitions

### Leave Source
- leave_assignment_history: Source is the leave assignment records in the payroll ledger (authoritative)
- employee_profile_summary: Source is the employee profile record (may be stale)
- case_summary_only: Only the case summary was usable

### Leave Precedence Source
- approved_assignment_current_period: An approved leave assignment for the current period controls
- approved_assignment_over_profile: An approved assignment overrides the profile
- profile_summary_current_period: The profile summary for the current period controls
- case_summary_only: Only the case summary was usable

### Payroll Status / Payroll Source Status
- submitted: A submitted salary assignment (authoritative)
- draft: A draft salary assignment (excluded)
- superseded: A superseded salary assignment (excluded)

### Approval Gate / Closeout Gate
- approval_sufficient_when_records_clean: All records are clean; closeout can proceed
- approval_not_sufficient_when_folder_or_notice_defective: Folder or notice has defects; block closeout

### Final Control Result
- approve_closeout: Closeout approved, no blockers
- hold_for_folder_and_notice_defects: Hold for folder or notice defects
- ready_with_monitoring: Ready but monitor

### Notice Quality
- valid: Notice is valid and complete
- defective: Notice has defects

### Notice Defects
- missing_ack_deadline: Notice lacks acknowledgement deadline
- missing_appeal_instructions: Notice lacks appeal instructions
- missing_waitlist_status: Notice lacks waitlist status
- missing_correct_policy: Notice references wrong policy

### Notice Evidence Source
- notice_packet_inspection: Inspection of notice packets
- message_notice_inspection: Inspection of message-based notices
- case_summary_only: Only the case summary

### Audit Scope
- document_notice_findings_only: Audit findings about documents and notices only
- leave_source_precedence_only: Audit findings about leave source precedence only
- payroll_assignment_readiness: Audit findings about payroll assignment readiness

### Evidence Source Order
- approval_history_folder_notice_audit: Check approvals, then folder, then notice, then audit
- folder_notice_audit: Check folder, then notice, then audit
- audit_only: Check audit only

### Candidate Outcome Control
- committee_decision_with_offer_confirmation: Committee decision confirmed by offer register
- message_status_only: Based on message status only
- case_summary_only: Based on case summary only

### Candidate Status Source
- interview_feedback_and_offer: Interview feedback and offer register (authoritative)
- case_summary_only: Only case summary
- message_only: Only messages

### Cost Source
- recruitment_cost_ledger: Recruitment cost ledger values
- case_summary_only: Only case summary

### Selected Offer Status
- accepted: Offer accepted
- draft: Offer in draft
- withdrawn: Offer withdrawn
- none: No offer

### Onboarding Handoff
- create_payroll_precheck: Create a payroll precheck
- create_submitted_assignment_after_acceptance: Create submitted assignment after acceptance
- no_payroll_handoff: No payroll handoff needed

### Payroll Handoff Gate
- accepted_offer_only: Only accepted offers create a handoff
- accepted_offer_and_submitted_assignment: Both accepted offer and submitted assignment needed
- all_interviewed_candidates: All interviewed candidates

### Payroll Assignment Status Required
- submitted_after_acceptance: Must be submitted after acceptance
- submitted: Must be submitted
- draft_allowed: Draft allowed

### Draft Exclusion Rule
- exclude_draft_assignment: Exclude draft assignments
- draft_allowed: Draft allowed
- exclude_superseded_only: Only exclude superseded

### Offer Exclusion Reason
- no_accepted_status_or_offer: No accepted status or offer exists
- waitlisted_not_selected: Waitlisted, not selected
- already_rejected: Already rejected

### Closeout Action / Next Action
- approve_onboarding_close: Approve the onboarding closeout
- block_close_and_reissue_notice: Block close and reissue notice
- open_records_remediation: Open a records remediation

### Closeout Blockers
- missing_required_files: Required files are missing from folder
- missing_required_tags: Required tags are missing from folder
- defective_formal_notice: Formal notice is defective

### Folder Required Tag Action
- no_tag_action: Tags are present; no action needed
- add_required_tag: Tags missing; add required tag

### Escalation Action
- open_records_remediation: Open records remediation
- block_close_and_reissue_notice: Block close and reissue notice
- no_action: No escalation needed

### Records Remediation Owner
- Records: Records team
- People Ops Compliance: People Ops Compliance team
- Payroll QA: Payroll QA team

### Notice Remediation Action
- reissue_defective_notices: Reissue defective notices
- no_notice_action: No notice action needed
- send_new_offer_notice: Send a new offer notice

### Waitlisted Followup Action
- send_waitlist_notice: Send waitlist notice
- reissue_waitlist_notice_not_rejection: Reissue waitlist notice (not a rejection)
- no_action: No action needed

### Rejected Followup Action
- send_rejection_notice: Send rejection notice
- no_action: No action needed
- reissue_rejection_notice: Reissue rejection notice

### Handoff Control Result
- submitted_handoff_required_after_acceptance: Submitted handoff required after acceptance
- submitted_handoff_required: Submitted handoff required
- no_handoff_required: No handoff required

## Decision Logic

### Leave assignment selection
1. Filter payroll-ledgers by employee_id and record_type = Leave assignment
2. From those, select status = Approved (preferred) or Submitted (fallback)
3. Exclude all Draft and Superseded records into excluded_leave_ids
4. Read annual_days from approved_leave_days, policy_name as effective_leave_policy

### Salary assignment selection
1. Filter payroll-ledgers by employee_id and record_type = Salary assignment
2. From those, select status = Submitted
3. Exclude all Draft records into excluded_payroll_ids
4. Read base_salary and effective_date from the selected entry

### Audit event selection
1. Fetch all audit events
2. Match by case_id for case-scoped tasks, or by employee_id for employee-scoped tasks
3. Classify by event type: notice.defect maps to document_notice_findings_only, leave.profile_mismatch maps to leave_source_precedence_only, payroll.ready maps to payroll_assignment_readiness
4. For leave-source decisions, include audits with leave scope and exclude audits with document/notice scope
5. For document/notice decisions, include audits with document/notice scope and exclude audits with leave or payroll scope

### Cross-module / escalation audit events
Some audit events (like AUD-XMODULE-77 with event cross_module.escalation_package) reference multiple employees and serve as umbrella alerts. They should be noted but their specific employee_id is multiple. When such events exist, they may flag broader lifecycle risks.
