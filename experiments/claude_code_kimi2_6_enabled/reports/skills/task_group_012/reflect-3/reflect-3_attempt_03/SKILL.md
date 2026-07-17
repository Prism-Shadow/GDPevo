# PeopleOps Lifecycle Audit Skill

## Overview
Audit and reconcile employee lifecycle cases (onboarding, leave, payroll, recruitment) using the PeopleOps Console API. All data is fetched from REST endpoints; no UI interaction is required.

## Environment
- Base URL: `<TASK_ENV_BASE_URL>` (resolves to the staged GDPevo URL)
- API endpoints are under `/api/`

## Core API Endpoints
| Endpoint | Data |
|----------|------|
| `/api/employees` | Employee profiles, status, leave balances |
| `/api/cases` | All cases |
| `/api/cases/{case_id}` | Individual case with approvals, attachments, audit_events |
| `/api/documents` | Folder readiness, files, tags |
| `/api/messages` | Formal notices, defects, quality |
| `/api/audit` | All audit events |
| `/api/audit/{audit_id}` | Individual audit event |
| `/api/recruitment` | Recruitment openings with candidates, cost ledger, offer register, notice packets |
| `/api/payroll-ledgers` | Leave assignments and salary assignments |
| `/api/policies` | Active policies (LEAVE-SRC-001, PAY-SRC-001, POL-DOCS-2026, HR-POL-014) |
| `/api/summary` | System counts |

## Task Types and Rules

### 1. Onboarding Closeout (Employee Lifecycle)
**Goal:** Verify leave setup and payroll setup before approving onboarding close.

**Rules:**
- Query `/api/payroll-ledgers` for the employee's leave assignments and salary assignments.
- **Leave precedence:** The latest **Approved** or **Submitted** leave assignment for the period controls. Exclude **Draft**, **Voided**, and **Superseded** records.
- **Payroll precedence:** Use the current **Submitted** salary assignment. Exclude **Draft** and **Superseded** records.
- `leave_precedence_source`: `"approved_assignment_current_period"` when an approved assignment exists.
- `payroll_source_status`: `"submitted"` for the authoritative assignment.
- `approval_closeout_gate`: `"approval_sufficient_when_records_clean"` when records are clean (no folder/notice defects).
- `final_control_result`: `"approve_closeout"` when records are clean.
- `closeout_action`: `"approve_onboarding_close"` when clean; otherwise block or remediate.

### 2. Case Review (Folder + Notice Audit)
**Goal:** Review a case for folder readiness and formal notice quality.

**Rules:**
- Get case details from `/api/cases/{case_id}` (includes approvals, attachments, audit_events).
- Check folder readiness via `/api/documents` (compare `files` vs `required_files`, `tags` vs `required_tags`).
- Check notice quality via `/api/messages` (look for `quality` and `defects`).
- `folder_ready`: true only if all required files AND required tags are present.
- `missing_files`: list files in `required_files` but not in `files`.
- `required_tag_present`: true only if all `required_tags` are in `tags`.
- `notice_quality`: `"defective"` if any defects exist; `"valid"` otherwise.
- `notice_defects`: exact values from message `defects` array.
- `approval_closeout_gate`: `"approval_not_sufficient_when_folder_or_notice_defective"` if either folder or notice has issues.
- `closeout_blockers`: include `"missing_required_files"`, `"missing_required_tags"`, and/or `"defective_formal_notice"` as applicable.
- `next_action`: `"block_close_and_reissue_notice"` when notice is defective; `"open_records_remediation"` when folder is incomplete.
- `escalation_action`: `"open_records_remediation"` for folder issues; `"block_close_and_reissue_notice"` for notice issues; `"no_action"` if clean.
- `final_control_result`: `"hold_for_folder_and_notice_defects"` when there are blockers; `"approve_closeout"` when clean.
- `audit_event_id`: the primary audit event for this case.
- `supporting_audit_event_ids`: include the primary audit event ID (and any other directly supporting events).
- `excluded_audit_event_ids`: include adjacent audit events from unrelated cases/employees that should not influence this decision.
- `evidence_source_order`: `"approval_history_folder_notice_audit"` when all sources are relevant.
- `notice_evidence_source`: `"notice_packet_inspection"` when inspecting notice packets; `"message_notice_inspection"` when inspecting messages.

### 3. Recruitment Reconciliation
**Goal:** Reconcile recruitment outcomes for an opening.

**Rules:**
- Get recruitment data from `/api/recruitment` (returns openings with candidates, cost_ledger, offer_register, notice_packets, payroll_precheck_records).
- `selected_candidate`: candidate with `committee_decision: "Selected"`.
- `waitlisted_candidates`: candidates with `committee_decision: "Waitlisted"`.
- `rejected_candidates`: candidates with `committee_decision: "Rejected"`.
- `offer_id` / `offer_base_salary`: from `offer_register` for the selected candidate.
- `selected_offer_status`: from offer register (`"accepted"`, `"draft"`, `"withdrawn"`, `"none"`).
- `recruitment_cost_total`: sum of all `amount` values in `cost_ledger`.
- `cost_source`: `"recruitment_cost_ledger"`.
- `notice_followup_required`: candidate IDs from `notice_packets` where `status` is `"not_sent"` or `"draft_reissue_required"`.
- `waitlisted_followup_action`: `"send_waitlist_notice"` for waitlisted candidates needing notice; `"reissue_waitlist_notice_not_rejection"` when a defective waitlist notice exists.
- `rejected_followup_action`: `"send_rejection_notice"` for rejected candidates needing notice; `"no_action"` if already sent.
- `candidate_status_source`: `"interview_feedback_and_offer"` when both candidate review and offer data exist.
- `candidate_outcome_control`: `"committee_decision_with_offer_confirmation"` when committee decisions are confirmed by offer register.
- `onboarding_handoff`: `"create_payroll_precheck"` for accepted offers (initial payroll precheck); `"create_submitted_assignment_after_acceptance"` for creating submitted assignment.
- `payroll_handoff_gate`: `"accepted_offer_only"` when only the accepted offer matters for handoff; `"accepted_offer_and_submitted_assignment"` when both are required.
- `payroll_assignment_status_required`: `"submitted_after_acceptance"` per policy PAY-SRC-001.
- `draft_payroll_allowed`: false (draft prechecks do not satisfy the assignment gate per PAY-SRC-001).
- `offer_exclusion_reason_for_waitlisted`: `"no_accepted_status_or_offer"` for waitlisted candidates (no accepted offer); `"waitlisted_not_selected"` when explicitly waitlisted.
- `handoff_control_result`: `"submitted_handoff_required_after_acceptance"` when a submitted assignment is needed after acceptance.
- `notice_quality_source`: `"notice_packet_inspection"` when inspecting notice_packets from recruitment data.

### 4. Leave Source Precedence
**Goal:** Determine authoritative leave policy and balance when profile summary conflicts with assignment.

**Rules:**
- Query `/api/payroll-ledgers` for leave assignments and `/api/employees` for profile.
- Query `/api/cases/{case_id}` and `/api/audit/{audit_id}` for audit detail.
- Policy LEAVE-SRC-001: latest approved or submitted leave assignment controls. Draft/voided/obsolete records are excluded.
- `precedence_source`: `"approved_assignment_over_profile"` when approved assignment overrides stale profile.
- `profile_policy_ignored`: true when the profile summary is stale and the approved assignment controls.
- `leave_precedence_source`: `"approved_assignment_current_period"` for the current period's approved assignment.
- `audit_result`: `"profile_summary_stale"` when audit confirms profile is stale; `"ready_with_monitoring"` when ready; `"block_close"` when blocked.
- `next_action`: `"update_employee_summary"` when profile is stale; `"open_records_remediation"` when records need fixing; `"no_action"` when clean.
- `audit_scope`: `"leave_source_precedence_only"` for leave precedence decisions.
- `supporting_audit_event_ids`: include the primary audit event ID that supports the leave-scope decision.
- `excluded_audit_event_ids`: include adjacent document/notice audit events that are not relevant to the leave-scope decision (e.g., folder.tag_missing events).

### 5. Payroll Assignment Readiness
**Goal:** Verify payroll assignment and accrual readiness.

**Rules:**
- Query `/api/payroll-ledgers` for salary assignments.
- Query `/api/cases/{case_id}` and `/api/audit/{audit_id}` for audit detail.
- Policy PAY-SRC-001: use current submitted salary assignment. Draft planning assignments do not affect payroll readiness.
- `salary_assignment_id`: the submitted assignment ID.
- `base_salary`: from the submitted assignment.
- `effective_date`: from the submitted assignment's `updated_at` or period start.
- `excluded_assignment_id`: the draft/superseded assignment ID.
- `payroll_source_status`: `"submitted"`.
- `draft_exclusion_rule`: `"exclude_draft_assignment"`.
- `accrual_ready`: true when audit confirms readiness with monitoring.
- `accrual_batch_id`: from the submitted assignment's `accrual_batch_id` field.
- `audit_event_id`: the payroll readiness audit event.
- `control_result`: `"ready_with_monitoring"` when audit says ready with monitoring; `"hold_for_folder_and_notice_defects"` when blocked; `"approve_closeout"` when fully approved.
- `audit_scope`: `"payroll_assignment_readiness"`.

## General Principles
1. **Always prefer submitted/approved records over drafts.** Draft records are excluded per policy.
2. **Use the case detail endpoint** (`/api/cases/{case_id}`) for approvals, attachments, and embedded audit events.
3. **Use the audit detail endpoint** (`/api/audit/{audit_id}`) for precise audit detail.
4. **For enum fields,** use the exact normalized labels from the answer template; never use free text.
5. **For lists,** ensure exact values and correct ordering when the judge is sensitive to it.
6. **Supporting vs excluded audit events:** Include the primary audit event in `supporting_audit_event_ids`; exclude unrelated cross-case audit events in `excluded_audit_event_ids`.
