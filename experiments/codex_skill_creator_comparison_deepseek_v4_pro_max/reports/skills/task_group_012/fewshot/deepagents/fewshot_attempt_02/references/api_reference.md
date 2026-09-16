# PeopleOps Console API Reference

Base URL is provided at runtime as `<TASK_ENV_BASE_URL>`. All requests use HTTP
GET unless noted.

Login credentials (when required by the application UI):
- Email: `ops.lead@peopleops.local`
- Password: `PeopleOps#2026`

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Application entrypoint / index |
| GET | `/api/manifest` | API manifest listing available endpoints and structures |
| GET | `/api/summary` | System-wide summary dashboard |
| GET | `/api/employees` | Full employee directory |
| GET | `/api/cases` | All cases list |
| GET | `/api/cases/{case_id}` | Single case detail with full record |
| GET | `/api/policies` | All policy documents list |
| GET | `/api/policies/{policy_id}` | Single policy document detail |
| GET | `/api/payroll-ledgers` | Payroll ledger and assignment records |
| GET | `/api/recruitment` | Recruitment openings, candidates, offers |
| GET | `/api/documents` | Document/folder index |
| GET | `/api/messages` | Message/communication records |
| GET | `/api/notifications` | Notice packets and notifications |
| GET | `/api/audit` | Audit event index |
| GET | `/api/audit/{audit_id}` | Single audit event detail with findings |
| GET | `/api/attachments/{attachment_id}` | Download a specific attachment/file |
| POST | `/api/cases/{case_id}/comments` | Add a comment to a case |

## Endpoint Use by Task Type

**Onboarding closeout (employee leave + payroll):**
- `/api/employees` to locate the employee by ID
- `/api/policies` and `/api/policies/{policy_id}` to read leave policy text
- `/api/payroll-ledgers` for assignment records, salary, effective dates,
  accrual batches
- `/api/audit` and `/api/audit/{audit_id}` for audit evidence

**Case review (folder readiness + notice quality):**
- `/api/cases/{case_id}` for case detail, approval history, tags
- `/api/documents` for folder contents and required files
- `/api/notifications` for formal notice packets and quality inspection
- `/api/audit` and `/api/audit/{audit_id}` for document/notice findings

**Recruitment reconciliation:**
- `/api/recruitment` for openings, candidates, interview feedback, offers
- `/api/payroll-ledgers` for payroll handoff readiness
- `/api/notifications` for notice packets sent to candidates
- `/api/cases/{case_id}` for related case detail

**Leave source precedence:**
- `/api/employees` for employee profile summary policy
- `/api/payroll-ledgers` for leave assignment history and current balances
- `/api/policies/{policy_id}` for policy document text
- `/api/audit` and `/api/audit/{audit_id}` for leave-scope audit evidence

**Payroll assignment readiness:**
- `/api/payroll-ledgers` for assignment records, salary, accrual batches
- `/api/audit` and `/api/audit/{audit_id}` for payroll-scope audit evidence

## Reading Records

Every endpoint returns JSON. Navigate from the list endpoints (e.g.
`/api/employees`) to identify the target record, then fetch the detail endpoint
for complete information.

When inspecting a case, document, or audit record, examine all nested fields:
- **Case records** carry `approval_history`, `tags`, `folder_status`,
  `notice_status`, and `related_entities`.
- **Payroll/ledger records** carry `status` (submitted, draft, superseded),
  `effective_date`, `salary`, `accrual_batch`, and `assignment_id`.
- **Audit records** carry `scope`, `findings`, `related_event_ids`, and
  `event_type`.
- **Recruitment records** carry `candidates`, `offers`, `interview_feedback`,
  `committee_decision`, and `cost_ledger`.
- **Notice/notification records** carry `notice_type`, `quality_flag`, and
  `defect_details`.

## Determining Record Status

- `submitted` — authoritative, use for decisions.
- `draft` — exclude from decisions unless the task explicitly allows drafts.
- `superseded` — the record was replaced by a newer submitted version; exclude
  it.

Always prefer the most recent submitted record when multiple exist.
