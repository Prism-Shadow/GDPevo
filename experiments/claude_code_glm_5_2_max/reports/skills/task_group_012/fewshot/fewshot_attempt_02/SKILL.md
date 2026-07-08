---
name: peopleops-lifecycle-clearance
description: Solve PeopleOps employee-lifecycle clearance / audit / reconciliation tasks against the read-only Northwind People Lifecycle Portal JSON API. Use when a task asks to verify onboarding closeout, leave source precedence, payroll/accrual readiness, case folder + formal-notice quality, or recruitment reconciliation, and return a normalized JSON answer.
---

# PeopleOps Lifecycle Clearance Skill

## When to use
Use this skill for any task that points at the Northwind "PeopleOps Console" / "People Lifecycle Portal" and asks you to verify, audit, reconcile, or clear an HR-lifecycle artifact and return a JSON answer matching a template. The task types covered:

- **Onboarding closeout verification** — effective leave policy + payroll setup for an employee before approving close.
- **Leave source precedence** — which leave policy/balance is authoritative when profile summary, ledger, policy doc, and audit disagree.
- **Payroll assignment & accrual readiness** — which salary assignment controls, draft exclusion, accrual batch readiness.
- **Case folder + formal-notice quality** — folder readiness (missing files/tags), notice defect detection, approval-vs-block decision.
- **Recruitment reconciliation** — candidate outcome, offer confirmation, cost sum, notice follow-up, payroll handoff gate.

Every task boils down to: resolve the entity, pull authoritative records from the right API, apply source-precedence + exclusion rules, detect defects, pick the matching audit event, choose the normalized enum labels, emit one JSON object.

## Environment
- Web UI: `<remote-env-url>/`
- JSON API base: `<remote-env-url>` (read-only, **no auth**)
- Health: `GET /health` -> `{"ok": true, ...}`
- The prompt's `http://127.0.0.1:<port>/` and login `ops.lead@peopleops.local / PeopleOps#2026` refer to THIS remote environment. Do not start a local server and do not attempt login; just hit `/api/*`.

### Endpoints (all GET, read-only)
| Endpoint | Use for |
|---|---|
| `/api/manifest` | module/file map, dataset seed (sanity check) |
| `/api/summary` | live record counts + departments |
| `/api/employees?q=&status=` | employee profile records (`leave_balance_days`, `salary_band`, no policy name, no assignment history) |
| `/api/payroll-ledgers?q=&status=&type=` | **leave assignments + salary assignments + aux ledgers** (single source for both leave and payroll precedence) |
| `/api/cases?q=&status=&type=` | policy case summaries |
| `/api/cases/<case_id>` | FULL case detail: `approvals[]`, `attachments[]` (with `content`), `comments[]`, `audit_events[]`, `policy_refs[]`, `summary` |
| `/api/policies` / `/api/policies/<id>` | authoritative business-rule definitions (source-precedence, folder checklist, payroll, notice) |
| `/api/documents?q=` | lifecycle document folders: `files[]`, `required_files[]`, `required_tags[]`, `tags[]`, `ready` |
| `/api/messages?q=` | formal notices: `quality`, `defects[]`, `recipient`, `case_id`, `status` |
| `/api/notifications?q=` | same shape as messages (ack deadlines / appeal info) |
| `/api/audit?q=&case_id=` | audit events: `audit_id`, `event`, `detail`, `actor`, `case_id`, `employee_id` |
| `/api/audit/<audit_id>` | single audit event detail |
| `/api/attachments/<attachment_id>` | attachment text content (also embedded in case detail) |
| `/api/recruitment?q=` | openings: `candidates[]`, `offer_register[]`, `cost_ledger[]`, `notice_packets[]`, `payroll_precheck_records[]` |

Search with `?q=<keyword>` (matches across fields). Filter with `?status=` / `?type=`. Always fetch the **full case detail** via `/api/cases/<id>` (the summary list omits attachments, comments, full audit events).

## Standard operating procedure

1. **Identify the entity & task type.** From the prompt extract: employee id (`EMP-xxx`), case id (`CASE-...`), opening id (`REQ-...`), or candidate id (`CAND-...`), plus which decision is asked (leave / payroll / folder+notice / recruitment). The primary id field of the answer (`employee_id` / `case_id` / `opening_id`) must echo it exactly.

2. **Probe + confirm.** `curl -s <remote-env-url>/health` then `/api/summary` to confirm the service is live. Do not save remote data to disk; pipe through `python3 -m json.tool` or a `python3 -c` filter.

3. **Gather evidence in precedence order** (call the endpoints that carry **authoritative** records, not the stale summaries):
   - **Leave entity** -> `/api/payroll-ledgers?q=<EMP-ID>` then filter `record_type == "Leave assignment"` and `period == current`. Also `/api/employees?q=<EMP-ID>` (profile summary — treat as *non-authoritative*), `/api/policies` (LEAVE-SRC-001), `/api/audit?case_id=...` or `/api/audit?q=<EMP-ID>`.
   - **Payroll entity** -> `/api/payroll-ledgers?q=<EMP-ID>` then filter `record_type == "Salary assignment"`. Also `/api/policies` (PAY-SRC-001), `/api/audit?q=<EMP-ID>`.
   - **Case folder + notice** -> `/api/cases/<id>` (approvals, attachments, embedded audit_events, policy_refs), `/api/documents?q=<CASE-ID-or-keyword>` (folder), `/api/messages?q=<CASE-ID>` + `/api/notifications?q=<CASE-ID>` (notices), `/api/audit?case_id=<id>`.
   - **Recruitment** -> `/api/recruitment?q=<OPENING-ID>` (one object with candidates/offer_register/cost_ledger/notice_packets). Cross-check with `/api/cases` + `/api/audit` + `/api/messages` for adjacent notice defects.

4. **Look up the matching policy** in `/api/policies` for the authoritative rule text (Leave Source Precedence, Payroll Assignment Source, Lifecycle Folder Checklist, Remote Work Policy). The policy sections name the exact exclusion + gate rules — quote them mentally to justify each enum.

5. **Apply business rules** (below) to derive each field. Prefer the **authoritative assignment/ledger** over any summary; exclude drafts/superseded; detect folder + notice defects independently of the approval.

6. **Select the audit event** whose `event` and `detail` match the task scope; collect supporting ids and explicitly list any *adjacent* audit events that must be excluded from that scope.

7. **Map every enum/boolean** to the exact normalized label from the answer template's `allowed_values`. No free text in enum fields.

8. **Validate against the pre-submission checklist**, then emit ONE JSON object matching the template. No markdown, no commentary, no extra keys.

## Field definitions & answer shapes

Each task ships an `answer_template.json` whose keys are the fields you must populate. Recurring field families:

- **Identity**: `employee_id` / `case_id` / `opening_id` / `selected_candidate` / `waitlisted_candidates` / `rejected_candidates`.
- **Leave**: `effective_leave_policy` (string = the controlling assignment's `policy_name`), `annual_days` / `balance_days` (int = controlling assignment's `approved_leave_days`), `assignment_id` (the controlling `ledger_id`), `excluded_leave_ids` (list of superseded/draft `ledger_id`s).
- **Payroll**: `payroll_assignment_id` / `salary_assignment_id` (controlling `ledger_id`), `base_salary` (number from controlling salary assignment), `effective_date` (the assignment's `period` / effective date), `excluded_payroll_ids` / `excluded_assignment_id`, `accrual_ready`, `accrual_batch_id`.
- **Folder**: `folder_ready` (bool), `missing_files` (list = `required_files` minus `files`), `required_tag_present` (bool = all `required_tags` in `tags`), `folder_required_tag_action` (`add_required_tag` if a tag missing else `no_tag_action`).
- **Notice**: `notice_quality` (`valid`/`defective` from message `quality`), `notice_defects` (list of defect codes from message `defects`).
- **Approval**: `final_decision`, `approval_authority` (approver), `approval_event_id` (approval_id).
- **Audit**: `audit_event_id`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, `audit_scope`, `audit_result`.
- **Gate / control**: `closeout_action`, `next_action`, `approval_closeout_gate`, `closeout_blockers`, `escalation_action`, `records_remediation_owner`, `notice_remediation_action`, `final_control_result` / `control_result` / `handoff_control_result`.
- **Source labels**: `leave_source`, `leave_precedence_source`, `payroll_source_status`, `payroll_source_status_required`, `draft_exclusion_rule`, `cost_source`, `notice_evidence_source`, `notice_quality_source`, `candidate_status_source`, `candidate_outcome_control`, `evidence_source_order`.

## Business rules

### Leave source precedence
- Authoritative source = the **latest `Approved` (or `Submitted`) leave assignment** for the current period in `/api/payroll-ledgers` (`record_type == "Leave assignment"`).
- `leave_source = "leave_assignment_history"`, `leave_precedence_source = "approved_assignment_current_period"`, `precedence_source = "approved_assignment_over_profile"`.
- **Exclude** every assignment whose status is `Superseded`, `Draft`, voided, or obsolete -> list in `excluded_leave_ids`. Drafts and superseded records never control even if their day count differs.
- **Ignore the employee profile summary** (`leave_balance_days` / any case summary / HRMS leave ledger) when it conflicts with an approved assignment -> `profile_policy_ignored = true`, `audit_result = "profile_summary_stale"`, `next_action = "update_employee_summary"`.
- `effective_leave_policy` = the controlling assignment's `policy_name`; `annual_days`/`balance_days` = its `approved_leave_days` (use `worksheet_leave_days` only if `approved_leave_days` is absent/zero).
- Corroborate via `/api/policies` LEAVE-SRC-001 and the leave-scope audit event.

### Payroll source precedence & accrual
- Authoritative source = the **current `Submitted` salary assignment** in `/api/payroll-ledgers` (`record_type == "Salary assignment"`, status `Submitted`).
- `payroll_source_status = "submitted"`, `payroll_source_status_required = "submitted_after_acceptance"`, `draft_exclusion_rule = "exclude_draft_assignment"`, `draft_payroll_allowed = false`.
- **Exclude** any `Draft` (or `Superseded`) salary assignment -> `excluded_payroll_ids` / `excluded_assignment_id`. Draft planning assignments do not affect payroll readiness or accrual.
- `base_salary` = the submitted assignment's `base_salary`; `effective_date` = its `period` (e.g. `2026-04-01` from period `2026-04`) or `updated_at` date.
- Accrual readiness: `accrual_ready = true` when the submitted salary assignment carries an `accrual_batch_id` matching the accrual batch; `accrual_batch_id` = that value. `control_result = "ready_with_monitoring"`, `audit_scope = "payroll_assignment_readiness"`.
- Corroborate via PAY-SRC-001.

### Folder readiness
- A folder is ready **only if** `ready == true` AND every `required_files` entry is present in `files` AND every `required_tags` entry is present in `tags` (per POL-DOCS-2026). When in doubt, compute the set differences yourself.
- `missing_files = required_files - files`. `required_tag_present = (required_tags ⊆ tags)`.
- `folder_ready = false` if any missing file or missing tag.
- If a required tag is missing -> `folder_required_tag_action = "add_required_tag"`, `closeout_blockers` includes `missing_required_tags`. If only files missing, `folder_required_tag_action = "no_tag_action"` and blocker is `missing_required_files`.

### Formal-notice defect detection
- Inspect the formal notice via `/api/messages?q=<case_id>` (and `/api/notifications`) — read the embedded `quality` and `defects[]`. Do **not** rely on the case summary text alone -> `notice_evidence_source = "notice_packet_inspection"`.
- `notice_quality = "defective"` when message `quality == "defective"` (or any defect listed); else `valid`.
- Defect codes (from message `defects`, corroborated against HR-POL-014 section 7.1 which requires appeal instructions + acknowledgement deadline + tax equalization etc.):
  - `missing_ack_deadline` — acknowledgement deadline absent.
  - `missing_appeal_instructions` — appeal section absent.
  - `missing_waitlist_status` — waitlist candidate notice omits waitlist status.
  - `missing_correct_policy` — notice references a legacy/incorrect policy vs the approved assignment.
- A defective notice -> `closeout_blockers` includes `defective_formal_notice`.

### Approval closeout gate (cross-cutting)
- An **approval is NOT sufficient to close** when either the folder is defective (missing files/tags) or the formal notice is defective. -> `approval_closeout_gate = "approval_not_sufficient_when_folder_or_notice_defective"`, `final_control_result = "hold_for_folder_and_notice_defects"`.
- Only when folder + notice + all records are clean does `approval_closeout_gate = "approval_sufficient_when_records_clean"` and `final_control_result = "approve_closeout"`.
- `final_decision` comes from the case `approvals[]` (e.g. `Approved` + note "with conditions" -> `approved_with_conditions`). `approval_authority` = approval `approver`; `approval_event_id` = approval `approval_id`.
- When blocked: `next_action = "block_close_and_reissue_notice"`, `escalation_action = "open_records_remediation"`, `notice_remediation_action = "reissue_defective_notices"`. When there are no notice defects but only records/folder issues, `notice_remediation_action = "no_notice_action"`.
- `escalation_action` for clean cases = `no_action`.

### Audit event selection
- Pick the audit event whose `event` matches the task **scope**:
  - leave-scope -> `leave.*` (e.g. `leave.profile_mismatch`), `audit_scope = "leave_source_precedence_only"`.
  - payroll/accrual -> `payroll.*` (e.g. `payroll.ready`, `payroll.draft_excluded`), `audit_scope = "payroll_assignment_readiness"`.
  - folder/notice -> `notice.defect` / `folder.tag_missing` / `case.close_blocked`, `audit_scope = "document_notice_findings_only"`.
- `supporting_audit_event_ids = [the chosen event]`. Any adjacent audit event **outside the scope** (e.g. a `folder.tag_missing` event when the task is leave-precedence) goes in `excluded_audit_event_ids` — do not let it influence the in-scope decision.
- `cross_module.escalation_package` events are navigational (they list related event ids); do not select them as the single scope event and exclude them from single-scope supporting lists.
- `audit_result` mirrors the audit detail when it states a QA verdict: `profile_summary_stale`, `ready_with_monitoring`, `block_close`.

### Escalation owner
- Records issues (missing files / missing tags / folder not ready) -> `Records`.
- Payroll draft-exclusion / accrual issues -> `Payroll QA`.
- Cross-module / combined lifecycle risk -> `People Ops Compliance`.

### Recruitment reconciliation
- `/api/recruitment?q=<opening_id>` returns one object. Reconstruct outcomes from `candidates[]` + `offer_register[]`:
  - `selected_candidate` = candidate with `committee_decision == "Selected"`.
  - `waitlisted_candidates` = those with `committee_decision == "Waitlisted"`.
  - `rejected_candidates` = those with `committee_decision == "Rejected"`.
  - Arrays contain **candidate IDs only**.
- Offer: from `offer_register` where `candidate_id == selected` -> `offer_id`, `offer_base_salary`, `selected_offer_status = "accepted"` (read the literal status).
- Cost: `recruitment_cost_total = sum(amount)` over **all** `cost_ledger` lines; `cost_source = "recruitment_cost_ledger"`.
- Notice follow-up: `notice_followup_required` = candidate IDs from `notice_packets[]` where `status == "not_sent"`. Their `required_action` -> `waitlisted_followup_action` / `rejected_followup_action` (e.g. `send_waitlist_notice`, `send_rejection_notice`).
- Candidate status source: `interview_feedback_and_offer` (committee decision cross-checked with offer register), `candidate_outcome_control = "committee_decision_with_offer_confirmation"`, `notice_quality_source = "notice_packet_inspection"`.
- Payroll handoff gate: created only after the selected candidate has an **accepted** offer; the assignment must then be **submitted** -> `onboarding_handoff = "create_payroll_precheck"`, `payroll_handoff_gate = "accepted_offer_only"`, `payroll_assignment_status_required = "submitted_after_acceptance"`, `draft_payroll_allowed = false`, `handoff_control_result = "submitted_handoff_required_after_acceptance"`.
- Waitlisted candidates have no accepted offer -> `offer_exclusion_reason_for_waitlisted = "no_accepted_status_or_offer"`.

## Common misjudgments & exclusion rules
- **Stale profile summary** — do not take `employee.leave_balance_days` or a case `summary` as the leave policy of record when an approved current-period assignment exists. Always prefer the assignment ledger.
- **Draft assignments** — never selected for leave or payroll; always moved to the excluded list. Status `Draft` is excluded even when its day/salary number is larger.
- **Superseded assignments** — excluded from leave (still list in `excluded_leave_ids`).
- **Missing tags treated as cosmetic** — a missing required tag is a hard `closeout_blocker` (`missing_required_tags`); folder_ready is false.
- **Missing ack/appeal treated as formality** — accept the message's `defects[]` verbatim; each maps to a blocker `defective_formal_notice`.
- **Approval treated as closeout** — an "Approved" case is still **blocked** if folder or notice is defective. The gate is records-driven, not approval-driven.
- **Audit scope leakage** — an adjacent folder/notice audit event must NOT anchor a leave-precedence answer (and vice versa). Move it to `excluded_audit_event_ids`.
- **Case summary-only notice judgment** — always inspect the actual message/notice packet; summaries can hide defects.
- **Free-text enums** — every enum/list-of-enum field must use a label from the template `allowed_values`; off-label synonyms fail.
- **Extra keys / markdown** — emit exactly the template keys as one bare JSON object; no leading/trailing prose.
- **Cost from summary** — sum the `cost_ledger` lines yourself; never read a precomputed cost from a summary.
- **Waitlisted offered** — waitlisted candidates have no accepted offer and no payroll handoff; only the selected candidate does.

## Pre-submission checklist
1. Identity field (`employee_id`/`case_id`/`opening_id`) matches the prompt entity exactly.
2. Leave answer sourced from an **Approved/Submitted current-period Leave assignment**; drafts/superseded listed in excluded.
3. Payroll answer sourced from a **Submitted** Salary assignment; draft(s) listed in excluded; `accrual_batch_id` copied from it.
4. Folder: `missing_files` = required − present; `required_tag_present` computed from tag set; `folder_required_tag_action` set accordingly.
5. Notice: `notice_defects` copied from the message `defects[]`; `notice_quality` matches.
6. `approval_closeout_gate` is `..._not_sufficient...` iff any blocker exists; `final_control_result` is `hold_for_folder_and_notice_defects` iff blocker.
7. Audit: chosen event's scope matches task scope; out-of-scope events in `excluded_audit_event_ids`; `audit_scope` enum matches scope.
8. Recruitment: cost = sum of all ledger lines; arrays are candidate IDs only; handoff gate = accepted offer + submitted assignment; `draft_payroll_allowed = false`.
9. Every enum/boolean field uses an exact template `allowed_values` label — no synonyms, no free text.
10. Output is a single bare JSON object with exactly the template keys; no markdown fences, no commentary.
