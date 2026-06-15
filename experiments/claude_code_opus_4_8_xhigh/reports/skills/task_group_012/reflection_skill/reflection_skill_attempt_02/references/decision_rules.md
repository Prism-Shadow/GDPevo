# Decision rules by subsystem

Detailed, transferable rules for each PeopleOps Console task shape. Read the
SKILL.md first; come here when you need the full logic for a given subsystem.
No concrete entity is named here — resolve real IDs at run time.

## Table of contents
1. Onboarding closeout
2. Policy / remote-work case review
3. Leave source precedence
4. Recruitment outcome reconciliation
5. Payroll / accrual readiness
6. Escalation owner / SLA from an audit package

---

## 1. Onboarding closeout

Goal: pick the authoritative leave and payroll setup, list exclusions, decide the
closeout action.

- Leave: among an employee's leave assignments, the **approved** assignment for
  the current period is authoritative. Exclude **superseded** and **draft**
  assignments. The effective leave policy name and annual days come from the
  approved assignment. `leave_source` = leave_assignment_history;
  `leave_precedence_source` = approved_assignment_current_period.
- Payroll: the **submitted** salary assignment controls base salary; exclude the
  **draft**. `payroll_status` / `payroll_source_status` = submitted.
- Records-clean check: if there is no case folder / notice defect tied to this
  employee, records are clean.
  - `closeout_action` = approve_onboarding_close.
  - `approval_closeout_gate` = approval_sufficient_when_records_clean.
  - `final_control_result` = approve_closeout.
- If a folder/notice defect exists, fall into the case-review gating (section 2):
  block and route to remediation instead of approving.

## 2. Policy / remote-work case review

Goal: judge folder readiness and formal-notice quality on top of an approval, and
decide whether closeout may proceed.

- Approval: read the final approval event — its `approver` is the approval
  authority, its decision maps to the normalized `final_decision`
  ("Approved with conditions" -> approved_with_conditions). The approval event ID
  is reported verbatim.
- Folder readiness (set comparison):
  - `folder_ready` = (required_files ⊆ files) AND (required_tags ⊆ tags).
  - `missing_files` = required_files − files.
  - `required_tag_present` = required_tags ⊆ tags.
  - If a file is missing but the tag is present: `folder_required_tag_action` =
    no_tag_action and the only file-related blocker is missing_required_files.
- Notice quality: from the notice packet's `quality` and `defects`.
  - `notice_quality` = valid | defective.
  - `notice_defects` = the packet's defect codes (normalized vocabulary only).
  - `notice_evidence_source` = notice_packet_inspection (structured packet),
    even if delivered through the messages endpoint.
- Audit: the in-case audit event that records the defect is the supporting event.
  - `audit_event_id` and `supporting_audit_event_ids` = that event.
  - `excluded_audit_event_ids` = adjacent in-case events from a different scope;
    `[]` if none. Never include events from other cases/employees.
  - `audit_scope` = document_notice_findings_only.
- Gating when any folder file/tag missing OR notice defective:
  - `approval_closeout_gate` = approval_not_sufficient_when_folder_or_notice_defective.
  - `final_control_result` = hold_for_folder_and_notice_defects.
  - `next_action` = block_close_and_reissue_notice.
  - `closeout_blockers` = the set actually present (missing_required_files /
    missing_required_tags / defective_formal_notice).
  - `escalation_action` = open_records_remediation when a folder/file defect
    exists (this is the structural escalation; distinct from the notice fix).
  - `records_remediation_owner` = the team that uploaded/owns the folder checklist
    (the `uploaded_by` on the folder attachment), not the case owner.
  - `notice_remediation_action` = reissue_defective_notices when the notice is
    defective.
- `evidence_source_order` = approval_history_folder_notice_audit (approval first,
  then folder, then notice, then audit).

## 3. Leave source precedence

Goal: decide whether an approved assignment or the profile summary is
authoritative for the effective leave state.

- The **approved** leave assignment overrides a **stale** employee profile
  summary when the ledger, policy document, and audit detail confirm it.
  - `precedence_source` = approved_assignment_over_profile.
  - `leave_precedence_source` = approved_assignment_current_period.
  - `profile_policy_ignored` = true.
  - Effective policy name, assignment ID, and balance_days all come from the
    approved assignment.
- Audit:
  - `audit_result` = profile_summary_stale (the audit confirms the profile is
    stale and the approved assignment controls).
  - `supporting_audit_event_ids` = the leave-scope audit event(s).
  - `excluded_audit_event_ids` = adjacent document/notice audit event(s) for the
    same employee — out of the leave decision's scope.
  - `audit_scope` = leave_source_precedence_only.
- `next_action` = update_employee_summary (correct the stale profile).
- Note: other ledger rows (superseded / submitted / approved adjustments) may
  exist, but the named authoritative approved assignment supplies the balance.

## 4. Recruitment outcome reconciliation

Goal: reconcile candidate outcomes, cost, follow-up, and payroll handoff for an
opening.

- Candidate outcomes from committee decision + offer confirmation:
  `selected_candidate`, `waitlisted_candidates`, `rejected_candidates` (candidate
  IDs only, as sets).
  - `candidate_status_source` = interview_feedback_and_offer.
  - `candidate_outcome_control` = committee_decision_with_offer_confirmation.
- Offer: the accepted offer in the offer register supplies `offer_id`,
  `offer_base_salary`, and `selected_offer_status` = accepted.
- Cost: `recruitment_cost_total` = sum of ALL cost-ledger line amounts.
  `cost_source` = recruitment_cost_ledger.
- Notices:
  - `notice_followup_required` = candidates whose notice packet status is
    not-sent (typically waitlisted + rejected).
  - `waitlisted_followup_action` = send_waitlist_notice;
    `rejected_followup_action` = send_rejection_notice (from packet required_action).
  - `notice_quality_source` = notice_packet_inspection.
- Payroll handoff after acceptance (drafts/prechecks never satisfy the gate):
  - `onboarding_handoff` = create_submitted_assignment_after_acceptance.
  - `payroll_handoff_gate` = accepted_offer_and_submitted_assignment.
  - `payroll_assignment_status_required` = submitted_after_acceptance.
  - `draft_payroll_allowed` = false.
  - `handoff_control_result` = submitted_handoff_required_after_acceptance.
- `offer_exclusion_reason_for_waitlisted` = no_accepted_status_or_offer.

## 5. Payroll / accrual readiness

Goal: pick the controlling payroll assignment and judge accrual-batch readiness.

- The **submitted** assignment controls; exclude the **draft**.
  - `salary_assignment_id` / `base_salary` from the submitted row.
  - `excluded_assignment_id` = the draft.
  - `payroll_source_status` = submitted; `draft_exclusion_rule` =
    exclude_draft_assignment.
  - `effective_date` = derived from the submitted row (period start / updated
    date) when there is no explicit effective-date field; format it as the API
    presents the date.
- Accrual readiness from the audit event:
  - `accrual_ready`, `accrual_batch_id`, and `control_result` come from the
    payroll-readiness audit event. When the submitted assignment matches the
    accrual batch, `control_result` = ready_with_monitoring.
  - `audit_scope` = payroll_assignment_readiness.

## 6. Escalation owner / SLA from an audit package

When a template asks for an escalation owner or an SLA value:

1. Open the audit package / audit event detail tied to the case or decision.
2. Read the owner/team and SLA verbatim from that record.
3. If the field is an enum, map the owner to the template's allowed_values; if it
   is a free string, copy exactly. Prefer the most specific in-scope record over a
   summary. Never invent or default an SLA number or owner.
