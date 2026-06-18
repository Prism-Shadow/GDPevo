---
name: peopleops-console-review
description: >-
  Answer PeopleOps Console HR-lifecycle review/control tasks against the local
  JSON API: onboarding closeout, leave source-precedence, payroll/accrual
  readiness, document-folder readiness and formal-notice quality, recruitment
  reconciliation, and audit-scope decisions. Use this whenever a task points at
  an "HR portal / PeopleOps Console" and asks you to determine the authoritative
  record, exclude draft/superseded/losing records, check folder readiness, judge
  notice quality/defects, pick the controlling/supporting audit event, gate
  approval vs closeout, or sum recruitment cost — and to emit JSON matching a
  given answer_template.json with normalized business-label enums. Trigger it
  even when the prompt only names an employee/case/opening ID and asks for a
  "control result", "next action", "precedence", "readiness", or "reconciliation".
---

# PeopleOps Console Review

You are an HR operations control reviewer working over a read-only JSON API. A task
hands you ONE focal entity — an employee, a case, or a recruitment opening — plus an
`answer_template.json`. Your job is to gather the authoritative evidence, apply
fixed source-precedence and gating rules, and return JSON that exactly matches the
template using its normalized enum labels.

The hard part is never finding data; it is **judgment**: which record is authoritative,
which records are excluded, what makes a folder or notice defective, which audit event
controls, and whether approval is enough to close. The rules below are stable across
tasks; the entity IDs and values are not. Learn the rules, look up the specifics live.

For the exact endpoint shapes, the raw-field-to-enum mapping, and the full enum
vocabulary, read `references/api_and_enums.md`. Read it early — it is the lookup table
this file refers to.

## Step 0 — Orient

1. `GET /health` to confirm the service is up (base URL is in `environment_access.md`).
2. Read the task's `answer_template.json`. It is the contract: it tells you exactly
   which fields to emit, their types, and for each enum field the `allowed_values`.
   Do not invent fields, omit fields, or use a label outside a field's `allowed_values`.
3. Identify the focal entity and its task family from the prompt and the template's
   field names (leave fields -> leave precedence; payroll/accrual -> payroll readiness;
   folder/notice/approval -> document-notice closeout; candidates/offer/cost ->
   recruitment reconciliation). Templates often mix families; answer every field.

## Step 1 — Gather (filtered lookups only)

Query ONLY records tied to the focal entity, always with a precise filter. Never list
a collection bare to discover unrelated entities.

- Employee tasks: `GET /api/employees?q=<EMP-ID>` for context, then
  `GET /api/payroll-ledgers?q=<EMP-ID>` — this single store holds both the leave
  assignments and the salary assignments. If the task references a case, also
  `GET /api/cases/<CASE-ID>` for its embedded `audit_events`, approvals, attachments.
- Case tasks: `GET /api/cases/<CASE-ID>`, then `GET /api/documents?q=<CASE-ID>`,
  `GET /api/messages?q=<CASE-ID>` (notices), and `GET /api/audit?case_id=<CASE-ID>`.
- Recruitment tasks: `GET /api/recruitment?q=<REQ-ID>` returns the whole packet
  (candidates, offers, cost ledger, notice packets, prechecks); add the linked case
  if the template asks for case-level fields.
- Read the governing policy with `GET /api/policies?q=<POLICY-ID>` (policy_refs on the
  case) when you need the rule in its own words, especially for owner/SLA/gate wording.

## Step 2 — Apply the rules

### A. Source precedence (leave and payroll)
Submitted/approved records override draft, stale, superseded, and voided ones.

- **Leave entitlement** comes from the controlling **leave *assignment*** record
  (`record_type == "Leave assignment"`) that is `Approved` or `Submitted` for the
  current period. Its `policy_name` is the effective policy and its day count
  (`approved_leave_days`) is the entitlement/balance. Raw `HRMS leave ledger` and
  `People Ops adjustment` rows are movement/adjustment data, NOT the controlling
  assignment — never report their id or their day count as the entitlement.
- **An approved leave assignment overrides a stale employee profile summary** even
  when the profile's leave_balance differs. When that happens, the profile policy is
  ignored (`profile_policy_ignored: true`), precedence is `approved_assignment_over_profile`
  / `approved_assignment_current_period`, and the leave source is `leave_assignment_history`.
- **Payroll/salary** comes from the current **Submitted** salary assignment; its
  `base_salary` and effective date (the assignment's `updated_at` date, consistent
  with its `period`) are authoritative. Draft planning assignments do not affect
  payroll readiness or accrual checks.
- **Exclusions are explicit outputs.** Put every losing record's id in the matching
  `excluded_*` list: superseded and draft leave records in `excluded_leave_ids`, the
  draft salary record in `excluded_payroll_ids` / `excluded_assignment_id`. The
  selected record never appears in an exclusion list.

### B. Document-folder readiness (set comparison)
Compute readiness yourself from the folder; do not just echo the `ready` flag.
- `missing_files = required_files \ files` (required members not present). `folder_ready`
  is true only when that set is empty. Report the missing members exactly as named.
- `required_tag_present` is true iff every member of `required_tags` is in `tags`.
  If a required tag is missing, `folder_required_tag_action = add_required_tag` and
  add `missing_required_tags` to `closeout_blockers`; otherwise `no_tag_action`.
- Any missing required file -> add `missing_required_files` to `closeout_blockers`.

### C. Formal-notice quality and defects
Inspect the actual notice packet / message, not the case summary (notice evidence
source = `notice_packet_inspection` or `message_notice_inspection`).
- The notice's own `quality` field gives `valid` / `defective`; its `defects[]` array
  already holds normalized defect codes — copy them verbatim. Allowed defect codes:
  `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`,
  `missing_correct_policy`.
- A defective notice -> add `defective_formal_notice` to `closeout_blockers`,
  `notice_remediation_action = reissue_defective_notices`.

### D. Audit event selection (controlling/supporting, with scope exclusion)
A case may carry several audit events; classify each by its `event` namespace and keep
only those in the task's scope:
- `leave.*` -> `leave_source_precedence_only`
- `payroll.*` -> `payroll_assignment_readiness`
- `folder.*` / `notice.*` -> `document_notice_findings_only`

The in-scope event is the controlling `audit_event_id` and goes in
`supporting_audit_event_ids`; out-of-scope events (e.g. a `folder.*` event during a
leave-precedence task) go in `excluded_audit_event_ids`. When the controlling audit
`detail` contains a `QA result: <label>` clause, that label is the normalized
`audit_result` / `control_result` (e.g. `profile_summary_stale`, `ready_with_monitoring`,
`block_close`) — report it verbatim, and trust the record id named alongside it.

### E. Approval vs closeout gate
Approval authority alone does NOT permit close when records are defective.
- If the folder is incomplete, a required tag is missing, or the notice is defective:
  gate = `approval_not_sufficient_when_folder_or_notice_defective`, final result =
  `hold_for_folder_and_notice_defects`, next/closeout action =
  `block_close_and_reissue_notice` for notice defects and/or `open_records_remediation`
  for folder/file/tag defects (escalation_action). Populate `closeout_blockers` with
  every blocker found.
- If all records are clean (authoritative leave + submitted payroll, folder ready,
  tag present, notice valid): gate = `approval_sufficient_when_records_clean`, result =
  `approve_closeout`, action = `approve_onboarding_close`.
- A payroll-readiness audit that says ready-with-monitoring -> `accrual_ready: true`,
  `control_result = ready_with_monitoring` (proceed under monitoring, not a hard close).
- `evidence_source_order` for closeout reviews is `approval_history_folder_notice_audit`
  (check the approval, then the folder, then the notice, then the audit).

### F. Recruitment reconciliation
- Candidate outcomes come from each candidate's `committee_decision`
  (`Selected`/`Waitlisted`/`Rejected`), confirmed by the offer register — source =
  `interview_feedback_and_offer`, control = `committee_decision_with_offer_confirmation`.
  Arrays contain candidate IDs only.
- `selected_candidate` is the Selected one; its accepted offer gives `offer_id`,
  `offer_base_salary`, and `selected_offer_status = accepted`. Waitlisted/rejected
  candidates have no live offer -> `offer_exclusion_reason_for_waitlisted =
  no_accepted_status_or_offer`.
- `recruitment_cost_total` = sum of EVERY `amount` in `cost_ledger`; cost_source =
  `recruitment_cost_ledger`.
- `notice_followup_required` = candidate IDs whose notice packet `status == "not_sent"`;
  the packet's `required_action` gives the per-candidate follow-up label
  (`send_waitlist_notice` for waitlisted, `send_rejection_notice` for rejected).
- Payroll handoff is created only AFTER the selected candidate has an accepted offer,
  and it must be a Submitted assignment (draft prechecks do not satisfy the gate):
  `payroll_handoff_gate = accepted_offer_only`,
  `payroll_assignment_status_required = submitted_after_acceptance`,
  `draft_payroll_allowed = false`. With an accepted offer and no precheck yet,
  `onboarding_handoff = create_payroll_precheck` and
  `handoff_control_result = submitted_handoff_required_after_acceptance`.

### G. Escalation owner / SLA (procedure, never assume)
When a field asks who owns remediation or what the SLA is, read it from the case/audit
package or the governing policy verbatim (e.g. the actor/owner on the controlling
audit event, the folder-checklist uploader, or the policy owner), then map to the
template's `allowed_values` owner labels. Document/folder remediation belongs to the
records function; never guess an owner or an SLA number.

## Step 3 — Emit
- Output exactly one JSON object with exactly the template's fields. No markdown, no
  commentary, no extra keys.
- Every enum/source/gate/scope/status/result field uses a label from THAT field's
  `allowed_values` — normalized labels, never free text. The same option pool can
  appear in different order across fields; pick by rule, not by position.
- List fields are sets: candidate/record IDs only, no duplicates, no narration; an
  empty set is `[]`, not omitted.
- Mirror the template's types: integer day counts stay integers, salaries are numbers,
  booleans are booleans.

## Common pitfalls (exclusion checklist)
- Picking a Draft or Superseded record as authoritative, or forgetting to list the
  losers in the `excluded_*` field.
- Using an HRMS-ledger or adjustment row's id/days as the leave entitlement instead of
  the Leave assignment record.
- Trusting the folder `ready` flag instead of computing `required_files \ files`.
- Reading notice quality/defects from the case summary instead of the notice packet.
- Including an out-of-scope audit event (folder/notice event in a leave task, etc.) in
  the supporting list instead of the excluded list.
- Treating approval authority as sufficient to close while a folder/file/tag/notice
  defect is open.
- Missing a cost-ledger line in the sum, or putting names instead of candidate IDs in
  the outcome arrays.
- Inventing an owner, SLA, or any concrete value the records do not state.
