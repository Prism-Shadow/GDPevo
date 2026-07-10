# ERP HR Employee Lifecycle & Policy Operations — Skill Guide

## Overview

This skill covers PeopleOps lifecycle closeout verification, leave-source precedence,
policy-case folder/notice review, recruitment reconciliation, and payroll-assignment
readiness checks against the Northwind People HRMS.

**Environment:** Use the API at `GDPEVO_ENV_BASE_URL` (do not use localhost). All data
is read-only via GET endpoints.

---

## API Reference

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/manifest` | Business modules, record counts, entry points |
| `GET /api/summary` | Case counts by status, departments, record counts |
| `GET /api/employees` | All employee profile summaries (list) |
| `GET /api/cases` | All cases (list) |
| `GET /api/cases/<case_id>` | Single case with approvals, attachments, audit_events, comments |
| `GET /api/cases/<case_id>/comments` | Case comments only |
| `GET /api/policies` | All policy documents |
| `GET /api/policies/<policy_id>` | Single policy by ID |
| `GET /api/payroll-ledgers` | All leave/salary assignments and adjustment records |
| `GET /api/recruitment` | Recruitment openings with candidates, offers, cost ledgers, notices |
| `GET /api/documents` | Document folders with required/actual files and tags |
| `GET /api/messages` | Formal notice messages with defect information |
| `GET /api/notifications` | Same dataset as /api/messages |
| `GET /api/audit` | All audit events |
| `GET /api/audit/<event_id>` | Single audit event by ID |
| `GET /api/attachments/<attachment_id>` | Raw attachment text content |

**Important:** There is NO filtering query parameter on list endpoints. Fetch the full
collection and filter client-side by `employee_id`, `case_id`, `record_type`, etc.

### Record-Type Taxonomy in Payroll Ledgers

The `/api/payroll-ledgers` endpoint mixes multiple record types. Filter by `record_type`:

| `record_type` | Purpose | Relevant fields |
|---|---|---|
| `"Leave assignment"` | Authoritative leave entitlement | `ledger_id`, `policy_name`, `approved_leave_days`, `status`, `period` |
| `"Salary assignment"` | Authoritative payroll/salary | `ledger_id`, `base_salary`, `status`, `period`, `accrual_batch_id` |
| `"HRMS leave ledger"` | **Not authoritative** — system-level adjustments; ignore for policy decisions |
| `"Payroll worksheet"` | **Not authoritative** — planning data; ignore for policy decisions |
| `"People Ops adjustment"` | **Not authoritative** — operational tweaks; ignore for policy decisions |

**Only `"Leave assignment"` and `"Salary assignment"` records are authoritative.**
Ignore all other record types when determining policy, leave entitlement, or payroll.

---

## Core Business Rules

### 1. Leave Source Precedence (LEAVE-SRC-001)

**Rule:** The latest **approved** (or submitted, in order of recency) leave assignment
for the current period controls. The employee profile summary is a **cached snapshot**
and is stale when an approved leave assignment exists for the same period.

**Decision logic:**
1. Filter payroll-ledger records to `record_type == "Leave assignment"` AND `employee_id == <target>`.
2. Exclude records with `status == "Draft"` or `status == "Superseded"`.
3. The remaining record with the **most recent `updated_at`** is authoritative.
4. `effective_leave_policy` = `policy_name` from that record.
5. `annual_days` / `balance_days` = `approved_leave_days` from that record (integer).
6. `assignment_id` = `ledger_id` from that record.
7. If the employee profile summary shows a different `leave_balance_days` and an
   approved assignment exists, the profile is **stale** — ignore it.
8. `precedence_source` = `"approved_assignment_over_profile"` (or
   `"approved_assignment_current_period"` for the leave_precedence_source field).
9. `profile_policy_ignored` = `true` when the assignment overrides the profile.

**Status priority:** `Approved` > `Submitted` > `Superseded` (excluded) > `Draft` (excluded)

### 2. Payroll Assignment Source (PAY-SRC-001 §3.4)

**Rule:** Use the current **submitted** salary assignment. Draft planning assignments
do **not** affect payroll readiness or accrual checks.

**Decision logic:**
1. Filter payroll-ledger records to `record_type == "Salary assignment"` AND `employee_id == <target>`.
2. Exclude records with `status == "Draft"`.
3. Select the **submitted** record (status `"Submitted"`). If multiple, use the most
   recent `updated_at`.
4. `salary_assignment_id` / `payroll_assignment_id` = `ledger_id` of the submitted record.
5. `base_salary` = `base_salary` from that record.
6. `effective_date` = the `period` field from that record (format `"YYYY-MM"`).
7. `excluded_assignment_id` / `excluded_payroll_ids` = ledger_ids with `status == "Draft"`.
8. `payroll_source_status` / `payroll_status` = `"submitted"`.
9. `draft_exclusion_rule` = `"exclude_draft_assignment"`.

### 3. Recruiting Payroll Handoff Gate (PAY-SRC-001 §4.2)

**Rule:** Payroll handoff is created **only** after a selected candidate has an
**accepted** offer. The handoff must be **submitted**; draft prechecks do **not**
satisfy the assignment gate.

**Decision logic:**
1. Identify the selected candidate (`committee_decision == "Selected"`).
2. Check their offer status in the `offer_register`. Only `"accepted"` qualifies.
3. `onboarding_handoff` = `"create_submitted_assignment_after_acceptance"` when
   selected + accepted; otherwise `"no_payroll_handoff"`.
4. `payroll_handoff_gate` = `"accepted_offer_only"` (only the accepted candidate).
5. `payroll_assignment_status_required` = `"submitted_after_acceptance"`.
6. `draft_payroll_allowed` = `false`.
7. `handoff_control_result` = `"submitted_handoff_required_after_acceptance"`.

### 4. Lifecycle Folder Readiness (POL-DOCS-2026 §5.1)

**Rule:** A folder is **not ready** unless **all** required files AND **all** required
tags shown in the folder checklist are present. Both conditions must be met
independently.

**Decision logic:**
1. Look up the document folder by `document_id` matching the case or employee.
2. Compare `files` (actual) against `required_files`. Missing = `required_files - files`.
3. Compare `tags` (actual) against `required_tags`. Missing = `required_tags - tags`.
4. `folder_ready` = `true` **only if** both sets of missing items are empty.
5. The `ready` boolean on the document object reflects this check.
6. `missing_files` = list of required filenames that are absent.
7. `required_tag_present` = `true` when all `required_tags` are in `tags`; `false` otherwise.
8. `folder_required_tag_action` = `"add_required_tag"` if tags missing, else `"no_tag_action"`.

### 5. Formal Notice Quality

**Rule:** Formal notices referenced in `/api/messages` and `/api/notifications` carry
a `defects` array and a `quality` field. A notice with any defect is `"defective"`.

**Common defect values:**
- `"missing_ack_deadline"` — acknowledgement deadline absent
- `"missing_appeal_instructions"` — appeal instructions absent
- `"missing_waitlist_status"` — waitlist status omitted
- `"missing_correct_policy"` — references incorrect/legacy policy

**Decision logic:**
1. Check messages for the target `case_id`.
2. If `quality == "defective"` or `defects` is non-empty, the notice is defective.
3. `notice_quality` = `"defective"`; otherwise `"valid"`.
4. `notice_defects` = the list of defect codes from the message.
5. `notice_evidence_source` = `"message_notice_inspection"` when defects are on the
   message record (use the messages endpoint).
6. `notice_remediation_action` = `"reissue_defective_notices"` when defective.

### 6. Approval Closeout Gate

**Rule:** Closeout may only proceed when approval is final, the folder is ready,
AND the notice is valid. Missing any of these = block or hold.

**Decision logic:**
1. Check the case's `approvals` array. A final-step approval (`step` containing
   `"Final"`) with `decision == "Approved"` is required.
2. Verify folder readiness (§4 above).
3. Verify notice quality (§5 above).
4. `approval_closeout_gate`:
   - `"approval_sufficient_when_records_clean"` — approval exists, folder ready, notice valid
   - `"approval_not_sufficient_when_folder_or_notice_defective"` — folder or notice defective
5. `final_control_result` / `control_result`:
   - `"approve_closeout"` — all gates pass
   - `"hold_for_folder_and_notice_defects"` — one or more failures
   - `"ready_with_monitoring"` — gates pass but ongoing monitoring flagged by audit

---

## Audit Event Scoping

### Audit Event Types and Events

| `event` value | Meaning |
|---|---|
| `"leave.profile_mismatch"` | Profile summary disagrees with approved leave assignment |
| `"payroll.ready"` | Payroll assignment and accrual match; ready with monitoring |
| `"payroll.draft_excluded"` | Draft payroll record correctly excluded |
| `"notice.defect"` | Formal notice has defects |
| `"folder.tag_missing"` | Required tag is absent from folder |
| `"case.close_blocked"` | Closeout blocked due to folder/notice defects |
| `"cross_module.escalation_package"` | Combined lifecycle risk package; references related events |

### Audit Scope Values

| `audit_scope` value | When to use |
|---|---|
| `"leave_source_precedence_only"` | When the task is about determining authoritative leave policy/source |
| `"document_notice_findings_only"` | When reviewing folder readiness and/or notice quality |
| `"payroll_assignment_readiness"` | When checking payroll/accrual readiness |

### Scope Isolation Rule

**When a task asks you to determine leave source precedence:**
- Include audit events where `event` is `"leave.profile_mismatch"` (supporting).
- **Exclude** audit events where `event` is `"folder.tag_missing"`, `"case.close_blocked"`,
  `"notice.defect"`, `"payroll.ready"`, or `"payroll.draft_excluded"` — those belong
  to document/notice or payroll scopes, not leave scope.
- The `audit_scope` = `"leave_source_precedence_only"`.

**When a task asks you to review folder readiness and/or notice quality:**
- Include audit events where `event` is `"notice.defect"`, `"folder.tag_missing"`,
  or `"case.close_blocked"` (supporting).
- **Exclude** audit events where `event` is `"leave.profile_mismatch"` or
  `"payroll.ready"` — those are leave-scope or payroll-scope events.
- The `audit_scope` = `"document_notice_findings_only"`.

**When a task asks you to check payroll assignment readiness:**
- Include audit events where `event` is `"payroll.ready"` or `"payroll.draft_excluded"`.
- The `audit_scope` = `"payroll_assignment_readiness"`.

### Cross-Module Escalation (XMODULE)

When a `cross_module.escalation_package` event exists (e.g., AUD-XMODULE-77), its
`detail` field lists `Related events`. Each related event should be reviewed at its
own scope level. The package itself is a container and does not change the scope of
its children.

---

## Recruitment Reconciliation Workflow

### Candidate Classification

Candidates have a `committee_decision` field:
- `"Selected"` — chosen for the role
- `"Waitlisted"` — backup candidates
- `"Rejected"` — not selected

### Output Arrays

- `selected_candidate`: single candidate_id (the "Selected" candidate)
- `waitlisted_candidates`: list of candidate_ids with decision `"Waitlisted"`
- `rejected_candidates`: list of candidate_ids with decision `"Rejected"`

### Offer Handling

- The selected candidate's offer is in `offer_register` matched by `candidate_id`.
- `offer_id` = the matched offer's `offer_id`.
- `offer_base_salary` = the offer's `base_salary`.
- `selected_offer_status` = offer `status` (`"accepted"`, `"draft"`, `"withdrawn"`, `"none"`).
- `candidate_status_source` = `"interview_feedback_and_offer"` when using the full
  recruitment record.
- `candidate_outcome_control` = `"committee_decision_with_offer_confirmation"`.

### Notice Follow-Up

Notice packets are in the `notice_packets` array. Each has:
- `candidate_id`, `notice_type` (`"waitlist"` or `"rejection"`), `status`, `required_action`

- **Waitlisted candidates:**
  - If `notice_type == "waitlist"` and `status != "sent"`:
    - `waitlisted_followup_action` = `"send_waitlist_notice"` (or `"reissue_waitlist_notice_not_rejection"` if the notice exists but is defective)
  - Add `candidate_id` to `notice_followup_required` if action is needed.
- **Rejected candidates:**
  - If `notice_type == "rejection"` and `status != "sent"`:
    - `rejected_followup_action` = `"send_rejection_notice"`
  - Add `candidate_id` to `notice_followup_required` if action is needed.
- `offer_exclusion_reason_for_waitlisted` = `"no_accepted_status_or_offer"` since
  waitlisted candidates never have accepted offers.

### Notice Quality (Recruitment Context)

- `notice_quality_source` = `"notice_packet_inspection"` when using notice_packets data.
- Check for `defects` on the notice packets; the common defect for recruitment is
  `"missing_waitlist_status"`.

### Cost Calculation

- `recruitment_cost_total` = **sum of all** `amount` values in the `cost_ledger` array.
- Sum ALL line items — do not filter. Even items that appear administrative (platform
  fees, coordination, travel) count toward the total.
- `cost_source` = `"recruitment_cost_ledger"`.

### Payroll Handoff (Recruitment)

- Only triggered for the **selected candidate with an accepted offer**.
- Check `payroll_precheck_records`: if any exist with `status == "Draft"`, they do NOT
  satisfy the gate.
- `no_payroll_handoff` is correct when no handoff is needed (no accepted offer).
- `create_submitted_assignment_after_acceptance` is correct when the selected candidate
  has accepted.

---

## Closeout and Remediation

### Closeout Actions

| Action | When |
|---|---|
| `"approve_onboarding_close"` | All gates pass: approval final, folder ready, notice valid |
| `"block_close_and_reissue_notice"` | Notice is defective |
| `"open_records_remediation"` | Folder missing required files or tags |

### Remediation Ownership

| Issue | Owner |
|---|---|
| Missing required files or tags | `"Records"` |
| Defective formal notice or missing policy compliance | `"People Ops Compliance"` |
| Payroll assignment discrepancies | `"Payroll QA"` |

### Closeout Blockers

| Blocker | Condition |
|---|---|
| `"missing_required_files"` | Folder missing one or more required files |
| `"missing_required_tags"` | Folder missing one or more required tags |
| `"defective_formal_notice"` | Notice has one or more defects |

### Escalation

When closeout is blocked at multiple levels, `escalation_action` = `"open_records_remediation"`
or `"block_close_and_reissue_notice"` depending on whether the root cause is
folder/tag/documentation or notice quality.

---

## Field Reference — Normalized Enum Values

### Leave/Payroll Source Precedence

| Field | Enum Values |
|---|---|
| `leave_source` / `leave_precedence_source` | `"leave_assignment_history"`, `"approved_assignment_current_period"`, `"employee_profile_summary"`, `"profile_summary_current_period"`, `"case_summary_only"` |
| `precedence_source` | `"approved_assignment_over_profile"`, `"employee_profile_summary"`, `"case_summary_only"` |
| `payroll_status` / `payroll_source_status` | `"submitted"`, `"draft"`, `"superseded"` |
| `draft_exclusion_rule` | `"exclude_draft_assignment"`, `"draft_allowed"`, `"exclude_superseded_only"` |

### Closeout and Control

| Field | Enum Values |
|---|---|
| `closeout_action` | `"approve_onboarding_close"`, `"block_close_and_reissue_notice"`, `"open_records_remediation"` |
| `approval_closeout_gate` | `"approval_sufficient_when_records_clean"`, `"approval_not_sufficient_when_folder_or_notice_defective"` |
| `final_control_result` / `control_result` | `"approve_closeout"`, `"hold_for_folder_and_notice_defects"`, `"ready_with_monitoring"` |
| `audit_result` | `"profile_summary_stale"`, `"ready_with_monitoring"`, `"block_close"` |
| `next_action` | `"update_employee_summary"`, `"open_records_remediation"`, `"no_action"`, `"block_close_and_reissue_notice"`, `"approve_onboarding_close"` |

### Folder and Notice

| Field | Enum Values |
|---|---|
| `notice_quality` | `"valid"`, `"defective"` |
| `notice_defects` | `"missing_ack_deadline"`, `"missing_appeal_instructions"`, `"missing_waitlist_status"`, `"missing_correct_policy"` |
| `notice_evidence_source` | `"notice_packet_inspection"`, `"message_notice_inspection"`, `"case_summary_only"` |
| `notice_remediation_action` | `"reissue_defective_notices"`, `"no_notice_action"`, `"send_new_offer_notice"` |
| `folder_required_tag_action` | `"no_tag_action"`, `"add_required_tag"` |
| `closeout_blockers` | `"missing_required_files"`, `"missing_required_tags"`, `"defective_formal_notice"` |
| `evidence_source_order` | `"approval_history_folder_notice_audit"`, `"folder_notice_audit"`, `"audit_only"` |

### Recruitment

| Field | Enum Values |
|---|---|
| `candidate_status_source` | `"interview_feedback_and_offer"`, `"case_summary_only"`, `"message_only"` |
| `candidate_outcome_control` | `"committee_decision_with_offer_confirmation"`, `"message_status_only"`, `"case_summary_only"` |
| `selected_offer_status` | `"accepted"`, `"draft"`, `"withdrawn"`, `"none"` |
| `cost_source` | `"recruitment_cost_ledger"`, `"case_summary_only"` |
| `waitlisted_followup_action` | `"send_waitlist_notice"`, `"reissue_waitlist_notice_not_rejection"`, `"no_action"` |
| `rejected_followup_action` | `"send_rejection_notice"`, `"no_action"`, `"reissue_rejection_notice"` |
| `onboarding_handoff` | `"create_payroll_precheck"`, `"create_submitted_assignment_after_acceptance"`, `"no_payroll_handoff"` |
| `payroll_handoff_gate` | `"accepted_offer_only"`, `"accepted_offer_and_submitted_assignment"`, `"all_interviewed_candidates"` |
| `payroll_assignment_status_required` | `"submitted_after_acceptance"`, `"submitted"`, `"draft_allowed"` |
| `offer_exclusion_reason_for_waitlisted` | `"no_accepted_status_or_offer"`, `"waitlisted_not_selected"`, `"already_rejected"` |
| `handoff_control_result` | `"submitted_handoff_required_after_acceptance"`, `"submitted_handoff_required"`, `"no_handoff_required"` |
| `notice_quality_source` | `"notice_packet_inspection"`, `"message_notice_inspection"`, `"case_summary_only"` |

### Audit

| Field | Enum Values |
|---|---|
| `audit_scope` | `"leave_source_precedence_only"`, `"document_notice_findings_only"`, `"payroll_assignment_readiness"` |

### Case Decisions

| Field | Enum Values |
|---|---|
| `final_decision` | `"approved_with_conditions"`, `"approved"`, `"rejected"`, `"held"` |

### Remediation

| Field | Enum Values |
|---|---|
| `records_remediation_owner` | `"Records"`, `"People Ops Compliance"`, `"Payroll QA"` |
| `escalation_action` | `"open_records_remediation"`, `"block_close_and_reissue_notice"`, `"no_action"` |

---

## Data Flow: Step-by-Step Workflow for Each Task Type

### Onboarding Closeout Verification

1. Get employee from `/api/employees` (by employee_id).
2. Get all payroll ledgers; filter to the employee's leave assignments (record_type = "Leave assignment", status != "Draft" and != "Superseded").
3. Get all payroll ledgers; filter to the employee's salary assignments (record_type = "Salary assignment", status = "Submitted").
4. Determine authoritative leave assignment (most recent approved/submitted).
5. Determine submitted salary assignment; identify draft payroll records to exclude.
6. Set closeout_action based on whether records are clean.

### Policy Case Folder & Notice Review

1. Get case from `/api/cases/<case_id>`.
2. Get comments from `/api/cases/<case_id>/comments`.
3. Get document from `/api/documents` matching the case's document folder.
4. Check folder readiness: compare files vs required_files, tags vs required_tags.
5. Get messages from `/api/messages`; find the message for this case_id.
6. Check notice quality: inspect defects array.
7. Check approvals for final decision and authority.
8. Get audit events; scope to document/notice events only.
9. Set final_decision, closeout blockers, and next_action.

### Leave Source Precedence

1. Get employee from `/api/employees` (by employee_id).
2. Get all payroll ledgers; filter to the employee's leave assignments.
3. Exclude Draft and Superseded; pick the most recent Approved or Submitted.
4. Get the relevant leave policy (LEAVE-SRC-001).
5. Compare the employee profile's leave_balance_days with the assignment's approved_leave_days.
6. Get audit events; scope to leave-source events only (exclude document/notice and payroll events).
7. If profile differs from assignment, profile is stale; effective leave comes from the assignment.

### Payroll Assignment & Accrual Readiness

1. Get employee from `/api/employees` (by employee_id).
2. Get all payroll ledgers; filter to the employee's salary assignments.
3. Identify the submitted record (selected) and any draft records (excluded).
4. Check for `accrual_batch_id` on the submitted record.
5. Get relevant audit events; scope to payroll events.
6. Accrual is ready when submitted salary assignment has an accrual_batch_id AND
   the audit event confirms `payroll.ready` with `ready_with_monitoring`.

### Recruitment Reconciliation

1. Get recruitment data from `/api/recruitment`; find the opening by `opening_id`.
2. Classify candidates by `committee_decision`.
3. Find the selected candidate's offer in `offer_register`.
4. Compute `recruitment_cost_total` = sum of all `cost_ledger[].amount`.
5. Check `notice_packets` for required follow-up actions.
6. Check messages for notice quality defects.
7. Determine payroll handoff: selected + accepted offer = handoff required.
8. Verify that no draft payroll precheck records exist that would be confused with
   submitted assignments.

---

## Common Pitfalls

1. **Confusing record types in payroll ledgers.** Only `"Leave assignment"` and
   `"Salary assignment"` are authoritative. `"HRMS leave ledger"`, `"Payroll worksheet"`,
   and `"People Ops adjustment"` are not policy-controlling records.

2. **Trusting the employee profile summary for leave.** The profile is a cached
   snapshot. Always cross-check with the leave assignment ledger. If an approved
   assignment exists with different values, the assignment wins.

3. **Counting Draft records.** Draft leave assignments and draft salary assignments
   are planning artifacts. Never use them for current-state decisions. Always exclude
   them via `excluded_leave_ids` / `excluded_payroll_ids` / `excluded_assignment_id`.

4. **Superseded records.** Like Drafts, superseded records are historical and must be
   excluded. Only current Approved or Submitted records carry weight.

5. **Forgetting required tags on folder readiness.** A folder with all files present
   but a missing required tag is NOT ready. Both conditions (files AND tags) must pass.

6. **Narrow audit scope for leave tasks.** When the task asks about leave source
   precedence, do not include document/notice audit events (like `folder.tag_missing`
   or `notice.defect`) in the supporting set. Those belong to a different scope.

7. **Recruitment cost: partial sums.** Sum ALL cost_ledger items. Do not pick and choose.

8. **Confusing notice_packets with messages.** Notices in the recruitment module come
   from `notice_packets`; formal decision notices come from `/api/messages`. Use the
   correct source for the context.

9. **Draft payroll prechecks masquerading as assignments.** In recruitment,
   `payroll_precheck_records` with status `"Draft"` are not real assignments. They
   do not satisfy the payroll handoff gate.

10. **Using the wrong approval for authority.** Only the final-step approval
    (`step` containing "Final") determines the case decision. Intake or intermediate
    approvals are preparatory.

11. **Mixing leave and salary assignment ledger entries.** When the task asks for
    both leave and payroll for the same employee, they come from different
    record_type filters on the same ledger endpoint — ensure you filter correctly
    for each.

12. **Evidence source ordering.** When the answer template requires
    `evidence_source_order`, the correct chain for case-review tasks is
    `"approval_history_folder_notice_audit"` — approvals first, then folder, then
    notice, then audit.

---

## Sorting Rules

- **Leave assignments:** Sort by `updated_at` descending; the most recent
  non-draft/non-superseded record is authoritative.
- **Payroll assignments:** Sort by `updated_at` descending; select the most recent
  `"Submitted"` record.
- **Candidates in output arrays:** List candidate IDs in the order they appear in
  the recruitment record's `candidates` array (preserve original order).
- **Audit events:** No specific sort required; include by relevance to the scope.
  Supporting events should be listed before excluded events conceptually, but both
  arrays simply contain IDs.

---

## Date and Period Conventions

- `period` in payroll ledgers uses `"YYYY-MM"` format for salary assignments and
  `"YYYY"` format for annual leave assignments.
- `effective_date` in policies uses `"YYYY-MM-DD"`.
- `effective_date` in payroll output comes from the salary assignment's `period`
  (format `"YYYY-MM"`).
- `updated_at` and `timestamp` use ISO-8601 format.
- For the 2026 effective state, filter to records whose `period` covers 2026
  (annual `"2026"` or monthly `"2026-*"`).

---

## Policy Reference Quick Card

| Policy ID | Title | Owner | Key Rule |
|---|---|---|---|
| `LEAVE-SRC-001` | Leave Source Precedence | People Ops | Latest approved/submitted assignment controls; drafts excluded |
| `PAY-SRC-001` | Payroll Assignment Source | Payroll | Submitted salary only; drafts ignored; handoff after accepted offer |
| `HR-POL-014` | Remote Work Policy | Legal Desk | Exception requires executive approval, tax equalization, appeal instructions, ack deadline |
| `POL-DOCS-2026` | Lifecycle Folder Checklist | Records | Folder ready only when ALL required files AND tags present |
