---
name: court-clerk-closeout
description: >-
  Reconcile local court case materials against a Court Operations Portal API
  and produce structured JSON closeout answers matching a supplied answer
  template.  Handles audit conflict resolution, fee reconciliation, payment-
  plan structuring, probation and license order forms, placeholder handling,
  and register exclusions.  Use when a task involves cross-referencing court
  hearing notes, memos, finance extracts, sentencing records, or petition
  summaries against a court portal to produce a templated clerk-ready answer.
license: MIT
---

# Court Clerk Closeout Skill

## What this skill does

Produces structured, clerk-ready JSON closeout packages by reconciling local
court case materials (hearing notes, audit memos, finance extracts, petition
intake summaries, form excerpts) against live records from a Court Operations
Portal REST API.  The output is always a single JSON object that conforms
exactly to an answer template supplied alongside the task.

## When to apply this skill

Apply when the task description:

- Mentions a "Court Operations Portal" with a `<TASK_ENV_BASE_URL>`.
- Supplies an `answer_template.json` payload that defines the output shape.
- Includes local payloads (`.md`, `.json`, `.csv`) that must be cross-checked
  against the portal.
- Asks for a clerk-ready JSON answer covering case dispositions, fee
  reconciliation, payment plans, probation referrals, or license orders.

## Operating rules

### 1.  Order of operations

Carry out steps in this fixed sequence.  Do not skip or reorder.

1. **Read the prompt** -- extract the target case/citation/petition numbers,
   the `<TASK_ENV_BASE_URL>`, the list of available portal endpoints, and the
   path to the answer template.

2. **Read the answer template** -- note every `required_top_level_key`,
   `ordering_rules` entry, `enum` list, `field_type`, and instruction
   (currency precision, date format, sort direction).  The final output must
   satisfy every constraint defined here.

3. **Read every local payload** -- ingest all documents in the provided
   `input/payloads/` directory.  Treat local documents as the primary source
   for case events (hearing dispositions, bench rulings, clerk notations,
   fee-order decisions).  Payloads often carry corrections that override stale
   data in the finance queue or older CMS screens.

4. **Query the portal for each target matter** -- use the exact endpoint names
   listed in the prompt (e.g. `GET /api/cases`, `GET /api/charges`,
   `GET /api/fee-schedules`).  Query parameters depend on the endpoint:

   - Cases / citations: pass `?case_number=` or `?citation_number=` with the
     target identifier.
   - Fee schedules / payment policies / forms / jurisdictions: retrieve the
     full list when no filter is obvious, then select the row matching the
     subject jurisdiction and effective date.
   - Search: use for defendant-name lookups when a case number is not the only
     key (e.g. traffic citations that may have a case-number alias).

5. **Reconcile conflicts** -- see Section 2 below.

6. **Build the output object** -- see Section 3 below.

7. **Return JSON only** -- no markdown fences, no prose, no commentary.
   Exactly the shape the answer template demands.

### 2.  Reconciliation rules

When local payloads and portal records disagree, resolve using the following
hierarchy.  The answer template's `resolution_source` enum encodes this:

| Priority | Source                    | When to use                                                |
|----------|---------------------------|------------------------------------------------------------|
| 1        | Hearing notes / bench     | Judge's in-court statements, signed orders, oral rulings   |
| 2        | Corroborating memos       | Clerk audit memos, supervisor notes, formal corrections    |
| 3        | Fee schedule (portal)     | Current financial amounts, assessment rates, policy caps   |
| 4        | CMS / portal record       | Identity (DOB, name spelling) when no local override       |

Additional reconciliation principles:

- **Identity conflicts**:  If the hearing note or audit memo corrects a
  defendant name or DOB, use the corrected value.  If DOB is genuinely missing
  from all sources, use the placeholder `TBD from case file` and flag it.

- **Counsel conflicts**:  Calendar abbreviations (e.g. "APD") may be
  misleading.  When the hearing record or defense memo says the attorney is
  appointed private counsel, classify as `appointed_private`, not
  `public_defender`.  Public-defender user fees must not be posted for
  appointed-private cases.

- **Fee schedule staleness**:  Finance-queue amounts that reference an
  archived or prior-year dollar value must be replaced by the current fee
  schedule from the portal.  Flag the stale amount as a reconciliation item.

- **Departure / sentence label conflicts**:  When a legacy screen or draft
  worksheet carries a departure label but the judge's oral pronouncement
  (recorded in hearing notes) explicitly states no departure, remove the
  departure label and mark the audit finding.

- **Case status**:  If the docket note or hearing record states that a final
  order was *not* signed, the case is not disposed.  Set status to
  `pending`/`deferred`/`continued`, do not post financial entries, and exclude
  it from the disposed register.

### 3.  Output construction

#### 3a.  Structural conformance

- Every `required_top_level_key` in the answer template must appear in the
  output at the top level.
- Items within arrays must contain every `required_key` listed for that item
  type in the template.
- Enum values must be drawn **only** from the template's enum lists.  Never
  coin a new value or substitute prose.

#### 3b.  Typing and formatting

- **Currency**:  numeric values, two decimal places (e.g. `150.00`, not
  `150`).
- **Dates**:  ISO `YYYY-MM-DD`.
- **Date-times**:  ISO local `YYYY-MM-DDTHH:MM:SS` when the template calls for
  `datetime`.
- **Null**:  use `null` (JSON null) only when the template explicitly allows
  it; otherwise use a placeholder string.

#### 3c.  Sorting

Apply every `ordering_rules` entry from the template.  The canonical sort key
varies by task type:

- By `case_number` ascending for criminal/sentencing dockets.
- By `citation_number` ascending for traffic dockets.
- By `petition_id` ascending for petition packets.
- Within audit findings, secondary-sort by `issue_type`.
- Within exclusions, sort by the item name or charge code ascending.

#### 3d.  Financial reconciliation entries

- Map each fee line from the local materials/portal to the fee codes the
  template defines.
- Cross-check every amount against the current fee schedule (portal).
- Flag unsupported items (those not backed by a court order, current schedule,
  or policy) with status `exclude` and a reason code.  Unsupported items must
  still be listed in fee reconciliation (so the clerk sees what was removed)
  but their amounts must not flow into `case_total` or register totals.

#### 3e.  Payment-plan arithmetic

When the template requires a payment schedule:

- `total_due` = fines_and_costs + restitution + account_fee (if supported).
- `regular_installment_amount` = approved monthly payment.
- `total_installments` = floor(total_due / regular_installment_amount).
- `final_payment_amount` = total_due - (regular_installment_amount * total_installments).
  When the final payment equals the regular installment (balance divides
  evenly), final_payment_amount still equals the regular installment.
- `final_due_date` = first_due_date + (total_installments - 1) months.
- `return_to_court_date`: use the candidate date from the petition summary; do
  not invent one.

Cross-check the approved monthly amount against the payment policy band from
the portal (minimum / maximum).  Classify the support level using the
template's enum (e.g. `supported_by_budget`, `below_policy_minimum`).

#### 3f.  Probation and license forms

- **CC-1375 (probation referral)**:  Only prepare when a supervised probation
  order was signed.  If the sentencing notes say no referral order was signed,
  set status to `not_ordered`.  Use the conviction date as the referral date
  basis.
- **CC-1379 (license suspension)**:  The suspension start date derives from
  the `license_start_basis` in the template -- typically the conviction date
  for DUI matters.  Suspension end date = start date + suspension months.
- When the driver's license number is missing from all case materials and the
  portal, use the placeholder `TBD from case file`.

#### 3g.  Placeholder handling

- Missing personally identifiable information (SSN, driver's license number,
  addresses, phone numbers, attorney/judge/probation-officer contact details)
  must be recorded as `TBD from case file`.
- Do **not** invent identifiers, contact details, or missing field values.
- When multiple fields are missing for a case, list each one in a
  `missing_fields` array sorted alphabetically.

#### 3h.  Exclusions and register items that must stay out

Exclude from the register (financial posting) any item that:

- Belongs to a case without a signed final order (continued/pending).
- Is a fee type the current fee schedule or payment policy does not support.
- Has no triggering event in the hearing record (e.g. late-payment fee when
  the case was never late, DMV fee when no DMV referral was ordered).
- References a stale or superseded schedule amount.

Every excluded item must be documented with a reason code from the template
and the case/citation it applies to.

#### 3i.  Register / batch totals

- Sum financial totals **only** for disposed cases whose fee status is `post`.
- Held, pending, and excluded cases contribute zero to totals.
- `grand_total` = sum of fine_total + court_cost_total + assessment_total +
  user_fee_total (or the equivalent category breakdown the template defines).

### 4.  API interaction patterns

- Use `<TASK_ENV_BASE_URL>` exactly as provided -- no trailing slash
  manipulation.
- Always check the response status; a 200 with an empty array means no record
  exists for that query.
- Fee schedules and payment policies returned by the portal may contain
  effective-date ranges.  Select the row that covers the case disposition
  date.
- The `/api/search` endpoint can be useful for disambiguating similarly-named
  defendants or finding case records when the primary key is uncertain.

### 5.  Common pitfalls to avoid

- **Do not** carry forward stale fee amounts from a finance queue or old
  worksheet without cross-checking the current portal schedule.
- **Do not** treat "APD", "PD", or similar calendar abbreviations as
  definitive -- verify against the hearing record or defense memo.
- **Do not** post financial entries for cases where the hearing notes or
  docket records say the final order was not signed.
- **Do not** invent monetary amounts, dates, identifiers, or contact details
  that are absent from both local materials and portal records.
- **Do not** reorder top-level keys or nest items incorrectly -- follow the
  answer template's structure exactly.
- **Do not** wrap the output in markdown code fences.
- **Do not** include an account-management, collection, late, DMV,
  restitution, copy, or certification fee unless the portal record or current
  schedule directly supports it for the specific matter.
