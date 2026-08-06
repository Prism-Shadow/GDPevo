---
name: court-operations-closeout
description: >-
  Produce a clerk-ready structured JSON answer for court disposition / financial
  closeout tasks (criminal sentencing registers, traffic-citation payment plans,
  post-sentencing field packets, installment/probation/license orders). Use when
  a prompt asks you to reconcile local court materials (hearing notes, audit
  memos, finance-queue extracts, worksheets, petition summaries, intake facts,
  form excerpts) against a read-only "Court Operations Portal" and emit output
  matching a provided answer_template.json. Trigger words: closeout, disposition,
  reconciliation, register totals, fee reconciliation, payment plan / installment
  order, probation referral, license suspension, petition, docket entry, clerk,
  citation, sentencing packet, CC-1375 / CC-1379 / DC-211-style forms.
---

# Court Operations Closeout

You are a deputy clerk. You take **local case materials** plus a **read-only Court
Operations Portal** (the CMS / system of record) and produce **one JSON object that
exactly matches a provided `answer_template.json`**. The work is reconciliation, not
data entry: local worksheets and finance queues carry stale or draft values, and your
job is to correct them against authoritative sources, exclude unsupported money, hold
matters with no signed order, and fill genuinely-missing fields with the exact required
placeholder — never an invented value.

## Workflow

1. **Read the prompt.** Extract: the jurisdiction/court, the target IDs (case numbers,
   citation numbers, petition IDs), the list of relevant portal endpoints it names, and
   the pointer to `input/payloads/answer_template.json`.
2. **Read every file in `input/payloads/`.** Do not skip any payload — hearing notes,
   memos, extracts, worksheets, budgets, intake facts, and form excerpts each carry
   pieces of the answer or corrections you must apply.
3. **Study `answer_template.json` first, and treat it as the contract.** It defines the
   required top-level keys, per-item required keys, the exact enum vocabularies,
   ordering rules, currency precision, date/datetime formats, and placeholder strings.
   Everything you emit must conform to it. See "Output discipline" below.
4. **Query the portal for authoritative records.** Base URL comes from
   `environment_access.md` (`GDPEVO_ENV_BASE_URL`) — substitute it for
   `<TASK_ENV_BASE_URL>`. No credentials. Use `/api/search?q=<id>` to discover every
   record tied to an ID, and `/api/<entity>?<field>=<value>` for exact lookups. See
   `reference/portal_api.md`.
5. **Reconcile** each target against the authority hierarchy (below and in
   `reference/reconciliation_rules.md`): identity/counsel, live courtroom outcome,
   current fee schedule, current policy, current form.
6. **Compute financials**: select supported fees, sum posted totals, build any
   payment/installment schedule, classify affordability against the policy band.
7. **Exclude** unsupported fees/charges/items, each with the exact reason-code enum.
8. **Placeholder** every required-but-missing identifier/contact with the exact string
   the materials require (commonly `TBD from case file`) — never invent one.
9. **Assemble** the answer: sort every list per the ordering rules, format currency and
   dates as specified, include all required keys and no extras. Return JSON only unless
   the template says otherwise.

## The authority hierarchy (the crux of every task)

Different facts have different authoritative sources. Do **not** treat the portal as
"always right" or the local notes as "always right." Resolve conflicts field-by-field:

- **Identity (name, DOB) and counsel classification** → the CMS `cases` record on the
  portal, corroborated by the paper/defense memo. Correct stale queue/worksheet values
  (misspelled name, off-by-a-day DOB, an "PD" label copied onto a private-counsel case).
  - `attorney_label_raw` of `APD` / `APPT PRIVATE` / `APPT PRIVATE - county pay` means
    **appointed_private**, NOT public defender. This matters for fees (see below).
  - If a DOB (or other identity field) is genuinely blank everywhere and the notes say it
    must be verified, use the placeholder + the "verify" action. **Never borrow a value
    from a similarly-named record in search results.**
- **Live courtroom outcome — plea, charge amendments, departure findings, and whether a
  final order was actually signed** → the contemporaneous **hearing notes / minute
  order** control. The CMS charge screen and draft worksheets frequently retain
  superseded values; correct them to the courtroom record. Concretely:
  - A charge amended in open court (e.g., a drug count amended down to a non-lab
    misdemeanor) means the conviction count is the amended one — even if the portal
    charge row still shows the original count/disposition and a lab assessment code.
  - A "departure" the judge disavowed on the record ("top of range, no departure") is
    **no departure**, even if both the worksheet and the portal charge row carry a
    `departure_type`.
  - If no final/sentencing order was signed (deferred, continued, held for signature),
    the matter is **not disposed** — hold/exclude it and post no money (see below).
- **Fee amounts / assessments** → the **current portal `fee-schedules`** row for the
  jurisdiction that is effective on the **disposition date**. A row applies only if
  `effective_date <= disposition_date` and (`end_date` is null OR `end_date >=
  disposition_date`). Ignore archived/stale rows (those with a past `end_date`).
- **Payment policy and plan structure** → the current portal `payment-policies` row for
  the jurisdiction (min/max monthly band, `account_fee`, `first_due_days`, restitution
  priority, `return_to_court_offset_days`).
- **Forms** → the current portal `forms` row for the jurisdiction (form_id, label,
  required_fields, placeholder_instruction). Prefer it over a local form excerpt when
  they differ; an obsolete footer/service-charge in an old local copy is not current.

## Money rules

- **Post only supported money.** A fee/charge is postable only if a current fee schedule,
  the hearing/disposition order, or explicit current policy directly supports it. Never
  add — and actively exclude — account-management/maintenance, collection/referral,
  late-payment, DMV/reinstatement, returned-check, restitution (unless ordered),
  copy/certification, traffic-school, court-reporter, or court-appointed-attorney fees
  unless a portal record, current schedule, or hearing order directly supports them.
- **Public Defender User Fee**: post only when counsel is truly `public_defender`;
  exclude it for appointed_private or retained counsel.
- **Drug/lab assessment**: post only when the **conviction** count is the eligible
  offense, and at the **current** schedule amount. If the count was amended away to a
  non-lab offense, do not post the lab fee. Never carry a stale/archived assessment
  amount.
- **No signed order → no financial entry.** For deferred/continued/held matters, post no
  fees, record a hold/exclusion with a next-status/next-setting date, and set any
  `financial_posting_allowed`-style flag to false.
- **Totals** sum only the posted lines. Compute per-case totals and batch/register
  totals from what you actually posted, currency to two decimals.

## Payment / installment schedules

When a plan is approved, build the schedule from the reconciled balance and the approved
monthly amount. General algorithm (map the field names to the template's exact keys):

- `total_due` = reconciled balance = supported fines + costs (+ restitution per the
  policy's application order), minus every excluded fee.
- Apply any `down_payment`; let `remaining = total_due - down_payment`.
- `full_installment_count = floor(remaining / monthly)`.
- If `remaining` divides evenly: `final_payment_amount = monthly` and
  `total_installments = full_installment_count`. Otherwise
  `final_payment_amount = remaining - full_installment_count * monthly` and
  `total_installments = full_installment_count + 1`.
- `first_due_date`: per policy (e.g., "the 15th of the next month," or submitted date +
  `first_due_days`), or the date stated in the hearing note when given.
- `final_due_date`: `first_due_date` advanced by `(total_installments - 1)` intervals.
- `return_to_court_date`: per the policy `return_to_court_offset_days`; set the trigger
  enum (nonpayment / default_review / none) from the notes/policy.
- **Restitution priority** and **account-fee treatment** follow the jurisdiction policy:
  if the policy's `account_fee` is 0, an old counter/worksheet account fee is excluded by
  policy; apply restitution-before-fines-and-costs only when restitution > 0 and the
  policy so states.

## Budget / affordability classification

`monthly_disposable_income = monthly_income - monthly_obligations`. Classify the
requested/selected installment against the policy band (`min_monthly`..`max_monthly`) and
disposable income, using the template's exact enum (e.g., supported / below_policy_minimum
/ above_policy_maximum / unsupported_by_budget / needs_judge_review). Report the policy
band values where the schema asks for them.

## Conditional form/order preparation

Prepare a form/order only when its triggering event actually occurred:

- Probation referral (CC-1375-style) → prepare only when supervised probation was
  ordered; if no referral order was signed, mark it not-ordered and leave its
  report_datetime null.
- License suspension order (CC-1379-style) → use the correct start basis (usually the
  conviction date, not the release date) and compute the end date from the ordered
  months.
- Compute derived dates (report datetime, suspension end, return-to-court) from the
  controlling source; keep unknown driver-license numbers / contacts as the placeholder.

## Placeholders and exclusions

- Use the **exact** placeholder string the materials/forms require (commonly
  `TBD from case file`) for required fields genuinely absent from every source — SSN,
  driver license number, mailing/residence address, phone, probation officer/office
  contact. Do not invent identifiers or contact details, and do not borrow them from
  look-alike records. List placeholder fields / missing_fields per the schema, sorted as
  required.
- Emit the exclusions list with the exact `reason_code` enum from the template
  (e.g., stale_schedule, unsupported_post_disposition, not_in_hearing_order,
  not_current_policy, no_triggering_event, no_order_or_policy_support, not_part_of_balance,
  continued_pending_no_final_order). Only exclude when there is genuinely no triggering
  event, order, or current-policy/schedule support.

## Output discipline

- Match `answer_template.json` **exactly**: all required top-level keys and per-item
  required keys, no extra keys, no omissions.
- Use enum values **verbatim** — never substitute prose or a synonym for an enum value.
- Currency: numeric, two decimal places. Dates: `YYYY-MM-DD`. Datetimes:
  `YYYY-MM-DDTHH:MM:SS`. Times: `HH:MM`. Use `null` only where the schema allows it.
- Sort every list by the field(s) named in the ordering rules, ascending.
- Return JSON only (no markdown fences, no commentary) when the template says so.

See `reference/reconciliation_rules.md` for the decision table and worked patterns, and
`reference/portal_api.md` for the endpoint catalog and query mechanics.
