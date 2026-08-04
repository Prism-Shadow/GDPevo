---
name: peopleops-console
description: PeopleOps HR console agent for employee onboarding closeout, case folder and notice review, recruitment reconciliation, leave source precedence validation, and payroll assignment readiness. Use when working with the PeopleOps API at a configured task environment to verify HR records, reconcile recruitment outcomes, validate leave/payroll assignments against submitted records, or audit case folders and formal notices. The skill encodes draft-exclusion rules, source-precedence hierarchies, cross-reference verification patterns, and audit-scope segmentation applicable to any PeopleOps business task.
---

# PeopleOps Console Skill

## Setup

Read `environment_access.md` in the working directory to obtain:
- `BASE_URL` — the runner base URL (typically `http://task-env:9012/`)
- Login credentials (`ops.lead@peopleops.local` / `PeopleOps#2026`)
- The list of allowed GET and POST endpoints

All data retrieval happens through the listed GET endpoints. The only mutation allowed is `POST /api/cases/{case_id}/comments`.

## Data Authority Rules

### Draft Exclusion
Draft records are never authoritative. Always prefer **submitted** or **approved** records. When a draft and a submitted record exist for the same entity, use the submitted record and explicitly exclude the draft.

### Source Precedence

| Domain | Authoritative Source (highest first) |
|--------|--------------------------------------|
| Leave policy & balance | 1. Approved leave assignment history (current period)  2. Employee profile summary |
| Payroll assignment | 1. Submitted assignment  2. Draft assignment (exclude, do not use) |
| Recruitment candidate outcome | 1. Interview feedback + offer status  2. Case summary |
| Case evidence | 1. Approval history + folder + notice + audit  2. Folder + notice + audit  3. Audit only |
| Notice quality | 1. Notice packet inspection  2. Message notice inspection  3. Case summary |
| Cost totals | 1. Recruitment cost ledger  2. Case summary |

When the higher-precedence source confirms a different state than a lower one, the lower source is considered **stale** or **superseded** and should be marked for exclusion or update.

## Cross-Reference Verification

For any finding, confirm against at least **three independent sources** when available:
- **Ledger / case records** — the operational data
- **Policy documents** — the rules that should govern the data
- **Audit events** — the timestamped trail of decisions

Discrepancies among sources indicate a remediation need. When all sources agree against a draft or summary record, the draft/summary record is stale.

## Audit Scope Segmentation

When reviewing audit events:
- Include only audit events whose scope matches the current review (leave, payroll, document/notice).
- Explicitly **exclude** adjacent audit events from unrelated scopes.
- Report both `supporting_audit_event_ids` (included) and `excluded_audit_event_ids` (excluded) when the template requires them.

## Folder & Notice Review

When evaluating a case folder:
- Check for **required files** — every case type has a mandatory file checklist.
- Check for **required tags** — a missing tag is a blocker.
- Assess **notice quality** as `valid` or `defective`.
- Common notice defects: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- Blockers are: `missing_required_files`, `missing_required_tags`, `defective_formal_notice`.

## Recruitment Reconciliation

When reconciling a recruitment opening:
- Determine candidate outcomes from interview feedback and offer register.
- Selected candidate: has an accepted offer.
- Waitlisted: interviewed, offer status not accepted.
- Rejected: no offer or offer withdrawn/rejected.
- Sum all recruitment cost ledger line items for `recruitment_cost_total`.
- Payroll handoff gate: `accepted_offer_only` (only the selected, accepted candidate) or `accepted_offer_and_submitted_assignment`.

## Output Rules

- Return **only valid JSON** matching the provided answer template exactly.
- Use **normalized enum labels** from the template — never free-text explanations for gate, source, status, scope, or control-result fields.
- Arrays contain **identifiers only** (employee IDs, assignment IDs, audit event IDs, etc.).
- Monetary values are numbers, not strings.
- Dates use ISO 8601 format (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`).

## Common Workflow

1. Parse the task prompt to identify the business domain and target records.
2. Fetch all relevant data via GET endpoints.
3. Identify submitted/approved vs. draft records for the target entity.
4. Apply source precedence to determine the authoritative state.
5. Cross-reference against policy documents and audit events.
6. Segment audit events by scope; include supporting, exclude unrelated.
7. Assess folder readiness, notice quality, or recruitment outcomes as applicable.
8. Populate the answer template with normalized enum values.
9. Return the JSON object — no markdown, no explanatory text.
