# Business-Judgment Rules — Reference

These are the reusable decision rules. They are derived from the policy documents
in the environment (read the relevant `/api/policies/<id>` to confirm wording for a
given task) and apply across the whole task family. No concrete entity values here —
fetch the live records for the entity you are working and apply the rule.

## 1. Source precedence (the central idea)

The portal stores several records for the same fact (leave, payroll). They disagree
on purpose. You must pick the **authoritative** one and list the rest as excluded.

Precedence, strongest to weakest:
1. **Approved / Submitted** record of the correct record type, for the relevant
   period → authoritative.
2. **Employee profile summary** (the `/api/employees` row) → a convenience summary
   that may be stale; it loses to an approved/submitted assignment.
3. **Case summary** text → weakest; never authoritative on its own.

Excluded automatically: `Draft`, `Superseded`, voided, or obsolete records, even
when a profile summary agrees with them. When the prompt asks for excluded IDs,
return every losing record of that fact (drafts AND superseded), as a set.

Pick the *current/latest* approved-or-submitted record for the period in question.
If both an Approved and a Submitted record exist for the same fact and period, they
are typically consistent; prefer the one the audit/policy text names as controlling.

## 2. Leave authoritative record

The controlling leave record is the `record_type: "Leave assignment"` row that is
`Approved` (or `Submitted`) for the period. Take `policy_name` →
`effective_leave_policy`, and `approved_leave_days` (or the assignment's day count)
→ `annual_days` / `balance_days`. The `ledger_id` of that row → `assignment_id`.

Do NOT use `HRMS leave ledger` or `People Ops adjustment` worksheet rows as the
controlling assignment — they are accrual/adjustment detail, not the entitlement
source. Exclude Draft/Superseded leave assignments.

A profile summary can match the authoritative *balance* yet still carry a *stale
policy name*; in that case the assignment still controls and the profile policy is
ignored (`profile_policy_ignored: true`).

## 3. Payroll authoritative record

The controlling salary record is the `record_type: "Salary assignment"` with
`status: "Submitted"` for the relevant period. Take `base_salary` and derive
`effective_date` from its `period` (a `2026-04` period → `2026-04-01`). Exclude the
`Draft` salary assignment (`exclude_draft_assignment`). A draft is never allowed to
control (`draft_payroll_allowed: false`).

## 4. Folder readiness (set comparison)

A folder is ready only if **all** required files and **all** required tags are
present (the "required evidence" rule in the lifecycle-folder policy document —
fetch the policy the case references to confirm wording).
- `missing_files` = `required_files` − `files` (set difference; return as a set).
- `required_tag_present` = `required_tags ⊆ tags`.
- If a required tag is missing → `add_required_tag`; otherwise `no_tag_action`.
- `folder_ready` = (no missing files) AND (all required tags present). Cross-check
  the folder-checklist attachment / `folder.tag_missing` audit detail; they restate
  the same gaps.

## 5. Notice-defect detection + normalized defect vocabulary

Inspect the **notice packet** (the message record for the case) — its `quality` and
`defects[]` fields are authoritative. Prefer `notice_packet_inspection` /
`message_notice_inspection` as the source; never decide notice quality from the case
summary alone. `quality: "defective"` with one or more codes → `notice_quality:
defective`, copy the codes into `notice_defects` (set).

Normalized defect codes (the only allowed values — part of the output contract):
- `missing_ack_deadline`
- `missing_appeal_instructions`
- `missing_waitlist_status`
- `missing_correct_policy`

A defective formal notice must be reissued before close
(`reissue_defective_notices`); a valid notice → `no_notice_action`.

## 6. Audit event selection (controlling vs off-scope)

Each case can carry several audit events covering different scopes. Pick the event
whose `event`/`detail` matches the question's scope and use it as the controlling /
supporting audit; read its result label verbatim from `detail`.

- Leave question → `leave.*` event; scope `leave_source_precedence_only`.
- Payroll question → `payroll.*` event; scope `payroll_assignment_readiness`.
- Document/notice question → `notice.*` / `folder.*` event; scope
  `document_notice_findings_only`.

Adjacent events of a *different* scope on the same case are listed in
`excluded_audit_event_ids` (e.g. a `folder.tag_missing` event is excluded from a
leave-precedence decision). If the controlling event is the only one in scope,
`supporting_audit_event_ids` = [that event] and `excluded_audit_event_ids` may be
empty.

The audit `detail` often spells out the result label you must emit (e.g.
"QA result: <label>"). Use that label, mapped to the template's enum.

## 7. Approval-vs-closeout gate

An approval decision does NOT by itself permit closeout. The gate:
- `approval_sufficient_when_records_clean` — approval closes the case only when the
  folder is ready AND the notice is valid AND records are clean.
- `approval_not_sufficient_when_folder_or_notice_defective` — if the folder is
  missing files/tags OR the notice is defective, approval is not enough; hold.

Consequences:
- Clean records + approval → `approve_closeout` / `approve_onboarding_close`.
- Folder and/or notice defective → `hold_for_folder_and_notice_defects` and
  `block_close_and_reissue_notice`; populate `closeout_blockers` from
  {`missing_required_files`, `missing_required_tags`, `defective_formal_notice`}.
- Records-level gaps that need a team to fix → `open_records_remediation`; the
  `records_remediation_owner` is read from who owns the folder/records evidence
  (the checklist's uploader / the document policy owner), mapped to the template
  enum (e.g. `Records`, `People Ops Compliance`, `Payroll QA`).

An approval `decision: "Approved"` with a conditions note → `approved_with_conditions`;
`approval_authority` = the approver role; `approval_event_id` = the `approval_id`.

## 8. Recruitment outcomes, costs, handoff

- `selected_candidate` = candidate with `committee_decision: "Selected"` **and** an
  accepted offer in `offer_register`. Its `offer_id` and `base_salary` feed
  `offer_id` / `offer_base_salary`; `selected_offer_status` = that offer's status.
- `waitlisted_candidates` / `rejected_candidates` = grouped by `committee_decision`
  (lists of candidate IDs only).
- Outcome control = `committee_decision_with_offer_confirmation`; status source =
  `interview_feedback_and_offer` (not message/case-summary).
- `recruitment_cost_total` = sum of **all** `cost_ledger[].amount`; source =
  `recruitment_cost_ledger`.
- `notice_followup_required` = candidates whose `notice_packets` entry is `not_sent`
  (lists of candidate IDs). Map each to its `required_action`
  (`send_waitlist_notice`, `send_rejection_notice`). A waitlisted candidate gets a
  waitlist notice, not a rejection.
- Handoff: an accepted offer triggers a payroll handoff. If there is no payroll
  precheck/submitted assignment yet, the action is `create_payroll_precheck`; the
  gate is `accepted_offer_only`; required assignment status is
  `submitted_after_acceptance`; `draft_payroll_allowed: false`;
  `handoff_control_result: submitted_handoff_required_after_acceptance`.
- Waitlisted candidates are excluded from selection because they have
  `no_accepted_status_or_offer`.

## 9. Escalation owner / SLA from an audit package (procedure only)

When a task asks for an escalation owner or an SLA, fetch the named audit package /
audit event and read the owner and SLA **verbatim from its `detail` text** (or the
linked policy). Do not invent numbers and do not carry a value over from a different
task — every task's owner/SLA is specific to its own named package. Map any free-text
owner onto the template's allowed owner enum if one is provided.
