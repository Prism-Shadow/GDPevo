# PeopleOps Business Rules

These are the domain rules that every PeopleOps verification task depends on. They are derived from the policy documents, audit detail, and answer patterns observed across the task types.

## Record precedence

### Leave assignments

When multiple leave assignment records exist for an employee:

1. Collect all ledger records with `record_type: "Leave assignment"` for the target `employee_id`.
2. Exclude any record with `status: "Draft"` — drafts are planning artifacts, never authoritative.
3. Among the remaining records, prefer `status: "Approved"` over `status: "Superseded"`.
4. If two approved records exist for the same period, the later one (by `updated_at`) controls.
5. The controlling record's `policy_name` is the effective leave policy and its `approved_leave_days` is the authoritative balance.

A `status: "Submitted"` leave assignment is treated as authoritative when no Approved record exists for the same period.

### Salary assignments

When multiple salary assignment records exist:

1. Collect all ledger records with `record_type: "Salary assignment"` for the target `employee_id`.
2. Exclude any record with `status: "Draft"` — these are planning artifacts.
3. The controlling record is the one with `status: "Submitted"` (or `"Approved"` if no Submitted exists).
4. Base salary, effective date, and assignment ID come from the controlling record.

### Approved assignment overrides stale profile summary

When an approved leave assignment in the ledger gives a different policy or day count than the employee's profile:

- The approved ledger assignment controls. The profile `leave_balance_days` and any implied policy are treated as outdated.
- The profile is marked as stale (`profile_policy_ignored: true`).
- The audit event confirming this mismatch is included in the leave-scope supporting events.

## Folder readiness

A document folder (from `/api/documents`) is ready when **both** conditions hold:

1. Every entry in `required_files` is present in the `files` array.
2. Every entry in `required_tags` is present in the `tags` array.

If either condition fails, `folder_ready` is `false` and the missing items go into `missing_files` and/or inform the `required_tag_present` boolean.

## Notice quality

A formal notice (from `/api/messages` or `/api/notifications`) is:

- `"valid"` when `defects` is an empty array.
- `"defective"` when `defects` contains one or more defect labels.

Defect labels in this domain:

| Defect label | Meaning |
|-------------|---------|
| `missing_ack_deadline` | The notice omits a required acknowledgement deadline |
| `missing_appeal_instructions` | The notice omits required appeal instructions |
| `missing_waitlist_status` | A waitlist notice fails to mention the candidate's waitlist status |
| `missing_correct_policy` | The notice references an incorrect or stale policy |

## Recruitment reconciliation

### Candidate outcomes

Candidate status is determined by `committee_decision` in the recruitment opening:

- `"Selected"` → the selected candidate
- `"Waitlisted"` → waitlisted candidates
- `"Rejected"` → rejected candidates

### Offer verification

- The selected candidate must have a matching entry in `offer_register` with `status: "accepted"`.
- The `offer_id` and `base_salary` come from that entry.

### Cost total

`recruitment_cost_total` is the arithmetic sum of every `amount` in the `cost_ledger` array for the opening. Sum all line items; do not filter.

### Notice follow-up

- Waitlisted and rejected candidates need follow-up notices if their `notice_packets` entry shows `status: "not_sent"` or `required_action` is present.
- The follow-up action label comes from the answer template's enum for that field.

### Payroll handoff

- Payroll handoff is created only for the **selected** candidate with an **accepted** offer.
- Draft payroll prechecks (`payroll_precheck_records` with Draft status) do not satisfy the handoff gate.
- The required assignment status is `"submitted_after_acceptance"` when the accepted candidate needs a submitted payroll assignment.

## Audit scoping

Tasks reference three distinct audit scopes. Use these to decide which audit events to include or exclude:

| Scope | Include audit events where | Exclude audit events where |
|-------|---------------------------|---------------------------|
| `leave_source_precedence_only` | `event` is about leave policy/profiles (e.g., `leave.profile_mismatch`) | `event` is about documents, notices, folders, or payroll (e.g., `folder.tag_missing`, `notice.defect`) |
| `document_notice_findings_only` | `event` is about documents, folders, tags, or notice defects | `event` is about leave or payroll |
| `payroll_assignment_readiness` | `event` is about payroll readiness or draft exclusion | `event` is about leave, documents, or notices |

An audit event may share the same `case_id` or `employee_id` as the target but belong to a different scope. Exclude it from the supporting events array when its scope doesn't match the task's scope.

## Escalation and cross-module events

`cross_module.escalation_package` audit events reference multiple other events and cases. They are informational — do not include them in supporting events for a single-scope decision unless the task explicitly asks for cross-module analysis.

## Closeout gates

| Gate label | When it applies |
|-----------|----------------|
| `approval_sufficient_when_records_clean` | All records are authoritative (no drafts, no stale profiles), folder is ready, notice is valid |
| `approval_not_sufficient_when_folder_or_notice_defective` | Folder is not ready, or notice is defective, or required files/tags are missing |

## Draft exclusion

Any record with `status: "Draft"` (whether leave assignment, salary assignment, or payroll precheck) is excluded from the authoritative answer. List excluded draft records by their IDs in the appropriate `excluded_*` field from the answer template.
