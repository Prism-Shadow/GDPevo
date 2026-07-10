# People Lifecycle HRMS — Employee Lifecycle & Policy Operations SOP

## Environment

All API calls go to `http://34.46.77.124:8012`. There is no localhost or port
variable — ignore any task text that references localhost, 127.0.0.1, or
`<port>`. The login credential `ops.lead@peopleops.local / PeopleOps#2026` is
the single ops operator identity used across all tasks.

## API Endpoint Inventory & Data Model

| Endpoint | Returns | Key fields |
|---|---|---|
| `GET /api/summary` | Counts, departments, case breakdown | `departments[].department_id`, `counts` |
| `GET /api/employees` | All 44 employees | `employee_id`, `name`, `department`, `leave_balance_days`, `status`, `hire_date`, `salary_band`, `manager` |
| `GET /api/cases` | All cases, summary level | `case_id`, `employee_id`, `status`, `priority`, `policy_refs`, `owner`, `summary` |
| `GET /api/cases/<id>` | Full case detail | `approvals[]`, `attachments[]`, `audit_events[]`, `comments[]` |
| `GET /api/policies` | All policies | `policy_id`, `title`, `summary`, `sections[].{heading,body}`, `owner`, `status` |
| `GET /api/policies/<id>` | Single policy detail | Same shape |
| `GET /api/payroll-ledgers` | All ledger entries (61) | `ledger_id`, `employee_id`, `record_type`, `status`, `policy_name`, `approved_leave_days`, `base_salary`, `period`, `accrual_batch_id` |
| `GET /api/recruitment` | All openings (2) | `opening_id`, `candidates[]`, `offer_register[]`, `cost_ledger[]`, `notice_packets[]`, `payroll_precheck_records[]` |
| `GET /api/documents` | All folder documents (4) | `document_id`, `files[]`, `required_files[]`, `tags[]`, `required_tags[]`, `ready` |
| `GET /api/messages` | All formal notices (4) | `message_id`, `case_id`, `quality`, `defects[]`, `status`, `channel` |
| `GET /api/notifications` | All notifications (4) | Same shape as messages (mirrors in this env) |
| `GET /api/audit` | All audit events (8) | `audit_id`, `case_id`, `employee_id`, `event`, `detail`, `actor`, `timestamp` |
| `GET /api/audit/<id>` | Single audit event | Same shape |
| `GET /api/attachments/<id>` | Attachment content | `attachment_id`, `kind`, `content`, `name`, `status` |

### Record types in payroll-ledgers

The single `/api/payroll-ledgers` list serves both leave and payroll:

- **`record_type: "Leave assignment"`** — fields: `ledger_id`, `employee_id`, `policy_name`, `approved_leave_days`, `period` (e.g. `"2026"`), `status`
- **`record_type: "Salary assignment"`** — fields: `ledger_id`, `employee_id`, `base_salary`, `period` (e.g. `"2026-03"`), `status`, optionally `accrual_batch_id`
- **Other ledger rows** — `"Payroll worksheet"`, `"People Ops adjustment"`, `"HRMS leave ledger"` — are noise/synthetic data irrelevant to lifecycle decisions unless explicitly referenced by an audit event.

Filter by `record_type` **and** `employee_id` when querying assignments. Never mix record types across leave and payroll decisions.

## Status Precedence (Universal Rule)

For ALL record types — leave assignments, salary assignments, offers:

```
Submitted / Approved  >  Superseded  >  Draft
```

- **Submitted** and **Approved** are authoritative for the current period.
- **Superseded** records belong to a prior state and must be excluded from current decisions.
- **Draft** records are never authoritative — exclude them unconditionally.
- When multiple submitted/approved records exist for the same employee, pick the one with the most recent `updated_at` that still falls within the relevant period.

This rule is codified in:
- **LEAVE-SRC-001 §2.1** — "The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict."
- **PAY-SRC-001 §3.4** — "Use the current submitted salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks."

## Source Precedence (Conflict Resolution)

When two data sources disagree about the same fact, resolve in this order:

1. **Approved/Submitted assignment record** (ledger) — highest authority
2. **Audit event detail** — confirms or contradicts assignment state
3. **Policy document text** — normative rule, not an instance value
4. **Employee profile summary** (`/api/employees`) — lowest authority; may be stale

A profile summary (`leave_balance_days` on the employee object) is only authoritative when no approved or submitted assignment exists for the employee. When an approved assignment exists and the profile shows different values, the assignment wins and the profile is marked stale.

## Five Task Patterns

### Pattern A — Onboarding Closeout (Leave + Payroll)

**Goal:** Verify leave and payroll setup for an employee before approving onboarding close.

**API workflow:**
1. `GET /api/employees` — locate the employee record
2. `GET /api/payroll-ledgers` — filter by `employee_id`, separate into `record_type: "Leave assignment"` and `record_type: "Salary assignment"`
3. Optionally cross-check with `/api/policies/LEAVE-SRC-001` and `/api/policies/PAY-SRC-001`

**Decision rules:**
- **Leave:** Filter leave assignments for the employee. Pick the one with `status: "Approved"` (or `"Submitted"` if no approved exists). Its `policy_name` is the effective leave policy, `approved_leave_days` is the annual days, `ledger_id` is the assignment_id. Exclude all `"Draft"` and `"Superseded"` entries into `excluded_leave_ids`.
- **Payroll:** Filter salary assignments for the employee. Pick the one with `status: "Submitted"`. Its `ledger_id` is the payroll_assignment_id, `base_salary` is the base salary. Exclude all `"Draft"` entries into `excluded_payroll_ids`.
- **Gate:** If both leave and payroll have clean submitted/approved records (no conflicting superseded overriding, no drafts only), gate is `approval_sufficient_when_records_clean` and `closeout_action: "approve_onboarding_close"`.

**Normalized labels to use:**
- `leave_source`: `"leave_assignment_history"` when derived from ledger
- `payroll_status` / `payroll_source_status`: `"submitted"` when the authoritative record is submitted
- `leave_precedence_source`: `"approved_assignment_current_period"`
- `approval_closeout_gate`: `"approval_sufficient_when_records_clean"` or `"approval_not_sufficient_when_folder_or_notice_defective"`
- `final_control_result`: `"approve_closeout"`, `"hold_for_folder_and_notice_defects"`, or `"ready_with_monitoring"`
- `closeout_action`: `"approve_onboarding_close"`, `"block_close_and_reissue_notice"`, or `"open_records_remediation"`

### Pattern B — Case Folder & Notice Review

**Goal:** Determine if a case folder is complete and the formal notice is legally sufficient.

**API workflow:**
1. `GET /api/cases/<case_id>` — get case detail including approvals, attachments, audit_events
2. `GET /api/documents` — locate the folder document for this case; check `required_files` vs `files` and `required_tags` vs `tags`
3. `GET /api/messages` — locate the formal notice for this case; check `quality` and `defects`
4. `GET /api/audit` — find supporting audit events for the case
5. `GET /api/policies/POL-DOCS-2026` and `GET /api/policies/HR-POL-014` — validate policy requirements

**Decision rules:**
- **Folder ready:** `true` ONLY when `files` contains every entry in `required_files` AND `tags` contains every entry in `required_tags`. Otherwise `false`, with `missing_files` listing absent required files.
- **Required tag present:** `true` when all `required_tags` are in the document's `tags` array; otherwise `false`.
- **Notice quality:** Read the message record. If `quality: "defective"`, extract `defects[]` into `notice_defects`. Valid defects: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- **Approval authority:** From `approvals[]` on the case detail — the `approver` field of the final approval step.
- **Approval event ID:** The `approval_id` from the final approval in `approvals[]`.
- **Audit event:** Pick the audit event related to document/notice findings for this case. Exclude unrelated audit events (e.g., leave or payroll scope events).
- **Gate:** `approval_not_sufficient_when_folder_or_notice_defective` when folder lacks files/tags OR notice is defective. `approval_sufficient_when_records_clean` otherwise.

**Normalized labels:**
- `final_decision`: `"approved_with_conditions"`, `"approved"`, `"rejected"`, `"held"`
- `notice_quality`: `"valid"` or `"defective"`
- `audit_scope`: `"document_notice_findings_only"` when scoped to folder/notice
- `next_action`: `"block_close_and_reissue_notice"` when notice defective, `"open_records_remediation"` when folder incomplete, `"approve_onboarding_close"` when clean
- `evidence_source_order`: `"approval_history_folder_notice_audit"` when all sources used
- `escalation_action`: `"open_records_remediation"` when folder missing items
- `records_remediation_owner`: `"Records"` for folder issues, `"People Ops Compliance"` for notice issues, `"Payroll QA"` for payroll
- `final_control_result`: `"hold_for_folder_and_notice_defects"` or `"approve_closeout"`

### Pattern C — Recruitment Reconciliation

**Goal:** Reconcile a recruitment opening — determine selected/waitlisted/rejected candidates, compute costs, and set up follow-up notices and payroll handoff.

**API workflow:**
1. `GET /api/recruitment` — locate the opening by `opening_id`
2. From the recruitment record: inspect `candidates[]`, `offer_register[]`, `cost_ledger[]`, `notice_packets[]`, `payroll_precheck_records[]`
3. Cross-reference with `/api/policies/PAY-SRC-001` for handoff gate rules

**Decision rules:**
- **Selected candidate:** The candidate with `committee_decision: "Selected"` AND an accepted offer in `offer_register[]` (match by `candidate_id`). Extract `offer_id` and `base_salary` from the offer.
- **Waitlisted candidates:** All candidates with `committee_decision: "Waitlisted"`.
- **Rejected candidates:** All candidates with `committee_decision: "Rejected"`.
- **Cost total:** Sum all `amount` values in `cost_ledger[]`. Do not filter or exclude any line items.
- **Notice follow-up required:** Waitlisted and rejected candidates whose notice in `notice_packets[]` has `status` other than `"sent"` (e.g., `"not_sent"`, `"draft_reissue_required"`). Check `required_action` for the specific action.
- **Payroll handoff:** Only for the selected candidate with `offer_register[]` `status: "accepted"`. If `payroll_precheck_records[]` contains draft entries (status `"Draft"`), they do NOT satisfy the handoff gate — only submitted assignments count (PAY-SRC-001 §4.2).
- **Draft payroll allowed:** `false` — draft prechecks never satisfy the gate.

**Candidate arrays:** Must contain **candidate IDs only** (strings), not full candidate objects.

**Normalized labels:**
- `candidate_status_source`: `"interview_feedback_and_offer"` when derived from committee + offer
- `candidate_outcome_control`: `"committee_decision_with_offer_confirmation"`
- `selected_offer_status`: `"accepted"`, `"draft"`, `"withdrawn"`, or `"none"`
- `cost_source`: `"recruitment_cost_ledger"`
- `notice_quality_source`: `"notice_packet_inspection"` when using notice_packets, `"message_notice_inspection"` when using messages
- `waitlisted_followup_action`: `"send_waitlist_notice"` or `"reissue_waitlist_notice_not_rejection"`
- `rejected_followup_action`: `"send_rejection_notice"` or `"no_action"`
- `payroll_handoff_gate`: `"accepted_offer_only"` (only selected + accepted counts)
- `payroll_assignment_status_required`: `"submitted_after_acceptance"`
- `draft_payroll_allowed`: `false`
- `offer_exclusion_reason_for_waitlisted`: `"no_accepted_status_or_offer"`
- `handoff_control_result`: `"submitted_handoff_required_after_acceptance"`
- `onboarding_handoff`: `"create_payroll_precheck"` or `"create_submitted_assignment_after_acceptance"`

### Pattern D — Leave Source Precedence

**Goal:** Resolve which leave policy assignment is authoritative when profile and ledger disagree.

**API workflow:**
1. `GET /api/employees` — get the employee profile (note `leave_balance_days` and `status`)
2. `GET /api/payroll-ledgers` — filter by `employee_id` and `record_type: "Leave assignment"`; find approved/submitted entries
3. `GET /api/audit` — find audit events for this employee related to leave (`event` containing `"leave"`)
4. `GET /api/policies/LEAVE-SRC-001` — confirm the precedence rule

**Decision rules:**
- When an approved leave assignment exists in the ledger, it controls. The profile summary `leave_balance_days` may match or mismatch.
- When the approved assignment's `policy_name` differs from what the profile implies, the assignment wins (`profile_policy_ignored: true`).
- The `precedence_source` is `"approved_assignment_over_profile"` when the approved assignment overrides.
- `leave_precedence_source` is `"approved_assignment_current_period"`.
- The supporting audit event is one scoped to leave (event = `"leave.profile_mismatch"`). Its `audit_id` goes into `supporting_audit_event_ids`.
- Exclude document/notice-scoped audit events (those with `event` like `"folder.tag_missing"`, `"notice.defect"`) from `excluded_audit_event_ids` — they belong to a different scope.
- `audit_scope` is `"leave_source_precedence_only"`.

**Normalized labels:**
- `precedence_source`: `"approved_assignment_over_profile"`, `"employee_profile_summary"`, or `"case_summary_only"`
- `leave_precedence_source`: `"approved_assignment_current_period"`, `"profile_summary_current_period"`, or `"case_summary_only"`
- `audit_result`: `"profile_summary_stale"`, `"ready_with_monitoring"`, or `"block_close"`
- `next_action`: `"update_employee_summary"`, `"open_records_remediation"`, or `"no_action"`
- `audit_scope`: `"leave_source_precedence_only"`, `"document_notice_findings_only"`, or `"payroll_assignment_readiness"`

### Pattern E — Payroll Assignment & Accrual Readiness

**Goal:** Identify the authoritative salary assignment and check if payroll accrual is ready.

**API workflow:**
1. `GET /api/payroll-ledgers` — filter by `employee_id` and `record_type: "Salary assignment"`; separate submitted from draft
2. `GET /api/audit` — find audit events for this employee related to payroll (`event` containing `"payroll"`)
3. `GET /api/policies/PAY-SRC-001` — confirm the source rule

**Decision rules:**
- The submitted salary assignment is authoritative. Extract `ledger_id`, `base_salary`, and the `period` as effective date (format `YYYY-MM-DD`, using the first day of the period e.g. `"2026-04"` → `"2026-04-01"`).
- Draft salary assignments for the same employee are excluded — put their `ledger_id` into `excluded_assignment_id`.
- Accrual readiness: `true` when the submitted assignment has a non-null `accrual_batch_id` field and a corresponding audit event confirms readiness.
- The audit event with `event: "payroll.ready"` supports the readiness decision.
- `control_result`: `"ready_with_monitoring"` when the submitted assignment is clean and audit confirms readiness.

**Normalized labels:**
- `payroll_source_status`: `"submitted"` (the authoritative status)
- `draft_exclusion_rule`: `"exclude_draft_assignment"`
- `audit_scope`: `"payroll_assignment_readiness"`
- `control_result`: `"ready_with_monitoring"`, `"hold_for_folder_and_notice_defects"`, or `"approve_closeout"`

## Sorting & Selection Rules

1. **Multiple records for the same employee:** Filter by `employee_id` first, then by `record_type`, then select by status precedence (Approved/Submitted > Superseded > Draft). If multiple records have equal status, prefer the one with the most recent `updated_at`.
2. **Date formats:** All API dates are ISO-8601. Effective dates for salary assignments use the period's first day (`"2026-04"` → `"2026-04-01"`).
3. **Audit event selection:** Match by `case_id` OR `employee_id`, then filter by `event` type to scope to the task domain (leave, payroll, notice, folder).
4. **Offer-to-candidate matching:** Use `candidate_id` as the join key between `candidates[]` and `offer_register[]`.

## Audit Scope Isolation (Critical)

Audit events carry an `event` field that determines scope. NEVER mix scopes:

| Event pattern | Scope | Use for |
|---|---|---|
| `leave.*` (e.g., `leave.profile_mismatch`) | Leave precedence | Pattern D |
| `payroll.*` (e.g., `payroll.ready`, `payroll.draft_excluded`) | Payroll readiness | Pattern E |
| `notice.*` (e.g., `notice.defect`) | Document/notice | Pattern B |
| `folder.*` (e.g., `folder.tag_missing`) | Document/notice | Pattern B |
| `case.*` (e.g., `case.close_blocked`) | Multi-domain | Patterns B, D, E |
| `cross_module.*` | Escalation package | All patterns |

When a task asks for leave scope, exclude document/notice audit events (and vice versa). Put excluded events in `excluded_audit_event_ids` and supporting events in `supporting_audit_event_ids`.

## Common Pitfalls

1. **Using the employee profile summary as authoritative.** The `/api/employees` `leave_balance_days` field may be stale. Always cross-check against the ledger and let approved assignments override.
2. **Including draft records in authoritative decisions.** Any record with `status: "Draft"` must be excluded from leave policy, payroll assignment, and offer acceptance decisions.
3. **Mixing record types in payroll-ledgers.** Filter by `record_type` before extracting values. A "Salary assignment" row has `base_salary` but `approved_leave_days: 0` — don't accidentally treat it as a leave record.
4. **Mixing audit scopes.** A document/notice audit event (e.g., `folder.tag_missing`) is not evidence for a leave source decision. Scope audit events to the task domain.
5. **Omitting required notice defects.** When `notice_quality` is `"defective"`, each entry in `defects[]` must be listed. A missing defect is a control failure.
6. **Using draft payroll precheck as valid handoff.** PAY-SRC-001 §4.2 explicitly requires submitted assignments. Draft prechecks are placeholders that do not satisfy the gate.
7. **Incomplete folder assessment.** A folder must have ALL `required_files` AND ALL `required_tags` present to be `ready`. Missing even one file or tag means `folder_ready: false`.
8. **Computing recruitment cost incorrectly.** Sum ALL items in `cost_ledger[]` — do not filter by label, line_id, or any other field.
9. **Using the wrong candidate ID format.** Candidate-related output arrays must contain candidate ID strings only (`"CAND-DA-7701"`), not objects.
10. **Overlooking approval event IDs.** The case detail's `approvals[]` array carries the authoritative approval event ID (`approval_id`) and approver (`approver`). Use these, not audit event IDs, for approval tracking.
11. **Policy vs. instance confusion.** Policy documents (`/api/policies`) describe rules. Ledger entries and case details are instances. Use policies to validate, but derive values from instance data.
12. **Notice packet vs. message inspection.** Recruitment tasks use `notice_packets[]` within the recruitment object. Case review tasks use `/api/messages`. Don't cross streams — the notice source label must match: `"notice_packet_inspection"` for recruitment, `"notice_packet_inspection"` (or `"message_notice_inspection"`) for case-level notice review.

## Output Conventions

- All output is JSON matching the provided `answer_template.json` schema.
- Enum fields must use the exact allowed-value strings — no free text, no variations in capitalization or punctuation.
- `list[string]` fields use plain string arrays. Empty arrays use `[]`, not `null`.
- Boolean fields use JSON `true`/`false`, not strings.
- Numeric fields (`annual_days`, `base_salary`, `balance_days`, `recruitment_cost_total`, `offer_base_salary`) use JSON numbers (no quotes).
- Date strings use `YYYY-MM-DD` format.
