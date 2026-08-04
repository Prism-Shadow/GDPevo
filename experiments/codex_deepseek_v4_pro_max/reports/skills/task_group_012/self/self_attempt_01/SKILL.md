 # PeopleOps Compliance Verification

 A reusable skill for performing PeopleOps HR compliance verification tasks against a REST API backend. Covers onboarding closeout, case folder/notice review, recruitment reconciliation, leave-source precedence, and payroll assignment readiness.

 ## Operating Principles

 ### Record Authority
 - Prefer **submitted** or **approved** records over drafts in all contexts.
 - **Assignment history** overrides **employee profile summary** overrides **case summary**.
 - An approved leave assignment overrides a stale employee profile summary when the ledger, policy document, and audit detail confirm the approved assignment.
 - Ignore profile-summary policy values when they conflict with an authoritative approved assignment.
 - Never use draft or superseded records as the basis for a final decision.

 ### Evidence Gathering Protocol
 1. Start with `GET /api/manifest` and `GET /api/summary` to survey available data.
 2. For employee-scoped tasks, pull `GET /api/employees`, then drill into `GET /api/payroll-ledgers`, `GET /api/policies`, and `GET /api/audit` as needed.
 3. For case-scoped tasks, pull `GET /api/cases/{case_id}`, then cross-reference `GET /api/documents`, `GET /api/messages`, `GET /api/notifications`, and `GET /api/audit`.
 4. For recruitment tasks, pull `GET /api/recruitment`, then cross-reference `GET /api/cases`, `GET /api/payroll-ledgers`, `GET /api/policies`, `GET /api/documents`, and `GET /api/audit`.
 5. Always verify findings across at least two independent endpoints before concluding.

 ### Exclusion Rules
 - Exclude any record with status **draft** from final decisions (payroll assignments, leave assignments, offers).
 - Exclude **superseded** records when a newer submitted/approved record exists.
 - Exclude **stale** employee profile summary values when an approved assignment provides a more recent authoritative state.
 - Exclude **adjacent** audit events whose scope does not match the verification type being performed (e.g., exclude document/notice audit events from a leave-source-precedence decision, and vice versa).

 ## Verification Workflows

 ### Onboarding Closeout
 - Verify the employee's effective leave policy and payroll setup using submitted assignment-history records only.
 - Identify which leave and payroll assignment IDs are authoritative.
 - Collect excluded (draft/superseded) assignment IDs.
 - Determine closeout action: `approve_onboarding_close` if records are clean, `block_close_and_reissue_notice` if notice is defective, `open_records_remediation` if folder/records need fixing.

 ### Case Folder and Notice Review
 - Inspect the case folder for all required files. Flag any missing files.
 - Verify the required tag is present on the case.
 - Assess formal notice quality for defects: missing acknowledgment deadline, missing appeal instructions, missing waitlist status, missing correct policy reference.
 - The approval gate is `approval_sufficient_when_records_clean` when folder and notice are defect-free; otherwise `approval_not_sufficient_when_folder_or_notice_defective`.
 - Evidence source order: `approval_history_folder_notice_audit` > `folder_notice_audit` > `audit_only`.
 - Notice evidence comes from `notice_packet_inspection` (preferred) or `message_notice_inspection`.
 - Final control is `approve_closeout` only when both folder and notice are clean; otherwise `hold_for_folder_and_notice_defects`.

 ### Recruitment Reconciliation
 - Determine candidate outcomes from interview feedback and offer records (`interview_feedback_and_offer`), not from case summary or messages alone.
 - Selected candidate must have an accepted offer. Waitlisted candidates have no accepted offer. Rejected candidates were explicitly rejected.
 - `recruitment_cost_total` is the sum of all ledger items in the recruitment cost ledger.
 - Notice follow-up is required for candidates who need waitlist or rejection notices sent/reissued.
 - Payroll handoff only proceeds for accepted offers: `create_submitted_assignment_after_acceptance`.
 - Payroll assignment status must be `submitted_after_acceptance`; draft assignments are not allowed.
 - Handoff control result is `submitted_handoff_required_after_acceptance` when an offer is accepted.

 ### Leave Source Precedence
 - Compare the employee profile summary leave policy against the leave assignment history.
 - When the profile summary is stale and an approved assignment is confirmed by ledger, policy document, and audit, the approved assignment is authoritative.
 - Precedence source: `approved_assignment_over_profile` when assignment wins; `employee_profile_summary` when no conflict exists.
 - Audit scope for this workflow is `leave_source_precedence_only`.
 - Supporting audit events must be in the leave-source scope; exclude adjacent document/notice audit events.
 - Profile policy should be ignored (`true`) when overridden by an approved assignment.
 - Next action: `update_employee_summary` when profile is stale; `no_action` when aligned.

 ### Payroll Assignment and Accrual Readiness
 - Use the submitted payroll assignment; exclude draft assignments.
 - Verify accrual batch readiness for the target period.
 - Draft exclusion rule: `exclude_draft_assignment`.
 - Payroll source status must be `submitted`.
 - Audit scope is `payroll_assignment_readiness`.
 - Control result is `ready_with_monitoring` when the submitted assignment and accrual batch are valid; `hold_for_folder_and_notice_defects` when issues exist.

 ## Output Format
 - Always return a single JSON object matching the provided answer template schema.
 - Use only the `allowed_values` enum labels from the template for every constrained field; never substitute free-text explanations.
 - Do not include markdown fences, explanatory text, or extra keys outside the template.
 - Arrays (e.g., candidate IDs, excluded IDs, missing files) must contain only the relevant identifiers as strings.

 ## Posting Comments
 - When a comment must be added to a case, use `POST /api/cases/{case_id}/comments` with a JSON body containing `author`, `created_at`, `visibility`, and `body` fields.

 ## Cross-Task Constants
 - Login credentials: `ops.lead@peopleops.local` / `PeopleOps#2026`.
 - The base URL is provided at task time as `<TASK_ENV_BASE_URL>`.
