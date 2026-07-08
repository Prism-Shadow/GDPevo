---
name: hr-lifecycle-clearance-audit
description: Solve HR employee-lifecycle clearance/audit tasks against the remote Northwind PeopleOps read-only JSON API. Use when a task asks you to inspect leave assignments, payroll/accrual readiness, policy-case folder+notice defects, recruitment handoff, or audit closeout, and return a structured JSON answer.
---

# HR Lifecycle Clearance/Audit Skill

## When to use
Use this skill for any task that asks you to act as an HR control reviewer over the Northwind People Lifecycle Portal (remote PeopleOps console). Signals: a prompt names an employee ID (`EMP-###`), a policy case ID (`CASE-...`), a recruitment opening (`REQ-...`), or a candidate ID, and asks you to return structured fields like leave policy, payroll status, folder readiness, notice defects, audit event, approval closeout gate, or final control result as JSON matching a template.

## Environment contract
- Web UI: `<remote-env-url>/` (Northwind People Lifecycle Portal). The prompt's `http://127.0.0.1:<port>/` and login `ops.lead@peopleops.local / PeopleOps#2026` point at THIS remote host. Credentials are illustrative; no auth is needed.
- JSON API base: `<remote-env-url>` (read-only, no auth). Always use this base.
- Health: `GET /health` -> `{"ok": true, ...}`. Probe it first if a call hangs.
- Use `curl -s --max-time 20 "<base>/api/..."` and pipe through `python3 -m json.tool`. Do NOT save remote data to disk.

### Endpoints (GET), in the order you typically need them
| Endpoint | Returns | Use for |
|---|---|---|
| `/api/manifest` | module/endpoint map, file counts, seed | orientation only |
| `/api/summary` | record counts, departments | orientation only |
| `/api/employees?q=<term>` | employee records (leave_balance_days, status, department) | identity confirmation, profile-summary comparison |
| `/api/payroll-ledgers?q=<term>` | **both** "Leave assignment" and "Salary assignment" records (+ accrual_batch_id, base_salary, period, status) | leave precedence AND payroll/accrual readiness |
| `/api/cases?q=<term>` | case summaries | case lookup |
| `/api/cases/<case_id>` | FULL case: approvals[], attachments[](content), comments[], audit_events[], summary | folder evidence, approval history, per-case audit |
| `/api/documents?q=<term>` | document folders: files[], required_files[], tags[], required_tags[], ready | folder readiness |
| `/api/messages?q=<term>` | formal notices: quality, defects[], status, channel | notice defect inspection |
| `/api/notifications?q=<term>` | same shape as messages | notice defect cross-check |
| `/api/audit?case_id=<id>` and `/api/audit` | audit events: audit_id, event, detail, actor, employee_id, case_id | audit event selection; `/api/audit/<id>` for one event |
| `/api/recruitment?q=<term>` | opening: candidates[], offer_register[], cost_ledger[], notice_packets[], payroll_precheck_records[] | recruitment handoff + cost sum |
| `/api/policies` and `/api/policies/<id>` | policy definitions | reference text (e.g. notice requirements) |
| `/api/attachments/<attachment_id>` | attachment text content | follow from case attachments if folder detail is in an attachment |

**Searching**: `?q=<keyword>` searches across fields. The same keyword (e.g. an employee ID or case ID) often hits multiple endpoints. For payroll-ledgers and audit, `q=` an employee ID returns that employee's records; `audit?case_id=` filters by case.

## Overall SOP (step-by-step)
1. **Parse the prompt.** Identify the entity the prompt is about (employee / case / opening), the stated decision dimension (leave, payroll+accrual, folder+notice, recruitment handoff, audit), and any explicit rules ("exclude draft", "use submitted", "use the answer-template labels, not free text").
2. **Identity resolution.** Search `/api/employees?q=` (or `/api/cases?q=` / `/api/recruitment?q=`) to confirm the entity ID and name. Record `employee_id` / `case_id` / `opening_id` exactly.
3. **Gather evidence by dimension.** Call the endpoint(s) for the dimension(s) the prompt names (see decision tables below). Always fetch the FULL case detail for case-based tasks (`/api/cases/<id>`) because attachments/comments/audit_events live only there.
4. **Apply precedence / readiness rules** (below) to pick the controlling record and the excluded records. Assign the normalized enum labels, never free text.
5. **Select the audit event** whose `event`/`detail` matches the task's `audit_scope`. Exclude out-of-scope events.
6. **Decide the approval closeout gate and final control result** from the combined folder + notice + payroll + leave state.
7. **Fill every field** in the provided `answer_template.json`. Output strict JSON (numbers as numbers, booleans as booleans, lists as JSON arrays, enums exactly as listed).
8. **Run the pre-submission checklist** (below).

## Field shape reference
Templates vary per task, but the field families are stable. Populate the union the template asks for:

- **Identity**: `employee_id` | `case_id` | `opening_id` (string, exact).
- **Leave**: `effective_leave_policy` (policy_name of the winning assignment), `annual_days`/`balance_days` (integer = winning assignment's approved_leave_days), `assignment_id` (winning ledger_id), `excluded_leave_ids` (list), `leave_source`, `leave_precedence_source`, `precedence_source`, `profile_policy_ignored` (bool).
- **Payroll**: `salary_assignment_id`/`payroll_assignment_id` (winning ledger_id), `base_salary` (number), `effective_date` (string), `excluded_assignment_id`/`excluded_payroll_ids`, `payroll_status`/`payroll_source_status`, `draft_exclusion_rule`, `accrual_ready` (bool), `accrual_batch_id`.
- **Folder**: `folder_ready` (bool), `missing_files` (list), `required_tag_present` (bool), `folder_required_tag_action`.
- **Notice**: `notice_quality` (valid/defective), `notice_defects` (list of defect codes), `notice_evidence_source`, `notice_followup_required` (candidate IDs), `notice_remediation_action`.
- **Approval**: `approval_authority`, `approval_event_id`/`approval_id`, `final_decision`.
- **Audit**: `audit_event_id`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, `audit_scope`, `audit_result`.
- **Closeout/gate**: `closeout_action`/`next_action`, `approval_closeout_gate`, `closeout_blockers`, `escalation_action`, `records_remediation_owner`, `final_control_result`/`control_result`, `evidence_source_order`.
- **Recruitment**: `selected_candidate`, `waitlisted_candidates`, `rejected_candidates`, `offer_id`, `offer_base_salary`, `recruitment_cost_total`, `onboarding_handoff`, `candidate_status_source`, `candidate_outcome_control`, `selected_offer_status`, `cost_source`, `waitlisted_followup_action`, `rejected_followup_action`, `payroll_handoff_gate`, `payroll_assignment_status_required`, `draft_payroll_allowed`, `offer_exclusion_reason_for_waitlisted`, `handoff_control_result`.

## Business rules

### A. Leave source precedence (tasks naming leave policy / balance)
- **Endpoint**: `/api/payroll-ledgers?q=<EMP>`, filter `record_type == "Leave assignment"`.
- **Winning record**: the "Leave assignment" with `status == "Approved"` for the current period. If multiple Approved exist for the current period, take the one whose `period` matches the review period and is most recent by `updated_at`. (`status == "Submitted"` for a Leave assignment is also acceptable when no Approved exists — per policy LEAVE-SRC-001 "latest approved or submitted assignment controls".)
- **Exclude** any Leave assignment with `status` in `{Draft, Superseded, Voided}` — put their `ledger_id`s in `excluded_leave_ids`.
- **Ignore non-assignment ledger rows**: records with `record_type` like "HRMS leave ledger", "People Ops adjustment", "Salary assignment" are NOT leave assignments. They are decoys; never use their `approved_leave_days`/`worksheet_leave_days` as the policy figure.
- **Profile conflict**: the employee profile (`/api/employees`) has a `leave_balance_days` and an implied policy. When the approved assignment's policy/days differs from the profile, the **approved assignment wins** and the profile is stale. Set `leave_source = leave_assignment_history`, `leave_precedence_source = approved_assignment_current_period` (or `precedence_source = approved_assignment_over_profile`), `profile_policy_ignored = true`.
- **audit_result** for a stale profile = `profile_summary_stale`; **next_action** = `update_employee_summary`.
- **audit_scope** = `leave_source_precedence_only`. Only the leave-source audit event (`event` like `leave.profile_mismatch`) is supporting; a folder/tag/notice audit event on the same case is OUT of scope and goes in `excluded_audit_event_ids`.

### B. Payroll source precedence + accrual readiness (tasks naming payroll/accrual)
- **Endpoint**: `/api/payroll-ledgers?q=<EMP>`, filter `record_type == "Salary assignment"`.
- **Winning record**: the Salary assignment with `status == "Submitted"`. (`draft` and `superseded` are excluded.)
- `base_salary` = winning assignment's `base_salary` (number). `salary_assignment_id`/`payroll_assignment_id` = its `ledger_id`.
- `payroll_status`/`payroll_source_status` = `submitted`. `excluded_assignment_id`/`excluded_payroll_ids` = the Draft (and any Superseded) salary assignment `ledger_id`s.
- `draft_exclusion_rule` = `exclude_draft_assignment`.
- `effective_date` = the winning assignment's effective date: use the `period` (`YYYY-MM` -> `YYYY-MM-01`) or its `updated_at` date portion (they agree).
- **Accrual**: if the winning submitted assignment carries an `accrual_batch_id`, then `accrual_ready = true` and `accrual_batch_id` = that value. If no `accrual_batch_id` is present on the submitted assignment, `accrual_ready = false`.
- **audit_event_id** = the payroll audit event for this employee (`event` like `payroll.ready` or `payroll.draft_excluded`). **audit_scope** = `payroll_assignment_readiness`.
- **control_result**: when the submitted assignment exists and accrual batch is present -> `ready_with_monitoring`. (If folder/notice defects also exist on the case, escalate to `hold_for_folder_and_notice_defects`; otherwise stay `ready_with_monitoring`.) Clean onboarding with submitted payroll and approved leave and clean folder/notice -> `approve_closeout`.

### C. Folder readiness (tasks naming folder / records)
- **Endpoint**: `/api/documents?q=<case-or-emp>`. Also read the case's `attachments[]` content text on `/api/cases/<id>` (folder checklists often describe missing files / tags in plain text).
- `folder_ready` = the document record's `ready` boolean (AND confirm against attachments: a checklist attachment saying "Missing X" overrides a stale `ready:true`).
- `missing_files` = `required_files` minus `files` (set difference). List each missing filename exactly.
- `required_tag_present` = true iff every tag in `required_tags` appears in `tags`.
- `folder_required_tag_action`: `no_tag_action` if the required tag(s) are present; `add_required_tag` if any required tag is missing.
- `closeout_blockers` gains `missing_required_files` (any missing file) and/or `missing_required_tags` (any missing required tag).

### D. Notice defect detection (tasks naming notice / formal notice)
- **Endpoint**: `/api/messages?q=<case>` (and `/api/notifications?q=<case>` as cross-check). The recruitment `notice_packets[]` array is the equivalent for candidate notices.
- `notice_quality` = the message's `quality` field (`valid` / `defective`).
- `notice_defects` = the message's `defects[]` array. Defect code vocabulary (exactly these tokens):
  - `missing_ack_deadline` — no acknowledgement deadline in the notice body/subject.
  - `missing_appeal_instructions` — no appeal instructions.
  - `missing_waitlist_status` — a waitlist notice that fails to state waitlist status.
  - `missing_correct_policy` — notice cites a wrong/stale policy.
- Do not invent defect codes beyond these four. If the audit `detail` text describes a defect, map it to the closest code only if a message/notice packet actually carries that defect; the message/notice-packet `defects[]` is authoritative.
- `notice_evidence_source` = `notice_packet_inspection` (when you read message/notice-packet defects) — preferred over `message_notice_inspection`/`case_summary_only`.
- `notice_remediation_action`: `reissue_defective_notices` when any defect present; `no_notice_action` when valid.
- A defective notice adds `defective_formal_notice` to `closeout_blockers` and drives `next_action = block_close_and_reissue_notice`.

### E. Approval closeout gate + final control result
- Read approvals from the FULL case (`/api/cases/<id>` -> `approvals[]`). `approval_authority` = the final approver; `approval_event_id` = its `approval_id`; `final_decision` derived from `decision`/`note` (`Approved` + "with conditions" -> `approved_with_conditions`).
- **approval_closeout_gate** = `approval_sufficient_when_records_clean` when folder is ready, all required tags present, and notice is valid. **approval_closeout_gate** = `approval_not_sufficient_when_folder_or_notice_defective` when ANY of: missing required file, missing required tag, or defective notice. Approval alone never closes a defective folder/notice.
- **final_control_result** (the master enum, reuse for `control_result`):
  - `approve_closeout` — folder ready, tags present, notice valid, payroll submitted, leave approved.
  - `hold_for_folder_and_notice_defects` — any folder/notice defect.
  - `ready_with_monitoring` — payroll submitted + accrual ready, monitored cases where no blocking defect but QA flagged monitoring.
- **next_action / closeout_action**:
  - `block_close_and_reissue_notice` — notice defective.
  - `open_records_remediation` — missing files/tags.
  - `approve_onboarding_close` — fully clean.
  - `update_employee_summary` — leave stale-profile case.
- **escalation_action** / **records_remediation_owner**: folder/records defects -> owner `Records`; cross-module/notice package -> `People Ops Compliance`; payroll-only -> `Payroll QA`.

### F. Audit event selection
- For each task, `audit_scope` is determined by the decision dimension:
  - leave tasks -> `leave_source_precedence_only`
  - payroll/accrual tasks -> `payroll_assignment_readiness`
  - folder/notice tasks -> `document_notice_findings_only`
- `audit_event_id` = the single audit event whose `event`/`detail` matches the scope for this entity/case (e.g. `leave.profile_mismatch`, `payroll.ready`, `payroll.draft_excluded`, `notice.defect`, `case.close_blocked`). Prefer the event whose `employee_id`/`case_id` matches the task entity.
- `supporting_audit_event_ids` = all in-scope events (usually just the one). `excluded_audit_event_ids` = audit events on the same case that belong to a DIFFERENT scope (e.g. a `folder.tag_missing` event on a leave-scope task). Cross-module "escalation package" events (`cross_module.escalation_package`) are umbrella events — list their referenced child event IDs only if the task is explicitly cross-module; otherwise exclude the umbrella.
- **audit_result** for leave-stale = `profile_summary_stale`; payroll-ready = `ready_with_monitoring`; folder/notice block = `block_close`.

### G. Recruitment handoff + cost (tasks naming opening/candidates)
- **Endpoint**: `/api/recruitment?q=<opening>`.
- **Candidate outcome** — reconstruct from `candidates[]` + `offer_register[]`:
  - `selected_candidate` = the candidate with `committee_decision == "Selected"` whose offer in `offer_register` has `status == "accepted"`.
  - `waitlisted_candidates` = `committee_decision == "Waitlisted"`.
  - `rejected_candidates` = `committee_decision == "Rejected"`.
  - `candidate_status_source` = `interview_feedback_and_offer`; `candidate_outcome_control` = `committee_decision_with_offer_confirmation`; `selected_offer_status` = the offer's `status` (accepted / draft / withdrawn / none).
- **Cost**: `recruitment_cost_total` = sum of every `cost_ledger[].amount`. `cost_source` = `recruitment_cost_ledger`. Do not use case-summary cost figures.
- **Notice followup**: for each entry in `notice_packets[]` with `status == "not_sent"`, add its `candidate_id` to `notice_followup_required`. `waitlisted_followup_action` = the waitlist packet's `required_action` (e.g. `send_waitlist_notice`); `rejected_followup_action` = the rejection packet's `required_action` (e.g. `send_rejection_notice`). `notice_quality_source` = `notice_packet_inspection`.
- **Payroll handoff**: a payroll assignment must be created for the accepted candidate only. `payroll_handoff_gate` = `accepted_offer_only`; `payroll_assignment_status_required` = `submitted_after_acceptance`; `draft_payroll_allowed` = false. `offer_exclusion_reason_for_waitlisted` = `no_accepted_status_or_offer` (waitlisted/rejected candidates get no submitted assignment).
- **onboarding_handoff**: if `payroll_precheck_records[]` is empty and the selected offer is accepted -> `create_payroll_precheck` (or `create_submitted_assignment_after_acceptance` when a submitted assignment must follow acceptance; pick per the template's wording — the controlling rule is the offer must be accepted before any assignment). `no_payroll_handoff` only when no accepted offer exists.
- **handoff_control_result**: accepted offer, assignment not yet submitted -> `submitted_handoff_required_after_acceptance`; submitted assignment already present -> `submitted_handoff_required`; no accepted offer -> `no_handoff_required`.

## Common misjudgments and exclusion rules
- **Selecting a Draft or Superseded leave/payroll assignment as controlling.** Always exclude Draft and Superseded from the controlling record; still list them in the `excluded_*` fields.
- **Treating "HRMS leave ledger" / "People Ops adjustment" rows as leave assignments.** Only `record_type == "Leave assignment"` defines the policy. Other rows are decoys.
- **Trusting the employee profile `leave_balance_days` over the approved assignment.** The approved assignment wins; the profile is "stale" when they conflict.
- **Trusting the case `summary` text for defects.** The summary is a hint; the authoritative defects are in `/api/messages` `defects[]` (or `notice_packets[].required_action` for recruitment). Inspect the packet, don't infer from prose.
- **Closing out on approval alone when the folder or notice is defective.** Approval is NEVER sufficient when a required file is missing, a required tag is missing, or the notice is defective.
- **Including out-of-scope audit events as supporting.** A folder event on a leave-scope task goes to `excluded_audit_event_ids`, not supporting.
- **Counting the cross-module umbrella audit event as a single entity's finding.** It references child events; assign the child event to the relevant entity.
- **Free-text enum values.** Use the exact normalized labels from the answer template (e.g. `ready_with_monitoring`, `hold_for_folder_and_notice_defects`, `exclude_draft_assignment`, `leave_assignment_history`). No spaces, no capitalization variants.
- **Recruitment cost from a case summary.** Always sum the `cost_ledger` amounts; do not rely on any summary number.
- **Offering a payroll handoff to waitlisted/rejected candidates.** Only the accepted selected candidate gets the submitted-after-acceptance assignment.
- **Missing the FULL case detail.** `/api/cases` (list) does NOT include attachments/comments/per-case audit_events; you must call `/api/cases/<case_id>`.

## Pre-submission checklist
- [ ] Every field in the provided `answer_template.json` is present and uses the exact enum token / type from the template.
- [ ] Identity (`employee_id`/`case_id`/`opening_id`) matches the prompt and the API record.
- [ ] Controlling leave assignment = Approved (current period) "Leave assignment" record; Draft/Superseded and non-assignment rows are in `excluded_*` and NOT used for figures.
- [ ] Controlling payroll = Submitted "Salary assignment"; Draft/Superseded excluded.
- [ ] `missing_files` = required_files minus files; `required_tag_present` reflects every required tag.
- [ ] `notice_defects` come from the message/notification/notice-packet `defects[]`, mapped to the four codes only.
- [ ] `approval_closeout_gate` is `...not_sufficient...` if any folder or notice defect exists, regardless of approval.
- [ ] `final_control_result`/`control_result` consistent with the gate: defects -> `hold_for_folder_and_notice_defects`; clean -> `approve_closeout`; submitted-payroll+accrual monitor -> `ready_with_monitoring`.
- [ ] `audit_scope` matches the task dimension; `excluded_audit_event_ids` lists same-case out-of-scope events.
- [ ] `recruitment_cost_total` = sum of `cost_ledger` amounts (number, not string).
- [ ] Booleans are `true`/`false`; lists are JSON arrays; numbers are unquoted.
- [ ] Output is strict JSON parseable by `python3 -m json.tool`; no trailing commas, no comments.
