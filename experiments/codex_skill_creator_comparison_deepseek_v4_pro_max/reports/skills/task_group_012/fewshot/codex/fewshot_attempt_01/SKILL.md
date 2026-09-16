---
name: people-ops-console
description: Navigate the Northwind People Lifecycle Portal (PeopleOps Console) for HRMS verification tasks. Use when Codex needs to verify onboarding closeouts, review case folders and formal notices for defects, reconcile recruitment outcomes and costs, resolve leave source precedence disputes, validate payroll assignment readiness and accrual checks, inspect audit events, policies, documents, messages, and employee records via the task-environment REST API. The console exposes employees, cases, policies, payroll ledgers, recruitment pipelines, documents, messages, notifications, and audit logs. Use this skill whenever the task references a PeopleOps Console, Northwind HRMS, employee verification, policy case review, recruitment reconciliation, leave precedence, or payroll readiness.
---

# People Ops Console

## Overview

This skill covers the Northwind People Lifecycle Portal, a REST API at `<TASK_ENV_BASE_URL>` that surfaces HRMS data across nine business modules. Every task follows the same core loop: read the task description, fetch data from the relevant endpoints, apply the business rules encoded in policies/audit/ledgers, and return a JSON answer matching the provided answer template.

## Quick Start

The base URL is always `<TASK_ENV_BASE_URL>`. No credentials are required. Hit `/api/manifest` first to confirm the endpoint catalog, then fetch the concrete records you need.

```bash
curl -s <TASK_ENV_BASE_URL>/api/manifest | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/summary | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/employees | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/cases | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/payroll-ledgers | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/policies | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/audit | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/recruitment | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/documents | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/messages | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/notifications | python3 -m json.tool
```

Individual case detail and policy detail endpoints also exist:

```bash
curl -s <TASK_ENV_BASE_URL>/api/cases/{case_id} | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/policies/{policy_id} | python3 -m json.tool
curl -s <TASK_ENV_BASE_URL>/api/audit/{audit_id} | python3 -m json.tool
```

See [references/api_endpoints.md](references/api_endpoints.md) for the full endpoint catalog with response shapes.

## Core Workflow

Every task follows this sequence:

1. Read the prompt to identify the target entities (employee, case, opening) and the answer template schema.
2. Fetch all records from the relevant endpoints in parallel. Do not cherry-pick; you need the full dataset to apply exclusion rules correctly.
3. Apply the business rules encoded in policy documents, audit events, and ledger records. See [references/policies.md](references/policies.md) for the extracted rules.
4. Construct the JSON answer using only the normalized enum values from the answer template.
5. Return pure JSON -- no markdown, no explanatory text.

## Task Types

### Onboarding Closeout Verification

Target: an employee in Onboarding status. Use `/api/employees` for the profile, `/api/payroll-ledgers` for leave assignments and salary assignments filtered by the employee_id. Apply:

- **Leave source precedence**: the latest Approved leave assignment for the period controls; Draft and Superseded records are excluded.
- **Payroll source precedence**: the Submitted salary assignment controls; Draft assignments are excluded.
- **Closeout gate**: approve only when both leave and payroll records are clean (no defective assignments, no draft-only sources). If records are contested or incomplete, block close or open remediation.

Output fields: `employee_id`, `effective_leave_policy`, `leave_source`, `annual_days`, `assignment_id`, `excluded_leave_ids`, `payroll_assignment_id`, `base_salary`, `payroll_status`, `excluded_payroll_ids`, `closeout_action`, `leave_precedence_source`, `payroll_source_status`, `approval_closeout_gate`, `final_control_result`.

### Case Folder and Notice Review

Target: a case (e.g., CASE-RW-221, CASE-445). Use the case detail endpoint (`/api/cases/{case_id}`) for approvals and attachments. Cross-reference `/api/documents` for the case document folder (find by matching reference in attachment or by document title) and `/api/messages` for formal notice quality.

- **Folder readiness**: all `required_files` and `required_tags` must be present. Check against the document's `files` and `tags` arrays.
- **Notice quality**: inspect the message record for `quality` and `defects`. The allowed defects are `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- **Audit evidence**: use the audit event with the matching `case_id` and the correct audit scope (`document_notice_findings_only`). Exclude audit events whose scope is unrelated (e.g., exclude leave-source or payroll-scope audits from a document/notice decision).
- **Closeout decision**: when folder has missing files/tags or notice has defects, the gate is `approval_not_sufficient_when_folder_or_notice_defective` and blockers should list the specific defects. Evidence source order is `approval_history_folder_notice_audit`.

Output fields: `case_id`, `final_decision`, `approval_authority`, `approval_event_id`, `folder_ready`, `missing_files`, `required_tag_present`, `notice_quality`, `notice_defects`, `audit_event_id`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, `audit_scope`, `next_action`, `approval_closeout_gate`, `closeout_blockers`, `evidence_source_order`, `folder_required_tag_action`, `notice_evidence_source`, `escalation_action`, `records_remediation_owner`, `notice_remediation_action`, `final_control_result`.

### Recruitment Reconciliation

Target: a recruitment opening (e.g., REQ-DA-77). Use `/api/recruitment` for the pipeline. The recruitment object contains `candidates` (with committee_decision), `offer_register`, `cost_ledger`, `notice_packets`, `payroll_precheck_records`.

- **Candidate outcomes**: map committee_decision to selected/waitlisted/rejected. Candidate IDs only in the output arrays.
- **Cost total**: sum all `amount` values from `cost_ledger`.
- **Notice follow-up**: waitlisted and rejected candidates without sent notices need follow-up; candidates with defective notices need reissue. The notice quality source is `notice_packet_inspection` when packets exist, otherwise fall back to `message_notice_inspection` or `case_summary_only`.
- **Payroll handoff**: only the accepted (selected) candidate triggers a payroll handoff. The handoff must be Submitted, not Draft. Draft `payroll_precheck_records` do not satisfy the gate. Selected offer status is `accepted`, cost source is `recruitment_cost_ledger`, candidate status source is `interview_feedback_and_offer`.

Output fields: `opening_id`, `selected_candidate`, `waitlisted_candidates`, `rejected_candidates`, `offer_id`, `offer_base_salary`, `recruitment_cost_total`, `notice_followup_required`, `onboarding_handoff`, plus all control/source/status fields from the template.

### Leave Source Precedence

Target: an employee whose profile summary may conflict with an approved leave assignment. Use `/api/employees` for the profile, `/api/payroll-ledgers` for leave assignments, `/api/policies/LEAVE-SRC-001` for the precedence rule, `/api/audit` for audit evidence.

- **Precedence rule**: an Approved leave assignment overrides the employee profile summary when the ledger, policy, and audit confirm it. Use `approved_assignment_current_period` as the leave_precedence_source and `approved_assignment_over_profile` as the precedence_source.
- **Audit scope**: use only `leave_source_precedence_only` audits; exclude `document_notice_findings_only` or `payroll_assignment_readiness` audits from the leave decision.
- **Profile staleness**: when the audit detail says `profile_summary_stale`, the profile policy is ignored (`profile_policy_ignored: true`) and the next action is `update_employee_summary`.

Output fields: `employee_id`, `effective_leave_policy`, `assignment_id`, `balance_days`, `precedence_source`, `profile_policy_ignored`, `audit_event_id`, `audit_result`, `next_action`, `leave_precedence_source`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, `audit_scope`.

### Payroll Assignment Readiness

Target: an employee whose salary assignment and accrual batch need validation. Use `/api/payroll-ledgers` for salary assignments, `/api/audit` for readiness audit.

- **Source rule**: use the Submitted salary assignment; exclude Draft assignments (`exclude_draft_assignment`). The payroll source status is `submitted`.
- **Accrual check**: a Submitted salary assignment that matches an accrual batch is ready. The audit confirms readiness with `ready_with_monitoring`.
- **Audit scope**: `payroll_assignment_readiness`.

Output fields: `employee_id`, `salary_assignment_id`, `base_salary`, `effective_date`, `excluded_assignment_id`, `accrual_ready`, `accrual_batch_id`, `audit_event_id`, `control_result`, `payroll_source_status`, `draft_exclusion_rule`, `audit_scope`.

## Business Rules Quick Reference

See [references/policies.md](references/policies.md) for the complete extracted business rules from all four policies. The key rules are:

| Rule | Policy | Summary |
|------|--------|---------|
| Leave assignment source | LEAVE-SRC-001 2.1 | Latest approved/submitted assignment for the period controls; draft, voided, and obsolete excluded |
| Payroll salary source | PAY-SRC-001 3.4 | Current submitted salary assignment controls base salary; draft planning assignments excluded |
| Recruiting payroll handoff | PAY-SRC-001 4.2 | Handoff created only after selected candidate has accepted offer; handoff must be submitted, draft prechecks do not satisfy |
| Folder readiness | POL-DOCS-2026 5.1 | Folder not ready unless all required files and required tags from checklist are present |
| Remote work notice | HR-POL-014 7.1 | International exceptions require appeal instructions and acknowledgement deadline in formal notice |

## Answer Templates

Every task provides an `answer_template.json` in its payloads. The template defines the output schema with allowed enum values. Every field value must come from the template's `allowed_values` list -- never use free-text explanations for gate, source, status, scope, or result fields.

Load the template file from `input/payloads/answer_template.json` before constructing the answer. Match its structure exactly.

## Enum Value Glossary

The templates draw from a closed set of normalized business labels. See [references/policies.md](references/policies.md) for the full glossary with definitions, but the critical ones:

- **Leave source**: `leave_assignment_history` (from ledger), `employee_profile_summary`, `case_summary_only`
- **Payroll status**: `submitted`, `draft`, `superseded`
- **Closeout gate**: `approval_sufficient_when_records_clean`, `approval_not_sufficient_when_folder_or_notice_defective`
- **Final control**: `approve_closeout`, `hold_for_folder_and_notice_defects`, `ready_with_monitoring`
- **Notice quality**: `valid`, `defective`
- **Audit scope**: `document_notice_findings_only`, `leave_source_precedence_only`, `payroll_assignment_readiness`
- **Evidence source order**: `approval_history_folder_notice_audit`, `folder_notice_audit`, `audit_only`
- **Candidate outcome control**: `committee_decision_with_offer_confirmation`, `message_status_only`, `case_summary_only`
- **Handoff control**: `submitted_handoff_required_after_acceptance`, `submitted_handoff_required`, `no_handoff_required`
