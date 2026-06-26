---
name: peopleops-console-lifecycle-control
description: Solve ERP HR "PeopleOps Console" lifecycle/leave/payroll/policy-case/recruitment/document/notice/audit tasks by cross-referencing the remote HTTP API and applying source-precedence, folder-readiness, notice-defect, and audit-scope business rules to emit normalized-label JSON.
---

# PeopleOps Console — Lifecycle Control Skill

You answer HR lifecycle questions for the PeopleOps Console by reading a remote
HTTP API and returning a single JSON object that matches the task's
`answer_template.json`. Every value must be either a fact pulled from the API or
the exact **normalized business label** allowed by the template enum. Never write
free-text explanations into label fields, and never invent IDs.

## 1. How to use the remote API

Base URL is given in the environment-access doc. No auth (login text in prompts is
flavor). All responses are JSON. Use HTTP GET; `q=` is a case-insensitive
substring filter over scalar fields, so `q=EMP-118`, `q=CASE-445`, `q=REQ-DA-77`
are effective lookups; omit `q` to list a whole collection.

Endpoints you will rely on:
- `/api/summary`, `/api/manifest` — counts, departments, sanity check.
- `/api/employees?q=` — profile (department, salary_band, `leave_balance_days`, status).
- `/api/payroll-ledgers?q=` — BOTH leave assignments AND salary assignments AND
  accrual/adjustment rows live here, keyed by `record_type`, `status`, `period`.
- `/api/policies` / `/api/policies/{id}` — the governing precedence rules (read these first; they state the tie-break logic verbatim).
- `/api/cases?...` (summaries) and `/api/cases/{id}` (FULL: approvals,
  attachments, comments, embedded audit_events, folder/notice detail).
- `/api/documents?q=` — folders with `files`, `required_files`, `tags`,
  `required_tags`, `ready`.
- `/api/messages?q=` — formal notices delivered as messages, with `quality` and `defects`.
- `/api/recruitment?q=` — openings with `candidates`, `offer_register`,
  `cost_ledger`, `notice_packets`, `payroll_precheck_records`.
- `/api/audit?q=&case_id=` and `/api/audit/{id}` — QA events; their `detail`
  text is frequently the authoritative tie-breaker (see below).

**Workflow for any task:** (1) read the prompt + answer_template to learn which
fields and which enum labels are in play; (2) pull the focal entity by id across
employees, payroll-ledgers, cases/{id}, documents, messages, recruitment, audit;
(3) read the policy doc(s) named in the case's `policy_refs`; (4) apply the rules
below; (5) emit JSON matching the template, using only allowed enum values and
correct types (integers as integers, lists as lists, booleans as booleans).

## 2. Core source-precedence rules

These come from the policy documents and are the heart of most tasks.

**Leave source precedence (LEAVE-SRC-001).** The latest **approved or submitted**
leave assignment for the period controls entitlement. Draft, voided, superseded,
and obsolete rows are EXCLUDED even when the employee profile summary disagrees.
- `leave_source` = `leave_assignment_history` (not `employee_profile_summary`).
- `leave_precedence_source` = `approved_assignment_current_period`
  (NOT `profile_summary_current_period`).
- When a case is specifically a profile-vs-assignment dispute:
  `precedence_source` = `approved_assignment_over_profile`,
  `profile_policy_ignored` = `true`, and the next action is to update the stale
  summary (`update_employee_summary`).
- List every excluded leave ledger id (draft + superseded/obsolete) in the
  excluded-leave field.

**Payroll/salary source (PAY-SRC-001).** Use the **current submitted** salary
assignment for base salary and readiness. Draft planning assignments do NOT count
and must be excluded; superseded rows are excluded too.
- `payroll_status` / `payroll_source_status` = `submitted`.
- `draft_exclusion_rule` = `exclude_draft_assignment`; `draft_payroll_allowed` = `false`.
- Put the draft (and any superseded) salary id in the excluded-payroll field.

**Accrual readiness.** A submitted salary assignment is accrual-ready when it
matches the relevant accrual batch (the assignment row carries the
`accrual_batch_id`, and an audit `payroll.ready` event confirms it).
- `accrual_ready` = `true` in that case; take `accrual_batch_id` from the
  submitted assignment row.
- `control_result` for payroll readiness = `ready_with_monitoring` — NOT
  `approve_closeout` (that label is reserved for onboarding-close with clean records).

## 3. Folder readiness, missing files, and required tags

From the lifecycle folder checklist (POL-DOCS-2026): a folder is ready ONLY when
**every** required file AND **every** required tag is present.
- `folder_ready` = the document's `ready` flag; verify it by diffing
  `required_files` minus `files` and `required_tags` minus `tags`.
- `missing_files` = required_files not present in files (exact filenames).
- `required_tag_present` = whether the required tag(s) are all in `tags`.
- If the required tag is already present, `folder_required_tag_action` =
  `no_tag_action`; only use `add_required_tag` when a required tag is missing.
- `closeout_blockers` is driven by the actual gaps: include
  `missing_required_files` only if a file is missing, `missing_required_tags`
  only if a tag is missing, `defective_formal_notice` only if the notice is
  defective. Do not list a blocker that does not apply (e.g. tag present ⇒ no
  `missing_required_tags`).

## 4. Formal-notice quality and defect codes

Notices are inspected from the **notice packet** (recruitment `notice_packets`)
or the message record (`/api/messages`), which carry `quality` and `defects`.
- `notice_quality` = `valid` or `defective` straight from the record.
- `notice_quality_source` / `notice_evidence_source` = `notice_packet_inspection`
  (assess the formal notice packet; this is the right label even when the notice
  is delivered through a message channel — do not pick `message_notice_inspection`
  or `case_summary_only`).
- Defect codes come from the controlled vocabulary and must match the record's
  `defects` exactly: `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`. Copy the listed defects;
  do not infer extra ones.
- Remediation: a defective notice ⇒ `reissue_defective_notices` /
  `block_close_and_reissue_notice`. A waitlist notice that was wrongly omitted or
  mislabeled is reissued as a waitlist notice, not a rejection
  (`reissue_waitlist_notice_not_rejection`); a not-yet-sent waitlist/rejection
  notice is a fresh send (`send_waitlist_notice` / `send_rejection_notice`).

## 5. Approval / closeout gate and final control result

Approval alone is not enough to close.
- `approval_closeout_gate` = `approval_sufficient_when_records_clean` ONLY when
  the folder is ready AND the notice is valid (no defects). If any folder file/tag
  gap or notice defect exists, it is
  `approval_not_sufficient_when_folder_or_notice_defective`.
- `final_control_result`:
  - clean records (no folder/notice defect) ⇒ `approve_closeout`;
  - any folder/notice defect ⇒ `hold_for_folder_and_notice_defects`;
  - `ready_with_monitoring` is the payroll-readiness verdict, not an
    onboarding-close verdict.
- `closeout_action` / `next_action` follows the same logic: clean ⇒
  `approve_onboarding_close`; notice defect ⇒ `block_close_and_reissue_notice`; a
  missing required FILE is a records issue ⇒ `open_records_remediation`. When both
  a file is missing and the notice is defective, the immediate `next_action`
  addresses the notice (`block_close_and_reissue_notice`) while the
  `escalation_action` opens records remediation for the file
  (`open_records_remediation`) — these two fields can legitimately differ.
- `evidence_source_order` for a closeout review =
  `approval_history_folder_notice_audit` (approvals first, then folder, notice, audit).
- `records_remediation_owner` for a single case's missing folder file = `Records`
  (owner of folder/required evidence). `People Ops Compliance` owns the
  cross-module escalation package, not single-case file remediation.

## 6. Audit correlation and scope (very point-sensitive)

Each task has ONE audit scope; set `audit_scope` to match the task:
`leave_source_precedence_only`, `payroll_assignment_readiness`, or
`document_notice_findings_only`.

- `audit_event_id` / `supporting_audit_event_ids` = the audit event(s) whose
  `event`/`detail` are IN the current scope (e.g. the `leave.profile_mismatch`
  event for a leave task, the `payroll.ready` event for an accrual task, the
  `notice.defect` / folder event for a doc/notice task).
- `excluded_audit_event_ids` = **same-case** audit events that belong to a
  DIFFERENT scope and must be kept out of this decision (e.g. on a leave-scope
  task, exclude the same case's folder/notice audit event). Rules learned the
  hard way:
  - Do NOT dump every other case's audit ids into the exclusion list — only
    same-case, out-of-scope events belong there.
  - If the case has no other-scope audit event, `excluded_audit_event_ids` = `[]`.
  - Omitting a genuinely adjacent same-case out-of-scope event costs points, so
    always check the full `/api/cases/{id}.audit_events` list for siblings.
- **The audit `detail` text is an authoritative tie-breaker.** When a leave or
  payroll task has several "Approved"/"Submitted" ledger rows, the audit QA detail
  often names the controlling assignment id and the resulting balance/policy —
  trust that named record rather than guessing the latest or largest row.
- The cross-module escalation package event lists the related event ids and the
  control owner; treat it as the routing record, not as in-scope evidence for a
  single entity's leave/payroll decision.

## 7. Recruitment reconciliation

- Candidate outcomes come from committee decision + offer confirmation:
  `candidate_status_source` = `interview_feedback_and_offer`,
  `candidate_outcome_control` = `committee_decision_with_offer_confirmation`.
  Map `committee_decision` to selected / waitlisted / rejected arrays
  (arrays hold candidate IDs only).
- The selected candidate's offer status comes from `offer_register`
  (`accepted` / `draft` / `withdrawn`); `offer_id` and `offer_base_salary` from
  that register row.
- `recruitment_cost_total` = **sum of this opening's `cost_ledger` items only**.
  Do not add other openings' ledgers. `cost_source` = `recruitment_cost_ledger`.
- Notice follow-up: list candidates whose notices are not yet sent / are
  defective; choose send vs reissue per §4.
- Waitlisted candidates are excluded from the payroll/offer handoff because they
  have `no_accepted_status_or_offer`.
- Payroll handoff gate (PAY-SRC-001): a handoff is created only after a selected
  candidate has an **accepted** offer, and the handoff/assignment must be
  **submitted** — a draft precheck never satisfies the gate
  (`draft_payroll_allowed` = `false`). When an offer is accepted, a submitted
  handoff/assignment is required after acceptance; when no offer is accepted,
  there is no handoff. (The exact normalized label among the close gate/status
  variants depends on the template's enum wording — read the allowed values and
  pick the option that states "submitted, after acceptance"; verify against the
  policy text rather than assuming.)

## 8. Output discipline / common misjudgments that cost points

- Return ONLY the JSON object matching the template — no markdown, no commentary.
- Use the EXACT allowed enum strings; respect types (int vs number vs string,
  list vs scalar, boolean not string).
- Dates in dedicated date fields are usually `YYYY-MM-DD` (derive from
  `period`/`updated_at`), not full timestamps.
- Authoritative state spans modules: never answer a leave/payroll question from
  the employee profile or a case summary alone — confirm with the ledger, the
  policy doc, and the audit detail.
- Mistakes that previously lowered scores, now avoided:
  - using `profile_summary` precedence instead of `approved_assignment`;
  - calling a payroll-readiness result `approve_closeout` instead of `ready_with_monitoring`;
  - listing unrelated cases' audit ids as "excluded", or conversely forgetting to
    exclude a same-case out-of-scope audit event;
  - choosing `message_notice_inspection` instead of `notice_packet_inspection`;
  - assigning single-case file remediation to People Ops Compliance instead of Records;
  - summing cost ledgers across openings instead of the one opening in scope;
  - flagging `missing_required_tags` when the required tag is actually present.

NOTE: There is no judge or scoring API available at test time. Do not attempt to
call any feedback/scoring endpoint when solving real tasks — derive the answer
from the read-only PeopleOps API and the rules above.
