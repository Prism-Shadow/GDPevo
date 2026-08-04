## When to Use

Use this skill when asked to verify or decide PeopleOps lifecycle records — employee onboarding closeout, case folder and notice review, leave source precedence, recruiting pipeline reconciliation, or payroll assignment and accrual readiness — against a REST API that exposes employee, case, policy, payroll-ledger, document, message, notification, audit, and recruitment endpoints.

---

## How to Solve PeopleOps Lifecycle Tasks

### 1. Explore the API

Start with two discovery endpoints before drilling into specifics:

- `GET /api/manifest` — lists business modules, data file sizes, and entry-point URLs.
- `GET /api/summary` — shows record counts, case status breakdowns, and department rosters.

Use these to understand the shape of the dataset, then pull the relevant resources:

- `GET /api/employees` — all employee profiles (name, designation, department, leave_balance_days, salary_band, status, remote_profile).
- `GET /api/payroll-ledgers` — mixed endpoint containing both **leave assignments** (record_type `Leave assignment`) and **salary assignments** (record_type `Salary assignment`), plus HRMS leave ledgers, payroll worksheets, and People Ops adjustments. Filter by `employee_id` for a specific person.
- `GET /api/cases` and `GET /api/cases/{id}` — case list and per-case detail including approvals, attachments, comments, and case-level audit events.
- `GET /api/policies` — policy documents with effective dates, owners, and section bodies.
- `GET /api/documents` — folder checklists per document: required files, present files, required tags, present tags, and overall readiness.
- `GET /api/notifications` and `GET /api/messages` — formal notices with quality (`valid`/`defective`), defect lists, and required remediation.
- `GET /api/audit` and `GET /api/audit/{id}` — audit events with actor, event type, detail, and QA results.
- `GET /api/recruitment` — candidate pipelines per opening: committee decisions, offer register, cost ledger, notice packets, and payroll precheck records.

### 2. Apply Source Precedence Rules

Three policy documents dictate which records are authoritative. Always apply them:

**LEAVE-SRC-001**: The latest **Approved** or **Submitted** leave assignment for the period controls. Draft, voided, superseded, and obsolete records are excluded — even when employee profile summaries disagree. The employee profile `leave_balance_days` field is treated as a **summary** that may be stale; the assignment ledger is the source of truth.

**PAY-SRC-001**: Use the current **Submitted** salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks. For recruiting: payroll handoff is created **only after** a selected candidate has an accepted offer, and the handoff must be **submitted**; draft prechecks do not satisfy the assignment gate.

**POL-DOCS-2026**: A case folder is **not ready** unless **all** required files **and** all required tags shown in the folder checklist are present. A single missing file or missing tag makes the folder not ready, regardless of how many other items are present.

**HR-POL-014**: Formal notices for remote-work exceptions must include appeal instructions and an acknowledgement deadline.

### 3. Cross-Reference Audit Events

Always verify decisions against audit events. An audit event with a QA result (e.g., `profile_summary_stale`, `ready_with_monitoring`, `block close`) is the final authority on the state of a record. When constructing an answer:

- For leave-precedence tasks, include only audit events scoped to leave source issues (`leave_source_precedence_only`). Explicitly exclude document/notice or payroll audit events from the leave-scope decision.
- For document/notice tasks, include only audit events scoped to document and notice findings (`document_notice_findings_only`). Exclude leave or payroll events.
- For payroll/accrual tasks, include only payroll-scoped audit events (`payroll_assignment_readiness`).

Supporting audit events are those that corroborate the primary audit finding. Excluded audit events are those from adjacent scopes that should not influence the current decision.

### 4. Notice Quality Assessment

A formal notice is defective when it lacks any of:
- `missing_ack_deadline` — no acknowledgement deadline.
- `missing_appeal_instructions` — no appeal instructions.
- `missing_waitlist_status` — waitlist status omitted (recruiting context).
- `missing_correct_policy` — references an incorrect or stale policy.

Always check both the notifications/messages endpoint for the quality field **and** the notice packet within recruitment data for the `defects` array.

### 5. Folder Readiness

A folder's readiness is determined by comparing its `files` list against `required_files`, and its `tags` list against `required_tags`. A folder is ready (`true`) only when both sets are fully satisfied. Missing files and missing tags are each independent blockers.

### 6. Recruiting Pipeline Reconciliation

For recruitment openings:
- **Selected candidate**: The one with `committee_decision: "Selected"`. Confirm their offer status in the `offer_register` (must be `accepted` for payroll handoff).
- **Waitlisted candidates**: Those with `committee_decision: "Waitlisted"`. Check notice packets for defective waitlist notices.
- **Rejected candidates**: Those with `committee_decision: "Rejected"`. Check whether rejection notices have been sent.
- **Cost total**: Sum all `amount` fields in the `cost_ledger`.
- **Payroll handoff**: Only the selected candidate with an accepted offer triggers a payroll assignment. Draft prechecks for waitlisted candidates are excluded.

### 7. Construct the Answer

Given the `answer_template.json` in the task payloads directory:

- Every answer must be valid JSON matching the template structure exactly.
- For fields with `"type": "enum"`, use **only** one of the listed `allowed_values`. Never substitute free-text explanations for enum fields.
- Use the exact identifiers (employee IDs, case IDs, assignment IDs, audit event IDs, document IDs, offer IDs, candidate IDs) as they appear in API responses.
- Derive values directly from API data: employee profiles, assignment ledgers, case details, audit events, document checklists, notice quality fields, and recruitment records.
- Explicit `"correct"` decisions are confirmed by audit QA results.

### 8. Common Decision Patterns

| Scenario | Decision |
|----------|----------|
| Approved leave assignment exists; profile disagrees | Use the approved assignment; profile is stale |
| Only draft leave/payroll assignment exists | No authoritative record yet; cannot close |
| Submitted payroll assignment + clean audit | `ready_with_monitoring` |
| Folder missing required files or tags | `hold_for_folder_and_notice_defects` |
| Defective formal notice | `block_close_and_reissue_notice` / `reissue_defective_notices` |
| Selected candidate with accepted offer | `create_submitted_assignment_after_acceptance` |
| Waitlisted candidate with defective notice | `reissue_waitlist_notice_not_rejection` |
| All records clean (approved assignment, submitted payroll, no defects) | `approve_onboarding_close` / `approve_closeout` |
