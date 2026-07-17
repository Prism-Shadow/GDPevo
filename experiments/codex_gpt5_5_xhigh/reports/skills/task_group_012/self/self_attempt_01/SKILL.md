# PeopleOps Console Reconciliation SOP

Use this skill for PeopleOps Console tasks that ask for a JSON answer from an `answer_template.json`. These tasks are evidence reconciliation exercises: identify the authoritative record, exclude stale/draft/adjacent evidence, and emit only the normalized fields required by the template.

## Environment Habit

1. Read the prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: exact keys, exact enum spellings, booleans as booleans, numbers as numbers, and arrays as arrays of IDs unless the template says otherwise.
2. Read `environment_access.md` and replace any prompt URL like `http://127.0.0.1:<port>/` with the provided remote base URL. Use the credentials from that file if opening the UI.
3. The app is usually faster through its read APIs. Useful endpoints:
   - `/api/employees?q=<id-or-name>` for profile summaries.
   - `/api/cases?q=<id-or-name>` and `/api/cases/<case_id>` for case overview, approvals, attachments, comments, and case-scoped audit entries.
   - `/api/payroll-ledgers?q=<employee-id-or-name>` for leave assignments, leave ledgers, salary assignments, statuses, salary, effective period, and accrual batch IDs.
   - `/api/recruitment?q=<opening-id>` for candidates, committee decisions, offers, cost ledger, notice packets, and payroll precheck records.
   - `/api/documents?q=<case-or-folder-id>` for required files, filed files, required tags, current tags, and readiness.
   - `/api/messages?q=<case-or-message-id>` for formal notice body, status, quality, and defects.
   - `/api/audit?q=<case-employee-or-opening-id>` and `/api/audit/<audit_id>` for scope-specific audit details.
   - `/api/policies/<policy_id>` for the source-precedence rule when a case references policy IDs.

## Source Precedence

- Case summaries are navigation hints, not final authority. Confirm with the specific module records and policy/audit evidence.
- Leave: for an effective-year leave setup, the current `Approved` or `Submitted` leave assignment for the relevant period controls. Use `approved_leave_days` from the controlling assignment, not worksheet or stale profile numbers. Exclude `Draft`, `Superseded`, obsolete, and adjacent non-assignment ledger rows. If the employee profile conflicts but the assignment, policy, and leave audit agree, mark the profile as ignored/stale.
- Payroll: use the current `Submitted` salary assignment. Draft planning assignments do not affect salary, effective date, accrual readiness, or handoff readiness. When an accrual batch is requested, require an audit or ledger record tying the submitted assignment to that batch.
- Documents/folders: a folder is ready only when every required file and every required tag in the checklist is present. Missing either files or tags blocks readiness.
- Formal notices: inspect notice packets/messages and audit detail. A notice is defective when required content is missing, even if the case has an approval. Use the template defect enum exactly, such as `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, or `missing_correct_policy`.
- Recruitment: use candidate review/committee decision plus offer register. The selected candidate needs the selected decision and accepted offer; waitlisted/rejected lists contain candidate IDs only. Sum every recruiting cost ledger line for `recruitment_cost_total`. Notice follow-up comes from notice packet status/required action. Payroll handoff is gated by accepted offer and must become a submitted handoff/assignment; drafts do not satisfy the gate.
- Approval/closeout: approval alone is sufficient only when records, folder, and notice evidence are clean. Folder or notice defects should block closeout or trigger records/notice remediation according to the template.

## Audit Scope Rules

- Include only audit events that support the requested decision scope.
- Use `leave_source_precedence_only` for leave assignment/profile conflicts.
- Use `payroll_assignment_readiness` for salary assignment and accrual readiness.
- Use `document_notice_findings_only` for folder readiness and formal notice quality.
- If the case has adjacent audits from another scope, list them in `excluded_audit_event_ids` when the template asks for exclusions. Do not let a document/notice audit decide leave precedence, or a leave audit decide folder readiness.

## Normalized Output Conventions

- Always copy enum labels from the template, never invent prose labels.
- Common leave labels:
  - `leave_assignment_history` when an assignment/ledger record controls over a profile.
  - `approved_assignment_current_period` for the effective approved/submitted leave assignment.
  - `approved_assignment_over_profile` when a stale employee profile is ignored.
- Common payroll labels:
  - `submitted` for the selected payroll source status.
  - `exclude_draft_assignment` when a draft salary assignment appears but must be ignored.
  - `ready_with_monitoring` when audit and batch evidence say payroll/accrual can proceed.
- Common document/notice labels:
  - `approval_not_sufficient_when_folder_or_notice_defective` when approval exists but required folder or notice evidence is bad.
  - `hold_for_folder_and_notice_defects` or `block_close_and_reissue_notice` when defects remain.
  - `approval_history_folder_notice_audit` when approval, folder checklist, notice/message, and audit are all used.
- Common recruitment labels:
  - `interview_feedback_and_offer` and `committee_decision_with_offer_confirmation` when candidate decision and accepted offer are both used.
  - `notice_packet_inspection` when notice follow-up is based on notice packets/messages.
  - `accepted_offer_only` for payroll gates that apply only to the selected accepted candidate.
  - `submitted_after_acceptance` when the required payroll handoff must be submitted after an accepted offer.

## Pitfalls

- Do not answer from the employee profile alone when assignment history exists.
- Do not select newer draft records over older submitted/approved authoritative records.
- Do not use worksheet days when the task asks for approved/effective leave days.
- Do not count waitlisted or rejected candidates for payroll handoff.
- Do not omit missing tags just because all files are present, or omit missing files just because the tag is present.
- Do not return explanations, markdown, or extra fields when the prompt asks for JSON only.
