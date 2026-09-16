# API Reference Details

Field-level descriptions for each endpoint response. Use this when interpreting raw API responses.

## /api/summary

```json
{
  "counts": {
    "employees": 44,
    "cases": 7,
    "policies": 4,
    "payroll_ledgers": 61,
    "recruitment": 2,
    "documents": 4,
    "messages": 4,
    "notifications": 4,
    "audit_events": 8
  },
  "departments": [
    {
      "department_id": "D-101",
      "name": "People Ops",
      "leader": "Theo Tran"
    }
  ]
}
```

The summary gives dataset size and department roster. Use it for orientation, not for decision-making.

## /api/employees

Returns an array of employee profile objects:

```json
{
  "employee_id": "EMP-104",
  "name": "Mira Chen",
  "department": "Engineering",
  "department_id": "D-103",
  "designation": "Platform Engineer",
  "division": "Product and Technology",
  "status": "Onboarding",
  "employment_type": "Full-time",
  "hire_date": "2026-03-01",
  "leave_balance_days": 18,
  "location": "Boston",
  "manager": "Alicia Ames",
  "remote_profile": "Hybrid",
  "salary_band": "B4"
}
```

**Important:** The `leave_balance_days` field on the profile may be stale. The profile summary does not always reflect the latest approved leave assignment from the payroll ledgers. Always verify against `/api/payroll-ledgers` using the source precedence rule.

## /api/cases

Returns an array of case summary objects. For full detail, fetch `/api/cases/{case_id}`.

```json
{
  "case_id": "CASE-RW-221",
  "case_type": "Remote work exception",
  "title": "Remote-work exception review for Rahul Johnson",
  "status": "In Review",
  "priority": "High",
  "employee_id": "EMP-221",
  "employee_name": "Rahul Johnson",
  "department": "R&D",
  "owner": "Legal Desk",
  "policy_refs": ["HR-POL-014", "POL-DOCS-2026"],
  "summary": "Approved with conditions but notice must be reissued.",
  "due_at": "2026-06-05T17:00",
  "opened_at": "2026-05-21T10:20"
}
```

## /api/cases/{case_id}

Returns full case detail including:

- `approvals[]` -- approval history with `approval_id`, `approver`, `decision`, `step`, `decided_at`, `note`
- `attachments[]` -- filed attachments with `attachment_id`, `name`, `kind`, `content`, `status`, `uploaded_by`
- `audit_events[]` -- audit events linked to the case
- `comments[]` -- internal comments
- `policy_refs[]` -- policy IDs referenced by the case

The `attachments` can include checklist attachments whose `content` field describes folder readiness findings.

## /api/policies

Returns an array of policy documents:

```json
{
  "policy_id": "HR-POL-014",
  "title": "Remote Work Policy",
  "summary": "Remote-work jurisdiction, exception, and notice requirements.",
  "status": "Active",
  "effective_date": "2026-01-01",
  "owner": "Legal Desk",
  "sections": [
    {
      "heading": "4.2 Domestic jurisdiction",
      "body": "Remote work is limited to approved domestic tax jurisdictions..."
    }
  ]
}
```

Key policies to reference:
- **HR-POL-014** (Remote Work Policy) -- jurisdiction, exception, and notice requirements. Section 7.1 requires executive approval, time limits, tax equalization, VPN-only access, quarterly compliance review, appeal instructions, and acknowledgement deadline in the formal notice.
- **LEAVE-SRC-001** (Leave Source Precedence) -- Section 2.1: "The latest approved or submitted leave assignment for the period controls. Draft, voided, and obsolete records are excluded even when profile summaries conflict."
- **PAY-SRC-001** (Payroll Assignment Source) -- Section 3.4: "Use the current submitted salary assignment. Draft planning assignments do not affect payroll readiness or accrual checks." Section 4.2: "Recruiting payroll handoff is created only after a selected candidate has an accepted offer. The handoff must be submitted; draft prechecks do not satisfy the assignment gate."
- **POL-DOCS-2026** (Lifecycle Folder Checklist) -- Section 5.1: "A folder is not ready unless all required files and required tags shown in the folder checklist are present."

## /api/payroll-ledgers

Returns an array of mixed record types. Filter by `record_type` and `employee_id`.

**Leave assignment records:**
```json
{
  "ledger_id": "LA-104-2026-B",
  "employee_id": "EMP-104",
  "employee_name": "Mira Chen",
  "record_type": "Leave assignment",
  "status": "Approved",
  "period": "2026",
  "policy_name": "Engineering Flex Leave 2026",
  "approved_leave_days": 18,
  "worksheet_leave_days": 18,
  "updated_at": "2026-03-01T09:00"
}
```

**Salary assignment records:**
```json
{
  "ledger_id": "PAY-104-2026-SUB",
  "employee_id": "EMP-104",
  "employee_name": "Mira Chen",
  "record_type": "Salary assignment",
  "status": "Submitted",
  "period": "2026-03",
  "base_salary": 128000,
  "accrual_batch_id": null,
  "approved_leave_days": 0,
  "worksheet_leave_days": 0,
  "updated_at": "2026-03-01T09:30"
}
```

**Status values:** `Approved`, `Submitted`, `Draft`, `Superseded`

For leave decisions: use the latest `Approved` or `Submitted` leave assignment. `Superseded` and `Draft` are excluded.

For salary decisions: use the `Submitted` salary assignment. `Draft` salary assignments are excluded.

## /api/recruitment

Returns an array of recruitment openings:

```json
{
  "opening_id": "REQ-DA-77",
  "title": "Data Analyst",
  "status": "Submitted",
  "candidates": [
    {
      "candidate_id": "CAND-DA-7701",
      "name": "Mira Shah",
      "committee_decision": "Selected",
      "pipeline_stage": "Final committee",
      "notice_status": "Offer package approved",
      "rounds": [5, 5]
    }
  ],
  "offer_register": [
    {
      "offer_id": "OFFER-DA-7701",
      "candidate_id": "CAND-DA-7701",
      "base_salary": 112000,
      "status": "accepted"
    }
  ],
  "cost_ledger": [
    {
      "line_id": "REQ-DA-77-COST-01",
      "label": "Agency sourcing invoice",
      "amount": 4800
    }
  ],
  "notice_packets": [
    {
      "candidate_id": "CAND-DA-7702",
      "notice_type": "waitlist",
      "status": "not_sent",
      "required_action": "send_waitlist_notice"
    }
  ]
}
```

**Committee decision values:** `Selected`, `Waitlisted`, `Rejected`
**Offer status values:** `accepted`, `draft`, `withdrawn`
**Notice status values:** `not_sent`, `sent`

For `recruitment_cost_total`: sum all `amount` values in `cost_ledger[]`.
For `notice_followup_required`: list candidate IDs where the notice packet has `status: "not_sent"` or `required_action` is non-null.
For payroll handoff: only the selected candidate with `offer_register` status `accepted` triggers `create_payroll_precheck`.

## /api/documents

Returns an array of document folders:

```json
{
  "document_id": "DOC-RW-221",
  "title": "Exception-Case-RW-221",
  "ready": false,
  "files": ["request-summary.txt", "decision-record.txt"],
  "required_files": ["request-summary.txt", "decision-record.txt", "tax-equalization-agreement.pdf"],
  "tags": ["PolicyException2026"],
  "required_tags": ["PolicyException2026"]
}
```

**Folder readiness check:** The `ready` boolean is not authoritative. Verify by comparing `files` against `required_files` and `tags` against `required_tags`. Missing items are closeout blockers.

## /api/messages

Returns an array of formal notice messages:

```json
{
  "message_id": "MSG-RW-221",
  "case_id": "CASE-RW-221",
  "subject": "Formal Decision CASE-RW-221",
  "body": "Approved with conditions. Acknowledgement requested by 2026-04-25.",
  "recipient": "Rahul Johnson",
  "channel": "Email",
  "status": "Draft",
  "sent_at": "2026-04-24T12:00",
  "quality": "defective",
  "defects": ["missing_appeal_instructions"]
}
```

**Notice quality values:** `valid`, `defective`
**Defect values:** `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`

Match messages to cases by `case_id`. A notice with `quality: "defective"` is a closeout blocker.

## /api/audit

Returns an array of audit events:

```json
{
  "audit_id": "AUD-CASE221-09",
  "case_id": "CASE-RW-221",
  "employee_id": "EMP-221",
  "actor": "Legal QA",
  "event": "notice.defect",
  "detail": "Formal notice missing appeal instructions; return notice for reissue before close.",
  "source": "Audit Service",
  "timestamp": "2026-04-24T10:00"
}
```

**Event types seen in the data:**
- `leave.profile_mismatch` -- profile summary stale, approved assignment controls
- `payroll.ready` -- payroll assignment matches accrual batch
- `notice.defect` -- formal notice has defects
- `case.close_blocked` -- case closeout blocked by folder/notice issues
- `payroll.draft_excluded` -- draft payroll record excluded
- `folder.tag_missing` -- folder missing required tags
- `cross_module.escalation_package` -- combined lifecycle risk package

**Audit scoping rule:** When a task asks about a specific scope (e.g., leave source precedence), include only audit events whose `event` field matches that scope. Exclude audit events from other scopes even if they share the same `employee_id` or `case_id`.

## /api/notifications

Returns system notifications (same shape as /api/messages in this dataset). Check for message-level details if the prompt requires notification inspection.

## /api/attachments/{attachment_id}

Returns attachment content. Attachments are listed in case detail under `attachments[]`. Use this to read checklist attachments that describe folder readiness findings.

## Common Query Patterns

### Finding an employee's leave assignments
```bash
curl -s $BASE/api/payroll-ledgers | jq '[.[] | select(.employee_id=="EMP-104" and .record_type=="Leave assignment")]'
```

### Finding an employee's salary assignments
```bash
curl -s $BASE/api/payroll-ledgers | jq '[.[] | select(.employee_id=="EMP-104" and .record_type=="Salary assignment")]'
```

### Filtering drafts/superseded out
```bash
curl -s $BASE/api/payroll-ledgers | jq '[.[] | select(.employee_id=="EMP-104" and .record_type=="Leave assignment" and .status != "Draft" and .status != "Superseded")]'
```

### Finding the document folder for a case
Look for a folder whose `document_id` or `title` references the case or employee. The mapping is not always direct -- read all documents and match by context.

### Finding the audit events for a specific scope
```bash
curl -s $BASE/api/audit | jq '[.[] | select(.case_id=="CASE-445" or .employee_id=="EMP-255")]'
```

Then filter by event type to isolate the right scope.
