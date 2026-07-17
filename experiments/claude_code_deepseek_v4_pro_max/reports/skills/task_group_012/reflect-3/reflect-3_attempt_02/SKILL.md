# ERP HR Employee-Lifecycle & Policy-Operations Skill

## Overview

This skill covers verification and reconciliation tasks across the People Lifecycle
HRMS: onboarding closeout, remote-work policy case review, recruitment
reconciliation, leave source precedence, and payroll assignment readiness.

## API Usage Workflow

### Step 1 — Orient
Fetch the manifest (`GET /api/manifest`) for available modules and record counts,
then the summary (`GET /api/summary`) for case statuses and department listings.

### Step 2 — Gather evidence by domain
Use the authoritative endpoints for each domain; never rely on a single source.

| Domain | Primary Endpoint | Drill-down |
|--------|-----------------|------------|
| Employee profile | `GET /api/employees` | filter by `employee_id` |
| Leave assignments | `GET /api/payroll-ledgers` | filter by `employee_id` + `record_type: "Leave assignment"` |
| Salary assignments | `GET /api/payroll-ledgers` | filter by `employee_id` + `record_type: "Salary assignment"` |
| Cases | `GET /api/cases` then `GET /api/cases/<id>` | includes approvals, attachments, audit_events, comments |
| Policies | `GET /api/policies` then `GET /api/policies/<id>` | policy sections contain the business rules |
| Documents/Folders | `GET /api/documents` | `ready`, `required_files`, `required_tags`, `tags`, `files` |
| Messages/Notices | `GET /api/messages` | `quality`, `defects`, `channel` |
| Audit events | `GET /api/audit` then `GET /api/audit/<id>` | `event`, `detail`, `case_id`, `employee_id` |
| Recruitment | `GET /api/recruitment` | candidates, offer_register, cost_ledger, notice_packets |

### Step 3 — Cross-reference with policy
Always cross-reference findings against the relevant policy document. Policy
sections are the authoritative business rules. The four policies are:

- **LEAVE-SRC-001** — Leave Source Precedence (assignment vs profile)
- **PAY-SRC-001** — Payroll Assignment Source (§3.4 salary, §4.2 recruiting handoff)
- **HR-POL-014** — Remote Work Policy (jurisdiction, exception, notice requirements)
- **POL-DOCS-2026** — Lifecycle Folder Checklist (required files and tags)

## Business Rules

### Record Status Precedence
- **Approved** or **Submitted** records control. These are the authoritative
  "effective" records.
- **Draft** records are planning artifacts and MUST be excluded from all
  operational decisions (leave, payroll, accrual, closeout).
- **Superseded** records are obsolete and MUST be excluded alongside drafts.
- **Voided** records (if present) are excluded per LEAVE-SRC-001 §2.1.

### Leave Source Precedence (LEAVE-SRC-001 §2.1)
- The latest approved or submitted leave assignment for the current period
  controls the effective leave policy and annual days.
- The employee profile summary (`leave_balance_days`, etc.) is subordinate.
  When it conflicts with an approved assignment, the profile is stale and
  must be ignored.
- Even when the profile and assignment happen to match numerically, the
  assignment is still the authoritative source; the profile is not the basis
  for the decision.
- The leave assignment's `policy_name` is the effective leave policy.
- `approved_leave_days` on the controlling assignment is the authoritative
  annual leave balance.

### Payroll Assignment Source (PAY-SRC-001 §3.4)
- The current **submitted** salary assignment controls base salary and
  payroll readiness.
- Draft salary assignments do not affect payroll readiness or accrual checks.
- The effective date is derived from the submitted record's `updated_at` date.
- When an `accrual_batch_id` is present on the submitted record, it links the
  assignment to its accrual batch.

### Recruiting Payroll Handoff (PAY-SRC-001 §4.2)
- Payroll handoff is created ONLY after a selected candidate has an **accepted**
  offer. No acceptance → no handoff.
- The handoff assignment must be **submitted**; draft prechecks do not satisfy
  the gate.
- Waitlisted and rejected candidates do not trigger payroll handoff — they have
  no accepted offer.

### Folder Readiness (POL-DOCS-2026 §5.1)
- A folder is ready ONLY when ALL `required_files` are present AND ALL
  `required_tags` are present in the folder's tags.
- Compare the folder's `files` array against `required_files` and the `tags`
  array against `required_tags`. Missing items are blockers.
- The folder's `ready` boolean reflects this check but always verify against
  the actual arrays.

### Formal Notice Requirements (HR-POL-014 §7.1)
- Formal notices for executive/exception approvals must include:
  - Acknowledgement deadline
  - Appeal instructions
- Missing any of these makes the notice **defective** and the notice must be
  reissued before closeout.

### Recruitment Candidate Outcomes
- Candidate status is determined by `committee_decision` (Selected / Waitlisted /
  Rejected), confirmed against the `offer_register`.
- The selected candidate is the one with `committee_decision: "Selected"` and
  an accepted offer in the offer register.
- Waitlisted and rejected candidates are listed separately by their
  committee_decision value.
- Notice packets dictate follow-up: if `status: "not_sent"`, the action is
  **send** (not reissue). If `status: "draft_reissue_required"` or the notice
  has defects, the action is **reissue**.

## Output Field Conventions

### Normalized Labels
Always use the exact enum values from the answer template. Key mappings:

**Record status → normalized label:**
- `"Approved"` or `"Submitted"` → `"submitted"` (for payroll_source_status)
- `"Draft"` → excluded; `draft_exclusion_rule: "exclude_draft_assignment"`
- `"Superseded"` → excluded alongside drafts

**Leave source:**
- When using ledger-based assignment history → `"leave_assignment_history"`
- When the approved assignment overrides the profile → `"approved_assignment_over_profile"`
- Precedence label → `"approved_assignment_current_period"`

**Audit scope alignment:**
- Leave precedence tasks → `"leave_source_precedence_only"`
- Payroll/accrual tasks → `"payroll_assignment_readiness"`
- Document/notice tasks → `"document_notice_findings_only"`

**Closeout gates:**
- Clean records (no missing files, no defective notices, drafts excluded) →
  `"approval_sufficient_when_records_clean"`
- Any folder or notice defect →
  `"approval_not_sufficient_when_folder_or_notice_defective"`

**Final control results:**
- All clear → `"approve_closeout"`
- Defects found → `"hold_for_folder_and_notice_defects"`
- Pass with caveats → `"ready_with_monitoring"`

**Recruitment-specific:**
- Handoff gate → `"accepted_offer_and_submitted_assignment"`
- Assignment status required → `"submitted_after_acceptance"`
- Draft payroll allowed → `false`
- Offer exclusion for waitlisted → `"no_accepted_status_or_offer"`
- Handoff control result → `"submitted_handoff_required_after_acceptance"`
- Waitlisted action (not sent) → `"send_waitlist_notice"`
- Rejected action (not sent) → `"send_rejection_notice"`
- Status source → `"interview_feedback_and_offer"`
- Outcome control → `"committee_decision_with_offer_confirmation"`
- Cost source → `"recruitment_cost_ledger"`
- Notice quality source → `"notice_packet_inspection"`

**Case review:**
- Approval with conditions → `"approved_with_conditions"` (not `"approved"`)
- Evidence order when using all sources → `"approval_history_folder_notice_audit"`
- Notice evidence source → `"message_notice_inspection"` (when using the
  messages endpoint) or `"notice_packet_inspection"` (when using recruitment
  notice_packets)

## Date, Calculation, and Sorting Rules

### Dates
- Effective dates come from the controlling record's `updated_at` field,
  formatted as `YYYY-MM-DD`.
- When a record has a `period` field (e.g., `"2026-04"`), the effective date
  is the `updated_at` truncated to the date portion.
- Hire date from the employee profile may be relevant for onboarding but is
  not the effective date for payroll/leave assignments.

### Calculations
- **Recruitment cost total**: Sum ALL `amount` values in the `cost_ledger`
  array. Do not filter, do not round — use the exact sum.
- **Annual leave days**: Use `approved_leave_days` from the controlling
  approved/submitted leave assignment (integer).
- **Base salary**: Use `base_salary` from the controlling submitted salary
  assignment (number, as-is).

### Sorting
- No implicit sorting is required for candidate or assignment lists; list
  items in the order they appear in the source data.

## Source Precedence (Cross-Domain)

| Decision | Primary Source | Override Rule |
|----------|---------------|---------------|
| Leave policy & days | Payroll-ledger leave assignment (Approved/Submitted) | Overrides employee profile summary |
| Base salary | Payroll-ledger salary assignment (Submitted) | Draft assignments excluded |
| Candidate outcome | Recruitment committee_decision + offer_register | Committee decision confirmed by offer status |
| Folder readiness | Documents endpoint (files + tags vs required) | The `ready` boolean is a hint; verify arrays |
| Notice quality | Messages endpoint (defects array) | Cross-check with audit events |
| Payroll readiness | Payroll-ledger + audit events | Audit event detail is authoritative |
| Accrual readiness | Audit event detail + accrual_batch_id on submitted assignment | Must match |

## Common Pitfalls

1. **Draft records are NOT "close enough."** Draft leave assignments and draft
   payroll assignments must always be listed in the excluded IDs. Including
   them or omitting them from exclusions will produce incorrect results.

2. **Superseded records must also be excluded.** Just like drafts, superseded
   records are obsolete and must appear in the excluded-IDs list. Do not treat
   them as merely "old but valid."

3. **"Approved with conditions" ≠ "Approved."** Use the exact normalized label
   `"approved_with_conditions"` when the approval decision note contains
   conditions. The plain `"approved"` label is reserved for unconditional
   approvals.

4. **Folder `ready` boolean is not sufficient.** Always check `required_files`
   against `files` and `required_tags` against `tags` explicitly. The `ready`
   flag is a summary; the arrays are the ground truth.

5. **Notices never sent vs notices needing reissue.** When `notice_packets`
   show `status: "not_sent"`, the action is `"send_*_notice"`. When status
   is `"draft_reissue_required"` or defects are present, the action is
   `"reissue_*_notice"`. Do not confuse these.

6. **Audit scope must match the task domain.** Using a payroll audit event
   for a leave-precedence decision (or vice versa) contaminates the analysis.
   Always align `audit_scope` with the primary decision type, and list
   non-matching audit events in `excluded_audit_event_ids`.

7. **The employee profile leave balance is not authoritative.** Even when it
   coincidentally matches the approved assignment, the profile is not the
   source of truth. The assignment record from the payroll-ledger endpoint
   always controls.

8. **Recruitment cost total is a raw sum.** Sum all `cost_ledger[].amount`
   values; do not apply discounts, filters, or rounding.

9. **Payroll handoff requires BOTH acceptance AND submission.** An accepted
   offer alone is insufficient — the resulting assignment must be submitted
   (not draft). The gate is `"accepted_offer_and_submitted_assignment"`.

10. **Missing files AND defective notices can coexist as blockers.** When both
    are present, list both in `closeout_blockers` and set the final control
    result to `"hold_for_folder_and_notice_defects"`.

11. **Tag presence is binary.** A required tag is either in the folder's `tags`
    array or it isn't. Partial or similar tag names do not count.

12. **Effective date precision.** Always use the full `YYYY-MM-DD` format
    derived from the controlling record's `updated_at`, not the `period`
    string (which may be `"2026-04"`).
