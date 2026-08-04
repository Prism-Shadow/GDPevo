## Description

Operating rules for the PeopleOps HR management console. Covers employee onboarding closeout, leave/payroll source precedence, case folder and notice quality review, recruitment closeout, candidate lifecycle, and payroll handoff readiness.

## Access

- **Base URL**: `<TASK_ENV_BASE_URL>`
- **Credentials**: `ops.lead@peopleops.local` / `PeopleOps#2026`
- **API**: All endpoints are GET-only except `POST /api/cases/{case_id}/comments` (JSON body with `author`, `created_at`, `visibility`, `body`).

## Source Precedence Rules

These rules determine which records are authoritative when multiple sources exist for the same entity.

### General Hierarchy

1. **Submitted/approved records** always override **draft records**. Never use draft records as final authority.
2. **Assignment history** overrides **employee profile summary** when the assignment is approved and corroborated by ledger, policy document, and audit event detail.
3. **Interview feedback combined with offer records** is the authoritative source for candidate outcomes — not case summaries or messages alone.
4. **Payroll assignment records** must be **submitted** (not draft) to be used for accrual or handoff decisions.

### Exclusion Rules

- **Draft records**: Always exclude from final determinations. Identify them and list them in exclusion fields.
- **Superseded records**: Exclude records marked as superseded.
- **Out-of-scope audit events**: Exclude audit events whose scope does not match the current review. Audit scope values are `leave_source_precedence_only`, `document_notice_findings_only`, and `payroll_assignment_readiness`.

## Evidence Source Ordering

When collecting evidence for a decision, follow this order and escalate only when the current tier is insufficient:

1. **Case summary and approval history** — start here for context.
2. **Case folder and formal notice packet** — inspect for required files, tags, and notice quality.
3. **Audit event detail** — cross-reference with specific audit event IDs for the relevant scope.
4. **Employee profile summary, leave ledger, policy documents, payroll assignment records** — use for leave/payroll-specific decisions.

Evidence source priority values: `approval_history_folder_notice_audit` > `folder_notice_audit` > `audit_only`.

## Closeout Gate Rules

A closeout can only be approved when records are clean and complete.

- **Approval sufficient**: `approval_sufficient_when_records_clean` — all records submitted, no defects, all required files present.
- **Approval not sufficient**: `approval_not_sufficient_when_folder_or_notice_defective` — any missing files, missing tags, or defective notices block approval.

### Folder Readiness

- Verify all required files are present in the case folder. List any missing files.
- Verify required tags are present on the case. If a required tag is missing, the action is `add_required_tag`.

### Formal Notice Quality

- Inspect the formal notice packet for these defects:
  - `missing_ack_deadline` — no acknowledgment deadline specified.
  - `missing_appeal_instructions` — no appeal process instructions.
  - `missing_waitlist_status` — waitlist status not communicated.
  - `missing_correct_policy` — incorrect or missing policy reference.
- Notice quality is either `valid` or `defective`.
- Notice evidence source: prefer `notice_packet_inspection` over `message_notice_inspection` over `case_summary_only`.

### Final Control Result

- `approve_closeout` — all gates passed, records clean.
- `hold_for_folder_and_notice_defects` — folder or notice defects found.
- `ready_with_monitoring` — records clean but ongoing monitoring advised.

## Leave and Payroll Verification

### Leave Source Precedence

- `approved_assignment_current_period` — authoritative when an approved leave assignment exists for the effective period and is confirmed by ledger/policy/audit.
- `profile_summary_current_period` — used only when no approved assignment exists for the period.
- `case_summary_only` — last resort, used only when neither assignment nor profile data is available.

- When the approved assignment overrides the profile: set `profile_policy_ignored` to `true`, and the audit result to `profile_summary_stale`. The next action is `update_employee_summary`.

### Payroll Source Status

- Preferred status: `submitted`. Draft records must be excluded.
- `draft_exclusion_rule`: use `exclude_draft_assignment` to filter out draft payroll assignments. Use `exclude_superseded_only` when drafts are acceptable but superseded records are not. Use `draft_allowed` only when explicitly warranted.

### Accrual Readiness

- Verify the accrual batch is identified and ready based on submitted payroll assignment data.
- The audit scope for payroll/accrual checks is `payroll_assignment_readiness`.

## Recruitment Closeout and Candidate Lifecycle

### Candidate Outcome Determination

- Source for candidate status: `interview_feedback_and_offer` is authoritative. Fall back to `case_summary_only` or `message_only` only when feedback/offer data is unavailable.
- Outcome control: `committee_decision_with_offer_confirmation` — the committee decision paired with offer acceptance status is the final authority.

### Offer Status

- `accepted` — candidate accepted the offer. Triggers payroll handoff eligibility.
- `draft` — offer not yet finalized. Do not use for decisions.
- `withdrawn` — offer was retracted.
- `none` — no offer exists.

### Waitlist and Rejection Handling

- **Waitlisted candidates**: Send waitlist notice. If a rejection was incorrectly sent, `reissue_waitlist_notice_not_rejection`. If no action needed, `no_action`.
- **Rejected candidates**: Send rejection notice. If already sent correctly, `no_action`. If defective, `reissue_rejection_notice`.
- **Waitlisted exclusion reason**: A waitlisted candidate is excluded from offer processing because `no_accepted_status_or_offer` (no accepted offer exists for them), `waitlisted_not_selected` (they were waitlisted, not selected), or `already_rejected` (already processed as rejected).

### Payroll Handoff

- **Handoff gate**: `accepted_offer_only` (handoff after acceptance alone), `accepted_offer_and_submitted_assignment` (requires both acceptance and a submitted payroll assignment), `all_interviewed_candidates` (handoff for all).
- **Assignment status required**: `submitted_after_acceptance` (submitted assignment post-acceptance), `submitted` (any submitted assignment), `draft_allowed` (drafts accepted).
- **Draft payroll allowed**: `false` unless explicitly warranted.
- **Handoff control result**: `submitted_handoff_required_after_acceptance`, `submitted_handoff_required`, or `no_handoff_required`.
- **Onboarding handoff actions**: `create_payroll_precheck`, `create_submitted_assignment_after_acceptance`, or `no_payroll_handoff`.

### Recruitment Costs

- Source: `recruitment_cost_ledger` is authoritative. Fall back to `case_summary_only` only when the ledger is unavailable.

## Audit Integration

- Every material decision must reference at least one **audit event ID**.
- Use **supporting audit event IDs** for events that corroborate the decision within scope.
- Use **excluded audit event IDs** for events that are adjacent but outside the current audit scope.
- Audit scope must match the type of review being performed:
  - `document_notice_findings_only` — for folder/notice quality reviews.
  - `leave_source_precedence_only` — for leave policy and balance determinations.
  - `payroll_assignment_readiness` — for payroll assignment and accrual checks.

## Records Remediation

When records are defective:
- **Owner**: `Records` (folder/file issues), `People Ops Compliance` (policy/notice issues), `Payroll QA` (payroll assignment issues).
- **Escalation**: `open_records_remediation` to fix record-level issues, `block_close_and_reissue_notice` to block and reissue defective notices, `no_action` if clean.
- **Notice remediation**: `reissue_defective_notices` to reissue, `send_new_offer_notice` for new offers, `no_notice_action` if clean.

## Output Format

- Return **only JSON**, no markdown or explanatory text.
- Match the **answer template** structure exactly.
- Use the **normalized enum labels** defined in the template for all gate, source, scope, status, owner, remediation, and control-result fields. Do not substitute free-text explanations.
- All field names, types, and allowed values are defined by the answer template. Do not invent new fields.

## API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/manifest` | System manifest |
| GET | `/api/summary` | Dashboard summary |
| GET | `/api/employees` | Employee listing |
| GET | `/api/cases` | Case listing |
| GET | `/api/cases/{id}` | Case detail |
| GET | `/api/cases/{id}/comments` | Case comments |
| GET | `/api/policies` | Policy listing |
| GET | `/api/policies/{id}` | Policy detail |
| GET | `/api/payroll-ledgers` | Payroll ledger |
| GET | `/api/recruitment` | Recruitment openings and candidates |
| GET | `/api/documents` | Document listing |
| GET | `/api/messages` | Messages/notices |
| GET | `/api/notifications` | System notifications |
| GET | `/api/audit` | Audit event listing |
| GET | `/api/audit/{id}` | Audit event detail |
| GET | `/api/attachments/{id}` | File attachments |
| POST | `/api/cases/{id}/comments` | Add case comment |
