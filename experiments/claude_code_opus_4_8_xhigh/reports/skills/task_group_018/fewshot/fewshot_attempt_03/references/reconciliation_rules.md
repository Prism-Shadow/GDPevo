# Reconciliation & posting rules

These rules resolve conflicts between the local payloads (worksheets, finance-queue
extracts, hearing notes, audit memos, petition summaries) and the portal. They are
the substance of every task in this family. Apply them, then format to the current
`answer_template.json`.

## 1. Source-of-truth precedence (highest wins)

1. **Signed court record / courtroom outcome** — the hearing notes, closeout
   note, audit memo, or sentencing intake that record what the judge actually
   did. Governs: plea, finding/conviction, whether a count was **amended** or
   **dismissed**, whether an order was **signed**, judge's **departure** ruling,
   fine announced/waived, first-due date if the court set one, next court
   setting. If **no signed/final order** exists → the matter is held/excluded;
   post **no** financials for it.
2. **Portal CMS** (`cases`, `charges`, `citations`) — authoritative for
   **identity** (name spelling, DOB), **counsel_type**, **offense_code /
   statute / severity**, and **structured sentence numbers** (jail days
   imposed/suspended, probation months, fine amount, `departure_type`) *for any
   field the court record leaves unstated*.
3. **Portal fee schedule / payment policy / forms** — authoritative for
   **amounts**, installment band, first-due & return-to-court offsets, account
   fee, restitution priority, form id/label/placeholder text.
4. **Local worksheet / finance-queue / draft sheet** — LEAST authoritative.
   These are the material *being audited*. Use them only to surface conflicts;
   never adopt their value when a higher source disagrees.

**Audit findings** = each place a lower source conflicts with a higher one.
Record the conflicted value, the corrected value, and which source resolved it,
using the template's `issue_type` / `resolution_source` (or equivalent) enums.
Typical resolution tags: identity/DOB → use CMS; counsel mislabel → use the
corroborating memo or court record; stale amount → use current fee schedule;
draft/unsigned → hold; judge overrode a legacy departure → use hearing notes.

## 2. Identity & placeholders — never invent

- Use the CMS name spelling and DOB. If the target's own record has no DOB (and
  the notes say verify from the file / do not borrow), emit the **exact required
  placeholder string** (e.g. `TBD from case file`) and flag "verify", rather
  than copying a similarly-named row.
- Missing identifiers/contacts required by a form (SSN, driver-license number,
  mailing/residence address, phone, probation officer, probation-office
  location) → the required placeholder string. Choose the template's
  `reason_code` by kind: identifier (SSN, DL#) vs contact (address/phone) vs
  office/party detail (probation officer/office).
- Collect every placeholder into the template's placeholder list, sorted as the
  template says (usually by field/case name ascending).

## 3. Counsel classification

- Take `counsel_type` from CMS, not `attorney_label_raw`.
- A court record / audit memo that explicitly reclassifies counsel overrides
  (e.g. an "APD"/"PD" calendar label the judge clarified as appointed-private,
  county-paid → `appointed_private`).
- Consequence: the **Public Defender User Fee applies only when the final
  counsel is `public_defender`** — not appointed-private, not retained.

## 4. Fees — post only what a current schedule or an order supports

For each posting case, build the fee set from the **current** jurisdiction
schedule (date-window match) plus court-ordered amounts:

- **Court cost** — mandatory current `court_cost` amount.
- **Fine** — the amount the court imposed (0 when waived). Confirm against the
  charge record.
- **Drug / crime-lab assessment** — apply **only when the actual conviction is a
  controlled-substance count** (charge `assessment_code = DRUG_ASSESSMENT` *and*
  the court record convicted on that count). If the count was **amended away or
  dismissed**, exclude the assessment even though the worksheet carried it.
  Use the **current** scheduled amount, not an archived one.
- **Public Defender user fee** — only if final counsel is `public_defender`
  (§3). Use current amount.
- **Traffic fine** — the current `standard_fine` for the matched
  `violation_code` tier, **plus** each mandatory `county_surcharge`. Not the
  statutory-maximum note, not a prior-year (stale) amount.

**Never add** account-management/maintenance, late-payment, collection-referral,
DMV/reinstatement, returned-check, copy/certification, traffic-school, restitution
(unless actually ordered), court-appointed-attorney, or court-reporter fees unless
a current schedule row or a signed order directly supports them. In the template's
exclusions list, record each with its reason (stale schedule; not in the hearing
order; not current policy; no triggering event; not part of balance for an
otherwise-real fee like DMV reinstatement) and count its included amount as 0.

## 5. Charge / disposition summary

Per convicted count, emit what the template asks: `count_no`, `offense_code`,
`plea`, `charge_disposition`, `fine`, jail days imposed/suspended, probation
months, departure. Rules:

- **plea / conviction** from the court record; fall back to the charge `plea`
  only when the record is silent. If the record says guilt was adjudicated,
  `charge_disposition` = guilty even if the portal `disposition` still reads a
  stale `nolle prosequi` / `dismissed`.
- **jail / probation / fine numbers** from the portal charge when the record does
  not state them.
- **amended / dismissed counts**: the conviction is the *amended-to* offense;
  count the original as an amended-away/dismissed count where the template tracks
  that.
- **departure_status** — map to the template's departure enum:
  - Court record explicitly says no departure / top-of-range → `no_departure`
    (override any portal `dispositional`/`durational`).
  - Otherwise take the portal `departure_type`: `durational` → durational,
    `dispositional` **with a real `departure_reason`** → dispositional.
  - A minimal/suspended-only disposition with no substantive departure finding,
    or a non-disposed (held/pending) matter → `not_applicable`
    (or the template's pending token).
  - If the template only distinguishes misdemeanor vs felony, a **misdemeanor**
    conviction → its "not evaluated (misdemeanor)" token and a felony with no
    departure → its "none" token.

## 6. Case status & register action

- Convicted with a signed order → `disposed` / enter disposition + financials.
- No signed/final order (draft, continued, status hold) → `deferred`/pending;
  hold financials; disposition_date `null` where the template allows; add to the
  exclusions list with the next status-check date and
  `financial_posting_allowed = false`.
- **Totals** (register/batch) sum **only posted** cases; count held/excluded
  cases separately. Provide each requested subtotal (fine, court cost,
  assessment/lab, user fee, grand total, disposed vs held counts).

## 7. Payment / installment orders

Balance = fines-and-costs balance (+ restitution balance **only if** the order
carries restitution). Add an account fee **only if** policy `account_fee > 0`
(the stale counter/worksheet "$25 account-maintenance" row is excluded when
policy account_fee is 0). Down payment = policy `down_payment_required`
(usually 0).

Use `scripts/finance_math.py` for the arithmetic (integer-cents safe):

- Installments: `full = floor(balance / monthly)`; `remainder = balance -
  full*monthly`. If remainder = 0 → total = full, final = monthly. If remainder
  > 0 → total = full + 1, final = remainder. Map onto the template's field names
  (some call the regular count `full_installment_count`/`full_payment_count` and
  the grand count `payment_count`/`total_installments`).
- Chosen monthly = the requested/approved amount **iff** it is within
  `[min_monthly, max_monthly]` and ≤ disposable income; otherwise classify with
  the template's support enum (`below_policy_minimum`, `above_policy_maximum`,
  `unsupported_by_budget` vs `supportable`/`supported_by_budget`). Policy band
  min/max come from the payment policy.
- **first_due_date** = the court-ordered first-due date if the minute/note gives
  one; otherwise `submitted_date` (or disposition date) + policy `first_due_days`.
- **final_due_date** = first_due + (total_installments − 1) months.
- **return_to_court_date** = final_due + policy `return_to_court_offset_days`.
- **payment_application_order**: if restitution is present, follow the policy's
  restitution priority (usually restitution before fines/costs); otherwise
  fines/costs only.

## 8. Forms & account references

- Use portal `form_id` / `label`; corroborate any local form excerpt against it.
- For a traffic matter with no separate case/account number, the **account
  reference is the citation number** (per the form rule).
- When a template asks which required form labels were used, list exactly the
  labels the local form excerpt names, using the allowed enum strings verbatim.

## 9. Output formatting (every task)

- Match `answer_template.json` **exactly**: the `required_top_level_keys`, nested
  keys, and enum tokens (emit enum values, never prose).
- Apply every ordering rule (usually sort arrays by case/citation/petition id
  ascending; sub-lists alphabetically).
- Money = number to two decimals; dates ISO `YYYY-MM-DD`; datetimes
  `YYYY-MM-DDTHH:MM:SS`; use `null` exactly where the template permits it.
- Return **JSON only** (no markdown) when the template/prompt says so.
