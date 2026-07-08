# SKILL: Northwind PeopleOps Console — HR Employee-Lifecycle Verification

## When to use

Use this skill for any task that asks you to verify, reconcile, or close out a
PeopleOps employee-lifecycle record in the Northwind "People Lifecycle Portal".
This covers five recurring archetypes:

1. **Onboarding closeout** — verify an employee's effective leave setup +
   payroll setup, then approve or block onboarding close (e.g. "verify final
   onboarding closeout for EMP-XXX").
2. **Policy-case folder + formal-notice review** — review a policy case
   (remote-work exception, etc.) for folder readiness and formal notice quality,
   then decide approval/block (e.g. "Review CASE-RW-XXX for folder readiness and
   formal notice quality").
3. **Recruitment reconciliation** — reconcile a recruitment opening's candidate
   outcomes, offer register, cost ledger, and notice packets (e.g. "Reconcile
   the recruitment outcome packet for REQ-XXX").
4. **Leave source precedence** — determine which leave policy/balance is
   authoritative when the employee profile summary conflicts with an approved
   assignment (e.g. "validate leave source precedence for EMP-XXX").
5. **Payroll assignment + accrual readiness** — validate the submitted salary
   assignment and whether an accrual batch is ready (e.g. "inspect payroll
   assignment and accrual readiness for EMP-XXX").

If the prompt mentions PeopleOps Console, login `ops.lead@peopleops.local` /
`PeopleOps#2026`, an `http://127.0.0.1:<port>/` solver URL, employees
`EMP-XXX`, cases `CASE-XXX`, openings `REQ-XXX`, or asks for a JSON answer
matching an `answer_template.json` — this is the skill.

## Environment mechanics (read first)

- The "local" solver URL and login in the prompt are **illustrative**. The real
  environment is the **remote** console:
  - Web UI: `<remote-env-url>/`
  - JSON API base: `<remote-env-url>` (read-only, **no authentication**)
  - Health check: `GET <remote-env-url>/health` → `{"ok": true, ...}`
- All API calls are plain `GET`. No auth header, no login step. The prompt's
  `127.0.0.1:<port>` and credentials point at THIS remote host — substitute
  `<remote-env-url>` everywhere.
- Always fetch with `curl -s` and pipe to `python3 -m json.tool` for readability.
- `?q=<keyword>` searches across fields (employee id, name, case id, candidate
  id, subject, body, etc.). `?status=` / `?type=` / `?case_id=` filter where
  relevant. Searching by the literal ID token (e.g. `?q=EMP-104`) is the most
  reliable lookup.

### Available endpoints (GET)

| Endpoint | Returns | Use for |
|---|---|---|
| `/api/manifest` | module/endpoint map, dataset seed | sanity check counts |
| `/api/summary` | live record counts + departments | orientation |
| `/api/employees?q=` | employee **profile summary** (leave_balance_days, salary_band, status, hire_date, manager) | the "stale" profile to compare against |
| `/api/cases?q=` | case summaries | find the case for an employee/opening |
| `/api/cases/<case_id>` | **FULL** case (approvals[], attachments[] with content, comments[], audit_events[]) | primary evidence for folder/notice/approval |
| `/api/policies` and `/api/policies/<id>` | policy definitions + sections | authoritative business rules |
| `/api/payroll-ledgers?q=` | **leave assignments AND salary assignments** ledger history | authoritative leave + payroll records |
| `/api/recruitment?q=` | opening: candidates[], offer_register[], cost_ledger[], notice_packets[], payroll_precheck_records[] | recruitment reconciliation |
| `/api/documents?q=` | lifecycle folders (ready, required_files, files, required_tags, tags) | folder readiness |
| `/api/messages?q=` | formal notice messages (quality, defects[], ack deadline, appeal info) | formal notice quality |
| `/api/notifications?q=` | notifications (ack deadlines, appeal instructions) | secondary notice evidence |
| `/api/audit?q=` and `?case_id=` | audit events (event type, actor, detail, owner, timestamp) | control result + scope selection |
| `/api/audit/<audit_id>` | single audit event detail | confirm one event |
| `/api/attachments/<id>` | attachment text content | rarely needed; case full detail already embeds attachment `content` |

## Standard investigation SOP (endpoint calling order)

For ANY task, run this base sequence first, then branch by archetype.

1. **Read the prompt + `answer_template.json` first.** Enumerate every output
   field and its `allowed_values`. You will ONLY emit values from those enums —
   never free-text. The template IS the contract.
2. **Health check** (optional): `curl -s <remote-env-url>/health`.
3. **Extract IDs** from the prompt (employee id `EMP-XXX`, case id `CASE-XXX`,
   opening id `REQ-XXX`). These become your `?q=` terms.
4. **Fetch the employee profile summary**: `GET /api/employees?q=<EMP-XXX>`.
   Record `leave_balance_days`, `salary_band`, `status`, `hire_date`. This is
   the *profile* view — often stale; do NOT treat it as authoritative yet.
5. **Fetch the ledger/assignment history**: `GET /api/payroll-ledgers?q=<EMP-XXX>`.
   This single endpoint returns BOTH `record_type: "Leave assignment"` and
   `record_type: "Salary assignment"` rows. Each row has `status`
   (Approved/Submitted/Draft/Superseded), `ledger_id`, `policy_name` /
   `base_salary`, `period`, `accrual_batch_id`.
6. **Find the case(s)**: `GET /api/cases?q=<EMP-XXX>` (and `?q=<CASE-XXX>` if a
   case id was given).
7. **Fetch FULL case detail**: `GET /api/cases/<case_id>`. This carries
   `approvals[]`, `attachments[]` (with embedded `content`), `comments[]`, and
   `audit_events[]`. This is your richest single source.
8. **Branch by archetype** (see sections below) for documents, messages,
   recruitment, and audit-specific fetches.
9. **Fetch policies**: `GET /api/policies` to confirm the controlling rule
   (leave precedence, payroll source, folder checklist, remote-work notice
   requirements). Cite the policy section that justifies each exclusion.
10. **Map every answer field** to a concrete record value (an ID, a status
    string, a number). If a field has no evidence, prefer the "clean/none/
    no_action" enum — do not invent.

### Branch A — Onboarding closeout (leave + payroll)

After the base sequence:
- Determine the **authoritative leave assignment**: among the
  `record_type: "Leave assignment"` rows, pick the one whose `status` is
  `Approved` (preferred) or `Submitted`, with the latest `updated_at` for the
  target `period` (2026). That row's `policy_name` = effective leave policy,
  `approved_leave_days` = annual days, `ledger_id` = assignment id.
- **Excluded leave ids** = every other leave-assignment row for that period:
  `Superseded` and `Draft` rows are ALWAYS excluded (LEAVE-SRC-001 §2.1).
- Determine the **authoritative payroll**: among `record_type: "Salary
  assignment"` rows, pick `status: "Submitted"`. Its `base_salary` and
  `ledger_id` are authoritative. `Draft` salary rows are excluded
  (PAY-SRC-001 §3.4).
- **Closeout gate**: check whether the employee has a case / document folder /
  formal notice with defects (run Branch B checks). If no case/doc/notice/audit
  exists for the employee, records are "clean".
  - clean + authoritative records → `closeout_action: approve_onboarding_close`,
    `approval_closeout_gate: approval_sufficient_when_records_clean`,
    `final_control_result: approve_closeout`.
  - folder or notice defective → `closeout_action:
    block_close_and_reissue_notice` (or `open_records_remediation` if only
    records/files are wrong), `final_control_result:
    hold_for_folder_and_notice_defects`, gate
    `approval_not_sufficient_when_folder_or_notice_defective`.
- Source labels: `leave_source: leave_assignment_history`,
  `leave_precedence_source: approved_assignment_current_period`,
  `payroll_source_status: submitted`.

### Branch B — Policy-case folder + formal-notice review

For a given `CASE-XXX`:
- `GET /api/cases/<CASE-XXX>` → read `approvals[]` (approver + decision +
  approval_id), `attachments[]` (folder-checklist content), `audit_events[]`.
- `GET /api/documents?q=<EMP or CASE or title>` → match the folder.
  `folder_ready = document.ready`. `missing_files = required_files - files`.
  `required_tag_present = (required_tags ⊆ tags)`.
- `GET /api/messages?q=<EMP or CASE>` → the formal decision message.
  `notice_quality = message.quality` ("valid"/"defective").
  `notice_defects = message.defects[]` (already enumerated by the API).
- `GET /api/audit?case_id=<CASE-XXX>` → pick the audit event whose `event`
  matches the scope: `notice.defect` or `folder.*` for document/notice
  findings.
- Decision mapping:
  - approval decision "Approved" + any folder/notice defect →
    `final_decision: approved_with_conditions` (or `held`), `next_action:
    block_close_and_reissue_notice`.
  - folder tag missing but files present → `folder_required_tag_action:
    add_required_tag`; tag present → `no_tag_action`.
  - notice defective → `notice_remediation_action: reissue_defective_notices`;
    clean → `no_notice_action`.
  - `closeout_blockers` = union of `missing_required_files`,
    `missing_required_tags`, `defective_formal_notice` — only list the ones that
    actually apply (do NOT list tags if the tag is present).
  - `evidence_source_order: approval_history_folder_notice_audit` when you used
    approvals + folder + notice + audit; `folder_notice_audit` if no approval
    history; `audit_only` if only audit exists.
  - `notice_evidence_source: message_notice_inspection` for formal decision
    messages from `/api/messages`; `notice_packet_inspection` for recruitment
    notice packets from `/api/recruitment`; `case_summary_only` only as a
    last resort.
  - `records_remediation_owner`: `Records` for missing folder files/tags;
    `People Ops Compliance` for notice/policy defects; `Payroll QA` for payroll.
  - `escalation_action: block_close_and_reissue_notice` when both folder and
    notice are defective; `open_records_remediation` when only records;
    `no_action` when clean.
  - `final_control_result: hold_for_folder_and_notice_defects` when any blocker;
    `approve_closeout` when clean.

### Branch C — Recruitment reconciliation

`GET /api/recruitment?q=<REQ-XXX>` returns one opening object with sub-arrays.
- **Candidates**: for each `candidates[]` row, `committee_decision` ∈ {Selected,
  Waitlisted, Rejected}. Bucket candidate ids accordingly:
  - `selected_candidate` = the Selected one **confirmed** by an entry in
    `offer_register[]` with `status: "accepted"`.
  - `waitlisted_candidates[]`, `rejected_candidates[]` = the rest.
- **Offer**: from `offer_register[]` matching the selected candidate:
  `offer_id`, `offer_base_salary`, `selected_offer_status` = offer `status`
  (accepted/draft/withdrawn/none).
- **Cost**: `recruitment_cost_total` = **sum of every `amount` in
  `cost_ledger[]`** (all line items, regardless of label). `cost_source:
  recruitment_cost_ledger`. Never use the case summary's cost figure if it
  differs from the ledger sum.
- **Notice follow-up**: `notice_packets[]` lists each non-selected candidate's
  required notice. `notice_followup_required[]` = candidate ids whose
  `status: "not_sent"`.
  - waitlisted + not_sent → `waitlisted_followup_action: send_waitlist_notice`.
  - rejected + not_sent → `rejected_followup_action: send_rejection_notice`.
  - If a waitlist notice was sent but is mislabeled/missing the waitlist status
    → `reissue_waitlist_notice_not_rejection`.
- **Payroll handoff** (PAY-SRC-001 §4.2): handoff is created ONLY after the
  selected candidate has an **accepted** offer; the handoff must be
  **submitted** (draft prechecks do NOT satisfy the gate).
  - offer accepted → `onboarding_handoff:
    create_submitted_assignment_after_acceptance`,
    `payroll_handoff_gate: accepted_offer_and_submitted_assignment`,
    `payroll_assignment_status_required: submitted_after_acceptance`,
    `draft_payroll_allowed: false`,
    `handoff_control_result: submitted_handoff_required_after_acceptance`.
  - no accepted offer → `onboarding_handoff: no_payroll_handoff`,
    `handoff_control_result: no_handoff_required`.
- Source labels: `candidate_status_source: interview_feedback_and_offer`,
  `candidate_outcome_control: committee_decision_with_offer_confirmation`,
  `notice_quality_source: notice_packet_inspection`,
  `offer_exclusion_reason_for_waitlisted: waitlisted_not_selected`.
- Arrays contain **candidate IDs only** (e.g. `CAND-DA-7701`), never names.

### Branch D — Leave source precedence

- Profile summary (`/api/employees`) gives `leave_balance_days` + an implied
  policy. The **approved leave assignment** in `/api/payroll-ledgers`
  (`record_type: "Leave assignment"`, `status: "Approved"`) is authoritative
  per LEAVE-SRC-001 §2.1.
- Apply precedence: an approved assignment **overrides** a stale profile
  summary when the ledger, policy document, and audit detail confirm it.
  - `precedence_source: approved_assignment_over_profile`,
    `leave_precedence_source: approved_assignment_current_period`,
    `profile_policy_ignored: true`,
    `effective_leave_policy` = assignment `policy_name`,
    `assignment_id` / `balance_days` = assignment `ledger_id` /
    `approved_leave_days`.
- **Audit selection**: include only `leave.*` audit events in the leave-scope
  decision (`supporting_audit_event_ids`). EXCLUDE adjacent `folder.*`,
  `notice.defect`, `payroll.*`, and `cross_module.*` events
  (`excluded_audit_event_ids`). `audit_scope:
  leave_source_precedence_only`.
- `audit_result`: echo the QA result in the audit `detail`
  (`profile_summary_stale` / `ready_with_monitoring` / `block_close`).
- `next_action: update_employee_summary` when the profile is stale but the
  assignment is clean; `open_records_remediation` when records are broken;
  `no_action` when already aligned.

### Branch E — Payroll assignment + accrual readiness

- Among `record_type: "Salary assignment"` rows, pick `status: "Submitted"`
  → `salary_assignment_id`, `base_salary`. `excluded_assignment_id` = the
  `Draft` row. `effective_date` = the assignment `period` start (e.g. period
  `2026-04` → `2026-04-01`; cross-check `updated_at`/`hire_date`).
- `accrual_ready`: read the `payroll.ready` audit event. If its `detail` says
  `ready_with_monitoring` and the submitted assignment `accrual_batch_id`
  matches the batch → `accrual_ready: true`, `accrual_batch_id` from the
  assignment row, `audit_event_id` = that audit id, `control_result:
  ready_with_monitoring`.
- `payroll_source_status: submitted`,
  `draft_exclusion_rule: exclude_draft_assignment`,
  `audit_scope: payroll_assignment_readiness`.

## Business rules (derived from the policy documents)

Fetch `/api/policies` and treat these as authoritative:

### LEAVE-SRC-001 — Leave Source Precedence (owner: People Ops)
> "The latest approved or submitted leave assignment for the period controls.
> Draft, voided, and obsolete records are excluded even when profile summaries
> conflict."

- Precedence order: **approved/submitted assignment > profile summary > case
  summary only**.
- Excluded leave ids = all `Draft`, `Superseded`/`Voided`, and obsolete
  assignment rows for the period — **even if** their day count matches or the
  profile disagrees.

### PAY-SRC-001 — Payroll Assignment Source (owner: Payroll)
> "Use the current submitted salary assignment. Draft planning assignments do
> not affect payroll readiness or accrual checks." AND "Recruiting payroll
> handoff is created only after a selected candidate has an accepted offer. The
> handoff must be submitted; draft prechecks do not satisfy the assignment
> gate."

- Submitted salary assignment controls `base_salary`. Drafts excluded from
  payroll readiness + accrual.
- Recruiting handoff: accepted offer required, AND the resulting assignment
  must be `submitted` (never draft).

### POL-DOCS-2026 — Lifecycle Folder Checklist (owner: Records)
> "A folder is not ready unless all required files and required tags shown in
> the folder checklist are present."

- `folder_ready = false` if ANY required file missing OR ANY required tag
  missing.
- `missing_files = required_files - files`; missing tags drive
  `folder_required_tag_action: add_required_tag`.

### HR-POL-014 — Remote Work Policy §7.1 (owner: Legal Desk)
> International exceptions require "executive approval, time limits, tax
> equalization, VPN-only access, quarterly compliance review, appeal
> instructions, and acknowledgement deadline in the formal notice."

- A formal notice is **defective** unless it contains BOTH appeal instructions
  AND an acknowledgement deadline (plus the other elements). The
  `/api/messages` `defects[]` array enumerates exactly which are missing.
- Folder must also contain the tax-equalization agreement file for exception
  cases.

## Audit selection & scope rules

Audit events carry an `event` type. Scope your decision to the matching events
and **exclude adjacent ones**:

| `event` prefix/type | belongs to scope |
|---|---|
| `leave.*` (e.g. `leave.profile_mismatch`) | `leave_source_precedence_only` |
| `notice.defect` | `document_notice_findings_only` |
| `folder.*` (e.g. `folder.tag_missing`) | `document_notice_findings_only` |
| `payroll.*` (e.g. `payroll.ready`, `payroll.draft_excluded`) | `payroll_assignment_readiness` |
| `case.close_blocked` | the relevant defect scope (folder/notice) |
| `cross_module.escalation_package` | NONE — exclude from every single-scope decision |

- `supporting_audit_event_ids` = in-scope events for THIS decision.
- `excluded_audit_event_ids` = out-of-scope events present on the same case
  (e.g. a `folder.tag_missing` event is excluded from a leave-scope decision).
- `audit_event_id` (singular) = the single primary event the decision rests on.
- `audit_result`: read the literal QA result phrase from the audit `detail`
  (`profile_summary_stale`, `ready_with_monitoring`, `block_close`).

## Candidate outcome & cost rules

- Outcomes come from `committee_decision` in `candidates[]`, **confirmed** by
  the `offer_register[]` for the selected candidate. `candidate_outcome_control:
  committee_decision_with_offer_confirmation`.
- `selected_offer_status` = the offer_register `status` for the selected
  candidate (`accepted` / `draft` / `withdrawn` / `none`).
- `offer_exclusion_reason_for_waitlisted: waitlisted_not_selected` (waitlisted
  candidates never get an offer id).
- `recruitment_cost_total` = **Σ all `cost_ledger[].amount`**. Sum every line;
  do not cherry-pick by label. `cost_source: recruitment_cost_ledger`.
- Arrays (waitlisted/rejected/notice_followup) hold **candidate IDs only**.

## Common misjudgments & exclusion rules

- **Don't trust the employee profile summary as authoritative.** It is
  frequently stale. The approved/submitted assignment in `/api/payroll-ledgers`
  wins (LEAVE-SRC-001). A matching number does NOT prove alignment — the policy
  name and audit must confirm.
- **Don't mix salary + leave rows.** `/api/payroll-ledgers` returns both
  `record_type` values in one list. Filter by `record_type` before deciding.
- **Don't include Draft/Superseded records** in the authoritative answer.
  Always list them in `excluded_*_ids`. Draft salary rows do not affect accrual
  readiness.
- **Don't list a tag blocker when the tag is present.** Compare
  `required_tags` ⊆ `tags` precisely. Only emit `missing_required_tags` in
  `closeout_blockers` if a required tag is actually missing.
- **Don't conflate notice defects.** Use the exact `defects[]` from
  `/api/messages`. A present ack deadline means `missing_ack_deadline` does NOT
  apply. Defect enum: `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`.
- **Don't include adjacent-scope audit events** in a single-scope decision.
  Exclude `folder.*`/`notice.defect` from leave scope; exclude `leave.*`/`payroll.*`
  from document/notice scope.
- **Don't route a payroll handoff before offer acceptance.** Draft prechecks
  never satisfy the gate. `draft_payroll_allowed: false`.
- **Don't sum cost from the case summary.** Always sum the `cost_ledger[]`
  amounts directly.
- **Don't put candidate names in arrays.** IDs only.
- **Don't free-text enums.** Every enum field must be a string copied verbatim
  from the task's `answer_template.json` `allowed_values`.
- **Don't treat an "Approved" case as closeable.** Approval is necessary but
  not sufficient: a folder or notice defect blocks closeout
  (`approval_closeout_gate: approval_not_sufficient_when_folder_or_notice_defective`).
- **Don't read test/train gold answers.** Solve only from the live read-only
  API + policies. Use only the documented read-only endpoints for evidence.

## Exact answer fields (per archetype) — what each field must be

**Onboarding closeout**: `employee_id`; `effective_leave_policy` (assignment
policy_name); `leave_source`; `annual_days`; `assignment_id`; `excluded_leave_ids`;
`payroll_assignment_id`; `base_salary`; `payroll_status`; `excluded_payroll_ids`;
`closeout_action`; `leave_precedence_source`; `payroll_source_status`;
`approval_closeout_gate`; `final_control_result`.

**Policy-case review**: `case_id`; `final_decision`; `approval_authority`
(approver); `approval_event_id` (approval_id); `folder_ready`; `missing_files`;
`required_tag_present`; `notice_quality`; `notice_defects[]`; `audit_event_id`;
`supporting_audit_event_ids[]`; `excluded_audit_event_ids[]`; `audit_scope`;
`next_action`; `approval_closeout_gate`; `closeout_blockers[]`;
`evidence_source_order`; `folder_required_tag_action`; `notice_evidence_source`;
`escalation_action`; `records_remediation_owner`; `notice_remediation_action`;
`final_control_result`.

**Recruitment**: `opening_id`; `selected_candidate`; `waitlisted_candidates[]`;
`rejected_candidates[]`; `offer_id`; `offer_base_salary`;
`recruitment_cost_total`; `notice_followup_required[]`; `onboarding_handoff`;
`candidate_status_source`; `candidate_outcome_control`; `selected_offer_status`;
`cost_source`; `notice_quality_source`; `waitlisted_followup_action`;
`rejected_followup_action`; `payroll_handoff_gate`;
`payroll_assignment_status_required`; `draft_payroll_allowed` (bool);
`offer_exclusion_reason_for_waitlisted`; `handoff_control_result`.

**Leave precedence**: `employee_id`; `effective_leave_policy`; `assignment_id`;
`balance_days`; `precedence_source`; `profile_policy_ignored` (bool);
`audit_event_id`; `audit_result`; `next_action`; `leave_precedence_source`;
`supporting_audit_event_ids[]`; `excluded_audit_event_ids[]`; `audit_scope`.

**Payroll accrual**: `employee_id`; `salary_assignment_id`; `base_salary`;
`effective_date`; `excluded_assignment_id`; `accrual_ready` (bool);
`accrual_batch_id`; `audit_event_id`; `control_result`; `payroll_source_status`;
`draft_exclusion_rule`; `audit_scope`.

## Pre-submission checklist

Before emitting the JSON answer, verify each item:

1. **Shape** — the JSON matches `answer_template.json` field-for-field (no extra
   keys, no missing keys, correct types: string/int/number/bool/list).
2. **Enums exact** — every enum value is copied verbatim from the template's
   `allowed_values`; no synonyms, no casing changes, no free-text.
3. **Authoritative source chosen** — leave answer comes from the
   approved/submitted assignment (not the profile); payroll from the submitted
   assignment (not draft).
4. **Exclusions listed** — all Draft/Superseded leave + payroll IDs appear in
   the `excluded_*_ids` lists; none leak into the authoritative fields.
5. **Folder + notice checked** for the closeout gate — `folder_ready`,
   `missing_files`, `required_tag_present`, `notice_quality`, `notice_defects`
   all reflect the actual `/api/documents` + `/api/messages` evidence, not the
   case summary blurb.
6. **Audit scope clean** — `supporting_audit_event_ids` contains only in-scope
   events; adjacent-scope (and any `cross_module.*`) events are in
   `excluded_audit_event_ids`.
7. **Cost summed** — `recruitment_cost_total` equals the literal sum of every
   `cost_ledger[].amount` (re-add to confirm).
8. **Arrays are IDs** — candidate/waitlist/reject/notice arrays contain IDs,
   not names; empty arrays `[]` when nothing applies (do not omit the key).
9. **Control result consistent** — if any blocker exists, `final_control_result`
  is `hold_for_folder_and_notice_defects` and the gate is
  `approval_not_sufficient_when_folder_or_notice_defective`; if records are
  clean, it is `approve_closeout` with `approval_sufficient_when_records_clean`.
10. **No gold, no internal access** — nothing references evaluator
    internals or unseen answer keys; all evidence is traceable to a `GET` on
    the remote read-only API.
