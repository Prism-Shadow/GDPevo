# PeopleOps Console Business Rules

This reference distills the policy documents and data patterns into actionable
rules. Apply each rule by reading the relevant API endpoint and comparing the
returned data against the rule's criteria.

---

## Table of Contents

- [Leave Source Precedence](#leave-source-precedence)
- [Payroll Assignment Source](#payroll-assignment-source)
- [Document Folder Readiness](#document-folder-readiness)
- [Notice Quality Inspection](#notice-quality-inspection)
- [Recruitment Reconciliation](#recruitment-reconciliation)
- [Audit Scoping](#audit-scoping)
- [Closeout and Control Gates](#closeout-and-control-gates)

---

## Leave Source Precedence

**Policy:** LEAVE-SRC-001, section 2.1

The latest approved or submitted leave assignment for the current period
controls. Draft, voided, superseded, and obsolete records are excluded even
when the employee profile summary shows different values.

**How to apply:**

1. Pull `/api/payroll-ledgers` and filter for `record_type: "Leave assignment"`
   and the target `employee_id`.
2. Sort the matching records by `updated_at` descending within the current
   period.
3. Find the first record whose `status` is `"Approved"` (or `"Submitted"` if
   no approved record exists). This is the authoritative assignment.
4. Ignore any record with `status: "Draft"` or `status: "Superseded"`.
5. Compare against the employee record from `/api/employees`. If the profile
   `leave_balance_days` differs from the authoritative assignment's
   `approved_leave_days`, the profile summary is stale and the assignment
   controls.

**Decision labels:**
- `leave_source`: `"leave_assignment_history"` when the ledger supplies the
  answer; `"employee_profile_summary"` when only the profile is available;
  `"case_summary_only"` when neither source is authoritative.
- `leave_precedence_source`: `"approved_assignment_current_period"` when an
  approved assignment controls; `"profile_summary_current_period"` when the
  profile is authoritative; `"case_summary_only"` otherwise.
- `precedence_source`: `"approved_assignment_over_profile"` when the approved
  assignment overrides a stale profile.

**Exclusion rule:** Every ledger record that is not the authoritative one must
be listed as excluded, including draft and superseded records for the same
employee and period.

---

## Payroll Assignment Source

**Policy:** PAY-SRC-001, sections 3.4 and 4.2

Use the current submitted salary assignment. Draft planning assignments do not
affect payroll readiness or accrual checks. A recruiting payroll handoff is
created only after a selected candidate has an accepted offer; the handoff must
be submitted, draft prechecks do not satisfy the assignment gate.

**How to apply:**

1. Pull `/api/payroll-ledgers` and filter for `record_type: "Salary
   assignment"` and the target `employee_id`.
2. Find the record with `status: "Submitted"`. This is the authoritative
   payroll assignment. Its `base_salary` and `ledger_id` are the answer.
3. Any record with `status: "Draft"` is excluded. Do not use draft salary
   values.
4. For accrual readiness, check whether the submitted assignment has an
   `accrual_batch_id` field — if present and the audit event confirms
   readiness, accrual is ready.

**Decision labels:**
- `payroll_status`: `"submitted"` when the authoritative record is submitted.
- `payroll_source_status`: `"submitted"` when the source is a submitted
  assignment.
- `draft_exclusion_rule`: `"exclude_draft_assignment"` when draft records must
  be excluded.
- `payroll_handoff_gate`: `"accepted_offer_only"` for recruitment payroll
  handoff after acceptance.
- `payroll_assignment_status_required`: `"submitted_after_acceptance"` when a
  submitted assignment is needed after offer acceptance.

---

## Document Folder Readiness

**Policy:** POL-DOCS-2026, section 5.1

A folder is not ready unless all required files and required tags shown in the
folder checklist are present.

**How to apply:**

1. Pull `/api/documents` and find the document record matching the case or
   employee referenced in the prompt.
2. Compare the `files` array against `required_files`. Every entry in
   `required_files` must appear in `files` for the folder to be `ready: true`.
3. Compare the `tags` array against `required_tags`. Every entry in
   `required_tags` must appear in `tags`.
4. The `ready` field on the document is pre-computed but verify it yourself —
   the API sets it `true` only when both conditions are satisfied.

**Decision labels:**
- `folder_ready`: `true` when all required files and tags are present.
- `missing_files`: list any entries in `required_files` that are absent from
  `files`.
- `required_tag_present`: `true` when all required tags are present.
- `folder_required_tag_action`: `"no_tag_action"` when tags are correct;
  `"add_required_tag"` when a required tag is missing.

---

## Notice Quality Inspection

Formal notices (decisions, waitlist notices, rejection notices) appear in
`/api/messages` and `/api/notifications`. Each notice has a `quality` field
(`"valid"` or `"defective"`) and a `defects` array listing specific issues.

**Known defect labels:**
- `missing_ack_deadline` — no acknowledgement deadline in the notice
- `missing_appeal_instructions` — no appeal process described
- `missing_waitlist_status` — waitlist status omitted from waitlist notice
- `missing_correct_policy` — notice references wrong or stale policy

**How to apply:**

1. Pull `/api/messages` and `/api/notifications`. Find notices matching the
   case or candidate referenced in the prompt.
2. If `quality` is `"defective"`, collect the `defects` array entries.
3. A defective notice blocks closeout and requires reissue.

**Decision labels:**
- `notice_quality`: `"valid"` or `"defective"` from the notice record.
- `notice_defects`: the `defects` array entries.
- `notice_evidence_source`: `"notice_packet_inspection"` when inspecting the
  notice record directly; `"message_notice_inspection"` when using message
  data; `"case_summary_only"` when neither source is available.
- `notice_remediation_action`: `"reissue_defective_notices"` when a defective
  notice must be reissued; `"no_notice_action"` when all notices are valid.

---

## Recruitment Reconciliation

Recruitment openings in `/api/recruitment` contain candidates, offers, cost
ledgers, and notice packets. Reconcile each component against the business
rules.

**Candidate outcomes:**

1. Read the `candidates` array. Each candidate has a `committee_decision`:
   `"Selected"`, `"Waitlisted"`, or `"Rejected"`.
2. The `selected_candidate` is the one with `committee_decision: "Selected"`.
3. `waitlisted_candidates` and `rejected_candidates` are arrays of candidate
   IDs with those decisions.

**Offer verification:**

1. Read the `offer_register`. Find the offer for the selected candidate.
2. The `offer_id` and `base_salary` come from the matching offer record.
3. `selected_offer_status` is the `status` of that offer (`"accepted"`,
   `"draft"`, `"withdrawn"`, or `"none"` if no offer exists).

**Cost calculation:**

1. Sum all `amount` values in the `cost_ledger` array. This is
   `recruitment_cost_total`.

**Notice follow-up:**

1. Read the `notice_packets` array. Each packet has `candidate_id`,
   `notice_type` (`"waitlist"` or `"rejection"`), `required_action`, and
   `status`.
2. Any candidate whose notice packet `status` is `"not_sent"` requires
   follow-up.
3. `notice_followup_required` lists the candidate IDs needing notice action.

**Decision labels:**
- `candidate_status_source`: `"interview_feedback_and_offer"` when the
  recruitment workspace is used; `"case_summary_only"` otherwise.
- `candidate_outcome_control`: `"committee_decision_with_offer_confirmation"`
  when both committee decision and offer register are checked.
- `selected_offer_status`: `"accepted"`, `"draft"`, `"withdrawn"`, or
  `"none"`.
- `cost_source`: `"recruitment_cost_ledger"` when costs come from the ledger.
- `waitlisted_followup_action`: `"send_waitlist_notice"` when a waitlisted
  candidate needs a notice; `"no_action"` otherwise.
- `rejected_followup_action`: `"send_rejection_notice"` when a rejected
  candidate needs a notice; `"no_action"` otherwise.
- `onboarding_handoff`: `"create_payroll_precheck"` when payroll precheck
  should be created; `"create_submitted_assignment_after_acceptance"` when
  a submitted assignment is needed post-acceptance; `"no_payroll_handoff"`
  otherwise.
- `handoff_control_result`: `"submitted_handoff_required_after_acceptance"`
  when a submitted handoff is needed after acceptance;
  `"submitted_handoff_required"` when a submitted handoff is needed;
  `"no_handoff_required"` otherwise.
- `draft_payroll_allowed`: `false` — draft payroll is never allowed for
  handoff.
- `offer_exclusion_reason_for_waitlisted`: `"no_accepted_status_or_offer"` when
  waitlisted candidates lack an accepted offer.

---

## Audit Scoping

Audit events appear in two places: embedded within case details (via
`/api/cases/{case_id}`) and in the top-level `/api/audit` collection. The
top-level collection may contain cross-cutting events not attached to any
specific case.

**How to apply:**

1. Pull `/api/audit` for the full event list.
2. For a leave-precedence task, scope to audit events with `event:
   "leave.profile_mismatch"` relevant to the employee. Exclude `event:
   "folder.tag_missing"` and other document/notice events from the leave
   scope.
3. For a payroll-readiness task, scope to events with `event:
   "payroll.ready"` and `event: "payroll.draft_excluded"` relevant to the
   employee.
4. For a case-review task, scope to events matching the case ID, covering
   document and notice findings.
5. When a `cross_module.escalation_package` event exists, review its `detail`
   for related audit IDs but do not assign its findings to a single entity
   without checking those related events independently.

**Decision labels:**
- `audit_scope`: `"leave_source_precedence_only"` for leave tasks;
  `"document_notice_findings_only"` for case-review tasks;
  `"payroll_assignment_readiness"` for payroll tasks.
- `supporting_audit_event_ids`: audit IDs that directly support the decision.
- `excluded_audit_event_ids`: audit IDs that are adjacent (document, notice,
  or cross-module) and must be excluded from the primary scope.
- `evidence_source_order`: `"approval_history_folder_notice_audit"` when the
  full chain is used; `"folder_notice_audit"` when skipping approvals;
  `"audit_only"` when only audit events are available.

---

## Closeout and Control Gates

**Final decisions and actions:**

Every task culminates in a control decision that gates further action. The
decision flows from the evidence gathered in the preceding steps.

- `approve_onboarding_close`: Everything is clean; approve the closeout.
- `block_close_and_reissue_notice`: Notice is defective; block close and
  require reissue.
- `open_records_remediation`: Folder or records have defects that need
  remediation by a specific owner.

**Gate labels:**
- `approval_closeout_gate`: `"approval_sufficient_when_records_clean"` when
  no blockers exist; `"approval_not_sufficient_when_folder_or_notice_defective"`
  when blockers exist.
- `closeout_blockers`: list from `"missing_required_files"`,
  `"missing_required_tags"`, `"defective_formal_notice"` — include each that
  applies.
- `final_control_result`: `"approve_closeout"` when clean;
  `"hold_for_folder_and_notice_defects"` when blocked;
  `"ready_with_monitoring"` when ready but requires monitoring.
- `records_remediation_owner`: `"Records"` for folder/file issues; `"People
  Ops Compliance"` for compliance issues; `"Payroll QA"` for payroll issues.
- `escalation_action`: `"open_records_remediation"` for record defects;
  `"block_close_and_reissue_notice"` for notice defects; `"no_action"`
  otherwise.
- `next_action`: the remediation or approval action to take next.

---

## Summary Decision Tables

### When to approve, block, or remediate

| Condition | Action |
|---|---|
| All records clean, notice valid, folder ready | approve |
| Notice defective or folder not ready | block and reissue |
| Records stale or incomplete but not blocking | remediate with monitoring |

### Which records to exclude

| Record status | Treatment |
|---|---|
| Draft (leave or payroll) | Exclude |
| Superseded (leave) | Exclude |
| Approved (leave) | Use |
| Submitted (payroll) | Use |
