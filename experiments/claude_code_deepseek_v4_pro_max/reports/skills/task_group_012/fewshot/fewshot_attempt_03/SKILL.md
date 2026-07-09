# People Lifecycle HRMS — Employee Lifecycle & Policy Operations

## Overview

This skill covers the ERP HR employee-lifecycle and policy-operations task group:
onboarding closeout, leave source precedence, payroll assignment readiness,
recruitment reconciliation, and policy case folder/notice review. All work is
done against a shared remote People Lifecycle HRMS API at the base URL provided
in `environment_access.md`.

## API Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/manifest` | Business modules, entry points, file counts, seed, generation date |
| `GET /api/summary` | Case counts by status, employee/department overview |
| `GET /api/employees` | All employee records with profile, department, leave balance, status |
| `GET /api/cases` | All cases with status, owner, policy refs, priority, summary |
| `GET /api/cases/<case_id>` | Single case detail |
| `GET /api/cases/<case_id>/comments` | Case comments (may error if none) |
| `GET /api/policies` | Policy documents — title, summary, sections (heading+body), owner, status |
| `GET /api/payroll-ledgers` | Combined leave-assignment and salary-assignment records with status |
| `GET /api/recruitment` | Per-opening: candidates, offer register, cost ledger, notice packets, payroll precheck records |
| `GET /api/documents` | Case folders — files present, required files, tags present, required tags, ready flag |
| `GET /api/messages` | Formal notices / messages with quality, defects list, status, channel |
| `GET /api/notifications` | Same shape as /api/messages in this dataset |
| `GET /api/audit` | All audit events with actor, case_id, event type, detail, source |
| `GET /api/audit/<event_id>` | Single audit event detail |
| `GET /api/attachments/<attachment_id>` | Individual attachment content |

## General API Workflow

1. **Orient**: Fetch `/api/manifest` and `/api/summary` to confirm available modules and record counts.
2. **Identify the entity**: Fetch the employee, case, or recruitment opening by ID from the
   appropriate collection endpoint, or locate it by name/ID in the list response.
3. **Cross-reference**: Pull related records — policies, payroll-ledgers, documents, messages,
   audit events — filtering by employee_id or case_id.
4. **Apply precedence rules**: Submitted/approved records override drafts and profile summaries.
   See Source Precedence below.
5. **Produce normalized output**: Use only the enum values defined in the task's answer template.
   Never emit free-text where an enum slot exists.

## Core Business Rules

### Source Precedence — Leave

**Rule**: An approved (or submitted) leave assignment overrides the employee profile summary,
even when they conflict.

Governing policy: `LEAVE-SRC-001` §2.1 — "The latest approved or submitted leave assignment
for the period controls. Draft, voided, and obsolete records are excluded even when profile
summaries conflict."

- The employee profile's `leave_balance_days` may be stale — always verify against the
  payroll-ledger leave-assignment records for the same employee and period.
- When multiple leave assignments exist for an employee, pick the one with status
  `Approved` or `Submitted` (not `Draft`, not `Superseded`).
- If the profile summary conflicts with the authoritative assignment, flag
  `profile_summary_stale` and set `next_action: "update_employee_summary"`.

### Source Precedence — Payroll

**Rule**: Use the current **submitted** salary assignment. Draft planning assignments do not
affect payroll readiness or accrual checks.

Governing policy: `PAY-SRC-001` §3.4 — "Use the current submitted salary assignment. Draft
planning assignments do not affect payroll readiness or accrual checks."

- Filter payroll-ledger records to `record_type: "Salary assignment"` for the target employee.
- Keep only `status: "Submitted"` records.
- Exclude all `status: "Draft"` salary assignments. List their ledger IDs in
  `excluded_payroll_ids` or `excluded_assignment_id`.
- The effective `base_salary` comes from the submitted record.

### Source Precedence — Recruitment

**Rule**: Recruiting payroll handoff is created only after a selected candidate has an
**accepted** offer. The handoff must be submitted; draft prechecks do not satisfy the gate.

Governing policy: `PAY-SRC-001` §4.2 — "Recruiting payroll handoff is created only after a
selected candidate has an accepted offer. The handoff must be submitted; draft precheck
assignments do not satisfy the gate."

- Payroll handoff gate: `accepted_offer_only` — only the candidate with an accepted offer
  qualifies for payroll precheck/handoff.
- `draft_payroll_allowed: false` — draft payroll precheck records are never valid for handoff.

### Folder Readiness

**Rule**: A case folder is ready **only** when ALL required files are present AND ALL required
tags are present.

Governing policy: `POL-DOCS-2026` §5.1 — "A folder is not ready unless all required files and
required tags shown in the folder checklist are present."

- Compare `document.files` against `document.required_files` — any file in required_files but
  not in files is **missing**.
- Compare `document.tags` against `document.required_tags` — any tag in required_tags but not
  in tags is **missing**.
- `folder_ready: true` only when both sets are complete; `false` otherwise.
- Missing files and missing tags are separate blockers.

### Formal Notice Quality

**Rule**: Formal decision notices must include appeal instructions, an acknowledgement deadline,
and (for waitlist notices) the waitlist status. A notice referencing a wrong or stale policy is
also defective.

Inspect messages (or notice_packets for recruitment) for:
- `missing_appeal_instructions` — appeal process not stated
- `missing_ack_deadline` — acknowledgement deadline not stated
- `missing_waitlist_status` — waitlist notice omits the candidate's waitlist position
- `missing_correct_policy` — notice references a stale/incorrect policy instead of the
  authoritative assignment

Source for notice inspection: `/api/messages` (or `notice_packets` in recruitment) — never
rely on case summary alone for notice quality.

### Record Status Hierarchy

| Record Type | Authoritative Statuses | Excluded Statuses |
|---|---|---|
| Leave assignment | `Approved`, `Submitted` | `Draft`, `Superseded`, `Voided` |
| Salary assignment | `Submitted` | `Draft` |
| Offer | `accepted` | `draft`, `withdrawn`, `none` |
| Payroll precheck | `Submitted` | `Draft` |

## Task-Type Specific SOPs

### 1. Onboarding Closeout Verification

**Goal**: Verify leave setup and payroll setup before approving onboarding close.

**Data sources** (in order):
1. `/api/employees` — confirm employee identity, department, hire date, status
2. `/api/payroll-ledgers` — filter by employee_id, separate leave assignments from salary assignments
3. `/api/policies` — confirm governing policies (LEAVE-SRC-001, PAY-SRC-001)

**Steps**:
- For **leave**: find the employee's leave-assignment records (`record_type: "Leave assignment"`).
  Select the record with status `Approved` (or `Submitted` if no Approved exists). Its
  `policy_name` is the `effective_leave_policy`, its `approved_leave_days` is the `annual_days`.
- Exclude all other leave-assignment records (Draft, Superseded, earlier versions).
- For **payroll**: find salary-assignment records (`record_type: "Salary assignment"`).
  Select the one with status `Submitted`. Its `ledger_id` is the `payroll_assignment_id`,
  its `base_salary` is authoritative.
- Exclude Draft salary assignments.
- **Closeout gate**: if only clean (submitted/approved) records remain after excluding drafts,
  `approval_closeout_gate: "approval_sufficient_when_records_clean"` and
  `final_control_result: "approve_closeout"`.

### 2. Policy Case Folder & Notice Review

**Goal**: Determine whether a case folder is ready and the formal notice is valid.

**Data sources** (in order):
1. `/api/cases/<case_id>` — case metadata, policy refs, status
2. `/api/documents` — find the folder for this case; check files and tags
3. `/api/messages` — find formal notices for this case; inspect quality and defects
4. `/api/audit` — find audit events linked to this case_id

**Steps**:
- **Folder check**: compute `missing_files` = `required_files \ files`; compute missing tags
  similarly. Set `folder_ready` to `true` only if both lists are empty.
- **Notice check**: inspect each message for the case. If `quality: "defective"`, collect the
  `defects` array. Common defects: missing appeal instructions, missing ack deadline, missing
  waitlist status, wrong policy.
- **Audit correlation**: find audit events matching the case_id and relevant to
  document/notice findings. The most recent relevant audit event is typically the primary.
- **Decision tree**:
  - If folder incomplete OR notice defective → `final_decision: "approved_with_conditions"`,
    `approval_closeout_gate: "approval_not_sufficient_when_folder_or_notice_defective"`,
    `final_control_result: "hold_for_folder_and_notice_defects"`,
    `next_action: "block_close_and_reissue_notice"`.
- **Escalation**: when blockers exist, set `escalation_action: "open_records_remediation"`,
  `records_remediation_owner: "Records"`, `notice_remediation_action: "reissue_defective_notices"`.

### 3. Recruitment Reconciliation

**Goal**: Determine candidate outcomes, required follow-up notices, and payroll handoff from
a recruitment opening.

**Data sources** (in order):
1. `/api/recruitment` — find the opening by `opening_id`; get candidates, offers, costs, notices
2. `/api/cases` — confirm the case for this opening
3. `/api/policies` — PAY-SRC-001 §4.2 for payroll handoff gate
4. `/api/messages` — cross-check notice quality if notice_packets are present
5. `/api/payroll-ledgers` — verify any payroll precheck records

**Steps**:
- **Candidate classification**: read `committee_decision` for each candidate:
  - `Selected` → `selected_candidate`
  - `Waitlisted` → `waitlisted_candidates` array
  - `Rejected` → `rejected_candidates` array
- **Offer**: find the offer for the selected candidate in `offer_register`. Extract
  `offer_id`, `base_salary`, and confirm `status: "accepted"`.
- **Cost**: sum all `amount` values in the `cost_ledger` array → `recruitment_cost_total`.
- **Notice follow-up**: consult `notice_packets`. Any candidate whose notice `status` is
  `not_sent` or `draft_reissue_required` needs follow-up. Waitlisted candidates get
  `send_waitlist_notice`; rejected candidates get `send_rejection_notice`.
- **Payroll handoff**: only the selected candidate with `offer.status: "accepted"` triggers
  `onboarding_handoff: "create_payroll_precheck"`. `draft_payroll_allowed: false`.
- **Waitlisted exclusion**: waitlisted candidates lack an accepted offer → set
  `offer_exclusion_reason_for_waitlisted: "no_accepted_status_or_offer"`.

### 4. Leave Source Precedence Validation

**Goal**: Determine which leave policy is authoritative when profile and assignment conflict.

**Data sources** (in order):
1. `/api/employees` — read profile `leave_balance_days` and policy reference
2. `/api/payroll-ledgers` — filter leave assignments for employee
3. `/api/policies` — LEA-SRC-001 for precedence rule
4. `/api/audit` — find leave-related audit events for this employee

**Steps**:
- Compare the employee profile summary against approved leave assignments in the ledger.
- If an approved assignment exists with different policy/days than the profile:
  - The approved assignment controls.
  - Set `precedence_source: "approved_assignment_over_profile"`.
  - Set `profile_policy_ignored: true`.
  - Set `audit_result: "profile_summary_stale"`.
  - Set `next_action: "update_employee_summary"`.
- **Audit scope**: use `leave_source_precedence_only`. Include audit events about leave/profile
  mismatch as `supporting_audit_event_ids`. **Exclude** document/notice audit events (e.g.,
  `AUD-DOC*`) from the leave-scope decision — those belong to a different scope.
- The `leave_precedence_source` is `approved_assignment_current_period` when the assignment
  controls.

### 5. Payroll Assignment & Accrual Readiness

**Goal**: Verify the submitted payroll assignment is clean and accrual can proceed.

**Data sources** (in order):
1. `/api/employees` — confirm employee status
2. `/api/payroll-ledgers` — salary assignments for employee, accrual batch references
3. `/api/audit` — payroll readiness audit events
4. `/api/policies` — PAY-SRC-001

**Steps**:
- Filter salary assignments for the employee. Select the `Submitted` one as authoritative.
- Identify and exclude all `Draft` salary assignments.
- Check for an `accrual_batch_id` field on the submitted record — this indicates accrual linkage.
- If the submitted record has an accrual batch and no blockers → `accrual_ready: true`.
- Set `draft_exclusion_rule: "exclude_draft_assignment"`.
- Set `audit_scope: "payroll_assignment_readiness"`.
- If ready but proceed with monitoring → `control_result: "ready_with_monitoring"`.

## Audit Event Handling

### Scope-Based Filtering

Audit events serve different purposes. Filter by the task's audit scope:

| Scope | Include | Exclude |
|---|---|---|
| `leave_source_precedence_only` | Events with `event: "leave.profile_mismatch"` or about leave assignment vs profile | Document/notice events (`AUD-DOC*`, events about folder tags, notice defects) |
| `document_notice_findings_only` | Events about folder readiness, notice defects, case close blocks | Leave/payroll source events |
| `payroll_assignment_readiness` | Events about payroll readiness, draft exclusion, salary assignment | Document/notice events |

### Supporting vs Excluded Audit Events

- `supporting_audit_event_ids` — audit events that confirm the finding and are within scope
- `excluded_audit_event_ids` — audit events for the same employee/case that belong to a
  different scope and must not influence the current decision

## Enum Reference

### Closeout Actions
- `approve_onboarding_close` — all records clean, proceed
- `block_close_and_reissue_notice` — folder or notice defective, stop and fix
- `open_records_remediation` — cross-module issues requiring Records team

### Final Control Results
- `approve_closeout` — clean, ready to close
- `hold_for_folder_and_notice_defects` — folder incomplete or notice invalid
- `ready_with_monitoring` — submitted records OK but continue monitoring

### Leave Precedence Sources
- `approved_assignment_current_period` — approved assignment controls
- `profile_summary_current_period` — profile is authoritative (rare; only when no approved assignment exists)
- `case_summary_only` — fallback when neither is available

### Payroll Source Status
- `submitted` — authoritative
- `draft` — must be excluded
- `superseded` — must be excluded (for salary assignments)

### Notice Quality
- `valid` — all required elements present
- `defective` — one or more defects found

### Notice Defects (enum)
- `missing_ack_deadline`
- `missing_appeal_instructions`
- `missing_waitlist_status`
- `missing_correct_policy`

### Approval Closeout Gates
- `approval_sufficient_when_records_clean` — no blockers
- `approval_not_sufficient_when_folder_or_notice_defective` — blockers present

### Audit Scopes
- `leave_source_precedence_only`
- `document_notice_findings_only`
- `payroll_assignment_readiness`

### Candidate Status Sources
- `interview_feedback_and_offer` — authoritative; from committee decision + offer register
- `case_summary_only` — fallback
- `message_only` — fallback

### Offer Statuses
- `accepted` — triggers payroll handoff
- `draft` — not valid
- `withdrawn` — not valid
- `none` — no offer exists

### Payroll Handoff Gates
- `accepted_offer_only` — handoff only for accepted candidate
- `accepted_offer_and_submitted_assignment` — stricter
- `all_interviewed_candidates` — broadest (non-standard)

### Notice Follow-up Actions
- `send_waitlist_notice` — for waitlisted candidates
- `send_rejection_notice` — for rejected candidates
- `reissue_waitlist_notice_not_rejection` — when waitlist notice is defective and must be corrected

### Records Remediation Owner
- `Records`
- `People Ops Compliance`
- `Payroll QA`

### Evidence Source Order
- `approval_history_folder_notice_audit` — full chain, most thorough
- `folder_notice_audit` — skip approval history
- `audit_only` — audit events only

## Common Pitfalls

1. **Draft contamination**: Always filter out Draft-status records before computing
   authoritative values. Draft leave assignments, draft salary assignments, and draft
   payroll prechecks must never be treated as authoritative.
2. **Profile staleness**: The employee profile's `leave_balance_days` may not match the
   approved assignment. Always cross-check against the payroll-ledger.
3. **Scope leakage**: When computing leave-source decisions, exclude document/notice audit
   events. When computing document/notice decisions, exclude leave/payroll source events.
   Audit events must be filtered by scope relevance.
4. **Folder readiness requires both files AND tags**: A folder with all files but a missing
   tag is NOT ready. Check both dimensions.
5. **Notice inspection source**: Always inspect `/api/messages` for formal notice quality,
   not just the case summary. The case summary may say "approved" while the notice is
   defective.
6. **Offer register scope**: Only candidates with entries in the `offer_register` have offers.
   Waitlisted and rejected candidates typically have no offer record.
7. **Cost sum**: `recruitment_cost_total` is the sum of ALL `amount` values in the cost
   ledger — no filtering, no exclusions.
8. **Payroll precheck vs assignment**: A draft payroll precheck record does NOT satisfy
   the payroll assignment gate. Only submitted assignments count.
9. **Enum-only output**: Every field listed in the answer template's enum constraints must
   use one of the allowed values exactly. Free-text variants (e.g., "Approved assignment"
   instead of `approved_assignment_current_period`) will fail validation.
10. **Case ID format**: Case IDs use the format from the API response exactly — `CASE-RW-221`,
    `REQ-DA-77`, etc. Do not normalize or transform them.
11. **Accrual batch**: When a submitted salary assignment carries an `accrual_batch_id` field,
    link it to accrual readiness. Its presence on a submitted record is a positive signal.
12. **Superseded leave records**: A `Superseded` leave assignment is NOT authoritative —
    it's been replaced. Use the current Approved/Submitted assignment instead.
