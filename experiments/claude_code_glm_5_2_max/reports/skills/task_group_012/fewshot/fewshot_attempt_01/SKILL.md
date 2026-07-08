---
name: northwind-people-lifecycle-closeout
description: Verify People Ops employee-lifecycle closeouts (leave/payroll precedence, folder readiness, formal-notice quality, audit-scope selection, recruitment reconciliation) against the remote Northwind PeopleOps Console read-only JSON API. Use whenever a task asks to validate/audit/reconcile an onboarding closeout, leave source precedence, payroll assignment readiness, policy-case folder+notice, or recruitment outcome packet.
---

# Northwind People-Lifecycle Closeout Verification

## When to use
Use for any task that points at the PeopleOps Console / "Northwind People Lifecycle Portal" and asks to verify, audit, or reconcile an HR lifecycle closeout. Five archetypes map to five answer shapes:
1. **Leave + payroll onboarding closeout** (employee-level, records-clean check).
2. **Policy-case folder readiness + formal-notice quality** (case-level, defect/blocker check).
3. **Leave source-precedence validation** (approved assignment vs stale profile summary).
4. **Payroll assignment + accrual readiness** (submitted vs draft assignment).
5. **Recruitment outcome reconciliation** (candidate outcomes, cost sum, notice follow-up, payroll handoff).

## Environment
- Web UI: <remote-env-url>/  (login `ops.lead@peopleops.local / PeopleOps#2026` is illustrative; not needed for API).
- JSON API base: `<remote-env-url>` — read-only, **no auth**. Health: `GET /health`.
- The prompt's `http://127.0.0.1:<port>/` refers to THIS remote host. Always use `<remote-env-url>`.
- Do NOT save remote data to files; curl and inspect in the shell only.

### Endpoints (all GET)
| Endpoint | Carries |
|---|---|
| `/api/manifest` | module/endpoint map + dataset seed |
| `/api/summary` | live record counts + departments |
| `/api/employees?q=&status=` | employee records (scalar profile + `leave_balance_days`) |
| `/api/cases?q=&status=&type=` | case summaries |
| `/api/cases/<case_id>` | **FULL** case: `approvals[]`, `attachments[]`, `audit_events[]`, `comments[]`, `policy_refs[]`, status, owner, summary |
| `/api/policies` , `/api/policies/<id>` | policy sections (what a valid notice/folder must contain) |
| `/api/payroll-ledgers?q=&status=&type=` | **combined ledger** of `record_type`: `Leave assignment`, `Salary assignment`, `Payroll worksheet`, `HRMS leave ledger`, `People Ops adjustment` |
| `/api/recruitment?q=` | openings: `candidates[]`, `offer_register[]`, `cost_ledger[]`, `notice_packets[]`, `payroll_precheck_records[]` |
| `/api/documents?q=` | lifecycle folders: `files[]`, `required_files[]`, `required_tags[]`, `tags[]`, `ready` |
| `/api/messages?q=` | formal notices: `recipient`, `status`, `quality` (valid/defective), `defects[]`, `body`, `subject` |
| `/api/notifications?q=` | notifications (same shape as messages) |
| `/api/audit?q=&case_id=` | audit events: `audit_id`, `case_id`, `employee_id`, `event`, `detail`, `actor`, `timestamp` |
| `/api/audit/<audit_id>` | single audit event detail |
| `/api/attachments/<attachment_id>` | attachment text content (follow from case `attachments[]`) |

**Critical shape fact:** leave assignments and salary assignments are NOT separate endpoints — they both live in `/api/payroll-ledgers` distinguished by `record_type` (`Leave assignment` / `Salary assignment`). Fetch with `?q=<EMP-id>` then filter by `record_type`.

## Endpoint calling order (gather evidence)
1. Identify the subject: an `EMP-xxx`, a `CASE-xxx` / `REQ-xxx`, or a `DOC-xxx`.
2. `/api/employees?q=<EMP>` → profile summary (name, status, `leave_balance_days`, salary_band) — the *possibly stale* summary.
3. `/api/payroll-ledgers?q=<EMP>` → leave + salary assignments. Filter by `record_type`.
4. If a case exists: `/api/cases/<case_id>` → approvals, attachments, audit_events, comments, policy_refs. (Case IDs are reused as `CASE-<emp-suffix>` and recruitment opening IDs `REQ-xxx` are also cases.)
5. `/api/documents?q=<DOC-or-EMP-or-case-token>` → folder readiness. Document IDs follow `DOC-<case-or-emp-tag>`.
6. `/api/messages?case_id=<case>` (or `/api/messages?q=`) → formal notice quality + defects.
7. `/api/audit?case_id=<case>` (and `/api/audit?q=<EMP>`) → audit events; call `/api/audit/<id>` for full detail text.
8. `/api/policies/<policy_id>` (from case `policy_refs`) → confirms what a valid notice/folder must contain (e.g. exception notices need appeal instructions + acknowledgement deadline; onboarding folders need specific files).
9. For recruitment: `/api/recruitment?q=<REQ-id>` → candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records.

## Field shapes you will read
- **Leave assignment** record: `ledger_id` (LA-…), `policy_name`, `period` (e.g. "2026"), `status` (`Approved`/`Superseded`/`Draft`), `approved_leave_days`, `worksheet_leave_days`, `updated_at`.
- **Salary assignment** record: `ledger_id` (PAY-…), `base_salary`, `period` (e.g. "2026-04"), `status` (`Submitted`/`Draft`/`Superseded`), `accrual_batch_id` (sometimes), `updated_at`.
- **Document folder**: `document_id`, `ready` (bool), `files[]`, `required_files[]`, `required_tags[]`, `tags[]`.
- **Message/notice**: `message_id`, `case_id`, `recipient`, `status`, `quality` (`valid`/`defective`), `defects[]`, `body`, `subject`.
- **Audit event**: `audit_id`, `case_id`, `employee_id`, `event` (e.g. `leave.profile_mismatch`, `payroll.ready`, `notice.defect`, `folder.tag_missing`, `case.close_blocked`, `cross_module.escalation_package`), `detail` (often contains `QA result: <label>`), `actor`.
- **Case detail**: `case_id`, `case_type`, `status`, `summary`, `owner`, `approvals[]` (`approval_id`, `approver`, `decision`, `step`, `decided_at`), `attachments[]` (`attachment_id`, `name`, `kind`, `status`), `audit_events[]`, `comments[]`, `policy_refs[]`.
- **Recruitment opening**: `opening_id`, `candidates[]` (`candidate_id`, `committee_decision` Selected/Waitlisted/Rejected, `notice_status`, `rounds[]`), `offer_register[]` (`offer_id`, `candidate_id`, `base_salary`, `status` accepted/draft/withdrawn), `cost_ledger[]` (`line_id`, `label`, `amount`), `notice_packets[]` (`candidate_id`, `notice_type`, `required_action`, `status`, optional `defects`/`quality`), `payroll_precheck_records[]`.

## Business rules

### Leave source precedence
- Candidate = the `Leave assignment` with `status == "Approved"` whose `period` matches the current/effective period (e.g. "2026"). Among multiple Approved same-period, take the latest `updated_at`.
- `annual_days` / `balance_days` = that assignment's `approved_leave_days` (NOT the employee profile `leave_balance_days`).
- Exclude every other leave assignment (status `Superseded`, `Draft`, or older period) — list them in `excluded_leave_ids`.
- `leave_source = "leave_assignment_history"`; `leave_precedence_source = "approved_assignment_current_period"`.
- If the profile summary (`leave_balance_days` / profile policy) conflicts with the approved assignment, the profile is STALE: `precedence_source = "approved_assignment_over_profile"`, `profile_policy_ignored = true`, `audit_result = "profile_summary_stale"`, `next_action = "update_employee_summary"`.

### Payroll source precedence
- Candidate = the `Salary assignment` with `status == "Submitted"` for the current/effective period.
- `base_salary` from that record. `effective_date` = the assignment's period (`YYYY-MM`) rendered as `YYYY-MM-01` (or an explicit effective_date field if present).
- Exclude `Draft` and `Superseded` assignments → `excluded_assignment_id` / `excluded_payroll_ids`.
- `payroll_source_status = "submitted"`; `draft_exclusion_rule = "exclude_draft_assignment"`.
- `accrual_ready = true` only if a Submitted assignment carries a matching `accrual_batch_id` (and the payroll audit confirms `payroll.ready`); the accrual batch id = that `accrual_batch_id`.
- `control_result = "ready_with_monitoring"` when submitted assignment matches an accrual batch (ready, but monitored). `block_close`/`hold_for_folder_and_notice_defects` when defective.

### Folder readiness (from `/api/documents`)
- `missing_files = required_files − files`.
- `required_tag_present = (required_tags ⊆ tags)`.
- `folder_ready = (missing_files empty) AND required_tag_present AND documents.ready == true`.
- `folder_required_tag_action = "add_required_tag"` if any required tag missing, else `"no_tag_action"`.
- Contributes to `closeout_blockers`: `"missing_required_files"` (if missing_files non-empty), `"missing_required_tags"` (if tag missing).

### Formal-notice defect detection (from `/api/messages` or recruitment `notice_packets`)
- `notice_quality = message.quality` (`valid` / `defective`). `notice_defects = message.defects[]`.
- Defect enum space: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- Policy context (e.g. HR-POL-014 §7.1) defines what a valid exception notice MUST contain (executive approval, time limits, tax equalization, VPN-only, quarterly review, **appeal instructions**, **acknowledgement deadline**) — use it to sanity-check defects; the authoritative defects are the pre-computed `defects[]` array.
- `notice_evidence_source = "notice_packet_inspection"` when a structured notice record with explicit `quality`/`defects` fields is inspected. Use `"message_notice_inspection"` only when evidence is a raw message channel without a structured packet, `"case_summary_only"` as last resort.
- If `notice_quality == "defective"` → add `"defective_formal_notice"` to `closeout_blockers`.

### Audit selection (scope-based)
Choose `audit_scope` by archetype:
- folder/notice case → `document_notice_findings_only`
- leave-precedence case → `leave_source_precedence_only`
- payroll-readiness case → `payroll_assignment_readiness`

Map audit `event` prefix to scope:
- `leave.*` → leave scope
- `notice.defect`, `folder.*`, `case.close_blocked` → document/notice scope
- `payroll.*` → payroll scope

Rules:
- `supporting_audit_event_ids` = audit events whose event-type belongs to the chosen scope for this case/employee.
- `excluded_audit_event_ids` = adjacent audit events whose event-type belongs to a DIFFERENT scope (e.g. when scope is leave, exclude `folder.tag_missing` / `notice.defect` / `payroll.*` events). Use `[]` when none.
- `audit_event_id` (single primary) = the in-scope audit event for this case (usually the one whose `detail` carries `QA result: <label>`).
- Derive `audit_result` / `control_result` from the `detail` text `QA result: <X>` if present; else infer: `leave.profile_mismatch`→`profile_summary_stale`; `payroll.ready`→`ready_with_monitoring`; `case.close_blocked`→`block_close`; `notice.defect`→ defective/hold.

### Approval closeout gate (THE key decision)
- **Clean** (folder ready AND notice valid AND records approved/submitted, no draft selected):
  `approval_closeout_gate = "approval_sufficient_when_records_clean"`, `final_control_result = "approve_closeout"`, `closeout_action / next_action = "approve_onboarding_close"`.
- **Defective** (folder missing files/tags OR notice defective):
  `approval_closeout_gate = "approval_not_sufficient_when_folder_or_notice_defective"`, `final_control_result = "hold_for_folder_and_notice_defects"`, `next_action = "block_close_and_reissue_notice"`.
- A case **approval existing is NOT sufficient** when the folder or notice is defective — the gate blocks closeout regardless of approval. This is the most common misjudgment.
- `ready_with_monitoring` is an intermediate result (records OK but a follow-up needed, e.g. update stale profile); it is neither full approve nor hold.

### Escalation & remediation owners
- `escalation_action`: `"open_records_remediation"` when a folder/file/task defect exists; `"block_close_and_reissue_notice"` when only a notice defect; `"no_action"` when clean.
- `records_remediation_owner`: `"Records"` for folder/file defects; `"People Ops Compliance"` for notice/policy-compliance defects; `"Payroll QA"` for payroll-assignment defects.
- `notice_remediation_action`: `"reissue_defective_notices"` when notice defective; `"send_new_offer_notice"` when a new offer notice is required; `"no_notice_action"` when clean.
- `evidence_source_order`: `"approval_history_folder_notice_audit"` when the full chain (approval history → folder → notice → audit) is inspected (typical for folder/notice cases); `"folder_notice_audit"` when no approval history; `"audit_only"` last resort.

### Recruitment cost-summing
- `recruitment_cost_total` = **sum of every `cost_ledger[].amount`** across ALL line items (do not skip any line, do not use the case summary's number). `cost_source = "recruitment_cost_ledger"`.

### Candidate outcome reconstruction
- `selected_candidate` = candidate with `committee_decision == "Selected"` AND an `offer_register` entry with `status == "accepted"`.
- `waitlisted_candidates` = `committee_decision == "Waitlisted"` (IDs only).
- `rejected_candidates` = `committee_decision == "Rejected"` (IDs only).
- `candidate_status_source = "interview_feedback_and_offer"`; `candidate_outcome_control = "committee_decision_with_offer_confirmation"`.
- `selected_offer_status` = the selected candidate's offer status (`accepted`/`draft`/`withdrawn`/`none`).
- `offer_id`, `offer_base_salary` from the selected candidate's offer_register entry.
- `notice_followup_required` = candidates whose notice is not properly delivered (notice_status like "Notice not sent"/"not_sent", or notice_packets `status == "not_sent"`) — typically the waitlisted + rejected candidates needing notices. The selected (offer-accepted) candidate is NOT in this list.
- `waitlisted_followup_action = "send_waitlist_notice"` (or `"reissue_waitlist_notice_not_rejection"` if a defective waitlist notice was mistakenly sent as a rejection).
- `rejected_followup_action = "send_rejection_notice"` (or `"reissue_rejection_notice"` if a defective rejection notice exists).
- `notice_quality_source = "notice_packet_inspection"` (inspect recruitment `notice_packets[]`).

### Payroll handoff gate (recruitment → onboarding)
- `payroll_handoff_gate = "accepted_offer_only"` (only the accepted-offer candidate proceeds to payroll).
- `payroll_assignment_status_required = "submitted_after_acceptance"`; `draft_payroll_allowed = false`.
- `onboarding_handoff`:
  - `"create_payroll_precheck"` when an offer is accepted but no submitted payroll assignment exists yet (`payroll_precheck_records` empty / no submitted assignment).
  - `"create_submitted_assignment_after_acceptance"` when a submitted assignment already exists.
  - `"no_payroll_handoff"` when no accepted offer.
- `handoff_control_result = "submitted_handoff_required_after_acceptance"` (accepted offer, assignment not yet submitted) / `"submitted_handoff_required"` (assignment submitted) / `"no_handoff_required"`.
- `offer_exclusion_reason_for_waitlisted = "no_accepted_status_or_offer"` (waitlisted candidates are excluded from offer/payroll because they have no accepted status or offer).

## Answer field definitions (produce these, exact enum labels from each task's `answer_template.json`)
Always emit JSON matching the provided `answer_template.json` — every field the template lists, using ONLY `allowed_values` for enum fields. Key fields by archetype:
- **Leave+payroll closeout**: `employee_id`, `effective_leave_policy`, `leave_source`, `annual_days`, `assignment_id`, `excluded_leave_ids[]`, `payroll_assignment_id`, `base_salary`, `payroll_status`, `excluded_payroll_ids[]`, `closeout_action`, `leave_precedence_source`, `payroll_source_status`, `approval_closeout_gate`, `final_control_result`.
- **Folder+notice case**: `case_id`, `final_decision`, `approval_authority`, `approval_event_id`, `folder_ready`, `missing_files[]`, `required_tag_present`, `notice_quality`, `notice_defects[]`, `audit_event_id`, `supporting_audit_event_ids[]`, `excluded_audit_event_ids[]`, `audit_scope`, `next_action`, `approval_closeout_gate`, `closeout_blockers[]`, `evidence_source_order`, `folder_required_tag_action`, `notice_evidence_source`, `escalation_action`, `records_remediation_owner`, `notice_remediation_action`, `final_control_result`.
  - `approval_event_id` = the `approval_id` of the FINAL approval step; `approval_authority` = its `approver`; `final_decision` from case status/summary/approval decision.
- **Leave precedence**: `employee_id`, `effective_leave_policy`, `assignment_id`, `balance_days`, `precedence_source`, `profile_policy_ignored`, `audit_event_id`, `audit_result`, `next_action`, `leave_precedence_source`, `supporting_audit_event_ids[]`, `excluded_audit_event_ids[]`, `audit_scope`.
- **Payroll readiness**: `employee_id`, `salary_assignment_id`, `base_salary`, `effective_date`, `excluded_assignment_id`, `accrual_ready`, `accrual_batch_id`, `audit_event_id`, `control_result`, `payroll_source_status`, `draft_exclusion_rule`, `audit_scope`.
- **Recruitment**: `opening_id`, `selected_candidate`, `waitlisted_candidates[]`, `rejected_candidates[]`, `offer_id`, `offer_base_salary`, `recruitment_cost_total`, `notice_followup_required[]`, `onboarding_handoff`, `candidate_status_source`, `candidate_outcome_control`, `selected_offer_status`, `cost_source`, `notice_quality_source`, `waitlisted_followup_action`, `rejected_followup_action`, `payroll_handoff_gate`, `payroll_assignment_status_required`, `draft_payroll_allowed`, `offer_exclusion_reason_for_waitlisted`, `handoff_control_result`.

## Common misjudgments / exclusion rules (DO NOT)
- Do NOT pick a `Draft` (or `Superseded`) leave/salary assignment even if it shows more days / higher salary. Always pick Approved/Submitted current-period; list drafts+superseded in the `excluded_*` fields.
- Do NOT trust the employee profile `leave_balance_days` or profile policy over an approved leave assignment — the profile can be stale.
- Do NOT treat an existing case approval as sufficient for closeout when the folder is missing files or the notice is defective (the approval-closeout gate blocks closeout).
- Do NOT put adjacent-scope audit events in `supporting_audit_event_ids`; move them to `excluded_audit_event_ids` (e.g. `folder.tag_missing` excluded from a leave-scope decision).
- Do NOT sum only some cost lines — `recruitment_cost_total` is the sum of ALL `cost_ledger` amounts; never use a summary-stated total.
- Do NOT include the selected (offer-accepted) candidate in `notice_followup_required`; follow-up = waitlisted + rejected needing notices.
- Do NOT reissue a waitlist notice as a rejection (or vice versa): waitlist → waitlist notice, rejection → rejection notice.
- Do NOT allow draft payroll for onboarding handoff (`draft_payroll_allowed` is `false`).
- Do NOT return candidate objects in arrays — arrays must contain candidate IDs (strings) only.
- Do NOT add markdown or explanatory text — return ONLY the JSON object matching the template.
- Do NOT invent enum labels — use exactly the strings in the template's `allowed_values`.

## Pre-submission checklist
- [ ] Every field in the task's `answer_template.json` is present; no extra fields.
- [ ] Every enum value matches an `allowed_values` entry exactly (case-sensitive).
- [ ] All IDs are exact strings copied from the API (case-sensitive: `EMP-`, `CASE-`, `LA-`, `PAY-`, `AUD-`, `DOC-`, `REQ-`, `CAND-`, `OFFER-`).
- [ ] Arrays contain only strings (IDs) where the template says `list[string]`; empty arrays `[]` when none (e.g. `excluded_audit_event_ids`).
- [ ] Numbers are JSON numbers: `base_salary`/`offer_base_salary`/`recruitment_cost_total` as number; `annual_days`/`balance_days` as integer.
- [ ] Leave: Approved current-period assignment selected; Draft+Superseded listed in `excluded_leave_ids`; `annual_days` from the selected assignment.
- [ ] Payroll: Submitted assignment selected; Draft excluded and named in `excluded_payroll_ids`/`excluded_assignment_id`; `payroll_source_status="submitted"`.
- [ ] Folder: `missing_files = required_files − files`; `required_tag_present` correct; `folder_ready` consistent.
- [ ] Notice: `notice_defects` exactly matches `message.defects[]`; `notice_quality` matches.
- [ ] Audit: `supporting`/`excluded` split correctly by scope; `audit_event_id` is the in-scope event; `audit_scope` matches archetype.
- [ ] Gate logic: folder-or-notice defective ⇒ `approval_not_sufficient_when_folder_or_notice_defective` + `hold_for_folder_and_notice_defects`; clean ⇒ `approval_sufficient_when_records_clean` + `approve_closeout`.
- [ ] Recruitment: `recruitment_cost_total` = sum of all cost lines; candidate arrays are IDs only; `draft_payroll_allowed=false`; handoff fields consistent with accepted-offer-only gate.
- [ ] `effective_date` formatted `YYYY-MM-DD`.
- [ ] Output is a single bare JSON object — no markdown fences, no commentary.
