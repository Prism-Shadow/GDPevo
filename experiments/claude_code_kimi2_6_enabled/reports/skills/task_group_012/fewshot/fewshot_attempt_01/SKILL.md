# PeopleOps Console — HR Operations & Compliance Verification

## Environment
- Base URL: `<TASK_ENV_BASE_URL>` (resolves to `http://34.46.77.124:8012`)
- Credentials: `ops.lead@peopleops.local` / `PeopleOps#2026`
- **Never** use localhost/127.0.0.1 unless the remote URL itself points there.

## General Workflow
1. Open the solver URL and log in with the provided credentials.
2. Navigate to the relevant workspace/module (Recruitment, Cases, Employee Profile, Leave Ledger, Payroll, Audit Events, etc.).
3. Gather evidence from authoritative sources, applying the precedence rules below.
4. Fill the JSON answer using **only** the normalized enum labels from `answer_template.json`.
5. Return **only** JSON — no markdown or explanatory text.

---

## Source Precedence Rules
| Situation | Authoritative Source | Excluded Source |
|-----------|---------------------|-----------------|
| Leave policy/balance | Approved leave assignment (current period) | Stale employee profile summary; draft assignments |
| Payroll assignment | Submitted assignment | Draft assignments; superseded assignments |
| Candidate outcome | Interview feedback + offer register | Message-only status; case summary-only |
| Recruitment cost | Recruitment cost ledger | Case summary-only |
| Notice quality | Notice packet inspection | Message notice inspection; case summary-only |

- **Always exclude draft records** from authoritative decisions.
- When an approved assignment exists and is confirmed by ledger/policy/audit, the employee profile summary is **stale** and should be ignored (`profile_policy_ignored: true`).

---

## Audit Event Handling
- Include the **primary audit event** that supports the decision in `audit_event_id` and `supporting_audit_event_ids`.
- **Exclude** adjacent audit events that belong to a different scope:
  - Document/notice audit events (e.g., `AUD-DOCxxx`) are **excluded** from leave-source-precedence decisions.
  - Set `audit_scope` to the narrowest applicable value:
    - `leave_source_precedence_only`
    - `document_notice_findings_only`
    - `payroll_assignment_readiness`

---

## Closeout & Control Gates
| Condition | Gate | Final Result |
|-----------|------|--------------|
| Submitted payroll + valid notice + complete folder | `approval_sufficient_when_records_clean` | `approve_closeout` |
| Missing required files OR defective notice OR missing tag | `approval_not_sufficient_when_folder_or_notice_defective` | `hold_for_folder_and_notice_defects` |
| Payroll ready, draft excluded, monitoring OK | — | `ready_with_monitoring` |

- `closeout_blockers` can include: `missing_required_files`, `missing_required_tags`, `defective_formal_notice`.
- If notice is defective, set `notice_remediation_action: "reissue_defective_notices"` and `next_action: "block_close_and_reissue_notice"`.
- If records need cleanup, set `escalation_action: "open_records_remediation"` and `records_remediation_owner: "Records"`.

---

## Notice Quality Inspection
- Inspect the **notice packet** (not messages or case summaries) for defects.
- Defect enum values: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`.
- If any defect exists → `notice_quality: "defective"`; otherwise `"valid"`.

---

## Recruitment Reconciliation
- **Selected candidate**: the one with an accepted offer (`selected_offer_status: "accepted"`).
- **Waitlisted candidates**: need `waitlisted_followup_action: "send_waitlist_notice"`.
- **Rejected candidates**: need `rejected_followup_action: "send_rejection_notice"`.
- **Recruitment cost total**: sum of **all** recruiting campaign ledger line items.
- **Payroll handoff**: only for accepted offers (`onboarding_handoff: "create_payroll_precheck"`).
- Draft payroll is **not** allowed for handoff (`draft_payroll_allowed: false`).
- `payroll_assignment_status_required`: `"submitted_after_acceptance"`.

---

## Payroll & Accrual Readiness
- Select the **submitted** payroll assignment; exclude the **draft** (`draft_exclusion_rule: "exclude_draft_assignment"`).
- Verify the accrual batch is ready (`accrual_ready: true/false`).
- `payroll_source_status`: `"submitted"` for the authoritative assignment.

---

## Enum Field Discipline
- **Never** invent free-text values for fields defined as enums in the answer template.
- Always copy the exact allowed string from the template's `allowed_values` list.
- Arrays of candidate IDs must contain **only** IDs (no objects or descriptions).
- Dates should be ISO-8601 strings (e.g., `2026-04-01`).

---

## Evidence Source Order
When multiple sources are reviewed, set `evidence_source_order` to the template enum that matches the hierarchy used:
- `approval_history_folder_notice_audit` (most comprehensive)
- `folder_notice_audit`
- `audit_only`
