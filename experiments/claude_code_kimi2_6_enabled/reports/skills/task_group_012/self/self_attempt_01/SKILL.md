# PeopleOps Lifecycle Verification Skill

## Overview
Verify employee lifecycle records (onboarding, leave, payroll, recruitment, policy cases) in the Northwind People Lifecycle Portal by querying its REST API and applying source-precedence rules. Return structured JSON answers using normalized business labels from the task's answer template.

## Environment
- Base URL: `<TASK_ENV_BASE_URL>` (staged remote URL; never localhost)
- Login via web UI if needed: `ops.lead@peopleops.local` / `PeopleOps#2026`
- All data is accessible through read-only REST endpoints; no write actions are required for verification tasks.

## Core API Endpoints
Query these endpoints with `?q=<search>` filters:
- `/api/employees?q=<id_or_name>` — profile, status, leave balance
- `/api/cases/<case_id>` — full case detail (approvals, attachments, audit events, comments)
- `/api/cases?q=<query>` — case list
- `/api/payroll-ledgers?q=<employee_id>` — leave assignments, salary assignments, adjustments
- `/api/recruitment?q=<opening_id>` — candidates, offers, cost ledger, notice packets, payroll prechecks
- `/api/documents?q=<case_or_doc_id>` — folder checklists (required vs filed files/tags)
- `/api/messages?q=<case_id>` — formal notices (quality, defects)
- `/api/audit?q=<case_or_employee_id>` — audit events
- `/api/policies` — policy documents (source-precedence rules)

## Source-Precedence Rules (from policies)
Apply these consistently:
1. **Leave**: The latest **Approved** or **Submitted** leave assignment for the period controls. **Draft**, voided, and obsolete records are excluded even when employee profile summaries conflict.
2. **Payroll**: The current **Submitted** salary assignment controls base salary. **Draft** planning assignments do not affect payroll readiness or accrual checks.
3. **Recruitment payroll handoff**: Created only after a selected candidate has an **accepted** offer. The handoff must be **submitted**; draft prechecks do not satisfy the assignment gate.
4. **Documents**: A folder is **not ready** unless all `required_files` are present in `files` and all `required_tags` are present in `tags`.

## Task-Type Playbooks

### A. Onboarding / Lifecycle Closeout (single employee)
1. Get `/api/employees?q=<employee_id>` for profile and status.
2. Get `/api/payroll-ledgers?q=<employee_id>` for all assignments.
3. Identify the **authoritative** records:
   - Leave: select `status="Approved"` (or latest `Submitted`) assignment for the effective period.
   - Exclude: `Draft`, `Superseded`, or older assignments.
   - Payroll: select `status="Submitted"` salary assignment.
   - Exclude: `Draft` salary assignments.
4. Determine `closeout_action` and `final_control_result`:
   - If records are clean (no missing folder files, no defective notices, no draft interfering), use `approve_onboarding_close` / `approve_closeout`.
   - If the formal notice is defective or folder is incomplete, use `block_close_and_reissue_notice` / `hold_for_folder_and_notice_defects`.
   - If data needs remediation, use `open_records_remediation`.
5. Map enum values from the answer template exactly.

### B. Policy Case Review (remote work, lifecycle hold)
1. Get `/api/cases/<case_id>` for approvals, attachments, audit events.
2. Get `/api/documents?q=<case_id>` for folder checklist.
3. Get `/api/messages?q=<case_id>` for formal notice inspection.
4. Get `/api/audit?q=<case_id>` for supporting audit events.
5. Evaluate:
   - **Final decision**: `approved_with_conditions` if approval note says so; otherwise match approval `decision`.
   - **Folder ready**: true only when `required_files` ⊆ `files` AND `required_tags` ⊆ `tags`.
   - **Missing files**: compute `required_files - files`.
   - **Required tag present**: compute `required_tags` intersection with `tags`.
   - **Notice quality**: `valid` if message `defects` is empty; else `defective`.
   - **Notice defects**: map from message `defects` array directly.
   - **Audit scope**: `document_notice_findings_only` for folder/notice cases; `leave_source_precedence_only` for leave cases; `payroll_assignment_readiness` for payroll cases.
   - **Excluded audit events**: adjacent events from a different scope (e.g., a folder/notice audit event is excluded when deciding leave-source precedence, and vice versa).
6. Set `approval_closeout_gate`:
   - `approval_not_sufficient_when_folder_or_notice_defective` if any blocker exists.
   - `approval_sufficient_when_records_clean` otherwise.

### C. Recruitment Reconciliation
1. Get `/api/recruitment?q=<opening_id>`.
2. Classify candidates by `committee_decision` into `selected_candidate`, `waitlisted_candidates`, `rejected_candidates`.
3. Check `offer_register` for offer status of selected candidate.
4. Sum all `cost_ledger` amounts for `recruitment_cost_total`.
5. Check `notice_packets` for required follow-up:
   - Waitlisted candidates without sent notices → `send_waitlist_notice`.
   - Rejected candidates without sent notices → `send_rejection_notice`.
6. Determine `onboarding_handoff`:
   - If selected candidate has `accepted` offer, use `create_submitted_assignment_after_acceptance`.
   - If no accepted offer, use `no_payroll_handoff`.
7. Set enums from the answer template (e.g., `candidate_outcome_control`, `cost_source`, `notice_quality_source`).

### D. Leave Source Precedence
1. Get employee profile (`/api/employees`) and payroll ledgers (`/api/payroll-ledgers`).
2. Compare profile `leave_balance_days`/`policy` against the latest Approved/Submitted assignment.
3. If they conflict, the approved assignment wins per `LEAVE-SRC-001`.
4. Identify the controlling audit event (e.g., `leave.profile_mismatch`) and supporting/excluded events by scope.
5. Set `precedence_source` to `approved_assignment_over_profile` when the assignment overrides the profile.
6. Set `profile_policy_ignored` to `true` when the profile is stale.

### E. Payroll Assignment Readiness
1. Get `/api/payroll-ledgers?q=<employee_id>`.
2. Select the `Submitted` salary assignment as authoritative.
3. Identify the `Draft` assignment to exclude.
4. Verify accrual readiness via the case audit event or ledger `accrual_batch_id`.
5. Map to enums: `payroll_source_status: submitted`, `draft_exclusion_rule: exclude_draft_assignment`, `audit_scope: payroll_assignment_readiness`.

## Normalized Business Labels (Critical)
Always use the exact enum values from the answer template. Common labels include:
- `leave_source`: `leave_assignment_history`, `employee_profile_summary`, `case_summary_only`
- `leave_precedence_source` / `precedence_source`: `approved_assignment_current_period`, `profile_summary_current_period`, `case_summary_only`, `approved_assignment_over_profile`
- `payroll_source_status` / `payroll_status`: `submitted`, `draft`, `superseded`
- `closeout_action` / `next_action`: `approve_onboarding_close`, `block_close_and_reissue_notice`, `open_records_remediation`, `update_employee_summary`, `no_action`
- `final_control_result` / `control_result`: `approve_closeout`, `hold_for_folder_and_notice_defects`, `ready_with_monitoring`
- `approval_closeout_gate`: `approval_sufficient_when_records_clean`, `approval_not_sufficient_when_folder_or_notice_defective`
- `audit_scope`: `document_notice_findings_only`, `leave_source_precedence_only`, `payroll_assignment_readiness`
- `notice_quality`: `valid`, `defective`
- `notice_defects`: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`
- `final_decision`: `approved_with_conditions`, `approved`, `rejected`, `held`
- `candidate_outcome_control`: `committee_decision_with_offer_confirmation`, `message_status_only`, `case_summary_only`
- `handoff_control_result`: `submitted_handoff_required_after_acceptance`, `submitted_handoff_required`, `no_handoff_required`
- `draft_exclusion_rule`: `exclude_draft_assignment`, `draft_allowed`, `exclude_superseded_only`

## Output Rules
- Return **only** a single JSON object matching the task's `input/payloads/answer_template.json`.
- Do **not** wrap in markdown code fences or add explanatory text.
- For array fields, include only the requested identifiers (candidate IDs, audit IDs, file names, etc.).
- For numeric sums (e.g., `recruitment_cost_total`), sum all items from the authoritative ledger.
- For boolean fields, use JSON `true`/`false`.

## Common Pitfalls
1. **Using profile summary instead of assignment history** — The employee profile may be stale; always check payroll ledgers and apply policy source precedence.
2. **Including draft records** — Draft assignments, draft notices, and draft payroll records must be excluded unless the template explicitly allows them.
3. **Missing cross-module audit events** — A case may have audit events from multiple scopes; include only those matching the current decision scope and explicitly exclude adjacent ones.
4. **Folder readiness logic** — A folder is ready only when **both** required files and required tags are fully satisfied.
5. **Notice quality from the wrong source** — Inspect the message/notice packet (`/api/messages` or `notice_packets`), not the case summary, for defects.
6. **Recruitment cost total** — Sum **all** lines in the recruitment `cost_ledger`, not just a subset.
7. **Enum exactness** — Copy enum values character-for-character from the answer template; even slight differences will fail validation.
