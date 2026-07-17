# People Lifecycle HRMS — Operations Skill

## Environment
- **Base URL**: `http://34.46.77.124:8012`
- **Credentials**: `ops.lead@peopleops.local` / `PeopleOps#2026`
- All endpoint references below are relative to the base URL.

## API Endpoint Reference

| Endpoint | Purpose |
|---|---|
| `GET /api/manifest` | Module inventory, file counts, entry points |
| `GET /api/summary` | Case counts by status, department list |
| `GET /api/employees` | All employee profiles (44 total) |
| `GET /api/cases` | All cases with status, owner, policy refs |
| `GET /api/cases/<case_id>` | Case detail: approvals, attachments, audit events, comments, policy refs |
| `GET /api/policies` | Policy documents with sections, effective dates, owners |
| `GET /api/payroll-ledgers` | Leave assignments AND salary assignments (61 records shared ledger) |
| `GET /api/recruitment` | Openings with candidates, offer registers, cost ledgers, notice packets, payroll precheck records |
| `GET /api/documents` | Document folders with files, required_files, required_tags, tags, readiness |
| `GET /api/audit` | All audit events with actor, event type, detail, case linkage |
| `GET /api/audit/<event_id>` | Single audit event detail |
| `GET /api/messages` | Messages/notices sent or pending |
| `GET /api/notifications` | System notifications |

---

## Business Domain Workflows

### 1. Employee Onboarding Closeout (Leave + Payroll Verification)

**Trigger**: Employee status is `"Onboarding"`. Before approving closeout, verify leave setup and payroll setup.

**API Workflow**:
1. `GET /api/employees` — locate the employee by `employee_id`, confirm `status: "Onboarding"`
2. `GET /api/payroll-ledgers` — find all records for the employee, then split into:
   - **Leave assignments**: `record_type: "Leave assignment"` — has `policy_name`, `approved_leave_days`, `worksheet_leave_days`, `period`
   - **Salary assignments**: `record_type: "Salary assignment"` — has `base_salary`, `period`
3. `GET /api/cases` — find associated onboarding case for the employee
4. `GET /api/audit` — check for audit events linked to the employee/case

**Record Status Filtering Rules**:
- **Draft records**: ALWAYS exclude. Draft records have `status: "Draft"` and represent planning/worksheet data, not committed assignments.
- **Superseded records**: Exclude. Superseded records (`status: "Superseded"`) were replaced by a later approved assignment and are no longer authoritative.
- **Approved (leave) / Submitted (payroll)**: These ARE the authoritative records for the current period.

**Leave Source Precedence**:
- An **approved leave assignment** in the payroll ledger (`status: "Approved"`) overrides the employee profile summary's `leave_balance_days` and any policy name implied by the profile.
- Source label: `"leave_assignment_history"` → normalizes to `leave_precedence_source: "approved_assignment_current_period"`
- The employee profile summary (`GET /api/employees`) is secondary; use it only when no approved assignment exists.

**Payroll Source Precedence**:
- A **submitted salary assignment** (`status: "Submitted"`) controls base salary.
- Source label: `payroll_source_status: "submitted"`
- Draft salary assignments (`status: "Draft"`) are excluded from payroll readiness.

**Closeout Decision Logic**:
- If all leave assignments have exactly one Approved (no Draft/Superseded confusion) AND payroll has exactly one Submitted (no Draft): → `closeout_action: "approve_onboarding_close"`, `final_control_result: "approve_closeout"`
- If records have Draft or Superseded entries that need cleanup: → `closeout_action: "open_records_remediation"`

**Field Mapping for Onboarding Closeout**:
| Field | Source | Notes |
|---|---|---|
| `effective_leave_policy` | `policy_name` of the Approved leave assignment | From payroll-ledgers |
| `annual_days` | `approved_leave_days` of the Approved leave assignment | Integer |
| `assignment_id` | `ledger_id` of the Approved leave assignment | |
| `excluded_leave_ids` | All ledger_ids with status Draft or Superseded | Array of strings |
| `payroll_assignment_id` | `ledger_id` of the Submitted salary assignment | |
| `base_salary` | `base_salary` of the Submitted salary assignment | Number, from payroll-ledgers |
| `excluded_payroll_ids` | All salary ledger_ids with status Draft | |
| `leave_source` | `"leave_assignment_history"` | Fixed when using ledger |
| `payroll_status` | `"submitted"` | Fixed when using submitted record |
| `leave_precedence_source` | `"approved_assignment_current_period"` | |

---

### 2. Case Folder & Formal Notice Quality Review

**Trigger**: A policy case (remote-work exception, leave, etc.) requires folder readiness and notice quality verification before closeout.

**API Workflow**:
1. `GET /api/cases/<case_id>` — get approvals, attachments (folder checklist), audit events, comments
2. `GET /api/documents` — locate the folder for the case; check `files`, `required_files`, `tags`, `required_tags`
3. `GET /api/policies` — review relevant policy sections for required notice elements
4. `GET /api/audit` — find audit events linked to the case, paying attention to `notice.defect` and `folder.*` events
5. `GET /api/cases/<case_id>/comments` — review internal comments for defect notes
6. `GET /api/messages` and `GET /api/notifications` — inspect notice packets for quality

**Folder Readiness Rules**:
- A folder is **ready** (`folder_ready: true`) ONLY when:
  - ALL `required_files` are present in `files`
  - ALL `required_tags` are present in `tags`
- Compute `missing_files` as: `required_files` minus `files` (set difference)
- Tag check: `required_tag_present` is `true` when all `required_tags` ⊆ `tags`
- When tags are all present: `folder_required_tag_action: "no_tag_action"`; otherwise `"add_required_tag"`

**Notice Quality Rules**:
- Formal notices are inspected for required elements as defined in the governing policy:
  - Remote work exception notices (HR-POL-014 §7.1) require: acknowledgement deadline, appeal instructions, tax equalization terms
- **Defect types** (from answer template enum):
  - `"missing_ack_deadline"` — notice lacks response/acknowledgement deadline
  - `"missing_appeal_instructions"` — notice lacks appeal process description
  - `"missing_waitlist_status"` — waitlist notice omits candidate status
  - `"missing_correct_policy"` — notice references wrong policy
- Notice quality is `"valid"` only when zero defects; `"defective"` otherwise

**Evidence Source Order**:
- `"approval_history_folder_notice_audit"` — full chain: check approvals first, then folder checklist, then notice quality, then audit events
- `"folder_notice_audit"` — skip approvals, start at folder
- `"audit_only"` — rely solely on audit events

**Decision Logic**:
- Folder ready AND notice valid → `final_decision: "approved"`, `approval_closeout_gate: "approval_sufficient_when_records_clean"`, `final_control_result: "approve_closeout"`
- Folder ready BUT notice defective → `final_decision: "approved_with_conditions"`, `approval_closeout_gate: "approval_not_sufficient_when_folder_or_notice_defective"`, `next_action: "block_close_and_reissue_notice"`, `final_control_result: "hold_for_folder_and_notice_defects"`
- Folder NOT ready → same gate as above, `escalation_action: "open_records_remediation"`

**Closeout Blocker Mapping**:
- `missing_files` non-empty → blocker `"missing_required_files"`
- `required_tag_present: false` → blocker `"missing_required_tags"`
- `notice_quality: "defective"` → blocker `"defective_formal_notice"`

**Records Remediation**:
- When `escalation_action: "open_records_remediation"`, set `records_remediation_owner`:
  - Missing files → `"Records"`
  - Missing tags → `"Records"`
  - Defective notice → `"Records"` (responsible for reissue)
- `notice_remediation_action`:
  - Defective formal notice → `"reissue_defective_notices"`
  - Valid notice → `"no_notice_action"`
  - Waitlist notice defect → `"reissue_waitlist_notice_not_rejection"`

**Audit Scope for Document/Notice Decisions**:
- Scope: `"document_notice_findings_only"` — only audit events related to folder/files/tags and notice quality
- `supporting_audit_event_ids`: audit events that confirm the finding
- `excluded_audit_event_ids`: audit events for other scopes (leave, payroll) that should NOT influence the document/notice decision

---

### 3. Recruitment Reconciliation

**Trigger**: A recruitment opening case needs outcome reconciliation — classify candidates, verify offers, compute costs, determine follow-up notices, and set up payroll handoff.

**API Workflow**:
1. `GET /api/recruitment` — locate the opening by `opening_id`; extract candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records
2. `GET /api/cases/<case_id>` (if case_id differs from opening_id) — cross-reference
3. `GET /api/policies` — check PAY-SRC-001 for handoff gate rules
4. `GET /api/audit` — check for recruitment-related audit events

**Candidate Classification**:
- Candidates are classified by `committee_decision` field:
  - `"Selected"` → `selected_candidate` (single candidate ID string)
  - `"Waitlisted"` → `waitlisted_candidates` (array of candidate IDs)
  - `"Rejected"` → `rejected_candidates` (array of candidate IDs)
- Candidate outcome source: `"interview_feedback_and_offer"` (from committee decision + offer register)
- Outcome control: `"committee_decision_with_offer_confirmation"`

**Offer Handling**:
- Selected candidate's offer from `offer_register`: read `offer_id`, `base_salary`, `status`
- `selected_offer_status`: the `status` of the selected candidate's offer (`"accepted"`, `"draft"`, `"withdrawn"`, `"none"`)
- Only `"accepted"` offers trigger payroll handoff

**Cost Calculation**:
- `recruitment_cost_total`: SUM of ALL `amount` values in `cost_ledger` array
- Cost source: `"recruitment_cost_ledger"`
- Do NOT filter or exclude any ledger line items — sum everything

**Notice Follow-up**:
- Check `notice_packets` for each non-selected candidate:
  - `notice_type: "waitlist"` with `status: "not_sent"` → `waitlisted_followup_action: "send_waitlist_notice"`
  - `notice_type: "rejection"` with `status: "not_sent"` → `rejected_followup_action: "send_rejection_notice"`
  - If notice exists but is defective → `"reissue_waitlist_notice_not_rejection"` or `"reissue_rejection_notice"`
  - If notice already sent and valid → `"no_action"`
- `notice_followup_required`: array of candidate IDs that need any follow-up notice
- Notice quality source: `"notice_packet_inspection"` (from recruitment notice_packets)

**Payroll Handoff Rules** (per PAY-SRC-001 §4.2):
- `payroll_handoff_gate: "accepted_offer_only"` — only the accepted candidate triggers handoff
- `onboarding_handoff`: `"create_payroll_precheck"` when handoff is needed
- `payroll_assignment_status_required: "submitted_after_acceptance"` — handoff must be submitted, not draft
- `draft_payroll_allowed`: `false` — draft payroll precheck records do not satisfy the gate
- Check `payroll_precheck_records`: if any exist with `status: "Draft"`, they must be excluded
- `offer_exclusion_reason_for_waitlisted`: `"no_accepted_status_or_offer"` — waitlisted candidates have no accepted offer
- `handoff_control_result`: `"submitted_handoff_required_after_acceptance"` when selected candidate has accepted

---

### 4. Leave Source Precedence Validation

**Trigger**: An employee's leave policy/balance needs reconciliation — the profile summary may be stale vs. the approved assignment in the ledger.

**API Workflow**:
1. `GET /api/employees` — get profile `leave_balance_days`
2. `GET /api/payroll-ledgers` — find approved leave assignment for the employee
3. `GET /api/policies` — review LEAVE-SRC-001 (source precedence policy)
4. `GET /api/audit` — find audit events linked to the employee's leave case
5. `GET /api/cases` — find the leave-related case

**Precedence Rule** (per LEAVE-SRC-001 §2.1):
- An **Approved leave assignment** in the ledger ALWAYS overrides the employee profile summary
- When ledger and profile disagree, the ledger wins
- `precedence_source: "approved_assignment_over_profile"` → normalizes to `leave_precedence_source: "approved_assignment_current_period"`
- `profile_policy_ignored: true` when the profile summary is stale

**Audit Event Scoping for Leave Decisions**:
- Scope: `"leave_source_precedence_only"`
- `supporting_audit_event_ids`: audit events that confirm the leave source finding (event type `leave.*`)
- `excluded_audit_event_ids`: audit events related to document/folder/notice that are adjacent but should NOT influence the leave decision (event types `folder.*`, `notice.*`, `document.*`)

**Decision Logic**:
- Approved assignment exists AND profile is stale → `audit_result: "profile_summary_stale"`, `next_action: "update_employee_summary"`
- All aligned → `audit_result: "ready_with_monitoring"`, `next_action: "no_action"`

**Field Mapping**:
| Field | Source |
|---|---|
| `effective_leave_policy` | `policy_name` from the Approved leave assignment ledger |
| `assignment_id` | `ledger_id` from the Approved leave assignment |
| `balance_days` | `approved_leave_days` from the Approved leave assignment (integer) |
| `precedence_source` | `"approved_assignment_over_profile"` |
| `leave_precedence_source` | `"approved_assignment_current_period"` |

---

### 5. Payroll Assignment & Accrual Readiness

**Trigger**: Verify an employee's payroll assignment is authoritative and accrual batches are ready.

**API Workflow**:
1. `GET /api/payroll-ledgers` — find all salary assignment records for the employee
2. `GET /api/audit` — find payroll-related audit events
3. `GET /api/policies` — review PAY-SRC-001 for salary source rules
4. `GET /api/cases/<case_id>` — check case status

**Record Selection Rules** (per PAY-SRC-001 §3.4):
- Use the **submitted salary assignment** — `record_type: "Salary assignment"` with `status: "Submitted"`
- **Exclude draft assignments**: `status: "Draft"` salary assignments are planning records only
- `payroll_source_status: "submitted"`
- `draft_exclusion_rule: "exclude_draft_assignment"`

**Accrual Readiness**:
- `accrual_batch_id` is identified from the audit event detail or case attachment
- Format: `ACCR-YYYY-MM-X` (e.g., `ACCR-2026-04-B` for April 2026 batch B)
- `accrual_ready: true` when the submitted assignment matches the accrual batch and no blockers exist
- `effective_date`: the `period` field from the salary assignment, or the hire date for new hires, in `YYYY-MM-DD` format

**Audit Scope**:
- `audit_scope: "payroll_assignment_readiness"`

**Control Result**:
- Submitted assignment found, accrual matches → `control_result: "ready_with_monitoring"`
- Draft confusion or mismatch → `control_result: "hold_for_folder_and_notice_defects"`

---

## Cross-Cutting Rules

### Record Status Hierarchy (Source Precedence)
For ALL record types (leave assignments, salary assignments, offers):
1. **Submitted / Approved** — authoritative; use for all business decisions
2. **Superseded** — was once authoritative but replaced; exclude from current decisions
3. **Draft** — planning/worksheet only; NEVER authoritative; always exclude

### Audit Event Scoping
When an audit scope is specified, ONLY include audit events matching that domain:
- `"leave_source_precedence_only"` → events with `leave.*` pattern in `event` field
- `"document_notice_findings_only"` → events with `notice.*`, `folder.*`, `document.*` patterns
- `"payroll_assignment_readiness"` → events with `payroll.*` pattern

Exclude events from other domains in `excluded_audit_event_ids`. Include supporting events in `supporting_audit_event_ids`.

### ID Format Conventions
- Employees: `EMP-NNN`
- Leave assignments: `LA-NNN-YYYY-X` or `LA-NNN-APP-NN`
- Salary/payroll assignments: `PAY-NNN-YYYY-SUB` or `PAY-NNN-SUB-NN`
- Draft assignments: suffix `-DRAFT` or `-DRAFT-NN`
- Cases: `CASE-NNN` or `CASE-RW-NNN` or `REQ-XX-NN`
- Audit events: `AUD-XXXX-NN`
- Offers: `OFFER-XX-NNNN`
- Candidates: `CAND-XX-NNNN`
- Accrual batches: `ACCR-YYYY-MM-X`
- Documents: `DOC-XXXX-XXX`

### Sorting Rules
- Candidate arrays: sort by candidate_id ascending
- Excluded IDs: sort by ledger_id ascending
- Audit event IDs: sort alphanumerically

### Date Conventions
- `effective_date`: ISO date format `YYYY-MM-DD`
- Payroll periods: `YYYY-MM` format
- Leave periods: `YYYY` format
- Timestamps: ISO 8601 `YYYY-MM-DDTHH:MM`

### Normalized Enum Values — Quick Reference

**closeout_action**: `approve_onboarding_close` | `block_close_and_reissue_notice` | `open_records_remediation`

**final_control_result**: `approve_closeout` | `hold_for_folder_and_notice_defects` | `ready_with_monitoring`

**approval_closeout_gate**: `approval_sufficient_when_records_clean` | `approval_not_sufficient_when_folder_or_notice_defective`

**leave_precedence_source** / **leave_source**: `approved_assignment_current_period` | `profile_summary_current_period` | `case_summary_only` (use `leave_assignment_history` for leave_source field specifically)

**payroll_status** / **payroll_source_status**: `submitted` | `draft` | `superseded`

**audit_scope**: `leave_source_precedence_only` | `document_notice_findings_only` | `payroll_assignment_readiness`

**final_decision**: `approved_with_conditions` | `approved` | `rejected` | `held`

**notice_quality**: `valid` | `defective`

**next_action**: `block_close_and_reissue_notice` | `approve_onboarding_close` | `open_records_remediation` | `update_employee_summary` | `no_action`

**records_remediation_owner**: `Records` | `People Ops Compliance` | `Payroll QA`

**notice_remediation_action**: `reissue_defective_notices` | `no_notice_action` | `send_new_offer_notice`

**candidate_outcome_control**: `committee_decision_with_offer_confirmation` | `message_status_only` | `case_summary_only`

**selected_offer_status**: `accepted` | `draft` | `withdrawn` | `none`

**payroll_handoff_gate**: `accepted_offer_only` | `accepted_offer_and_submitted_assignment` | `all_interviewed_candidates`

**handoff_control_result**: `submitted_handoff_required_after_acceptance` | `submitted_handoff_required` | `no_handoff_required`

---

## Common Pitfalls

1. **Draft records masquerading as authoritative**: Always filter by `status` before using any ledger/assignment record. Draft records often have realistic-looking data (salary, days) but are planning artifacts.

2. **Confusing leave assignments with salary assignments in the ledger**: `/api/payroll-ledgers` returns both types. Always filter by `record_type` first (`"Leave assignment"` vs `"Salary assignment"`), then by status.

3. **Using employee profile summary when a ledger assignment exists**: The profile `leave_balance_days` may be stale. Always check the ledger for an Approved assignment first; if one exists, it overrides the profile.

4. **Including adjacent audit events in the wrong scope**: When the task asks for leave-scope decisions, exclude document/notice audit events. When it asks for document/notice decisions, exclude leave/payroll audit events.

5. **Missing the cost total sum**: `recruitment_cost_total` is the SUM of ALL cost_ledger `amount` values — do not filter, do not average, do not pick the largest.

6. **Folder readiness requires BOTH files AND tags**: A folder is only ready when ALL required_files are present AND ALL required_tags are present. Missing either → `folder_ready: false`.

7. **Conditional approval vs. pure approval**: When a case has an approval decision of `"Approved"` but the folder/notice has defects, the `final_decision` is `"approved_with_conditions"` (not `"approved"`). Pure `"approved"` requires clean folder AND clean notice.

8. **Notice packets vs. messages vs. case summary for notice quality**: Use `notice_packet_inspection` when recruitment notice_packets exist; use `message_notice_inspection` when only messages are available; use `case_summary_only` as last resort.

9. **Payroll handoff requires accepted offer**: Per PAY-SRC-001 §4.2, only candidates with an accepted offer trigger payroll handoff. Waitlisted and rejected candidates do not.

10. **Superseded is not Draft**: Superseded records were once valid but replaced. Draft records were never valid. Both are excluded from current decisions, but for different reasons — `excluded_leave_ids` should contain both, but the business rationale differs.

11. **approval_closeout_gate is binary**: It's either `"approval_sufficient_when_records_clean"` (records have no defects) or `"approval_not_sufficient_when_folder_or_notice_defective"` (any defect found). There is no middle ground.

12. **Single selected candidate vs. arrays**: `selected_candidate` is always a SINGLE string (the candidate_id). `waitlisted_candidates` and `rejected_candidates` are always arrays of strings.
