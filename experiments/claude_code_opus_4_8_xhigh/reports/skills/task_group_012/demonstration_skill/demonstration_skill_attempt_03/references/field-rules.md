# Field rules: picking winners, naming losers, mapping labels

This file explains *why* a field gets its value, so you can transfer the logic to
new entities. The template always tells you the allowed labels; this file tells
you which evidence selects which label. No concrete entity values appear here —
read them live.

## Record-status precedence ladder

Across leave and payroll, status — not edit recency — decides authority:

```
Approved / Submitted   -> authoritative (the winner)
Superseded             -> excluded (was authoritative, now replaced)
Draft / Voided / Obsolete -> excluded (never authoritative)
```

So when several rows exist for one subject and period, the winner is the
Approved (leave) or Submitted (salary) row; everything else goes into the
matching `excluded_*` list. A newer `updated_at` on a Draft does **not** promote
it. This mirrors the source-precedence policy text ("latest approved/submitted
controls; drafts and obsolete excluded even when summaries conflict").

### Record-type discrimination (leave)

The payroll-ledgers endpoint mixes `record_type`s. For leave *entitlement*, the
authoritative source is the formal **leave assignment** record. HRMS leave
ledgers and People-Ops adjustment rows are operational/transactional, not the
entitlement of record — do not pick them as `effective_leave_policy` /
`assignment_id` / balance, even if their numbers look plausible or fractional.

## Profile-vs-assignment

An employee profile carries a `leave_balance_days` and sometimes a policy. When
an approved leave assignment exists for the period, the **assignment overrides
the profile**. Even if the profile number happens to match the assignment, the
*source* is the assignment, and the profile is treated as stale:

- `precedence_source = approved_assignment_over_profile`
- `profile_policy_ignored = true`
- `leave_source = leave_assignment_history` (not `employee_profile_summary`)
- `audit_result = profile_summary_stale`
- `next_action = update_employee_summary` (fix the stale summary; this is not a
  records-remediation or block situation by itself)

## Reading control results from audit `detail`

Audit events carry a human-readable `detail` that usually states the QA verdict
in words. Map the verdict to the template's control-result enum rather than
inferring from scratch:

- a "ready_with_monitoring" verdict (e.g. submitted assignment matches the
  accrual batch) -> `control_result = ready_with_monitoring`, `accrual_ready = true`
- a "profile_summary_stale" verdict -> `audit_result = profile_summary_stale`
- a notice-defect / "return for reissue" verdict -> drives the hold/blocker path

Pick the event whose `event`/`detail`/`employee_id`/`case_id` matches the
subject and scope of the question. That event is the `audit_event_id` /
controlling/supporting event. Any other event on the same case that addresses a
different concern (e.g. a folder/tag event when the question is about leave) is
**off-scope** and belongs in `excluded_audit_event_ids`. When there is only the
one relevant event, the exclusion list is empty (`[]`).

## Folder readiness as set math

```
folder_ready          = (required_files ⊆ files) AND (required_tags ⊆ tags)
missing_files         = required_files \ files        # exact filenames
required_tag_present  = required_tags ⊆ tags
```

`closeout_blockers` is the subset of
{`missing_required_files`, `missing_required_tags`, `defective_formal_notice`}
that actually applies. The folder's own `ready` boolean should agree with your
computation; if it does not, recheck your set difference. `folder_required_tag_action`
= `add_required_tag` only when a required tag is missing, otherwise `no_tag_action`.

## Notice quality and the defect vocabulary

Judge the notice from the **notice packet / message** (`quality`, `defects`),
corroborated by the controlling audit `detail` — never from the case summary.
`notice_quality = defective` if any defect is present, else `valid`. Defect codes
are a closed vocabulary; emit only these labels and only the ones present:

```
missing_ack_deadline
missing_appeal_instructions
missing_waitlist_status
missing_correct_policy
```

(These come from the formal-notice requirements: a compliant notice typically
needs an acknowledgement deadline, appeal instructions, correct policy
reference, and — for recruitment waitlist notices — waitlist status. A missing
element produces the matching defect code.)

`notice_remediation_action = reissue_defective_notices` when defective; else
`no_notice_action`. For recruitment, an unsent rejection/waitlist notice routes
to `send_rejection_notice` / `send_waitlist_notice` (a fresh send, not a reissue).

## Approval vs closeout gating

An approval authorizes the *decision* but not necessarily the *closeout*:

- Clean records + approval present ->
  `approval_closeout_gate = approval_sufficient_when_records_clean`,
  `final_control_result = approve_closeout`,
  `next_action = approve_onboarding_close`.
- Any defective folder/notice ->
  `approval_closeout_gate = approval_not_sufficient_when_folder_or_notice_defective`,
  `final_control_result = hold_for_folder_and_notice_defects`,
  `next_action = block_close_and_reissue_notice`,
  `escalation_action = open_records_remediation`.

A decision can be `approved_with_conditions` while closeout is still held — the
two are separate. Do not let the existence of an approval flip closeout to
approve when blockers exist.

## Escalation owner / SLA — read, do not invent

When a field asks for the records-remediation owner, escalation owner, or an SLA,
fetch the controlling remediation/audit/escalation package and read the owner and
any SLA **verbatim** from its detail/owner fields, then map to the template's
allowed owner labels (the closed set of owner enums the template lists). If the
package does not state a value, do not fabricate one. This keeps the answer
grounded in the data rather than in assumptions.

## Recruitment specifics

- Outcomes come from `committee_decision`; the offer register *confirms* the
  selection (`candidate_outcome_control = committee_decision_with_offer_confirmation`).
- Only an offer with status `accepted` counts as accepted
  (`selected_offer_status = accepted`); otherwise it is draft/withdrawn/none.
- `recruitment_cost_total` = arithmetic sum of all cost-ledger `amount` values.
- A waitlisted candidate has no accepted offer, hence no payroll handoff:
  `offer_exclusion_reason_for_waitlisted = no_accepted_status_or_offer`.
- Payroll handoff only after an accepted offer, and it must be a *submitted*
  assignment; draft prechecks do not satisfy the gate
  (`draft_payroll_allowed = false`).

## Type discipline

- Day counts: usually `integer`; but adjustment rows can be fractional, so read
  the actual numeric value and respect the template's declared type.
- Salary / cost / base salary: `number`.
- Dates: `string` exactly as stored (e.g. `YYYY-MM-DD`).
- Booleans: real `true`/`false`.
- `list[*]` fields: sets — complete, deduplicated, no off-scope members; empty
  list `[]` when nothing applies.
