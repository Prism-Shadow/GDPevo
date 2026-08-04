## When to Use

Use this skill when working inside a PeopleOps lifecycle management environment that exposes a REST API with `/api/summary`, `/api/manifest`, `/api/employees`, `/api/cases`, `/api/payroll-ledgers`, `/api/policies`, `/api/audit`, `/api/documents`, `/api/messages`, `/api/recruitment`, and `/api/notifications` endpoints. The skill applies to verification tasks involving employee onboarding closeout, leave/payroll reconciliation, case folder and notice reviews, recruitment pipeline handoff, leave-source precedence, and payroll accrual readiness.

## Core Business Rules (Distilled from Policies)

### Leave Source Precedence (LEAVE-SRC-001)
- The latest **approved** or **submitted** leave assignment for the period is authoritative.
- **Exclude** records with status `Draft`, `Voided`, or `Superseded` — even when an employee profile summary shows different values.
- An approved leave assignment **overrides** a stale employee profile summary when confirmed by the ledger, policy document, and audit detail.

### Payroll Assignment Source (PAY-SRC-001)
- The current **submitted** salary assignment controls base salary.
- **Exclude** `Draft` planning assignments — they do not affect payroll readiness or accrual checks.
- For recruitment handoffs (§4.2): a payroll handoff is created only **after** a selected candidate has an **accepted offer**. The handoff must be **submitted**; draft prechecks do not satisfy the assignment gate.

### Lifecycle Folder Checklist (POL-DOCS-2026)
- A case folder is **not ready** unless **all** required files listed in the folder checklist are present **and** all required tags are applied.
- Verify via `/api/documents`: compare `files` and `tags` against `required_files` and `required_tags`.

### Formal Notice Requirements (HR-POL-014)
- International/executive exception notices must include: appeal instructions, acknowledgement deadline, tax equalization, VPN-only access, quarterly compliance review.
- Inspect `/api/messages` for `defects` lists and `quality` assessments.
- Common defects: `missing_appeal_instructions`, `missing_ack_deadline`, `missing_waitlist_status`, `missing_correct_policy`.

## Data-Source Navigation Pattern

1. **Orient**: Call `/api/manifest` and `/api/summary` first to learn available modules, record counts, departments, and case statuses.
2. **Identify the subject**: Use `/api/employees` to find the employee, `/api/cases` to find the case, or `/api/recruitment` to find the opening.
3. **Drill into authoritative records**: Fetch the specific resource (e.g., `/api/cases/{id}`, `/api/payroll-ledgers`, `/api/audit/{id}`).
4. **Cross-reference with policies**: Read `/api/policies` and `/api/policies/{id}` to confirm the governing rule before deciding.
5. **Validate with audit**: Use `/api/audit` to find audit events that confirm or contradict the current state.

## Record Status Filtering

When evaluating assignments and ledgers:
- **Include**: records with status `Approved` or `Submitted`.
- **Exclude**: records with status `Draft`, `Superseded`, or `Voided`.
- For leave assignments: prefer `Approved` over `Submitted`; use the latest by `updated_at` within the relevant period.
- For payroll assignments: prefer `Submitted`; `Approved` payroll assignments may also be valid if no `Submitted` exists for the period.

## Audit Scope Separation

Audit events belong to distinct scopes. When answering a scope-specific question:
- **Leave source precedence** scope: include audit events with `leave.*` events; **exclude** `folder.*`, `notice.*`, and `payroll.*` events from the leave-scope decision.
- **Document/notice findings** scope: include audit events with `notice.*` or `case.close_blocked` events; **exclude** leave and payroll audit events.
- **Payroll assignment readiness** scope: include `payroll.*` audit events; **exclude** document and notice audit events.
- The `audit_scope` field controls which evidence is relevant.

## Enum-Only Answers

Many answer-template fields are enums with a fixed set of `allowed_values`. Always:
- Use the exact string from the `allowed_values` list in the answer template.
- Never use free-text where an enum value exists.
- Match the enum label to the business situation described by the data and policies.

## Recruitment Pipeline Pattern

When working with a recruitment opening:
- Candidates have `committee_decision` values: `Selected`, `Waitlisted`, `Rejected`.
- Selected candidate → check `offer_register` for offer status (`accepted`, `draft`, `withdrawn`).
- Payroll handoff: required only for the accepted, selected candidate; must be a submitted assignment (not a draft precheck).
- Notice follow-up: inspect `notice_packets` for unsent or defective notices; use `required_action` field for the correct action.
- Cost totals: sum all amounts in the `cost_ledger` array.

## Case Review Pattern

When reviewing a policy case:
- Check `approvals[]` for the final decision, approver identity, and approval event ID.
- Check `/api/documents` against the case's document references for folder readiness.
- Check `/api/messages` for formal notice quality and defects.
- Check `/api/audit` for events linked to the case that confirm or flag issues.
- If folder is incomplete or notice is defective → result is a hold/block; remediation is required before close.

## Employee Closeout Pattern

When verifying an employee for onboarding closeout:
- Gather leave assignments from `/api/payroll-ledgers` filtered by `employee_id` and `record_type: "Leave assignment"`.
- Gather salary assignments from `/api/payroll-ledgers` filtered by `employee_id` and `record_type: "Salary assignment"`.
- Apply status filtering (exclude Draft, Superseded; use Approved/Submitted).
- The effective leave policy comes from the authoritative assignment, not the employee profile summary.
- If records are clean (no draft/superseded confusion, submitted payroll, approved leave) → approve closeout.
- If records conflict or contain only drafts → block and remediate.

## Verification Checklist

Before finalizing any answer:
- Confirm the authoritative record type for each field (assignment vs. profile vs. case summary).
- Re-read the relevant policy sections.
- Verify that excluded IDs are correctly identified (draft/superseded records).
- Confirm audit scope alignment: supporting events match the scope, non-scope events are excluded.
- Use only the exact enum strings from the answer template.
