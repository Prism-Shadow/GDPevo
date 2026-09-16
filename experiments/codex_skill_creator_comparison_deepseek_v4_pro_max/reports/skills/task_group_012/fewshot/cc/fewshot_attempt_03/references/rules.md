# PeopleOps Business Rules & Normalized Labels

This document catalogues all business rules that must be applied when
verifying records in the PeopleOps Console, plus the complete set of
normalized enum labels that appear in answer templates.

---

## Source Precedence

When multiple records exist for the same employee or entity, always prefer:

1. **Approved/Submitted ledger record** — the most authoritative source.
   - For leave: an assignment with `status: "Approved"` or `status: "Submitted"`
     controls the effective policy and balance days.
   - For salary: an assignment with `status: "Submitted"` controls the base
     salary and effective date.
2. **Employee profile summary** — a fallback. The profile may show stale data;
   override it when a more current ledger record exists.
3. **Case summary** — weakest. Use only when no ledger or profile exists for
   the entity being verified.

This flows from policy `LEAVE-SRC-001` section 2.1: "The latest approved or submitted
leave assignment for the period controls. Draft, voided, and obsolete records
are excluded even when profile summaries conflict."

---

## Record Exclusion Rules

| Record status | Treatment | Reason |
|---|---|---|
| `Draft` | Always exclude from authoritative decisions | Planning artifact, no operational effect |
| `Superseded` | Exclude when a newer Approved/Submitted record exists for the same period | Replaced by a more current assignment |
| `Approved` | Use as authoritative | Fully validated record |
| `Submitted` | Use as authoritative | Submitted and pending approval, but operational |

When a task asks for `excluded_leave_ids` or `excluded_payroll_ids`, list every
ledger ID that was filtered out under these rules for the subject employee.

---

## Folder Readiness

From policy `POL-DOCS-2026` section 5.1: "A folder is not ready unless all required
files and required tags shown in the folder checklist are present."

Procedure:
1. From `/api/documents`, find the document folder for the case.
2. Compare `files` against `required_files` — any entry in `required_files`
   that is not in `files` is a missing file.
3. Compare `tags` against `required_tags` — any entry in `required_tags` that
   is not in `tags` is a missing tag.
4. The `ready` field is a pre-computed boolean; use it, but also report the
   specific gaps.

---

## Formal Notice Quality

Inspect the message (from `/api/messages`) or notification (from
`/api/notifications`) for the case.
The `quality` field is either `valid` or `defective`.

When `defective`, the `defects` array contains one or more of:

| Defect code | Meaning |
|---|---|
| `missing_ack_deadline` | Notice lacks an acknowledgement deadline |
| `missing_appeal_instructions` | Notice lacks appeal instructions |
| `missing_waitlist_status` | Waitlist status not communicated to waitlisted candidate |
| `missing_correct_policy` | Notice references a stale or incorrect policy |

---

## Audit Event Scoping

Audit events have an `event` field. Map it to one of three audit scopes:

| Audit scope enum | Events included |
|---|---|
| `document_notice_findings_only` | `notice.defect`, `folder.tag_missing`, `folder.file_missing` |
| `leave_source_precedence_only` | `leave.profile_mismatch` |
| `payroll_assignment_readiness` | `payroll.ready`, `payroll.draft_excluded` |

`case.close_blocked` events may span multiple domains — read the `detail` field
to determine which scope it belongs to, and only include it in the scope the
task is asking about.

`cross_module.escalation_package` events reference multiple related events by
ID in their `detail` text. Do not treat them as belonging to any single scope;
instead, read the related events and scope each of those individually.

When a task asks for `supporting_audit_event_ids`, include only events whose
`event` field matches the audit scope the task is verifying. When it asks for
`excluded_audit_event_ids`, include events for the same employee/case whose
`event` field belongs to a different scope.

---

## Recruitment Workflow Rules

From policy `PAY-SRC-001` section 4.2: "Recruiting payroll handoff is created only
after a selected candidate has an accepted offer. The handoff must be
submitted; draft prechecks do not satisfy the assignment gate."

For a recruitment opening:

1. The selected candidate is the one with `committee_decision: "Selected"`.
2. Waitlisted candidates have `committee_decision: "Waitlisted"`.
3. Rejected candidates have `committee_decision: "Rejected"`.
4. The offer for the selected candidate comes from `offer_register` — use the
   `offer_id` and `base_salary` from the entry with `status: "accepted"`.
5. `recruitment_cost_total` is the sum of all `amount` values in `cost_ledger`.
   Sum them exactly; do not estimate.
6. `notice_followup_required` lists candidate IDs with unsent notices from
   `notice_packets` (where `status: "not_sent"`).
7. Draft payroll prechecks (from `payroll_precheck_records` with draft status)
   are excluded, and `draft_payroll_allowed` is `false`.
8. Only `accepted` offers trigger payroll handoff.

---

## Leave Source Precedence Verification

1. Get the employee from `/api/employees`. Note the policy name implied by the
   department and leave balance — the profile summary is NOT authoritative.
2. Get leave assignments from `/api/payroll-ledgers` for the employee
   (`record_type: "Leave assignment"`).
3. Select the assignment with `status: "Approved"` or `status: "Submitted"`
   that has the most recent `updated_at`. Exclude Draft and Superseded.
4. Get audit events from `/api/audit` and filter for `event:
   "leave.profile_mismatch"` for the employee.
5. The approved assignment controls. If its policy differs from the employee
   profile, the profile is stale and `profile_policy_ignored` is `true`.
6. `supporting_audit_event_ids` includes the leave-scope audit event.
   `excluded_audit_event_ids` includes any document/notice audit events that
   reference the same employee.

---

## Payroll Assignment & Accrual Readiness

1. Get salary assignments from `/api/payroll-ledgers` for the employee
   (`record_type: "Salary assignment"`).
2. Select the `status: "Submitted"` assignment. Exclude all `status: "Draft"`
   assignments.
3. If the submitted assignment has an `accrual_batch_id` field, accrual is
   ready and `accrual_ready` is `true`.
4. Get audit events from `/api/audit` for the employee with `event:
   "payroll.ready"` to confirm.

---

## Onboarding Closeout

1. Get the employee from `/api/employees`.
2. Get leave assignments for the employee — select the Approved assignment,
   exclude Draft and Superseded.
3. Get salary assignments for the employee — select the Submitted assignment,
   exclude Draft.
4. Map findings to the closeout decision:
   - If all records are clean (submitted salary, approved leave, no stray
     draft records): `approve_onboarding_close`.
   - If there are defects in folder or notice: `block_close_and_reissue_notice`.
   - If records need remediation: `open_records_remediation`.

---

## Normalized Enum Labels Reference

These labels appear across answer templates. Always use them verbatim from the
template rather than from this reference, but the meanings are consistent:

### Source labels

| Label | Meaning |
|---|---|
| `leave_assignment_history` | Leave decision based on payroll-ledger leave assignments |
| `employee_profile_summary` | Leave decision based on employee profile (fallback) |
| `case_summary_only` | Decision based only on case summary (weakest) |
| `approved_assignment_over_profile` | Approved assignment overrides profile |
| `approved_assignment_current_period` | The approved assignment controls for the current period |
| `profile_summary_current_period` | The profile summary controls (no assignment found) |

### Status labels

| Label | Meaning |
|---|---|
| `submitted` | The record is submitted and operational |
| `draft` | The record is a draft; exclude |
| `superseded` | The record has been replaced by a newer one |

### Closeout / gate / control labels

| Label | Meaning |
|---|---|
| `approve_onboarding_close` | Approve the onboarding close |
| `block_close_and_reissue_notice` | Block close; formal notice must be reissued |
| `open_records_remediation` | Open a records remediation workflow |
| `approval_sufficient_when_records_clean` | Approval is sufficient because records are clean |
| `approval_not_sufficient_when_folder_or_notice_defective` | Approval is not sufficient because folder or notice has defects |
| `approve_closeout` | Final: approve the closeout |
| `hold_for_folder_and_notice_defects` | Final: hold because folder/notice has defects |
| `ready_with_monitoring` | Final: ready but monitor |
| `profile_summary_stale` | Audit finding: employee profile is stale |
| `block_close` | Audit finding: block the close |

### Recruitment labels

| Label | Meaning |
|---|---|
| `interview_feedback_and_offer` | Candidate status from interview feedback + offer register |
| `committee_decision_with_offer_confirmation` | Outcome confirmed by committee + offer |
| `recruitment_cost_ledger` | Cost from recruitment cost ledger |
| `notice_packet_inspection` | Notice quality from notice packet inspection |
| `message_notice_inspection` | Notice quality from message inspection |
| `create_payroll_precheck` | Create a payroll precheck for onboarding |
| `create_submitted_assignment_after_acceptance` | Create submitted assignment after offer acceptance |
| `no_payroll_handoff` | No payroll handoff needed |
| `accepted_offer_only` | Handoff gate: accepted offer only |
| `accepted_offer_and_submitted_assignment` | Handoff gate: accepted offer + submitted assignment |
| `submitted_after_acceptance` | Assignment must be submitted after acceptance |
| `submitted_handoff_required_after_acceptance` | Handoff required: submitted after acceptance |
| `no_accepted_status_or_offer` | Exclusion reason: no accepted offer for this candidate |
| `send_waitlist_notice` | Send waitlist notice to waitlisted candidate |
| `reissue_waitlist_notice_not_rejection` | Reissue waitlist notice (not a rejection) |
| `send_rejection_notice` | Send rejection notice |
| `no_action` | No action required |
| `add_required_tag` | Add missing required tag to folder |
| `no_tag_action` | No tag action needed |
| `reissue_defective_notices` | Reissue defective notices |
| `no_notice_action` | No notice action needed |
| `send_new_offer_notice` | Send a new offer notice |

### Audit scope labels

| Label | Meaning |
|---|---|
| `document_notice_findings_only` | Scope: document and notice findings |
| `leave_source_precedence_only` | Scope: leave source precedence |
| `payroll_assignment_readiness` | Scope: payroll assignment readiness |

### Evidence source order labels

| Label | Meaning |
|---|---|
| `approval_history_folder_notice_audit` | Evidence order: approval -> folder -> notice -> audit |
| `folder_notice_audit` | Evidence order: folder -> notice -> audit |
| `audit_only` | Evidence order: audit only |

### Remediation owner labels

| Label | Meaning |
|---|---|
| `Records` | Remediation owned by Records |
| `People Ops Compliance` | Remediation owned by People Ops Compliance |
| `Payroll QA` | Remediation owned by Payroll QA |

### Recruitment-specific labels

| Label | Meaning |
|---|---|
| `accepted` | Offer accepted by candidate |
| `draft` | Offer is draft |
| `withdrawn` | Offer withdrawn |
| `none` | No offer exists |
| `exclude_draft_assignment` | Draft assignment excluded (payroll context) |
| `draft_allowed` | Draft records are allowed (normally false) |
| `exclude_superseded_only` | Only superseded excluded, not drafts |
