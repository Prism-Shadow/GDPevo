---
name: peopleops-console-erp-hr
description: Solve ERP HR "PeopleOps Console" tasks (employee lifecycle, leave, payroll, policy cases, recruitment, documents, messages, audit) by reading the remote HTTP API, applying source-precedence and folder/notice control rules, and emitting normalized-label JSON answers.
---

# PeopleOps Console — Solver Skill

You answer HR lifecycle questions about a fixed dataset exposed ONLY through a
remote read-only HTTP API. There is no local DB. Each task prompt gives you a
business question plus an `answer_template.json` of typed/enum fields; you must
return one JSON object whose keys exactly match the template, using the template's
**normalized business labels** (enum strings) — never free text.

## 1. The remote API (read-only)

Base URL is given in `environment_access.md` (e.g. `<remote-env-url>`).
The web URL / login in the prompt is flavor; ignore it and use the API.

- `GET /api/summary` and `GET /api/manifest` — counts, departments, module list. Start here for orientation.
- `GET /api/employees?q=&status=` — profile cards (name, dept, manager, salary_band, `leave_balance_days`, status).
- `GET /api/payroll-ledgers?q=&status=&type=` — the workhorse. Holds BOTH **Leave assignment** rows and **Salary assignment** rows (plus HRMS/People-Ops adjustment ledger rows), each with a `status` and `record_type`.
- `GET /api/policies` / `GET /api/policies/{id}` — the written precedence rules (LEAVE-SRC-001, PAY-SRC-001, POL-DOCS-2026, HR-POL-014).
- `GET /api/cases?q=&status=&type=` (summaries) then `GET /api/cases/{case_id}` (FULL detail: approvals, attachments, comments, embedded audit_events, folder/notice refs). Always pull the full case for case tasks.
- `GET /api/recruitment?q=` — full opening packet: candidates (committee_decision, notice_status, rounds), offer_register, cost_ledger, notice_packets, payroll_precheck_records.
- `GET /api/documents?q=` — folders: `files`, `required_files`, `tags`, `required_tags`, and a precomputed `ready` boolean.
- `GET /api/messages?q=` and `GET /api/notifications?q=` — formal notices with `quality` (valid/defective) and a `defects` list.
- `GET /api/audit?q=&case_id=` / `GET /api/audit/{audit_id}` — QA/control events. The `detail` text usually NAMES the authoritative record and the QA verdict verbatim (e.g. "profile_summary_stale", "ready_with_monitoring", "block close"). Trust it as confirming evidence, but still verify against ledgers/folders/notices.

`q=` is a case-insensitive substring match over scalar fields. Use IDs as queries
(`q=EMP-104`, `q=CASE-RW-221`, `q=REQ-DA-77`). Omit `q` to dump a whole collection
(these collections are small — tens of rows — so dumping is cheap and recommended).

**Cross-module rule:** an employee's authoritative state is spread across modules.
A leave/payroll task almost always needs payroll-ledgers + policies + audit; a case
task needs the full case + documents + messages/notifications + audit. Always
cross-reference; never answer from the employee profile card alone (the profile
`leave_balance_days`/policy is the *stale summary* the tasks test you on).

## 2. Core business rules (transferable)

### 2.1 Leave source precedence (LEAVE-SRC-001)
"The latest **approved or submitted** leave assignment for the period controls.
Draft, voided, superseded, and obsolete records are excluded even when profile
summaries conflict."
- Among `record_type == "Leave assignment"` rows for the employee/period, pick the
  one with status **Approved** (or Submitted) that is newest (`updated_at`). That
  row's `policy_name` is the `effective_leave_policy`; its `approved_leave_days`
  (= `worksheet_leave_days` when clean) is the `annual_days`/`balance_days`; its
  `ledger_id` is the authoritative `assignment_id`.
- EXCLUDE every other leave assignment: `Superseded`, `Draft` go into
  `excluded_leave_ids`.
- The employee profile's `leave_balance_days` and any "legacy/profile policy" is
  the STALE summary → it loses to the approved assignment. Set
  `profile_policy_ignored = true`, `precedence_source = approved_assignment_over_profile`,
  `leave_precedence_source = approved_assignment_current_period`,
  `leave_source = leave_assignment_history`.
- If audit confirms it, `audit_result = profile_summary_stale` and the corrective
  `next_action = update_employee_summary` (not records remediation, not "no action").
- Watch out: the ledger may also contain non-assignment rows ("HRMS leave ledger",
  "People Ops adjustment"). The controlling assignment is the **Leave assignment**
  record named in the audit `detail`; adjustment-ledger rows are not the authority.

### 2.2 Payroll assignment source (PAY-SRC-001)
"Use the current **submitted** salary assignment. Draft planning assignments do not
affect payroll readiness or accrual checks."
- Among `record_type == "Salary assignment"` rows, pick status **Submitted**. Its
  `ledger_id` → `payroll_assignment_id`/`salary_assignment_id`, `base_salary`,
  `period`/`updated_at` → effective date.
- The Draft salary assignment goes to `excluded_payroll_ids`/`excluded_assignment_id`.
  Set `payroll_status`/`payroll_source_status = submitted`,
  `draft_exclusion_rule = exclude_draft_assignment`, `draft_payroll_allowed = false`.
- Accrual readiness: the submitted assignment "matches" an accrual batch (audit
  detail names it, e.g. `ACCR-2026-04-B`). If so `accrual_ready = true`,
  `accrual_batch_id` = that batch, `control_result = ready_with_monitoring`,
  `audit_scope = payroll_assignment_readiness`.

### 2.3 Folder readiness (POL-DOCS-2026)
"A folder is NOT ready unless all required files AND all required tags in the
checklist are present."
- `folder_ready = (set(required_files) ⊆ set(files)) AND (set(required_tags) ⊆ set(tags))`.
  The documents endpoint also gives a precomputed `ready` boolean — confirm with it.
- `missing_files = required_files − files` (verbatim filenames, e.g.
  `"tax-equalization-agreement.pdf"`). `required_tag_present = required_tags ⊆ tags`.
- If a required tag is missing → `closeout_blockers` includes `missing_required_tags`
  and `folder_required_tag_action = add_required_tag`; if all tags present →
  `no_tag_action`.

### 2.4 Formal-notice defect detection
The notice for a case lives in **messages/notifications** (and/or recruitment
`notice_packets`). Read its `quality` and `defects`.
- `notice_quality = valid | defective` (from the message's `quality`).
- `notice_defects` = the message `defects` list, restricted to the template's
  allowed enum: `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`.
- `notice_evidence_source = message_notice_inspection` when the notice is a message/
  notification; `notice_packet_inspection` for recruitment offer/waitlist/rejection
  packets; never `case_summary_only`.

### 2.5 Closeout / control gate (the central decision)
"Approval alone is NOT sufficient to close when the folder or notice is defective."
- `approval_closeout_gate`:
  - `approval_sufficient_when_records_clean` if folder ready AND notice valid AND no draft-record conflicts.
  - `approval_not_sufficient_when_folder_or_notice_defective` otherwise.
- Map the gate to results:
  - Clean records → `final_decision`/`closeout_action`=`approve_onboarding_close` /
    `final_control_result = approve_closeout`.
  - Folder/notice defects → `next_action = block_close_and_reissue_notice`,
    `final_control_result = hold_for_folder_and_notice_defects`,
    `escalation_action = block_close_and_reissue_notice`,
    `notice_remediation_action = reissue_defective_notices`.
  - Payroll/accrual "ready but watch" → `ready_with_monitoring`.
- `closeout_blockers` ⊆ {`missing_required_files`, `missing_required_tags`,
  `defective_formal_notice`} — include only the ones that actually apply.
- `records_remediation_owner` = the folder/case owner doing the fix: `Records`
  (folder file/tag gaps), `People Ops Compliance` (cross-module escalation),
  `Payroll QA` (payroll). Use the document/case `owner`.
- `evidence_source_order = approval_history_folder_notice_audit` for closeout cases
  (read approvals, then folder, then notice, then audit).

### 2.6 Recruitment reconciliation
- Candidate outcomes come from `committee_decision`: Selected → `selected_candidate`;
  Waitlisted → `waitlisted_candidates`; Rejected → `rejected_candidates`. Arrays hold
  **candidate IDs only**.
  - `candidate_status_source = interview_feedback_and_offer`,
    `candidate_outcome_control = committee_decision_with_offer_confirmation`.
- Offer: from `offer_register` for the selected candidate → `offer_id`,
  `offer_base_salary`, `selected_offer_status` (e.g. `accepted`).
- `recruitment_cost_total` = **sum of ALL `cost_ledger[].amount`** (every line),
  `cost_source = recruitment_cost_ledger`.
- Follow-up notices: any candidate whose notice has not been sent / is defective needs
  follow-up. `notice_followup_required` = those candidate IDs (waitlisted + rejected
  with `status=not_sent`). `notice_quality_source = notice_packet_inspection`.
  - `waitlisted_followup_action = send_waitlist_notice` (or
    `reissue_waitlist_notice_not_rejection` if a wrong/rejection notice went out —
    never downgrade a waitlist to rejection).
  - `rejected_followup_action = send_rejection_notice`.
- Payroll handoff gate (PAY-SRC-001 §4.2): created ONLY after the selected candidate
  has an **accepted** offer, and the handoff must be a **submitted** assignment;
  draft prechecks do not satisfy the gate.
  - Accepted offer present →
    `onboarding_handoff = create_submitted_assignment_after_acceptance`,
    `payroll_handoff_gate = accepted_offer_only`,
    `payroll_assignment_status_required = submitted_after_acceptance`,
    `draft_payroll_allowed = false`,
    `handoff_control_result = submitted_handoff_required_after_acceptance`.
  - `offer_exclusion_reason_for_waitlisted = no_accepted_status_or_offer` (waitlisted/
    rejected have no accepted offer, so they are excluded from handoff).

### 2.7 Audit correlation & scope (exclusion discipline)
Each task has a **scope**, and you must include only the audit events in scope and
EXCLUDE adjacent events even when they touch the same case/employee.
- `audit_scope` ∈ {`leave_source_precedence_only`, `payroll_assignment_readiness`,
  `document_notice_findings_only`}. Pick by the task's subject.
- `supporting_audit_event_ids` = events whose `event`/`detail` matches the scope:
  - leave precedence → `leave.profile_mismatch` (e.g. profile_summary_stale).
  - payroll readiness → `payroll.ready` / `payroll.draft_excluded`.
  - document/notice → `notice.defect` and `folder.tag_missing`.
- `excluded_audit_event_ids` = same-case events from the OTHER domain. Example: a
  leave task on a case that also has a `folder.tag_missing` event must EXCLUDE that
  document event from the leave-scope decision (and vice versa).
- Cross-module escalation packages (`cross_module.escalation_package`) name their
  related events in `detail`; treat those as the in-scope set for that package and
  honor the stated control owner and remediation clock.

## 3. Normalized-label vocabulary (copy enum values exactly)

Always emit the template's literal enum strings. Key vocab observed:
- Source: `leave_assignment_history`, `employee_profile_summary`, `case_summary_only`;
  `approved_assignment_over_profile`; `approved_assignment_current_period`,
  `profile_summary_current_period`.
- Payroll status: `submitted` | `draft` | `superseded`; `exclude_draft_assignment`,
  `draft_allowed`, `exclude_superseded_only`.
- Folder/notice: `folder_ready` boolean; `valid`|`defective`; defect enums above;
  `notice_packet_inspection`|`message_notice_inspection`|`case_summary_only`;
  `add_required_tag`|`no_tag_action`.
- Gate: `approval_sufficient_when_records_clean` |
  `approval_not_sufficient_when_folder_or_notice_defective`.
- Decisions/actions: `approved_with_conditions`|`approved`|`rejected`|`held`;
  `block_close_and_reissue_notice` | `approve_onboarding_close` | `open_records_remediation`;
  `update_employee_summary`|`no_action`; `reissue_defective_notices`|`no_notice_action`|`send_new_offer_notice`.
- Final control: `approve_closeout` | `hold_for_folder_and_notice_defects` | `ready_with_monitoring`.
- Audit scope/results: `leave_source_precedence_only`|`payroll_assignment_readiness`|
  `document_notice_findings_only`; `profile_summary_stale`|`ready_with_monitoring`|`block_close`.
- Recruitment: `create_submitted_assignment_after_acceptance`|`create_payroll_precheck`|`no_payroll_handoff`;
  `accepted_offer_only`|`accepted_offer_and_submitted_assignment`|`all_interviewed_candidates`;
  `submitted_handoff_required_after_acceptance`; `no_accepted_status_or_offer`.
- Owners: `Records` | `People Ops Compliance` | `Payroll QA`.

## 4. Common misjudgments / exclusion rules

- Do NOT use the employee profile card's `leave_balance_days` or its policy — that is
  the stale summary; the approved assignment overrides it.
- Do NOT count Draft or Superseded assignments as authoritative; put them in the
  exclusion lists. Draft prechecks never satisfy a payroll handoff gate.
- Do NOT sum a subset of cost lines — `recruitment_cost_total` is ALL ledger lines.
- Do NOT fold a folder/document audit event into a leave or payroll scope (and vice
  versa); use `excluded_audit_event_ids`.
- Do NOT mark a folder ready if a required TAG is missing even when all files exist
  (and vice versa) — both conditions are required.
- A defective notice or an incomplete folder BLOCKS close even when final approval
  exists ("Approved with conditions" is still defective until the notice is reissued).
- Arrays in recruitment answers must contain candidate IDs only, never names.
- Prefer the primary domain evidence source over `case_summary_only` / `message_only`
  whenever the detailed record exists (it almost always does).
- Emit only keys present in the template; fill list fields with `[]` when empty
  (e.g. no excluded audit events) rather than omitting them.

## 5. Step-by-step SOP for a new task

1. Read the prompt + `answer_template.json`. Note the subject entity (EMP-/CASE-/REQ-),
   the domain (leave / payroll / case-closeout / recruitment), and every enum's allowed values.
2. `GET /api/summary` for orientation (optional once familiar).
3. Pull the subject: `employees?q=`, then the relevant deep records:
   - leave/payroll → `payroll-ledgers?q=<EMP>` + relevant `policies`.
   - case closeout → `cases/{id}` + `documents?q=` + `messages?q=`/`notifications?q=`.
   - recruitment → `recruitment?q=<REQ>`.
4. Pull audit: `audit?q=<EMP or CASE>` (or `case_id=`); read `detail` text for the
   named authoritative record and verdict.
5. Apply §2 rules to choose the authoritative record(s), compute exclusions, assess
   folder/notice, and decide the gate/control result.
6. Map every field to its template enum using §3 vocab; double-check exclusion lists
   and scope.
7. Output a single JSON object matching the template keys exactly — no markdown, no
   commentary, normalized labels only.
