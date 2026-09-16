---
name: peopleops-workflow
description: Solve PeopleOps Console tasks by navigating the API systematically, applying business rules for source precedence, status filtering, and evidence ordering across leave, payroll, recruitment, and case-review workflows.
---

Use these instructions when solving PeopleOps Console tasks that involve leave
verification, payroll readiness, recruitment reconciliation, case folder
review, or cross-module lifecycle controls.

## Base Setup

The task environment provides a base URL in the form
`<TASK_ENV_BASE_URL>`. Construct all API calls by appending the endpoint
paths listed below to that base. Credentials:

```
ops.lead@peopleops.local
PeopleOps#2026
```

The API is read-only for all GET endpoints listed under **Allowed Endpoints**.
There is a `POST /api/cases/{case_id}/comments` endpoint for adding comments
but it is rarely needed. Do not call `/api/judge`.

## Core Business Policies

These four policies control every workflow. Read them from
`/api/policies/{policy_id}` when the task crosses a policy boundary, or rely
on the rules summarized here when the policy text is not critical to the
current subtask.

| Policy ID          | Domain              | Core Rule                                                                 |
|--------------------|---------------------|---------------------------------------------------------------------------|
| LEAVE-SRC-001      | Leave precedence    | The latest Approved or Submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict. |
| PAY-SRC-001        | Payroll assignment  | Use the current Submitted salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks. Recruiting payroll handoff is created only after a selected candidate has an accepted offer; the handoff must be Submitted. |
| HR-POL-014         | Remote work         | Remote work exceptions require executive approval, time limits, tax equalization, VPN-only access, quarterly compliance review, appeal instructions, and acknowledgement deadline in the formal notice. |
| POL-DOCS-2026      | Folder checklist    | A folder is not ready unless all required files and required tags shown in the folder checklist are present. |

## API Endpoints and Usage

### Discovery

Start with `GET /api/summary` and `GET /api/manifest` to orient yourself.

### Reference Data (index endpoints)

| Endpoint                  | Returns                                        |
|---------------------------|-------------------------------------------------|
| GET /api/employees        | All employee profiles with status, leave_balance, department, salary_band |
| GET /api/cases            | All cases with status, owner, policy_refs, summary |
| GET /api/policies         | All policy documents with sections              |
| GET /api/payroll-ledgers  | Mixed ledger: leave assignments, salary assignments, accrual records, HRMS ledger entries |
| GET /api/recruitment      | Recruitment openings with candidates, offers, cost ledger, notice packets |
| GET /api/documents        | Document folders with files, required_files, required_tags, tags, ready flag |
| GET /api/messages         | Formal notices with quality, defects, status    |
| GET /api/audit            | Audit events with actor, event type, detail     |
| GET /api/notifications    | Notifications (supplementary)                   |

### Detail Endpoints

- `GET /api/cases/{case_id}` -- case detail including approvals, attachments, audit_events (case-scoped), comments
- `GET /api/policies/{policy_id}` -- single policy detail
- `GET /api/audit/{audit_id}` -- single audit event detail
- `GET /api/attachments/{attachment_id}` -- attachment content (e.g. folder checklist text)

### Important Structural Notes

**Payroll-ledgers** is a mixed endpoint. Every record has a `record_type` field.
Filter on `record_type` to isolate the relevant slice:

- `"Leave assignment"` -- `ledger_id` is the leave assignment ID, `status` is `Approved`, `Superseded`, `Draft`, etc.
- `"Salary assignment"` -- `ledger_id` is the payroll assignment ID, contains `base_salary`, `accrual_batch_id`
- Other record types (`People Ops adjustment`, `Payroll worksheet`, `HRMS leave ledger`) are noise records for most tasks.

**Recruitment** returns an array of openings. Each opening contains:

- `candidates[]` -- candidate list with `committee_decision` (`Selected`, `Waitlisted`, `Rejected`)
- `offer_register[]` -- offers with `status` (`accepted`, `draft`, `withdrawn`)
- `cost_ledger[]` -- cost line items with `amount`
- `notice_packets[]` -- notice status per candidate with `notice_type`, `required_action`, `defects`
- `payroll_precheck_records[]` -- draft precheck records (excluded from handoff)

**Documents** returns folders. Key fields: `files[]` (present), `required_files[]`
(expected), `tags[]` (present), `required_tags[]` (expected), `ready` (boolean).

**Messages** returns formal notices. Key fields: `quality` (`valid` / `defective`),
`defects[]` (e.g. `missing_appeal_instructions`, `missing_ack_deadline`,
`missing_waitlist_status`, `missing_correct_policy`).

## Workflow Decision Tree

Identify the task type from the prompt and follow the corresponding workflow.

### 1. Leave Verification (leave policy, balance, assignment)

**Goal**: Determine the effective leave policy, annual days, and assignment ID
for an employee. Apply source precedence.

**Procedure**:

1. Call `GET /api/employees` and find the target employee by ID or name.
   Note the profile `leave_balance_days` and department -- these are reference
   values, not authoritative.

2. Call `GET /api/payroll-ledgers` and filter for `record_type: "Leave assignment"`,
   `employee_id: <target>`. Sort by `updated_at` descending.

3. Apply the LEAVE-SRC-001 rule:
   - Select the record with the latest `updated_at` whose `status` is `Approved`
     or `Submitted`.
   - Exclude all records with `status` of `Draft`, `Voided`, or `Superseded`.
   - The selected record's `policy_name` is the effective leave policy.
   - The selected record's `approved_leave_days` is the annual days.
   - The selected record's `ledger_id` is the assignment ID.

4. Collect excluded IDs: every record for the target employee whose `status` is
   not the selected authoritative status (i.e. `Superseded`, `Draft`, `Voided`).

5. **Leave source** is always `leave_assignment_history` when you used the
   ledger to find the authoritative record.

6. **Leave precedence source** is `approved_assignment_current_period` when an
   Approved/Submitted assignment was found.

7. Cross-check against the task's case (if any). Call `GET /api/cases/{case_id}`
   and examine `audit_events`. If the task mentions a profile mismatch or stale
   profile, identify the audit event confirming the stale profile. That audit
   event is the supporting evidence.

8. If the task also asks about payroll for the same employee, follow the
   payroll workflow below for that employee.

**Decision rule**: When the ledger assignment's policy or days differ from the
profile, the ledger assignment controls. The profile is stale.

### 2. Payroll Assignment Verification

**Goal**: Verify the submitted payroll assignment, exclude draft records, and
determine accrual readiness.

**Procedure**:

1. Call `GET /api/payroll-ledgers` and filter for `record_type: "Salary assignment"`,
   `employee_id: <target>`.

2. Apply the PAY-SRC-001 rule:
   - Select the record with `status: "Submitted"`.
   - Exclude all records with `status: "Draft"` (or `Superseded`).
   - The selected record's `ledger_id` is the payroll assignment ID.
   - The selected record's `base_salary` is the base salary.
   - If the record has an `accrual_batch_id`, note it.

3. Accrual readiness: if the submitted record references an `accrual_batch_id`
   and the task asks about accrual, check that the batch ID exists and the
   record is submitted. The accrual is ready when the submitted assignment is
   clean.

4. If a case is associated, call `GET /api/cases/{case_id}` and examine
   `audit_events` for payroll-related events. Use the audit event that confirms
   the submitted assignment controls.

5. `payroll_source_status` is `submitted`.
   `draft_exclusion_rule` is `exclude_draft_assignment`.
   `audit_scope` is `payroll_assignment_readiness`.

6. `control_result`:
   - `ready_with_monitoring` when the submitted assignment is found and no
     blockers exist.
   - `approve_closeout` when the task is an onboarding closeout and both leave
     and payroll are clean.

### 3. Case Folder and Notice Review

**Goal**: Review a case's folder readiness and formal notice quality.

**Procedure**:

1. Call `GET /api/cases/{case_id}` to get case detail, approvals, attachments,
   and case-scoped audit events.

2. **Evidence order**: `approval_history_folder_notice_audit`
   - First read approvals to understand the decision and authority.
   - Then check the folder (documents API).
   - Then inspect the formal notice (messages API or case attachments).
   - Then corroborate with audit events.

3. **Folder check**: Use the case's `policy_refs` and attachment checklist.
   Call `GET /api/documents` and locate the folder for this case (match by
   employee or case context). Verify:
   - `files` contains all `required_files`. Missing files are listed in `missing_files`.
   - `tags` contains all `required_tags`. If a required tag is absent,
     `required_tag_present` is false.

4. **Notice check**: Call `GET /api/messages` and locate the message for this case
   (match by `case_id`). Determine:
   - `quality`: `valid` or `defective`
   - `defects[]`: list of defect codes found
   - If the message quality is `defective`, `notice_quality` is `defective`.

5. **Decision**:
   - If folder is not ready or notice is defective:
     - `final_decision`: `approved_with_conditions` (if approval exists) or `held`
     - `approval_closeout_gate`: `approval_not_sufficient_when_folder_or_notice_defective`
     - `closeout_blockers`: list the applicable blockers (`missing_required_files`,
       `defective_formal_notice`, `missing_required_tags`)
     - `next_action`: `block_close_and_reissue_notice` when notice is defective;
       `open_records_remediation` when folder is defective
     - `final_control_result`: `hold_for_folder_and_notice_defects`
   - If both folder and notice are clean:
     - `approval_closeout_gate`: `approval_sufficient_when_records_clean`
     - `final_control_result`: `approve_closeout` or `ready_with_monitoring`

6. **Audit events**: Use the audit events from the case detail or `/api/audit`.
   The primary `audit_event_id` is the one most directly related to the
   document/notice findings. Supporting events are those in the same scope.
   Excluded events are those outside the document/notice scope (e.g. payroll or
   leave events when the task scope is document/notice).

7. **Audit scope** for case folder/notice tasks: `document_notice_findings_only`.

8. **Notice evidence source**: `notice_packet_inspection` when you read the
   messages endpoint; `message_notice_inspection` when the notice evidence is
   only in messages.

### 4. Recruitment Reconciliation

**Goal**: Reconcile a recruitment opening's candidate outcomes, offer, costs,
notice follow-ups, and payroll handoff.

**Procedure**:

1. Call `GET /api/recruitment` and locate the target opening by `opening_id`.

2. **Candidate outcomes** from the `candidates[]` array:
   - `committee_decision: "Selected"` -> `selected_candidate`
   - `committee_decision: "Waitlisted"` -> `waitlisted_candidates`
   - `committee_decision: "Rejected"` -> `rejected_candidates`
   - `candidate_status_source`: `interview_feedback_and_offer`
   - `candidate_outcome_control`: `committee_decision_with_offer_confirmation`

3. **Offer details** from `offer_register[]`:
   - Match the selected candidate to their offer.
   - `offer_id` and `offer_base_salary` from the matched offer.
   - `selected_offer_status`: `accepted`, `draft`, `withdrawn`, or `none` (when
     no offer exists for the selected candidate).
   - `offer_exclusion_reason_for_waitlisted`: `no_accepted_status_or_offer`

4. **Recruitment cost**: Sum all `amount` values in `cost_ledger[]`.
   `cost_source`: `recruitment_cost_ledger`.

5. **Notice follow-up** from `notice_packets[]`:
   - For waitlisted candidates: check if a waitlist notice is required.
     If `status` is `not_sent`, the candidate needs `send_waitlist_notice`.
     If `status` is `draft_reissue_required`, use `reissue_waitlist_notice_not_rejection`.
     `waitlisted_followup_action` maps to the required action.
   - For rejected candidates: check if a rejection notice is required.
     If `status` is `not_sent`, use `send_rejection_notice`.
     `rejected_followup_action` maps to the required action.
   - `notice_followup_required`: list of candidate IDs needing any notice follow-up.
   - `notice_quality_source`: `notice_packet_inspection`

6. **Payroll handoff**:
   - Only proceed if the selected candidate has an `accepted` offer.
   - `payroll_handoff_gate`: `accepted_offer_only`
   - `payroll_assignment_status_required`: `submitted_after_acceptance`
   - `draft_payroll_allowed`: `false`
   - `onboarding_handoff`: `create_payroll_precheck`
   - `handoff_control_result`: `submitted_handoff_required_after_acceptance`

7. Exclude `payroll_precheck_records[]` from the handoff gate decision -- they
   are draft placeholders.

### 5. Leave Precedence Dispute (profile vs assignment)

**Goal**: When the profile summary conflicts with the leave ledger, determine
which source is authoritative.

**Procedure**:

1. Follow the Leave Verification workflow (Section 1) to find the authoritative
   assignment from the ledger.

2. Compare the profile's `leave_balance_days` and department context against the
   ledger assignment's `policy_name` and `approved_leave_days`.

3. If they differ, the ledger assignment controls per LEAVE-SRC-001.
   - `precedence_source`: `approved_assignment_over_profile`
   - `leave_precedence_source`: `approved_assignment_current_period`
   - `profile_policy_ignored`: `true`
   - `audit_result`: `profile_summary_stale`
   - `next_action`: `update_employee_summary`

4. **Audit event separation**: When the task asks for audit events:
   - `supporting_audit_event_ids`: audit events that confirm the leave
     precedence decision (e.g. `leave.profile_mismatch` events).
   - `excluded_audit_event_ids`: audit events that are about document folders
     or notice quality -- they are adjacent but outside the leave scope.
   - `audit_scope`: `leave_source_precedence_only`

5. The audit event confirming the stale profile is the primary `audit_event_id`.

### 6. Onboarding Closeout (combined leave + payroll)

**Goal**: Combined workflow -- verify both leave and payroll for an onboarding
employee, then determine the closeout action.

**Procedure**:

1. Run the Leave Verification workflow (Section 1) for the target employee.

2. Run the Payroll Assignment Verification workflow (Section 2) for the same
   employee.

3. **Closeout decision**:
   - If both leave and payroll are clean (no blockers):
     - `closeout_action`: `approve_onboarding_close`
     - `approval_closeout_gate`: `approval_sufficient_when_records_clean`
     - `final_control_result`: `approve_closeout`
   - If leave has blocked records or payroll has issues:
     - `closeout_action`: `block_close_and_reissue_notice` or
       `open_records_remediation` depending on the nature of the issue.

## Status Filtering Rules

These rules apply across all workflows:

| Record Type         | Authoritative Statuses       | Excluded Statuses                  |
|---------------------|------------------------------|------------------------------------|
| Leave assignment    | `Approved`, `Submitted`      | `Superseded`, `Draft`, `Voided`    |
| Salary assignment   | `Submitted`                  | `Draft`, `Superseded`              |
| Payroll precheck    | `Submitted`                  | `Draft`                            |
| Offer               | `accepted`                   | `draft`, `withdrawn`               |

Always exclude draft records unless the task explicitly instructs otherwise.
Superseded records are historically prior and no longer authoritative.

## Audit Scope Separation

Audit events serve different business scopes. When a task asks for audit
events, identify which scope applies and include only events in that scope.

| Audit Event Type          | Scope                          |
|---------------------------|--------------------------------|
| `leave.profile_mismatch`  | leave_source_precedence_only   |
| `payroll.ready`, `payroll.draft_excluded` | payroll_assignment_readiness |
| `notice.defect`, `case.close_blocked`, `folder.tag_missing` | document_notice_findings_only |
| `cross_module.escalation_package` | Cross-module -- read its detail for related event IDs |

When the task scope is `leave_source_precedence_only`, exclude
document/notice events (like `folder.tag_missing`). When the task scope is
`document_notice_findings_only`, exclude leave and payroll events.

## Evidence Order

For each task type, gather evidence in this order:

1. **Leave/payroll tasks**: employee profile -> payroll-ledgers -> policies -> case detail -> audit events
2. **Case folder/notice tasks**: case detail (approvals) -> documents folder -> messages (notice) -> audit events
3. **Recruitment tasks**: recruitment opening -> offer register -> cost ledger -> notice packets -> payroll precheck records

Always consult the relevant policy document (`/api/policies/{policy_id}`) when
the task references a policy or when you need to validate a business rule.
The policy text is authoritative for edge cases.

## Output Format

Every task provides an `answer_template.json` in
`input/payloads/answer_template.json`. Read this template first -- it defines
the exact JSON shape, field types, and allowed enum values for the response.
Use only the normalized enum values listed in the template. Do not use
free-text explanations for enum fields.

Return the final answer as a single JSON object matching the template exactly.
Do not include markdown fences or explanatory text unless the task prompt
permits it.

## Quick Reference: Normalized Enum Values

These are the common enum values used across tasks. Always defer to the
task's answer template for the exact set.

**Leave source**: `leave_assignment_history`, `employee_profile_summary`,
`case_summary_only`

**Leave precedence**: `approved_assignment_current_period`,
`profile_summary_current_period`, `case_summary_only`

**Payroll source status**: `submitted`, `draft`, `superseded`

**Draft exclusion**: `exclude_draft_assignment`, `draft_allowed`,
`exclude_superseded_only`

**Audit scope**: `leave_source_precedence_only`, `document_notice_findings_only`,
`payroll_assignment_readiness`

**Closeout action**: `approve_onboarding_close`, `block_close_and_reissue_notice`,
`open_records_remediation`

**Approval gate**: `approval_sufficient_when_records_clean`,
`approval_not_sufficient_when_folder_or_notice_defective`

**Final control result**: `approve_closeout`, `hold_for_folder_and_notice_defects`,
`ready_with_monitoring`

**Notice quality**: `valid`, `defective`

**Notice defects**: `missing_ack_deadline`, `missing_appeal_instructions`,
`missing_waitlist_status`, `missing_correct_policy`

**Candidate outcome control**: `committee_decision_with_offer_confirmation`,
`message_status_only`, `case_summary_only`

**Offer status**: `accepted`, `draft`, `withdrawn`, `none`

**Notice evidence source**: `notice_packet_inspection`, `message_notice_inspection`,
`case_summary_only`

**Payroll handoff gate**: `accepted_offer_only`,
`accepted_offer_and_submitted_assignment`, `all_interviewed_candidates`

**Handoff control result**: `submitted_handoff_required_after_acceptance`,
`submitted_handoff_required`, `no_handoff_required`

**Next action (leave)**: `update_employee_summary`, `open_records_remediation`,
`no_action`

**Precedence source**: `approved_assignment_over_profile`,
`employee_profile_summary`, `case_summary_only`

**Audit result**: `profile_summary_stale`, `ready_with_monitoring`, `block_close`

**Evidence source order**: `approval_history_folder_notice_audit`,
`folder_notice_audit`, `audit_only`

**Folder tag action**: `no_tag_action`, `add_required_tag`

**Escalation action**: `open_records_remediation`,
`block_close_and_reissue_notice`, `no_action`

**Records remediation owner**: `Records`, `People Ops Compliance`, `Payroll QA`

**Notice remediation action**: `reissue_defective_notices`, `no_notice_action`,
`send_new_offer_notice`

**Waitlisted followup action**: `send_waitlist_notice`,
`reissue_waitlist_notice_not_rejection`, `no_action`

**Rejected followup action**: `send_rejection_notice`, `no_action`,
`reissue_rejection_notice`

**Onboarding handoff**: `create_payroll_precheck`,
`create_submitted_assignment_after_acceptance`, `no_payroll_handoff`

**Candidate status source**: `interview_feedback_and_offer`, `case_summary_only`,
`message_only`

**Cost source**: `recruitment_cost_ledger`, `case_summary_only`

**Payroll assignment status required**: `submitted_after_acceptance`,
`submitted`, `draft_allowed`

**Offer exclusion reason**: `no_accepted_status_or_offer`,
`waitlisted_not_selected`, `already_rejected`
