# SKILL: People Ops Employee-Lifecycle Reconciliation (Remote Console API)

Executable SOP for reconciling HR employee-lifecycle records against the live,
read-only PeopleOps console JSON API. SELF-derived: no gold answers or judge
feedback were used; every rule below was reasoned out from the live API +
active policy documents.

## When to use
Use whenever a task points at the PeopleOps console and asks you to
verify / reconcile / close out an HR lifecycle record, returning a JSON object
whose fields are *normalized business labels* (enums). The task will name one of:
- an employee ID `EMP-###` (onboarding closeout, leave-source precedence,
  payroll/accrual readiness), or
- a case ID `CASE-###` / `REQ-###` / `XMODULE-###` (policy-case folder + formal
  notice review, recruitment reconciliation), or
- an opening ID `REQ-###`.

The five recurring archetypes this skill covers:
1. Onboarding closeout — leave setup + payroll setup verification.
2. Policy-case folder readiness + formal-notice quality (remote-work exception etc.).
3. Recruitment packet reconciliation (candidate outcomes, cost, notices, handoff).
4. Leave-source precedence (approved assignment vs stale profile summary).
5. Payroll-assignment + accrual-readiness validation.

## Environment
- Remote read-only JSON API, **no auth**: base `<remote-env-url>`
- Web UI: `<remote-env-url>/`
- Data is deterministic (manifest seed 12012). GET only; never POST/PUT.
- Invoke: `curl -s <remote-env-url>/api/<endpoint> | python3 -m json.tool`
- Pipe through `python3 -c` to filter large lists (e.g. `if e['employee_id']=='EMP-122'`).

### Endpoints (and what each is good for)
| Endpoint | Records | Use for |
|---|---|---|
| `/api/manifest` | meta | counts, modules, seed |
| `/api/summary` | meta | entity counts, cases_by_status, departments |
| `/api/employees` | 44 | profile: department, leave_balance_days, salary_band, status, manager, remote_profile (NOTE: profile has salary_band only, never a base_salary number) |
| `/api/cases` | 7 (list) | locate case by employee_id / case_id; summary hint |
| `/api/cases/<id>` | full | **authoritative case source**: approvals[], attachments[] (with content), audit_events[], comments[], policy_refs |
| `/api/payroll-ledgers` | 61 | leave + salary assignments + HRMS/adjustment ledgers, by employee_id |
| `/api/policies` | 4 | controlling rule text (HR-POL-014, LEAVE-SRC-001, PAY-SRC-001, POL-DOCS-2026) |
| `/api/documents` | 4 | folder readiness: files vs required_files, tags vs required_tags, ready |
| `/api/messages` | 4 | formal-case notices: defects[], quality, status, by case_id |
| `/api/notifications` | 4 | duplicates of messages (cross-check only) |
| `/api/recruitment` | 2 | openings: candidates, offer_register, cost_ledger, notice_packets, payroll_precheck_records |
| `/api/audit` | 8 | all audit events; partition by scope |
| `/api/audit/<id>` | 1 | single event (same fields as list — per-id adds nothing extra) |
| `/api/attachments/<id>` | — | **unreliable/empty in this build**; read attachments via `/api/cases/<id>.attachments[].content` instead |

### payroll-ledgers record_type cheat sheet
`record_type` values and what they mean:
- `"Leave assignment"` — leave entitlement records. Fields: `ledger_id`, `policy_name`, `approved_leave_days`, `worksheet_leave_days`, `status` (Approved/Superseded/Draft), `period`. **Authoritative = Approved.**
- `"Salary assignment"` — payroll salary records. Fields: `ledger_id`, `base_salary`, `period`, `accrual_batch_id` (when present), `status` (Submitted/Draft). **Authoritative = Submitted.**
- `"HRMS leave ledger"` / `"People Ops adjustment"` — secondary leave ledgers; treat as non-authoritative supporting evidence unless an audit explicitly elevates one.

## Endpoint calling order (the SOP, in sequence)
1. `GET /api/summary` — orient (entity counts, case statuses, departments).
2. `GET /api/employees` — resolve the named `EMP-###`; capture profile (department, leave_balance_days, salary_band, status) for later *conflict* checks (the profile is often stale or lacks a salary number).
3. `GET /api/cases` — locate the case(s) for that employee / opening (`employee_id` match, or `case_id`/`opening_id` from the prompt).
4. `GET /api/cases/<id>` — pull full detail: `approvals[]`, `attachments[]` (folder-checklist `content`), embedded `audit_events[]`, `comments[]`, `policy_refs`, `summary`. The `summary` is a *hint*, never the answer.
5. `GET /api/payroll-ledgers` — filter by `employee_id`; bucket by `record_type`+`status`. Choose the authoritative Approved (leave) / Submitted (salary) record; collect Draft + Superseded records for the exclusion lists.
6. `GET /api/policies` — read **every** `policy_id` listed in the case's `policy_refs`; the section bodies contain the controlling rules (see Business Rules). This is the single most important step for the enum/source fields.
7. `GET /api/documents` — match the folder `document_id` (referenced in case attachments, e.g. `DOC-RW-221`); compute `folder_ready = (required_files ⊆ files) AND (required_tags ⊆ tags)`; derive `missing_files` and `required_tag_present`.
8. `GET /api/messages` (then `/api/notifications` to confirm) — for the `case_id`: read the formal-notice `defects[]` and `quality`. This is the notice-quality evidence for **lifecycle cases**.
9. For `REQ-*` openings: `GET /api/recruitment` — pull `candidates[]`, `offer_register[]`, `cost_ledger[]`, `notice_packets[]`, `payroll_precheck_records[]`, `status`. Note the optional per-opening `audit_event_id`.
10. `GET /api/audit` — list all events; select by `event` type + `case_id`/`employee_id`. Partition into **supporting** (in-scope) vs **excluded** (adjacent, out-of-scope). Use `/api/audit/<id>` only if you need one event isolated.
11. (Skip) `/api/attachments/<id>` — unreliable; use step 4's attachment content.

## Field definitions — where each answer field comes from
- `employee_id` / `opening_id` / `case_id` — copy verbatim, case-sensitive (hyphens and trailing segment letters like `-SUB-03`, `-APP-02` matter).
- `effective_leave_policy` — `policy_name` of the authoritative **Approved leave assignment** (never the profile, never a stale case summary).
- `annual_days` / `balance_days` — `approved_leave_days` of the authoritative leave assignment (NOT `worksheet_leave_days`, NOT `profile.leave_balance_days`).
- `assignment_id` (leave) — `ledger_id` of the authoritative Approved leave assignment.
- `excluded_leave_ids` — `ledger_id` of every OTHER leave assignment (Superseded + Draft). Never include the chosen authoritative one.
- `payroll_assignment_id` / `salary_assignment_id` — `ledger_id` of the authoritative **Submitted salary assignment**.
- `base_salary` — `base_salary` of the Submitted salary assignment (profile has only `salary_band`, never a salary number).
- `effective_date` — the salary assignment's `period` string (e.g. `"2026-04"`) representing the effective period.
- `payroll_status` / `payroll_source_status` — `"submitted"` (the Submitted assignment's status mapped to the enum label).
- `excluded_payroll_ids` / `excluded_assignment_id` — the Draft (and any Superseded) salary-assignment `ledger_id`(s).
- `accrual_batch_id` — `accrual_batch_id` on the Submitted salary assignment ledger.
- `accrual_ready` — true when a Submitted assignment exists AND an audit `payroll.ready` event confirms it matches the accrual batch; else false.
- `folder_ready` — computed from `/api/documents` (all `required_files` present AND all `required_tags` present).
- `missing_files` — `required_files` minus `files` (filenames).
- `required_tag_present` — `required_tags` ⊆ `tags`.
- `notice_quality` — `"defective"` if the matching message has any `defects[]`, else `"valid"`.
- `notice_defects` — the message's `defects[]`, each from the allowed enum (`missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status`, `missing_correct_policy`).
- `audit_event_id` — the single in-scope audit event id driving the result.
- `supporting_audit_event_ids` — all in-scope audit event ids.
- `excluded_audit_event_ids` — adjacent audit event ids that belong to a DIFFERENT scope (e.g. a `folder.tag_missing` event when the task is leave-precedence).
- `audit_scope` — the task's scope: `leave_source_precedence_only` | `document_notice_findings_only` | `payroll_assignment_readiness`.
- `approval_event_id` / `approval_authority` / `final_decision` — from `/api/cases/<id>.approvals[]`: the **Final approval** step's `approval_id`, `approver`, `decision`. Map decision `"Approved"` + note `"Approved with conditions"` → `approved_with_conditions`.
- `recruitment_cost_total` — Σ of ALL `cost_ledger[].amount` for the opening (every line, no exclusions, no per-candidate filtering). `cost_source` = `recruitment_cost_ledger`.
- `selected_candidate` / `waitlisted_candidates` / `rejected_candidates` — `candidate_id` partitioned by `committee_decision` (Selected/Waitlisted/Rejected).
- `offer_id` / `offer_base_salary` / `selected_offer_status` — from `offer_register[]` for the Selected candidate's offer (`offer_id`, `base_salary`, `status`).

## Business rules (derived from the active policies + audit behavior)
1. **LEAVE-SRC-001 §2.1 — Leave Source Precedence.** The latest Approved or Submitted leave assignment for the period CONTROLS. Draft, voided, and obsolete (Superseded) records are EXCLUDED even when the employee profile summary conflicts. An approved assignment overrides a stale profile summary. → `leave_source = leave_assignment_history`; `precedence_source = approved_assignment_over_profile`; `leave_precedence_source = approved_assignment_current_period`; `profile_policy_ignored = true` when the profile references a legacy policy (audit `leave.profile_mismatch` / `profile_summary_stale`).
2. **PAY-SRC-001 §3.4 — Submitted salary source.** Use the current SUBMITTED salary assignment. Draft planning assignments do NOT affect payroll readiness or accrual checks. → `payroll_source_status = submitted`; `draft_exclusion_rule = exclude_draft_assignment`; excluded draft/superseded assignments never set the base salary.
3. **PAY-SRC-001 §4.2 — Recruiting handoff gate.** A payroll handoff is created ONLY after a selected candidate has an ACCEPTED offer, and the handoff assignment MUST be SUBMITTED. Draft prechecks do NOT satisfy the gate. → `payroll_handoff_gate = accepted_offer_only`; `payroll_assignment_status_required = submitted_after_acceptance`; `draft_payroll_allowed = false`; `handoff_control_result = submitted_handoff_required_after_acceptance` when an offer is accepted, else `no_handoff_required`.
4. **POL-DOCS-2026 §5.1 — Lifecycle Folder Checklist.** A folder is NOT ready unless ALL required files AND required tags are present. → `folder_ready = (required_files ⊆ files) ∧ (required_tags ⊆ tags)`; `folder_required_tag_action = add_required_tag` when a required tag is absent, else `no_tag_action`.
5. **HR-POL-014 §7.1 — Executive exceptions (formal notice content).** A formal notice for an international/exception case must contain: executive approval, time limits, tax equalization, VPN-only access, quarterly compliance review, **appeal instructions**, and **acknowledgement deadline**. Missing any → notice defective. Defect enum: `missing_ack_deadline`, `missing_appeal_instructions`, `missing_waitlist_status` (recruitment waitlist notices), `missing_correct_policy` (leave-summary notices that reference a legacy policy).
6. **APPROVAL CLOSEOUT GATE.** A final "Approved" (even by VP People / HR Director) is NOT sufficient to close when the folder OR the formal notice is defective. → `approval_closeout_gate = approval_not_sufficient_when_folder_or_notice_defective` if any folder or notice defect; `approval_sufficient_when_records_clean` otherwise. **The DECISION (`approved_with_conditions`) and the CONTROL RESULT (`hold_for_folder_and_notice_defects`) are DISTINCT** — you can approve the decision while holding the closeout.
7. **FINAL CONTROL RESULT mapping.**
   - `approve_closeout` — records clean: Submitted payroll + Approved leave + folder ready + notice valid + no blocking audit.
   - `hold_for_folder_and_notice_defects` — folder missing files/tags OR notice defective (closeout gate fails).
   - `ready_with_monitoring` — Submitted assignment confirmed + accrual batch matches (`payroll.ready` audit), monitor; this is a payroll-readiness signal, not a full closeout approval.
8. **CLOSEOUT / NEXT / ESCALATION ACTION mapping.**
   - `approve_onboarding_close` ↔ `approve_closeout`.
   - `block_close_and_reissue_notice` ↔ notice defective (reissue the defective formal notice before close).
   - `open_records_remediation` ↔ folder/records defective (missing files or tags).
9. **AUDIT SCOPE & SELECTION.** Each audit event's `event` type fixes its scope:
   - `leave.profile_mismatch` / `leave.*` → `leave_source_precedence_only`.
   - `payroll.ready` / `payroll.draft_excluded` / `payroll.*` → `payroll_assignment_readiness`.
   - `notice.defect` / `folder.tag_missing` / `case.close_blocked` / document corrections → `document_notice_findings_only`.
   - `cross_module.escalation_package` → lists related event ids in its `detail`; review each related event's own case before assigning entity-level owners/SLA.
   - For a given task: `supporting_audit_event_ids` = events whose event-type scope matches the task; `excluded_audit_event_ids` = adjacent events of a *different* scope (even on the same case). When a leave-precedence task and a folder/notice audit share a case, the folder/notice audit is EXCLUDED from the leave-scope decision.
10. **ESCALATION / REMEDIATION OWNER.**
   - Folder / file / tag records defects → `Records` (POL-DOCS-2026 owner = Records; folder-checklists uploaded_by Records).
   - Cross-module lifecycle control packages / people-ops-controlled holds → `People Ops Compliance` (XMODULE control owner).
   - Payroll draft/superseded assignment defects → `Payroll QA`.
   - `notice_remediation_action = reissue_defective_notices` when a notice is defective; `send_new_offer_notice` only when a genuinely new offer notice is required; `no_notice_action` when notices are valid.
11. **RECRUITMENT candidate outcomes.** `committee_decision` (Selected/Waitlisted/Rejected) is CONFIRMED by the `offer_register` — only a Selected candidate with an **accepted** offer is the true `selected_candidate`. → `candidate_outcome_control = committee_decision_with_offer_confirmation`; `candidate_status_source = interview_feedback_and_offer`. If no offer is accepted, there is no selection and no handoff.
12. **RECRUITMENT cost.** `recruitment_cost_total = Σ cost_ledger[].amount` for the opening — sum EVERY line regardless of which candidate it relates to; no deductions, no subset. `cost_source = recruitment_cost_ledger`.
13. **RECRUITMENT notice follow-up.** `notice_followup_required` = candidate_ids whose notice status is `not_sent` or `draft_reissue_required` (a notice action is still owed). Then:
   - Waitlist notice missing `waitlist_status` → `reissue_waitlist_notice_not_rejection` (NEVER convert a waitlist into a rejection).
   - Unsent waitlist notice → `send_waitlist_notice`.
   - Unsent rejection notice → `send_rejection_notice`.
   - Already-sent valid rejection → `no_action`.
14. **offer_exclusion_reason_for_waitlisted.** Why a waitlisted candidate is excluded from offer/handoff = `waitlisted_not_selected` (committee waitlisted them). Use `no_accepted_status_or_offer` only when a *Selected* candidate lacks an accepted offer; `already_rejected` when the candidate was committee-rejected.

## Notice-evidence source: message vs packet
- **Lifecycle case** formal notices live in `/api/messages` (subject typically `Formal Decision CASE-###`) with explicit `defects[]`/`quality` → `notice_evidence_source` / `notice_quality_source = message_notice_inspection`.
- **Recruitment** notices live in the opening's `notice_packets[]` (`/api/recruitment`) with `status`/`required_action` and (sometimes) `defects`/`quality` → `notice_quality_source = notice_packet_inspection`.
- Fall back to `case_summary_only` only when neither a message nor a packet exists.

## Common misjudgments & exclusion rules (do NOT)
- Do NOT use the employee profile `leave_balance_days` or its implied policy when an Approved/Submitted leave assignment exists — the assignment overrides; the profile may be stale (`leave.profile_mismatch`).
- Do NOT use `worksheet_leave_days` — use `approved_leave_days`.
- Do NOT treat a Draft or Superseded leave/salary assignment as authoritative; always exclude them in `excluded_*_ids`.
- Do NOT pull `base_salary` from the profile — the profile has only `salary_band`; `base_salary` comes from the Submitted salary ledger.
- Do NOT close out a case just because the approval step says "Approved" — re-check folder readiness and notice quality first (closeout gate).
- Do NOT confuse the DECISION (`approved_with_conditions`) with the CONTROL RESULT (`hold`) when folder/notice defects exist.
- Do NOT sum only some `cost_ledger` lines — sum EVERY line for the opening.
- Do NOT convert a waitlist notice defect into a rejection — waitlisted candidates get `reissue_waitlist_notice_not_rejection`.
- Do NOT create a payroll handoff for non-accepted-offer candidates, and do NOT let a draft precheck satisfy the handoff gate.
- Do NOT mix audit scopes: leave-precedence task → exclude folder/notice events; payroll-readiness task → only `payroll.*` events; folder/notice review → exclude leave/payroll-scope events.
- Do NOT trust the case `summary` alone as the answer — it is a hint; verify against approvals, folder, notice, ledger, and audit.
- Do NOT include markdown, prose, or explanations in the final JSON — return JSON only, matching the template exactly.
- Do NOT invent or "normalize" IDs — copy them verbatim from the API (case-sensitive: `PAY-122-SUB-03`, `LA-118-APP-02`, `AUD-PAY122-07`).

## Pre-submission checklist
- [ ] JSON only; no markdown fences, no trailing commentary.
- [ ] Every template field is present with the correct type (string / integer / number / boolean / list).
- [ ] Every enum uses an EXACT `allowed_values` label from the template (correct casing and underscores; no free text, no typos).
- [ ] Arrays contain only IDs (`candidate_id` / `audit_id` / `ledger_id`); `missing_files` contains filenames.
- [ ] `excluded_*_ids` lists include ALL non-authoritative records (Draft + Superseded) and EXCLUDE the chosen authoritative one.
- [ ] `base_salary` / `annual_days` / `balance_days` come from the Submitted/Approved ledger, not the profile or worksheet.
- [ ] `final_control_result` is consistent with `closeout_action`/`next_action` and `approval_closeout_gate` (clean → approve; folder/notice defect → hold; payroll ready → monitor).
- [ ] `audit_scope` matches the task; the supporting-vs-excluded audit partition is correct (adjacent-scope events excluded).
- [ ] `recruitment_cost_total` = sum of ALL `cost_ledger` lines (re-add to verify arithmetic).
- [ ] For recruitment: handoff only on accepted offer; `draft_payroll_allowed = false`; `selected_offer_status` = the offer register's status.
- [ ] IDs copied verbatim and case-sensitive; salary-period string used for `effective_date`.
- [ ] The answer is fully derivable from the live API evidence above — no fabricated fields.
