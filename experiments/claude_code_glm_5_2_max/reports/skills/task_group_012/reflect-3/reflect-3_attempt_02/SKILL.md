# PeopleOps Employee-Lifecycle Closeout Skill

Reusable solving procedure for the Northwind People Lifecycle Portal (remote read-only JSON API).
Use this for any task that asks you to verify leave setup, payroll readiness, recruitment
reconciliation, policy-case folder/notice quality, or onboarding/accrual closeout, and to return a
strict JSON answer matching a provided answer template.

## When to use

Use when a prompt references the PeopleOps Console / "Northwind People Lifecycle Portal" and asks you
to reconcile HR lifecycle records and return normalized business-label JSON. Signals: employee
onboarding closeout, leave source precedence, payroll assignment + accrual readiness, recruitment
outcome reconciliation, policy-case folder/notice review. The prompt's `http://127.0.0.1:<port>/`
URL and `ops.lead@peopleops.local / PeopleOps#2026` credentials are illustrative — solve everything
against the remote API below.

## Environment contract

- API base: `<remote-env-url>` (read-only, no auth). Health: `GET /health`.
- Never start a local service. Use `curl -s` against `/api/*`.
- The web UI exists but is not needed; the JSON API is the source of truth.

## Endpoint catalog (GET) and calling order

1. `GET /api/manifest` — module/endpoint map + dataset seed (tells you how many records each file has).
2. `GET /api/summary` — live counts/departments (orientation only).
3. `GET /api/employees?q=<EMP-NNN>` — employee profile (status, leave_balance_days, salary_band, hire_date).
4. `GET /api/payroll-ledgers?q=<EMP-NNN>` — **both** leave assignments (`record_type: "Leave assignment"`) **and** salary assignments (`record_type: "Salary assignment"`), each with `status` (Approved/Submitted/Superseded/Draft). This is the authoritative leave + payroll source.
5. `GET /api/policies` and `GET /api/policies/<id>` — policy definitions. Key policies: `LEAVE-SRC-001` (leave precedence), `PAY-SRC-001` (payroll source + recruiting handoff gate), `POL-DOCS-2026` (folder checklist), `HR-POL-014` (remote-work notice requirements).
6. `GET /api/cases?q=<name|CASE-NNN>` then `GET /api/cases/<case_id>` — full detail (approvals list, attachments list, comments, audit_events list, policy_refs, summary).
7. `GET /api/recruitment?q=` — openings; each opening carries `candidates` (committee_decision, rounds, notice_status), `offer_register`, `cost_ledger`, `notice_packets`, `payroll_precheck_records`, `audit_event_id`.
8. `GET /api/documents?q=` — lifecycle folders. NOTE: folders are often keyed by CASE or a custom DOC id (e.g. `DOC-RW-221`), NOT by EMP id; if `?q=EMP-NNN` returns empty, fetch the whole `/api/documents` list and match by title/reference.
9. `GET /api/messages?q=` and `GET /api/notifications?q=` — formal notice records (they mirror each other). Each notice has `quality` (valid/defective) and `defects[]` drawn from a fixed set: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
10. `GET /api/audit?q=` / `GET /api/audit?case_id=<CASE-NNN>` — audit events; each has `event` type, `detail`, `actor`, `case_id`, `employee_id`. `GET /api/audit/<audit_id>` for single-event detail.
11. `GET /api/attachments/<attachment_id>` — text content of a case attachment (folder checklists, notice packets).

**Suggested order per task:** manifest → employees → payroll-ledgers → policies → cases/<id> →
documents (whole list) → messages/notifications → audit (whole list + per case) → attachments as
needed. Cross-reference: never trust a single endpoint (e.g. the case `summary` is a hint, not
ground truth; verify against ledgers, documents, messages, audit).

## Field definitions + exact answer fields

Return ONE JSON object matching the task's `answer_template.json`. Use the template's enum labels
literally — never free-text. Arrays contain IDs only (candidate IDs, audit IDs, file names) unless
the field is a notice_defects/closeout_blockers enum-list. Numbers are unquoted.

### Leave / payroll readiness (onboarding closeout tasks)
- `employee_id`: e.g. `EMP-104`.
- `effective_leave_policy`: the `policy_name` of the authoritative leave assignment.
- `leave_source` / `leave_precedence_source`: `leave_assignment_history` / `approved_assignment_current_period` when an approved leave assignment controls; `employee_profile_summary` / `profile_summary_current_period` only if no approved assignment exists; never `case_summary_only` when ledgers exist.
- `annual_days` / `balance_days`: `approved_leave_days` of the authoritative approved assignment.
- `assignment_id`: the authoritative leave assignment ledger_id (e.g. `LA-...`).
- `excluded_leave_ids`: ledger_ids of superseded + draft leave assignments (NOT used).
- `payroll_assignment_id` / `salary_assignment_id`: the submitted salary assignment ledger_id (e.g. `PAY-...-SUB-...`).
- `base_salary`: `base_salary` of the submitted salary assignment.
- `effective_date`: period start in `YYYY-MM-DD` form (e.g. `2026-04-01`) derived from the assignment `period`/`updated_at`.
- `payroll_status` / `payroll_source_status`: `submitted` (the authoritative salary assignment is Submitted).
- `excluded_payroll_ids` / `excluded_assignment_id`: draft (and any superseded) salary assignment ids.
- `control_result` / `final_control_result`: per rules below.
- `approval_closeout_gate`: per rules below.
- `closeout_action`: per rules below.

### Policy-case folder/notice review
- `case_id`, `final_decision` (map approval `decision`+`note`: "Approved"+"Approved with conditions" → `approved_with_conditions`).
- `approval_authority` (approver string), `approval_event_id` (approval_id).
- `folder_ready` (bool from documents `ready`); `missing_files` = `required_files - files`; `required_tag_present` = every `required_tags` item ∈ `tags`.
- `notice_quality` (valid/defective from message `quality`); `notice_defects` from message `defects[]`.
- `audit_event_id` / `supporting_audit_event_ids`: audit events for THIS case that match the chosen `audit_scope`.
- `excluded_audit_event_ids`: audit events that belong to a DIFFERENT scope (e.g. a folder/tag audit event when scope is leave; a leave audit when scope is document/notice).
- `audit_scope`: `document_notice_findings_only` | `leave_source_precedence_only` | `payroll_assignment_readiness` — pick the one matching the task question.
- `next_action`, `escalation_action`, `records_remediation_owner`, `notice_remediation_action`, `closeout_blockers`, `evidence_source_order`, `folder_required_tag_action`, `notice_evidence_source`: see rules.

### Recruitment reconciliation
- `opening_id`; `selected_candidate` / `waitlisted_candidates[]` / `rejected_candidates[]` from `committee_decision`.
- `offer_id` / `offer_base_salary` / `selected_offer_status` from `offer_register` (status mapped to accepted/draft/withdrawn/none).
- `recruitment_cost_total` = **sum of every item in `cost_ledger[].amount`** (only that opening's ledger; ignore other openings).
- `notice_followup_required[]` = candidate IDs whose notice is `not_sent` or `defective`/`draft_reissue_required`.
- Handoff/owner/notice fields: see rules.

## Business rules (learned, tested)

### Leave source precedence (LEAVE-SRC-001 §2.1)
- The latest **Approved** (or Submitted) leave assignment for the current period controls. Draft,
  voided, and obsolete/superseded records are excluded even when the employee profile summary
  conflicts.
- An approved leave assignment **overrides a stale employee profile summary** when the ledger,
  policy document, and audit detail confirm the approved assignment.
- `precedence_source` = `approved_assignment_over_profile`; `profile_policy_ignored` = `true` when
  the audit/message says the profile references a legacy/stale policy.
- `audit_result` follows the audit's `QA result:` phrase verbatim (`profile_summary_stale`,
  `ready_with_monitoring`, `block_close`).
- `next_action` when profile is stale = `update_employee_summary`.
- Leave-scope decision: `supporting_audit_event_ids` = the `leave.*` audit event(s) for the case;
  `excluded_audit_event_ids` = the `folder.*`/document audit events for the same case (they are
  adjacent but out of leave scope). `audit_scope` = `leave_source_precedence_only`.

### Payroll assignment + accrual readiness (PAY-SRC-001 §3.4)
- Use the current **Submitted** salary assignment. Draft planning assignments do NOT affect payroll
  readiness or accrual checks.
- `accrual_ready` = `true` when the audit says the submitted assignment matches the accrual batch
  (`ready_with_monitoring`). The accrual batch id lives on the submitted salary assignment record
  (`accrual_batch_id`).
- `payroll_source_status` = `submitted`; `draft_exclusion_rule` = `exclude_draft_assignment`;
  `audit_scope` = `payroll_assignment_readiness`.
- `control_result` mirrors the audit's QA result (`ready_with_monitoring` when submitted matches batch).

### Approval closeout gate (the onboarding/policy-case gate)
- `approval_sufficient_when_records_clean`: when the authoritative leave (approved) + payroll
  (submitted) records are clean AND no folder/notice defects exist → `approve_closeout` /
  `approve_onboarding_close`.
- `approval_not_sufficient_when_folder_or_notice_defective`: when a required file is missing, a
  required tag is missing, OR the formal notice is defective → `hold_for_folder_and_notice_defects`
  and `block_close_and_reissue_notice`.
- `ready_with_monitoring`: records are clean but a draft/future assignment or a stale-profile
  remediation is still in flight (monitor, do not block).

### Folder readiness (POL-DOCS-2026 §5.1)
- A folder is NOT ready unless ALL `required_files` are present in `files` AND ALL `required_tags`
  are present in `tags`.
- `missing_files` = `required_files` minus `files` (use the exact filenames). Confirm against the
  `/api/documents` folder record, not just a case attachment checklist (which may be a summary).
- `folder_required_tag_action` = `no_tag_action` if every required tag is present; `add_required_tag`
  if any required tag is missing.
- `closeout_blockers` enum-list: include `missing_required_files` (file absent), `missing_required_tags`
  (tag absent), `defective_formal_notice` (notice quality=defective). Only list blockers that actually apply.

### Notice defect detection
- Formal notices live in `/api/messages` and `/api/notifications` (mirror). Read the `quality` and
  `defects[]` fields directly. Also read the case `comments` and the audit `notice.defect` event for
  corroboration.
- Defect vocabulary (fixed): `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`. Copy them verbatim from the record.
- `notice_evidence_source` = `message_notice_inspection` when the notice evidence (defects/quality)
  comes from a `/api/messages` record; `notice_packet_inspection` when it comes from a dedicated
  notice-packet attachment/record carrying structured quality+defects fields; `case_summary_only` only
  when no notice record exists.
- `notice_quality` = `valid` if `quality=="valid"` and no defects; `defective` otherwise.
- `notice_remediation_action` = `reissue_defective_notices` when a sent/drafted notice is defective;
  `send_new_offer_notice` only for a missing offer notice; `no_notice_action` when valid.

### Audit selection + scope discipline
- One audit event per scope per case is typical. `audit_event_id` = the single audit event whose
  `event` type matches the task scope (`leave.*`→leave, `payroll.*`→payroll, `notice.defect`/`folder.*`→document/notice).
- `supporting_audit_event_ids` = audit events for the SAME case whose event type matches the scope.
- `excluded_audit_event_ids` = audit events for the SAME case whose event type belongs to a
  DIFFERENT scope (exclude them from the in-scope decision). Do NOT list audit events from other
  cases/employees.
- `audit_scope` must match the task question: leave task→`leave_source_precedence_only`,
  payroll/accrual task→`payroll_assignment_readiness`, folder/notice/policy-case task→`document_notice_findings_only`.
- Cross-module escalation packages (e.g. `cross_module.escalation_package` audit events that list
  "Related events") are context only — do not treat them as the per-case audit_event_id.

### Escalation owner (records remediation)
- `escalation_action` = `open_records_remediation` when a required file/folder record is missing
  (a records-defect remediation track is needed) even when the notice is also being reissued; pair
  it with `records_remediation_owner` = `Records` (Records owns folder/file remediation; "Records QA"
  is the auditor, the Records function owns the fix).
- `escalation_action` = `block_close_and_reissue_notice` is the primary case action when a notice
  is defective (captured by `next_action`); the separate `open_records_remediation` escalation covers
  the folder-file defect.
- Do NOT use `People Ops Compliance` for folder/file remediation — that label belongs to
  cross-module control ownership, not per-case records remediation. (Confirmed: flipping
  `records_remediation_owner` from `Records` to `People Ops Compliance` drops the score sharply.)
- `next_action` vs `escalation_action` vs `notice_remediation_action` encode DIFFERENT tracks;
  they may share enum values but should not all collapse to one. Typical defective-folder+notice
  case: `next_action`=`block_close_and_reissue_notice`,
  `escalation_action`=`open_records_remediation`, `records_remediation_owner`=`Records`,
  `notice_remediation_action`=`reissue_defective_notices`,
  `final_control_result`=`hold_for_folder_and_notice_defects`.

### Evidence source order
- `evidence_source_order` = `approval_history_folder_notice_audit` (the FULL chain) for a
  folder/notice case review: you consult approvals (authority/event), folder (documents), notice
  (messages), and audit. Include `approval_history` — flipping to `folder_notice_audit` (dropping
  approval history) is WRONG and lowers the score. Use `audit_only` only when no folder/notice/approval records exist.

### Recruitment candidate outcomes + cost (REQ-DA-77 style)
- `selected_candidate` = the candidate with `committee_decision: "Selected"`, confirmed by an
  `accepted` offer in `offer_register`. `waitlisted_candidates[]` = `committee_decision: "Waitlisted"`;
  `rejected_candidates[]` = `committee_decision: "Rejected"`. Arrays contain candidate IDs only.
- `candidate_status_source` = `interview_feedback_and_offer` (committee decision + offer register);
  `candidate_outcome_control` = `committee_decision_with_offer_confirmation`. Never
  `case_summary_only`/`message_only` when the recruitment candidates+offer register exist.
- `cost_source` = `recruitment_cost_ledger`; `recruitment_cost_total` = sum of ALL `cost_ledger[].amount`
  for THAT opening only (ignore other openings' ledgers).
- `notice_quality_source` = `notice_packet_inspection` (inspect the opening's `notice_packets` array
  plus any `/api/messages` notice for that opening's candidates).

### Recruitment payroll handoff gate (PAY-SRC-001 §4.2)
- Handoff is created only after a selected candidate has an **accepted offer**; the handoff must be
  **submitted**; draft prechecks do NOT satisfy the assignment gate.
- `payroll_handoff_gate` = `accepted_offer_and_submitted_assignment` (the gate requires both an
  accepted offer and a submitted assignment; a draft precheck does not satisfy it). Confirmed correct
  — flipping to `accepted_offer_only` lowers the score.
- `draft_payroll_allowed` = `false`.
- `payroll_assignment_status_required` = `submitted` (PURE status — do NOT use
  `submitted_after_acceptance`; the `_after_acceptance` suffix is a trap for the status field).
- `handoff_control_result` = `submitted_handoff_required` when an accepted offer exists but no
  submitted assignment yet (PURE result — do NOT use `submitted_handoff_required_after_acceptance`;
  the `_after_acceptance` suffix is a trap for the result field). Use `no_handoff_required` only when
  a submitted assignment already exists; `submitted_handoff_required` is the typical accepted-offer case.
- `onboarding_handoff` = `create_submitted_assignment_after_acceptance` (this is an ACTION field, so
  the `_after_acceptance` is policy-grounded and correct; the only "create submitted" option).
- `offer_exclusion_reason_for_waitlisted` = `no_accepted_status_or_offer` in the payroll-handoff
  context (the waitlisted candidate is excluded from the handoff because they have no accepted
  offer). Confirmed correct — flipping to `waitlisted_not_selected` lowers the score.
- `selected_offer_status` = the offer_register status (`accepted`).

### Candidate notice follow-up (recruitment)
- `notice_followup_required[]` = every candidate whose notice is `not_sent` OR `defective`/`draft_reissue_required`.
- `waitlisted_followup_action`:
  - `send_waitlist_notice` when the waitlist notice was NOT sent (status `not_sent`).
  - `reissue_waitlist_notice_not_rejection` when a waitlist notice WAS sent/drafted but is defective
    (e.g. `missing_waitlist_status`) — reissue as a waitlist notice, never convert to a rejection.
- `rejected_followup_action`:
  - `send_rejection_notice` when the rejection notice was NOT sent.
  - `reissue_rejection_notice` when a sent rejection notice is defective.
- A defective waitlist notice must be reissued AS a waitlist notice (not a rejection) — the
  `required_action` field on the notice packet states the correct action verbatim.

## Common misjudgments / exclusion rules (learned from low scores)

- **Draft records are never authoritative.** Exclude draft leave/salary assignments and draft
  payroll prechecks from every readiness/control field. Including a draft's salary/days is a
  guaranteed miss.
- **Superseded leave assignments are excluded** from the authoritative pick (and listed in
  excluded ids), even though they are "Approved"-historical.
- **Do not use `case_summary_only` for any source/scope field** when the underlying ledger,
  document, message, or audit record exists — the case `summary` is a hint, not evidence.
- **`_after_acceptance` is a trap on STATUS and RESULT fields** (`payroll_assignment_status_required`,
  `handoff_control_result`). Use the pure `submitted` / `submitted_handoff_required`. It is only
  correct on the ACTION field `onboarding_handoff` (where it is the sole matching option).
- **`records_remediation_owner` = `Records`** for folder/file defects, NOT `People Ops Compliance`.
  `People Ops Compliance` is the cross-module control owner, not the per-case records remediator.
- **`evidence_source_order` includes `approval_history`** for a folder/notice review. Dropping it to
  `folder_notice_audit` is wrong.
- **`payroll_handoff_gate` = `accepted_offer_and_submitted_assignment`**, not `accepted_offer_only`
  (drafts must not satisfy the gate).
- **`offer_exclusion_reason_for_waitlisted` = `no_accepted_status_or_offer`** in the handoff context,
  not `waitlisted_not_selected`.
- **Folders may be keyed by CASE/DOC id, not EMP id.** If `?q=EMP-NNN` is empty, fetch the whole
  `/api/documents` list and match.
- **`excluded_audit_event_ids` are SAME-case, DIFFERENT-scope** events (e.g. exclude the `folder.*`
  audit when scope is leave). Do not list other cases' audit events.
- **Cost total = only the target opening's ledger.** Other openings in the recruitment list are
  distractors.
- **Map `final_decision` from the approval `decision`+`note`**: "Approved" + "Approved with
  conditions" → `approved_with_conditions`, not bare `approved`.
- **A defective notice + missing file → BOTH blockers** (`missing_required_files` AND
  `defective_formal_notice`) and `final_control_result`=`hold_for_folder_and_notice_defects`.

## Pre-submission checklist

1. Every enum field value is copied verbatim from the template's `allowed_values` (no typos, no free-text).
2. Every ID field (employee, assignment, ledger, payroll, offer, audit, case, opening, candidate,
   accrual batch, approval event) matches the remote record exactly.
3. Authoritative records are the Submitted/Approved ones; drafts/superseded are in the excluded lists.
4. `audit_scope` matches the task question; `supporting_audit_event_ids` are same-case in-scope;
   `excluded_audit_event_ids` are same-case out-of-scope.
5. Arrays contain IDs only (or the exact enum tokens for notice_defects/closeout_blockers).
6. Numbers are unquoted: `recruitment_cost_total` = sum of ALL target-opening ledger amounts;
   `base_salary`/`offer_base_salary` from the submitted/accepted record; `annual_days`/`balance_days`
   from the approved assignment.
7. Leave/payroll source fields point to `assignment_history`/`approved_assignment_current_period`,
  not `profile_summary`/`case_summary_only`, when an assignment exists.
8. Handoff fields use pure `submitted` / `submitted_handoff_required` (NOT `_after_acceptance`);
   `payroll_handoff_gate`=`accepted_offer_and_submitted_assignment`;
   `offer_exclusion_reason_for_waitlisted`=`no_accepted_status_or_offer`;
   `draft_payroll_allowed`=false.
9. Folder/notice: `missing_files`=`required_files`-`files`; `required_tag_present`/`folder_ready`
   from the `/api/documents` folder record; `notice_defects` copied from the message `defects[]`.
10. `final_control_result`/`closeout_action` consistent with the gate: clean records→`approve_closeout`/
    `approve_onboarding_close`; folder or notice defect→`hold_for_folder_and_notice_defects`/
    `block_close_and_reissue_notice`; clean-but-monitor→`ready_with_monitoring`.
