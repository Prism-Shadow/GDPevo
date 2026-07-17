# ERP HR Employee-Lifecycle & Policy-Operations Skill

## Overview

This skill covers PeopleOps verification tasks across the employee lifecycle:
onboarding closeout, leave source precedence, payroll assignment readiness, policy
case folder/notice review, and recruitment reconciliation. The system provides
REST APIs for employees, payroll ledgers, cases, policies, documents, messages,
audit events, and recruitment data.

## API Usage Workflow

The `environment_access.md` entrypoint provides the base URL. All data is
read-only via GET endpoints. The canonical workflow for any lifecycle
verification follows the evidence hierarchy below.

### Key Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/employees` | Employee profiles with summary leave balance, status, department |
| `GET /api/payroll-ledgers` | Leave assignments, salary assignments, accrual batches, HRMS ledgers |
| `GET /api/cases` | Case list with status, owner, policy refs, summary |
| `GET /api/cases/<id>` | Case detail including approvals, attachments, audit events, comments |
| `GET /api/policies` | Policy documents with sections, effective dates, ownership |
| `GET /api/documents` | Document folders with file lists, required files, required tags |
| `GET /api/messages` | Formal notices with quality, defects, channel, status |
| `GET /api/audit` | Audit events with actor, event type, detail, case/employee linkage |
| `GET /api/audit/<id>` | Single audit event detail |
| `GET /api/recruitment` | Recruitment packets with candidates, offers, cost ledger, notice packets |
| `GET /api/notifications` | Same dataset as messages (formal notice inspection) |
| `GET /api/manifest` | System metadata and entry points |
| `GET /api/summary` | Aggregate counts, departments |

### Evidence Hierarchy

Always collect evidence in this order when multiple sources are available:

1. **Approval history** — from case detail `approvals[]`
2. **Folder / documents** — from `GET /api/documents`
3. **Formal notice / messages** — from `GET /api/messages` or `GET /api/notifications`
4. **Audit events** — from `GET /api/audit`

For recruitment tasks, use: candidate committee decisions → offer register →
cost ledger → notice packets → audit events.

## Core Business Rules

### 1. Source Precedence: Assignment/Ledger Over Profile Summary

The authoritative record for leave, payroll, and assignment data is the
**ledger** (assignment history), not the employee profile summary.

- **LEAVE-SRC-001 (Section 2.1)**: The latest approved or submitted leave
  assignment for the period controls. The employee profile summary may be stale;
  always verify against the assignment ledger.
- **PAY-SRC-001 (Section 3.4)**: Use the current submitted salary assignment.
  Draft planning assignments do not affect payroll readiness or accrual checks.

**Decision rule**: When the assignment ledger and employee profile summary
conflict, the ledger wins. Mark the profile summary as stale and flag for update.

### 2. Record Status Filtering

Record status determines whether a record is authoritative:

| Status | Authoritative? | Action |
|---|---|---|
| `Approved` | Yes | Use as the effective record |
| `Submitted` | Yes | Use as the effective record |
| `Superseded` | No | Exclude — treated as obsolete |
| `Draft` | No | Exclude — not yet in effect |
| `Voided` | No | Exclude |

**Rule**: When multiple records exist for the same employee and period, select
the latest Approved or Submitted record. Exclude all Draft and Superseded
records from the authoritative answer.

**For payroll assignments specifically**: PAY-SRC-001 requires `Submitted`
status. An `Approved` leave assignment and a `Submitted` payroll assignment are
both valid in their respective domains.

### 3. Draft Handling

Draft records are **never** authoritative:

- Draft leave assignments are excluded from effective leave policy determination
- Draft payroll/salary assignments are excluded from payroll readiness
- Draft payroll precheck records do not satisfy the assignment gate for
  recruiting handoff (PAY-SRC-001 Section 4.2)
- Draft messages/notices are flagged as defective if they lack required elements

When asked for excluded record IDs, always include every record with status
`Draft` (and `Superseded`/obsolete) for the relevant employee.

### 4. Folder Readiness (POL-DOCS-2026 Section 5.1)

A case folder is **ready** only when **all** of these are true:
- Every file in `required_files` is present in `files`
- Every tag in `required_tags` is present in `tags`

If any required file is missing → folder is **not ready**, include it in
`missing_files`.

If any required tag is missing → folder is **not ready**, and
`required_tag_present` is `false`.

### 5. Formal Notice Quality

Inspect the notice/message for the case. A notice is **defective** if its
`defects` array is non-empty or its `quality` field is `"defective"`.

Required notice elements per HR-POL-014 Section 7.1 (executive exceptions):
- Appeal instructions
- Acknowledgement deadline

Common notice defects:
- `missing_appeal_instructions` — no appeal process described
- `missing_ack_deadline` — no acknowledgement deadline
- `missing_waitlist_status` — waitlist notice omits status
- `missing_correct_policy` — references wrong/stale policy

### 6. Closeout Gate

The approval closeout gate determines whether onboarding/lifecycle close can
proceed:

- **`approval_sufficient_when_records_clean`**: All records are valid
  (submitted/approved), no draft contamination, folder complete, notice valid.
- **`approval_not_sufficient_when_folder_or_notice_defective`**: Either the
  folder is missing required files/tags OR the formal notice has defects.

Closeout is blocked when **either** the folder or the notice is defective.

### 7. Recruiting Payroll Handoff Gate (PAY-SRC-001 Section 4.2)

Payroll handoff after recruitment follows this gate:
1. Selected candidate must have an **accepted** offer
2. The handoff assignment must be **submitted** (not draft)
3. Draft precheck records do not satisfy the gate

**Handoff control result**: `submitted_handoff_required_after_acceptance` when
an offer is accepted but no submitted assignment exists yet.

**Draft payroll allowed**: `false` — draft prechecks never satisfy the
assignment gate.

**Offer exclusion for waitlisted candidates**: `no_accepted_status_or_offer` —
waitlisted candidates have no accepted offer.

### 8. Leave Precedence for 2026 Effective State

When determining the effective 2026 leave policy for an employee:

1. Query the leave ledger for the employee's 2026-period assignments
2. Filter to Approved or Submitted status only (exclude Draft, Superseded)
3. The latest Approved/Submitted record controls the effective policy and
   balance days
4. If the employee profile summary differs, the profile is stale and should be
   ignored
5. Supporting audit events are those scoped to leave precedence
6. Exclude document/notice audit events from the leave-scope decision

### 9. Recruitment Reconciliation

For recruitment packet reconciliation:

- **Candidate classification**: Use the `committee_decision` field from the
  recruitment candidate list (`Selected`, `Waitlisted`, `Rejected`)
- **Selected candidate**: The one with `committee_decision: "Selected"`
- **Offer details**: From `offer_register[]`, match by `candidate_id`
- **Cost total**: Sum **all** `amount` values in the `cost_ledger[]` array
- **Notice followup**: Any candidate whose notice packet has
  `status: "not_sent"` or `status: "draft_reissue_required"` needs followup
- **Notice packets** drive followup actions: `send_waitlist_notice`,
  `send_rejection_notice`, or `reissue_waitlist_notice_not_rejection`

### 10. Payroll Assignment & Accrual Readiness

For payroll/accrual verification:

- Identify the submitted salary assignment for the employee
- Exclude draft assignments
- Accrual readiness: `true` when the submitted assignment's `accrual_batch_id`
  matches the current accrual batch
- The audit event confirming readiness provides the batch verification
- Effective date comes from the submitted assignment's `period` field (format
  `YYYY-MM`, map to `YYYY-MM-DD` using the first of the month)

### 11. Audit Event Scoping

When the task asks for audit evidence:

- **Supporting audit events**: Include only events relevant to the specific
  decision scope (e.g., leave precedence, payroll readiness, document/notice)
- **Excluded audit events**: Exclude events that belong to a different scope
  (e.g., exclude document/notice audit events from a leave-source-precedence
  decision, and vice versa)
- Each audit event has a `case_id` and `event` type that determines its scope
- Cross-module escalation packages (event type `cross_module.escalation_package`)
  reference related events that must be reviewed individually

## Output Field Conventions

### Enum Value Selection

Always use the exact enum string from the answer template. Never use free-text
where an enum is provided. Key patterns:

- **Source fields**: Select the value that describes where data was actually
  found (assignment history, notice packet, recruitment ledger, etc.)
- **Gate fields**: Select based on the condition that applies
  (`approval_sufficient_when_records_clean` vs
  `approval_not_sufficient_when_folder_or_notice_defective`)
- **Control/result fields**: Match the overall outcome
  (`approve_closeout`, `hold_for_folder_and_notice_defects`,
  `ready_with_monitoring`)
- **Action fields**: Match the specific remediation needed
- **Scope fields**: Narrow to the specific decision domain

### List Fields

- Candidate lists (`waitlisted_candidates`, `rejected_candidates`): candidate
  IDs only
- `missing_files`: filenames only (no paths)
- `excluded_*_ids`: record IDs for excluded items
- `notice_defects`: enum values from the allowed defect list
- `closeout_blockers`: enum values from the allowed blocker list

### Numeric Fields

- `base_salary`: integer, no currency symbol or formatting
- `annual_days` / `balance_days`: integer (whole days from approved assignment)
- `recruitment_cost_total`: sum of all cost ledger `amount` values (number,
  not integer — may include cents if present in data)

### Boolean Fields

- `folder_ready`: `true` only when ALL required files AND ALL required tags
  are present
- `required_tag_present`: `true` when every required tag is in the folder's tags
- `profile_policy_ignored`: `true` when the assignment overrides the profile
- `accrual_ready`: `true` when submitted assignment matches accrual batch
- `draft_payroll_allowed`: `false` per policy

### Date Fields

- `effective_date`: Use the `period` from the payroll ledger record, formatted
  as `YYYY-MM-DD` (first day of the period month). Example: period `2026-04`
  → `"2026-04-01"`.

## Sorting Rules

- Candidate arrays: Order as they appear in the recruitment data
- Excluded IDs: Order as they appear in the ledger (chronologically by
  `updated_at`)
- Missing files: Order as they appear in the document's `required_files` list
  (files present are removed; preserve order of remaining)

## Common Pitfalls

1. **Trusting the employee profile summary**: The profile summary's
   `leave_balance_days` can be stale. Always cross-check against the leave
   assignment ledger for the same period. The approved/submitted assignment
   overrides the profile.

2. **Including draft records as authoritative**: Draft leave assignments, draft
   payroll assignments, and draft payroll precheck records must always be
   excluded. They represent planning data, not current state.

3. **Treating Superseded as valid**: Superseded records have been replaced by a
   newer record. They are obsolete and must be excluded alongside drafts.

4. **Missing the folder-tag check**: A folder can have all required files but
   still not be ready if a required tag is missing. Check both `required_files`
   AND `required_tags`.

5. **Using the wrong audit events for a scope**: Document/notice audit events
   should not be included as supporting evidence for leave-source-precedence
   decisions, and vice versa. Scope audit events to the decision domain.

6. **Computing cost total incorrectly**: Sum ALL items in the cost ledger, not
   a subset. The total is a simple sum of `amount` fields.

7. **Confusing notice inspection source with message source**: Notices appear in
   both `/api/messages` and `/api/notifications` (same dataset). Inspect the
   notice packet/message directly rather than relying on case summaries.

8. **Applying the wrong payroll gate**: The recruiting payroll handoff requires
   BOTH an accepted offer AND a submitted assignment. An accepted offer alone is
   not sufficient.

9. **Mixing candidate types in arrays**: `waitlisted_candidates` and
   `rejected_candidates` must contain only candidate IDs. Do not include names
   or other identifiers.

10. **Missing cross-referencing between endpoints**: A complete answer often
    requires data from multiple endpoints. For example, an onboarding closeout
    requires employees + payroll-ledgers (for both leave and salary assignments).
    A case review requires cases + documents + messages + audit.
