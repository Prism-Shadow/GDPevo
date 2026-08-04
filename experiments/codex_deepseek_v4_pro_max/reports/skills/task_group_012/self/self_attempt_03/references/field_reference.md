
# Answer Template Field Reference

## Employee-Focused Fields (Train 001, 004, 005)

| Field | Type | Appears In | Description |
|-------|------|------------|-------------|
| `employee_id` | string | 001, 004, 005 | Target employee identifier |
| `effective_leave_policy` | string | 001, 004 | Name of the authoritative leave policy |
| `leave_source` | enum | 001 | How leave policy was determined |
| `annual_days` / `balance_days` | integer | 001, 004 | Leave balance in days |
| `assignment_id` | string | 001, 004 | Authoritative leave assignment identifier |
| `excluded_leave_ids` | list[string] | 001 | Leave record IDs that must be excluded (drafts/superseded) |
| `profile_policy_ignored` | boolean | 004 | Whether the profile summary policy should be ignored |
| `salary_assignment_id` / `payroll_assignment_id` | string | 001, 005 | Authoritative payroll assignment identifier |
| `base_salary` | number | 001, 005 | Base salary amount |
| `effective_date` | string | 005 | Effective date of the payroll assignment |
| `excluded_assignment_id` | string | 005 | Payroll assignment ID to exclude (draft) |
| `excluded_payroll_ids` | list[string] | 001 | Payroll record IDs that must be excluded |
| `accrual_ready` | boolean | 005 | Whether the accrual batch is ready to proceed |
| `accrual_batch_id` | string | 005 | Accrual batch identifier |

## Case-Focused Fields (Train 002)

| Field | Type | Appears In | Description |
|-------|------|------------|-------------|
| `case_id` | string | 002 | Target case identifier |
| `final_decision` | enum | 002 | Final decision on the case |
| `approval_authority` | string | 002 | Entity that holds approval authority |
| `approval_event_id` | string | 002 | The approval event identifier |
| `folder_ready` | boolean | 002 | Whether case folder is complete |
| `missing_files` | list[string] | 002 | Required files not found in folder |
| `required_tag_present` | boolean | 002 | Whether required tag is on the case |
| `notice_quality` | enum | 002 | Quality of the formal notice |
| `notice_defects` | list[enum] | 002 | Specific defects found in the notice |
| `closeout_blockers` | list[enum] | 002 | Blockers preventing closeout |
| `folder_required_tag_action` | enum | 002 | Action needed for required tag |

## Audit-Focused Fields (Train 002, 004, 005)

| Field | Type | Appears In | Description |
|-------|------|------------|-------------|
| `audit_event_id` | string | 002, 004, 005 | Primary audit event for this review |
| `supporting_audit_event_ids` | list[string] | 002, 004 | Audit events supporting the decision (in-scope) |
| `excluded_audit_event_ids` | list[string] | 002, 004 | Audit events excluded (out-of-scope) |
| `audit_scope` | enum | 002, 004, 005 | Scope of the audit review |
| `audit_result` | enum | 004 | Finding from the audit review |

## Recruitment-Focused Fields (Train 003)

| Field | Type | Appears In | Description |
|-------|------|------------|-------------|
| `opening_id` | string | 003 | Recruitment opening identifier |
| `selected_candidate` | string | 003 | Candidate ID selected for the role |
| `waitlisted_candidates` | list[string] | 003 | Candidate IDs on waitlist |
| `rejected_candidates` | list[string] | 003 | Candidate IDs rejected |
| `offer_id` | string | 003 | Offer identifier for selected candidate |
| `offer_base_salary` | number | 003 | Base salary on the offer |
| `recruitment_cost_total` | number | 003 | Sum of recruitment cost ledger entries |
| `notice_followup_required` | list[string] | 003 | Candidate IDs needing notice followup |

## Control & Gate Fields (Cross-cutting)

| Field | Type | Appears In | Description |
|-------|------|------------|-------------|
| `closeout_action` / `next_action` | enum | 001, 002, 004 | Action to take after review |
| `approval_closeout_gate` | enum | 001, 002 | Gate status for approval/closeout |
| `final_control_result` / `control_result` | enum | 001, 005 | Final result of the control check |
| `leave_precedence_source` / `precedence_source` | enum | 001, 004 | Source that determined leave precedence |
| `payroll_source_status` | enum | 001, 005 | Status of the payroll source record |
| `draft_payroll_allowed` | boolean | 003 | Whether draft payroll assignments are acceptable |
| `evidence_source_order` | enum | 002 | Chain of evidence used for decision |
| `notice_evidence_source` | enum | 002 | Source used for notice quality assessment |
| `handoff_control_result` | enum | 003 | Result of payroll handoff check |
| `candidate_status_source` | enum | 003 | Source for candidate status determination |
| `candidate_outcome_control` | enum | 003 | Control mechanism for candidate outcomes |
| `selected_offer_status` | enum | 003 | Status of the selected candidate's offer |
| `cost_source` | enum | 003 | Source for recruitment cost data |
| `notice_quality_source` | enum | 003 | Source for notice quality determination |
| `waitlisted_followup_action` | enum | 003 | Action for waitlisted candidates |
| `rejected_followup_action` | enum | 003 | Action for rejected candidates |
| `payroll_handoff_gate` | enum | 003 | Gate condition for payroll handoff |
| `payroll_assignment_status_required` | enum | 003 | Required status for payroll assignment |
| `offer_exclusion_reason_for_waitlisted` | enum | 003 | Why waitlisted candidates are excluded from offers |
| `onboarding_handoff` | enum | 003 | Onboarding handoff action |
| `draft_exclusion_rule` | enum | 005 | Rule applied for draft exclusion |
