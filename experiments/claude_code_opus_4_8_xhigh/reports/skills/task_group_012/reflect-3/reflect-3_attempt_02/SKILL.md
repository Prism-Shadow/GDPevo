---
name: peopleops-console-lifecycle-control
description: Resolve PeopleOps Console HR lifecycle/leave/payroll/policy-case/recruitment/document/audit tasks by applying source-precedence, folder-readiness, notice-defect, and audit-scope rules and emitting the template's normalized business labels.
---

# PeopleOps Console — Lifecycle Control Skill

You answer People Ops / ERP-HR verification tasks by reading a remote HTTP API,
applying a fixed set of business rules, and returning ONE JSON object whose keys
and enum values exactly match the task's `answer_template.json`.

## 0. Operating contract (read first)

- The answer template is the spec. Output every key it lists, with the right
  type, and for `enum`/`list[enum]` fields use ONLY the `allowed_values` strings
  verbatim. Never invent labels or write free-text explanations into label fields.
- Each field is scored independently (partial credit). So: (1) lock in every
  field that the data states literally before reasoning about interpretive ones,
  and (2) a wrong enum only costs that field — but vague/over-broad list fields
  bleed points, so keep lists tight and justified.
- IDs are copied verbatim from the API (assignment ids, offer ids, audit ids,
  approval ids, candidate ids, batch ids). Never paraphrase or reformat them.
- Dates are full calendar dates `YYYY-MM-DD` (take the date part of the record's
  effective/updated timestamp). Do NOT substitute the monthly `period` string
  (`YYYY-MM`) for an `effective_date`.

## 1. Remote API workflow

Base service exposes read-only JSON endpoints (no auth; login text in prompts is
flavor). Typical calls:

- `GET /api/summary` and `/api/manifest` — orient: counts, departments, modules.
- `GET /api/employees?q=<id|name>` — profile summary (department, balance, status).
- `GET /api/payroll-ledgers?q=<emp_id>` — leave assignments AND salary
  assignments AND accrual/adjustment rows live here together; filter mentally by
  `record_type` and `status`.
- `GET /api/cases` (summaries) then `GET /api/cases/{case_id}` for the FULL
  record: `approvals`, `attachments`, `comments`, `audit_events`, `policy_refs`.
- `GET /api/policies` / `/api/policies/{id}` — the authoritative precedence rules.
- `GET /api/documents?q=` — folder `required_files`/`files`, `required_tags`/`tags`, `ready`.
- `GET /api/messages?q=` — formal-notice messages with `quality` and `defects`.
- `GET /api/recruitment?q=` — openings, candidates, `offer_register`, `cost_ledger`,
  `notice_packets`, `payroll_precheck_records`.
- `GET /api/audit?q=&case_id=` and `/api/audit/{id}` — QA results; `case_id`
  filter returns exactly the events for one case.
- `GET /api/attachments/{id}` — raw notice/checklist body text.

Always cross-reference: an employee's authoritative state is spread across
employees, payroll-ledgers, policies, cases, documents, messages, and audit. When
an audit QA event names a specific controlling record, that naming is decisive —
use that exact id, its policy, and its numbers.

## 2. Source-precedence business rules

### Leave entitlement precedence
- The latest **Approved or Submitted** leave assignment for the period controls.
  **Draft, voided, superseded/obsolete** records are excluded — even when the
  employee profile summary disagrees. (An approved assignment overrides a stale
  profile summary.)
- Among multiple valid assignments, the latest dated Approved/Submitted one wins;
  prefer the annual leave-assignment row (e.g. `record_type: Leave assignment`)
  over month-scoped ledger adjustments unless the task asks for an adjustment.
- `excluded_leave_ids` / excluded records = EVERY non-controlling leave row
  (both superseded and draft), not just one.
- Normalized labels:
  - `leave_source` = `leave_assignment_history` when you read the assignment
    ledger (not the profile or case summary).
  - `leave_precedence_source` = `approved_assignment_current_period` when the
    controller is an Approved row for the period.
  - `precedence_source` = `approved_assignment_over_profile` when overriding a
    stale profile; `profile_policy_ignored = true`; `audit_result =
    profile_summary_stale`; remediation `next_action = update_employee_summary`.

### Payroll / salary precedence
- Use the **current Submitted salary assignment**. Draft planning assignments do
  NOT affect payroll readiness or accruals and must be excluded.
- `payroll_status` / `payroll_source_status` = `submitted`;
  `draft_exclusion_rule` = `exclude_draft_assignment`;
  `excluded_payroll_ids` / `excluded_assignment_id` = the draft (and any
  superseded) row.
- `base_salary` and `effective_date` come from the Submitted row (full date).
- Accruals: a batch is ready when the Submitted assignment matches the accrual
  batch and QA says so — `accrual_ready = true`, `control_result =
  ready_with_monitoring`, `audit_scope = payroll_assignment_readiness`.

### General draft/submitted/approved/superseded ordering
Authority for "what is effective": **Approved/Submitted > everything**;
**Draft and Superseded/voided/obsolete are always excluded** from the effective
state and listed as the excluded ids.

## 3. Folder readiness & document checklist

- A folder is ready ONLY when **all** `required_files` AND **all** `required_tags`
  are present. Compare the document's `required_files` vs `files` and
  `required_tags` vs `tags`.
- `missing_files` = required_files not in files (list them exactly).
- Missing FILE and missing TAG are SEPARATE blockers. If the required tag is
  present, `required_tag_present = true` and `folder_required_tag_action =
  no_tag_action`; only use `add_required_tag` when a required tag is absent.
- `closeout_blockers` lists only the categories actually failing:
  `missing_required_files`, `missing_required_tags`, `defective_formal_notice` —
  include each only if true.

## 4. Formal-notice defects

- Notice quality comes from inspecting the notice packet/message: `notice_quality`
  is `valid` or `defective`; copy the `defects` codes verbatim into
  `notice_defects`. Defect codes seen: `missing_ack_deadline`,
  `missing_appeal_instructions`, `missing_waitlist_status`,
  `missing_correct_policy`.
- Treat the notice-quality evidence source as **`notice_packet_inspection`**
  (inspect the formal-notice packet body), not `message_notice_inspection` or
  `case_summary_only`, even when the defect is logged in a message.
- Remediation: a defective notice -> `notice_remediation_action =
  reissue_defective_notices` and `next_action = block_close_and_reissue_notice`.
- Remote-work international-exception notices (per the Remote Work Policy) must
  contain: executive approval, time limits, tax equalization, VPN-only access,
  quarterly compliance review, appeal instructions, and an acknowledgement
  deadline. A missing element is a defect.

## 5. Closeout gate & final control result

- `approval_closeout_gate` is data-driven, not a constant:
  - clean records, no folder/notice defects -> `approval_sufficient_when_records_clean`.
  - any folder or notice defect -> `approval_not_sufficient_when_folder_or_notice_defective`.
- `final_control_result`:
  - clean -> `approve_closeout` (and `closeout_action = approve_onboarding_close`).
  - folder/notice defects -> `hold_for_folder_and_notice_defects`.
  - submitted-and-matching payroll/accrual -> `ready_with_monitoring`.
- `evidence_source_order` for closeout reviews = `approval_history_folder_notice_audit`.
- `records_remediation_owner` for routing remediation = `People Ops Compliance`
  (compliance owns remediation routing; do not default to the uploader/Records).

## 6. Audit correlation & scope (high-value, easy to get wrong)

- `audit_event_id` = the QA event whose topic matches the decision (leave event
  for a leave task, payroll event for a payroll task, notice event for a notice
  task), scoped to the case under review.
- `supporting_audit_event_ids` = the SAME-CASE event(s) on the decision's topic.
- `excluded_audit_event_ids` = ONLY the SAME-CASE **adjacent off-topic** events
  (e.g. the folder/tag event when the decision is about leave; the doc/notice
  events from sibling cases that a naive reader might mis-attribute). 
  - DO NOT dump the entire audit log or unrelated other-case/other-topic events
    into the excluded list — that is penalized. Keep it to the few genuinely
    adjacent, easily-confused events.
- `audit_scope` matches the decision: `leave_source_precedence_only`,
  `payroll_assignment_readiness`, or `document_notice_findings_only`.
- A cross-module escalation package (an audit event that "opens a package" and
  lists related event ids with a control owner and remediation clock) is its own
  thing: its related events and owner apply to the escalation, not to a single
  per-entity decision. For a single, non-escalation case set
  `escalation_action = no_action` rather than echoing `next_action`.

## 7. Recruitment reconciliation

- Outcomes come from `committee_decision` + the offer register, i.e.
  `candidate_status_source = interview_feedback_and_offer` and
  `candidate_outcome_control = committee_decision_with_offer_confirmation`.
- `selected_candidate` (Selected), `waitlisted_candidates`, `rejected_candidates`
  from committee decisions; arrays hold candidate IDs only.
- Offer: take `offer_id`, `offer_base_salary`, and `selected_offer_status`
  (`accepted`/`draft`/`withdrawn`/`none`) from the offer register for the
  selected candidate.
- `recruitment_cost_total` = sum of the **target opening's** `cost_ledger` line
  items ONLY. "All campaign ledger items" means all lines of THAT campaign — do
  not sum other openings. `cost_source = recruitment_cost_ledger`.
- Notice follow-up: candidates whose notice is `not_sent` need `send_*` actions
  (`send_waitlist_notice`, `send_rejection_notice`); use `reissue_*` only when an
  existing notice is defective/flagged for reissue. `notice_followup_required`
  lists those candidate IDs. `notice_quality_source = notice_packet_inspection`.
- `offer_exclusion_reason_for_waitlisted = no_accepted_status_or_offer`
  (waitlisted candidates have no accepted offer), NOT `waitlisted_not_selected`.

### Payroll handoff gate (recruiting)
- The handoff is created only after the selected candidate has an **accepted
  offer**, and the handoff must be a **Submitted** assignment; draft prechecks do
  NOT satisfy the gate.
- `payroll_handoff_gate = accepted_offer_only` (the trigger to create a handoff is
  the accepted offer).
- `payroll_assignment_status_required = submitted_after_acceptance`;
  `draft_payroll_allowed = false`;
  `onboarding_handoff = create_submitted_assignment_after_acceptance`;
  `handoff_control_result = submitted_handoff_required_after_acceptance`.

## 8. Common misjudgments that cost points (checklist)

1. Putting unrelated/other-case audit events into `excluded_audit_event_ids`
   (keep it to same-case adjacent off-topic events only).
2. Using `message_notice_inspection` instead of `notice_packet_inspection`.
3. Summing cost across all openings instead of the one target campaign.
4. Returning a `period` (`YYYY-MM`) where an `effective_date` (`YYYY-MM-DD`) is
   required.
5. Treating the closeout gate / control result as a constant instead of deriving
   it from whether records are actually clean.
6. Confusing missing FILE vs missing TAG (separate blockers / actions).
7. Echoing `next_action` into `escalation_action` for a non-escalation case
   (use `no_action`).
8. Forgetting to exclude BOTH superseded and draft records (not just one) from
   leave; forgetting to exclude the draft from payroll.
9. Defaulting remediation owner to the file uploader instead of
   `People Ops Compliance`.

## 9. Per-task method

1. Read the prompt + `answer_template.json`; note every key, type, and enum set.
2. Pull the relevant employee/case/recruitment record and ALL cross-referenced
   modules (ledger, policy, documents, messages, audit).
3. Fill data-literal fields first (ids, salaries, day counts, dates, decisions).
4. Apply the precedence/readiness/defect/audit-scope rules above for enums.
5. Keep list fields tight; copy ids verbatim; use full dates; output only the JSON
   object (no markdown, no commentary).
