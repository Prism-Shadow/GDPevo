# ERP HR Employee-Lifecycle and Policy-Operations Skill

## Overview

This skill covers five related HRMS operations:
1. **Onboarding closeout** — verifying leave and payroll setup before approving close
2. **Remote-work policy case review** — folder readiness and formal notice quality
3. **Recruitment reconciliation** — candidate outcomes, offer verification, notice follow-up, and payroll handoff
4. **Leave source precedence** — determining the authoritative leave policy when sources conflict
5. **Payroll assignment and accrual readiness** — verifying submitted salary assignment and accrual batch status

---

## API Usage Workflow

### Endpoint Reference

All endpoints are under the base URL. Useful public endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/manifest` | Module inventory, record counts, seed |
| `GET /api/summary` | Aggregate counts, departmental structure |
| `GET /api/employees` | Employee profiles (summary-level, possibly stale) |
| `GET /api/payroll-ledgers` | Authoritative leave assignments, salary assignments, and ledger entries |
| `GET /api/cases` | All case headers |
| `GET /api/cases/<case_id>` | Case detail including approvals, attachments, audit events, comments |
| `GET /api/policies` | All policy documents |
| `GET /api/policies/<policy_id>` | Policy detail with sections |
| `GET /api/recruitment` | Recruitment openings with candidates, offer register, cost ledger, notice packets, payroll precheck records |
| `GET /api/documents` | Document folders with files, required files, required tags, and readiness status |
| `GET /api/messages` | Formal notices and messages with quality assessment and defect lists |
| `GET /api/notifications` | Notification records (often mirrors messages) |
| `GET /api/audit` | All audit events |
| `GET /api/audit/<event_id>` | Single audit event detail |

### Recommended Investigation Order

1. **Start with `/api/manifest`** to understand the environment shape and record counts.
2. **Locate the subject entity** — employee via `/api/employees`, case via `/api/cases`, or recruitment opening via `/api/recruitment`.
3. **Pull authoritative records** from `/api/payroll-ledgers` filtered by `employee_id`. Never treat the employee profile summary as authoritative for leave or payroll; it may be stale.
4. **Retrieve case detail** via `/api/cases/<case_id>` which embeds approvals, attachments, audit events, and comments.
5. **Check folder readiness** via `/api/documents` — compare actual files and tags against required lists.
6. **Inspect notices** via `/api/messages` or the `notice_packets` inside `/api/recruitment`.
7. **Verify with audit events** — `/api/audit` or embedded in case detail.
8. **Consult policy** via `/api/policies/<policy_id>` for the governing business rule.
9. **For recruitment**, pull `/api/recruitment` for the full opening packet: candidates, offer register, cost ledger, notice packets, and payroll precheck records.

---

## Core Business Rules

### 1. Leave Source Precedence (Policy LEAVE-SRC-001)

**Rule:** The latest **approved or submitted** leave assignment record for the period controls. Draft, voided/superseded, and obsolete records are **always excluded**, even when the employee profile summary shows different values.

**Authoritative record type:** `Leave assignment` (in `/api/payroll-ledgers` filtered by `record_type`).

**Precedence order:**
1. Approved leave assignment (highest authority)
2. Submitted leave assignment
3. Employee profile summary (stale, low trust — use only when no assignment records exist)
4. Case summary only (lowest trust)

**Other record types** (`People Ops adjustment`, `HRMS leave ledger`, `Payroll worksheet`) are **supporting records only** — they do not determine the authoritative leave policy or balance.

**When to ignore the profile summary:** An approved or submitted leave assignment **overrides** the `leave_balance_days` and policy shown in `/api/employees`. The profile is an approximation; the ledger assignment is the source of truth.

### 2. Payroll Assignment Source (Policy PAY-SRC-001 §3.4)

**Rule:** Use the current **submitted** salary assignment. **Draft** planning assignments do not affect payroll readiness or accrual checks. **Superseded** records are obsolete.

**Authoritative record type:** `Salary assignment` with status `Submitted`.

**Precedence order:**
1. Submitted salary assignment (authoritative)
2. Draft — excluded
3. Superseded — excluded

**Effective date** comes from the `updated_at` field of the submitted assignment.

### 3. Folder Readiness (Policy POL-DOCS-2026 §5.1)

**Rule:** A folder is **not ready** unless **ALL** required files **AND ALL** required tags are present.

- `ready: true` only when: `required_files ⊆ actual files` AND `required_tags ⊆ actual tags`
- If any required file is missing → `ready: false`
- If any required tag is missing → `ready: false`
- The `ready` field in `/api/documents` is pre-computed and authoritative.

### 4. Formal Notice Quality

**Required elements for a valid formal notice:**
- Acknowledgement deadline
- Appeal instructions
- Correct policy reference
- Waitlist status (for waitlist notices specifically)

**Recognized defect codes:**
- `missing_ack_deadline` — no acknowledgement deadline in the notice
- `missing_appeal_instructions` — no appeal instructions
- `missing_waitlist_status` — waitlist notice omits waitlist status
- `missing_correct_policy` — references wrong/legacy policy

**Quality determination:**
- `valid` — no defects
- `defective` — one or more defects present

**Evidence sources** (in priority order):
1. `notice_packet_inspection` — notice packets from `/api/recruitment` or `/api/messages` with explicit `defects` and `quality` fields
2. `message_notice_inspection` — message records with `defects` arrays
3. `case_summary_only` — fallback; lowest reliability

**Notice quality in messages vs notifications:** Messages and notifications typically contain the same data. Use the first source that has explicit `quality` and `defects` fields. When both exist and differ, prefer messages.

### 5. Recruitment Handoff Gate (Policy PAY-SRC-001 §4.2)

**Rule:** Payroll handoff is created **only after** a selected candidate has an **accepted offer**. The handoff assignment must be **submitted**; draft prechecks do **not** satisfy the assignment gate.

**Candidate outcome source precedence:**
1. Committee decision + offer register confirmation (highest authority)
2. Case summary only
3. Message-only status (lowest)

**Payroll handoff actions:**
- `create_submitted_assignment_after_acceptance` — selected candidate accepted; create and submit handoff
- `create_payroll_precheck` — preliminary check only, insufficient for gate
- `no_payroll_handoff` — no accepted candidate

**Draft payroll precheck records** (in `/api/recruitment` → `payroll_precheck_records`) are **never** acceptable for the handoff gate — only a submitted assignment satisfies the requirement.

**Payroll handoff gate scoping:**
- `accepted_offer_only` — only the accepted candidate matters for payroll
- `accepted_offer_and_submitted_assignment` — require both offer acceptance and submitted assignment
- `all_interviewed_candidates` — broader scope (rare)

### 6. Audit Scope Rules

**Three mutually exclusive audit scopes:**

| Scope | Use when reviewing |
|---|---|
| `document_notice_findings_only` | Folder readiness or formal notice quality |
| `leave_source_precedence_only` | Determining authoritative leave policy |
| `payroll_assignment_readiness` | Verifying payroll assignment and accrual status |

**Audit inclusion/exclusion rules:**
- When scoped to one domain (e.g., leave), **exclude** audit events from adjacent domains (e.g., document/notice findings, payroll events).
- The audit event that directly addresses the domain question is the **primary** audit event.
- Supporting audit events are those whose `event` field matches the domain being reviewed.
- Events with mismatched domains (e.g., `folder.tag_missing` when doing leave precedence) must be in `excluded_audit_event_ids`.

**Audit event types and their domains:**
- `leave.profile_mismatch` → leave scope
- `payroll.ready`, `payroll.draft_excluded` → payroll scope
- `notice.defect`, `folder.tag_missing`, `case.close_blocked` → document/notice scope
- `cross_module.escalation_package` → cross-module (references related events; review each before assigning)

### 7. Closeout Gate Logic

**Gate determination:**
- `approval_sufficient_when_records_clean` → All required records present, no defective notices, no missing files/tags, drafts properly excluded
- `approval_not_sufficient_when_folder_or_notice_defective` → At least one of: missing required files, missing required tags, defective formal notice

**Final control results:**
- `approve_closeout` — all records clean, closeout can proceed
- `hold_for_folder_and_notice_defects` — blocking issues found in folder or notice
- `ready_with_monitoring` — records are clean but the audit recommends ongoing monitoring (e.g., `payroll.ready` with "ready_with_monitoring" detail)

### 8. Closeout Actions

- `approve_onboarding_close` — records clean; proceed with close
- `block_close_and_reissue_notice` — defective notice; reissue required before close
- `open_records_remediation` — missing files/tags; open remediation workflow

**Blockers:**
- `missing_required_files` — at least one required file absent from folder
- `missing_required_tags` — at least one required tag absent from folder
- `defective_formal_notice` — notice has one or more quality defects

---

## Record Statuses and Their Meaning

| Status | Meaning | Authoritative? |
|---|---|---|
| `Approved` | Approved and active | **Yes** — for leave assignments |
| `Submitted` | Submitted and awaiting/live | **Yes** — for payroll assignments |
| `Draft` | Planning only, not live | **No** — always exclude |
| `Superseded` | Replaced by newer record | **No** — always exclude |

---

## Output Field Conventions

### Normalized Enum Labels

Always use the exact enum values from the answer template — never free-text descriptions. Key enums:

**Source/gate labels:**
- `approved_assignment_over_profile` — precedence when an approved assignment beats the profile summary
- `approved_assignment_current_period` — leave source is the approved assignment
- `profile_summary_current_period` — leave source is the profile (only when no assignment exists)
- `case_summary_only` — fallback when nothing better is available

**Control results:**
- `approve_closeout` / `hold_for_folder_and_notice_defects` / `ready_with_monitoring`

**Status values:**
- `submitted` / `draft` / `superseded`

**Notice quality:**
- `valid` / `defective`

**Folder required tag action:**
- `no_tag_action` — tag is present, no action needed
- `add_required_tag` — tag is missing, must be added

**Remediation owners:**
- `Records` — missing files/tags in the document folder
- `People Ops Compliance` — policy violations or cross-module issues
- `Payroll QA` — payroll-specific issues

**Escalation actions:**
- `block_close_and_reissue_notice` / `open_records_remediation` / `no_action`

---

## Calculation Rules

### Recruitment Cost Total

Sum **all** `amount` values from the recruitment opening's `cost_ledger` array. Do not filter by label or line type — every ledger line item counts.

### Leave Balance Days

Take `approved_leave_days` from the authoritative leave assignment record (not the employee profile and not from supporting ledger entries).

### Accrual Readiness

Accrual is `ready: true` when:
1. A submitted salary assignment exists for the employee
2. The assignment references an accrual batch ID
3. The audit confirms `payroll.ready` status

---

## Date and Sorting Rules

### Period Format
- Annual periods: `"2026"`
- Monthly periods: `"2026-03"`, `"2026-04"`, etc.

### Record Sorting (for same employee, same record_type)
When multiple records exist, sort by status precedence:
1. `Approved`/`Submitted` (tie-break by most recent `updated_at`)
2. `Superseded` (excluded from authority)
3. `Draft` (excluded from authority)

Within the same status, pick the **most recently updated** record (`updated_at` descending).

### Policy Effective Date
All policies in this environment have `effective_date: "2026-01-01"`.

---

## Evidence Source Order

For case reviews, the evidence source order indicates which sources were consulted and in what priority:

- `approval_history_folder_notice_audit` — full chain: approvals → folder checklist → notice inspection → audit detail
- `folder_notice_audit` — folder, notice, and audit only (no approvals)
- `audit_only` — audit events only

---

## Common Pitfalls

1. **Trusting the employee profile summary.** The `leave_balance_days` and policy in `/api/employees` can be stale. Always verify against `/api/payroll-ledgers` for the employee's leave and salary assignments.

2. **Including draft records.** Draft assignments (leave or payroll) must **always** be excluded from the authoritative determination, even if they have a newer date or higher values than approved/submitted records.

3. **Including superseded records.** "Superseded" means the record was replaced. It is not authoritative and must be excluded. Use the superseding (newer approved/submitted) record instead.

4. **Confusing record types.** Only `Leave assignment` record types determine leave policy. `People Ops adjustment`, `HRMS leave ledger`, and `Payroll worksheet` entries are **supporting records** — their values do not override the assignment record.

5. **Assuming folder is ready when some files/tags exist.** All required files AND all required tags must be present. Partial completeness = not ready.

6. **Mixing audit scopes.** When determining leave source precedence, exclude document/notice audit events. When reviewing folder/notice quality, exclude leave and payroll audit events. Audit events from the wrong domain will mislead the conclusion.

7. **Assuming notice is valid because it was sent.** A sent notice can still be defective. Always check the `quality` field and `defects` array in the message or notification record.

8. **Handoff for non-selected candidates.** Only the accepted candidate triggers payroll handoff. Waitlisted and rejected candidates need notice follow-up, not payroll setup.

9. **Draft payroll prechecks.** Draft precheck records in recruitment data do NOT satisfy the payroll handoff gate. A submitted assignment is required.

10. **Cost ledger filtering.** Sum ALL cost ledger line items — do not filter by label or exclude any line.

11. **Off-by-one in evidence precedence.** When the audit event explicitly names the controlling record (e.g., "Approved assignment LA-118-APP-02 controls leave policy"), that audit finding is binding. Don't override it with your own record comparison.

12. **Notice quality from wrong source.** When `/api/messages` has explicit `quality` and `defects` fields, use those rather than inferring quality from the case summary alone. If notice packets in `/api/recruitment` are available for the candidate, those take priority.
