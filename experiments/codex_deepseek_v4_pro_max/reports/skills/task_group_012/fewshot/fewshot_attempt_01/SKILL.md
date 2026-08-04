## PeopleOps HR Console — Structured Verification Skill

This skill enables an agent to perform structured PeopleOps verification, reconciliation, inspection, and closeout tasks against the PeopleOps HR Console API. The agent navigates employee profiles, leave and payroll assignments, recruitment pipelines, case folders, policy documents, audit events, messages, notices, and cost ledgers — then returns a JSON decision packet using only normalized business labels drawn from the task answer template.

### Before Starting Any Task

Locate and read `input/payloads/answer_template.json`. This file declares every expected field, its type (`string`, `integer`, `number`, `boolean`, `list[string]`), and — for enum fields — the exact set of allowed values. Every field you return must match the template's structure exactly, and every enum field must use one of its listed allowed values. Never invent a value outside the template.

### Environment

Connect to the PeopleOps Console at the base URL provided by the task runner (`<TASK_ENV_BASE_URL>`). All API endpoints are read-only `GET` except for case comments (`POST`). No authentication headers are required for API calls. Use the credentials from `environment_access.md` (`ops.lead@peopleops.local` / `PeopleOps#2026`) only when browser login is needed.

### API Endpoints

```
GET  /
GET  /api/manifest
GET  /api/summary
GET  /api/employees
GET  /api/cases
GET  /api/cases/{case_id}
GET  /api/policies
GET  /api/policies/{policy_id}
GET  /api/payroll-ledgers
GET  /api/recruitment
GET  /api/documents
GET  /api/messages
GET  /api/notifications
GET  /api/audit
GET  /api/audit/{audit_id}
GET  /api/attachments/{attachment_id}
POST /api/cases/{case_id}/comments   (JSON body: author, created_at, visibility, body)
```

Always start by fetching `/api/manifest` to understand the current data model and `/api/summary` for cross-entity counts. Then drill into entity-specific endpoints as the task requires.

### Business Rules

#### Record Selection and Source Precedence

- **Draft exclusion**: Always exclude records labelled `DRAFT` or with a draft status indicator. Prefer `submitted` or `approved` records.
- **Payroll assignments**: Use the `submitted` payroll assignment. Never use a draft payroll assignment for salary, effective date, or assignment identity.
- **Leave assignments**: An approved leave assignment in the assignment-history record overrides a stale employee-profile summary when the leave ledger, policy document, and audit detail all confirm the approved assignment.
- **Leave source precedence rule**: `approved_assignment_current_period` — the approved assignment for the current period is authoritative.
- **Profile vs. assignment conflict**: When the employee profile summary shows a policy that contradicts an approved leave assignment, ignore the profile policy and follow the approved assignment.

#### Case Folder and Notice Inspection

- Determine folder readiness by checking whether every required file listed in the case definition is present in the document list.
- Report any missing required files by filename.
- Inspect formal notice packets for completeness. A defective notice is one missing required elements such as appeal instructions.
- Tag presence alone is not sufficient; verify the tag value matches the required value.

#### Recruitment Reconciliation

- Candidate outcomes come from interview feedback and offer status. An accepted offer confirms selection; other candidates are waitlisted or rejected based on committee decision.
- Sum all recruiting-campaign ledger entries to compute `recruitment_cost_total`.
- Waitlisted candidates require a waitlist notice; rejected candidates require a rejection notice.
- Payroll handoff is gated on an accepted offer: only accepted candidates get a payroll precheck handoff.

#### Audit Evidence

- When an audit event supports a leave, payroll, document, or notice finding, include its ID in `supporting_audit_event_ids`.
- When an adjacent audit event belongs to a different scope (e.g., document/notice findings vs. leave-source precedence), list it in `excluded_audit_event_ids`.
- Cite the primary audit event in `audit_event_id`.

### Normalized Business Label Vocabulary

Use only labels from the tables below. Do not invent free-text explanations for fields that expect normalized labels.

#### Source and Precedence

| Field | Labels |
|---|---|
| `leave_precedence_source` | `approved_assignment_current_period`, `approved_assignment_over_profile`, `profile_summary_current_period`, `case_summary_only` |
| `leave_source` | `leave_assignment_history` |
| `payroll_source_status` | `submitted`, `draft`, `superseded` |
| `draft_exclusion_rule` | `exclude_draft_assignment`, `draft_allowed`, `exclude_superseded_only` |
| `candidate_status_source` | `interview_feedback_and_offer`, `case_summary_only`, `message_only` |
| `candidate_outcome_control` | `committee_decision_with_offer_confirmation` |
| `cost_source` | `recruitment_cost_ledger` |
| `notice_quality_source` | `notice_packet_inspection` |
| `evidence_source_order` | `approval_history_folder_notice_audit`, `folder_notice_audit`, `audit_only` |
| `notice_evidence_source` | `notice_packet_inspection` |
| `precedence_source` | `approved_assignment_over_profile`, `employee_profile_summary`, `case_summary_only` |

#### Gates and Controls

| Field | Labels |
|---|---|
| `approval_closeout_gate` | `approval_sufficient_when_records_clean`, `approval_not_sufficient_when_folder_or_notice_defective` |
| `final_control_result` | `approve_closeout`, `hold_for_folder_and_notice_defects`, `ready_with_monitoring` |
| `control_result` | `ready_with_monitoring`, `hold_for_folder_and_notice_defects`, `approve_closeout` |
| `payroll_handoff_gate` | `accepted_offer_only` |
| `payroll_assignment_status_required` | `submitted_after_acceptance` |
| `handoff_control_result` | `submitted_handoff_required_after_acceptance` |
| `draft_payroll_allowed` | `false` |
| `offer_exclusion_reason_for_waitlisted` | `no_accepted_status_or_offer` |

#### Audit Scope

| Field | Labels |
|---|---|
| `audit_scope` | `document_notice_findings_only`, `leave_source_precedence_only`, `payroll_assignment_readiness` |
| `audit_result` | `profile_summary_stale` |

#### Actions, Decisions, and Status

| Field | Labels |
|---|---|
| `closeout_action` | `approve_onboarding_close`, `block_close_and_reissue_notice`, `open_records_remediation` |
| `next_action` | `block_close_and_reissue_notice`, `update_employee_summary`, `open_records_remediation`, `approve_onboarding_close`, `no_action` |
| `final_decision` | `approved_with_conditions`, `approved`, `rejected`, `held` |
| `approval_authority` | `HR Director` |
| `notice_quality` | `defective`, `valid` |
| `notice_defects` | `missing_appeal_instructions`, `missing_ack_deadline`, `missing_waitlist_status`, `missing_correct_policy` |
| `folder_ready` | `true` / `false` |
| `required_tag_present` | `true` / `false` |
| `folder_required_tag_action` | `no_tag_action` |
| `closeout_blockers` | `missing_required_files`, `missing_required_tags`, `defective_formal_notice` |
| `escalation_action` | `open_records_remediation` |
| `records_remediation_owner` | `Records`, `People Ops Compliance`, `Payroll QA` |
| `notice_remediation_action` | `reissue_defective_notices` |
| `selected_offer_status` | `accepted` |
| `waitlisted_followup_action` | `send_waitlist_notice` |
| `rejected_followup_action` | `send_rejection_notice` |
| `onboarding_handoff` | `create_payroll_precheck` |
| `payroll_status` | `submitted` |
| `profile_policy_ignored` | `true` (when approved assignment overrides profile) |
| `accrual_ready` | `true` / `false` |

### Answer Format

- Return a single flat JSON object.
- Use the exact field names from the answer template provided in the task. If the task references `input/payloads/answer_template.json`, match its structure precisely.
- Every field that expects a normalized label must use one of the labels above. Do not write free-text for gated fields.
- String-valued fields whose values are not constrained by an enum (e.g., employee id, case id, policy name) must carry the exact identifiers as they appear in the API records.
- Arrays (e.g., candidate IDs, excluded assignment IDs, missing files) must contain string identifiers only — no objects, no nulls, no commentary.
- Numeric fields (`base_salary`, `annual_days`, `balance_days`, `recruitment_cost_total`) must be plain numbers.
- Boolean fields must be JSON `true` or `false`.
- Return only the JSON object. Do not wrap it in markdown fences unless the task instructions explicitly permit it.

### Task-Workflow Patterns

Each PeopleOps task follows a common pipeline:

1. **Orient**: Fetch `/api/manifest` and `/api/summary` to confirm the available entity types and counts.
2. **Load Template**: Read `input/payloads/answer_template.json` to understand every required field, its type, and allowed enum values.
3. **Select**: Based on the task prompt, pull the relevant entity collections (`/api/employees`, `/api/cases`, `/api/recruitment`, `/api/policies`, `/api/payroll-ledgers`, `/api/audit`, `/api/documents`, `/api/messages`, `/api/notifications`).
4. **Drill Down**: For employee tasks, fetch the specific employee summary. For case tasks, fetch the case detail. For recruitment, fetch the opening. For policy tasks, fetch individual policies.
5. **Filter**: Apply the business rules above to exclude drafts, prefer submitted/approved records, and resolve source-precedence conflicts.
6. **Inspect**: For case tasks, enumerate required files vs. present files. For notice tasks, inspect notice packet contents for completeness. For recruitment, cross-reference offer status with candidate lists.
7. **Evidence**: Pull audit events that directly support findings. Separate audit events that belong to a different scope into excluded lists.
8. **Assemble**: Build the JSON answer using only allowed enum values from the template. Every gate, source, scope, status, control-result, and action field must use a label from the template's allowed-values list.
9. **Return**: Output only the JSON object.

### Choosing the Right Enum Value

When the answer template offers multiple allowed values for an enum field, use these heuristics:

- **Draft exclusion**: Any status field about a record should be `submitted` or `approved`, never `draft`. Any exclusion rule field should be `exclude_draft_assignment`.
- **Source authority**: `approved_assignment_current_period` is the canonical label when an approved leave or payroll assignment record is the source of truth. `approved_assignment_over_profile` is used specifically when resolving a conflict between an employee profile and an approved assignment.
- **Folder/notice defects**: When required files are missing, use `missing_required_files` as a blocker. When a notice omits required content, use the specific defect label (e.g., `missing_appeal_instructions`).
- **Audit scope**: Match the audit scope label to the type of decision being made — `leave_source_precedence_only` for leave-authority decisions, `document_notice_findings_only` for folder and notice inspections, `payroll_assignment_readiness` for payroll and accrual readiness checks.
- **Control result and gate**: `approve_closeout` / `approval_sufficient_when_records_clean` when all checks pass with no defects. `hold_for_folder_and_notice_defects` / `approval_not_sufficient_when_folder_or_notice_defective` when folder or notice defects are found. `ready_with_monitoring` when the record is clean but ongoing monitoring is advised.
