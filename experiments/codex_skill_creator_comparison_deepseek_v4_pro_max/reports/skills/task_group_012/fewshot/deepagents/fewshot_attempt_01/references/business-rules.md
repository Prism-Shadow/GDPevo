## Record Status Precedence

The system has four record statuses. Only two are authoritative for current-state
decisions:

| Status | Authoritative? | Rule |
|--------|---------------|------|
| Approved | Yes | Controls when present for the current period. |
| Submitted | Yes | Controls when no Approved record exists for the current period. |
| Superseded | No | Replaced by a later record. Exclude from current-state decisions. |
| Draft | No | Planning/placeholder only. Always exclude from current-state decisions. |

When multiple records exist for the same employee and period, select the one with
the highest-priority authoritative status. If both Approved and Submitted exist,
Approved wins.

## Leave Assignment Rules

Source policy: `LEAVE-SRC-001` (fetch from `/api/policies`).

1. Query `/api/payroll-ledgers`, filter to `record_type: "Leave assignment"` for the target employee.
2. Exclude entries with status `Draft` or `Superseded`.
3. Among remaining entries, select the one with the latest `updated_at` timestamp for the current period.
4. The `policy_name` from that ledger entry is the **effective leave policy**.
5. The `approved_leave_days` from that entry is the **annual days / balance days**.
6. The `ledger_id` from that entry is the **assignment_id**.

The employee profile summary (`/api/employees` → `leave_balance_days`) is only
authoritative when no approved/submitted leave assignment exists. When an
assignment exists and is confirmed by audit, the profile summary is stale and
must be ignored.

## Payroll Assignment Rules

Source policy: `PAY-SRC-001` (fetch from `/api/policies`).

1. Query `/api/payroll-ledgers`, filter to `record_type: "Salary assignment"` for the target employee.
2. Exclude entries with status `Draft`.
3. Select the entry with status `Submitted` (or `Approved`) for the current period.
4. The `ledger_id` is the **payroll_assignment_id / salary_assignment_id**.
5. The `base_salary` from that entry is the authoritative salary.
6. The `effective_date` is the `period` field converted to an ISO date (e.g., `2026-04` → `2026-04-01`).

Draft salary assignments must always be excluded from payroll readiness checks.

## Folder Readiness Rules

Source policy: `POL-DOCS-2026` (fetch from `/api/policies`).

1. Identify the document folder referenced in the case (check case attachments for folder references, or `/api/documents` for documents matching the employee/case).
2. Compare `files` against `required_files`. Any file in `required_files` not in `files` is a missing file.
3. Compare `tags` against `required_tags`. Any tag in `required_tags` not in `tags` is a missing tag.
4. A folder is **ready** only when all required files and all required tags are present.

## Formal Notice Quality Rules

1. Check `/api/messages` (or `/api/notifications`) for messages linked to the target case (`case_id`).
2. A notice is **valid** when `quality` is not `"defective"` and `defects` is empty.
3. A notice is **defective** when `quality` is `"defective"` or `defects` is non-empty.
4. Known defect types:
   - `missing_ack_deadline` — no acknowledgement deadline in the notice
   - `missing_appeal_instructions` — no appeal instructions in the notice
   - `missing_waitlist_status` — waitlist status omitted
   - `missing_correct_policy` — references wrong/legacy policy

## Audit Event Scoping

Audit events are domain-specific. When a task requires audit evidence for a
specific domain, include only events matching that domain and exclude events
from other domains.

| Audit scope | Include events with | Exclude events with |
|-------------|--------------------|--------------------|
| `leave_source_precedence_only` | `event` like `leave.*` | `event` like `folder.*`, `notice.*`, `payroll.*`, `case.*`, `cross_module.*` |
| `payroll_assignment_readiness` | `event` like `payroll.*` | `event` like `leave.*`, `folder.*`, `notice.*`, `case.*`, `cross_module.*` |
| `document_notice_findings_only` | `event` like `notice.*`, `case.*` | `event` like `leave.*`, `payroll.*` (unless also relevant to folder/notice) |

When multiple audit events exist for a case, always determine which are in-scope
and which must be excluded before building the answer. Supporting audit events
are those in-scope; excluded audit events are those out-of-scope.

For leave precedence tasks, the audit scope is `leave_source_precedence_only`.
For payroll readiness tasks, the audit scope is `payroll_assignment_readiness`.
For folder/notice review tasks, the audit scope is `document_notice_findings_only`.

## Recruitment Reconciliation Rules

1. Fetch `/api/recruitment`, find the opening by `opening_id`.
2. Candidate classification from `committee_decision`:
   - `"Selected"` → **selected_candidate** (must also have an accepted offer in `offer_register`)
   - `"Waitlisted"` → **waitlisted_candidates**
   - `"Rejected"` → **rejected_candidates**
3. The offer for the selected candidate comes from `offer_register` matched by `candidate_id`.
4. `recruitment_cost_total` is the sum of all `amount` values in `cost_ledger`.
5. Notice follow-up:
   - Waitlisted candidates get `send_waitlist_notice` if their notice is not sent or defective.
   - Rejected candidates get `send_rejection_notice` if their notice is not sent.
   - If a notice already exists but is defective, reissue rather than send new.
6. Payroll handoff: `create_payroll_precheck` when the selected candidate has an accepted offer (`offer_register[].status == "accepted"`).
7. Draft payroll precheck records do not satisfy the assignment gate.
8. Waitlisted candidates are excluded from payroll because they have no accepted offer.

## Evidence Source Selection

When the answer template asks for a source enum (e.g., `leave_source`,
`candidate_status_source`, `cost_source`, `notice_evidence_source`), choose the
value that reflects the most authoritative data path actually used:

- If the determination came from the payroll-ledgers leave/salary assignment records → choose `leave_assignment_history` or the ledger-based option.
- If it came from the employee profile summary → choose `employee_profile_summary`.
- If it came from a case summary alone → choose `case_summary_only`.
- For recruitment: `interview_feedback_and_offer` when using candidate decisions + offer register.
- For costs: `recruitment_cost_ledger` when summing the cost ledger.
- For notices: `notice_packet_inspection` when inspecting the notice_packets array, `message_notice_inspection` when inspecting messages.

## Closeout and Control Gates

The `closeout_action` / `next_action` field captures the prescribed next step:

- `approve_onboarding_close` — all records clean, no blockers.
- `block_close_and_reissue_notice` — folder or notice defects require reissue before close.
- `open_records_remediation` — broader record issues need remediation ownership.

The `approval_closeout_gate` field:

- `approval_sufficient_when_records_clean` — approval is sufficient, no folder/notice defects.
- `approval_not_sufficient_when_folder_or_notice_defective` — approval alone insufficient; folder or notice problems block.

The `final_control_result` / `control_result` field:

- `approve_closeout` — all checks pass.
- `hold_for_folder_and_notice_defects` — blocked by folder/notice issues.
- `ready_with_monitoring` — ready but needs monitoring (e.g., accrual batch pending).

## Using the Answer Template

Every task provides an `answer_template.json` that defines the exact schema,
field types, and allowed enum values. The template is the authoritative
reference for output shape:

- Use only values from the `allowed_values` arrays for enum fields.
- Integer fields must be integers, not floats.
- Number fields accept integers or floats.
- List fields must be JSON arrays.
- Boolean fields must be `true` or `false`.

Never invent enum values. If a value is not in `allowed_values`, re-examine the
data to find the correct match.
