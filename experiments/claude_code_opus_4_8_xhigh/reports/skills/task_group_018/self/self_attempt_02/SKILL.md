---
name: court-operations-closeout-packet
description: >-
  Prepare a deputy-clerk closeout / field packet by reconciling local court
  materials (hearing & bench notes, audit memos, finance queue extracts and
  worksheets, petitions & budgets, form excerpts) against a read-only Court
  Operations Portal, then emit ONE JSON object that exactly matches the task's
  answer_template.json. Use for criminal sentencing/disposition registers,
  traffic-violation payment-plan closeouts, and post-sentencing financial /
  supervision (probation + license + installment) packets. Triggers: "closeout",
  "disposition register", "sentencing packet", "post-disposition/post-sentencing
  packet", "payment plan", "fee reconciliation", "audit findings", "Court
  Operations Portal", CC-1375 / CC-1379 forms, financial petitions.
---

# Court Operations Closeout Packet

You are a court clerk / deputy clerk. Each task gives you **local materials**
that are messy on purpose (bench shorthand, carry-forward drafts, stale amounts,
mislabeled counsel, omitted fees) plus a **read-only portal** that is the live
system of record, and asks for **one JSON object** matching a provided
`answer_template.json`. Your job is to *reconcile*, not transcribe.

## 1. Read the task before doing anything

1. `input/prompt.txt` — jurisdiction, target case/citation/petition IDs, hearing
   or disposition date, which endpoints are relevant, and which output sections
   are required.
2. **Every** file in `input/payloads/` — including `answer_template.json`. Read
   all payloads; each one carries facts and traps you must account for.
3. `environment_access.md` (repo root) — `GDPEVO_ENV_BASE_URL` and the allowed
   `GET` endpoints. There are no credentials. Use it **only** for network access.

`answer_template.json` is the contract. It defines the exact top-level keys,
nesting, enum vocabularies, ordering rules, currency precision, and date
formats. Read it first to know what to gather, and read it again at the end to
conform. Enums, key names, and reason codes differ per task — always copy them
**verbatim from that task's template**, never from memory or from another task.

## 2. Golden rules (never violate)

- **Output = one JSON object only.** No markdown, no commentary, no trailing
  prose. Match `answer_template.json` structure exactly.
- **Use only the template's enum values.** Do not substitute prose for an enum.
  If the template offers a `verify_before_entry` / `needs_judge_review` style
  value, prefer it over guessing when evidence is genuinely ambiguous.
- **Never invent** identifiers, contact details, fees, charges, balances, or
  conditions. A required-but-missing field takes the **exact placeholder string
  the materials specify** — commonly `"TBD from case file"` (confirm the literal
  string in the form excerpt / `placeholder_instruction` / template enum).
- **Reconcile, don't copy.** Local drafts and carried-forward values are
  suspect. Cross-check every consequential value against the portal and the
  signed courtroom record before you post it.
- **No signed final order ⇒ hold.** If the portal status is `deferred` /
  `pending` / `continued`, or the notes say the order was not signed, enter no
  disposition and no financials; route the matter to the hold/exclusion section
  and keep it out of the disposed register and batch totals.
- Follow the template's formatting: money as numbers to **two decimals**; dates
  `YYYY-MM-DD`; datetimes `YYYY-MM-DDTHH:MM:SS`; times `HH:MM`; use `null` only
  where the template explicitly allows it.
- Obey the template's **ordering rules** (usually sort lists by case/citation/
  petition/charge id ascending; sort field/item name lists alphabetically).

## 3. Authority hierarchy — who wins a conflict

Different fields are governed by different sources. Apply this split; it is the
core of the task and the basis of the audit findings.

| Field in question | Authoritative source |
|---|---|
| Identity: name spelling, DOB | Portal `/api/cases` (CMS). A corroborating audit memo that agrees strengthens it. Do **not** trust the finance-queue/worksheet spelling or DOB. |
| Counsel classification (retained / public_defender / appointed_private) | Portal `/api/cases` `counsel_type`. Calendar/queue abbreviations (e.g. "APD", "PD") are often wrong; the judge's on-record clarification and the memo override the abbreviation. |
| Case status (disposed vs deferred/pending/continued) | Portal `/api/cases` status + the signed-order evidence in the notes. |
| What the court actually did: plea, **charge disposition**, whether a **departure** was entered, pronounced sentence terms | The **signed courtroom record** (hearing/bench notes, corroborated by the audit memo). This overrides stale/draft values **even when they appear on the CMS charge screen** — the charge screen can carry draft departure labels or a superseded disposition. |
| Fee amount / whether a fee applies | The **current** portal fee schedule effective on the disposition date (see §5). Never the amount carried in the finance queue. |
| Payment-plan band, first-due timing, account fee, restitution priority, return-to-court offset | Portal `/api/payment-policies` for the jurisdiction. |
| Form id / label / required fields / placeholder rule | Portal `/api/forms` for the jurisdiction (local form excerpt is secondary/illustrative). |

When the portal and a corroborating memo agree against the local queue, the
resolution favors the authoritative source (CMS / hearing notes / fee schedule)
— pick the template's matching `resolution_source` / `recommended_resolution`
enum (`use_cms`, `use_hearing_notes`, `use_corrob_memo`, `use_fee_schedule`,
`hold_unsigned_order`, `verify_before_entry`, etc.).

## 4. Portal workflow

Base URL from `environment_access.md`. All endpoints are `GET` and support
filtering by query params (e.g. `?case_number=...`, `?jurisdiction_code=...`);
`/api/search?q=<identifier>` returns mixed `result_type` rows (cases, charges,
docket_entries…) and is the fastest way to locate a record. Responses are
`{"count", "results":[...]}`.

For each target matter, pull and reconcile:
- `/api/jurisdictions` — jurisdiction_code, court_name, policy_ref, timezone.
- `/api/cases` — identity, `counsel_type`, `attorney_name`, `status`,
  `disposition_date`, `attorney_label_raw` (the raw/abbreviated label to
  distrust).
- `/api/charges` — counts, plea, disposition, fine, jail imposed/suspended,
  probation months, `departure_type`/`departure_reason`, `assessment_code`,
  severity. **Treat departure and disposition here as claims to verify against
  the signed record, not as final truth.**
- `/api/docket-entries` — official entry text/dates; note the `disposition`
  entry's recorded status. Clerk-note text may be redacted.
- `/api/citations` (traffic) — plea, disposition, speed/zone, violation_code,
  plan_approved, monthly_payment, first_due_date.
- `/api/fee-schedules`, `/api/payment-policies`, `/api/forms`,
  `/api/financial-petitions` — reference data (see §5–§9).

See `references/portal_reference.md` for the field-level schema of each endpoint.

## 5. Fee-schedule selection (do this live every time)

Never post a fee amount carried in a local queue/worksheet. Select the
authoritative amount:

1. Filter `/api/fee-schedules` to the matter's `jurisdiction_code`.
2. Match the needed `fee_type` (and `violation_code` for traffic fines).
3. Keep only rows **effective on the disposition date**:
   `effective_date <= disposition_date AND (end_date is null OR end_date >= disposition_date)`.
4. **Discard** ended/stale rows, rows for other jurisdictions, and NOISE rows
   (e.g. "Copy or certification fee", "Archived local fee"). Use the surviving
   current amount.

Fee **applicability** rules:
- `court_cost` (circuit filing cost): mandatory on a disposed criminal case.
- `fine`: the amount pronounced in the signed sentence.
- Drug/crime-lab **assessment**: only when the *conviction* charge triggers it
  (controlled-substance / lab-relevant conviction with `assessment_code` set and
  the judge ordered it) — and at the **current** schedule amount, not an
  archived one.
- `public_defender_user_fee`: only when `counsel_type == public_defender` **and**
  the court did not waive it. Never for retained or appointed_private counsel.
- Post **no** fee on a held/deferred/pending/continued matter.

## 6. Never-post / exclusion list

Do not add these unless a current portal record, current policy, or a signed
order **directly** supports them; otherwise list them in the template's
exclusion section with the template's `reason_code`:

account-management / maintenance fee, collection / referral fee, late-payment
fee, DMV / reinstatement / notice fee, returned-check fee, traffic-school /
program fee, restitution (unless a restitution order exists), court-appointed-
attorney fee, court-reporter fee, copy / certification fee, **stale-schedule
amounts**, and **statutory-maximum substitutions**. Typical reason codes:
`stale_schedule`, `not_current_policy`, `no_triggering_event`,
`unsupported_post_disposition`, `not_in_hearing_order`, `no_order_or_policy_support`,
`not_part_of_balance`, `continued_pending_no_final_order`. A sticky-note/"should
we add…?" fee with no hearing-minute triggering event is always excluded.

## 7. Payment / installment math

Let `B` = starting balance made of supported line items only (see §5–§6). If a
down payment is approved (from the order or `policy.down_payment_required`),
subtract it first and schedule the remainder. With approved regular installment
`M` (see §8 for choosing/validating `M`):

- `full = floor(B / M)` ; `remainder = round(B - full*M, 2)`.
- If `remainder == 0`: `total_installments = full`; every installment is `M`;
  `final_payment_amount = M`.
- If `remainder > 0`: there is one smaller final payment;
  `full_payment_count = full`, `total_installments = full + 1`,
  `final_payment_amount = remainder`.
- If `B <= M`: a single installment equal to `B`.
- `first_due_date`: use the court-approved date if the notes/petition state one;
  otherwise derive from policy (`first_due_days` after submission/disposition, or
  the jurisdiction's stated convention such as "the 15th of the next month after
  disposition"). Honor a candidate date supplied in the payload when consistent.
- `final_due_date` = `first_due_date` advanced by `(total_installments - 1)`
  intervals (months for a monthly plan).
- `return_to_court_date` = the approved/candidate date if given, else
  disposition/first-due date + `policy.return_to_court_offset_days`.
- For a deferred single-due plan, interval = the template's deferred value and
  there is one payment of the full balance on the single due date.

## 8. Budget & support classification (financial petitions / VA packets)

- `disposable = monthly_income - monthly_obligations`.
- Policy band = `[policy.min_monthly, policy.max_monthly]`.
- Choose/validate the monthly amount `M` against the requested amount, the band,
  and disposable income, then set the support classification using **that
  template's enum**:
  - below the band ⇒ `below_policy_minimum`;
  - above the band ⇒ `above_policy_maximum`;
  - above disposable income ⇒ `unsupported_by_budget` (or `needs_judge_review`);
  - within band and affordable ⇒ `supportable` / `supported_by_budget`.
- **Account fee**: include only if `policy.account_fee > 0` and policy notes
  permit (e.g. non-indigent). A worksheet/counter fee row where the policy fee is
  `0` (or the petitioner is on public assistance/indigent) ⇒
  `excluded_by_policy`.
- **Payment application order**: if `policy.restitution_priority` puts
  restitution first **and** `restitution_balance > 0` (or the petitioner
  requests it and policy allows) ⇒ `restitution_before_fines_costs`; if
  restitution is `0` or priority is "Not applicable" ⇒ `fines_costs_only`.
- `total_due` = supported `fines_costs_balance` + `restitution_balance` +
  (`account_fee` only if included). Exclude everything in §6.
- **Petition classification**: first/current petition ⇒ `initial_installment`;
  second / default-review ⇒ `subsequent_review`; deferred single payment ⇒
  `deferred_payment`; exempt/no-ability ⇒ `exempt_no_payment`. Derive from
  `petition_sequence` / intake sequence label / `default_status`.

## 9. Forms, probation & license orders

- **Form id/label**: from `/api/forms` for the jurisdiction; `required_fields`
  and `placeholder_instruction` come from that record. `required_labels_used`
  (traffic plan) come from the labeled sections of the local form excerpt.
- **Account reference** (traffic): if no separate circuit case/account number
  exists, use the **citation number** as the account reference (per form rule).
- **Probation referral (CC-1375-style)**: `prepare_referral` only if supervised
  probation was ordered **and** a referral is required/signed; take
  `report_datetime` and term from the intake. If no supervised probation or no
  signed referral ⇒ `not_ordered` and `report_datetime = null`.
- **License order (CC-1379-style)**: `license_start_basis` defaults to
  `conviction_date` — a release-from-confinement date is memo context and does
  **not** replace the conviction date for the suspension consequence unless the
  sentence/law ties it to release/petition date. `suspension_end_date =
  start + suspension_months`. `driver_license_number` = placeholder unless
  present in the materials.

## 10. Totals, registers & exclusions

- Sum only **posted** amounts across **included** (disposed) matters for
  fine/cost/assessment/user-fee subtotals and the grand/batch total.
- Count disposed (entered) vs held/excluded matters as the template's total
  fields require.
- Held/deferred/pending/continued matters stay **out** of the disposed register
  and totals; list them in the template's exclusion/hold section with the
  matching reason code, a `financial_posting_allowed = false` flag if present,
  and a next-status-check date if required.

## 11. Self-check before returning

- Output parses as JSON and contains **exactly** the template's required
  top-level keys — nothing extra, nothing missing.
- Every enum value is drawn from the template's allowed list, spelled exactly.
- All money has two decimals; all dates/datetimes/times match the required
  formats; `null` appears only where allowed.
- Lists obey the template's ordering rules.
- No invented identifiers/fees/charges; placeholders use the exact required
  string.
- Every held/deferred matter is excluded from disposed totals and appears in the
  hold/exclusion section.
- Every posted fee traces to a current fee-schedule row effective on the
  disposition date; every excluded item has a valid reason code.
- Totals recompute correctly from the per-matter posted amounts.

See `references/reconciliation_playbook.md` for a compact, per-task-type
walkthrough of these rules.
