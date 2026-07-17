# PeopleOps Console — Review & Closeout Skill

## 1. Environment & Login
- Open `http://34.46.77.124:8012` (resolves `<TASK_ENV_BASE_URL>`).
- Login: `ops.lead@peopleops.local` / `PeopleOps#2026`.
- Return **only** JSON matching the task’s `answer_template.json`. No markdown, no extra text.

## 2. Source Precedence (Universal)
Use the strongest available source; never default to a weaker one when a stronger exists.

| Domain | Strongest → Weakest |
|--------|---------------------|
| Leave policy / balance | `leave_assignment_history` (approved, current period) → `employee_profile_summary` → `case_summary_only` |
| Payroll assignment | `submitted` → `superseded` → `draft` (always exclude draft) |
| Candidate status | `interview_feedback_and_offer` → `case_summary_only` → `message_only` |
| Recruitment cost | `recruitment_cost_ledger` (sum every campaign line item) → `case_summary_only` |
| Notice quality | `notice_packet_inspection` → `message_notice_inspection` → `case_summary_only` |
| Evidence order | `approval_history_folder_notice_audit` → `folder_notice_audit` → `audit_only` |

**Rule of thumb:** An approved assignment that is confirmed by ledger, policy document, and audit detail **overrides** any stale employee-profile summary.

## 3. Exclusion Rules
- **Drafts:** Always list draft IDs in the relevant `excluded_*` array (e.g., `excluded_leave_ids`, `excluded_payroll_ids`).
- **Superseded:** Exclude superseded records when a newer submitted/approved record exists.
- **Audit events:** For a scoped decision, include only audit events that directly support that scope in `supporting_audit_event_ids`; place adjacent/irrelevant audit events in `excluded_audit_event_ids`.
  - Leave-scope review → exclude document/notice audit events.
  - Document/notice-scope review → exclude leave-source audit events.

## 4. Closeout & Control Decision Tree
1. **Records clean + no defects**  
   - `closeout_action`: `approve_onboarding_close`  
   - `approval_closeout_gate`: `approval_sufficient_when_records_clean`  
   - `final_control_result`: `approve_closeout`
2. **Missing required files, missing required tags, or defective formal notice**  
   - `closeout_action`: `block_close_and_reissue_notice`  
   - `approval_closeout_gate`: `approval_not_sufficient_when_folder_or_notice_defective`  
   - `final_control_result`: `hold_for_folder_and_notice_defects`  
   - `closeout_blockers`: list applicable blockers (`missing_required_files`, `missing_required_tags`, `defective_formal_notice`)
3. **Records need remediation**  
   - `escalation_action` / `next_action`: `open_records_remediation`  
   - `records_remediation_owner`: `Records` (or template-specified owner)

## 5. Notice Quality Checklist
Inspect the notice packet for these exact defects; only report those actually present:
- `missing_ack_deadline`
- `missing_appeal_instructions`
- `missing_waitlist_status`
- `missing_correct_policy`

If any defect exists → `notice_quality`: `defective`, `notice_remediation_action`: `reissue_defective_notices`.

## 6. Recruitment Packet Reconciliation
- **Candidate arrays** must contain candidate IDs only.
- **Cost total** = sum of every recruiting campaign ledger line item.
- **Accepted offer** → `onboarding_handoff`: `create_payroll_precheck`, `payroll_assignment_status_required`: `submitted_after_acceptance`, `draft_payroll_allowed`: `false`, `handoff_control_result`: `submitted_handoff_required_after_acceptance`.
- **Waitlisted** → `waitlisted_followup_action`: `send_waitlist_notice` (never reissue as rejection).
- **Rejected** → `rejected_followup_action`: `send_rejection_notice`.
- `offer_exclusion_reason_for_waitlisted`: `no_accepted_status_or_offer` when applicable.

## 7. Payroll & Accrual Readiness
- Select the `submitted` payroll assignment; exclude any draft assignment.
- `draft_exclusion_rule`: `exclude_draft_assignment`.
- `payroll_source_status`: `submitted`.
- `audit_scope`: `payroll_assignment_readiness`.
- If submitted assignment exists and accrual batch is linked → `accrual_ready`: `true`, `control_result`: `ready_with_monitoring`.

## 8. Audit Scope Mapping
| Review Type | `audit_scope` value |
|-------------|---------------------|
| Leave precedence / stale profile | `leave_source_precedence_only` |
| Folder, documents, formal notice | `document_notice_findings_only` |
| Payroll / accrual readiness | `payroll_assignment_readiness` |

## 9. Enum Compliance
- Every enum field must use the **exact** normalized business label from the answer template.
- Do not paraphrase, do not invent values, and do not add free-text explanations inside enum fields.
- When a field is boolean, use JSON `true`/`false`; when a field is a list of strings, ensure it contains only the required IDs.
