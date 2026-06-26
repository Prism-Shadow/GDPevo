---
name: peopleops-lifecycle-control-solver
description: Use this skill for PeopleOps Console tasks that ask you to reconcile onboarding, leave, payroll, remote-work, recruitment, document, notice, or audit evidence into a strict JSON answer template. It is especially useful when prompts mention source precedence, submitted versus draft records, folder readiness, notice defects, payroll handoff, accrual readiness, or normalized business labels.
---

# PeopleOps Lifecycle Control Solver

Use this skill to solve PeopleOps Console reconciliation tasks from the prompt, the provided answer template, and the remote PeopleOps environment. The core habit is to collect evidence from the authoritative module records first, then use case summaries only as orientation or fallback.

## Setup

1. Read `environment_access.md` in the task workspace and use its remote base URL in place of any `127.0.0.1:<port>` URL shown in the prompt.
2. Read the prompt and `input/payloads/answer_template.json` before gathering evidence. The template is the contract for field names, types, and allowed enum labels.
3. Prefer direct JSON endpoints for repeatability, while using the browser UI when visual confirmation is helpful.
4. Do not use any judge endpoint or feedback source. Return only the requested JSON when the prompt asks for JSON-only output.

Useful endpoints:

```text
/api/summary
/api/cases
/api/cases/{case_id}
/api/employees?q={employee_or_name}
/api/payroll-ledgers?q={employee_or_assignment}
/api/policies
/api/policies/{policy_id}
/api/recruitment?q={opening_or_candidate}
/api/documents?q={case_or_document}
/api/messages?q={case_or_message}
/api/audit?q={case_employee_or_event}
/api/audit/{audit_id}
/api/attachments/{attachment_id}
```

Important environment habit: `/api/cases` is a summary list. Open `/api/cases/{case_id}` for approval history, comments, attachments, and case-linked audit events.

## Evidence Order

Use this precedence unless the prompt explicitly narrows the scope:

1. Policy documents define the business rule and source precedence.
2. Module records provide the authoritative values:
   - leave and salary assignments in payroll/leave ledgers
   - recruitment candidates, offers, cost ledger, notice packets, and payroll prechecks
   - document folder required files/tags and current files/tags
   - messages/notice packets for notice quality and defects
3. Case detail provides approval history, attachments, comments, and case-linked audit events.
4. Audit detail confirms the specific control result and scope.
5. Employee profile summary is lower precedence when assignment records conflict.
6. Case summary is only a fallback when no stronger evidence exists.

## Leave Source Precedence

For leave-policy or leave-balance tasks:

- Use the current-period approved or submitted leave assignment as authoritative.
- Exclude draft, superseded, voided, obsolete, or planning records even if they are newer or have more attractive values.
- An approved leave assignment overrides a stale employee profile summary when the ledger, policy document, or audit detail confirms it.
- Distinguish leave assignment records from ordinary leave ledger adjustments or monthly worksheet rows; use the assignment record when the task asks for effective policy, entitlement, assignment id, or annual/balance days.
- For audit fields, include audit events whose event/detail is about leave source precedence and exclude adjacent document/notice or payroll events.

Common normalized labels:

- `leave_source`: use `leave_assignment_history` for authoritative assignment/ledger evidence, `employee_profile_summary` only when the profile is current and controlling, and `case_summary_only` only as fallback.
- `precedence_source`: use `approved_assignment_over_profile` when assignment beats profile.
- `leave_precedence_source`: use `approved_assignment_current_period` when the current approved/submitted assignment controls.
- `audit_scope`: use `leave_source_precedence_only` for leave precedence findings.

## Payroll And Accrual Readiness

For payroll assignment, salary, onboarding closeout, or accrual tasks:

- Use the current submitted salary assignment as the payroll source.
- Exclude draft planning assignments and superseded records from payroll readiness.
- Base salary, effective period/date, assignment id, and accrual batch should come from the selected submitted assignment and supporting audit detail.
- Accrual readiness is supported when the submitted assignment matches the named accrual batch and the audit result says the payroll check is ready or ready with monitoring.
- Recruiting payroll handoff is not satisfied by a draft precheck. Handoff is created only after an accepted offer and must be submitted when the template asks for submitted assignment readiness.

Common normalized labels:

- `payroll_status` and `payroll_source_status`: use the status of the selected payroll assignment, usually `submitted`.
- `draft_exclusion_rule`: use `exclude_draft_assignment` when a draft salary assignment is present but not controlling.
- `payroll_handoff_gate`: use `accepted_offer_only` when handoff begins only after an accepted offer.
- `payroll_assignment_status_required`: use `submitted_after_acceptance` when recruiting handoff needs a submitted post-acceptance record.
- `draft_payroll_allowed`: usually `false` when policy says submitted records control.
- `audit_scope`: use `payroll_assignment_readiness` for payroll/accrual findings.
- `control_result` or `final_control_result`: use `ready_with_monitoring` when the submitted payroll/accrual evidence is clean but still monitored.

## Folder, Notice, And Closeout Controls

For remote-work, onboarding closeout, document correction, and formal-notice tasks:

- Approval history determines the business decision, authority, and approval event id. Approval does not by itself make a case ready to close.
- Folder readiness requires every `required_files` item to be present in `files` and every `required_tags` item to be present in `tags`.
- A formal notice is defective if the notice packet/message quality is defective or its defects list includes missing required content such as acknowledgement deadline, appeal instructions, waitlist status, or the correct policy.
- Use notice packet inspection before message inspection when notice packets exist. Use messages when the packet points to a message or the task asks for formal notice body/quality.
- Folder or notice defects block closeout even when the final decision is approved or approved with conditions.
- For document/notice tasks, include audit events scoped to folder or notice quality and exclude adjacent payroll or leave source-precedence events.

Common normalized labels:

- `folder_ready`: `true` only when required files and tags are complete.
- `missing_files`: exact required file names that are absent.
- `required_tag_present`: `true` only if every required tag is present.
- `notice_quality`: `defective` when defects are listed; otherwise `valid`.
- `closeout_blockers`: combine `missing_required_files`, `missing_required_tags`, and `defective_formal_notice` as applicable.
- `approval_closeout_gate`: use `approval_not_sufficient_when_folder_or_notice_defective` when any folder or notice defect remains; use `approval_sufficient_when_records_clean` only when records are clean.
- `evidence_source_order`: use `approval_history_folder_notice_audit` when a task requires approval, folder, notice, and audit evidence.
- `notice_evidence_source`: prefer `notice_packet_inspection`, then `message_notice_inspection`, then `case_summary_only`.
- `folder_required_tag_action`: use `add_required_tag` when required tags are missing; otherwise `no_tag_action`.
- `notice_remediation_action`: use `reissue_defective_notices` when notice defects remain.
- `records_remediation_owner`: use `Records` for missing files/tags, `People Ops Compliance` for closeout/notice control issues, and `Payroll QA` for payroll-readiness defects.
- `final_control_result`: use `hold_for_folder_and_notice_defects` when folder or notice blockers remain; `approve_closeout` only when approval and records are clean.

## Recruitment Reconciliation

For recruiting opening tasks:

- Use the recruitment endpoint for the opening. It normally contains candidates, offer register, cost ledger, notice packets, and payroll precheck records.
- Candidate outcome arrays must contain candidate IDs only.
- Select the candidate supported by committee decision plus accepted offer evidence.
- Waitlisted and rejected candidates come from committee decisions, then notice packets determine follow-up.
- `recruitment_cost_total` is the sum of all cost ledger line amounts for the opening.
- Offer id and salary come from the accepted selected-candidate offer, not from messages or case summary.
- Follow-up notices are required for candidates whose notice packet says `not_sent` or has a required action/defect.
- Payroll handoff requires an accepted offer and then a submitted handoff/precheck record; draft records do not satisfy the gate.

Common normalized labels:

- `candidate_status_source`: use `interview_feedback_and_offer` when candidate review and offer register are used.
- `candidate_outcome_control`: use `committee_decision_with_offer_confirmation` when selected/waitlisted/rejected outcomes are reconciled against the offer register.
- `selected_offer_status`: use the accepted offer status for the selected candidate, or `none` when no controlling offer exists.
- `cost_source`: use `recruitment_cost_ledger` when summing ledger lines.
- `notice_quality_source`: use `notice_packet_inspection` when packets identify missing or defective candidate notices.
- `waitlisted_followup_action`: use `send_waitlist_notice` for unsent waitlist notice, or `reissue_waitlist_notice_not_rejection` when the wrong notice was sent.
- `rejected_followup_action`: use `send_rejection_notice` for unsent rejection notice, `reissue_rejection_notice` for defective/wrong rejection notice, and `no_action` when complete.
- `offer_exclusion_reason_for_waitlisted`: use `no_accepted_status_or_offer` or `waitlisted_not_selected` according to the evidence.
- `handoff_control_result`: use `submitted_handoff_required_after_acceptance` when an accepted offer exists but no submitted handoff satisfies the gate.

## Audit Scope Discipline

Audit events are often adjacent but not interchangeable.

- Use the audit event whose event/detail matches the task scope as the primary `audit_event_id`.
- Put all same-scope supporting audits in `supporting_audit_event_ids`.
- Put nearby but out-of-scope audit events in `excluded_audit_event_ids`, especially document/notice findings during leave tasks, leave findings during document tasks, and payroll findings during folder/notice tasks.
- Do not let an audit event about one control override module evidence for a different control.

## JSON Assembly Checklist

Before finalizing:

1. Fill every field from the template with the exact expected type.
2. Use allowed enum labels exactly; do not invent prose labels.
3. Use numbers as numbers, booleans as booleans, and arrays as arrays even for one or zero items.
4. Keep candidate outcome arrays to candidate IDs only when requested.
5. Use empty arrays for no exclusions, no missing files, or no follow-up items.
6. Return the single JSON object only when the prompt says no markdown or explanation.
