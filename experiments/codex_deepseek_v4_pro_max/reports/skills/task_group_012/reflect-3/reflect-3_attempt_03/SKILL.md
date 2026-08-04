## When to use this skill

Use this skill when solving PeopleOps people-lifecycle reconciliation and closeout tasks. These tasks involve verifying employee leave, payroll, recruitment, policy-case, folder-readiness, formal-notice, and audit evidence across a Northwind HRMS environment. The skill captures the reusable methodology, evidence-gathering workflow, and domain rules needed to produce correct answer-template JSON.

## Core methodology

1. **Gather all available API evidence first.** Read `/api/manifest` for the data inventory, then fetch every relevant collection endpoint and every case-detail endpoint that is listed in the task prompt. Do not skip endpoints that appear unrelated; cross-module evidence is the norm.
2. **Identify the business question the task is asking.** Each task targets a specific lifecycle gate: onboarding closeout, policy-case folder/notice review, recruitment reconciliation, leave-source precedence, or payroll-assignment readiness.
3. **Apply the source-precedence rules below** to select authoritative records and exclude non-authoritative ones.
4. **Map findings to the answer template using the exact normalized labels** the template provides. Never use free-text explanations where an enum is available.
5. **Return only valid JSON matching the template shape.** No markdown, no commentary.

## Source-precedence rules

### Leave records

- The **latest approved or submitted** leave assignment for the current period controls. Draft, voided, superseded, and obsolete leave records **must be excluded** even when the employee-profile summary differs.
- The employee-profile summary is a **convenience view only**; when an approved assignment exists, the assignment overrides the profile.
- Policy: LEAVE-SRC-001 section 2.1.

### Payroll / salary records

- Use the **current submitted** salary assignment. Draft planning assignments do **not** affect payroll readiness, accrual checks, or closeout decisions.
- Exclude any assignment whose status is `Draft` or `Superseded`. Only `Submitted` or `Approved` assignments are authoritative.
- Policy: PAY-SRC-001 section 3.4.

### Recruiting handoff

- A payroll handoff is created **only after** a selected candidate has an **accepted** offer. The handoff must be **submitted**; draft prechecks do not satisfy the assignment gate.
- Policy: PAY-SRC-001 section 4.2.

### Folder readiness

- A folder is **not ready** unless **all** required files and **all** required tags shown in the folder checklist are present.
- Policy: POL-DOCS-2026 section 5.1.

### Formal notice quality

- A formal notice is **defective** if it lacks any required element (appeal instructions, acknowledgement deadline, waitlist status, or correct policy reference). 
- Notice defects are identified by inspecting message bodies and notice packets, verified against the relevant policy text (HR-POL-014, LEAVE-SRC-001, etc.).
- Policy: HR-POL-014 section 7.1.

## Evidence-gathering workflow

### Step 1 — Read the manifest

Call `GET /api/manifest` to understand the data landscape (how many employees, cases, documents, messages, audit events, etc.).

### Step 2 — Collect all relevant evidence

For every task, pull these endpoints (filter client-side as needed):

- `GET /api/employees` — employee profiles (leave_balance_days, status, salary_band, department).
- `GET /api/cases` — case list; then `GET /api/cases/{case_id}` for each case mentioned in the prompt (gives approvals, attachments, comments, case-specific audit events).
- `GET /api/payroll-ledgers` — leave assignments, salary assignments, accrual records. Every record has a `record_type` and a `status`. Filter by employee.
- `GET /api/recruitment` — opening details, candidate lists with committee decisions, offer registers, cost ledgers, notice packets, payroll precheck records.
- `GET /api/documents` — folder checklists with required/actual files and tags.
- `GET /api/messages` — formal notices, their quality assessments, and defect lists.
- `GET /api/audit` — authoritative QA results. Each audit event has a `case_id`, `event` type, and `detail` field containing the QA verdict.
- `GET /api/policies` — policy documents that define the business rules. Always cross-check policy section text, especially the headings cited in audit events or case summaries.

### Step 3 — Cross-reference evidence sources

Do not rely on a single endpoint. For each claim, verify across at least two sources (e.g., case summary + audit detail, or payroll-ledger record + policy section).

### Step 4 — Separate supporting audit events from excluded ones

Audit events have different scopes. When the task is about **leave source precedence**, include only leave-scope audit events as supporting and **exclude** document/notice audit events. When the task is about **document/notice findings**, include only document/notice audit events and exclude leave or payroll audit events.

## Domain vocabulary for answer templates

These normalized labels appear across answer templates. Use them exactly as written.

### Leave source fields

- `leave_source`: `leave_assignment_history` | `employee_profile_summary` | `case_summary_only`
- `leave_precedence_source` / `precedence_source`: `approved_assignment_current_period` | `approved_assignment_over_profile` | `profile_summary_current_period` | `employee_profile_summary` | `case_summary_only`

### Payroll source fields

- `payroll_status` / `payroll_source_status`: `submitted` | `draft` | `superseded`
- `draft_exclusion_rule`: `exclude_draft_assignment` | `draft_allowed` | `exclude_superseded_only`

### Audit scope

- `audit_scope`: `document_notice_findings_only` | `leave_source_precedence_only` | `payroll_assignment_readiness`

### Control results

- `final_control_result` / `control_result`: `approve_closeout` | `hold_for_folder_and_notice_defects` | `ready_with_monitoring`
- `audit_result`: `profile_summary_stale` | `ready_with_monitoring` | `block_close`

### Case / folder / notice

- `folder_ready` is a boolean: `true` only when every required file and every required tag is present.
- `notice_quality` / `quality`: `valid` | `defective`
- `notice_defects`: subset of `["missing_ack_deadline", "missing_appeal_instructions", "missing_waitlist_status", "missing_correct_policy"]`
- `closeout_blockers`: subset of `["missing_required_files", "missing_required_tags", "defective_formal_notice"]`
- `notice_remediation_action`: `reissue_defective_notices` | `no_notice_action` | `send_new_offer_notice`

### Recruitment

- `selected_offer_status`: `accepted` | `draft` | `withdrawn` | `none`
- `candidate_status_source`: `interview_feedback_and_offer` | `case_summary_only` | `message_only`
- `candidate_outcome_control`: `committee_decision_with_offer_confirmation` | `message_status_only` | `case_summary_only`
- `waitlisted_followup_action`: `send_waitlist_notice` | `reissue_waitlist_notice_not_rejection` | `no_action`
- `rejected_followup_action`: `send_rejection_notice` | `no_action` | `reissue_rejection_notice`
- `payroll_handoff_gate`: `accepted_offer_and_submitted_assignment` | `accepted_offer_only` | `all_interviewed_candidates`
- `handoff_control_result`: `submitted_handoff_required_after_acceptance` | `submitted_handoff_required` | `no_handoff_required`
- `offer_exclusion_reason_for_waitlisted`: `no_accepted_status_or_offer` | `waitlisted_not_selected` | `already_rejected`
- `cost_source`: `recruitment_cost_ledger` | `case_summary_only`

### Actions

- `next_action`: `block_close_and_reissue_notice` | `approve_onboarding_close` | `open_records_remediation` | `update_employee_summary` | `no_action`
- `escalation_action`: `open_records_remediation` | `block_close_and_reissue_notice` | `no_action`
- `records_remediation_owner`: `Records` | `People Ops Compliance` | `Payroll QA`

## Common antipatterns to avoid

- **Using draft records as authoritative.** Always check the `status` field. Draft and superseded records are never authoritative for closeout or readiness decisions.
- **Using the employee-profile summary when an approved assignment exists.** The summary is a cached view; the assignment ledger is the system of record.
- **Including non-scope audit events in supporting evidence.** An audit event about folder tags does not support a leave-precedence decision. Filter by `event` type and `case_id` relevance.
- **Mixing free-text explanations with enums.** Every field that has an `allowed_values` list in the template must use one of those exact values.
- **Including task-specific or candidate-answer values in this skill.** The skill encodes the reusable rules, not the answers to any particular train or test task.

## Task-type recognition guide

When approaching a new task, classify it by the answer-template shape and the prompt keywords:

- **Onboarding closeout** — checks employee leave setup + payroll setup. Template has `employee_id`, `effective_leave_policy`, `annual_days`, `assignment_id`, `payroll_assignment_id`, `base_salary`, closeout action.
- **Policy-case folder/notice review** — checks folder readiness + formal notice quality for a specific case. Template has `case_id`, `folder_ready`, `missing_files`, `notice_quality`, `notice_defects`, approval detail.
- **Recruitment reconciliation** — reconciles candidate outcomes, offers, costs, notices, and payroll handoff for an opening. Template has `opening_id`, candidate arrays, `offer_id`, `recruitment_cost_total`.
- **Leave source precedence** — determines which leave policy/balance is authoritative when profile and assignment conflict. Template has `precedence_source`, `profile_policy_ignored`, `audit_result`.
- **Payroll assignment readiness** — verifies submitted salary assignment and accrual batch readiness. Template has `salary_assignment_id`, `accrual_ready`, `accrual_batch_id`, `draft_exclusion_rule`.

## Before submitting

1. Confirm every field in the answer template has been populated.
2. Confirm every `enum` field uses an exact value from the template's `allowed_values`.
3. Confirm every `list[string]` or `list[enum]` field contains only valid IDs or enum values.
4. Confirm numeric fields (`annual_days`, `base_salary`, `recruitment_cost_total`, `balance_days`) are derived from the correct source records.
5. Confirm boolean fields (`folder_ready`, `required_tag_present`, `profile_policy_ignored`, `accrual_ready`, `draft_payroll_allowed`) are backed by evidence.
