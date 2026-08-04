 # PeopleOps Verification & Reconciliation Skill

 This skill teaches an agent how to perform structured verification and reconciliation tasks against a PeopleOps REST API. It covers record source precedence, draft exclusion, cross-referencing evidence across endpoints, and producing normalized JSON outputs.

 ## Environment Setup

 The PeopleOps application is accessed at the base URL provided in the task prompt as `<TASK_ENV_BASE_URL>`. Resolve this placeholder to the running environment URL (typically `http://task-env:9012/` or similar).

 Authentication uses browser-based login in the web UI with these credentials:

 - Username: `ops.lead@peopleops.local`
 - Password: `PeopleOps#2026`

 The API itself does not require authentication headers for GET or POST requests.

 ## API Reference

 ### GET Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Root / dashboard |
| `GET /api/manifest` | System manifest |
| `GET /api/summary` | Top-level summary |
| `GET /api/employees` | All employee profiles |
| `GET /api/cases` | All case records |
| `GET /api/cases/{case_id}` | Single case detail |
| `GET /api/policies` | All policies |
| `GET /api/policies/{policy_id}` | Single policy detail |
| `GET /api/payroll-ledgers` | Payroll ledger records |
| `GET /api/recruitment` | Recruitment openings, candidates, offers |
| `GET /api/documents` | Document / file records |
| `GET /api/messages` | Messages and communications |
| `GET /api/notifications` | Notification records |
| `GET /api/audit` | All audit events |
| `GET /api/audit/{audit_id}` | Single audit event detail |
| `GET /api/attachments/{attachment_id}` | Attachment detail or download |

 ### POST Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/cases/{case_id}/comments` | Add a comment to a case |

POST body format (`Content-Type: application/json`):
```json
{"author": "<string>", "created_at": "<YYYY-MM-DDTHH:MM>", "visibility": "<string>", "body": "<string>"}
```

## Core Verification Patterns

### Record Source Precedence

When multiple records exist for the same entity (leave policy, payroll assignment, etc.), apply source precedence:

1. **Approved assignment records** are authoritative over stale employee profile summaries.
2. **Submitted records** are authoritative over draft records.
3. **Current-period records** are authoritative over prior-period records.
4. When the leave/payroll ledger, policy document, and audit event detail all confirm an approved assignment, that assignment overrides a profile summary that may be stale.

Use the `leave_assignment_history` source (or `approved_assignment_current_period` precedence) when an approved assignment exists. Use `employee_profile_summary` only when no approved assignment is present.

### Draft and Superseded Record Exclusion

Always identify and exclude records with these statuses:

- **Draft**: Records with `"status": "draft"` or IDs containing `-DRAFT-` are never authoritative and must be excluded from final answers.
- **Superseded**: Records superseded by a newer submitted/approved record must be listed in exclusion fields.

Check the `status` or `state` field of each record. Only `submitted` or `approved` records count as authoritative.

### Cross-Referencing Evidence

To validate a claim, cross-reference at least two independent sources:

- **Employee data**: `/api/employees` for profile summaries, `/api/summary` for aggregate views.
- **Assignment records**: Examine the relevant ledger (leave assignments in leave-related fields; payroll assignments in `/api/payroll-ledgers`).
- **Policy documents**: `/api/policies/{policy_id}` confirms the named policy exists and matches the assignment.
- **Audit events**: `/api/audit` and `/api/audit/{audit_id}` provide an independent verification trail. Match audit events to the domain being verified (leave, payroll, documents/notices).
- **Case records**: `/api/cases/{case_id}` for case-specific context, approval history, and folder status.
- **Documents/notices**: `/api/documents` for required files, notice packets, and formal communications.
- **Messages**: `/api/messages` for candidate outreach and notice delivery evidence.
- **Recruitment**: `/api/recruitment` for openings, candidates, offers, and cost ledgers.

When audit events span multiple domains, filter to only the relevant scope. For a leave-source decision, use only leave-scoped audit events and exclude document/notice-scoped audit events. For a payroll decision, use only payroll-scoped audit events.

### Audit Scope Selection

Choose the audit scope based on the verification task:

- `leave_source_precedence_only` — for leave policy/payroll source validation tasks
- `document_notice_findings_only` — for case folder and formal notice review tasks
- `payroll_assignment_readiness` — for payroll assignment and accrual readiness tasks

Corresponding audit event IDs must be populated in `audit_event_id` (primary) and `supporting_audit_event_ids` (supporting). Adjacent audit events that belong to a different scope must be placed in `excluded_audit_event_ids`.

### Normalized Business Labels

Always use the exact normalized labels defined in each task's answer template for `source`, `gate`, `status`, `scope`, `owner`, `remediation`, and `final-result` fields. Do not use free-text explanations for these enumerated fields.

## Verification Workflows

### 1. Onboarding Closeout Verification

When verifying onboarding closeout for an employee:

1. Fetch the employee record from `/api/employees` and `/api/summary`.
2. Fetch applicable leave policies from `/api/policies`.
3. Inspect leave assignments (look for assignment records in the leave ledger or summary data). Identify the authoritative leave assignment — prefer submitted/approved over draft.
4. Inspect payroll assignments from `/api/payroll-ledgers`. Identify the authoritative payroll assignment — prefer submitted over draft.
5. Cross-reference with `/api/audit` events scoped to leave and payroll.
6. Determine:
   - Effective leave policy name and annual days
   - Authoritative assignment ID (exclude draft and superseded IDs)
   - Authoritative payroll assignment ID and base salary (exclude draft IDs)
   - Closeout action: `approve_onboarding_close` when records are clean; `block_close_and_reissue_notice` when defective; `open_records_remediation` when records need correction.
   - Final control result and approval gate

### 2. Case Folder and Notice Review

When reviewing a case for folder readiness and notice quality:

1. Fetch the case detail from `/api/cases/{case_id}`.
2. Inspect the case folder via `/api/documents` — identify any missing required files.
3. Check for required tags in the case or folder metadata.
4. Inspect the formal notice via notice packets (`/api/documents`) or messages (`/api/messages`). Check for defects:
   - `missing_ack_deadline`
   - `missing_appeal_instructions`
   - `missing_waitlist_status`
   - `missing_correct_policy`
5. Review approval history in the case to identify the approval authority, final decision, and approval event ID.
6. Cross-reference with audit events scoped to the document/notice domain (`document_notice_findings_only`).
7. Determine:
   - Final decision (`approved`, `approved_with_conditions`, `rejected`, `held`)
   - Folder readiness, missing files, required tag status
   - Notice quality (`valid` or `defective`) and specific defects
   - Next action and escalation path
   - Records remediation owner and notice remediation action
   - Final control result

### 3. Recruitment Reconciliation

When reconciling a recruitment opening:

1. Fetch the recruitment data from `/api/recruitment` — openings, candidates, offers.
2. Fetch the related case from `/api/cases`.
3. Inspect the recruitment cost ledger within the recruitment data and sum all campaign ledger item costs for `recruitment_cost_total`.
4. Inspect offer records to determine candidate outcomes:
   - **Selected**: The candidate with an accepted offer (status `accepted`).
   - **Waitlisted**: Candidates waitlisted but not selected (exclude from offer if no accepted status).
   - **Rejected**: Candidates explicitly rejected.
5. Inspect notices via `/api/documents` or `/api/messages` to determine which candidates need follow-up notices (waitlist and rejection notices).
6. Determine payroll handoff:
   - `create_payroll_precheck` when the selected candidate has accepted and needs a payroll pre-check.
   - `create_submitted_assignment_after_acceptance` when a submitted payroll assignment should be created after offer acceptance.
   - `no_payroll_handoff` when no payroll action is needed.
7. Validate that draft payroll assignments are not allowed for the handoff.

### 4. Leave Source Precedence Validation

When validating which leave policy source takes precedence:

1. Fetch the employee profile from `/api/employees` — note the profile summary leave policy.
2. Inspect leave assignments (from the leave ledger or employee detail). Look for approved assignment records.
3. Fetch the policy document from `/api/policies/{policy_id}` to confirm the policy exists.
4. Inspect audit events from `/api/audit` — identify leave-scope audit events.
5. Apply precedence: an approved leave assignment overrides a stale employee profile summary when the ledger, policy document, and audit detail all confirm the approved assignment.
6. Determine:
   - Effective leave policy (from the approved assignment)
   - Authoritative assignment ID
   - Balance days from the approved assignment
   - Whether the profile policy should be ignored (`true` when profile summary is stale)
   - Audit result (`profile_summary_stale` when profile is out of date; `ready_with_monitoring` otherwise)
   - Next action (`update_employee_summary` when profile is stale)
   - Supporting and excluded audit event IDs per scope

### 5. Payroll Assignment and Accrual Readiness

When inspecting payroll assignment and accrual readiness:

1. Fetch the employee record and payroll data from `/api/payroll-ledgers`.
2. Identify the authoritative payroll assignment — prefer `submitted` status. Exclude records with `draft` status (IDs containing `-DRAFT-`).
3. Note the salary, effective date, and assignment ID of the selected assignment.
4. Verify accrual readiness — check the accrual batch for the relevant period. Confirm the batch is ready to proceed.
5. Cross-reference with payroll-scoped audit events (`payroll_assignment_readiness`).
6. Determine:
   - Salary assignment ID and base salary
   - Effective date
   - Excluded assignment ID (the draft record)
   - Accrual readiness (`true`/`false`) and accrual batch ID
   - Audit event ID for the payroll verification
   - Control result (`ready_with_monitoring`, `hold_for_folder_and_notice_defects`, `approve_closeout`)
   - Draft exclusion rule (`exclude_draft_assignment`)

## Output Format

Every task provides an answer template at `input/payloads/answer_template.json`. The final output must:

1. Match the template structure exactly — same keys, same types.
2. Use only the allowed enum values listed in the template for each enumerated field.
3. Be valid JSON with no additional keys, markdown fences, or explanatory text (unless the template explicitly requests text fields).
4. For list fields, include only IDs (e.g., candidate IDs, assignment IDs, audit event IDs).
5. For numeric fields (`recruitment_cost_total`), compute the sum from the relevant ledger, not a rounded or estimated value.

## General Methodology

1. **Read the task prompt carefully** to identify the business domain (onboarding, case review, recruitment, leave precedence, payroll readiness).
2. **Fetch all relevant API endpoints** — be thorough; cross-reference data across endpoints.
3. **Identify the authoritative records** using source precedence and draft exclusion rules.
4. **Select the correct audit scope** and filter audit events accordingly.
5. **Populate the answer template** with enumerated values from the template's allowed lists.
6. **Validate** that no draft records appear in authoritative fields and that all exclusion lists are complete.
