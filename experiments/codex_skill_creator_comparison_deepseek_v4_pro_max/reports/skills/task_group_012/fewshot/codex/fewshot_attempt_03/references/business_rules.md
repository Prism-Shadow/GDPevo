# PeopleOps Business Rules

This document maps raw API data patterns to normalized business decisions. Apply these rules
in the order given for each domain.

## Onboarding Closeout

### Leave Assignment Selection

1. Filter payroll-ledger records for the target `employee_id` where `record_type` = `Leave assignment`.
2. Sort records by `updated_at` descending.
3. The **effective** leave assignment is the one with status `Approved` for the current period.
4. Records with status `Superseded` or `Draft` are **excluded** and their IDs go into `excluded_leave_ids`.
5. If the effective record is approved, `leave_source` = `leave_assignment_history`,
   `leave_precedence_source` = `approved_assignment_current_period`.
6. `effective_leave_policy` = the `policy_name` field of the approved record.
7. `annual_days` = `approved_leave_days` of the approved record.

### Payroll Assignment Selection

1. Filter payroll-ledger records for the target `employee_id` where `record_type` = `Salary assignment`.
2. Select the record with status `Submitted`. That is the effective payroll assignment.
3. Records with status `Draft` are excluded; their IDs go into `excluded_payroll_ids`.
4. `base_salary` = `base_salary` field of the submitted record.
5. `payroll_status` and `payroll_source_status` = `submitted`.

### Closeout Decision

| Condition | approval_closeout_gate | closeout_action | final_control_result |
|---|---|---|---|
| Leave and payroll both clean (only approved/submitted records) | `approval_sufficient_when_records_clean` | `approve_onboarding_close` | `approve_closeout` |
| Any draft or superseded record contaminates the effective record | `approval_not_sufficient_when_folder_or_notice_defective` | `block_close_and_reissue_notice` | `hold_for_folder_and_notice_defects` |

---

## Policy Case Folder and Notice Review

### Approval History

1. From case detail (`GET /api/cases/{case_id}`), examine the `approvals` array.
2. The final approval is the one with step `Final approval` (or the latest `decided_at` if ambiguous).
3. `final_decision` maps the approval decision:
   - `Approved` → `approved`
   - `Approved with conditions` → `approved_with_conditions`
   - `Rejected` → `rejected`
   - Any other → `held`
4. `approval_authority` = the `approver` field of the final approval.
5. `approval_event_id` = the `approval_id` of the final approval.

### Folder Checklist

1. From case attachments, find the one with `kind` = `Checklist`.
2. Alternatively, fetch documents from `GET /api/documents` and match by case context.
3. Compare `files` against `required_files`:
   - `missing_files` = set difference (required_files minus files).
   - `folder_ready` = `true` iff `missing_files` is empty.
4. Compare `tags` against `required_tags`:
   - `required_tag_present` = `true` iff all required_tags are in tags.
   - If tag missing, `folder_required_tag_action` = `add_required_tag`; else `no_tag_action`.

### Notice Quality

1. From `GET /api/messages`, find the message with matching `case_id`.
2. `notice_quality` = the `quality` field (`valid` or `defective`).
3. `notice_defects` = the `defects` array (empty list if quality is `valid`).
4. `notice_evidence_source` = `notice_packet_inspection` when using messages.

### Audit Events

1. From case detail `audit_events` or `GET /api/audit`, find events with matching `case_id`.
2. For document/notice review, prefer events with `event` = `notice.defect` or `case.close_blocked`.
3. `audit_event_id` = the primary audit event for the case's document/notice scope.
4. `supporting_audit_event_ids` = list containing the primary audit_id.
5. `excluded_audit_event_ids` = audit events whose scope does not match (e.g., payroll events when reviewing documents).
6. `audit_scope` = `document_notice_findings_only`.

### Blockers and Actions

Build `closeout_blockers` from the three conditions:

| If | Add to closeout_blockers |
|---|---|
| `folder_ready` is false | `missing_required_files` |
| `required_tag_present` is false | `missing_required_tags` |
| `notice_quality` is `defective` | `defective_formal_notice` |

When blockers exist:

- `approval_closeout_gate` = `approval_not_sufficient_when_folder_or_notice_defective`
- `final_control_result` = `hold_for_folder_and_notice_defects`
- `next_action` = `block_close_and_reissue_notice`
- `escalation_action` = `open_records_remediation`
- `records_remediation_owner` = the department owning the missing items:
  - Missing files/tags → `Records`
  - Defective notice → `People Ops Compliance`
- `notice_remediation_action` = `reissue_defective_notices` (if notice is defective) else `no_notice_action`

When no blockers:

- `approval_closeout_gate` = `approval_sufficient_when_records_clean`
- `final_control_result` = `approve_closeout`
- `next_action` = `approve_onboarding_close`
- `escalation_action` = `no_action`
- `closeout_blockers` = [] (empty list)

### Evidence Source Order

- When using approvals + folder checklist + notice review + audit: `approval_history_folder_notice_audit`
- When using only folder + notice + audit: `folder_notice_audit`
- When using only audit: `audit_only`

---

## Recruitment Reconciliation

### Candidate Classification

1. From the recruitment entry matching `opening_id`, read the `candidates` array.
2. Map `committee_decision`:
   - `Selected` → `selected_candidate` (single string)
   - `Waitlisted` → `waitlisted_candidates` (list of IDs)
   - `Rejected` → `rejected_candidates` (list of IDs)
3. `candidate_status_source` = `interview_feedback_and_offer`
4. `candidate_outcome_control` = `committee_decision_with_offer_confirmation`

### Offer Details

1. From `offer_register`, find the entry with `candidate_id` matching `selected_candidate`.
2. `offer_id` = the offer's `offer_id`.
3. `offer_base_salary` = the offer's `base_salary`.
4. `selected_offer_status` = the offer's `status` (`accepted`, `draft`, `withdrawn`, or `none` if no offer exists).
5. `offer_exclusion_reason_for_waitlisted`:
   - If waitlisted candidates have no accepted offer: `no_accepted_status_or_offer`
   - If waitlisted not selected: `waitlisted_not_selected`
   - If already rejected: `already_rejected`

### Cost Total

1. `recruitment_cost_total` = sum of all `amount` values in `cost_ledger`.
2. `cost_source` = `recruitment_cost_ledger`.

### Notice Follow-Up

1. From `notice_packets`, identify entries where `status` is `not_sent`.
2. `notice_followup_required` = list of candidate_ids from those entries.
3. Map `notice_type` to follow-up actions:
   - `waitlist` → `waitlisted_followup_action` = `send_waitlist_notice`
   - `rejection` → `rejected_followup_action` = `send_rejection_notice`
4. If notice is already sent, the corresponding action is `no_action`.
5. `notice_quality_source` = `notice_packet_inspection`.

### Payroll Handoff

1. If `selected_offer_status` is `accepted`:
   - `onboarding_handoff` = `create_payroll_precheck`
   - `payroll_handoff_gate` = `accepted_offer_only`
   - `payroll_assignment_status_required` = `submitted_after_acceptance`
   - `draft_payroll_allowed` = `false`
   - `handoff_control_result` = `submitted_handoff_required_after_acceptance`
2. If selected offer is not accepted:
   - `onboarding_handoff` = `no_payroll_handoff`
   - `payroll_handoff_gate` = `accepted_offer_only`
   - `draft_payroll_allowed` = `true`
   - `handoff_control_result` = `no_handoff_required`

---

## Leave Source Precedence

### Policy Rule

`LEAVE-SRC-001` section 2.1: "The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict."

### Decision Logic

1. Find the employee in `/api/employees` by `employee_id`. Note `leave_balance_days`.
2. Find leave assignments for this employee in `/api/payroll-ledgers` (record_type = `Leave assignment`).
3. Find the approved assignment: status = `Approved` for period = `2026`.

**If an approved assignment exists:**

- `effective_leave_policy` = `policy_name` from the approved assignment
- `assignment_id` = `ledger_id` from the approved assignment
- `balance_days` = `approved_leave_days` from the approved assignment
- `precedence_source` = `approved_assignment_over_profile`
- `leave_precedence_source` = `approved_assignment_current_period`
- `profile_policy_ignored` = `true` (because the profile summary is stale)

**If no approved assignment exists:**

- Use the employee profile summary values
- `precedence_source` = `employee_profile_summary`
- `leave_precedence_source` = `profile_summary_current_period`
- `profile_policy_ignored` = `false`

**If neither exists:**

- `precedence_source` = `case_summary_only`
- `leave_precedence_source` = `case_summary_only`

### Audit Events

1. From `/api/audit`, find audit events with matching `employee_id`.
2. The primary leave-scope event has `event` like `leave.profile_mismatch`.
3. `audit_event_id` = that audit_id.
4. `supporting_audit_event_ids` = list containing that audit_id.
5. `excluded_audit_event_ids` = events with non-leave scope (e.g., `folder.tag_missing`, `notice.defect`).
6. `audit_scope` = `leave_source_precedence_only`.
7. `audit_result`: when profile is stale → `profile_summary_stale`.
8. `next_action`: when profile is stale → `update_employee_summary`.

---

## Payroll Assignment Readiness

### Payroll Selection

1. Filter payroll-ledgers for `record_type` = `Salary assignment` and target `employee_id`.
2. The effective record has status `Submitted`.
3. `salary_assignment_id` = `ledger_id` of the submitted record.
4. `base_salary` = `base_salary` of the submitted record.
5. `effective_date` = first day of the `period` field (e.g., ISO month `YYYY-MM` → `YYYY-MM-01`).
6. `excluded_assignment_id` = `ledger_id` of any Draft salary assignment.

### Accrual Check

1. If the submitted record has an `accrual_batch_id` field:
   - `accrual_ready` = `true`
   - `accrual_batch_id` = the `accrual_batch_id` value
2. If absent: `accrual_ready` = `false`, `accrual_batch_id` = empty string.

### Audit Events

1. Find audit events with matching `employee_id` and `event` = `payroll.ready`.
2. `audit_event_id` = the audit_id of that event.
3. `audit_scope` = `payroll_assignment_readiness`.

### Control Result

| Condition | control_result |
|---|---|
| Submitted assignment found, accrual ready | `ready_with_monitoring` |
| Submitted assignment found, accrual not ready or issues found | `hold_for_folder_and_notice_defects` |
| Only draft assignments exist | `hold_for_folder_and_notice_defects` |

### Source Status

- `payroll_source_status` = `submitted` (when using submitted record)
- `draft_exclusion_rule` = `exclude_draft_assignment` (when draft exists and is excluded)

---

## Cross-Cutting Rules

### Record Status Priority

1. **Approved** — Controls the decision. Use it.
2. **Submitted** — Controls when no approved record exists.
3. **Superseded** — A previous approved/submitted that was replaced. Exclude it.
4. **Draft** — Not effective. Always exclude unless a policy explicitly permits drafts.

### Audit Scope Isolation

When a task constrains scope to a single domain (leave, payroll, document/notice), exclude audit
events from other domains from the supporting lists. Cross-module escalation events
(`cross_module.escalation_package`) should also be excluded from domain-specific decisions.
