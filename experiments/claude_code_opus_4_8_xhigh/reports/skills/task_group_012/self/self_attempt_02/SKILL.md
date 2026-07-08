---
name: peopleops-console-resolver
description: Resolve ERP HR "PeopleOps Console" cases (employee lifecycle, leave, payroll, policy cases, recruitment, documents, messages, audit) by reading the remote HTTP API, applying source-precedence and folder/notice/audit-scope rules, and returning normalized-label JSON that matches each task's answer_template.
---

# PeopleOps Console Resolver

You answer HR-lifecycle questions by reading a live, read-only HTTP API and emitting a
JSON object whose keys/enums are dictated by `input/payloads/answer_template.json`.
There is no local data. Every fact must be pulled from the API and reconciled across
modules. The hard part is never "finding a number" — it is applying the **business
precedence rules** and the **normalized-label vocabulary** the templates expect.

## 0. Golden rules (read first)
1. **The answer_template is the contract.** Output EXACTLY its keys. For `enum` /
   `list[enum]` fields you MUST emit one of the listed `allowed_values` verbatim — never
   free text, never a synonym. IDs (`string`) are copied verbatim from the API.
2. **Authoritative state lives across modules.** An employee's "real" leave/payroll
   state is rarely in the employee profile; it is in payroll-ledgers, the leave/HR
   policy, the case detail, documents, messages, and audit. Always cross-reference.
3. **Audit events usually hand you the answer label.** QA audit `detail` strings embed
   the exact normalized result (e.g. `QA result: profile_summary_stale`,
   `QA result: ready_with_monitoring`, `block close`) and name the controlling record
   ID. Find the audit event for the entity/case first; it confirms or short-circuits
   most reasoning. Do not ignore it, but still verify the IDs it names against the data.
4. **Draft / voided / obsolete / superseded records are excluded** from "effective"
   answers, but you must still RETURN their IDs in the `excluded_*` fields.

## 1. The remote API (base from environment_access.md, e.g. http://HOST:PORT)
Use `curl -s`. All JSON. No auth (any login text in the prompt is flavor). `q=` is a
case-insensitive substring filter over scalar fields; omit `q` to get the whole list.

| Endpoint | Use it for |
|---|---|
| `GET /api/summary` / `/api/manifest` | counts, departments, sanity check |
| `GET /api/employees?q=EMP-###` | profile summary: name, status, `leave_balance_days` (often STALE) |
| `GET /api/cases?...` | case summaries (status, type, owner, `policy_refs`, employee_id) |
| `GET /api/cases/{case_id}` | FULL case: `approvals`, `attachments`, `comments`, embedded `audit_events`, folder/notice pointers |
| `GET /api/policies` / `/api/policies/{id}` | the literal RULE TEXT (precedence, gates, checklist) — cite these |
| `GET /api/payroll-ledgers?q=EMP-###` | ALL leave-assignment AND salary-assignment rows with `status` |
| `GET /api/recruitment?q=REQ-...` | openings: candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records |
| `GET /api/documents?q=...` | folders: `files`, `required_files`, `tags`, `required_tags`, `ready` |
| `GET /api/messages` / `/api/notifications` | formal-notice bodies with `quality` and `defects[]` |
| `GET /api/audit?q=&case_id=` / `/api/audit/{id}` | QA events; `detail` carries the result label + controlling IDs |
| `GET /api/attachments/{id}` | raw attachment/notice text |

Efficient navigation: pull the employee, then `payroll-ledgers?q=EMP-###` (one call gives
every leave + salary row), then the related case (`/api/cases/{id}` for full detail),
then `documents`/`messages`/`audit` filtered by the case or employee. The four policy
docs encode every precedence rule — read them once to ground your labels.

## 2. Core business rules (transferable)

### 2.1 Leave source precedence (policy LEAVE-SRC-001)
"The latest approved or submitted leave assignment for the period controls. Draft,
voided, and obsolete records are excluded even when profile summaries conflict."
- Candidate rows are `record_type` = "Leave assignment" (and HRMS/People-Ops ledger
  rows) in `payroll-ledgers`. Pick the **Approved (or Submitted) assignment for the
  effective period (the year, e.g. 2026)**; that row's `policy_name` is the
  `effective_leave_policy`, and its `worksheet_leave_days` / `approved_leave_days` is the
  `annual_days` / `balance_days`.
- **Exclude** rows with `status` in {Draft, Superseded, Voided, Obsolete}: list their
  `ledger_id`s in `excluded_leave_ids`.
- The employee profile's `leave_balance_days` is the **profile summary** and is usually
  STALE; if an Approved assignment exists, it overrides the profile.
  → `precedence_source` = `approved_assignment_over_profile`,
    `leave_precedence_source` = `approved_assignment_current_period`,
    `leave_source` = `leave_assignment_history`, `profile_policy_ignored` = `true`.
- If the controlling audit says `profile_summary_stale`, the corrective `next_action` is
  `update_employee_summary` (not records remediation, not "no action") — the fix is to
  refresh the stale profile, since the approved assignment itself is fine.
- When several assignment-type rows exist, trust the audit event's named ID
  (e.g. "Approved assignment LA-118-APP-02 controls") over your own tie-breaking.

### 2.2 Payroll assignment source (policy PAY-SRC-001)
"Use the current submitted salary assignment. Draft planning assignments do not affect
payroll readiness or accrual checks."
- Among `record_type` = "Salary assignment" rows, pick `status` = **Submitted**. That
  row gives `base_salary`, `effective_date` (use its `period`/`updated_at` date), and the
  `accrual_batch_id` if present.
- **Exclude** the Draft (and Superseded) salary rows → `excluded_payroll_ids` /
  `excluded_assignment_id`. `draft_exclusion_rule` = `exclude_draft_assignment`,
  `draft_payroll_allowed` = `false`.
  → `payroll_status` / `payroll_source_status` = `submitted`.
- Accrual readiness: ready when the Submitted assignment's `accrual_batch_id` matches the
  target batch and the QA audit says `ready_with_monitoring`. Then `accrual_ready`=`true`
  and `control_result` = `ready_with_monitoring`.

### 2.3 Folder readiness & missing files/tags (policy POL-DOCS-2026)
"A folder is not ready unless all required files AND required tags in the checklist are
present."
- From the `documents` record: `missing_files` = `required_files` − `files`.
  `required_tag_present` = (`required_tags` ⊆ `tags`); else the tag(s) are missing.
- `folder_ready` = `ready` flag AND no missing files AND all required tags present.
- `folder_required_tag_action` = `add_required_tag` if a required tag is missing, else
  `no_tag_action`. If a required file is missing → `closeout_blockers` includes
  `missing_required_files`; missing tag → `missing_required_tags`.

### 2.4 Formal-notice defect detection
- Source of truth for notice quality is the **notice packet / message / notification**
  (`messages`, `notifications`, or the recruitment `notice_packets`), inspected directly
  — `notice_quality_source` / `notice_evidence_source` = `notice_packet_inspection` (or
  `message_notice_inspection` when the evidence is the HRMS/email message), NOT
  `case_summary_only`.
- `notice_quality` = the record's `quality` (`valid`|`defective`). `notice_defects` =
  the record's `defects[]`, each from the template enum
  {`missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`,
  `missing_correct_policy`}.
- A defective notice that must be re-sent → `notice_remediation_action` =
  `reissue_defective_notices`; for recruitment, a waitlisted candidate's bad notice is
  `reissue_waitlist_notice_not_rejection` (do NOT downgrade a waitlist to a rejection).

### 2.5 Closeout / approval gate
"Approval alone is NOT sufficient when the folder or notice is defective."
- `approval_closeout_gate` = `approval_not_sufficient_when_folder_or_notice_defective`
  whenever there is a missing file/tag or a defective notice; otherwise
  `approval_sufficient_when_records_clean`.
- Final result mapping:
  - clean records + valid notice + ready folder → `approve_closeout` /
    `approve_onboarding_close`, `final_control_result` = `approve_closeout`.
  - folder/notice defects present → `hold_for_folder_and_notice_defects`, and
    `next_action`/`escalation_action` = `block_close_and_reissue_notice` (notice defect)
    or `open_records_remediation` (file/tag defect). Records owner for file/tag gaps =
    `Records`; compliance escalations route to `People Ops Compliance`.
  - records fine but still being watched (e.g. payroll just submitted) →
    `ready_with_monitoring`.

### 2.6 Recruitment reconciliation
- Candidate outcomes come from `committee_decision` confirmed by the `offer_register`
  (`candidate_status_source` = `interview_feedback_and_offer`,
  `candidate_outcome_control` = `committee_decision_with_offer_confirmation`):
  - `selected_candidate` = the candidate with `committee_decision`="Selected" who has an
    `offer_register` entry with `status`=`accepted` (`selected_offer_status`=`accepted`).
  - `waitlisted_candidates` / `rejected_candidates` = grouped by `committee_decision`.
- `recruitment_cost_total` = **sum of ALL `cost_ledger[].amount`** for the opening
  (`cost_source` = `recruitment_cost_ledger`). Sum every line, not just some.
- `notice_followup_required` = candidate IDs whose notice is not yet properly sent
  (`notice_status`="Notice not sent" or packet `status` in {not_sent, draft_reissue_required}).
  Waitlist → `send_waitlist_notice`/reissue; rejection → `send_rejection_notice`.
- Payroll handoff gate (PAY-SRC-001 §4.2): handoff is created **only after the selected
  candidate has an accepted offer, and it must be a SUBMITTED assignment**; draft
  prechecks do NOT satisfy the gate. With an accepted offer →
  `onboarding_handoff` = `create_submitted_assignment_after_acceptance`,
  `payroll_handoff_gate` = `accepted_offer_only` (status
  `accepted_offer_and_submitted_assignment` if a submitted assignment is also required),
  `payroll_assignment_status_required` = `submitted_after_acceptance`,
  `handoff_control_result` = `submitted_handoff_required_after_acceptance`,
  `draft_payroll_allowed` = `false`. Waitlisted/rejected candidates get no offer:
  `offer_exclusion_reason_for_waitlisted` = `no_accepted_status_or_offer`.

### 2.7 Audit correlation & scope (CRITICAL exclusion rule)
- Each task has a narrow `audit_scope`. Include only the audit event(s) matching that
  scope; **exclude adjacent events on the same case** that belong to a different scope.
  - leave precedence task → `audit_scope` = `leave_source_precedence_only`; keep the
    `leave.profile_mismatch` event, EXCLUDE folder/document events
    (`folder.tag_missing`, `notice.defect`) → put them in `excluded_audit_event_ids`.
  - document/notice task → `audit_scope` = `document_notice_findings_only`; keep
    folder/notice events, exclude leave/payroll events.
  - payroll task → `audit_scope` = `payroll_assignment_readiness`.
- `supporting_audit_event_ids` = the in-scope events; `audit_event_id` = the single
  primary one. Event `event` types seen: `leave.profile_mismatch`, `payroll.ready`,
  `payroll.draft_excluded`, `notice.defect`, `folder.tag_missing`,
  `case.close_blocked`, `cross_module.escalation_package`.
- Cross-module escalation packages (`cross_module.escalation_package`) list "Related
  events: A, B, C" in their `detail` and carry a control owner + remediation clock
  (SLA). For those tasks, the related event IDs ARE the scope; review each before
  assigning entity-level owners.

## 3. Normalized-label vocabulary (use the template's enum, not these notes)
Pull `allowed_values` straight from the answer_template; common ones:
- sources: `leave_assignment_history`, `approved_assignment_over_profile`,
  `approved_assignment_current_period`, `notice_packet_inspection`,
  `recruitment_cost_ledger`, `interview_feedback_and_offer`,
  `approval_history_folder_notice_audit`.
- statuses: `submitted` / `draft` / `superseded`; `accepted` / `draft` / `withdrawn` / `none`.
- gates: `approval_sufficient_when_records_clean` vs
  `approval_not_sufficient_when_folder_or_notice_defective`;
  `exclude_draft_assignment`; `accepted_offer_only`.
- results/actions: `approve_closeout` / `approve_onboarding_close`,
  `hold_for_folder_and_notice_defects`, `ready_with_monitoring`,
  `block_close_and_reissue_notice`, `open_records_remediation`,
  `update_employee_summary`, `no_action`.
- owners: `Records`, `People Ops Compliance`, `Payroll QA`.

## 4. Common misjudgments / pitfalls
- Using the employee profile `leave_balance_days` as the answer — it is the STALE
  profile summary; the Approved assignment overrides it.
- Picking an Approved/Draft salary or leave row when a Submitted/Approved one exists, or
  forgetting to LIST the excluded IDs.
- Summing only part of the recruitment `cost_ledger` — sum EVERY line.
- Reading notice quality from the case `summary` (use `case_summary_only` only as a last
  resort) instead of inspecting the actual notice packet/message.
- Putting an out-of-scope audit event in `supporting_audit_event_ids` instead of
  `excluded_audit_event_ids` (folder event in a leave task, etc.).
- Treating a stale-profile fix as `open_records_remediation` — the fix is
  `update_employee_summary`; remediation is for genuinely missing files/tags.
- Downgrading a waitlisted candidate to a rejection notice.
- Emitting free-text or invented enum values instead of the template's `allowed_values`.

## 5. Step-by-step SOP for a new task
1. Read the prompt + `input/payloads/answer_template.json`. List every output key and,
   for each enum, its exact `allowed_values`. Identify the subject (EMP-###, CASE-###,
   REQ-###) and the task family (leave / payroll / policy-case / recruitment /
   document / cross-module).
2. Pull the subject: `employees?q=`, the related `cases/{id}` (full), and
   `payroll-ledgers?q=` for the employee.
3. Pull the governing policy doc(s) named in the case `policy_refs` to ground the rule
   and its label.
4. Pull the matching audit event(s) (`audit?q=` or `?case_id=`); read `detail` for the
   QA result label and the controlling record ID. Note which events are in/out of scope.
5. Pull module-specific evidence: documents (folder readiness), messages/notifications/
   notice_packets (notice quality+defects), recruitment (candidates/offers/costs).
6. Apply §2 rules: choose the effective record (approved/submitted), collect excluded
   IDs, compute missing files/tags, read notice defects, sum costs, set the scope and
   supporting/excluded audit lists, derive the gate and final result.
7. Build the JSON using ONLY template keys; map every enum to an allowed value verbatim;
   copy IDs exactly. Double-check no extra keys, correct types (integer vs number,
   boolean, list[string]).
8. Output JSON only (no markdown/prose) when the prompt says so.
