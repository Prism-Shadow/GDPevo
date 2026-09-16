---
name: peopleops-console
description: Solve PeopleOps Console business verification tasks by fetching API evidence, applying source-precedence and draft-exclusion rules, scoping audit events to the correct domain, and producing normalized JSON answers with enumerated business labels.
---

# PeopleOps Console Solver

This skill covers PeopleOps business verification workflows: onboarding closeout, case folder and notice review, recruitment reconciliation, leave source precedence, and payroll assignment readiness. Every task supplies an answer template and expects a single JSON object using the template's enumerated labels.

## Connection and Credentials

The prompt provides `<TASK_ENV_BASE_URL>`. Use these fixed credentials:

- Email: `ops.lead@peopleops.local`
- Password: `PeopleOps#2026`

All API responses are JSON. The solver reads data through GET endpoints; the only available POST endpoint is `/api/cases/{case_id}/comments`. The `/api/judge` endpoint is disabled and must not be called.

## Available Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/manifest` | Top-level navigation map of all workspaces and resources |
| `GET /api/summary` | High-level system summary |
| `GET /api/employees` | Employee directory with profile summaries |
| `GET /api/cases` | All cases index |
| `GET /api/cases/{case_id}` | Single case detail including approval history |
| `GET /api/policies` | Policy catalog |
| `GET /api/policies/{policy_id}` | Single policy document |
| `GET /api/payroll-ledgers` | Payroll assignment and accrual ledger records |
| `GET /api/recruitment` | Recruitment openings, candidates, and offers |
| `GET /api/documents` | Folder documents index |
| `GET /api/messages` | Formal notices and communications |
| `GET /api/notifications` | System notifications |
| `GET /api/audit` | Audit event index |
| `GET /api/audit/{audit_id}` | Single audit event detail |
| `GET /api/attachments/{attachment_id}` | Binary attachment content |

## General Method

1. **Read the prompt and answer template** first. Identify the workflow type and which fields the template requires. Each field's `allowed_values` are the only legal output labels.
2. **Fetch all relevant data** by calling the appropriate endpoints. Start broad (manifest, summary) and narrow to specific resources (employee, case, policy, ledger, audit). Use multiple parallel GET calls where possible.
3. **Apply the business rules** for the identified workflow (see sections below). Rules govern source precedence, draft exclusion, audit scoping, and final action determination.
4. **Produce exactly one JSON object** matching the template schema. Use only the enumerated labels from `allowed_values`. No markdown, no commentary, no extra text.

## Business Rules by Workflow

### Onboarding Closeout (leave and payroll verification)

**Source authority for leave**: An approved leave assignment in the current period is the authoritative record. The employee profile summary is stale when a submitted/approved assignment exists. Draft assignments are never authoritative.

Leave decision flow:
- Fetch the employee record, their leave assignments, the leave policies catalog, and audit events referencing the employee.
- Identify all leave assignment IDs. Classify each as `approved`/`submitted` (authoritative), `draft` (excluded), or `superseded` (excluded from effective determination).
- Select the most recent approved or submitted assignment for the current period. Its policy name becomes the effective leave policy. Its annual day count becomes the balance.
- All draft and superseded assignment IDs go into `excluded_leave_ids`.
- When an approved assignment is present, `leave_source` is `leave_assignment_history` and `leave_precedence_source` is `approved_assignment_current_period`.
- When only a profile summary is available with no approved assignment, `leave_source` is `employee_profile_summary` and `leave_precedence_source` is `profile_summary_current_period`.
- When the case summary alone must be relied on, `leave_source` is `case_summary_only` and `leave_precedence_source` is `case_summary_only`.

**Source authority for payroll**: A submitted payroll assignment is authoritative. Draft payroll assignments are excluded.

Payroll decision flow:
- Fetch payroll-ledger records for the employee.
- Identify submitted assignments (status `submitted`). Select the most recent submitted assignment; its ID, salary, and effective date are authoritative.
- All draft assignments go into `excluded_payroll_ids`.
- Payroll status reflects the selected assignment: `submitted`, `draft`, or `superseded`.
- `payroll_source_status` mirrors the status of the selected authoritative assignment.
- When a submitted assignment exists, `payroll_source_status` is `submitted`.

**Closeout action determination**:
- When both leave and payroll have clean submitted/approved records with no defects, `closeout_action` is `approve_onboarding_close`, `approval_closeout_gate` is `approval_sufficient_when_records_clean`, and `final_control_result` is `approve_closeout`.
- When records are defective (draft-only, missing, or conflicting), `closeout_action` is `block_close_and_reissue_notice` or `open_records_remediation`, `approval_closeout_gate` is `approval_not_sufficient_when_folder_or_notice_defective`, and `final_control_result` is `hold_for_folder_and_notice_defects`.
- When records are valid but need monitoring, `final_control_result` is `ready_with_monitoring`.

### Case Folder and Notice Review

**Evidence source order**: Always follow approval history, then folder contents, then notice packets, then audit events. The evidence source order (as a normalized label) is `approval_history_folder_notice_audit` when all sources are available; `folder_notice_audit` when approval history is not needed; `audit_only` when only audit evidence is relevant.

**Approval determination**:
- Fetch the case with its approval history (`/api/cases/{case_id}`). Identify the final approval event and the approving authority.
- Final decision options: `approved`, `approved_with_conditions`, `rejected`, `held`.

**Folder readiness**:
- Fetch documents for the case. Identify required documents by cross-referencing the case type and policy requirements.
- `folder_ready` is `true` only when all required files are present and the required tag is present.
- List any missing required files in `missing_files` (use exact filenames). Set `required_tag_present` based on whether the folder carries the required tag.

**Notice quality**:
- Fetch messages and notice packets for the case. Inspect the formal notice content.
- A notice is `valid` when it contains all required elements: acknowledgment deadline, appeal instructions, waitlist status (for relevant case types), and correct policy reference.
- A notice is `defective` when any required element is missing. `notice_defects` list the specific missing elements using only the allowed values: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- `notice_evidence_source` is `notice_packet_inspection` when notice packets are available; `message_notice_inspection` when only messages contain the notice; `case_summary_only` when neither source is available.

**Audit scoping**:
- Fetch audit events referencing the case. Classify each event by its domain: document/notice findings, leave source precedence, or payroll assignment readiness.
- For a case folder/notice review, the audit scope is `document_notice_findings_only`. Include only audit events that relate to document or notice findings as `supporting_audit_event_ids`. Exclude audit events from other domains in `excluded_audit_event_ids`.
- The primary `audit_event_id` is the most relevant audit event for the document/notice scope.

**Next action determination**:
- When `folder_ready` is `false` or `notice_quality` is `defective`: `next_action` is `block_close_and_reissue_notice`, `approval_closeout_gate` is `approval_not_sufficient_when_folder_or_notice_defective`, `final_control_result` is `hold_for_folder_and_notice_defects`.
- `closeout_blockers` lists the specific blockers: include `missing_required_files` when files are missing, `missing_required_tags` when the tag is absent, `defective_formal_notice` when the notice is defective.
- When folder is ready and notice is valid: `approval_closeout_gate` is `approval_sufficient_when_records_clean`, `final_control_result` is `approve_closeout`.
- `folder_required_tag_action` is `no_tag_action` when the tag is already present; `add_required_tag` when missing.
- `escalation_action`: `open_records_remediation` when folder defects require Records team involvement; `block_close_and_reissue_notice` when the notice must be reissued; `no_action` when no escalation is needed.
- `records_remediation_owner`: `Records` for document/file issues, `People Ops Compliance` for compliance issues, `Payroll QA` for payroll-related issues.
- `notice_remediation_action`: `reissue_defective_notices` when notice is defective, `send_new_offer_notice` when a new offer notice is needed, `no_notice_action` when no notice remediation is required.

### Recruitment Reconciliation

**Candidate outcome determination**:
- Fetch the recruitment opening, its candidates, interviews, and offers.
- `candidate_status_source` is `interview_feedback_and_offer` when interview feedback and offer records are available; `case_summary_only` when only the case summary is available; `message_only` when only messages contain status information.
- `candidate_outcome_control` is `committee_decision_with_offer_confirmation` when a committee decision exists and the offer record confirms it; `message_status_only` when only message-based status is available; `case_summary_only` when only the case summary is available.
- Selected candidate: the candidate with an accepted offer. `selected_offer_status` reflects the offer status: `accepted`, `draft`, `withdrawn`, or `none` if no offer exists.
- Waitlisted candidates: candidates explicitly marked as waitlisted in interview feedback or case records, who do not have an accepted offer.
- Rejected candidates: candidates explicitly marked as rejected.
- A candidate appears in only one of the three outcome lists.

**Offer and payroll handoff**:
- The `offer_id` is the offer associated with the selected candidate. `offer_base_salary` is the salary from that offer.
- `onboarding_handoff`: `create_payroll_precheck` when the selected candidate has an accepted offer and payroll setup is needed; `create_submitted_assignment_after_acceptance` when a submitted assignment must follow acceptance; `no_payroll_handoff` when no payroll action is needed.
- `payroll_handoff_gate`: `accepted_offer_only` when only accepted offers trigger handoff; `accepted_offer_and_submitted_assignment` when both acceptance and a submitted assignment are required; `all_interviewed_candidates` when all interviewed candidates trigger handoff.
- `payroll_assignment_status_required`: `submitted_after_acceptance` when the assignment must be submitted after the candidate accepts; `submitted` when any submitted status is sufficient; `draft_allowed` when drafts are acceptable.
- `draft_payroll_allowed`: `false` when drafts are excluded from payroll decisions; `true` when drafts are acceptable.
- `offer_exclusion_reason_for_waitlisted`: `no_accepted_status_or_offer` when waitlisted candidates lack an accepted offer; `waitlisted_not_selected` when waitlisted means not selected; `already_rejected` when the candidate was already rejected.
- `handoff_control_result`: `submitted_handoff_required_after_acceptance` when a submitted handoff must follow acceptance; `submitted_handoff_required` when a submitted handoff is required regardless; `no_handoff_required` when no handoff is needed.

**Recruitment costs**:
- `cost_source` is `recruitment_cost_ledger` when ledger data is available; `case_summary_only` otherwise.
- `recruitment_cost_total` is the numeric sum of all cost line items from the recruitment cost ledger for the opening.

**Notice follow-up**:
- `notice_quality_source`: `notice_packet_inspection` when notice packets are available; `message_notice_inspection` when only messages contain notice data; `case_summary_only` otherwise.
- `notice_followup_required` lists candidate IDs that need follow-up notices (waitlisted need waitlist notices, rejected need rejection notices).
- `waitlisted_followup_action`: `send_waitlist_notice` when waitlisted candidates lack a waitlist notice; `reissue_waitlist_notice_not_rejection` when an existing notice needs reissue; `no_action` when no follow-up is needed.
- `rejected_followup_action`: `send_rejection_notice` when rejected candidates lack a rejection notice; `reissue_rejection_notice` when an existing notice needs reissue; `no_action` when no follow-up is needed.

### Leave Source Precedence

This workflow resolves conflicts between an employee profile summary and leave assignment records.

- Fetch the employee, their leave assignments, the relevant policy document, and audit events referencing the employee.
- When an approved leave assignment exists for the current period and the policy document and audit detail confirm it: the approved assignment overrides the stale profile summary.
- `precedence_source`: `approved_assignment_over_profile` when an approved assignment overrides the profile; `employee_profile_summary` when the profile is authoritative; `case_summary_only` when only the case summary is available.
- `leave_precedence_source` mirrors the precedence: `approved_assignment_current_period` when the approved assignment is authoritative; `profile_summary_current_period` when the profile summary is authoritative; `case_summary_only` otherwise.
- `profile_policy_ignored` is `true` when the profile summary's policy is stale relative to an approved assignment; `false` otherwise.
- `balance_days` comes from the authoritative assignment, not the stale profile.
- `audit_scope` is `leave_source_precedence_only`. `supporting_audit_event_ids` lists audit events that confirm the leave precedence decision. `excluded_audit_event_ids` lists audit events from other domains (document/notice, payroll) that must be excluded from this leave-scope decision.
- `audit_result`: `profile_summary_stale` when the profile is outdated relative to an approved assignment; `ready_with_monitoring` when records are consistent but need monitoring; `block_close` when records are conflicting and closeout must be blocked.
- `next_action`: `update_employee_summary` when the profile summary needs updating to match the authoritative assignment; `open_records_remediation` when records need broader remediation; `no_action` when no action is needed.

### Payroll Assignment and Accrual Readiness

- Fetch payroll-ledger records for the employee, including assignment records and accrual batches.
- Select the submitted payroll assignment. Its ID is `salary_assignment_id`, its salary is `base_salary`, its effective date is `effective_date`.
- Draft assignments are excluded: `excluded_assignment_id` is the draft assignment ID, `draft_exclusion_rule` is `exclude_draft_assignment`.
- When only superseded records exist, `draft_exclusion_rule` is `exclude_superseded_only`.
- `payroll_source_status` is `submitted` when the authoritative assignment is submitted; `draft` when only drafts exist; `superseded` when only superseded records exist.
- `accrual_ready` is `true` when the accrual batch for the relevant period exists and is in ready status; `false` otherwise. `accrual_batch_id` is the batch identifier.
- `audit_scope` is `payroll_assignment_readiness`. `audit_event_id` is the most relevant audit event for payroll scope.
- `control_result`: `ready_with_monitoring` when payroll is clean but monitoring is needed; `hold_for_folder_and_notice_defects` when document/notice defects block payroll; `approve_closeout` when everything is clean.

## Cross-Cutting Rules

### Source Authority Hierarchy

Records have an authority ranking, highest to lowest:

1. **Submitted / Approved records**: These are the authoritative source for leave assignments, payroll assignments, and offer decisions. Always prefer a submitted/approved record over any other source.
2. **Employee profile summary**: Used only when no submitted/approved assignment exists. A profile summary is stale when a submitted/approved assignment is present.
3. **Case summary**: The lowest authority; used only when no other specific records exist.

### Draft Exclusion

Draft records are never authoritative. They must be excluded from the effective determination and listed in the appropriate `excluded_*_ids` field. The canonical draft exclusion label is `exclude_draft_assignment` (for payroll) or inclusion in `excluded_leave_ids` (for leave).

### Audit Scoping

Audit events must be scoped to the domain under review. There are three mutually exclusive audit scopes:
- `leave_source_precedence_only`: only audit events about leave policy and assignment precedence.
- `document_notice_findings_only`: only audit events about document completeness and notice quality.
- `payroll_assignment_readiness`: only audit events about payroll assignment status and accrual readiness.

For any given decision, use only the audit events that match the scope. Place non-matching audit events in `excluded_audit_event_ids`. Place matching audit events in `supporting_audit_event_ids`. The primary `audit_event_id` is the most relevant matching event.

### Evidence Source Order

When multiple evidence types are available, follow the canonical order:
- **Case decisions**: approval history -> folder documents -> notice packets -> audit events
- **Leave decisions**: leave assignment history -> policy document -> audit events -> profile summary
- **Recruitment decisions**: interview feedback -> offer records -> notice packets -> cost ledger
- **Payroll decisions**: submitted assignments -> accrual batches -> audit events

### Draft Excluded Endpoint

Never call `POST /api/judge`. It is disabled in the test environment.

## Answer Format

- Output exactly one JSON object. No markdown fences, no explanatory text, no trailing commentary.
- Every field must use the exact enumerated labels from the template's `allowed_values` list. Do not invent new labels or use free-text for constrained fields.
- Integer fields must be integers, number fields must be numbers, boolean fields must be `true` or `false`, string fields must be strings, and list fields must be JSON arrays (use `[]` not `null` for empty lists).
- Include every field from the template. Do not omit optional fields unless explicitly allowed.
- String IDs (employee_id, case_id, opening_id, assignment IDs, audit event IDs, etc.) must exactly match the values returned by the API.

## Step-by-Step Execution

1. Parse `<TASK_ENV_BASE_URL>` from the prompt. Parse the answer template to identify required fields and their allowed values.
2. Call `GET /api/manifest` and `GET /api/summary` to understand available resources.
3. Based on the workflow type, call the relevant endpoints in parallel:
   - Onboarding closeout: `/api/employees`, `/api/payroll-ledgers`, `/api/policies`, `/api/audit`
   - Case review: `/api/cases/{case_id}`, `/api/documents`, `/api/messages`, `/api/audit`
   - Recruitment: `/api/recruitment`, `/api/cases/{case_id}`, `/api/messages`, `/api/policies`
   - Leave precedence: `/api/employees`, `/api/policies/{policy_id}`, `/api/audit`
   - Payroll readiness: `/api/payroll-ledgers`, `/api/audit`
4. Apply the business rules from the relevant workflow section above to determine each field's value.
5. Construct the JSON object and emit it as the final response.
