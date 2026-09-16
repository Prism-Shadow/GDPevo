# PeopleOps Console Domain Model

This document catalogues every business object in the PeopleOps Console, its
relationships, and how to navigate between them.

---

## Object map

| Object | API endpoint | Key identity field | Where referenced |
|---|---|---|---|
| Employee | GET /api/employees | employee_id | Payroll ledgers, cases, audit events |
| Leave assignment | GET /api/payroll-ledgers (filter record_type) | ledger_id | Employee |
| Salary assignment | GET /api/payroll-ledgers (filter record_type) | ledger_id | Employee |
| Case | GET /api/cases, GET /api/cases/{id} | case_id | Documents, messages, audit events |
| Policy | GET /api/policies, GET /api/policies/{id} | policy_id | Cases (via policy_refs) |
| Document folder | GET /api/documents | document_id | Case (by naming convention) |
| Message (notice) | GET /api/messages | message_id | Case |
| Notification | GET /api/notifications | message_id | Case |
| Audit event | GET /api/audit, GET /api/audit/{id} | audit_id | Employee, case |
| Recruitment opening | GET /api/recruitment | opening_id | Candidates, offers, costs, notices |
| Attachment | GET /api/attachments/{id} | attachment_id | Case (via attachments array) |

---

## How objects link

### Employee -> Leave assignments

An employee may have multiple leave assignments in the payroll ledger. Filter
/api/payroll-ledgers by employee_id and record_type: "Leave assignment".
Choose the one with status: "Approved" (or "Submitted") and the most
recent updated_at. The assignment's policy_name is the effective leave
policy; its approved_leave_days (or worksheet_leave_days) is the annual
balance.

### Employee -> Salary assignments

Filter /api/payroll-ledgers by employee_id and record_type: "Salary
assignment". Choose the one with status: "Submitted" and the most recent
period. Its base_salary is the authoritative salary. If it has an
accrual_batch_id field, the accrual batch is ready.

### Case -> Documents

Document folders are not keyed by case_id directly. Instead, match by naming
convention: the document folder's document_id or title typically contains
the case ID or employee ID. For example, DOC-RW-221 corresponds to
CASE-RW-221.

### Case -> Messages / Notifications

Messages and notifications carry a case_id field. Filter /api/messages or
/api/notifications by case_id to find the formal notice for a case.

### Case -> Audit events

Audit events carry a case_id field. Filter /api/audit by case_id to find
all audit events for a case. Additionally, audit events carry an employee_id,
so you can also find audit events by employee.

### Employee -> Audit events

Audit events carry an employee_id. When a task asks you to review audit
events for an employee, filter /api/audit by employee_id.

### Case -> Approvals

Approvals are nested inside the case detail at GET /api/cases/{case_id} under
the approvals array. Each approval has an approval_id, approver,
decision, and decided_at.

### Case -> Attachments

Attachments are nested inside the case detail under the attachments array.
Each has an attachment_id that can be used with GET
/api/attachments/{attachment_id} to retrieve the attachment content.

### Recruitment opening -> Candidates, Offers, Costs

The recruitment opening (from GET /api/recruitment) contains nested arrays:
candidates, offer_register, cost_ledger, notice_packets, and
payroll_precheck_records. All data for a recruitment reconciliation is inside
the opening object -- no need to cross-reference other endpoints.

---

## Policing stale profile data

The employee profile at /api/employees carries a leave_balance_days field
that may be stale. The profile is stored at a point in time and may not reflect
the latest approved leave assignment from the ledger. Always cross-check:

1. Read the employee profile to get baseline data.
2. Read leave assignments from the ledger.
3. If an approved assignment exists and its policy or balance differs from the
   profile, the profile is stale. The assignment controls.

This is the core pattern behind the leave source precedence rule.

---

## Policing draft records

Draft records (status "Draft") appear in the payroll ledger alongside
operational records. They represent planning or proposed changes that have not
been submitted. Always filter them out:

- Draft leave assignments: not the effective leave policy
- Draft salary assignments: not the effective base salary
- Draft payroll prechecks (in recruitment): do not satisfy the handoff gate

Superseded records (status "Superseded") have been explicitly replaced. When
a newer Approved or Submitted record exists for the same employee and period,
exclude the superseded record.
