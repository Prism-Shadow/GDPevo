# PeopleOps Console JSON API — Reference

The environment is a local HR-lifecycle portal. Reach it ONLY over HTTP at the
base URL given in the task's `environment_access.md` (it specifies the host/port,
e.g. `http://127.0.0.1:<port>/`). The JSON API needs no auth; the login in the
prompt is for the web UI only. Always confirm reachability first with `GET /health`.

Use `curl -s "<base>/api/..."`. The `q` parameter is a case-insensitive substring
match against any scalar field on that resource, so `?q=<ENTITY-ID>` is the fast
way to pull everything tied to a specific employee, case, or opening.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness check; expect `{"ok": true, ...}`. |
| `GET /api/manifest` | Modules + per-dataset row counts. |
| `GET /api/summary` | Entity counts, cases-by-status, departments + leaders. |
| `GET /api/employees?q=&status=` | Employee profile summaries. |
| `GET /api/cases?q=&status=&type=` | Case summaries. |
| `GET /api/cases/<case_id>` | Full case detail: comments, attachments, approvals, audit_events, policy_refs. |
| `GET /api/policies?q=` / `GET /api/policies/<policy_id>` | Policy documents (sections + body text). |
| `GET /api/payroll-ledgers?q=&status=&type=` | Leave assignments AND salary assignments AND leave ledgers (one collection). |
| `GET /api/recruitment?q=` | Opening packets: candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records. |
| `GET /api/documents?q=` | Document folders: files, required_files, tags, required_tags, ready. |
| `GET /api/messages?q=` | Lifecycle messages / formal notices (with quality + defects). |
| `GET /api/notifications?q=` | Notification records. |
| `GET /api/audit?q=&case_id=` / `GET /api/audit/<audit_id>` | Audit events. |
| `GET /api/attachments/<attachment_id>` | Raw attachment text. |

## Anti-leakage / scope discipline

These tasks are graded for fairness, so confine queries to the entities the prompt
names and the records directly linked to them. Look entities up by their specific
IDs (`?q=<ID>` or the `/<id>` detail route, or `/api/audit?case_id=<CASE-ID>`).
Do NOT enumerate full collections with no filter to discover unrelated entities.

## Field shapes you will rely on (generic)

**Employee** (`/api/employees`): `employee_id`, `name`, `department`, `status`
(`Onboarding` / `Active` / ...), `leave_balance_days`, `salary_band`. The profile's
`leave_balance_days` and any profile policy are a *summary* that can be stale.

**payroll-ledgers row**: every row has `ledger_id`, `employee_id`, `record_type`,
`status`, `period`, `updated_at`. The collection mixes record types:
- `record_type: "Leave assignment"` → has `policy_name`, `approved_leave_days`,
  `worksheet_leave_days`. This is the authoritative leave source.
- `record_type: "Salary assignment"` → has `base_salary`, `period` (the effective
  month/date), sometimes `accrual_batch_id`.
- Other leave-ledger types (`HRMS leave ledger`, `People Ops adjustment`) are
  worksheet/adjustment rows, NOT the controlling leave assignment.
- `status` values include `Approved`, `Submitted`, `Draft`, `Superseded`.

**Case detail** (`/api/cases/<id>`): `approvals[]` (each `approval_id`, `approver`,
`decision`, `step`, `note`), `attachments[]` (`attachment_id`, `kind`, `name`,
`status`, `content`), `audit_events[]` (embedded copies of the audit rows),
`comments[]`, `policy_refs[]`, `owner`, `summary`, `status`.

**Document folder** (`/api/documents`): `files[]`, `required_files[]`, `tags[]`,
`required_tags[]`, `ready` (boolean). Readiness = required_files ⊆ files AND
required_tags ⊆ tags.

**Message / notice** (`/api/messages`): `message_id`, `case_id`, `subject`, `body`,
`recipient`, `status` (`Draft` / sent), `quality` (`valid` / `defective`),
`defects[]` (list of normalized defect codes). This is the notice-packet inspection
source.

**Recruitment packet** (`/api/recruitment`): `opening_id`, `title`, `status`,
`candidates[]` (`candidate_id`, `committee_decision` = `Selected`/`Waitlisted`/
`Rejected`, `notice_status`, `pipeline_stage`, `rounds`), `offer_register[]`
(`offer_id`, `candidate_id`, `base_salary`, `status` = `accepted`/`draft`/
`withdrawn`), `cost_ledger[]` (`line_id`, `label`, `amount`), `notice_packets[]`
(`candidate_id`, `notice_type`, `required_action`, `status`),
`payroll_precheck_records[]`.

**Audit event** (`/api/audit`): `audit_id`, `case_id`, `employee_id`, `event`
(e.g. `leave.profile_mismatch`, `payroll.ready`, `notice.defect`,
`folder.tag_missing`), `actor`, `source`, `detail` (free text — often states the
controlling record and the QA result verbatim, e.g. "QA result: <result>.
<which record> controls/matches ..."). The `detail` string is authoritative for
the result label and which record won — read it, don't guess.
