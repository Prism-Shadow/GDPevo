# PeopleOps Console — API map, field map, and enum vocabulary

This is the detailed reference for the PeopleOps Console review skill. Read it when
you need the exact endpoint shapes, how raw record fields map onto answer-template
enum labels, or the full normalized vocabulary. The main SKILL.md covers the
procedure and the judgment rules; this file is the lookup table.

The base URL is given in `environment_access.md` in the task directory. Confirm the
service is up with `GET /health` before doing anything else. The JSON API needs no
auth; the login in the prompt is for the web UI only — ignore it and use the API.

---

## 1. Endpoint map

All are GET. `q` is a case-insensitive substring match against any scalar field on
that resource, so you can search by an entity ID, a name, or a linked ID.

| Endpoint | Returns | Use it to |
|---|---|---|
| `GET /health` | `{ok, service}` | confirm reachability first |
| `GET /api/summary` | counts, cases-by-status | orient only; do not enumerate |
| `GET /api/employees?q=<id>` | employee summary rows | confirm the named employee, read department/manager/status |
| `GET /api/cases/<case_id>` | full case: approvals, attachments, audit_events, comments, policy_refs, owner, status | one-stop detail for a case; audit_events are embedded here too |
| `GET /api/cases?q=<id>` | case summary rows | find the case linked to an opening/employee |
| `GET /api/payroll-ledgers?q=<emp_id>` | leave assignments AND salary assignments for that employee | the authoritative store for both leave and payroll records |
| `GET /api/recruitment?q=<opening_id>` | one opening object: candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records | the whole recruitment packet in one call |
| `GET /api/documents?q=<case_id>` | document folder(s): files, required_files, required_tags, tags, ready | folder-readiness set comparison |
| `GET /api/messages?q=<case_id>` | lifecycle notices/messages: quality, defects[], status | formal-notice quality + defect codes |
| `GET /api/notifications?q=<case_id>` | notification records (often mirror messages) | secondary notice evidence |
| `GET /api/audit?case_id=<case_id>` or `GET /api/audit/<audit_id>` | audit events: event, detail, actor, source | controlling/supporting audit event + its verbatim result |
| `GET /api/policies?q=<policy_id>` | policy sections (heading, body) | read the governing rule in its own words |
| `GET /api/attachments/<attachment_id>` | raw attachment text | drill into a checklist/notice attachment |

There is **no** `/api/employees/<id>` or `/api/payroll-ledgers/<id>` detail route —
those return `{"error":"not_found"}`. Get per-employee records through
`/api/payroll-ledgers?q=<emp_id>` and per-case records through `/api/cases/<case_id>`.

**Anti-fishing discipline:** always pass a precise `q=` / `case_id=` filter tied to
the entity named in the task. Do not call a list endpoint bare to browse unrelated
entities.

---

## 2. Record-store field map

### payroll-ledgers rows (mixed store)
Each row has `ledger_id`, `employee_id`, `record_type`, `status`, `period`,
`updated_at`, plus type-specific fields.

- **Leave assignment** (`record_type == "Leave assignment"`): `policy_name`,
  `approved_leave_days`, `worksheet_leave_days`. This is the authoritative leave
  record type. `policy_name` -> effective_leave_policy; `approved_leave_days` ->
  annual_days / balance_days.
- **Salary assignment** (`record_type == "Salary assignment"`): `base_salary`,
  `accrual_batch_id` (when relevant). `ledger_id` -> payroll/salary assignment id;
  `base_salary` -> base_salary; the date portion of `updated_at` -> effective_date
  (it lines up with the assignment's `period`, e.g. an `updated_at` of
  `<YYYY-MM-DD>T<hh:mm>` for period `<YYYY-MM>` yields effective_date `<YYYY-MM-DD>`).
- **HRMS leave ledger / People Ops adjustment**: raw movement/adjustment rows.
  These are NOT the controlling assignment. Do not pick their `ledger_id` as the
  authoritative assignment and do not use their day counts as the entitlement.

`status` values seen: `Approved`, `Submitted`, `Superseded`, `Draft`. These map to
template enums in lowercase (`submitted`/`draft`/`superseded`). An Approved leave
**assignment** is the controlling source for leave; a Submitted salary
**assignment** is the controlling source for payroll.

### cases/<id>
`approvals[]` -> `{approval_id, approver, decision, step, note}`. The final/decision
approval gives approval_authority (`approver`) and approval_event_id (`approval_id`).
`audit_events[]` are embedded copies of the audit rows. `policy_refs[]` point to
governing policies. `owner`, `department`, `status`, `summary` give context.

### recruitment/<opening>
- `candidates[]`: `{candidate_id, committee_decision, notice_status, ...}`.
  `committee_decision` in {`Selected`, `Waitlisted`, `Rejected`} is the authoritative
  outcome -> selected/waitlisted/rejected arrays.
- `offer_register[]`: `{offer_id, candidate_id, base_salary, status}`. `status` in
  {`accepted`, `draft`, `withdrawn`}. Only an `accepted` offer for the Selected
  candidate is the live offer.
- `cost_ledger[]`: `{line_id, label, amount}`. recruitment_cost_total = sum of every
  `amount`.
- `notice_packets[]`: `{candidate_id, notice_type, status, required_action}`. Packets
  with `status == "not_sent"` -> follow-up required for that candidate, and
  `required_action` is the normalized follow-up action.
- `payroll_precheck_records[]`: empty means the post-acceptance handoff still needs to
  be created.

### documents
`{required_files[], files[], required_tags[], tags[], ready}`. Compute readiness as a
set comparison (see SKILL.md), do not just trust the `ready` flag — report the exact
missing members.

### messages / notifications (formal notices)
`{message_id, case_id, quality, defects[], status, recipient, subject, body}`.
`quality` in {`valid`, `defective`}. `defects[]` already hold normalized defect codes.

### audit/<id>
`{audit_id, case_id, employee_id, event, detail, actor, source, timestamp}`. The
`event` namespace (prefix before the dot) classifies scope:
`leave.*` (e.g. `leave.profile_mismatch`), `payroll.*` (e.g. `payroll.ready`),
`folder.*` / `notice.*` (e.g. `folder.tag_missing`, `notice.defect`). The `detail`
text frequently contains a `QA result: <label>` clause whose label is the normalized
audit/control result to report verbatim, plus the controlling record id.

### policies/<id>
`{policy_id, title, owner, sections[]}` with `sections[] = {heading, body}`. Read the
relevant section's `body` for the governing rule in its own words (e.g. submitted
salary controls; draft prechecks do not satisfy the handoff gate; latest
approved/submitted leave assignment controls over a stale profile). Report any
owner/SLA/escalation values by reading them verbatim — never invent them.

---

## 3. Enum vocabulary (the output contract)

These labels come from the train answer templates' `allowed_values`. They are the
only fixed vocabulary; use them verbatim and let each task's own template be the
source of truth for which fields and which subset apply.

**Leave source / precedence**
- leave_source: `leave_assignment_history`, `employee_profile_summary`, `case_summary_only`
- leave_precedence_source: `approved_assignment_current_period`, `profile_summary_current_period`, `case_summary_only`
- precedence_source: `approved_assignment_over_profile`, `employee_profile_summary`, `case_summary_only`

**Payroll source / draft handling**
- payroll_status / payroll_source_status: `submitted`, `draft`, `superseded`
- draft_exclusion_rule: `exclude_draft_assignment`, `draft_allowed`, `exclude_superseded_only`
- payroll_assignment_status_required: `submitted_after_acceptance`, `submitted`, `draft_allowed`
- payroll_handoff_gate: `accepted_offer_only`, `accepted_offer_and_submitted_assignment`, `all_interviewed_candidates`

**Folder / notice**
- notice_quality: `valid`, `defective`
- notice_defects: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`
- closeout_blockers: `missing_required_files`, `missing_required_tags`, `defective_formal_notice`
- folder_required_tag_action: `no_tag_action`, `add_required_tag`
- notice_evidence_source / notice_quality_source: `notice_packet_inspection`, `message_notice_inspection`, `case_summary_only`
- notice_remediation_action: `reissue_defective_notices`, `no_notice_action`, `send_new_offer_notice`

**Audit scope**
- audit_scope: `document_notice_findings_only`, `leave_source_precedence_only`, `payroll_assignment_readiness`
- audit_result: `profile_summary_stale`, `ready_with_monitoring`, `block_close`

**Decisions / gates / results**
- final_decision: `approved_with_conditions`, `approved`, `rejected`, `held`
- approval_closeout_gate: `approval_sufficient_when_records_clean`, `approval_not_sufficient_when_folder_or_notice_defective`
- evidence_source_order: `approval_history_folder_notice_audit`, `folder_notice_audit`, `audit_only`
- closeout_action / next_action / escalation_action: `approve_onboarding_close`, `block_close_and_reissue_notice`, `open_records_remediation`, `no_action` (subset per template)
- final_control_result / control_result: `approve_closeout`, `hold_for_folder_and_notice_defects`, `ready_with_monitoring`

**Recruitment outcomes / handoff**
- candidate_status_source: `interview_feedback_and_offer`, `case_summary_only`, `message_only`
- candidate_outcome_control: `committee_decision_with_offer_confirmation`, `message_status_only`, `case_summary_only`
- selected_offer_status: `accepted`, `draft`, `withdrawn`, `none`
- cost_source: `recruitment_cost_ledger`, `case_summary_only`
- onboarding_handoff: `create_payroll_precheck`, `create_submitted_assignment_after_acceptance`, `no_payroll_handoff`
- handoff_control_result: `submitted_handoff_required_after_acceptance`, `submitted_handoff_required`, `no_handoff_required`
- waitlisted_followup_action: `send_waitlist_notice`, `reissue_waitlist_notice_not_rejection`, `no_action`
- rejected_followup_action: `send_rejection_notice`, `no_action`, `reissue_rejection_notice`
- offer_exclusion_reason_for_waitlisted: `no_accepted_status_or_offer`, `waitlisted_not_selected`, `already_rejected`

**Remediation owner** (read from the case/audit package; do not assume)
- records_remediation_owner: `Records`, `People Ops Compliance`, `Payroll QA`

> Note: many fields share the same option pool but are offered in a different ORDER
> across templates. Order in `allowed_values` is not significance — always read the
> specific task's template to know which fields exist and which options are permitted
> for each, then choose by the rules, not by position.
