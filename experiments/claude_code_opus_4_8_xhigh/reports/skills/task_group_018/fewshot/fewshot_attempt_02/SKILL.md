---
name: court-closeout-reconciliation
description: >-
  Reconcile a court clerk closeout / post-disposition packet against the Court
  Operations Portal and emit the exact JSON required by answer_template.json.
  Use when a task gives you local court payloads (hearing/bench notes, finance
  queue or worksheet, financial petition + budget, form excerpts, audit memo)
  plus a Court Operations Portal base URL, and asks for a structured closeout:
  disposition register, identity/counsel audit, fee reconciliation, installment
  / extended payment plan, probation & license orders, or a post-sentencing
  field packet. Handles the AR criminal, OR traffic, and VA post-sentencing
  variants of these tasks.
---

# Court Closeout & Post-Disposition Reconciliation

## What these tasks are

A deputy-clerk task. You are handed **local paper-trail materials** (bench/hearing
notes, a finance queue or clerk worksheet, a financial petition + budget, form
excerpts, an audit memo) that are **known to be noisy** — they contain draft
values, stale carry-forwards, bench shorthand, ambiguous counsel labels, and
sticky-note "should we add X fee?" questions. Your job is to **reconcile them
against the authoritative Court Operations Portal** and produce one JSON object
that a clerk could post to the register.

The output shape, keys, enums, ordering, and rounding are dictated by the task's
`input/payloads/answer_template.json`. **That template is the contract** — read it
first and last. Field names and enum vocabularies differ from task to task; this
skill teaches the *method*, and you map the method's results onto whatever names
the template uses.

## Inputs you will get

- `input/prompt.txt` — the jurisdiction, target case/citation/petition IDs, the
  hearing/closeout date, and which output sections are wanted.
- `input/payloads/answer_template.json` — the required schema (keys, enums,
  ordering rules, currency/date formats). **Obey it exactly.**
- `input/payloads/*` — the noisy local materials (`.md`, `.json`, `.csv`).
- `environment_access.md` (repo root) — the portal base URL and allowed endpoints.

## Step 1 — Read the contract and the materials

1. Read `answer_template.json` end to end. Note the **top-level keys**, every
   nested object's **required keys**, the **enum lists**, the **ordering_rules**,
   and the currency/date/datetime formats. Build the output to match this exactly.
2. Read `prompt.txt` for the target IDs, jurisdiction, and the governing date
   (hearing date / disposition date / petition submitted date).
3. Read every payload. Treat their numbers and labels as **candidates to verify**,
   not facts.

## Step 2 — Query the portal (authoritative source)

Get the base URL from `environment_access.md` (`GDPEVO_ENV_BASE_URL=…`). Do **not**
hardcode it — it can change per task. All endpoints answer `GET`, return
`{"count": N, "results": [ … ]}`, and accept **exact-match filters by field name**,
e.g. `?case_number=…`, `?citation_number=…`, `?jurisdiction_code=…`,
`?petition_id=…`. The search endpoint takes `?q=…`.

Helper: `scripts/portal.sh <endpoint> [key=value ...]` (reads the base URL from
`environment_access.md` / `$GDPEVO_ENV_BASE_URL`). Example:
`scripts/portal.sh cases case_number=<TARGET_CASE_NUMBER>`.

Endpoint roles (full field list in `reference/portal_endpoints.md`):

| Endpoint | Authoritative for |
| --- | --- |
| `/api/jurisdictions` | jurisdiction_code, county, `policy_ref`, timezone |
| `/api/cases` | **identity** (defendant_first/last, `defendant_dob`), `counsel_type`, `attorney_name`, case `status`, `disposition_date` |
| `/api/charges` | count-level offense/statute/severity, plea, disposition, fine, jail days, probation months, departure, `assessment_code` — **but may be a stale screen; see Step 3** |
| `/api/citations` | traffic disposition, `violation_code`, speed/zone, approved plan values, `first_due_date` |
| `/api/fee-schedules` | **current** fee amounts by jurisdiction & type/violation_code |
| `/api/payment-policies` | installment band, `first_due_days`, `return_to_court_offset_days`, `account_fee`, `restitution_priority` |
| `/api/forms` | form_id, label, required_fields, `placeholder_instruction` |
| `/api/financial-petitions` | petition balances, `petition_sequence`, `default_status`, budget figures |
| `/api/search?q=` | fuzzy lookup — **look-alikes; never borrow identity from it** |

Always fetch the record for each target ID plus the jurisdiction's fee schedules,
payment policy, and relevant forms.

## Step 3 — Reconcile by source precedence

This is the heart of the task. Conflicts are deliberate. Resolve them with these
rules (full trap catalog in `reference/reconciliation_rules.md`):

- **Identity (name, DOB): the CMS `/api/cases` (or `/api/citations`) record wins.**
  If the CMS `defendant_dob` is `null`/absent and no reliable source supplies it,
  use the placeholder string the materials require (e.g. `TBD from case file`) and
  the "verify" identity action. **Never** copy a DOB from an `/api/search`
  look-alike hit.
- **Actual disposition (plea, finding, convicted vs amended/dismissed counts,
  fine, jail, probation, departure): the signed order / on-the-record hearing note
  for that hearing date wins over a stale CMS charge screen or a draft worksheet.**
  A CMS charge row can still show a superseded count, a departure, or an
  assessment that the amended conviction removed — trust the hearing note.
- **Counsel classification:** reconcile ambiguous raw labels (`APD`, `PD C. Hill`,
  `APPT PRIVATE`, `RET`) against the on-record clarification in the note/memo.
  "Appointed private counsel, county pay" = `appointed_private`, **not**
  `public_defender` — and it **suppresses the public-defender user fee**.
- **Fee amounts: the current portal fee schedule wins over any worksheet number.**
  Current = the row for that jurisdiction/type whose `end_date` is `null` and whose
  `effective_date` is on/before the disposition date. A row with a past `end_date`
  is stale — exclude it.
- **Departure:** an on-the-record "top of range / no separate departure finding"
  means no departure, even if a draft/CMS screen shows one. Misdemeanors are
  typically "not evaluated"; pending matters "not entered".
- **Unsigned / continued / deferred:** if no final order was entered, **do not post
  financials**. Set the hold/pending status, empty/zero the fees, use the hold /
  "no disposition" docket code, and add the matter to the exclusions list with the
  next status-check date from the note and posting-allowed = false.

Record each resolved conflict in the audit/`audit_findings` section using the
template's `issue_type` / `resolution_source` (or `audit_flag` /
`recommended_resolution`) enums — pick the enum value, never free prose.

## Step 4 — Fees, balances, and exclusions

Post a fee **only** if (a) it is on the current portal fee schedule for the
jurisdiction as mandatory/applicable, **or** (b) a signed order/hearing note
directly imposes it. Otherwise exclude it.

- **Discretionary fees** (e.g. public-defender user fee) post only when their
  trigger holds (counsel is public defender). **Account/maintenance fee** posts
  only when `payment-policies.account_fee > 0` for the jurisdiction.
- **Never invent** account-management, collection/collections-referral,
  late-payment, DMV/reinstatement, returned-check, traffic-school, copy,
  certification, restitution, court-appointed-attorney, or court-reporter fees.
  Each unsupported item goes in the exclusions list with the template's reason
  enum. Map the cause to the reason vocabulary the template provides, e.g.:
  stale/expired schedule → `stale_schedule` / `not_current_policy`; requires an
  event that never happened → `no_triggering_event` / `no_order_or_policy_support`;
  not in the signed order → `not_in_hearing_order`; unsupported substitution →
  `unsupported_post_disposition`; not part of the collectible balance →
  `not_part_of_balance`.
- **Total due** = sum of supported balances: fines & costs + restitution (if a
  balance exists) + surcharge (traffic) + current-schedule mandatory fees, minus
  everything excluded. Restitution is included in the balance when present; the
  policy's `restitution_priority` sets the `payment_application_order`.
- **Traffic fine tier**: take `violation_code` from the citation record, then read
  the matching current `standard_fine` (and `county_surcharge`) from the fee
  schedule. Tiers like "100 mph or greater" are keyed by the code, not by
  amount-over-limit alone.

## Step 5 — Payment / installment plans

When a plan is approved, compute it with the policy, not by guessing. Helper:
`scripts/installments.py` (see `--help`). The mechanics:

- `remaining = total_due − down_payment`. Working in cents:
  `regular_count = remaining // monthly` full installments of `monthly`, and a
  `final_payment_amount = remaining − regular_count·monthly` if it doesn't divide
  evenly; `total_installments = regular_count + 1`. (If it divides evenly, the last
  full payment is the final one.) Map these three quantities onto whatever names
  the template uses (`full_payment_count`/`full_installment_count`/`payment_count`,
  `final_payment_amount`, `total_installments`).
- **Validate the requested monthly against the policy band** `min_monthly..max_monthly`
  and against disposable income (`income − obligations`). Classify support with the
  template's enum (supported / below-minimum / above-maximum / needs-review).
- **first_due_date**: use the explicitly approved date if the note/citation states
  one; otherwise `submitted_date + first_due_days`. Validate any candidate date in
  the payload against this rule.
- **final_due_date** = `first_due_date` + `(total_installments − 1)` calendar months
  (same day-of-month).
- **return_to_court_date** = `final_due_date + return_to_court_offset_days`. Its
  time/trigger come from the policy/notes; absent a stated time, use the docket-call
  time evident in the materials.

## Step 6 — Forms, probation, license, placeholders

- **Form selection**: pick the `/api/forms` row for the jurisdiction and form
  family; use its `label`/`form_id` for the template's enum. Traffic account
  reference = the citation number when no separate account exists (per the form's
  `placeholder_instruction`).
- **Probation referral (CC-1375-style)**: if supervised probation was ordered,
  "prepare referral" with conviction date, term months, and report datetime from
  the notes. If no referral order was signed, mark "not ordered", term 0, report
  datetime null.
- **License order (CC-1379-style)**: suspension months from the sentence/worksheet;
  start basis is the **conviction date** (a release-from-confinement date does
  **not** replace it); `end = start + months` (calendar months). DL number →
  placeholder if unknown; DUI conviction → basis `dui_conviction`.
- **Placeholders**: use the exact required placeholder string **only** for
  form-required fields genuinely absent from all materials (SSN, driver license #,
  address, phone, probation officer/office). Never invent identifiers or contacts.
  Collect them into the placeholder list with the right reason enum
  (`missing_identifier` / `missing_contact` / `missing_office_detail` /
  `missing_party_detail`), sorted as the template instructs (and any `missing_fields`
  arrays sorted alphabetically).

## Step 7 — Totals, then format and self-check

- Recompute every total/count from the items you actually posted (assessed vs held
  counts, per-category fee sums, grand/batch totals). They must tie out to the
  line items.
- Emit **JSON only** if the template says so — no markdown, no commentary.
- Enforce the template's formats: ISO `YYYY-MM-DD` dates, `YYYY-MM-DDTHH:MM:SS`
  datetimes, money as JSON numbers rounded to two decimals, integers as integers,
  `null` exactly where allowed.
- **Enum discipline**: every enum-typed field must be a verbatim value from the
  template's list. Never substitute prose; use `verify_before_entry`-style values
  only when the template offers them and the fact is genuinely unresolved.
- **Apply every ordering rule** (sort arrays by the specified key, ascending).
- Final pass: for each required top-level and nested key in the template, confirm
  it is present, correctly typed, and sourced from the authoritative record or a
  reconciliation rule above — not from an unverified payload value.

## Reference files

- `reference/portal_endpoints.md` — every endpoint's fields and how to query them.
- `reference/reconciliation_rules.md` — the full conflict/trap catalog with the
  reasoning behind each resolution.
- `scripts/portal.sh` — curl wrapper for the portal.
- `scripts/installments.py` — installment schedule + date calculator.
