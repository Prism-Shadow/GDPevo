# Skill: Inspect Payroll Assignment and Accrual Readiness

## Environment
- Base URL resolves to `http://34.46.77.124:8012` (use `<TASK_ENV_BASE_URL>` as referenced in prompts).
- The portal exposes JSON REST APIs under `/api/`. In practice, direct `GET` calls to the endpoints below return data without extra session handling; if a frontend login screen is encountered, use the credentials supplied in the task prompt.

## Relevant APIs
| Endpoint | Purpose |
|---|---|
| `GET /api/payroll-ledgers?q=<employee_id>` | Salary assignments, periods, `accrual_batch_id`, and status. |
| `GET /api/audit?q=<employee_id>` | Global audit events (payroll QA results, draft-exclusion notes, etc.). |
| `GET /api/cases?q=<employee_id>` | Case summaries and embedded `audit_events` (fallback when no global payroll audit exists). |
| `GET /api/policies/PAY-SRC-001` | Reference policy: submitted assignments control; drafts are ignored. |

## Procedure
1. **Read the task prompt** to extract the target `employee_id` and the target accrual batch month (e.g., “April 2026”).
2. **Read `input/payloads/answer_template.json`** to confirm exact field names and enum values.
3. **Fetch payroll-ledgers** (`/api/payroll-ledgers?q=<employee_id>`) and filter to records where `record_type` contains `"Salary assignment"`.
4. **Select the controlling assignment** — the record with `status: "Submitted"`.
   - `salary_assignment_id` → `ledger_id`
   - `base_salary` → numeric `base_salary` (do not format as currency)
   - `effective_date` → use an explicit `effective_date` field if present; otherwise derive it from `period` by appending `-01` (e.g., `2026-04` → `2026-04-01`)
   - `payroll_source_status` → `"submitted"`
5. **Identify the excluded draft** — the salary assignment with `status: "Draft"`.
   - `excluded_assignment_id` → its `ledger_id` (or `""` if none exists)
   - `draft_exclusion_rule` → `"exclude_draft_assignment"`
6. **Determine accrual readiness** for the target month:
   - If the submitted assignment has a non-empty `accrual_batch_id` and its `period` matches the target month, set `accrual_ready: true` and `accrual_batch_id` to that batch ID.
   - Otherwise, set `accrual_ready: false` and `accrual_batch_id: ""`.
7. **Find the payroll audit event**:
   - Query `/api/audit?q=<employee_id>` and prefer the event whose `event` starts with `payroll.` and whose `detail` mentions the selected `ledger_id` or `accrual_batch_id`.
   - If absent, inspect the employee’s case(s) (`/api/cases?q=<employee_id>` → each case’s `audit_events`) for a payroll-related entry.
   - `audit_event_id` → the chosen `audit_id` (or `""` if none found).
8. **Map `control_result`** from audit evidence to the exact enum in the answer template:
   - Detail contains `"QA result: ready_with_monitoring"` → `"ready_with_monitoring"`
   - Detail contains `"QA result: block close"` or explicit folder/notice defects (missing files, missing tags, missing appeal instructions, etc.) → `"hold_for_folder_and_notice_defects"`
   - Detail contains `"QA result: approve_closeout"` → `"approve_closeout"`
   - If no payroll audit exists but the submitted assignment carries a matching accrual batch, default to `"ready_with_monitoring"`.
   - If no payroll audit and no matching batch, default to `"hold_for_folder_and_notice_defects"` unless the case is approved with no blocking evidence.
9. **Set `audit_scope`** → `"payroll_assignment_readiness"`.
10. **Write the final answer** as a single JSON object matching the answer template exactly, using the normalized enum strings (never free-text paraphrases).

## Pitfalls
- Never use a draft or superseded salary assignment as the controlling source.
- `accrual_ready` must be a JSON boolean (`true`/`false`), not a string.
- `base_salary` must remain a number.
- Enum fields (`control_result`, `payroll_source_status`, `draft_exclusion_rule`, `audit_scope`) must match the answer template allowed values verbatim.
- If multiple submitted salary assignments exist, prefer the one whose `period` aligns with the target accrual batch month.
- If multiple drafts exist, exclude the most recent one (latest `updated_at`).
