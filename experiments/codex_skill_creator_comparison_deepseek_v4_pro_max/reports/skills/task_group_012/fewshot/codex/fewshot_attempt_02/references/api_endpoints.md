# PeopleOps API Endpoints

All endpoints are relative to `<TASK_ENV_BASE_URL>`.

## Table of Contents

- [Discovery](#discovery)
- [Employees](#employees)
- [Cases](#cases)
- [Policies](#policies)
- [Payroll Ledgers](#payroll-ledgers)
- [Recruitment](#recruitment)
- [Documents](#documents)
- [Messages](#messages)
- [Notifications](#notifications)
- [Audit](#audit)
- [Attachments](#attachments)
- [Comments](#comments)

---

## Discovery

### GET /
Server root. Returns overall service status.

### GET /api/manifest
Returns navigation manifest listing all available API endpoints.

### GET /api/summary
Returns an aggregate summary across employees, cases, payroll, policies, and
other top-level records.

---

## Employees

### GET /api/employees
Returns the full employee directory. Each employee record includes:

- `id` — employee ID (e.g. `EMP-104`)
- `name` — full name
- `department`
- `profile_summary` — current profile-level policy and leave balance (may be
  stale; see business rules)
- `leave_assignments` — array of leave assignment records
- `payroll_assignments` — array of payroll assignment records

---

## Cases

### GET /api/cases
Returns all cases. Each case record includes:

- `case_id` (e.g. `CASE-RW-221`)
- `title`
- `status`
- `approval_history` — array of approval events with `event_id`,
  `approval_authority`, `decision`, and details
- `folder` — object with `files` array and `tags` array
- `notices` — array of formal notice packet references
- `related_employee_id`
- `related_opening_id`

### GET /api/cases/{case_id}
Returns full detail for a single case, including all nested approval, folder,
notice, and related-record data.

---

## Policies

### GET /api/policies
Returns all policy documents. Each policy record includes:

- `policy_id`
- `name` — policy name (e.g. `Engineering Flex Leave 2026`)
- `effective_period`
- `annual_leave_days` — default annual leave days under the policy
- `department`

### GET /api/policies/{policy_id}
Returns full text and metadata for a single policy.

---

## Payroll Ledgers

### GET /api/payroll-ledgers
Returns all payroll assignment records. Each payroll record includes:

- `assignment_id` (e.g. `PAY-104-2026-SUB`)
- `employee_id`
- `base_salary`
- `effective_date`
- `status` — one of `submitted`, `draft`, `superseded`
- `accrual_batch_id` — when present, the linked accrual batch
- `accrual_ready` — boolean for accrual readiness

---

## Recruitment

### GET /api/recruitment
Returns all recruitment openings, candidates, and offers. Each opening record
includes:

- `opening_id` (e.g. `REQ-DA-77`)
- `title`
- `candidates` — array of candidate records with `candidate_id`, `status`
  (`selected`, `waitlisted`, `rejected`)
- `offers` — array of offer records with `offer_id`, `candidate_id`,
  `base_salary`, `status` (`accepted`, `draft`, `withdrawn`, `none`)
- `cost_ledger` — array of cost line items with `item` description and `amount`
- `notices` — array of notice packet references per candidate

---

## Documents

### GET /api/documents
Returns the document registry listing all files across cases and employee
folders. Useful for verifying whether required files exist or are missing.

---

## Messages

### GET /api/messages
Returns all internal messages and communications. Each message includes sender,
recipient, subject, body, and timestamp. Messages may reference case IDs or
employee IDs.

---

## Notifications

### GET /api/notifications
Returns the notification log for formal notices sent, pending, or defective.
Each notification record includes:

- `notification_id`
- `case_id` or `candidate_id`
- `type` — notice type (offer, waitlist, rejection, onboarding, etc.)
- `quality` — `valid` or `defective`
- `defects` — array of defect labels
- `ack_deadline` — acknowledgment deadline date/time

---

## Audit

### GET /api/audit
Returns the full audit log. Each audit event includes:

- `audit_id` (e.g. `AUD-CASE221-09`)
- `scope` — `document_notice`, `leave_source`, `payroll_assignment`
- `findings` — structured findings object
- `related_case_id`
- `related_employee_id`
- `timestamp`

### GET /api/audit/{audit_id}
Returns full detail for a single audit event.

---

## Attachments

### GET /api/attachments/{attachment_id}
Returns file content and metadata for an attachment referenced by a case, notice
packet, or document.

---

## Comments

### POST /api/cases/{case_id}/comments
Post a comment on a case. Body: `{"text": "..."}`.
