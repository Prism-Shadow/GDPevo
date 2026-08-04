---
name: peopleops-console
description: >-
  Drive the PeopleOps Console through its REST API to verify employee
  onboarding closeout, case folder and notice readiness, recruitment
  handoff, leave source precedence, and payroll assignment readiness.
  Use when a task requires inspecting employee records, case folders,
  policy documents, audit events, recruitment ledgers, or payroll
  assignments and returning a structured JSON decision using normalized
  business labels from a supplied answer template.
---

# PeopleOps Console Skill

## Overview

Access the PeopleOps Console REST API to gather facts across employees,
cases, policies, payroll, recruitment, documents, messages, notifications,
and audit events and produce a structured decision payload. Every task
provides an answer template whose field values must come exclusively from
the enumerated business labels; free-text explanations are replaced by
normalized labels drawn from the template.

## Environment & Authentication

- Base URL: `<TASK_ENV_BASE_URL>` (default `http://task-env:9012/`)
- API authentication: none
- Browser / interactive login (only when a visual login page is needed):
  - Username: `ops.lead@peopleops.local`
  - Password: `PeopleOps#2026`

All data gathering MUST use the GET endpoints listed below. The single
POST endpoint is for writing case comments only.

## Available API Endpoints

### Read-only (GET)

| Endpoint | Purpose |
|---|---|
| `GET /` | Root landing page |
| `GET /api/manifest` | Full manifest of available objects |
| `GET /api/summary` | High-level cross-entity summary |
| `GET /api/employees` | Employee directory |
| `GET /api/cases` | All cases |
| `GET /api/cases/{case_id}` | Single case detail |
| `GET /api/policies` | Policy catalogue |
| `GET /api/policies/{policy_id}` | Single policy document |
| `GET /api/payroll-ledgers` | Payroll assignment and salary records |
| `GET /api/recruitment` | Recruitment openings, candidates, offers, costs |
| `GET /api/documents` | Document / file registry |
| `GET /api/messages` | Messages and notices |
| `GET /api/notifications` | Notification records |
| `GET /api/audit` | All audit events |
| `GET /api/audit/{audit_id}` | Single audit event detail |
| `GET /api/attachments/{attachment_id}` | Individual attachment content |

### Write (POST)

| Endpoint | Purpose |
|---|---|
| `POST /api/cases/{case_id}/comments` | Append a comment to a case |

POST body: `{"author":"<string>","created_at":"<string>","visibility":"<string>","body":"<string>"}`

## Workflow: How to Approach Any Task

1. **Read the prompt carefully.** Identify the primary entity (employee,
   case, opening) and the decision type (onboarding closeout, folder/notice
   review, recruitment handoff, leave precedence, payroll readiness).

2. **Find the answer template** at `input/payloads/answer_template.json`.
   Every field whose type is `enum` MUST be filled with exactly one of the
   `allowed_values`. Never invent a label.

3. **Gather facts from the API.** Use `curl` to the appropriate endpoints.
   Fetch related entities transitively (e.g. find the employee, then their
   leave assignments and payroll entries; find the case, then its folder
   documents, approval events, messages/notices, and audit trail).

4. **Apply record-precedence rules** (see below) to select the
   authoritative record set and exclude draft, superseded, or stale
   entries.

5. **Assemble the JSON answer** matching the template structure. Use
   normalized labels for every gate, source, status, scope, and
   control-result field.

6. **Output only the final JSON.** Unless the prompt explicitly requests
   explanatory text, write raw JSON with no markdown fences, commentary,
   or trailing text.

## Record-Precedence Rules

### Leave & Assignment Precedence

- **`submitted` or `approved` records always beat `draft` or `superseded`.**
  When multiple leave assignments exist for the same employee in the same
  period, pick the submitted/approved one and exclude everything else.
- **Approved leave assignment overrides a stale employee profile
  summary.** When the leave ledger, the policy document, and an audit
  event all confirm the approved assignment, treat the profile summary's
  policy as stale and set `profile_policy_ignored: true`.
- **Leave source labels:** `leave_assignment_history`,
  `employee_profile_summary`, `case_summary_only`.
- **Precedence labels:** `approved_assignment_current_period`,
  `profile_summary_current_period`, `case_summary_only`,
  `approved_assignment_over_profile`.

### Payroll Record Precedence

- **`submitted` beats `draft`.** When both exist, use the submitted
  assignment and list draft entries under excluded IDs.
- **Draft exclusion rule label:** `exclude_draft_assignment` when a
  submitted record exists; `draft_allowed` when no submitted record is
  present.
- **Payroll source labels:** `submitted`, `draft`, `superseded`.

### Case Folder & Notice Review

- **Folder readiness** requires every file listed in the related policy
  document or case requirements to be present. Missing files go into
  `missing_files`.
- **Required tags** are defined by the case or policy; verify the tag is
  present on the case object.
- **Formal notice quality:** Inspect the notice packet returned by the
  messages or notifications endpoint. A notice is `defective` if it is
  missing any of: acknowledgement deadline, appeal instructions,
  waitlist status, or the correct policy reference.
- **Notice defects labels:** `missing_ack_deadline`,
  `missing_appeal_instructions`, `missing_waitlist_status`,
  `missing_correct_policy`.
- **Evidence source order:** Work from approval history → folder →
  notice → audit. Label: `approval_history_folder_notice_audit`.
- **Audit scope for document/notice findings:** Use
  `document_notice_findings_only`. Support with audit events whose detail
  relates to documents or notices; exclude audit events that only pertain
  to leave source or payroll assignments.

### Recruitment & Candidate Status

- **Candidate status** derives from interview feedback AND offer
  acceptance. Label: `interview_feedback_and_offer`.
- **Accepted offers with `accepted` status** qualify for payroll handoff.
  Only candidates with an accepted offer move to payroll precheck.
- **Waitlisted candidates** have no accepted offer; they need a waitlist
  notice. Label: `send_waitlist_notice`. Exclude them from payroll
  handoff — label: `no_accepted_status_or_offer`.
- **Rejected candidates** need a rejection notice. Label:
  `send_rejection_notice`.
- **Cost source:** Use the recruitment cost ledger. Label:
  `recruitment_cost_ledger`.
- **Notice quality source:** Inspect the notice packet. Label:
  `notice_packet_inspection`.
- **Handoff gate:** `accepted_offer_only` (only accepted-offer candidates
  proceed); `accepted_offer_and_submitted_assignment` (requires payroll
  assignment too).
- **Payroll assignment status required for handoff:**
  `submitted_after_acceptance` means the payroll assignment must be
  submitted (not draft) and follow offer acceptance.

### Audit Event Selection

- Every decision that cites audit evidence must specify exactly one
  primary `audit_event_id`. Choose the audit event whose detail is most
  directly relevant to the scope of the current decision.
- **Supporting audit events** (`supporting_audit_event_ids`) are audit
  events within the same scope that corroborate the primary event.
- **Excluded audit events** (`excluded_audit_event_ids`) are audit events
  that exist in the same case or employee context but whose scope falls
  outside the current decision (e.g., document/notice audit events
  excluded from a leave-precedence-only decision).
- **Audit scope labels:**
  - `document_notice_findings_only` — for case folder and notice reviews.
  - `leave_source_precedence_only` — for leave policy precedence checks.
  - `payroll_assignment_readiness` — for payroll and accrual readiness.

## Control Result & Gate Labels

Use the appropriate label for the task's decision type:

### Onboarding Closeout
- Gate: `approval_sufficient_when_records_clean` or
  `approval_not_sufficient_when_folder_or_notice_defective`.
- Final result: `approve_closeout`, `hold_for_folder_and_notice_defects`,
  or `ready_with_monitoring`.
- Actions: `approve_onboarding_close`, `block_close_and_reissue_notice`,
  `open_records_remediation`.

### Case Folder / Notice
- Decision: `approved_with_conditions`, `approved`, `rejected`, `held`.
- Blockers: `missing_required_files`, `missing_required_tags`,
  `defective_formal_notice`.
- Remediation owner: `Records`.
- Remediation: `reissue_defective_notices`.

### Leave Source Precedence
- Audit result: `profile_summary_stale`, `ready_with_monitoring`,
  `block_close`.
- Next action: `update_employee_summary`, `open_records_remediation`,
  `no_action`.

### Payroll / Accrual
- Control result: `ready_with_monitoring`,
  `hold_for_folder_and_notice_defects`, `approve_closeout`.

### Recruitment Handoff
- Handoff control: `submitted_handoff_required_after_acceptance`,
  `submitted_handoff_required`, `no_handoff_required`.
- Handoff action: `create_payroll_precheck`.

## Answer Template Compliance

1. Copy the exact field names and structure from the supplied
   `answer_template.json`.
2. Every `enum` field must use one of the `allowed_values` verbatim.
3. `string` fields accept the discovered value (e.g. employee ID, case
   ID, assignment ID, policy name).
4. `integer` and `number` fields accept the discovered numeric value.
5. `boolean` fields accept `true` or `false`.
6. `list[string]` fields accept a JSON array of string values.
7. `list[enum]` fields accept a JSON array drawn from the listed
   `allowed_values`.

## Request Pattern

Use `curl -s` for all API calls:

```sh
curl -s '<TASK_ENV_BASE_URL>/api/<endpoint>'
```

For POST:

```sh
curl -s -X POST '<TASK_ENV_BASE_URL>/api/cases/<case_id>/comments' \
  -H 'Content-Type: application/json' \
  -d '{"author":"<name>","created_at":"<YYYY-MM-DDTHH:MM>","visibility":"Internal","body":"<text>"}'
```

## Reasoning Order

1. Fetch the manifest or summary to understand available objects.
2. Fetch the primary entity (employee, case, opening).
3. Based on the task type, fetch related records:
   - **Onboarding closeout:** leave assignments, payroll ledgers,
     policies.
   - **Case review:** approval history, documents (folder), messages
     (notices), audit events.
   - **Recruitment:** candidates, offers, cost ledgers, messages
     (notices).
   - **Leave precedence:** employee summary, leave assignments, policy
     document, audit events.
   - **Payroll readiness:** payroll assignments, accrual batches, audit
     events.
4. Apply the record-precedence rules to select authoritative records.
5. Map findings to the answer template's normalized labels.
6. Return the completed JSON.
