# Business Rules Catalog

Every rule below is derived from policy documents in the system and confirmed by
audit evidence across the five training examples. Apply these rules in the order
presented; later rules depend on earlier ones.

---

## Rule 1: Source Precedence (LEAVE-SRC-001 §2.1, PAY-SRC-001 §3.4)

> The latest approved or submitted record for the current period controls.
> Draft, voided, and obsolete records are excluded even when other sources
> (like profile summaries) conflict.

### Application

For any record type (leave assignment, salary assignment):

1. Collect all records for the target entity (employee, case, opening).
2. Filter out records with status `Draft` (and `Superseded` when an approved or
   submitted alternative exists).
3. Among remaining records, select the one with:
   - Highest priority status: `Approved` > `Submitted` > `Superseded` > `Draft`
   - Most recent `updated_at` as tiebreaker within the same status tier
4. The selected record's data controls the answer.

### Evidence chain

When the profile summary (from `GET /api/employees`) conflicts with the ledger
assignment, the ledger wins. This is confirmed by the `LEAVE-SRC-001` policy and
by audit events with event type `leave.profile_mismatch`.

---

## Rule 2: Leave Policy and Balance (LEAVE-SRC-001 §2.1)

1. From payroll-ledgers, filter for `record_type == "Leave assignment"` for the
   target employee.
2. Apply Rule 1 to select the authoritative assignment.
3. The `policy_name` on the selected assignment is the effective leave policy.
4. The `approved_leave_days` on the selected assignment is the annual leave
   days balance. When `approved_leave_days` is 0 (which may happen for salary
   assignments), use `worksheet_leave_days` instead.
5. The `ledger_id` of the selected assignment is the assignment ID.
6. All other leave assignment ledger IDs for this employee are excluded —
   list them in `excluded_leave_ids`.

### Example: Leave assignment source precedence

Ledgers for EMP-001 with record_type "Leave assignment":
- `LA-001-2024-A`: status Superseded, 16 days, "Standard Leave 2024"
- `LA-001-2024-B`: status Approved, 18 days, "Flex Leave 2024"
- `LA-001-2024-DRAFT`: status Draft, 20 days

Selected: `LA-001-2024-B` (Approved, most recent). Excluded: `LA-001-2024-A`,
`LA-001-2024-DRAFT`.

---

## Rule 3: Payroll Assignment (PAY-SRC-001 §3.4)

1. From payroll-ledgers, filter for `record_type == "Salary assignment"` for the
   target employee.
2. Apply Rule 1: prefer `Submitted` over `Draft`. Only draft records are
   excluded unless only drafts exist.
3. The `base_salary` on the selected assignment is the salary.
4. The `ledger_id` of the selected assignment is the payroll/salary assignment
   ID.
5. All draft salary assignment ledger IDs for this employee are excluded —
   list them in `excluded_payroll_ids`.
6. If the selected assignment has an `accrual_batch_id`, cross-reference with
   audit events mentioning that batch to determine accrual readiness.

### Example: Payroll assignment draft exclusion

Ledgers for EMP-001 with record_type "Salary assignment":
- `PAY-001-SUB-01`: status Submitted, 95000, effective 2026-04, accrual_batch_id `ACCR-2026-04-A`
- `PAY-001-DRAFT-02`: status Draft, 102000, effective 2026-05

Selected: `PAY-001-SUB-01`. Excluded: `PAY-001-DRAFT-02`.

---

## Rule 4: Draft Exclusion

Draft records are excluded from all authoritative decisions unless the answer
template explicitly allows them (check `draft_payroll_allowed`).

- When draft records exist and are excluded: `draft_exclusion_rule` is
  `exclude_draft_assignment`.
- When no draft records exist but superseded records are excluded:
  `draft_exclusion_rule` is `exclude_superseded_only`.
- When drafts are permitted: `draft_exclusion_rule` is `draft_allowed`.

---

## Rule 5: Payroll Status

The payroll status label is determined by the status of the selected salary
assignment:

- `Submitted` assignment → `payroll_status: "submitted"`
- Only `Draft` assignments exist → `payroll_status: "draft"`
- Only `Superseded` records → `payroll_status: "superseded"`

---

## Rule 6: Case Folder Readiness (POL-DOCS-2026 §5.1)

> A folder is not ready unless all required files and required tags shown in
> the folder checklist are present.

1. Read the case detail (`GET /api/cases/{case_id}`) to find attachments of
   kind `Checklist`. These describe folder status.
2. Cross-reference with `GET /api/documents`: find the document folder
   associated with the case/employee.
3. Compare `files` against `required_files` and `tags` against `required_tags`.
4. `folder_ready` is `true` only when all required files AND all required tags
   are present.
5. Missing files go in `missing_files` (filenames as strings).
6. `required_tag_present` is `true` only when all required tags are present.

---

## Rule 7: Formal Notice Quality (HR-POL-014 §7.1)

1. Find messages for the target case from `GET /api/messages` (match on
   `case_id`).
2. Read the `quality` field: `valid` or `defective`.
3. If defective, read the `defects` array. Map defect strings to the template's
   `allowed_values` for `notice_defects`:
   - `missing_ack_deadline` → `missing_ack_deadline`
   - `missing_appeal_instructions` → `missing_appeal_instructions`
   - `missing_waitlist_status` → `missing_waitlist_status`
   - `missing_correct_policy` → `missing_correct_policy`
4. `notice_quality` is `valid` or `defective`.
5. `notice_defects` lists the specific defects found.

### Notice evidence source

- When notice packets within the recruitment opening are inspected:
  `notice_evidence_source: "notice_packet_inspection"`.
- When messages from `GET /api/messages` are inspected:
  `notice_evidence_source: "message_notice_inspection"`.
- When only the case summary is used: `notice_evidence_source: "case_summary_only"`.

---

## Rule 8: Approvals and Final Decision

1. Read the case detail's `approvals` array.
2. Find the final approval step (usually `"Final approval"`).
3. The `approver` is the `approval_authority`.
4. The `approval_id` is the `approval_event_id`.
5. The `decision` is `Approved`, `Approved with conditions`, etc.
6. Map the decision to `final_decision`:
   - `Approved` → `approved` (when clean)
   - `Approved with conditions` → `approved_with_conditions`
   - `Rejected` → `rejected`
   - If blocked by defects → `held`

---

## Rule 9: Recruitment Reconciliation

### Candidate classification

1. Find the recruitment opening by `opening_id` in `GET /api/recruitment`.
2. Classify candidates by `committee_decision`:
   - `Selected` → `selected_candidate` (string, single ID)
   - `Waitlisted` → `waitlisted_candidates` (array of IDs)
   - `Rejected` → `rejected_candidates` (array of IDs)

### Offer and salary

1. Look up the selected candidate in `offer_register`.
2. `offer_id` is the offer ID.
3. `offer_base_salary` is the `base_salary` amount.
4. `selected_offer_status` is the offer status: `accepted`, `draft`, `withdrawn`,
   or `none` if no offer exists.

### Cost total

Sum all `amount` values in `cost_ledger`. This is `recruitment_cost_total`.

### Notice follow-up

1. Check `notice_packets` for each non-selected candidate.
2. Any notice with `status: "not_sent"` and a `required_action` means that
   candidate needs notice follow-up. List those candidate IDs in
   `notice_followup_required`.
3. For waitlisted candidates:
   - Notice not sent → `waitlisted_followup_action: "send_waitlist_notice"`
   - Notice defective → `waitlisted_followup_action: "reissue_waitlist_notice_not_rejection"`
   - No action needed → `waitlisted_followup_action: "no_action"`
4. For rejected candidates:
   - Notice not sent → `rejected_followup_action: "send_rejection_notice"`
   - Notice defective → `rejected_followup_action: "reissue_rejection_notice"`
   - No action needed → `rejected_followup_action: "no_action"`

### Payroll handoff (PAY-SRC-001 §4.2)

> Recruiting payroll handoff is created only after a selected candidate has an
> accepted offer. The handoff must be submitted; draft prechecks do not satisfy
> the assignment gate.

1. Only the selected candidate with `offer status == "accepted"` gets payroll
   handoff.
2. `onboarding_handoff` is `create_payroll_precheck` if the selected candidate
   has accepted.
3. `payroll_handoff_gate` is `accepted_offer_only`.
4. `payroll_assignment_status_required` is `submitted_after_acceptance` — the
   assignment must be submitted, not a draft precheck.
5. `draft_payroll_allowed` is `false` — draft precheck records exist but do not
   satisfy the gate.
6. `handoff_control_result` is `submitted_handoff_required_after_acceptance`.

### Source labels for recruitment

- `candidate_status_source`: Use `interview_feedback_and_offer` when committee
  decisions and the offer register are cross-referenced.
- `candidate_outcome_control`: Use `committee_decision_with_offer_confirmation`
  when both the committee decision and the offer acceptance status are verified.
- `cost_source`: Use `recruitment_cost_ledger` when costs are summed from the
  ledger.
- `notice_quality_source`: Use `notice_packet_inspection` when the recruitment
  opening's notice packets are inspected; use `message_notice_inspection` when
  messages from the messages endpoint are inspected.

---

## Rule 10: Audit Evidence

Audit events from `GET /api/audit` are the authoritative QA verdicts.

### How to use audit events

1. Filter audit events by `case_id` and/or `employee_id`.
2. Read the `event` type and `detail` to understand the verdict.
3. Use the audit event ID as `audit_event_id` when the event directly supports
   your finding.
4. Include relevant audit event IDs in `supporting_audit_event_ids`.
5. Exclude irrelevant audit events in `excluded_audit_event_ids`.

### Event type meanings

| Event type | Meaning |
|---|---|
| `leave.profile_mismatch` | Employee profile summary is stale; approved assignment controls |
| `payroll.ready` | Payroll assignment and accrual are clean |
| `payroll.draft_excluded` | Draft assignment must be ignored |
| `notice.defect` | Formal notice has defects |
| `case.close_blocked` | Closeout is blocked by folder/notice issues |
| `folder.tag_missing` | Required tag is missing from folder |
| `cross_module.escalation_package` | Multiple issues across modules |

### Audit scope

Choose the audit scope based on what you are checking:

- Leave-only checks → `audit_scope: "leave_source_precedence_only"`
  - Include leave-related audit event IDs in `supporting_audit_event_ids`
  - Exclude document/notice audit event IDs in `excluded_audit_event_ids`
- Folder + notice checks → `audit_scope: "document_notice_findings_only"`
- Payroll checks → `audit_scope: "payroll_assignment_readiness"`

---

## Rule 11: Closeout Decision Logic

Combine all findings to determine the closeout action and final control result.

### Decision tree

1. Are there **folder defects** (missing files or tags)?
   - Yes → `closeout_action: "open_records_remediation"` or
     `"block_close_and_reissue_notice"` (depending on whether notices are also
     defective).
2. Are there **notice defects**?
   - Yes → `closeout_action: "block_close_and_reissue_notice"`
   - `approval_closeout_gate: "approval_not_sufficient_when_folder_or_notice_defective"`
   - `final_control_result: "hold_for_folder_and_notice_defects"`
3. Are **all records clean**?
   - Yes → `closeout_action: "approve_onboarding_close"`
   - `approval_closeout_gate: "approval_sufficient_when_records_clean"`
   - `final_control_result: "approve_closeout"`
4. Is the **profile summary stale** but no other defects?
   - `next_action: "update_employee_summary"`
   - `audit_result: "profile_summary_stale"`
5. Is the **payroll assignment ready with monitoring**?
   - `control_result: "ready_with_monitoring"`
   - `accrual_ready: true`

### Cross-module escalation

When multiple defects span leave, payroll, documents, and notices, the
escalation action is `open_records_remediation`, with the remediation owner
determined by the primary problem area:
- Document/tag problems → `records_remediation_owner: "Records"`
- Notice defects → `records_remediation_owner: "People Ops Compliance"`
- Payroll issues → `records_remediation_owner: "Payroll QA"`

---

## Rule 12: Evidence Source Order

The evidence source order describes the chain of evidence reviewed:

- Full chain (approval → folder → notice → audit):
  `evidence_source_order: "approval_history_folder_notice_audit"`
- Shorter chain (folder → notice → audit):
  `evidence_source_order: "folder_notice_audit"`
- Audit only: `evidence_source_order: "audit_only"`

---

## Rule 13: Profile vs Assignment Precedence

When an approved leave assignment exists for the current period and the employee
profile summary shows different data:

1. The approved assignment controls (per `LEAVE-SRC-001` §2.1).
2. `precedence_source: "approved_assignment_over_profile"` (template specific)
   or `leave_precedence_source: "approved_assignment_current_period"`.
3. `profile_policy_ignored: true` — the profile value should be ignored.
4. `audit_result: "profile_summary_stale"` — the profile is out of date.
5. `next_action: "update_employee_summary"` — the profile needs updating.

### Example: Profile vs assignment precedence

Profile says `leave_balance_days: 16`. The approved leave assignment
`LA-001-APP-01` confirms 16 days under "Standard Leave 2026". An
audit event with event type `leave.profile_mismatch` confirms the profile is
stale. The assignment overrides the profile.

---

## Rule 14: Field Consistency Checks

Before writing the final answer, verify these consistency rules:

1. If `closeout_action` is `block_close_and_reissue_notice`:
   - `approval_closeout_gate` must be
     `approval_not_sufficient_when_folder_or_notice_defective`
   - `final_control_result` must be `hold_for_folder_and_notice_defects`

2. If `payroll_status` is `submitted` and draft records exist:
   - `draft_exclusion_rule` must be `exclude_draft_assignment`

3. If `notice_quality` is `defective`:
   - `notice_defects` must be non-empty
   - At least one `closeout_blockers` entry must be `defective_formal_notice`

4. If `folder_ready` is `false`:
   - `missing_files` must be non-empty
   - At least one `closeout_blockers` entry must be `missing_required_files`

5. Excluded arrays must contain all excluded IDs; never leave them empty when
   there are records to exclude.

6. All enum values must be exact matches to the `allowed_values` in the answer
   template. Even case differences will cause a mismatch.
