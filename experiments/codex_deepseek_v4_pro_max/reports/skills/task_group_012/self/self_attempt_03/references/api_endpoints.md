
# PeopleOps API Reference

Base URL is read from `environment_access.md` at runtime.

## GET Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /` | Root / dashboard |
| `GET /api/manifest` | Environment manifest / configuration |
| `GET /api/summary` | System-wide summary data |
| `GET /api/employees` | Employee directory and profiles |
| `GET /api/cases` | All cases |
| `GET /api/cases/{case_id}` | Single case detail including comments |
| `GET /api/policies` | All policy documents |
| `GET /api/policies/{policy_id}` | Single policy document detail |
| `GET /api/payroll-ledgers` | Payroll ledger entries |
| `GET /api/recruitment` | Recruitment openings and candidate data |
| `GET /api/documents` | Document registry |
| `GET /api/messages` | Message records and notice packets |
| `GET /api/notifications` | System notifications |
| `GET /api/audit` | Audit event listing |
| `GET /api/audit/{audit_id}` | Single audit event detail |
| `GET /api/attachments/{attachment_id}` | Binary attachment content |

## POST Endpoints

| Endpoint | Purpose | Body |
|----------|---------|------|
| `POST /api/cases/{case_id}/comments` | Add a comment to a case | `{"author":"<string>","created_at":"<string>","visibility":"<string>","body":"<string>"}` |

All `author`, `created_at`, and `visibility` fields are optional in the POST body.

## Data Fetch Strategy

- Start broad: fetch the collection endpoint first (`/api/employees`, `/api/cases`, `/api/audit`, `/api/payroll-ledgers`, `/api/recruitment`, `/api/policies`, `/api/messages`, `/api/documents`, `/api/notifications`).
- Filter client-side for the target IDs (employee, case, opening, etc.).
- Drill into detail endpoints (`/api/cases/{id}`, `/api/policies/{id}`, `/api/audit/{id}`) when deeper record inspection is needed.
- For leave assignment history, check the employee detail response and cross-reference with policies, payroll ledgers, and audit events.
- For recruitment, cross-reference the recruitment endpoint with cases, messages (for notice packets), and audit events.
