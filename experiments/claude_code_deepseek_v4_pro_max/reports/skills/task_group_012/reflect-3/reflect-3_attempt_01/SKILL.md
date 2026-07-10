# ERP HR Employee Lifecycle & Policy Operations

## Overview

This skill covers PeopleOps verification and reconciliation workflows across
employee onboarding, leave management, payroll assignments, policy-case folder
readiness, formal-notice quality, recruitment-pipeline reconciliation, and
audit-driven control decisions. All workflows operate against the shared
People Lifecycle HRMS API.

## API Workflow

### Key Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/manifest` | Module listing and file counts |
| `GET /api/summary` | Department list, case counts, overview |
| `GET /api/employees` | All employee profiles (leave balance, status, department, salary band) |
| `GET /api/policies` | Policy documents with sections and effective dates |
| `GET /api/cases` | All cases (status, owner, policy refs, summary) |
| `GET /api/cases/<case_id>` | Case detail including **approvals**, attachments, audit events, comments |
| `GET /api/cases/<case_id>/comments` | Case comments (may 404 if none) |
| `GET /api/payroll-ledgers` | Leave assignments, salary assignments, accruals — mixed record types |
| `GET /api/recruitment` | Openings with candidates, offer register, cost ledger, notice packets, payroll precheck records |
| `GET /api/documents` | Folder inventories: files present, required files, required tags, tags present, ready flag |
| `GET /api/messages` | Formal notices and messages with quality assessment and defect lists |
| `GET /api/notifications` | Same structure as messages; cross-reference by case_id |
| `GET /api/audit` | All audit events; use `GET /api/audit/<event_id>` for single-event detail |

### Query Strategy

1. Start with `/api/summary` and `/api/manifest` for orientation.
2. Identify the target entity (employee, case, opening) from the task prompt.
3. Pull the relevant main collection (`/api/employees`, `/api/cases`, `/api/recruitment`).
4. Pull `/api/payroll-ledgers` — this is the **single most important cross-cutting source** because it contains leave assignments, salary assignments, and accrual records all in one list. Filter by `employee_id` and `record_type`.
5. Pull `/api/policies` for the business rules that determine which records control.
6. For case-level work, always call `GET /api/cases/<case_id>` to get **approvals** (not visible in the list endpoint) and attachments.
7. Pull `/api/documents` for folder readiness checks.
8. Pull `/api/messages` for notice quality inspection.
9. Pull `/api/audit` for QA findings that confirm or override conclusions.

---

## Record-Type Discrimination in Payroll Ledgers

The `/api/payroll-ledgers` endpoint mixes several record types. Always filter by
`record_type` **and** `employee_id` together:

| `record_type` | Meaning | Used For |
|---|---|---|
| `Leave assignment` | Authoritative leave policy + days | Leave policy decisions |
| `Salary assignment` | Authoritative base salary + effective date | Payroll verification |
| `HRMS leave ledger` | System leave data (may be superseded) | Cross-validation only |
| `Payroll worksheet` | Payroll-run data | Cross-validation only |
| `People Ops adjustment` | Manual adjustments | Cross-validation only |

**Only `Leave assignment` and `Salary assignment` record types are
authoritative for business decisions.** Other record types appear in the ledger
but should never be mistaken for the controlling assignment.

### Status Precedence for Assignments

For both leave and salary assignments, apply this status filter:

1. **Approved** — controls (highest authority)
2. **Submitted** — controls if no Approved exists for the same period
3. **Superseded** — always exclude from current decisions
4. **Draft** — always exclude; never affects readiness, accrual, or closeout

When multiple approved/submitted records exist for the same employee and period,
the **latest by `updated_at`** controls. This rule is codified in policy
`LEAVE-SRC-001` section 2.1.

**Policy `PAY-SRC-001` section 3.4**: Use the current submitted salary
assignment. Draft planning assignments do not affect payroll readiness or
accrual checks.

---

## Source Precedence Rules

### Leave Policy

| Priority | Source | When It Controls |
|---|---|---|
| 1 (highest) | Approved leave assignment in payroll ledger | Always, when status is Approved |
| 2 | Submitted leave assignment | When no Approved exists for the period |
| 3 | Employee profile `leave_balance_days` | Only when no assignment exists in ledger |

An approved leave assignment **always overrides** the employee profile summary
when they conflict. If the employee profile shows a different policy or balance
than the approved assignment, the profile is **stale** and should be flagged for
update.

### Payroll Salary

| Priority | Source | When It Controls |
|---|---|---|
| 1 | Submitted salary assignment (`record_type: "Salary assignment"`) | Always |
| 2 | Draft salary assignment | Never controls — exclude |

### Document/Folder Readiness

A folder is **ready** only when:
1. ALL `required_files` are present in the `files` array
2. ALL `required_tags` are present in the `tags` array

If either condition fails, `ready` is `false`. Missing items become closeout
blockers. Per policy `POL-DOCS-2026` section 5.1.

### Notice Quality

Inspect messages (or notifications) linked to the case. A notice is
**defective** when `quality` is `"defective"` and `defects` is non-empty.
Common defects:
- `missing_appeal_instructions`
- `missing_ack_deadline`
- `missing_waitlist_status`
- `missing_correct_policy`

Draft-status messages are still evaluated for content quality — "Draft" on a
message means it hasn't been sent but its content can still be reviewed.

---

## Audit Event Handling

### Audit Scopes

When working with audit events, classify each event by scope:

| Audit Scope | When to Use |
|---|---|
| `leave_source_precedence_only` | Leave policy/balance decisions |
| `document_notice_findings_only` | Folder readiness + notice quality review |
| `payroll_assignment_readiness` | Payroll salary assignment + accrual checks |

### Supporting vs Excluded Audit Events

- **`supporting_audit_event_ids`**: Audit events whose findings **confirm** the
  decision within the current scope. Include events that directly corroborate
  your determination.

- **`excluded_audit_event_ids`**: Audit events that belong to the **same case or
  employee** but address a **different scope**. For example, when the scope is
  `leave_source_precedence_only`, exclude document/notice audit events
  (e.g., `folder.tag_missing`) — they are valid for their own domain but must
  not influence the leave-scope decision.

The same case may have multiple audit events across different scopes. Always
filter by relevance to the current question.

### Key Audit Events

- `leave.profile_mismatch` → profile is stale; approved assignment controls
- `payroll.ready` → submitted assignment is ready with monitoring
- `notice.defect` → formal notice has defects and must be reissued
- `case.close_blocked` → folder and/or notice issues prevent close
- `payroll.draft_excluded` → draft payroll record excluded; submitted controls
- `folder.tag_missing` → required tag absent from folder
- `cross_module.escalation_package` → package linking multiple related events

---

## Case Approvals

Case approvals are **only** visible in the case detail endpoint
(`GET /api/cases/<case_id>`), not in the list endpoint. The `approvals` array
contains:

- `approval_id` — use this as the **approval event ID**
- `approver` — the role or person who approved (use as `approval_authority`)
- `decision` — `"Approved"`, `"Rejected"`, etc.
- `step` — e.g., `"Final approval"`
- `decided_at` — timestamp

The approval authority is the **approver** from the approval record, not the
case owner.

---

## Recruitment Reconciliation

### Data Sources (in priority order)

1. **Recruitment record** (`/api/recruitment`) — candidates, offer register, cost ledger, notice packets
2. **Messages** (`/api/messages`) — cross-reference by `case_id` for notice quality
3. **Policy** `PAY-SRC-001` section 4.2 for payroll handoff rules

### Candidate Classification

Use the `committee_decision` field from each candidate entry:
- `"Selected"` → `selected_candidate`
- `"Waitlisted"` → `waitlisted_candidates`
- `"Rejected"` → `rejected_candidates`

### Offer Register

The `offer_register` array contains the accepted/withdrawn/draft offer for the
selected candidate. Match by `candidate_id`. Key fields: `offer_id`,
`base_salary`, `status`.

### Cost Calculation

**`recruitment_cost_total`** is the **sum of all `amount` values** in the
`cost_ledger` array. Sum every line item — do not filter or exclude any.

### Notice Follow-up

Check `notice_packets` for each non-selected candidate. A candidate requires
follow-up when `status` is `"not_sent"` or `"draft_reissue_required"`. The
`required_action` field tells you what to do:

| `required_action` | Meaning |
|---|---|
| `send_waitlist_notice` | Initial waitlist notice not yet sent |
| `send_rejection_notice` | Initial rejection notice not yet sent |
| `reissue_waitlist_notice_not_rejection` | Notice was sent but is defective — reissue without changing status |

### Payroll Handoff Gate

Per `PAY-SRC-001` section 4.2:
- A payroll handoff is created **only after** a selected candidate has an
  **accepted offer**.
- The handoff must be **submitted**; draft prechecks do **not** satisfy the
  assignment gate.
- Check `payroll_precheck_records` — if empty, no handoff has been created yet.
- Draft payroll records (`status: "Draft"`) must be excluded.

---

## Output Field Conventions

### Normalized Labels (Always Use These, Never Free-Text)

**Source fields** indicate where the data was drawn from:
- `leave_assignment_history` — data from payroll-ledger leave assignments
- `employee_profile_summary` — data from the employee profile only
- `case_summary_only` — using case-level summary when nothing deeper is available
- `interview_feedback_and_offer` — from recruitment candidates + offer register
- `recruitment_cost_ledger` — from recruitment cost_ledger array
- `notice_packet_inspection` — from recruitment notice_packets or messages
- `message_notice_inspection` — from messages endpoint
- `approval_history_folder_notice_audit` — full evidence chain
- `folder_notice_audit` — folder + notice + audit only
- `audit_only` — audit events only

**Precedence/status fields:**
- `approved_assignment_current_period` — approved assignment controls for current period
- `profile_summary_current_period` — profile controls (only when no assignment exists)
- `approved_assignment_over_profile` — assignment explicitly overrides stale profile

**Payroll status:**
- `submitted` — the controlling status for payroll
- `draft` — excluded from decisions
- `superseded` — excluded from decisions

**Exclusion rules:**
- `exclude_draft_assignment` — drafts are ignored
- `draft_allowed` — drafts may be considered (rare, only for pre-handoff previews)
- `exclude_superseded_only` — only superseded records excluded (drafts may remain)

**Closeout gates:**
- `approval_sufficient_when_records_clean` — all checks pass
- `approval_not_sufficient_when_folder_or_notice_defective` — one or more defects block close

**Control results:**
- `approve_closeout` — no issues; proceed
- `hold_for_folder_and_notice_defects` — blocking issues in folder/notice
- `ready_with_monitoring` — clean but requires ongoing monitoring

**Next actions:**
- `approve_onboarding_close` — proceed to close
- `block_close_and_reissue_notice` — notice defective; reissue before close
- `open_records_remediation` — folder/document issues need records-team fix
- `update_employee_summary` — employee profile is stale

**Recruitment handoff:**
- `create_submitted_assignment_after_acceptance` — create payroll assignment after offer accepted
- `create_payroll_precheck` — create preliminary check before full assignment
- `no_payroll_handoff` — no handoff needed (no accepted offer)

**Handoff gate:**
- `accepted_offer_only` — only an accepted offer is needed
- `accepted_offer_and_submitted_assignment` — both offer acceptance and submitted assignment required

---

## Date and Sorting Rules

- All dates are ISO 8601 (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`).
- For assignment precedence, compare by `updated_at` timestamp — latest
  non-draft, non-superseded record wins.
- Payroll `effective_date` comes from the controlling salary assignment's
  `updated_at` field, formatted as `YYYY-MM-DD`.
- The `period` field on assignments indicates the applicability window
  (e.g., `"2026"`, `"2026-04"`). Match periods when comparing records.
- Case `due_at` and `opened_at` use full ISO timestamps.
- Approval `decided_at` is the authoritative decision timestamp.

### Accrual Batch Matching

An accrual batch ID (e.g., `ACCR-2026-04-B`) appears on the submitted salary
assignment. The batch is ready when the audit confirms the submitted assignment
matches the batch and no blocking conditions exist.

---

## Common Pitfalls

1. **Using the employee profile for leave policy when a ledger assignment
   exists.** The profile `leave_balance_days` is only authoritative when no
   assignment record exists. Always check `/api/payroll-ledgers` first, filter
   by `employee_id` and `record_type: "Leave assignment"`.

2. **Treating all payroll-ledger records as assignments.** The ledger contains
   many record types (HRMS leave ledger, Payroll worksheet, People Ops
   adjustment). Only `Leave assignment` and `Salary assignment` record types
   carry authoritative weight.

3. **Including draft or superseded records in decisions.** Always filter by
   status: Approved > Submitted. Superseded and Draft records are excluded
   regardless of their `updated_at` date.

4. **Confusing the case owner with the approval authority.** The approval
   authority comes from the `approver` field in the case detail's `approvals`
   array, not from the case's `owner` field.

5. **Mixing audit scopes.** A single case may have audit events spanning leave,
   payroll, and document scopes. When the question is scoped to one domain,
   events from other domains go in `excluded_audit_event_ids` — they are not
   supporting events for the current scope.

6. **Checking only `document.ready` without inspecting `required_files` vs
   `files` and `required_tags` vs `tags`.** The `ready` flag is a convenience
   but the specific missing items must be listed individually.

7. **Overlooking the case detail endpoint for approvals.** The list endpoint
   (`/api/cases`) does not include the `approvals` array. Always call
   `/api/cases/<case_id>` when approval information is needed.

8. **Forgetting to sum ALL cost ledger items.** Every line in `cost_ledger`
   counts toward `recruitment_cost_total` — do not filter by label or category.

9. **Treating message `status: "Draft"` as un-reviewable.** Draft messages still
   have `quality` and `defects` fields that must be evaluated for notice-quality
   decisions.

10. **Using the wrong assignment for effective date.** The effective date for
    payroll comes from the **controlling submitted salary assignment's**
    `updated_at`, not from the employee's `hire_date` or the case's `opened_at`.

11. **Missing the policy documents as decision rules.** `/api/policies` contains
    the business rules that determine which records control. Always cross-check
    decisions against the relevant policy sections (especially
    `LEAVE-SRC-001` section 2.1 and `PAY-SRC-001` sections 3.4 and 4.2).
