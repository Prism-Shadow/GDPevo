# HR Employee-Lifecycle Onboarding Closeout Skill

## When to use

Use this skill when solving PeopleOps employee-lifecycle tasks that require verifying
onboarding closeout readiness, leave source precedence, payroll assignment readiness,
recruitment reconciliation, or policy case folder/notice quality against the Northwind
People Lifecycle Portal remote API. The skill covers five task archetypes:

1. **Onboarding closeout verification** (employee leave + payroll setup)
2. **Policy case folder/notice review** (folder readiness + formal notice quality)
3. **Recruitment reconciliation** (candidate outcomes + cost + payroll handoff)
4. **Leave source precedence** (approved assignment vs stale profile summary)
5. **Payroll assignment and accrual readiness** (submitted vs draft assignment)

## Remote API reference

- **Base URL**: `<remote-env-url>`
- **Web UI**: `<remote-env-url>/`
- **Auth**: none required (read-only REST API under `/api/*`)
- **Health check**: `GET /health`
- Login credentials (`ops.lead@peopleops.local / PeopleOps#2026`) are illustrative only.

## Step-by-step SOP

### Step 1: Read the manifest and summary
```
GET /api/manifest    # learn available modules and file counts
GET /api/summary     # live record counts and departments
```

### Step 2: Identify the entity in the prompt
Extract the employee ID (e.g. `EMP-104`), case ID (e.g. `CASE-RW-221`), or opening
ID (e.g. `REQ-DA-77`) from the task prompt.

### Step 3: Gather employee detail (leave assignment history)
```
GET /api/employees?q=<employee_id or name>
```
The employee object carries `leave_balance_days` (profile summary), `salary_band`,
`status`, `department`, `hire_date`. This is the **profile summary** — it may be stale.

### Step 4: Gather payroll ledgers (leave assignments + salary assignments)
```
GET /api/payroll-ledgers?q=<employee_id>
```
This is the **authoritative source** for both leave assignments and salary assignments.
Each record has a `record_type` field:
- `Leave assignment` — leave policy + approved days + status (Approved/Superseded/Draft)
- `Salary assignment` — base_salary + status (Submitted/Draft) + period + accrual_batch_id
- Other types: `HRMS leave ledger`, `People Ops adjustment` — these are ledger entries,
  not primary assignments. Check `status` (Submitted/Approved/Superseded/Draft).

**Key rule**: The `status` field determines whether the record is authoritative.
- Approved/Submitted = authoritative for the current period
- Superseded/Draft = excluded

### Step 5: Gather full case detail
```
GET /api/cases?q=<keyword>          # search for the case
GET /api/cases/<case_id>            # FULL detail: approvals, attachments, comments, audit_events
```
Full case detail includes nested `approvals[]`, `attachments[]`, `comments[]`, and
`audit_events[]` arrays that are NOT present in the search results.

### Step 6: Gather policy definitions
```
GET /api/policies                   # all policies
GET /api/policies/<policy_id>       # single policy detail
```
Critical policies:
- `LEAVE-SRC-001` — Leave Source Precedence
- `PAY-SRC-001` — Payroll Assignment Source (includes recruiting handoff gate)
- `POL-DOCS-2026` — Lifecycle Folder Checklist
- `HR-POL-014` — Remote Work Policy (notice requirements)

### Step 7: Gather documents folder
```
GET /api/documents?q=<keyword or document_id>
```
Each document folder has:
- `files[]` — files currently present
- `required_files[]` — files that must be present
- `tags[]` — tags currently present
- `required_tags[]` — tags that must be present
- `ready` — boolean (true only if all required files AND tags are present)

### Step 8: Gather formal notice messages
```
GET /api/messages?q=<keyword or case_id>
```
Each message has:
- `quality` — "valid" or "defective"
- `defects[]` — list of specific defects from: `missing_ack_deadline`,
  `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`
- `status` — "Draft" or other

### Step 9: Gather notifications
```
GET /api/notifications?q=<keyword or case_id>
```
Notifications mirror message content and carry the same defect/quality fields.

### Step 10: Gather audit events
```
GET /api/audit                      # all audit events
GET /api/audit?case_id=<case_id>    # filtered by case
GET /api/audit/<audit_id>           # single audit event detail
```
Each audit event has:
- `event` — event type (e.g. `leave.profile_mismatch`, `payroll.ready`,
  `notice.defect`, `case.close_blocked`, `folder.tag_missing`)
- `detail` — descriptive text, often containing the QA result and key identifiers

### Step 11: Gather attachment content (if referenced in case)
```
GET /api/attachments/<attachment_id>
```
Returns attachment text content with folder checklist details.

### Step 12: Gather recruitment data (for recruitment tasks)
```
GET /api/recruitment?q=<opening_id>
```
Returns candidates, offer_register, cost_ledger, notice_packets,
payroll_precheck_records.

## Endpoint calling order summary

For any task, call endpoints in this order:
1. `/api/manifest` — orientation
2. `/api/employees?q=<id>` — employee profile summary
3. `/api/payroll-ledgers?q=<id>` — leave assignments + salary assignments (authoritative)
4. `/api/cases/<case_id>` — full case detail (approvals, attachments, comments, audit_events)
5. `/api/policies` and `/api/policies/<id>` — policy definitions
6. `/api/documents?q=<id>` — document folder readiness
7. `/api/messages?q=<case_id>` — formal notice quality
8. `/api/notifications?q=<case_id>` — notification defects
9. `/api/audit?case_id=<case_id>` — audit events with QA results
10. `/api/attachments/<id>` — attachment content (follow from case attachments)
11. `/api/recruitment?q=<opening_id>` — recruitment data (for recruitment tasks only)

## Field definitions and answer conventions

### Common answer fields across task types

| Field | Type | Description |
|---|---|---|
| `employee_id` | string | Employee ID from the prompt (e.g. `EMP-104`) |
| `effective_leave_policy` | string | Policy name from the authoritative approved/submitted assignment |
| `assignment_id` | string | Ledger ID of the authoritative leave assignment |
| `annual_days` / `balance_days` | integer | Approved leave days from the authoritative assignment |
| `excluded_leave_ids` | list[string] | Ledger IDs of excluded (Superseded/Draft) leave records |
| `payroll_assignment_id` / `salary_assignment_id` | string | Ledger ID of the submitted salary assignment |
| `base_salary` | number | Base salary from the submitted salary assignment |
| `excluded_payroll_ids` / `excluded_assignment_id` | string/list | Ledger ID(s) of excluded (Draft) salary assignments |
| `audit_event_id` | string | The primary audit event for the task scope |
| `supporting_audit_event_ids` | list[string] | Audit events that confirm the decision |
| `excluded_audit_event_ids` | list[string] | Adjacent audit events outside the task scope |
| `audit_scope` | enum | The scope of audit review (see below) |
| `final_control_result` / `control_result` | enum | The final control outcome |

### Enum values by field

**leave_source**: `leave_assignment_history`, `employee_profile_summary`, `case_summary_only`

**leave_precedence_source**: `approved_assignment_current_period`, `profile_summary_current_period`, `case_summary_only`

**precedence_source**: `approved_assignment_over_profile`, `employee_profile_summary`, `case_summary_only`

**payroll_status / payroll_source_status**: `submitted`, `draft`, `superseded`

**closeout_action / next_action**: `approve_onboarding_close`, `block_close_and_reissue_notice`, `open_records_remediation`

**approval_closeout_gate**: `approval_sufficient_when_records_clean`, `approval_not_sufficient_when_folder_or_notice_defective`

**final_control_result / control_result**: `approve_closeout`, `hold_for_folder_and_notice_defects`, `ready_with_monitoring`

**audit_scope**: `payroll_assignment_readiness`, `document_notice_findings_only`, `leave_source_precedence_only`

**notice_quality**: `valid`, `defective`

**notice_defects** (list[enum]): `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`

**closeout_blockers** (list[enum]): `missing_required_files`, `missing_required_tags`, `defective_formal_notice`

**draft_exclusion_rule**: `exclude_draft_assignment`, `draft_allowed`, `exclude_superseded_only`

**audit_result**: `profile_summary_stale`, `ready_with_monitoring`, `block_close`

**final_decision**: `approved_with_conditions`, `approved`, `rejected`, `held`

**evidence_source_order**: `approval_history_folder_notice_audit`, `folder_notice_audit`, `audit_only`

**folder_required_tag_action**: `no_tag_action`, `add_required_tag`

**notice_evidence_source / notice_quality_source**: `notice_packet_inspection`, `message_notice_inspection`, `case_summary_only`

**escalation_action**: `open_records_remediation`, `block_close_and_reissue_notice`, `no_action`

**records_remediation_owner**: `Records`, `People Ops Compliance`, `Payroll QA`

**notice_remediation_action**: `reissue_defective_notices`, `no_notice_action`, `send_new_offer_notice`

**onboarding_handoff**: `create_payroll_precheck`, `create_submitted_assignment_after_acceptance`, `no_payroll_handoff`

**payroll_handoff_gate**: `accepted_offer_only`, `accepted_offer_and_submitted_assignment`, `all_interviewed_candidates`

**payroll_assignment_status_required**: `submitted_after_acceptance`, `submitted`, `draft_allowed`

**offer_exclusion_reason_for_waitlisted**: `no_accepted_status_or_offer`, `waitlisted_not_selected`, `already_rejected`

**handoff_control_result**: `submitted_handoff_required_after_acceptance`, `submitted_handoff_required`, `no_handoff_required`

**candidate_status_source**: `interview_feedback_and_offer`, `case_summary_only`, `message_only`

**candidate_outcome_control**: `committee_decision_with_offer_confirmation`, `message_status_only`, `case_summary_only`

**selected_offer_status**: `accepted`, `draft`, `withdrawn`, `none`

**cost_source**: `recruitment_cost_ledger`, `case_summary_only`

**waitlisted_followup_action**: `send_waitlist_notice`, `reissue_waitlist_notice_not_rejection`, `no_action`

**rejected_followup_action**: `send_rejection_notice`, `no_action`, `reissue_rejection_notice`

## Business rules

### Leave source precedence (LEAVE-SRC-001)
- The **latest approved or submitted** leave assignment for the period controls leave
  entitlement.
- Draft, voided, and obsolete (superseded) records are **excluded** even when profile
  summaries conflict.
- An approved leave assignment **overrides** a stale employee profile summary.
- When the ledger (payroll-ledgers), policy document (LEAVE-SRC-001), and audit detail
  all confirm the approved assignment, the profile summary must be ignored
  (`profile_policy_ignored: true`).
- Use `precedence_source: "approved_assignment_over_profile"` and
  `leave_precedence_source: "approved_assignment_current_period"`.

### Payroll assignment source (PAY-SRC-001)
- Use the **current submitted** salary assignment for base salary and accrual checks.
- **Draft** planning assignments do **not** affect payroll readiness or accrual checks.
- Exclude draft assignments using `draft_exclusion_rule: "exclude_draft_assignment"`.
- The payroll source status is `"submitted"` (the authoritative assignment's status).

### Recruiting handoff gate (PAY-SRC-001 section 4.2)
- The recruiting payroll handoff is created **only after** a selected candidate has an
  **accepted offer**.
- The handoff **must be submitted**; draft prechecks do **not** satisfy the assignment gate.
- `payroll_handoff_gate: "accepted_offer_only"` — the gate trigger is the accepted offer.
  The submitted-status requirement is captured separately in
  `payroll_assignment_status_required`.
- `draft_payroll_allowed: false` — draft assignments/prechecks never satisfy the gate.
- `offer_exclusion_reason_for_waitlisted: "no_accepted_status_or_offer"` — the waitlisted
  candidate is excluded from the offer/payroll handoff because they have no accepted offer
  status or offer record. Use this label, not the committee-decision label
  `"waitlisted_not_selected"`.
- `onboarding_handoff: "create_submitted_assignment_after_acceptance"` — create a submitted
  (not draft) assignment after the offer is accepted.

### Folder readiness (POL-DOCS-2026)
- A folder is **not ready** unless **all** required files AND **all** required tags shown in
  the folder checklist are present.
- `folder_ready` = the folder object's `ready` boolean.
- `missing_files` = items in `required_files` not in `files`.
- `required_tag_present` = true only if **all** `required_tags` are in `tags`.
- `folder_required_tag_action`: `"add_required_tag"` if any required tag is missing,
  otherwise `"no_tag_action"`.
- `closeout_blockers` includes `"missing_required_files"` if any files are missing,
  `"missing_required_tags"` if any tags are missing, and
  `"defective_formal_notice"` if the notice is defective.

### Notice defect detection
- Inspect the formal notice (message + notification) for defects.
- `notice_quality: "defective"` if any defect is present, otherwise `"valid"`.
- Defect types: `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`.
- `notice_defects` lists all defects found in the message's `defects[]` array.
- `notice_evidence_source / notice_quality_source: "notice_packet_inspection"` when
  inspecting notice_packets in recruitment data; `"message_notice_inspection"` when
  inspecting `/api/messages`.

### Approval closeout gate
- If both the folder is ready (no missing files, no missing tags) AND the notice is valid
  (no defects): `approval_closeout_gate: "approval_sufficient_when_records_clean"` and
  `final_control_result: "approve_closeout"`.
- If either the folder is not ready OR the notice is defective:
  `approval_closeout_gate: "approval_not_sufficient_when_folder_or_notice_defective"` and
  `final_control_result: "hold_for_folder_and_notice_defects"`.
- If the assignment is ready but requires monitoring (per audit):
  `final_control_result / control_result: "ready_with_monitoring"`.

### Audit selection and scope
- **Audit scope must match the task type**:
  - Leave source precedence task: `audit_scope: "leave_source_precedence_only"`
  - Document/notice review task: `audit_scope: "document_notice_findings_only"`
  - Payroll assignment readiness task: `audit_scope: "payroll_assignment_readiness"`
- **Supporting audit events**: include only audit events relevant to the task scope.
  - For leave tasks: include `leave.*` events (e.g. `leave.profile_mismatch`).
  - For payroll tasks: include `payroll.*` events (e.g. `payroll.ready`).
  - For document/notice tasks: include `notice.defect` and `folder.*` events.
- **Excluded audit events**: exclude adjacent audit events that are outside the task scope.
  - For leave tasks: exclude `folder.tag_missing`, `notice.defect` events.
  - For document/notice tasks: exclude `leave.*`, `payroll.*` events.
  - Leave the list empty `[]` if no adjacent events exist.

### Escalation owner
- `records_remediation_owner: "Records"` when the issue is missing files or missing tags
  in the document folder.
- `records_remediation_owner: "People Ops Compliance"` for cross-module or compliance
  escalations.
- `records_remediation_owner: "Payroll QA"` for payroll draft/assignment issues.
- `escalation_action: "open_records_remediation"` when folder/files need remediation.
- `escalation_action: "block_close_and_reissue_notice"` when the formal notice is
  defective and must be reissued.
- `notice_remediation_action: "reissue_defective_notices"` when the notice has defects.

### Cost-summing (recruitment)
- `recruitment_cost_total` = the **sum of all** `amount` values in the recruitment
  `cost_ledger[]` array.
- `cost_source: "recruitment_cost_ledger"` — always use the ledger, never the case summary.

### Candidate outcomes (recruitment)
- `selected_candidate` = the candidate with `committee_decision: "Selected"` AND an entry
  in the `offer_register` with `status: "accepted"`.
- `waitlisted_candidates` = candidates with `committee_decision: "Waitlisted"` (IDs only).
- `rejected_candidates` = candidates with `committee_decision: "Rejected"` (IDs only).
- `notice_followup_required` = candidate IDs whose notice packet `status` is `"not_sent"`
  (IDs only, no other text).
- `waitlisted_followup_action: "send_waitlist_notice"` when the waitlist notice has not
  been sent.
- `rejected_followup_action: "send_rejection_notice"` when the rejection notice has not
  been sent.
- `candidate_status_source: "interview_feedback_and_offer"` — outcomes come from
  committee decisions and the offer register.
- `candidate_outcome_control: "committee_decision_with_offer_confirmation"` — committee
  decisions confirmed by offer register status.
- `selected_offer_status: "accepted"` — from the offer register.

## Common misjudgments and exclusion rules

These are errors that reduced judge scores during training. Avoid them:

1. **payroll_handoff_gate**: Use `"accepted_offer_only"`, NOT
   `"accepted_offer_and_submitted_assignment"`. The gate is the trigger condition
   (accepted offer). The submitted-status requirement is a separate field
   (`payroll_assignment_status_required`).

2. **offer_exclusion_reason_for_waitlisted**: Use `"no_accepted_status_or_offer"`, NOT
   `"waitlisted_not_selected"`. The exclusion reason is the absence of an accepted offer
   status or offer record, not the committee's waitlist decision.

3. **Leave records to exclude**: Exclude ALL non-authoritative leave records — both
   Superseded AND Draft. Do not include only one type. The excluded list should contain
   every ledger ID that is not the authoritative approved/submitted assignment.

4. **Payroll records to exclude**: Exclude ALL Draft salary assignments. A Draft salary
   assignment with a higher salary number is still excluded in favor of the Submitted
   assignment.

5. **audit_scope mismatch**: Do not use a document/notice audit scope for a leave task,
   or vice versa. The audit scope must match the task archetype exactly.

6. **Excluded audit events**: For leave tasks, document/folder audit events (e.g.
   `folder.tag_missing`) must be listed in `excluded_audit_event_ids`, not in
   `supporting_audit_event_ids`. Only leave-scope audit events go in supporting.

7. **closeout_blockers**: Include ALL applicable blockers, not just one. If both files are
   missing AND the notice is defective, include both
   `"missing_required_files"` and `"defective_formal_notice"`.

8. **Folder tag check**: `required_tag_present` is true only if ALL required tags are
   present. A single missing required tag means `required_tag_present: false` and
   `folder_required_tag_action: "add_required_tag"`.

9. **Notice defects**: Copy defects exactly from the message's `defects[]` array. Do not
   infer defects that are not listed, and do not omit defects that are listed.

10. **Cost total**: Sum ALL cost_ledger items. Do not exclude any line item, even if it
    seems like an outlier or administrative charge.

11. **evidence_source_order**: For tasks that review approvals, folder, notice, and audit,
    use `"approval_history_folder_notice_audit"`. Do not abbreviate to
    `"folder_notice_audit"` if approval history was also reviewed.

12. **precedence_source vs leave_precedence_source**: These are different fields with
    different enum values. `precedence_source` uses
    `"approved_assignment_over_profile"` while `leave_precedence_source` uses
    `"approved_assignment_current_period"`. Do not confuse them.

## Pre-submission checklist

Before submitting any answer JSON, verify:

- [ ] All required fields from the answer template are present (no missing fields).
- [ ] All enum values match exactly one of the `allowed_values` from the template.
- [ ] `employee_id`, `case_id`, or `opening_id` matches the prompt exactly.
- [ ] The authoritative leave assignment is the **latest Approved** record (check
      `updated_at` timestamp and `status`).
- [ ] The authoritative salary assignment is the **Submitted** record.
- [ ] All non-authoritative leave/salary ledger IDs are in the excluded lists.
- [ ] `audit_scope` matches the task archetype.
- [ ] `supporting_audit_event_ids` contains only in-scope audit events.
- [ ] `excluded_audit_event_ids` contains only out-of-scope adjacent audit events.
- [ ] `final_control_result` is consistent with the approval closeout gate:
      - `approval_sufficient_when_records_clean` → `approve_closeout`
      - `approval_not_sufficient_when_folder_or_notice_defective` →
        `hold_for_folder_and_notice_defects`
      - `payroll.ready` audit result → `ready_with_monitoring`
- [ ] For recruitment tasks: `recruitment_cost_total` is the sum of all cost_ledger items.
- [ ] For recruitment tasks: all arrays contain candidate IDs only (no names, no text).
- [ ] `payroll_handoff_gate` is `"accepted_offer_only"` (not
      `"accepted_offer_and_submitted_assignment"`).
- [ ] `offer_exclusion_reason_for_waitlisted` is `"no_accepted_status_or_offer"` (not
      `"waitlisted_not_selected"`).
- [ ] `profile_policy_ignored` is `true` when the audit result is
      `profile_summary_stale`.
- [ ] `notice_defects` exactly matches the message's `defects[]` array.
- [ ] `closeout_blockers` includes ALL applicable blockers.
- [ ] `required_tag_present` is `false` if ANY required tag is missing.
- [ ] `folder_required_tag_action` is `"add_required_tag"` if any required tag is missing,
      otherwise `"no_tag_action"`.
- [ ] Output is valid JSON matching the answer template — no markdown, no explanatory
      text, no trailing commas.
