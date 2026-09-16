# PeopleOps Business Rules

## Table of Contents

- [Record Precedence](#record-precedence)
- [Draft Exclusion](#draft-exclusion)
- [Onboarding Closeout](#onboarding-closeout)
- [Case Folder and Notice Review](#case-folder-and-notice-review)
- [Recruitment Reconciliation](#recruitment-reconciliation)
- [Leave Source Precedence](#leave-source-precedence)
- [Payroll Assignment and Accrual Readiness](#payroll-assignment-and-accrual-readiness)

---

## Record Precedence

When multiple records describe the same fact, resolve by authority tier:

| Tier | Record type | beats |
|------|------------|-------|
| 1 | Submitted/approved leave assignment (from ledger) | Profile summary, case summary |
| 2 | Submitted payroll assignment | Draft payroll, superseded payroll |
| 3 | Approved assignment with supporting audit + policy + ledger | Stale profile summary |
| 4 | Notice packet inspection | Message-based notice inspection, case summary |
| 5 | Interview feedback + offer register | Case summary, message status |
| 6 | Recruitment cost ledger | Case summary |

Any record with status draft is never authoritative. Any record with status
superseded is never authoritative.

Profile summaries (employee_profile_summary) are stale by default. An
approved leave assignment with supporting evidence (audit log, policy document,
ledger) overrides a profile summary every time.

---

## Draft Exclusion

- Draft leave assignments: always exclude; list their IDs in
  excluded_leave_ids or excluded_assignment_id
- Draft payroll assignments: always exclude; list their IDs in
  excluded_payroll_ids or excluded_assignment_id
- Draft offers in recruitment: not authoritative; exclude from selected
  candidate determination
- Draft records never affect base_salary, annual_days, balance_days,
  accrual_ready, or any effective_* field

When an answer template asks for draft_exclusion_rule, the only correct
answer is exclude_draft_assignment unless the evidence explicitly allows
drafts for that specific scenario.

---

## Onboarding Closeout

For an employee onboarding closeout:

1. Read the employee from GET /api/employees
2. From the employee's leave_assignments, find the submitted (non-draft)
   assignment matching the current period
3. If multiple submitted assignments exist, pick the most recent one by date
4. Exclude all draft leave assignments in excluded_leave_ids
5. Read the policy from GET /api/policies to confirm the policy name and annual
   leave days
6. From the employee's payroll_assignments, find the submitted assignment;
   use its base_salary. Exclude draft payroll assignments
7. Set payroll_status to submitted when using a submitted record
8. Gate check: if leave and payroll records are both clean (no drafts
   contaminating the record, submitted assignments exist):
   - closeout_action: approve_onboarding_close
   - approval_closeout_gate: approval_sufficient_when_records_clean
   - final_control_result: approve_closeout
9. leave_source: leave_assignment_history (not profile summary)
10. leave_precedence_source: approved_assignment_current_period
    (not profile_summary_current_period)
11. payroll_source_status: submitted

---

## Case Folder and Notice Review

For case review:

### Evidence source order

Always follow: approval history to folder to notice packets to audit log.
This corresponds to the enum value approval_history_folder_notice_audit.

### Folder readiness

1. Read the case detail from GET /api/cases/{case_id}
2. Inspect the case's folder.files array
3. Cross-reference with GET /api/documents to confirm which files exist
4. Check folder.tags for required tags
5. folder_ready is true only when all required files are present
6. missing_files lists filenames of required-but-absent files
7. required_tag_present is true when the required tag exists; otherwise
   set folder_required_tag_action to add_required_tag

### Notice quality

1. Inspect formal notice packets from the case's notices array
2. Also inspect GET /api/notifications for matching case notices
3. Always use notice packet inspection: set notice_evidence_source to
   notice_packet_inspection, never message_notice_inspection or
   case_summary_only
4. Check each notice for defects:
   - missing_ack_deadline: no acknowledgment deadline set
   - missing_appeal_instructions: no appeal instructions included
   - missing_waitlist_status: waitlist status not communicated
   - missing_correct_policy: wrong or missing policy reference
5. If any defect found, set notice_quality to defective
6. notice_defects lists all applicable defect labels

### Gate and final decision

1. If folder is not ready OR notice is defective:
   - approval_closeout_gate: approval_not_sufficient_when_folder_or_notice_defective
   - final_control_result: hold_for_folder_and_notice_defects
   - closeout_blockers: include missing_required_files (if applicable),
     missing_required_tags (if applicable), defective_formal_notice
     (if applicable)
2. next_action: block_close_and_reissue_notice when notice is defective;
   open_records_remediation when folder has missing files
3. escalation_action: open_records_remediation when files missing;
   block_close_and_reissue_notice when notice defective
4. records_remediation_owner: Records for missing files
5. notice_remediation_action: reissue_defective_notices when notice defective
6. Reading the case's approval_history: find the final decision,
   approval authority, and approval event ID

### Audit scope for case review

1. Find the relevant audit event from GET /api/audit by matching the case ID
2. The audit scope for case-folder-notice review is always
   document_notice_findings_only
3. supporting_audit_event_ids includes the audit event that supports the
   document/notice findings
4. excluded_audit_event_ids lists any audit events with different scopes
   (leave, payroll) that should not influence this decision

---

## Recruitment Reconciliation

For recruitment opening reconciliation:

### Candidate determinations

1. Read GET /api/recruitment and find the opening by opening_id
2. For each candidate, determine status from interview feedback and offer status:
   - selected: candidate with an accepted offer
   - waitlisted: candidate explicitly waitlisted, no accepted offer
   - rejected: candidate explicitly rejected
3. Set candidate_status_source to interview_feedback_and_offer
4. Set candidate_outcome_control to committee_decision_with_offer_confirmation

### Offer and salary

1. Find the offer for the selected candidate (offer_id)
2. offer_base_salary is the selected candidate's accepted offer salary
3. selected_offer_status must be accepted for the selected candidate

### Cost

1. Sum all line-item amount values from the cost_ledger for the opening
2. Set cost_source to recruitment_cost_ledger

### Notice follow-up

1. Set notice_quality_source to notice_packet_inspection
2. Inspect notice packets for each waitlisted and rejected candidate
3. Candidates needing follow-up notices go in notice_followup_required
   (candidate IDs only)
4. waitlisted_followup_action: send_waitlist_notice
5. rejected_followup_action: send_rejection_notice

### Payroll handoff

1. Only the selected (accepted-offer) candidate triggers payroll handoff
2. onboarding_handoff: create_payroll_precheck
3. payroll_handoff_gate: accepted_offer_only
4. payroll_assignment_status_required: submitted_after_acceptance
5. draft_payroll_allowed: false
6. offer_exclusion_reason_for_waitlisted: no_accepted_status_or_offer
7. handoff_control_result: submitted_handoff_required_after_acceptance

---

## Leave Source Precedence

For leave-source dispute resolution:

1. Read GET /api/employees for the employee
2. Compare the employee's profile_summary leave policy/balance against
   their leave_assignments
3. Read GET /api/policies/{policy_id} to confirm the assignment's policy
4. Read GET /api/payroll-ledgers (or the employee's payroll data) to confirm
   the assignment ledger entry
5. Read GET /api/audit for audit events matching the employee ID
6. Rule: when an approved leave assignment exists AND the ledger, policy
   document, and audit detail all confirm it, the assignment overrides the
   profile summary
7. effective_leave_policy: from the approved assignment
8. assignment_id: the approved assignment ID
9. balance_days: from the approved assignment
10. precedence_source: approved_assignment_over_profile
11. leave_precedence_source: approved_assignment_current_period
12. profile_policy_ignored: true when the profile summary is stale
13. audit_result: profile_summary_stale when the profile is stale
14. next_action: update_employee_summary to bring the profile in sync

### Audit scope for leave precedence

1. audit_scope: leave_source_precedence_only
2. supporting_audit_event_ids: the audit event IDs that confirm the leave
   assignment (matching the leave scope)
3. excluded_audit_event_ids: audit events with other scopes (document_notice)
   that should not influence the leave decision

---

## Payroll Assignment and Accrual Readiness

For payroll validation:

1. Read GET /api/employees for the employee's payroll_assignments
2. Select the submitted payroll assignment; exclude all drafts
3. salary_assignment_id: the submitted assignment ID
4. base_salary: from the submitted assignment
5. effective_date: from the submitted assignment
6. excluded_assignment_id: the draft assignment ID
7. payroll_source_status: submitted
8. draft_exclusion_rule: exclude_draft_assignment

### Accrual readiness

1. Check the submitted payroll assignment for accrual_batch_id and accrual_ready
2. If the submitted assignment has a valid accrual batch and
   accrual_ready is true, accrual can proceed
3. accrual_batch_id: from the submitted assignment (if present)

### Audit scope for payroll

1. audit_scope: payroll_assignment_readiness
2. Find the relevant audit event from GET /api/audit matching the employee ID
   and payroll scope
3. control_result: ready_with_monitoring when submitted payroll is valid
   and accrual is ready
