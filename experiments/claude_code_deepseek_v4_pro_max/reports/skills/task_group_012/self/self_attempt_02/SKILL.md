# ERP HR Employee Lifecycle & Policy Operations Skill

## Overview

This skill covers People Operations tasks in the Northwind People HRMS: onboarding closeout,
leave source precedence, policy case review (folder readiness + formal notice quality),
recruitment reconciliation, and payroll assignment/accrual readiness. The system exposes a
REST API and a set of interrelated records — employee profiles, payroll ledgers, cases,
policies, documents, messages, audits, and recruitment packets. Decisions always flow from
**authoritative records** (approved/submitted ledger assignments) over summary snapshots
(employee profiles, case summaries, messages alone).

---

## API Usage Workflow

### Base URL
Use the URL from `environment_access.md`. Do not use localhost or 127.0.0.1 unless that
URL itself points there.

### Core Endpoints (all GET)

| Endpoint | What it returns |
|---|---|
| `/api/manifest` | Schema version, seed, file counts, business modules |
| `/api/summary` | Aggregate counts by status, department list |
| `/api/employees` | All employee profiles (summary view; may be stale) |
| `/api/cases` | All cases with summary fields |
| `/api/cases/<case_id>` | Case detail: approvals, attachments, audit_events, comments, policy_refs |
| `/api/policies` | All policies at summary level |
| `/api/policies/<policy_id>` | Single policy with section headings and body text |
| `/api/payroll-ledgers` | Leave assignments, salary assignments, worksheets, adjustments |
| `/api/recruitment` | All openings with candidates, offer_register, cost_ledger, notice_packets |
| `/api/documents` | All document folders with files, tags, required_files, required_tags, ready flag |
| `/api/messages` | All formal notice messages with quality, defects, channel, status |
| `/api/notifications` | System notifications |
| `/api/audit` | All audit events (summary) |
| `/api/audit/<event_id>` | Single audit event detail |
| `/api/attachments/<attachment_id>` | Attachment text content (plain text response) |

### Recommended Investigation Sequence

1. **Identify the subject** (employee, case, or opening) from the task prompt.
2. **Fetch the employee profile** (`/api/employees` → filter by `employee_id`) for
   baseline context — but NEVER treat it as authoritative when ledger records exist.
3. **Fetch the relevant ledger** (`/api/payroll-ledgers` → filter by `employee_id` and
   `record_type`). Distinguish Leave assignment vs Salary assignment rows.
4. **Fetch the case** (`/api/cases/<case_id>`) for approvals, attachments, linked
   audit events, and comments.
5. **Fetch policies** referenced in the case's `policy_refs`.
6. **Fetch documents** (`/api/documents`) for folder readiness checks.
7. **Fetch messages** (`/api/messages`) for formal notice quality checks.
8. **Fetch recruitment** (`/api/recruitment`) for candidate outcomes, offers, costs,
   and notice packets.
9. **Cross-reference audit events** — use `/api/audit` for the global list and
   `/api/audit/<id>` for detail. Audit events are scoped to a single concern; do not
   mix leave-scope audits into document/notice decisions, or vice versa.

---

## Business Rules by Module

### A. Leave Assignment Source Precedence

**Governing policy**: `LEAVE-SRC-001` §2.1 — *"The latest approved or submitted leave
assignment for the period controls. Draft, voided, and obsolete records are excluded
even when profile summaries conflict."*

**Status precedence** (highest to lowest):
1. `Approved` — authoritative
2. `Superseded` — replaced by a later assignment; exclude from current decisions
3. `Draft` — planning only; always exclude

**Decision logic**:
- Find all leave assignments for the employee in the current period (year `2026`).
- Pick the latest `Approved` record (by `updated_at`).
- If no `Approved` exists, fall back to the latest `Submitted` record.
- **Never** use `Draft` records.
- **Never** use `Superseded` records when a newer `Approved` exists for the same period.
- The employee profile's `leave_balance_days` and any inline policy reference are
  **secondary**. When an approved assignment exists and the profile conflicts, the
  profile is stale → `profile_policy_ignored: true`.

**Key fields from ledger**:
- `ledger_id` → `assignment_id`
- `policy_name` → `effective_leave_policy`
- `approved_leave_days` → `annual_days` / `balance_days`
- `status` → determines inclusion/exclusion

### B. Payroll / Salary Assignment Precedence

**Governing policy**: `PAY-SRC-001` §3.4 — *"Use the current submitted salary assignment.
Draft planning assignments do not affect payroll readiness or accrual checks."*

**Status precedence**:
1. `Submitted` — authoritative
2. `Draft` — always exclude

**Decision logic**:
- Find all salary assignments for the employee.
- Pick the `Submitted` record.
- Exclude every `Draft` record.
- Base salary comes from the `Submitted` assignment's `base_salary` field.
- Effective date is the assignment's `updated_at` date (date portion only).

**Accrual readiness**:
- An accrual batch is ready when a `Submitted` salary assignment carries a non-null
  `accrual_batch_id`.
- Draft assignments with accrual data do NOT make accrual ready.

### C. Recruiting Payroll Handoff Gate

**Governing policy**: `PAY-SRC-001` §4.2 — *"Recruiting payroll handoff is created
only after a selected candidate has an accepted offer. The handoff must be submitted;
draft prechecks do not satisfy the assignment gate."*

**Decision logic**:
- Only the **selected** candidate with an **accepted** offer triggers payroll handoff.
- The handoff action is `create_submitted_assignment_after_acceptance` when the
  selected candidate has accepted.
- `draft_payroll_allowed` is always `false` — draft prechecks are not valid handoffs.
- Waitlisted and rejected candidates do not trigger payroll handoff.

### D. Recruitment Reconciliation

**Candidate classification**:
- `committee_decision: "Selected"` → selected candidate
- `committee_decision: "Waitlisted"` → waitlisted candidate
- `committee_decision: "Rejected"` → rejected candidate

**Offer validation**:
- The selected candidate must have an entry in `offer_register` with `status: "accepted"`.
- `offer_id` and `offer_base_salary` come from the accepted offer.

**Cost calculation**:
- `recruitment_cost_total` = **sum of all `amount` values** in `cost_ledger`.
- Source is always `recruitment_cost_ledger` (never case summary).

**Notice follow-up**:
- Check `notice_packets` for each non-selected candidate.
- If `status: "not_sent"` and `required_action` says send → candidate ID goes in
  `notice_followup_required`.
- Waitlisted candidates with unsent notices → `send_waitlist_notice`.
- Rejected candidates with unsent notices → `send_rejection_notice`.
- Notice quality is determined from `notice_packet_inspection` (the notice_packets
  array in the recruitment record), not from messages alone.

**Source hierarchy for recruitment**:
- Candidate status: `interview_feedback_and_offer` (from recruitment endpoint's
  candidates array and offer_register).
- Outcome control: `committee_decision_with_offer_confirmation`.
- Cost: `recruitment_cost_ledger`.
- Notice quality: `notice_packet_inspection`.

### E. Policy Case Folder Readiness

**Governing policy**: `POL-DOCS-2026` §5.1 — *"A folder is not ready unless all
required files and required tags shown in the folder checklist are present."*

**Decision logic**:
- `folder_ready: true` ONLY when **all** `required_files` are present in `files` AND
  **all** `required_tags` are present in `tags`.
- Any missing file → `folder_ready: false`, list missing files in `missing_files`.
- Any missing tag → `required_tag_present: false`.
- Use the `/api/documents` endpoint to find the folder associated with the case.
- Also check case `attachments` of `kind: "Checklist"` — their `content` field
  confirms what is missing.

### F. Formal Notice Quality

**Notice inspection sources** (in priority order):
1. **Notice packet inspection** — the `notice_packets` array in `/api/recruitment`
   or the `messages` endpoint (`/api/messages`) for policy cases.
2. **Message notice inspection** — fallback when only messages are available.
3. **Case summary only** — lowest confidence; do not rely on this.

**Quality determination**:
- A notice is `defective` when its `defects` array is non-empty.
- If `quality` field is explicitly set, use it; otherwise infer from `defects`.
- Defect types (from messages/notice_packets):
  - `missing_ack_deadline` — acknowledgement deadline absent
  - `missing_appeal_instructions` — appeal process not described
  - `missing_waitlist_status` — waitlist status omitted
  - `missing_correct_policy` — references wrong/legacy policy

**Policy requirements** (from `HR-POL-014` §7.1):
International exception formal notices must include: executive approval reference,
time limits, tax equalization, VPN-only access, quarterly compliance review,
**appeal instructions**, and **acknowledgement deadline**.

### G. Closeout / Final Control Gates

**Approval closeout gate**:
- `approval_sufficient_when_records_clean` — all records are clean (no draft reliance,
  no folder defects, no notice defects).
- `approval_not_sufficient_when_folder_or_notice_defective` — any folder or notice
  defect blocks close.

**Final control result**:
- `approve_closeout` — all checks passed, records clean.
- `hold_for_folder_and_notice_defects` — blocked by folder and/or notice issues.
- `ready_with_monitoring` — records are correct but profile/system state needs
  follow-up (e.g., stale profile summary, but assignment is clean).

**Closeout blockers** (can be multiple):
- `missing_required_files` — folder missing required files.
- `missing_required_tags` — folder missing required tags.
- `defective_formal_notice` — formal notice has quality defects.

### H. Cross-Module Escalation

When a case like `XMODULE-77` references related audit events, inspect each
referenced event individually. Do not merge scopes:
- Leave-source audits → only for leave decisions.
- Document/notice audits → only for document/notice decisions.
- Payroll audits → only for payroll decisions.

**Remediation ownership**:
- Missing files/tags → `Records`.
- Defective notices / policy issues → `People Ops Compliance`.
- Payroll assignment issues → `Payroll QA`.

**Notice remediation actions**:
- `reissue_defective_notices` — when formal notice has defects.
- `send_new_offer_notice` — when offer notice needs to be sent.
- `no_notice_action` — when notices are clean.

---

## Audit Event Model

### Event Types and Their Scope

| Event | Scope | Use For |
|---|---|---|
| `leave.profile_mismatch` | `leave_source_precedence_only` | Leave source decisions |
| `payroll.ready` | `payroll_assignment_readiness` | Payroll readiness decisions |
| `payroll.draft_excluded` | `payroll_assignment_readiness` | Payroll draft exclusion |
| `notice.defect` | `document_notice_findings_only` | Notice quality decisions |
| `case.close_blocked` | `document_notice_findings_only` | Folder/notice blocking decisions |
| `folder.tag_missing` | `document_notice_findings_only` | Document/folder decisions |
| `cross_module.escalation_package` | cross-module (inspect each ref separately) | Escalation triage |

### Supporting vs Excluded Audit Events

When making a scoped decision:
- **Supporting**: Audit events whose scope matches the decision being made.
- **Excluded**: Audit events whose scope does NOT match (e.g., exclude
  `folder.tag_missing` events from a `leave_source_precedence_only` decision).

---

## Output Field Conventions

### Normalized Enum Values

**Precedence / source fields**:
- `approved_assignment_over_profile` — approved ledger assignment overrides stale profile.
- `employee_profile_summary` — only when no ledger assignment exists.
- `case_summary_only` — least authoritative; use only when nothing else is available.
- `approved_assignment_current_period` — the approved assignment for the current period.
- `profile_summary_current_period` — profile summary for the current period.
- `leave_assignment_history` — leave data sourced from ledger leave assignments.

**Payroll source status**:
- `submitted` — authoritative submitted assignment.
- `draft` — excluded planning record.
- `superseded` — replaced by a later record.

**Draft exclusion rule**:
- `exclude_draft_assignment` — draft records are always excluded.
- `draft_allowed` — drafts are permitted (rare; almost never used).
- `exclude_superseded_only` — only superseded records excluded.

**Audit scope** (exactly one per decision):
- `leave_source_precedence_only`
- `document_notice_findings_only`
- `payroll_assignment_readiness`

**Closeout / control actions**:
- `approve_onboarding_close` — proceed with close.
- `block_close_and_reissue_notice` — blocked; reissue notice.
- `open_records_remediation` — open remediation workflow.
- `update_employee_summary` — update stale profile.
- `no_action` — nothing needed.

**Recruitment-specific**:
- `interview_feedback_and_offer` — candidate outcome from interview + offer data.
- `committee_decision_with_offer_confirmation` — committee outcome confirmed by offer.
- `notice_packet_inspection` — notice quality from notice_packets array.
- `message_notice_inspection` — notice quality from messages endpoint.
- `recruitment_cost_ledger` — costs from cost_ledger array.
- `case_summary_only` — fallback; least reliable.

**Handoff / assignment gates**:
- `create_submitted_assignment_after_acceptance` — create submitted assignment once offer accepted.
- `create_payroll_precheck` — precheck only (not a full handoff).
- `no_payroll_handoff` — no handoff needed.
- `accepted_offer_only` — only accepted-offer candidates for payroll.
- `accepted_offer_and_submitted_assignment` — both conditions required.
- `all_interviewed_candidates` — all interviewed (rare).
- `submitted_after_acceptance` — submitted assignment required after acceptance.
- `submitted_handoff_required_after_acceptance` — handoff must be submitted after acceptance.
- `submitted_handoff_required` — submitted handoff generally required.
- `no_handoff_required` — no handoff needed.

**Follow-up actions (recruitment)**:
- `send_waitlist_notice` — send waitlist notification.
- `send_rejection_notice` — send rejection notification.
- `reissue_waitlist_notice_not_rejection` — reissue notice without changing to rejection.
- `reissue_rejection_notice` — reissue rejection notice.
- `no_action` — no follow-up needed.

**Offer exclusion reasons**:
- `no_accepted_status_or_offer` — no accepted offer exists.
- `waitlisted_not_selected` — candidate was waitlisted, not selected.
- `already_rejected` — candidate already rejected.

---

## Date, Calculation, and Sorting Rules

### Dates
- All dates are in ISO 8601 format: `YYYY-MM-DD` for date-only, with `T` separator
  for timestamps (e.g., `2026-03-01T09:00`).
- `effective_date` for payroll assignments: use the `updated_at` date portion
  (e.g., `2026-04-01` from `2026-04-01T09:30`).
- For leave assignments, the controlling period is `2026` — filter by `period: "2026"`
  or the start of the period year.

### Sorting / "Latest"
- When multiple assignments exist, the **latest** is determined by `updated_at`
  timestamp (not `ledger_id` order).
- For leave: pick the most recent `Approved` by `updated_at` for the current period.
- For payroll: pick the `Submitted` record (there is typically one).

### Calculations
- **Recruitment cost**: Sum all `amount` values in `cost_ledger`. Use exact arithmetic;
  do not round.
- **Annual leave days / balance days**: Use `approved_leave_days` from the authoritative
  leave assignment. Do NOT use `worksheet_leave_days` from the ledger (that is a
  different field for worksheet purposes).
- For salary assignments, `approved_leave_days` and `worksheet_leave_days` are `0` —
  ignore them; use `base_salary`.

### Candidate Arrays
- Arrays for `waitlisted_candidates`, `rejected_candidates`, and
  `notice_followup_required` must contain **candidate IDs only** (e.g., `"CAND-DA-7702"`),
  not names.

---

## Source Precedence (Cross-Module)

When multiple data sources conflict, resolve in this order:

### For Leave Entitlement
1. Approved leave assignment in payroll ledger (highest)
2. Submitted leave assignment in payroll ledger
3. Employee profile summary (lowest; stale when ledger exists)

### For Base Salary
1. Submitted salary assignment in payroll ledger (highest)
2. Employee profile salary_band (descriptive only; not a dollar amount)
3. Draft salary assignment (excluded)

### For Candidate Outcomes
1. Recruitment endpoint: `candidates[].committee_decision` + `offer_register[].status`
   (highest)
2. Audit events referencing the recruitment
3. Case summary (lowest)

### For Notice Quality
1. `notice_packets` in recruitment, or `messages` endpoint for policy cases (highest)
2. Audit events on notice defects (corroborating)
3. Case summary (lowest)

### For Folder Readiness
1. `/api/documents` folder record (highest)
2. Case attachment of kind `"Checklist"` (corroborating)
3. Case summary (lowest)

### Evidence Source Order (for case review)
1. `approval_history_folder_notice_audit` — full chain: approvals → folder → notice → audit.
2. `folder_notice_audit` — folder → notice → audit (no approvals).
3. `audit_only` — audit events only.

---

## Common Pitfalls

1. **Draft contamination**: Always filter out `Draft` status records from both leave
   and payroll ledgers. Draft records are planning placeholders and have no
   authoritative weight. This is the single most common error.

2. **Profile staleness**: Employee profile `leave_balance_days` may not match the
   approved assignment. When a ledger assignment exists with a different value, the
   profile is stale. Set `profile_policy_ignored: true` and use the ledger value.

3. **Scope mixing**: Do not use document/notice audit events (e.g., `folder.tag_missing`,
   `notice.defect`) to support leave-source-precedence decisions, or vice versa. Each
   audit event has exactly one scope. `supporting_audit_event_ids` and
   `excluded_audit_event_ids` must respect this boundary.

4. **Superseded vs Draft confusion**: `Superseded` means a record was replaced by a
   newer one — it was once valid but is now obsolete. `Draft` means it was never valid.
   Both are excluded from current decisions, but they are semantically different.
   Only `Superseded` goes in `exclude_superseded_only` lists.

5. **Cost sum precision**: Sum all cost_ledger amounts exactly as stored. Do not
   estimate, round, or omit line items.

6. **Tag vs file confusion**: `folder_ready` requires BOTH all `required_files` AND all
   `required_tags`. A folder with all files but a missing tag is NOT ready. Check both
   independently.

7. **Waitlist notice reissue vs rejection**: When a waitlisted candidate's notice is
   defective, the action is `reissue_waitlist_notice_not_rejection` — reissue the
   waitlist notice without converting it to a rejection. Do not confuse this with
   `send_rejection_notice` (for rejected candidates).

8. **Recruitment notice packets vs messages**: For recruitment tasks, notice quality
   comes from `notice_packets` in the recruitment endpoint, NOT from the general
   `/api/messages` endpoint (unless the notice_packets reference a specific
   `message_id`). For policy cases, notice quality comes from `/api/messages`.

9. **Payroll handoff requires accepted offer**: A candidate who is "Selected" but
   whose offer is still `draft` or absent does NOT trigger payroll handoff. The offer
   must be `accepted`.

10. **Audit detail vs audit list**: `/api/audit/<event_id>` returns the same fields
    as the entry in `/api/audit` or in a case's `audit_events`. The detail endpoint
    is useful for confirming an event exists and reading its full detail field.

11. **Employee ID in case vs employee ID in task**: Cases like `CASE-118` have
    `employee_id: "EMP-118"` (the subject employee). But audit events attached to the
    case may reference different entities. Always match on the task's target employee.

12. **Folder document lookup**: A case may reference a folder in its attachments
    (kind: "Checklist"), but the authoritative folder record is in `/api/documents`.
    Cross-reference both — the document endpoint provides `required_files`,
    `required_tags`, `files`, `tags`, and `ready`; the attachment provides a human
    summary confirming what is missing.

13. **Multiple assignments for same employee**: An employee may have multiple leave
    assignments or salary assignments. Always select based on status precedence and
    recency, not by picking the first one returned.

14. **Policy reference without case detail**: When a case lists `policy_refs`, fetch
    each policy at `/api/policies/<policy_id>` to read the section text. The policy
    body text contains the authoritative business rule.

15. **`worksheet_leave_days` vs `approved_leave_days`**: In leave assignment records,
    use `approved_leave_days` for the employee's leave entitlement. The
    `worksheet_leave_days` field is a separate worksheet tracking value and should not
    be used for entitlement decisions.
