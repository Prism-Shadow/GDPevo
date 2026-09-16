---
name: peopleops-lifecycle-solver
description: Solve PeopleOps lifecycle verification tasks (onboarding closeout, policy case review, recruitment reconciliation, leave/payroll source precedence, payroll readiness) against the PeopleOps REST API. Use this skill whenever the user needs to verify employee leave setup, payroll setup, case folder readiness, formal notice quality, candidate outcomes, recruitment costs, assignment source precedence, or accrual readiness using the PeopleOps task environment. The skill covers API navigation, evidence gathering, business rule application, and answer-template population with normalized business labels.
---

# PeopleOps Lifecycle Verification Solver

## Overview

This skill teaches how to solve PeopleOps lifecycle verification tasks against a
REST API-backed task environment. Every task provides a prompt, an answer
template (`answer_template.json`), and a base URL (usually expressed as
`<TASK_ENV_BASE_URL>`). The solver gathers evidence from the API, applies
business rules, and produces a JSON answer that matches the template exactly.

**Credentials**: When the prompt provides login credentials, use them verbatim.
The web UI login uses the same credentials. Common test credentials are
`ops.lead@peopleops.local` / `PeopleOps#2026`.

**Key principle**: The answer template is the contract. Every field has an
allowed type and, for enums, an explicit list of allowed values. Never invent
labels; pick only from the template's `allowed_values`.

---

## Step 1: Orient to the task

1. **Read the prompt** carefully. Identify the business scenario:

   - **Onboarding closeout** — leave setup + payroll setup verification for an
     employee whose status is `Onboarding`.
   - **Policy case review** — folder readiness + formal notice quality for a
     remote-work or lifecycle case.
   - **Recruitment reconciliation** — candidate outcomes + costs + notice
     follow-up for a recruitment opening.
   - **Leave source precedence** — resolve conflict between an employee profile
     summary and a leave assignment ledger record.
   - **Payroll assignment readiness** — validate submitted vs. draft salary
     assignments + accrual batch readiness.
   - **Cross-module escalation** — combines multiple checks across leave,
     payroll, documents, and notices.

2. **Read the answer template** from `input/payloads/answer_template.json`.
   This defines every field name, type, and allowed enum values. Keep it open
   while you work; all enum answers must come from its `allowed_values` lists.

3. **Call the API manifest**: `GET <TASK_ENV_BASE_URL>/api/manifest` to confirm
   which endpoints and data collections are available.

4. **Call the API summary**: `GET <TASK_ENV_BASE_URL>/api/summary` for record
   counts, departments, and status breakdowns.

---

## Step 2: Gather evidence

Read `references/api-endpoints.md` for the full endpoint reference with response
shapes. Here is a summary of what each endpoint answers:

| Endpoint | What it tells you |
|---|---|
| `GET /api/employees` | Employee profiles: name, department, leave_balance_days, status, salary_band, hire_date, manager |
| `GET /api/cases` | All cases; filter by case_id or employee_id. Also fetch individual case detail via `/api/cases/{case_id}` to get embedded approvals, attachments, and audit events |
| `GET /api/cases/{id}` | Single case detail: approvals (approver, decision, step), attachments (folder checklists), audit events |
| `GET /api/policies` | All policies with section text. Filter by policy_id |
| `GET /api/policies/{id}` | Single policy detail |
| `GET /api/payroll-ledgers` | **Authoritative** for leave assignments and salary assignments. Filter by employee_id, record_type, status |
| `GET /api/recruitment` | All recruitment openings: candidates (with committee_decision), offer_register, cost_ledger, notice_packets, payroll_precheck_records |
| `GET /api/documents` | Document folders: files, required_files, tags, required_tags, ready flag |
| `GET /api/messages` | All messages (formal notices): defects, quality, case_id, recipient |
| `GET /api/audit` | All audit events: **authoritative QA verdicts**. Filter by case_id, employee_id |
| `GET /api/audit/{id}` | Single audit event detail |
| `GET /api/notifications` | System notifications (useful for cross-module context) |

### Filtering strategy

The API returns full collections. Filter client-side in your solver code:

```python
import json, urllib.request

def fetch(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

base = "<TASK_ENV_BASE_URL>"

# Fetch all collections
employees = fetch(f"{base}/api/employees")
cases = fetch(f"{base}/api/cases")
ledgers = fetch(f"{base}/api/payroll-ledgers")
policies = fetch(f"{base}/api/policies")
docs = fetch(f"{base}/api/documents")
msgs = fetch(f"{base}/api/messages")
audits = fetch(f"{base}/api/audit")
recruitment = fetch(f"{base}/api/recruitment")
notifications = fetch(f"{base}/api/notifications")

# Filter by employee_id or case_id
emp_ledgers = [l for l in ledgers if l["employee_id"] == target_emp_id]
case_detail = fetch(f"{base}/api/cases/{target_case_id}")
emp_audits = [a for a in audits if a["employee_id"] == target_emp_id or a["case_id"] == target_case_id]
```

Always fetch individual case detail via `GET /api/cases/{case_id}` — it contains
embedded approvals, folder checklist attachments, comments, and audit events
that may not appear in the summary lists.

---

## Step 3: Apply business rules

Read `references/business-rules.md` for the complete rule catalog. Every rule is
derived from policy documents (especially `LEAVE-SRC-001`, `PAY-SRC-001`,
`HR-POL-014`, `POL-DOCS-2026`) and confirmed by audit evidence.

### The central source-precedence rule

> The latest **approved** or **submitted** record for the current period
> controls. Draft, voided, and superseded records must be excluded even when
> profile summaries conflict.

This applies to leave assignments, salary assignments, and any record with a
`status` field:

1. Prefer `Approved` or `Submitted` over `Draft` or `Superseded`.
2. If both are Approved/Submitted, prefer the most recent `updated_at`.
3. Exclude `Draft` records entirely unless the answer template explicitly allows
   them (check `draft_payroll_allowed` in the template).

### Leave verification

1. From payroll-ledgers, filter: `record_type == "Leave assignment"` for target
   employee.
2. Select the approved or submitted assignment with the latest `updated_at`.
3. The `policy_name` is the effective leave policy.
4. The `approved_leave_days` (or `worksheet_leave_days` when `approved_leave_days`
   is 0) is the annual/balance days.
5. The `ledger_id` is the assignment ID.
6. List draft and superseded assignment ledger IDs in the excluded array.

### Payroll verification

1. From payroll-ledgers, filter: `record_type == "Salary assignment"` for
   target employee.
2. Select the submitted one (status `Submitted`). If only draft exists, note
   that the status is `draft`.
3. The `base_salary` is the salary amount.
4. The `ledger_id` is the payroll/salary assignment ID.
5. Exclude draft assignment ledger IDs.
6. For accrual readiness checks: look for `accrual_batch_id` on the submitted
   assignment. Cross-reference with audit events that mention the batch.

### Case folder readiness

1. Read the case detail (`GET /api/cases/{case_id}`).
2. Inspect the **folder checklist attachment** (kind `Checklist`). It states
   which files and tags are present vs. missing.
3. Cross-reference with `GET /api/documents`: compare `files` against
   `required_files` and `tags` against `required_tags`.
4. A folder is **ready** only when **all** required files are present AND
   **all** required tags are present (per `POL-DOCS-2026` §5.1).
5. Missing files go in `missing_files`. Missing tags inform closeout blockers.

### Formal notice quality

1. Find messages for the target case from `GET /api/messages` (filter by
   `case_id`).
2. Check the `quality` field: `valid` or `defective`.
3. If defective, read the `defects` array. Possible defects:
   - `missing_ack_deadline` — no acknowledgement deadline in the notice
   - `missing_appeal_instructions` — no appeal instructions
   - `missing_waitlist_status` — waitlist status omitted
   - `missing_correct_policy` — references wrong/legacy policy
4. Also check the case's **approvals** (embedded in case detail) for the final
   approval authority, approval event ID, and decision.

### Recruitment reconciliation

1. Find the recruitment opening by `opening_id` in `GET /api/recruitment`.
2. Classify candidates by `committee_decision`:
   - `Selected` → `selected_candidate`
   - `Waitlisted` → `waitlisted_candidates`
   - `Rejected` → `rejected_candidates`
3. The offer register provides the offer ID, `base_salary`, and status for
   selected candidates. Only candidates with `status: "accepted"` qualify for
   payroll handoff.
4. Sum all `amount` values in `cost_ledger` for `recruitment_cost_total`.
5. Check `notice_packets` for follow-up: any notice with `required_action` and
   `status: "not_sent"` means that candidate needs notice follow-up.
6. For payroll handoff: per `PAY-SRC-001` §4.2, handoff is created only after
   the selected candidate has an **accepted** offer. Draft precheck records do
   not satisfy the gate.

### Audit evidence

Audit events (`GET /api/audit`) are the authoritative QA verdicts. When an audit
event confirms a finding (e.g., `profile_summary_stale`, `notice.defect`,
`case.close_blocked`, `payroll.draft_excluded`), use the audit event ID as
evidence.

- Include relevant audit event IDs in `audit_event_id` and
  `supporting_audit_event_ids`.
- Exclude irrelevant audit events in `excluded_audit_event_ids` — for example,
  when checking leave precedence, exclude audit events that are about documents
  or notices, not leave.

---

## Step 4: Populate the answer

### General rules

- Use **only** normalized enum labels from the answer template's
  `allowed_values`. Copy-paste to avoid typos.
- Arrays (`list[string]`) contain IDs only: employee IDs, case IDs, audit
  event IDs, assignment ledger IDs, candidate IDs.
- Numbers (`integer`, `number`) must match exactly what the data says.
- Booleans are `true`/`false` in JSON.
- Dates are strings like `"2026-04-01"`.
- Do not include extra fields the template does not ask for.
- **Return pure JSON. No markdown fences, no explanatory text, no surrounding
  prose.**

### Label selection guide

When the template asks for a source/gate/status/scope/result label, reason from
evidence then pick the matching allowed value. Below is guidance organized by
template field family:

**Leave source labels** (`leave_source`, `leave_precedence_source`):
- `leave_assignment_history` — authoritative record came from payroll-ledgers
  leave assignments (the standard case under `LEAVE-SRC-001` §2.1).
- `approved_assignment_current_period` — same meaning, used in precedence tasks.
- `employee_profile_summary` / `profile_summary_current_period` — profile
  summary controls (rare; only when no approved assignment exists).
- `case_summary_only` — case summary is the only available source.

**Payroll source labels** (`payroll_status`, `payroll_source_status`):
- `submitted` — controlling salary assignment has status Submitted.
- `draft` — only draft assignments exist.
- `superseded` — only superseded records exist.

**Closeout / next action**:
- `approve_onboarding_close` — all records clean, no defects.
- `block_close_and_reissue_notice` — formal notice is defective.
- `open_records_remediation` — documentation/tags/folder problems exist.
- `update_employee_summary` — profile summary is stale, needs update.
- `no_action` — nothing needed.

**Approval closeout gate**:
- `approval_sufficient_when_records_clean` — no defects found.
- `approval_not_sufficient_when_folder_or_notice_defective` — defects found.

**Final control result**:
- `approve_closeout` — everything passes.
- `hold_for_folder_and_notice_defects` — blocked by defects.
- `ready_with_monitoring` — passed but warrants monitoring.

**Audit scope**:
- `leave_source_precedence_only` — leave-only investigation.
- `document_notice_findings_only` — folder + notice investigation.
- `payroll_assignment_readiness` — payroll investigation.

**Recruitment labels**:
- `candidate_status_source`: `interview_feedback_and_offer` when committee
  decisions and offer register are cross-referenced; `case_summary_only` when
  only the case summary is used; `message_only` when only messages are used.
- `candidate_outcome_control`: `committee_decision_with_offer_confirmation`
  when both are cross-referenced; `message_status_only` / `case_summary_only`
  for weaker sources.
- `selected_offer_status`: `accepted`, `draft`, `withdrawn`, or `none` based on
  the offer register entry for the selected candidate.
- `cost_source`: `recruitment_cost_ledger` when costs come from the ledger;
  `case_summary_only` otherwise.
- `notice_quality_source`: `notice_packet_inspection` when notice packets
  (within the recruitment opening) are inspected; `message_notice_inspection`
  when messages endpoint is used; `case_summary_only` otherwise.
- `waitlisted_followup_action`: `send_waitlist_notice` when waitlist notice
  needs sending; `reissue_waitlist_notice_not_rejection` when an existing
  waitlist notice is defective; `no_action` when nothing needed.
- `rejected_followup_action`: `send_rejection_notice` when rejection notice
  needs sending; `reissue_rejection_notice` for reissue; `no_action` otherwise.
- `payroll_handoff_gate`: `accepted_offer_only` — only accepted candidates get
  payroll handoff (per `PAY-SRC-001` §4.2); `accepted_offer_and_submitted_assignment`;
  `all_interviewed_candidates`.
- `payroll_assignment_status_required`: `submitted_after_acceptance` — the
  handoff assignment must be submitted, not draft.
- `handoff_control_result`: `submitted_handoff_required_after_acceptance` when
  the selected candidate has an accepted offer and a submitted assignment is
  needed; `submitted_handoff_required`; `no_handoff_required`.
- `draft_payroll_allowed`: `false` when draft prechecks are present but not
  valid for the gate; `true` only if explicitly allowed.
- `offer_exclusion_reason_for_waitlisted`: `no_accepted_status_or_offer` —
  waitlisted candidates lack an accepted offer.

**Other labels**:
- `precedence_source`: `approved_assignment_over_profile` when the approved
  assignment overrides the profile; `employee_profile_summary` when profile
  controls; `case_summary_only` otherwise.
- `audit_result`: `profile_summary_stale` when profile is out of date;
  `ready_with_monitoring` when okay but watch; `block_close` when blocked.
- `escalation_action`: `open_records_remediation` when record problems need
  fixing; `block_close_and_reissue_notice` for notice defects; `no_action`.
- `records_remediation_owner`: `Records`, `People Ops Compliance`, or
  `Payroll QA` based on the nature of the problem.
- `notice_remediation_action`: `reissue_defective_notices` when notices have
  defects; `send_new_offer_notice` for new notices; `no_notice_action`.
- `draft_exclusion_rule`: `exclude_draft_assignment` when draft records must be
  excluded; `draft_allowed` when drafts are permitted; `exclude_superseded_only`
  when only superseded records are excluded.
- `evidence_source_order`: `approval_history_folder_notice_audit` when the full
  chain (approval → folder → notice → audit) is reviewed;
  `folder_notice_audit` for a shorter chain; `audit_only` when only audit
  events are used.
- `folder_required_tag_action`: `no_tag_action` when tag is present;
  `add_required_tag` when tag is missing.
- `notice_evidence_source`: `notice_packet_inspection` when notice packets are
  inspected; `message_notice_inspection` when messages endpoint is used;
  `case_summary_only` otherwise.

### Cross-reference before finalizing

Before writing the answer, verify internal consistency:

- If `closeout_action` is `block_close_and_reissue_notice`, then
  `approval_closeout_gate` should be
  `approval_not_sufficient_when_folder_or_notice_defective`, and
  `final_control_result` should be `hold_for_folder_and_notice_defects`.
- If `payroll_status` is `submitted` and draft records are excluded,
  `draft_exclusion_rule` should be `exclude_draft_assignment`.
- If an audit event confirms a finding, include its ID in the relevant
  `audit_event_id` and `supporting_audit_event_ids` arrays.
- Excluded IDs (audit, leave, payroll) must appear in the corresponding
  `excluded_*` array — never leave it empty if there are records to exclude.

---

## Step 5: Validate and output

1. **Re-read the answer template** one final time. Does every field have a
   value? Do all enum values match the `allowed_values` list exactly? Are all
   array items IDs only?
2. **Validate JSON** — it must parse cleanly without trailing commas.
3. **Output only the JSON object** — no markdown code fences, no explanatory
   text, no surrounding prose.

---

## Reference files

- [API Endpoints Reference](references/api-endpoints.md) — full endpoint
  reference with response field descriptions.
- [Business Rules Catalog](references/business-rules.md) — detailed rules with
  policy cross-references, precedence chains, and edge cases.

Read these when you need deeper detail on an endpoint or rule that the summary
above does not cover.
