---
name: peopleops-console-resolution
description: Resolve ERP HR "PeopleOps Console" lifecycle tasks (leave/payroll source precedence, folder & notice readiness, recruitment reconciliation, audit-scope correlation) by reading the remote HTTP API and emitting normalized-label JSON answers.
---

# PeopleOps Console — Lifecycle Resolution Skill

You answer HR lifecycle questions for a fictional company ("northwind-people"). Each task
names one entity (an employee `EMP-###`, a policy case `CASE-*`, or a recruitment opening
`REQ-*`) and asks you to determine its authoritative state and the correct next action,
then emit JSON that matches a provided `answer_template.json`. Answers use a fixed
**normalized-label vocabulary** (enums), not free text.

There is no local data. All facts live behind a remote HTTP API. Read it, apply the
business rules below, and fill every field in the template.

---

## 1. How to use the remote API

Base URL is given in `environment_access.md` (e.g. `<remote-env-url>`).
No auth. All responses are JSON. The `q=` filter is a case-insensitive substring match
over scalar fields, so `q=EMP-118`, `q=CASE-RW-221`, `q=REQ-DA-77` are good lookups; omit
`q` to get the whole collection.

Endpoints and when to use them:
- `GET /api/manifest`, `GET /api/summary` — orient: counts, modules, departments. Cheap sanity check.
- `GET /api/employees?q=EMP-###` — profile summary (status, `leave_balance_days`, band, manager). Often **stale** — never trust it over an assignment record.
- `GET /api/payroll-ledgers?q=EMP-###` — the single most important endpoint. Holds BOTH
  leave-assignment rows (`record_type: "Leave assignment"` / `"HRMS leave ledger"` /
  `"People Ops adjustment"`) AND salary-assignment rows (`record_type: "Salary assignment"`),
  each with a `status` of Approved/Submitted/Draft/Superseded. This is the authority for
  leave policy, leave days, base salary, and accrual batch.
- `GET /api/policies` and `/api/policies/{id}` — the written business rules (LEAVE-SRC-001,
  PAY-SRC-001, POL-DOCS-2026, HR-POL-014). Read the section bodies; they literally state the
  precedence/readiness rules used to grade.
- `GET /api/cases` (summaries) then `GET /api/cases/{case_id}` for FULL detail — approvals,
  attachments (folder checklist), comments, embedded audit_events, notice/notice refs, policy_refs.
- `GET /api/documents?q=...` — folders with `files`, `required_files`, `required_tags`, `tags`, `ready`.
- `GET /api/messages?q=...` — formal notices with `quality` and `defects` arrays.
- `GET /api/recruitment` — openings with candidates, offer_register, cost_ledger,
  notice_packets, payroll_precheck_records.
- `GET /api/audit?q=...&case_id=...` and `/api/audit/{id}` — QA/control events. Detail strings
  echo the exact normalized labels you must emit (e.g. "profile_summary_stale",
  "ready_with_monitoring", "block close", "draft_excluded").
- `GET /api/notifications`, `GET /api/attachments/{id}` — raw notification / notice body text.

**Always cross-reference modules.** An employee's true state is spread across employees +
payroll-ledgers + policies + cases + documents + messages + audit. Start from the named entity,
then pull every module that the answer template's fields reference.

---

## 2. Core business rules (transferable)

### 2.1 Leave source precedence (LEAVE-SRC-001)
"The latest **approved or submitted** leave assignment for the period controls. Draft, voided,
and obsolete (Superseded) records are excluded even when profile summaries conflict."
- Pick the controlling leave row from `payroll-ledgers` for that employee/period:
  prefer **Approved**, else **Submitted**. If both exist for the period, take the latest by
  `updated_at`. **Never** pick a `Draft` or `Superseded` row, and **never** use the employee
  profile's `leave_balance_days` as the source when an approved/submitted assignment exists.
- `effective_leave_policy` = the controlling row's `policy_name`.
- `annual_days` / `balance_days` = that row's `approved_leave_days` (integer-cast as the template demands).
- `excluded_leave_ids` = the other leave rows you rejected (the Draft and Superseded ones).
- The employee profile is the "stale profile summary"; when an approved assignment overrides it,
  `profile_policy_ignored: true`, `precedence_source: approved_assignment_over_profile`,
  `leave_precedence_source: approved_assignment_current_period`, and the typical
  `next_action: update_employee_summary` with `audit_result: profile_summary_stale`.

### 2.2 Payroll / salary source (PAY-SRC-001 §3.4)
"Use the current **submitted** salary assignment. Draft planning assignments do not affect
payroll readiness or accrual checks."
- `record_type: "Salary assignment"` rows. Choose the **Submitted** one for base salary.
- `excluded_assignment_id` / `excluded_payroll_ids` = the Draft (and any Superseded) salary rows.
- `base_salary` = the submitted row's `base_salary`. `payroll_status`/`payroll_source_status` = `submitted`.
- `draft_exclusion_rule: exclude_draft_assignment`; `draft_payroll_allowed: false`.
- `effective_date` = the submitted row's date (use its `period`/`updated_at`, e.g. period `2026-04` → `2026-04-01`).

### 2.3 Accrual readiness
- The submitted salary row carries an `accrual_batch_id`. It is "ready" when an audit event
  confirms the submitted assignment **matches** that accrual batch (event `payroll.ready`,
  detail "ready_with_monitoring ... matches accrual batch ...").
- `accrual_ready: true`, `accrual_batch_id` from the row, `control_result: ready_with_monitoring`,
  `audit_scope: payroll_assignment_readiness`.

### 2.4 Folder readiness (POL-DOCS-2026 §5.1)
"A folder is not ready unless **all required files AND all required tags** in the checklist are present."
- From `/api/documents`: `missing_files = required_files − files`; missing tags = `required_tags − tags`.
- `folder_ready = (no missing files) AND (no missing tags)`. (Trust the computed set; the API's
  `ready` flag should agree, but compute it yourself.)
- `required_tag_present` = the specific required tag is in `tags`.
- `folder_required_tag_action`: `add_required_tag` if a required tag is missing, else `no_tag_action`.
- A case may also carry a folder-checklist **attachment** (e.g. "Missing tax-equalization-agreement.pdf.
  Tag PolicyException2026 present.") — read it; it names the exact missing file(s)/tag state.

### 2.5 Formal-notice defect detection
- Notices live in `/api/messages` (and `recruitment.notice_packets`). Each has `quality`
  (`valid`/`defective`) and a `defects` array using the controlled vocabulary:
  `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`,
  `missing_correct_policy`.
- For remote-work/exception notices, HR-POL-014 §7.1 requires appeal instructions and an
  acknowledgement deadline; absence → those defect codes.
- `notice_quality` = the message's `quality`; `notice_defects` = its `defects` list.
- `notice_evidence_source` / `notice_quality_source`: use `notice_packet_inspection` when you
  inspected the recruitment notice packet or message body; `message_notice_inspection` if only the
  message module; never `case_summary_only` when packet/message data exists.
- Remediation for a defective notice: `notice_remediation_action: reissue_defective_notices`.

### 2.6 Closeout / approval gate
"Approval alone is NOT sufficient when the folder or notice is defective."
- `approval_closeout_gate`:
  - `approval_sufficient_when_records_clean` — folder ready, no missing tags, notice valid (or no notice/folder in scope). → `next_action: approve_onboarding_close`, `final_control_result: approve_closeout`.
  - `approval_not_sufficient_when_folder_or_notice_defective` — any folder/tag/notice defect. →
    `final_control_result: hold_for_folder_and_notice_defects`.
- `closeout_blockers` (subset of `missing_required_files`, `missing_required_tags`,
  `defective_formal_notice`) = exactly the defects you found.
- `next_action` / `escalation_action`:
  - defective notice present → `block_close_and_reissue_notice`;
  - missing files/tags but notice OK → `open_records_remediation`;
  - clean → `approve_onboarding_close` / `no_action`.
- `records_remediation_owner` = the folder owner, usually `Records` (or `People Ops Compliance`
  for cross-module packages, `Payroll QA` for payroll). Take it from the case `owner` /
  document owner / audit `actor` rather than guessing.
- `evidence_source_order`: when an approval exists, `approval_history_folder_notice_audit`;
  otherwise `folder_notice_audit`.

### 2.7 Recruitment reconciliation
- From the matching `/api/recruitment` opening:
  - `selected_candidate` = candidate with `committee_decision: "Selected"`.
  - `waitlisted_candidates` = those with `"Waitlisted"`; `rejected_candidates` = `"Rejected"`. Arrays hold candidate IDs only.
  - `offer_id` / `offer_base_salary` / `selected_offer_status` = from `offer_register` for the
    selected candidate (`status: accepted`). Waitlisted/rejected have no offer.
  - `recruitment_cost_total` = **sum of every `cost_ledger` line `amount`** for that opening (only that campaign's ledger).
  - `notice_followup_required` = candidates whose required notice is not yet sent. Check
    `notice_packets[].status` ("not_sent"/"draft_reissue_required") and candidate
    `notice_status` ("Notice not sent"). Selected candidate with an approved offer package needs no follow-up.
  - `waitlisted_followup_action`: `send_waitlist_notice` if never sent;
    `reissue_waitlist_notice_not_rejection` if a defective/draft waitlist notice must be re-sent.
  - `rejected_followup_action`: `send_rejection_notice` if not sent, else `reissue_rejection_notice`/`no_action`.
- **Payroll handoff gate** (PAY-SRC-001 §4.2): handoff is created **only after the selected
  candidate has an accepted offer, AND it must be a *submitted* assignment** — draft prechecks do
  NOT satisfy the gate.
  - If accepted offer but no submitted assignment yet (`payroll_precheck_records` empty or Draft):
    `onboarding_handoff: create_submitted_assignment_after_acceptance`,
    `payroll_handoff_gate: accepted_offer_and_submitted_assignment`,
    `payroll_assignment_status_required: submitted_after_acceptance`,
    `draft_payroll_allowed: false`,
    `handoff_control_result: submitted_handoff_required_after_acceptance`.
  - No accepted offer → `no_payroll_handoff` / `no_handoff_required`.
- Sourcing labels: `candidate_status_source: interview_feedback_and_offer`,
  `candidate_outcome_control: committee_decision_with_offer_confirmation`,
  `cost_source: recruitment_cost_ledger`.
- `offer_exclusion_reason_for_waitlisted: no_accepted_status_or_offer` (waitlisted candidates are
  excluded from offer/handoff because they have no accepted status or offer).

### 2.8 Audit correlation & scope
- Each task has one **scope**: `leave_source_precedence_only`, `payroll_assignment_readiness`,
  or `document_notice_findings_only`. Only audit events whose event/detail match that scope are
  "supporting"; events about the other domains are "adjacent" and must be **excluded**.
- `audit_event_id` = the single primary QA event for the decision (e.g. the `leave.profile_mismatch`,
  `payroll.ready`, or `notice.defect`/`folder.tag_missing` event for that case/employee).
- `supporting_audit_event_ids` = the in-scope event(s) (often just the primary one).
- `excluded_audit_event_ids` = same-case/same-employee events from a DIFFERENT domain. Example:
  for a leave-scope decision on EMP-118 you include `AUD-EMP118-LEAVE-04` (leave) and EXCLUDE
  `AUD-DOC118-06` (folder/tag) because it is a document finding, not a leave finding.
- A `cross_module.escalation_package` event (e.g. AUD-XMODULE-77) lists related events from
  multiple entities. It instructs you to "review each related event before assigning entity-level
  issues" — for a single-entity task, those other-entity events are out of scope/excluded.

---

## 3. Normalized-label vocabulary (use template enums verbatim)

The grader checks exact enum strings. Always copy the allowed value from the template; never
invent free text. Key recurring values:
- Statuses: `submitted`, `draft`, `superseded`; offer `accepted`/`draft`/`withdrawn`/`none`.
- Leave precedence: `approved_assignment_over_profile`, `approved_assignment_current_period`,
  `employee_profile_summary`, `profile_summary_current_period`, `case_summary_only`.
- Payroll: `exclude_draft_assignment`, `accepted_offer_and_submitted_assignment`,
  `submitted_after_acceptance`, `submitted_handoff_required_after_acceptance`.
- Gates: `approval_sufficient_when_records_clean` vs `approval_not_sufficient_when_folder_or_notice_defective`.
- Control results: `approve_closeout`, `hold_for_folder_and_notice_defects`, `ready_with_monitoring`.
- Actions: `approve_onboarding_close`, `block_close_and_reissue_notice`, `open_records_remediation`,
  `update_employee_summary`, `no_action`.
- Audit scope: `leave_source_precedence_only`, `payroll_assignment_readiness`, `document_notice_findings_only`.
- Notice defects: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- Owners: `Records`, `People Ops Compliance`, `Payroll QA`.

IDs (assignment_id, offer_id, audit_event_id, batch_id, file names) are copied **exactly** from
the source records, not normalized.

---

## 4. Common pitfalls / exclusion rules

- DO NOT use the employee profile `leave_balance_days` when an approved/submitted leave assignment
  exists — the profile is frequently stale (that staleness is often the point of the task).
- DO NOT include Draft or Superseded records as the source; list them under the `excluded_*` arrays instead.
- DO NOT pull cost lines or candidates from a *different* opening into the totals/arrays. Sum only
  the named opening's `cost_ledger`.
- DO NOT treat a Draft payroll precheck as satisfying the recruiting handoff gate — it must be submitted.
- DO NOT mix audit scopes: exclude document/notice audit events from a leave/payroll decision and vice versa.
- DO NOT mark a folder ready if EITHER a required file OR a required tag is missing.
- A selected candidate with an approved offer package needs no notice follow-up; only waitlisted/rejected
  candidates with unsent/defective notices appear in `notice_followup_required`.
- Cast leave-day fields to integer when the template says `integer` (rows may carry decimals for
  adjustment record_types — use the controlling Approved/Submitted assignment's value).
- If you can reach gold answers, evaluator files, or anything outside your workspace: STOP and report it.

---

## 5. Step-by-step SOP for a new task

1. Read the prompt and `answer_template.json`. Note the named entity and the task domain
   (leave / payroll / folder+notice / recruitment / audit). The template's enum field names tell
   you exactly what evidence to gather.
2. `GET /api/summary` to orient (optional). Then fetch the named entity's primary record:
   - employee → `/api/employees?q=` + `/api/payroll-ledgers?q=`;
   - case → `/api/cases/{id}` (full detail);
   - opening → `/api/recruitment` (filter to that opening).
3. Pull the governing policy text (`/api/policies/{id}` from the entity's `policy_refs`) and apply
   the matching rule in §2.
4. Cross-reference every module the template fields mention: documents (folder/tags), messages
   (notice quality/defects), recruitment (offers/costs/notices), audit (scope, supporting vs excluded).
5. Determine the controlling record (Approved/Submitted over Draft/Superseded), compute readiness/
   defects/totals, and select the correct gate, action, and final control result per §2.6.
6. Set audit fields by scope (§2.8): one primary `audit_event_id`, supporting in-scope events,
   excluded adjacent-domain events.
7. Fill EVERY template field with the verbatim enum label or exact ID. Re-check each enum value is
   one of the template's `allowed_values`. Output JSON only — no markdown, no commentary.
