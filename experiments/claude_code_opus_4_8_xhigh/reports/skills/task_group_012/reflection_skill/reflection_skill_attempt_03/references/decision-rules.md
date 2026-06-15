# Decision rules and normalized label vocabulary

Read this when you need to confirm which enum label a field takes, or to resolve
two similar-sounding labels. Every label below is drawn from answer-template
`allowed_values`; no concrete entity IDs or data values appear here. Use
placeholders (`<EMP-ID>`, `<CASE-ID>`, `<OPENING-ID>`, `<ASSIGNMENT-ID>`,
`<AUDIT-ID>`) when reasoning, and substitute the live values at solve time.

## Table of contents

1. Field families and their label sets
2. Source-precedence / status labels
3. Gate, scope, and control-result labels
4. Notice defect codes and notice evidence-source labels
5. Recruitment outcome / handoff labels
6. Generic decision walk-throughs (no concrete values)
7. Disambiguation cheatsheet for the look-alike labels

---

## 1. Field families and their label sets

The template names vary per task, but the labels cluster into families. Match the
field's `allowed_values` to a family below, then apply that family's rule.

## 2. Source-precedence / status labels

Leave source:
- `leave_assignment_history` — an explicit approved/submitted assignment record controls.
- `employee_profile_summary` — only when no assignment record overrides it.
- `case_summary_only` — only the case summary is available.

Leave precedence source:
- `approved_assignment_current_period` — approved assignment for the effective period controls.
- `profile_summary_current_period`
- `case_summary_only`

Precedence source (assignment-vs-profile decision):
- `approved_assignment_over_profile` — approved assignment beats a stale profile summary.
- `employee_profile_summary`
- `case_summary_only`

Payroll status / payroll source status / status:
- `submitted` — the authoritative salary assignment state.
- `draft` — excluded planning rows.
- `superseded` — excluded older rows.

Draft exclusion rule:
- `exclude_draft_assignment` — default; drop draft assignments.
- `draft_allowed`
- `exclude_superseded_only`

Rule of thumb: the authoritative record is the approved/submitted one for the
effective period. Drafts and superseded/obsolete/voided rows go in the excluded
set even when their salary or day counts are larger.

## 3. Gate, scope, and control-result labels

Approval/closeout gate:
- `approval_sufficient_when_records_clean` — folder ready AND notice valid.
- `approval_not_sufficient_when_folder_or_notice_defective` — any folder/notice defect.

Final control result / control result:
- `approve_closeout` — clean records, close approved.
- `approve_onboarding_close` — onboarding-specific clean close.
- `hold_for_folder_and_notice_defects` — defect present, do not close.
- `ready_with_monitoring` — payroll/accrual readiness confirmed with monitoring
  (read this verbatim from the payroll-readiness audit detail).

Closeout action / next action / escalation action:
- `approve_onboarding_close` / `approve_closeout` — clean.
- `block_close_and_reissue_notice` — a notice defect blocks close.
- `open_records_remediation` — a folder/file (records) defect blocks close.
- `no_action` — nothing to do.

Audit scope:
- `leave_source_precedence_only` — leave-topic events.
- `document_notice_findings_only` — folder/notice/document-topic events.
- `payroll_assignment_readiness` — payroll-topic events.

Evidence source order:
- `approval_history_folder_notice_audit` — full case review reads approval
  history, then folder, then notice, then audit.
- `folder_notice_audit`
- `audit_only`

Audit result:
- `profile_summary_stale` — audit confirms the profile is stale vs the assignment.
- `ready_with_monitoring`
- `block_close`

Records remediation owner:
- `Records`
- `People Ops Compliance`
- `Payroll QA`

(Read the actual owner from the governing policy / audit package — do not default
to the case owner.)

Folder required-tag action:
- `no_tag_action` — all required tags present.
- `add_required_tag` — a required tag is missing.

Notice remediation action:
- `reissue_defective_notices` — there is a defective notice to reissue.
- `no_notice_action`
- `send_new_offer_notice`

## 4. Notice defect codes and notice evidence-source labels

Notice quality:
- `valid`
- `defective`

Notice defect codes (copy verbatim from the structured notice `defects[]`):
- `missing_ack_deadline`
- `missing_appeal_instructions`
- `missing_waitlist_status`
- `missing_correct_policy`

Notice evidence source / notice quality source:
- `notice_packet_inspection` — a structured notice record with `quality` +
  `defects[]` exists (regardless of which endpoint serves it). This is the usual
  answer.
- `message_notice_inspection` — only a free-text message body, no structured
  notice record.
- `case_summary_only` — neither exists.

## 5. Recruitment outcome / handoff labels

Onboarding handoff (immediate next action):
- `create_payroll_precheck` — no precheck record exists yet ⇒ create one first.
- `create_submitted_assignment_after_acceptance` — precheck exists / a submitted
  assignment is the immediate artifact to produce.
- `no_payroll_handoff` — no accepted offer.

Payroll handoff gate (trigger / precondition):
- `accepted_offer_only` — an accepted offer alone triggers the handoff.
- `accepted_offer_and_submitted_assignment`
- `all_interviewed_candidates`

Payroll assignment status required (eventual end-state):
- `submitted_after_acceptance`
- `submitted`
- `draft_allowed`

Handoff control result:
- `submitted_handoff_required_after_acceptance`
- `submitted_handoff_required`
- `no_handoff_required`

Candidate status source:
- `interview_feedback_and_offer`
- `case_summary_only`
- `message_only`

Candidate outcome control:
- `committee_decision_with_offer_confirmation`
- `message_status_only`
- `case_summary_only`

Selected offer status:
- `accepted` / `draft` / `withdrawn` / `none`

Cost source:
- `recruitment_cost_ledger` — sum of all cost-ledger lines.
- `case_summary_only`

Waitlisted follow-up action:
- `send_waitlist_notice`
- `reissue_waitlist_notice_not_rejection`
- `no_action`

Rejected follow-up action:
- `send_rejection_notice`
- `no_action`
- `reissue_rejection_notice`

Offer exclusion reason for waitlisted:
- `no_accepted_status_or_offer` — waitlisted candidate has no accepted offer.
- `waitlisted_not_selected`
- `already_rejected`

## 6. Generic decision walk-throughs (no concrete values)

### Onboarding closeout (clean case)
Resolve `<EMP-ID>`. Among leave assignments, keep the approved one for the
period (`leave_assignment_history`, `approved_assignment_current_period`); put
superseded + draft in excluded leave IDs. Among payroll rows, keep the submitted
assignment (`submitted`); put draft in excluded payroll IDs. If no folder or
notice defect exists for this employee, records are clean ⇒ gate
`approval_sufficient_when_records_clean`, action `approve_onboarding_close`,
result `approve_closeout`.

### Remote-work folder + notice review (defective case)
Resolve `<CASE-ID>`; read approval (authority + event ID + decision). Folder:
compute `missing_files = required − present`; not ready if any missing; tag action
from required-tag presence. Notice: read structured record ⇒
`notice_packet_inspection`, copy defect codes, quality `defective`. Audit: the
on-topic notice/folder event is supporting; any off-topic same-case event is
excluded (often none ⇒ empty). Defect present ⇒ gate
`approval_not_sufficient_when_folder_or_notice_defective`, result
`hold_for_folder_and_notice_defects`; closeout blockers = the actual defects;
next action = reissue notice and/or open records remediation per defect type.

### Leave source precedence (assignment over stale profile)
Resolve `<EMP-ID>`; the leave audit (`profile_summary_stale`) names the
controlling approved `<ASSIGNMENT-ID>`. Use its policy + balance days; precedence
`approved_assignment_over_profile`; profile policy ignored = true; next action
`update_employee_summary`. Audit scope `leave_source_precedence_only`: supporting
= the leave event; excluded = the adjacent folder/document event.

### Payroll / accrual readiness
Resolve `<EMP-ID>`; keep the submitted assignment, exclude the draft. The payroll
audit detail states `ready_with_monitoring` and confirms the accrual batch ⇒
accrual ready = true; control result `ready_with_monitoring`; draft exclusion
`exclude_draft_assignment`; scope `payroll_assignment_readiness`. Effective date
from the submitted record's period as first-of-month.

### Recruitment reconciliation
Resolve `<OPENING-ID>`; bucket candidates by committee decision; selected
candidate's offer status from the register. Cost total = sum of all ledger lines
(`recruitment_cost_ledger`). Notice follow-up = candidates with not-sent notices
(waitlist ⇒ send waitlist notice; rejected ⇒ send rejection notice). Handoff (see
the three-concept rule): gate `accepted_offer_only`; if precheck list empty,
immediate action `create_payroll_precheck`; end-state required
`submitted_after_acceptance` / `submitted_handoff_required_after_acceptance`,
draft payroll not allowed.

## 7. Disambiguation cheatsheet for the look-alike labels

- notice evidence source: structured packet exists ⇒ `notice_packet_inspection`,
  not `message_notice_inspection`, even when the packet lives in messages.
- payroll handoff: the GATE is `accepted_offer_only`; the submitted-assignment
  requirement belongs to status-required / control-result, not the gate.
- onboarding handoff action: empty precheck list ⇒ `create_payroll_precheck`
  (earlier step), not `create_submitted_assignment_after_acceptance`.
- excluded records vs authoritative: bigger salary / more days on a draft or
  later-period row is a distractor; the submitted/approved row wins.
- audit supporting vs excluded: by event TOPIC, not by shared case/employee;
  no off-topic adjacent event ⇒ empty excluded list.
