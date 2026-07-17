# HR Employee-Lifecycle Clearance & Audit via Remote PeopleOps API

## When to use

Use this skill when solving any HR employee-lifecycle task against the Northwind PeopleOps Console remote environment. Task types include: onboarding closeout verification, leave source-precedence validation, payroll assignment and accrual readiness, policy-case folder/notice quality review, and recruitment outcome reconciliation. The answer is always a JSON object matching a provided `answer_template.json` whose fields are normalized business-choice enums (not free text).

## Environment

- **Base URL**: `<remote-env-url>` (use this; ignore `127.0.0.1:<port>` in prompts — it is illustrative).
- **Auth**: none. All `/api/*` endpoints are read-only GET.
- **Web UI**: `<remote-env-url>/` (not needed; the JSON API is authoritative).

## Read-only API endpoints (GET)

| Endpoint | Returns | Key fields |
|---|---|---|
| `/api/manifest` | Module map + dataset file counts | seed, generated_at |
| `/api/summary` | Live record counts | (may be sparse) |
| `/api/employees?q=<id>` | Employee profile | employee_id, leave_balance_days *(stale summary)*, status, salary_band |
| `/api/cases` | Case summaries (list) | case_id, case_type, status, summary |
| `/api/cases/<case_id>` | **FULL case detail** | approvals, attachments, audit_events (embedded), comments, policy_refs |
| `/api/policies` | Policy definitions | policy_id, sections (body/heading), owner |
| `/api/policies/<id>` | Single policy | same structure |
| `/api/payroll-ledgers?q=<emp_id>` | **Leave AND salary assignments** | ledger_id, record_type, status, base_salary, policy_name, approved_leave_days, accrual_batch_id, period |
| `/api/recruitment?q=<opening_id>` | Recruitment packet | candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records |
| `/api/documents?q=<keyword>` | Lifecycle document folders | document_id, ready, required_files, files, required_tags, tags |
| `/api/messages?q=<keyword>` | Formal notice messages | message_id, case_id, quality, defects, status, body |
| `/api/notifications?q=<keyword>` | Notifications (shares schema with messages on this env) | defects, ack/appeal info |
| `/api/audit` | All audit events | audit_id, case_id, employee_id, event, detail, actor |
| `/api/audit?case_id=<id>` | Audit filtered by case | same as above |
| `/api/audit/<audit_id>` | Single audit event detail | same fields |
| `/api/attachments/<attachment_id>` | Attachment text content | content, name, kind, status, uploaded_by |

## Overall SOP (step-by-step)

1. **Parse the prompt.** Identify: the entity (EMP-XXX, CASE-XXX, REQ-XXX), the task type (closeout / leave / payroll / folder-notice / recruitment), and the exact fields the template demands.

2. **Gather all records.** Call the relevant endpoints in this order:
   - **Employee tasks**: `/api/employees?q=EMP-XXX` → `/api/payroll-ledgers?q=EMP-XXX` (leave + payroll records live HERE, not inside the employee object).
   - **Case tasks**: `/api/cases/<case_id>` (full detail — covers approvals, folder-checklist attachment, embedded audit_events, comments).
   - **Documents**: `/api/documents` (or `?q=<keyword>` if the case attachment gave a folder ID like `DOC-XXX`).
   - **Notices**: `/api/messages?q=<case_id>` for HR cases; for recruitment, the `notice_packets` array inside `/api/recruitment` response.
   - **Audit**: `/api/audit` (full list) or `/api/audit?case_id=<id>` or `/api/audit/<id>` for detail.
   - **Recruitment**: `/api/recruitment?q=REQ-XXX` — candidates, offers, costs, notice packets, precheck records.
   - **Policies**: `/api/policies` (LEAVE-SRC-001, PAY-SRC-001, POL-DOCS-2026, HR-POL-014).

3. **Apply source-precedence / business rules** (below) to derive the authoritative records and exclude the non-authoritative ones.

4. **Check folder readiness and notice quality** even when a final approval exists in the case — the clearance gate is independent of approval status.

5. **Select audit events by scope.** Keep only the events matching the current task's `audit_scope`; list any adjacent (non-scope) events in `excluded_audit_event_ids`.

6. **Resolve each template field** to its normalized business-label enum value. Do not invent labels — pick from the template's `allowed_values`.

7. **Run the pre-submission checklist**, then output JSON strict-matching the template.

## Answer template conventions

Every task gives an `answer_template.json` whose fields are `string`, `number`, `integer`, `boolean`, `list[string]`, or `enum`/`list[enum]` with `allowed_values`.

- **IDs**: strings taken verbatim from the API (e.g. `LA-118-APP-02`, `PAY-122-SUB-03`, `AUD-CASE221-09`).
- **Enums**: choose *exactly* one value from `allowed_values` — no free-text, no invented labels.
- **Lists**: arrays of strings (IDs) or enums (defect codes / blocker codes).

### Field families you will encounter

| Family | Fields (may appear across different templates) |
|---|---|
| Employee/leave | `employee_id`, `effective_leave_policy`, `assignment_id`, `annual_days` / `balance_days`, `leave_precedence_source`, `precedence_source`, `profile_policy_ignored` |
| Payroll | `payroll_assignment_id` / `salary_assignment_id`, `base_salary`, `effective_date`, `payroll_status` / `payroll_source_status`, `payroll_assignment_id`, `excluded_payroll_ids` / `excluded_assignment_id`, `draft_exclusion_rule`, `accrual_ready`, `accrual_batch_id` |
| Folder/notice | `folder_ready`, `missing_files`, `required_tag_present`, `closeout_blockers`, `folder_required_tag_action`, `notice_quality`, `notice_defects`, `notice_evidence_source` / `notice_quality_source` |
| Case/approval | `case_id`, `final_decision`, `approval_authority`, `approval_event_id`, `approval_closeout_gate`, `evidence_source_order`, `next_action`, `escalation_action`, `records_remediation_owner`, `notice_remediation_action` |
| Audit | `audit_event_id`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, `audit_scope`, `audit_result` |
| Control result | `final_control_result` / `control_result`, `closeout_action`, `leave_source`, `leave_precedence_source` |
| Recruitment | `opening_id`, `selected_candidate`, `waitlisted_candidates`, `rejected_candidates`, `offer_id`, `offer_base_salary`, `recruitment_cost_total`, `notice_followup_required`, `notice_followup_required`, `onboarding_handoff`, `candidate_status_source`, `candidate_outcome_control`, `selected_offer_status`, `cost_source`, `waitlisted_followup_action`, `rejected_followup_action`, `payroll_handoff_gate`, `payroll_assignment_status_required`, `draft_payroll_allowed`, `offer_exclusion_reason_for_waitlisted`, `handoff_control_result` |

## Business rules (derived from solving train tasks against the live API)

### 1. Leave source precedence (LEAVE-SRC-001)

> "The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict."

- Leave assignments are `record_type: "Leave assignment"` in `/api/payroll-ledgers`. The employee profile's `leave_balance_days` is a **summary that may be stale** — never trust it over a ledger assignment.
- **Precedence**: Approved (current period) > Submitted (current period) > Superseded/voided/obsolete > Draft.
- An **approved current-period assignment overrides the stale profile summary** when the ledger, policy document, and audit detail confirm the assignment.
- When the profile is overridden, set:
  - `leave_precedence_source` = `approved_assignment_current_period`
  - `precedence_source` = `approved_assignment_over_profile`
  - `profile_policy_ignored` = `true`
  - `audit_result` = `profile_summary_stale`
  - `next_action` = `update_employee_summary`
- Exclude draft and superseded leave IDs in `excluded_leave_ids`.

### 2. Payroll source status and draft exclusion (PAY-SRC-001 § 3.4)

> "Use the current submitted salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks."

- Salary assignments are `record_type: "Salary assignment"` in `/api/payroll-ledgers`.
- **Submitted wins**; draft salary assignments are always excluded.
- In templates: `payroll_status` / `payroll_source_status` = `submitted`. `draft_exclusion_rule` = `exclude_draft_assignment`.
- Payroll "superseded" records are also non-authoritative but the primary explicit exclusion rule is `exclude_draft_assignment`.

### 3. Payroll accrual readiness

- The **submitted** salary assignment's `accrual_batch_id` (e.g. `ACCR-2026-04-B`) links to the accrual batch.
- If the audit event (`payroll.ready`) confirms the submitted assignment matches the accrual batch:
  - `accrual_ready` = `true`
  - `control_result` = `ready_with_monitoring`
- The audit `detail` string literally contains the QA result (`ready_with_monitoring` or `block_close`) — mirror it.
- Effective date: use the payroll ledger's period-normalized start date (the `updated_at` date's calender day, typically `YYYY-04-01` for a `2026-04` period, or the equivalent period start).

### 4. Folder readiness (POL-DOCS-2026)

> "A folder is not ready unless all required files and required tags shown in the folder checklist are present."

- Fetch from `/api/documents` (all) or by keyword. Also check `folder-checklist.txt` attachment in the case detail.
- Compute:
  - `folder_ready` = `ready` field from the documents endpoint (true only when all requirements are met).
  - `missing_files` = `required_files` not present in `files` (list the exact filename strings: e.g. `["tax-equalization-agreement.pdf"]`).
  - `required_tag_present` = every `required_tags` entry appears in `tags`.
  - `closeout_blockers` gets `missing_required_files` if any required file absent, `missing_required_tags` if any required tag absent, `defective_formal_notice` if the notice is defective.
- `folder_required_tag_action`: `no_tag_action` if all required tags present; `add_required_tag` if a required tag is missing.

### 5. Formal notice quality

- **For HR/policy cases**: inspect `/api/messages?q=<case_id>`. Each message has a `quality` field (`valid` or `defective`) and a `defects` array.
  - `notice_evidence_source` = `message_notice_inspection`.
- **For recruitment**: inspect `notice_packets` in the recruitment response. Each packet has `quality`, `defects`, and `required_action`.
  - `notice_quality_source` = `notice_packet_inspection`.
- Defect codes: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- Any defect in the array → `notice_quality` = `defective`.
- `notice_remediation_action` = `reissue_defective_notices` when defects exist; `no_notice_action` when the notice is valid or no notice is required.

### 6. Approval closeout gate

- A **final approval** (e.g. `APP-XXX-FINAL`, `HR Director` / `VP People`) is **NOT sufficient** when the folder or formal notice is defective.
- Set `approval_closeout_gate` = `approval_not_sufficient_when_folder_or_notice_defective` if:
  - `folder_ready` is `false`, OR
  - `notice_quality` is `defective`.
- Set `approval_closeout_gate` = `approval_sufficient_when_records_clean` only when BOTH folder and notice are clean (or absent, meaning no folder/notice defects exist for that entity).
- The case `summary` field is a **starting hint, not the decision** — always verify from attachments, messages, documents, and audit detail.

### 7. Control result resolution

| Conditions | `final_control_result` / `control_result` |
|---|---|
| Folder ready (or no folder needed) AND notice valid (or no notice needed) AND payroll source is submitted AND leave source is approved | `approve_closeout` |
| Folder not ready OR notice defective (regardless of approval status) | `hold_for_folder_and_notice_defects` |
| Payroll readiness scope where submitted assignment matches accrual batch and no folder/notice defect blocking | `ready_with_monitoring` |

- `closeout_action` / `next_action` for blocked hold: `block_close_and_reissue_notice`.
- `closeout_action` / `next_action` for approved: `approve_onboarding_close` (onboarding scope) — some tasks use `no_action` (leave scope: `update_employee_summary`).

### 8. Audit event scope selection

Only 8 audit events exist. Each has a `case_id` and `event` type. Select events matching the task scope:

| Scope (`audit_scope`) | Include event types | Exclude everything else |
|---|---|---|
| `leave_source_precedence_only` | `leave.profile_mismatch` | `notice.defect`, `folder.tag_missing`, `payroll.*`, `case.close_blocked`, `cross_module.*` |
| `payroll_assignment_readiness` | `payroll.ready`, `payroll.draft_excluded` | `leave.*`, `notice.*`, `folder.*` |
| `document_notice_findings_only` | `notice.defect`, `case.close_blocked`, `folder.tag_missing` | `leave.*`, `payroll.*` |

- Populate `audit_event_id` (primary), `supporting_audit_event_ids` (all scoping events that support the decision), `excluded_audit_event_ids` (adjacent audit events in the same case that are outside scope).
- Cross-module escalation events (`cross_module.escalation_package`) list related audit IDs in their `detail` — use these to understand which events are grouped, but don't include the cross-module event itself in a single-scope answer unless the task is about cross-module escalation.

### 9. Audit detail -> control result mapping

The audit `detail` string for QA results contains the literal control result:
- `profile_summary_stale` → `audit_result` = `profile_summary_stale`, `next_action` = `update_employee_summary`.
- `ready_with_monitoring` → `control_result` = `ready_with_monitoring`.
- `block close` → `final_control_result` = `hold_for_folder_and_notice_defects`.

### 10. Recruitment reconciliation

- **Candidate outcome**: from `committee_decision` field: `Selected` → `selected_candidate`; `Waitlisted` → `waitlisted_candidates`; `Rejected` → `rejected_candidates`. `candidate_status_source` = `interview_feedback_and_offer`; `candidate_outcome_control` = `committee_decision_with_offer_confirmation`.
- **Selected offer**: from `offer_register` — `offer_id`, `offer_base_salary`, `selected_offer_status` (e.g. `accepted`).
- **Recruitment cost total**: sum ALL `cost_ledger` item `amount` values. Do not round; do not exclude any line. `cost_source` = `recruitment_cost_ledger`.
- **Notice followup**: candidates whose notice status is `not_sent` or whose notice has defects belong in `notice_followup_required` (candidate IDs only).
- **Payroll handoff gate** (PAY-SRC-001 § 4.2): "handoff only after accepted offer; handoff must be submitted; draft prechecks don't satisfy the gate."
  - `onboarding_handoff` = `create_submitted_assignment_after_acceptance` (when offer accepted).
  - `payroll_handoff_gate` = `accepted_offer_and_submitted_assignment`.
  - `payroll_assignment_status_required` = `submitted_after_acceptance`.
  - `draft_payroll_allowed` = `false`.
  - `handoff_control_result` = `submitted_handoff_required_after_acceptance`.
- **Waitlisted followup**: if notice was never sent (`not_sent`) → `send_waitlist_notice`. If notice was sent but defective/needs fixing → `reissue_waitlist_notice_not_rejection`. **Never** reclassify a waitlisted candidate as rejected.
- **Rejected followup**: if notice was never sent → `send_rejection_notice`. If notice was sent but defective → `reissue_rejection_notice`.
- **Offer exclusion for waitlisted**: `offer_exclusion_reason_for_waitlisted` = `waitlisted_not_selected`.

### 11. Escalation and remediation owners

- `escalation_action`: `block_close_and_reissue_notice` when notice defective and closeout blocked; `open_records_remediation` is also available but the primary stop-and-fix action is block-and-reissue.
- `records_remediation_owner`: `Records` (when the folder is missing required files — the folder-checklist attachment is typically uploaded by Records). Use `People Ops Compliance` for cross-module/cross-entity compliance escalations. Use `Payroll QA` for payroll-specific record issues.
- `evidence_source_order`: `approval_history_folder_notice_audit` (the full chain: approvals → folder → notice → audit) when the task requires inspecting all four. Use `folder_notice_audit` when approvals are not part of the evidence. `audit_only` when only audit is checked.

## Common misjudgments and exclusion rules

1. **Stale employee profile summary**: `leave_balance_days` on `/api/employees` may not match the authoritative leave assignment. Always cross-check against `/api/payroll-ledgers`. Do not set `annual_days` / `balance_days` from the profile if an approved assignment exists with a different value. Set `profile_policy_ignored: true` when overriding.

2. **Draft leave assignment**: A leave assignment with `status: "Draft"` (and sometimes a name containing "Draft") must be placed in `excluded_leave_ids`, never used as the effective policy.

3. **Superseded leave assignment**: Also excluded. The superseded record was the prior policy version; the approved or submitted current one controls.

4. **Draft payroll assignment**: Must go in `excluded_payroll_ids` / `excluded_assignment_id`. A second salary assignment that is `Draft` with a higher base salary is a **trap** — the submitted one with the lower salary is authoritative. Never pick the draft to inflate numbers.

5. **Case summary treated as evidence**: The `summary` field on a case (and the XMODULE-77 cross-module case) is a hint. It says things like "Approval is final; closeout readiness must be verified…" — but the final control result comes from folder + notice + audit, not the summary text.

6. **Final approval mistaken for closeout**: Even with `APP-XXX-FINAL` decision `Approved`, if the folder is missing files or the notice is defective, the answer is `hold_for_folder_and_notice_defects` and `approval_closeout_gate` = `approval_not_sufficient_when_folder_or_notice_defective`.

7. **Audit scope leakage**: A single case (e.g. CASE-118) can have both a `leave.profile_mismatch` event AND a `folder.tag_missing` event. When the task scope is leave precedence only, the folder event goes in `excluded_audit_event_ids`. When the scope is document/notice only, the leave event is excluded.

8. **Notice defect — missing appeal instructions**: The most common defect. The case comment or audit `detail` mentions "lacks appeal instructions". Confirm in `defects` array as `missing_appeal_instructions`.

9. **Notice defect — missing ack deadline / waitlist status / correct policy**: Also from the `defects` array. Do not invent defect codes; use exactly the four allowed values.

10. **Missing required tag mistaken as present**: The case attachment text may say "Tag PolicyException2026 present" while the documents endpoint shows tags list actual contents. Trust the `/api/documents` endpoint's `tags` array over the attachment text description.

11. **Recruitment cost — partial sum**: `recruitment_cost_total` must include EVERY `cost_ledger` line item amount. Do not cherry-pick.

12. **Notice followup for selected candidate**: The selected candidate with an accepted offer does NOT need a rejection or waitlist notice — exclude them from `notice_followup_required`. Only waitlisted (need waitlist notice) and rejected (need rejection notice) candidates belong.

13. **Draft precheck treated as handoff**: Draft payroll precheck records do NOT satisfy the payroll handoff gate. The handoff must be `submitted_after_acceptance`. A draft precheck is not enough for `onboarding_handoff`.

14. **Waitlisted candidate reclassified as rejected**: The waitlisted followup action is `send_waitlist_notice` or `reissue_waitlist_notice_not_rejection`. Never send a rejection notice to a waitlisted candidate.

15. **URL**: Use `<remote-env-url>` not `127.0.0.1:<port>`.

## Pre-submission checklist

Before writing the final JSON:

1. **Leave**: Is `effective_leave_policy` / `annual_days` / `balance_days` / `assignment_id` from the approved/current-period assignment in `/api/payroll-ledgers` — NOT from the stale employee profile `leave_balance_days`?
2. **Leave exclusions**: Are all draft, superseded, voided, and obsolete leave assignment IDs in `excluded_leave_ids`?
3. **Payroll**: Is the selected salary assignment `status: Submitted`? Is the excluded one `status: Draft`? Is `base_salary` from the submitted assignment, not the draft?
4. **Folder**: Did you check `/api/documents` (or the case checklist attachment) and compute `missing_files` and `required_tag_present` exactly from the `files` / `required_files` / `tags` / `required_tags` arrays?
5. **Notice**: Did you inspect `/api/messages?q=<case_id>` (for HR cases) or `notice_packets` (for recruitment)? Are all `defects` values from the allowed set? Is `notice_evidence_source` / `notice_quality_source` correct (message vs packet)?
6. **Audit**: Does `audit_event_id` / `supporting_audit_event_ids` contain only events matching the task's `audit_scope`? Are adjacent (out-of-scope) events in `excluded_audit_event_ids`?
7. **Approval gate**: Does `approval_closeout_gate` reflect whether folder+notice are clean — independent of whether a final approval exists?
8. **Control result**: Does `final_control_result` / `control_result` match: clean → `approve_closeout`; folder/notice defective → `hold_for_folder_and_notice_defects`; payroll ready with matching accrual batch → `ready_with_monitoring`?
9. **Recruitment** (if applicable): Is `recruitment_cost_total` the sum of ALL cost_ledger amounts? Is `selected_offer_status` from the offer register? Are waitlisted/rejected candidate lists arrays containing only IDs? Is `draft_payroll_allowed false`? Is the handoff `submitted_after_acceptance`?
10. **Template match**: Is every field one of the template `allowed_values`? Are enums exact strings? Are arrays of IDs only (no labels/names)? Is the output pure JSON with no markdown or explanation?
