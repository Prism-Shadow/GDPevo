# HR Employee-Lifecycle Verification Skill

Reusable workflow rules for solving Northwind PeopleOps Console lifecycle tasks against the
remote read-only JSON API. Covers onboarding closeout, leave source precedence, payroll
assignment & accrual readiness, recruitment reconciliation, and policy-case folder/notice review.

## When to use

Use this skill whenever a task asks you to verify, reconcile, or audit an employee-lifecycle
record in the Northwind PeopleOps Console: approving onboarding close, determining authoritative
leave/payroll records, checking folder readiness and formal-notice quality, reconciling a
recruitment packet, or validating payroll/accrual readiness. The skill tells you which endpoints
to call, in what order, which records are authoritative, and which enum labels to emit.

## Environment

- API base: `<remote-env-url>` (read-only, no auth). Prefixed here as `{BASE}`.
- Health: `GET {BASE}/health`.
- The prompt's `http://127.0.0.1:<port>/` and login creds refer to this same remote env; use
  `{BASE}` for all API calls. The REST API under `/api/*` needs no auth.

### Available GET endpoints
- `/api/manifest` — module/endpoint map, dataset seed
- `/api/summary` — live record counts and departments
- `/api/employees?q=&status=` — employee profiles (leave balance lives here, but NOT the controlling policy)
- `/api/cases?q=&status=&type=` — policy-case summaries
- `/api/cases/<case_id>` — FULL case detail (approvals list, attachments list, comments list, embedded audit_events list). RICHEST endpoint.
- `/api/policies` and `/api/policies/<id>` — leave/payroll/folicy rule definitions
- `/api/payroll-ledgers?q=&status=&type=` — contains BOTH "Leave assignment" AND "Salary assignment" record_types (also HRMS leave ledger / People Ops adjustment). This is the leave + payroll ledger.
- `/api/recruitment?q=` — openings, candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records, audit_event_id
- `/api/documents?q=` — lifecycle folders (files present, required_files, tags, required_tags, ready)
- `/api/messages?q=` — formal notice messages (defects, quality, ack deadline, appeal info)
- `/api/notifications?q=` — same formal-notice records as messages
- `/api/audit?q=&case_id=` — audit events (control results, owners, SLA)
- `/api/audit/<audit_id>` — single audit event detail
- `/api/attachments/<attachment_id>` — attachment text content (follow from case attachments)

## Step-by-step SOP (endpoint calling order)

1. **Orient.** `GET /api/manifest` + `/api/summary` to confirm the dataset is live and see counts.
2. **Identify the subject entity** from the prompt: an `employee_id` (EMP-###), a `case_id`
   (CASE-### / CASE-RW-###), or an `opening_id` (REQ-###).
3. **Fetch the entity-specific records.**
   - Employee/leave/payroll tasks: `GET /api/employees?q=<id>` (profile) AND
     `GET /api/payroll-ledgers?q=<id>` (leave assignments + salary assignments). Filter the
     ledger by `record_type` ("Leave assignment" vs "Salary assignment") and `status`.
   - Case/folder/notice tasks: `GET /api/cases/<case_id>` for full detail (approvals,
     attachments, comments, audit_events). Then `GET /api/documents` and find the matching
     folder by title/id; `GET /api/messages` (and `/api/notifications`) for the formal notice.
   - Recruitment tasks: `GET /api/recruitment` and select the opening whose `opening_id` matches.
4. **Cross-reference supporting evidence.**
   - `GET /api/audit?q=<case_id>` or `<employee_id>` for control audit events; drill
     `GET /api/audit/<audit_id>` for detail.
   - `GET /api/policies/<policy_id>` for the rule text referenced in `policy_refs`.
   - `GET /api/attachments/<id>` for case attachment text.
5. **Filter client-side if a `q=` query returns empty.** The `q=` filter may not match on
   `employee_id`; when a filtered call returns `[]`, fetch the full list (e.g.
   `GET /api/audit` with no params) and filter locally by `case_id`/`employee_id`.
6. **Apply the business rules below** to pick authoritative records, detect defects, and select
   the audit scope.
7. **Emit normalized enum labels** exactly as spelled in the task's `answer_template.json`
   (lowercase, underscores). Never free-text a value that has an enum equivalent.

### Data-model gotchas
- `/api/payroll-ledgers` is the single source for BOTH leave entitlement and salary. A "Leave
  assignment" record carries the leave policy + days; a "Salary assignment" record carries
  `base_salary`, `effective_date` (use its `updated_at` date, `YYYY-MM-DD`), and
  `accrual_batch_id`. "HRMS leave ledger" and "People Ops adjustment" are NOT the authoritative
  assignment type — only "Leave assignment"/"Salary assignment" `record_type` with Approved or
  Submitted `status` controls.
- `/api/cases/<id>` embeds `audit_events`, `approvals`, `attachments`, `comments` — read it
  before querying the flat audit/messages endpoints.
- `/api/messages` and `/api/notifications` return the identical formal-notice records.

## Business rules (authoritative)

### Leave source precedence — policy LEAVE-SRC-001
- "The latest approved or submitted leave assignment for the period controls. Draft, voided, and
  obsolete records are excluded even when profile summaries conflict."
- An **approved leave assignment overrides a stale employee profile summary** when the ledger,
  policy document, and audit detail confirm the assignment.
- Authoritative fields come from the controlling Approved/Submitted "Leave assignment" record,
  NOT the employee profile: `effective_leave_policy` = the assignment's `policy_name`;
  `annual_days`/`balance_days` = its `approved_leave_days`.
- `leave_source` / `precedence_source` = the assignment-history source, not the profile or case
  summary. `leave_precedence_source` = `approved_assignment_current_period`.
- `profile_policy_ignored` = `true` when the assignment overrides the profile. Audit result
  `profile_summary_stale` => `next_action` = `update_employee_summary`.
- Exclude Superseded/Draft/voided leave records (list them in `excluded_leave_ids` where the
  template has that field).

### Payroll assignment source — policy PAY-SRC-001 (section 3.4)
- "Use the current submitted salary assignment. Draft planning assignments do not affect payroll
  readiness or accrual checks."
- `payroll_source_status` = `submitted`; `draft_exclusion_rule` = `exclude_draft_assignment`.
- `base_salary`, `effective_date` (the `updated_at` date, `YYYY-MM-DD`), and `accrual_batch_id`
  come from the **Submitted** salary assignment. List the draft in `excluded_assignment_id` /
  `excluded_payroll_ids`.
- Accrual readiness: `accrual_ready` = `true` when the submitted assignment matches the accrual
  batch (confirmed by a `payroll.ready` audit event). `control_result` =
  `ready_with_monitoring` when the audit says so.

### Recruiting handoff gate — policy PAY-SRC-001 (section 4.2)
- "Recruiting payroll handoff is created only after a selected candidate has an accepted offer.
  The handoff must be submitted; draft prechecks do not satisfy the assignment gate."
- `draft_payroll_allowed` = `false`. `payroll_handoff_gate` is gated on the accepted offer.
- `onboarding_handoff` = `create_submitted_assignment_after_acceptance` when an accepted offer
  exists and no submitted assignment is present yet.
- `handoff_control_result` = `submitted_handoff_required_after_acceptance`.
- Verify the exact enum intended for `payroll_assignment_status_required` and
  `handoff_control_result` against the template (the `_after_acceptance` suffix appears in some
  enum values; pick the variant consistent with the gate wording).

### Folder readiness — policy POL-DOCS-2026 (section 5.1)
- "A folder is not ready unless all required files and required tags shown in the folder
  checklist are present."
- `folder_ready` = (every `required_files` entry is in `files`) AND (every `required_tags` entry
  is in `tags`).
- `missing_files` = required_files NOT present in files (every one).
- `required_tag_present` = (required_tags subset of tags); `folder_required_tag_action` =
  `add_required_tag` if any required tag is missing, else `no_tag_action`.
- `closeout_blockers` (list, only the ones that apply): `missing_required_files`,
  `missing_required_tags`, `defective_formal_notice`.

### Notice defect detection — policy HR-POL-014 (section 7.1)
- Formal notices must contain: **appeal instructions**, **acknowledgement deadline**, and the
  **correct policy** reference; waitlist notices must also state **waitlist status**.
- Defect enums: `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`.
- `notice_quality` = `valid` if no defects, else `defective`; `notice_defects` = the defect list
  (already provided on the message/notice-packet record).
- Evidence source: for case notices use `/api/messages` => `notice_evidence_source` =
  `message_notice_inspection`. For recruitment, notice packets live inside the
  `/api/recruitment` opening object => `notice_quality_source` =
  `notice_packet_inspection`.

### Approval closeout gate
- Approval is **sufficient** when records are clean (leave + payroll clean AND no folder/notice
  defects) => `approval_closeout_gate` = `approval_sufficient_when_records_clean`.
- Approval is **NOT sufficient** when the folder OR the notice is defective =>
  `approval_not_sufficient_when_folder_or_notice_defective`.
- `final_control_result` / `control_result`:
  - `approve_closeout` — leave + payroll clean and no folder/notice defects.
  - `hold_for_folder_and_notice_defects` — folder or notice defective.
  - `ready_with_monitoring` — payroll assignment ready & matches accrual batch (monitor).
- `next_action`: `approve_onboarding_close` (clean), `block_close_and_reissue_notice` (defective
  notice blocks close), `open_records_remediation` (records to fix), `update_employee_summary`
  (stale profile).

### Audit selection & scope
- Match the audit scope to the task:
  - `leave_source_precedence_only` — include leave audit events; **EXCLUDE adjacent
    document/notice audit events** (e.g. a `folder.tag_missing` event on the same case).
  - `document_notice_findings_only` — include document/notice audit events; exclude adjacent
    leave/payroll events.
  - `payroll_assignment_readiness` — include the payroll audit event.
- `audit_event_id` = the single primary audit event supporting the review.
- `supporting_audit_event_ids` = the audit event(s) that support THIS decision. **Do NOT leave
  it empty when a supporting audit exists** — include the relevant event id(s) (including the
  primary when it is the supporting one for that scope).
- `excluded_audit_event_ids` = adjacent-scope audit events on the same case that must NOT
  influence this decision.
- Cross-module escalation packages (`event: cross_module.escalation_package`) bundle events from
  multiple cases/scopes; do NOT pull their referenced events into a single per-case scope
  decision.

### Escalation owner
- Folder/file defects => `records_remediation_owner` = `Records` (POL-DOCS-2026 owner; folder
  attachments are uploaded by Records).
- Cross-module escalation control owner = `People Ops Compliance`.
- `escalation_action` = `open_records_remediation` for records/folder defects. **This field is
  DISTINCT from `next_action`** — do not duplicate `next_action` into `escalation_action`.
  `next_action` is the case's immediate step (e.g. `block_close_and_reissue_notice` for a
  defective notice); `escalation_action` is the records-remediation escalation.
- `notice_remediation_action` = `reissue_defective_notices` when a notice is defective; else
  `no_notice_action`.

### Cost-summing (recruitment)
- `recruitment_cost_total` = the **sum of ALL line items** in the target opening's `cost_ledger`
  (that opening only — do not include other openings' ledgers). Sum the `amount` field of every
  `cost_ledger` entry.

### Candidate outcomes (recruitment)
- `selected_candidate` = the candidate with `committee_decision` = `Selected` AND an `accepted`
  offer in `offer_register`.
- `waitlisted_candidates` / `rejected_candidates` = the candidate IDs with the matching
  `committee_decision`.
- `candidate_status_source` = `interview_feedback_and_offer`; `candidate_outcome_control` =
  `committee_decision_with_offer_confirmation`.
- `selected_offer_status` = the offer's `status` (`accepted`/`draft`/`withdrawn`/`none`).
- Notice follow-up (from the opening's `notice_packets`):
  - Waitlisted: `send_waitlist_notice` (not sent) / `reissue_waitlist_notice_not_rejection`
    (defective or sent as rejection).
  - Rejected: `send_rejection_notice` (not sent) / `reissue_rejection_notice` (defective).
  - `notice_followup_required` = candidate IDs needing a notice action (send or reissue).
- `offer_exclusion_reason_for_waitlisted` = reason the waitlisted candidate is excluded from the
  offer/handoff. Two readings exist; verify against the offer register: the outcome-based reading
  `waitlisted_not_selected`, and the handoff-gate reading `no_accepted_status_or_offer` (no
  accepted offer => no handoff). Pick the one the template's surrounding fields imply.
- `cost_source` = `recruitment_cost_ledger`.
- Arrays must contain candidate IDs only (no names).

## Exact answer fields by task shape

### Onboarding closeout (leave + payroll setup) — e.g. EMP-104
Fields: `employee_id`, `effective_leave_policy`, `leave_source` (leave_assignment_history |
employee_profile_summary | case_summary_only), `annual_days`, `assignment_id`,
`excluded_leave_ids`, `payroll_assignment_id`, `base_salary`, `payroll_status` (submitted |
draft | superseded), `excluded_payroll_ids`, `closeout_action` (approve_onboarding_close |
block_close_and_reissue_notice | open_records_remediation), `leave_precedence_source`
(approved_assignment_current_period | profile_summary_current_period | case_summary_only),
`payroll_source_status`, `approval_closeout_gate`, `final_control_result`.

### Folder + notice review — e.g. CASE-RW-221
Fields: `case_id`, `final_decision` (approved_with_conditions | approved | rejected | held),
`approval_authority`, `approval_event_id` (the approval_id), `folder_ready`, `missing_files`,
`required_tag_present`, `notice_quality` (valid | defective), `notice_defects` (list[enum]),
`audit_event_id`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, `audit_scope`
(document_notice_findings_only | leave_source_precedence_only | payroll_assignment_readiness),
`next_action`, `approval_closeout_gate`, `closeout_blockers` (list[enum]),
`evidence_source_order` (approval_history_folder_notice_audit | folder_notice_audit | audit_only),
`folder_required_tag_action`, `notice_evidence_source` (notice_packet_inspection |
message_notice_inspection | case_summary_only), `escalation_action`, `records_remediation_owner`
(Records | People Ops Compliance | Payroll QA), `notice_remediation_action`, `final_control_result`.

### Recruitment reconciliation — e.g. REQ-DA-77
Fields: `opening_id`, `selected_candidate`, `waitlisted_candidates`, `rejected_candidates`,
`offer_id`, `offer_base_salary`, `recruitment_cost_total`, `notice_followup_required`,
`onboarding_handoff`, `candidate_status_source`, `candidate_outcome_control`,
`selected_offer_status`, `cost_source`, `notice_quality_source`, `waitlisted_followup_action`,
`rejected_followup_action`, `payroll_handoff_gate`, `payroll_assignment_status_required`,
`draft_payroll_allowed`, `offer_exclusion_reason_for_waitlisted`, `handoff_control_result`.

### Leave source precedence — e.g. EMP-118
Fields: `employee_id`, `effective_leave_policy`, `assignment_id`, `balance_days`,
`precedence_source` (approved_assignment_over_profile | employee_profile_summary |
case_summary_only), `profile_policy_ignored`, `audit_event_id`, `audit_result`
(profile_summary_stale | ready_with_monitoring | block_close), `next_action`
(update_employee_summary | open_records_remediation | no_action), `leave_precedence_source`,
`supporting_audit_event_ids`, `excluded_audit_event_ids`, `audit_scope`.

### Payroll assignment & accrual readiness — e.g. EMP-122
Fields: `employee_id`, `salary_assignment_id`, `base_salary`, `effective_date` (YYYY-MM-DD from
updated_at of the submitted assignment), `excluded_assignment_id`, `accrual_ready`,
`accrual_batch_id`, `audit_event_id`, `control_result` (ready_with_monitoring |
hold_for_folder_and_notice_defects | approve_closeout), `payroll_source_status`,
`draft_exclusion_rule` (exclude_draft_assignment | draft_allowed | exclude_superseded_only),
`audit_scope`.

## Common misjudgments & exclusion rules (learned from low scores)

1. **Empty `supporting_audit_event_ids`.** Leaving it `[]` when a supporting audit event exists
   loses points. Always list the audit event id(s) that support the decision (including the
   primary one for that scope).
2. **`escalation_action` duplicated as `next_action`.** They are distinct fields. For a
   folder-defect + notice-defect case: `next_action` = `block_close_and_reissue_notice` (the
   case's immediate step), `escalation_action` = `open_records_remediation` (escalate the
   folder/file issue to Records). Setting `escalation_action` = `block_close_and_reissue_notice`
   was confirmed WRONG and lowered the score.
3. **Using draft / superseded / obsolete records as authoritative.** Only Approved or Submitted
   "Leave assignment"/"Salary assignment" records control. Exclude drafts and superseded records
   in the `excluded_*` fields.
4. **Trusting the employee profile summary over the approved assignment.** When the profile is
   stale (audit says `profile_summary_stale`), `profile_policy_ignored` = `true` and the
   assignment's policy/days win.
5. **Counting a folder ready when files or tags are missing.** `folder_ready` requires ALL
   required_files AND ALL required_tags. List every absent required file in `missing_files`.
6. **Pulling adjacent-scope audit events into a narrow-scope decision.** For a leave-scope
   decision, exclude the document/notice audit (e.g. `folder.tag_missing`); for a document/notice
   decision, exclude leave/payroll audits. Cross-module escalation-package referenced events do
   not belong in a per-case scope decision.
7. **Summing cost ledgers across openings.** `recruitment_cost_total` is only the target
   opening's `cost_ledger` sum.
8. **Payroll handoff for non-selected / non-accepted candidates.** The handoff requires an
   accepted offer from the SELECTED candidate only; waitlisted/rejected candidates get notice
   follow-up, not a payroll assignment.
9. **`effective_date` as a period string.** Use the assignment's effective date `YYYY-MM-DD`
   (from `updated_at`), not the `period` (`YYYY-MM`).
10. **Recruitment handoff enum certainty.** The `_after_acceptance` variants exist for several
    payroll-handoff fields; confirm which variant each field expects against the template and
    the policy wording rather than assuming all fields take the suffixed form.

## Pre-submission checklist

- [ ] Every answer field from the template is present; no extra/missing fields.
- [ ] All enum values spelled EXACTLY as in `answer_template.json` (lowercase, underscores).
- [ ] **Leave/payroll:** the approved/submitted assignment is the source; drafts/superseded are
      excluded and listed in `excluded_*_ids`; `base_salary`/`effective_leave_policy`/`annual_days`
      come from the controlling assignment.
- [ ] **Folder:** `folder_ready`, `missing_files` (all absent required files),
      `required_tag_present`, `folder_required_tag_action` are mutually consistent.
- [ ] **Notice:** `notice_quality` + `notice_defects` taken from `/api/messages` (case) or the
      opening's `notice_packets` (recruitment); each required component checked
      (ack deadline, appeal instructions, waitlist status, correct policy).
- [ ] **Audit:** `audit_event_id` set; `supporting_audit_event_ids` non-empty when a supporting
      audit exists; `excluded_audit_event_ids` lists only adjacent-scope events;
      `audit_scope` matches the task.
- [ ] **Closeout:** `approval_closeout_gate`, `closeout_blockers`, `final_control_result`, and
      `next_action` are consistent with the defects found.
- [ ] **Escalation:** `records_remediation_owner`, `escalation_action` (≠ `next_action`),
      `notice_remediation_action` all set and distinct.
- [ ] **Recruitment:** arrays contain candidate IDs only; `recruitment_cost_total` = sum of that
      opening's `cost_ledger`; `selected_candidate` has an accepted offer; offer/handoff fields
      consistent with the accepted-offer gate; `draft_payroll_allowed` = false.
- [ ] **Leave precedence:** `precedence_source`/`leave_precedence_source` = the assignment
      source; `profile_policy_ignored` correct; adjacent document/notice audit excluded.
- [ ] JSON is valid; no markdown or explanatory text around it; boolean and number types correct.
