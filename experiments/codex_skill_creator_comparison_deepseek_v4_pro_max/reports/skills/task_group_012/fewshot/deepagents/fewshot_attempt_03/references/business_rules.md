# Business Rules

These rules apply across all PeopleOps Console tasks. Apply them in the order given below.

## 1. Source Precedence Rules

### 1.1 Leave Source Precedence

When determining an employee's effective leave policy and balance, apply this precedence:

1. The latest **Approved** leave assignment in the payroll ledger for the current period (2026) is authoritative.
2. If no Approved assignment exists, use the latest **Submitted** assignment.
3. **Draft** and **Superseded** leave assignments must be excluded.
4. An employee profile summary (`/api/employees`) is informational only. When the profile's `leave_balance_days` or implied policy conflicts with an approved assignment, the approved assignment controls and the profile is considered stale.

Policy confirmation: Policy `LEAVE-SRC-001` (Leave Source Precedence) §2.1 states the latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict.

### 1.2 Payroll Assignment Source

When determining payroll/salary values:

1. Use the current **Submitted** salary assignment from the ledger.
2. **Draft** planning assignments do not affect payroll readiness or accrual checks. Exclude them.
3. **Superseded** assignments are excluded.

Policy confirmation: Policy `PAY-SRC-001` (Payroll Assignment Source) §3.4 states the current submitted salary assignment controls base salary. Draft planning assignments do not affect readiness.

### 1.3 Recruitment Candidate Status

When determining candidate outcomes:

1. Use the `committee_decision` field from the recruitment entry's `candidates` array combined with the `offer_register` for confirmation.
2. A candidate is `Selected` only when `committee_decision` is `Selected` AND there is a matching entry in `offer_register`.
3. `Waitlisted` and `Rejected` candidates are determined by their `committee_decision`.
4. Do not rely on case summaries or message status alone — always cross-reference the recruitment data.

## 2. Draft Exclusion Rules

### 2.1 Leave Assignments

Exclude any leave assignment with status `Draft`. These are planning records, not authoritative.

### 2.2 Payroll / Salary Assignments

Exclude any salary assignment with status `Draft`. Only `Submitted` controls current payroll.

### 2.3 Superseded Records

Exclude records with status `Superseded`. They have been explicitly replaced.

### 2.4 Recruitment Payroll Prechecks

Draft precheck records (in `payroll_precheck_records` with status `Draft`) are placeholders. They do not satisfy the payroll assignment gate.

## 3. Notice Quality Rules

### 3.1 Formal Notice Defects

A formal notice is `defective` when it lacks any of the required elements. Possible defects:

- `missing_ack_deadline` — the notice does not include an acknowledgement deadline
- `missing_appeal_instructions` — the notice does not include appeal instructions
- `missing_waitlist_status` — a waitlist notice omits the waitlist status
- `missing_correct_policy` — the notice references an incorrect or legacy policy

### 3.2 Notice Review

Inspect the `messages` API (`/api/messages`) and recruitment `notice_packets` for quality assessment. The `defects` array on a message or notice packet enumerates specific defects. The `quality` field is `defective` when any defect exists.

## 4. Folder Readiness Rules

### 4.1 Required Evidence

A document folder is **ready** only when ALL of the following are true:

1. All `required_files` are present in the `files` array.
2. All `required_tags` are present in the `tags` array.

If either condition fails, the folder is **not ready**. The `missing_files` are the set difference `required_files - files`.

Policy confirmation: Policy `POL-DOCS-2026` (Lifecycle Folder Checklist) §5.1 states a folder is not ready unless all required files and required tags shown in the folder checklist are present.

## 5. Audit Scoping Rules

### 5.1 Audit Scope Values

- `document_notice_findings_only` — audit scope covers document folder and formal notice reviews only. Use when the primary finding concerns folder completeness or notice defects.
- `leave_source_precedence_only` — audit scope covers leave source precedence determination only. Use when the primary finding is a leave profile mismatch.
- `payroll_assignment_readiness` — audit scope covers payroll assignment and accrual readiness only. Use when the primary finding concerns payroll readiness.

### 5.2 Supporting vs. Excluded Audit Events

- **Supporting audit events**: Include the primary audit event that confirms the business finding. For leave-scope decisions, include the leave-profile-mismatch audit event. For document/notice decisions, include the notice-defect or case-close-blocked audit event. For payroll, include the payroll-ready audit event.
- **Excluded audit events**: When scoping a leave-source decision, exclude adjacent document/notice audit events (such as `folder.tag_missing` or `notice.defect`) that belong to the same case but address a different business concern. Similarly, when scoping a document/notice decision, exclude leave-source audit events.

### 5.3 Cross-Module Escalation

An audit event with `event` = `cross_module.escalation_package` signals that related events from different modules must be reviewed before assigning entity-level issues. The `detail` field lists the related audit event IDs.

## 6. Recruitment Handoff Rules

### 6.1 Payroll Handoff Gate

Payroll handoff from recruitment is created only after a selected candidate has an **accepted offer**. The handoff must be a **submitted** assignment; draft prechecks do not satisfy the gate.

Policy confirmation: Policy `PAY-SRC-001` §4.2.

### 6.2 Draft Payroll in Recruitment

Draft payroll precheck records are not valid for handoff. `draft_payroll_allowed` must be `false`.

### 6.3 Waitlisted Candidates

Waitlisted candidates who have not received a waitlist notice require follow-up. Their exclusion from payroll handoff is because they do not have an accepted offer (`offer_exclusion_reason_for_waitlisted` = `no_accepted_status_or_offer`).

### 6.4 Rejected Candidates

Rejected candidates who have not received a rejection notice require follow-up (send the rejection notice).

## 7. Onboarding Closeout Gates

### 7.1 Approval Closeout Gate

- `approval_sufficient_when_records_clean` — closeout can proceed when both leave and payroll records are clean (submitted/approved, no drafts used).
- `approval_not_sufficient_when_folder_or_notice_defective` — closeout is blocked when folder files are missing or formal notices are defective.

### 7.2 Closeout Blockers

- `missing_required_files` — the case folder lacks one or more required files.
- `missing_required_tags` — the case folder lacks one or more required tags.
- `defective_formal_notice` — the formal notice has quality defects.

## 8. Evidence Source Order

When multiple evidence types are available, prefer this order:

1. `approval_history_folder_notice_audit` — approval history, folder checklist, notice inspection, and audit detail together
2. `folder_notice_audit` — folder checklist, notice inspection, and audit detail
3. `audit_only` — audit detail only

Use the most comprehensive source available for the task.
