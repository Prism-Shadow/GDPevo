# Court Clerk Post-Hearing Reconciliation and Financial Packet Skill

## Overview

This skill prepares structured post-hearing or post-disposition reconciliation packets for
court clerk entry. It cross-references local case materials (hearing notes, clerk memos,
finance queue extracts, petition summaries, sentencing intake sheets, worksheet CSVs, and
local form excerpts) against the **Court Operations Portal** (`<TASK_ENV_BASE_URL>`) to
produce a single JSON answer conforming to an attached `answer_template.json`.

The skill handles criminal sentencing closeouts, traffic-violation payment-plan packets,
post-sentencing field packets (including CC-1375 probation referrals and CC-1379 license
suspension / installment orders), and multi-case criminal disposition registers.

## When to Use

Invoke this skill when the task involves:

- Closing out a criminal docket or traffic-violation hearing.
- Reconciling financial entries (fines, court costs, assessments, user fees) across
  multiple sources.
- Preparing post-sentencing form packets (probation referral, license suspension,
  installment payment orders).
- Identifying audit conflicts in defendant identity, counsel, status, fee schedules,
  or departure findings.
- Producing batch register totals with disposed and held/pending case counts.

## Workflow

Follow these steps for every task. Do not skip cross-reference steps.

### Step 1 — Orient

1. **Read the prompt** (`prompt.txt`). Note:
   - The court/jurisdiction, hearing date, and docket type.
   - The target case numbers, citation numbers, or petition IDs.
   - Which portal endpoints the prompt explicitly lists.
2. **Read every file in `input/payloads/`.** These are local materials such as:
   - Hearing or courtroom notes (may contain bench shorthand, nicknames, or
     carry-forward values from prior docket sheets).
   - Clerk audit memos listing known exceptions and supervisor notes.
   - Finance queue extracts or worksheets (CSV or JSON) with queued fee lines.
   - Local form excerpts describing form families and required fields.
   - Payment petition summaries with budget data and requested payment terms.
   - Sentencing intake sheets with the official conviction and sentence posture.
3. **Read the `answer_template.json`** in the payloads directory. This schema is the
   contract for the output. Note every required key, enum, field type, sort order,
   currency precision, and date format. If the template defines ordering rules, those
   rules are mandatory.

### Step 2 — Query the Portal

The portal base URL is `<TASK_ENV_BASE_URL>` (at generation time this resolves to the
running environment network address; ignore any `localhost`, `127.0.0.1`, or
`env/setup.sh` references in local task materials).

Available read-only endpoints (all `GET`):

| Endpoint | Key query parameters | Returns |
|---|---|---|
| `/api/jurisdictions` | none (list all) | Jurisdiction records with `jurisdiction_code`, `policy_ref`, court name, county, state, timezone. |
| `/api/cases` | `case_number`, `jurisdiction_code` | Case records: defendant name, DOB, counsel type and attorney name, status, disposition date, judge. |
| `/api/charges` | `case_number`, `jurisdiction_code` | Charge records per case: count number, offense code, statute, plea, disposition, fine, jail days imposed/suspended, probation months, departure type. |
| `/api/docket-entries` | `case_number`, `jurisdiction_code` | Docket entry log: entry date, type (filing, hearing, disposition, financial, clerk_note), text, source system. |
| `/api/citations` | `citation_number`, `jurisdiction_code` | Traffic citation records: defendant name, DOB, speed, zone, statute, violation code, plea, disposition, payment plan fields. |
| `/api/fee-schedules` | `jurisdiction_code` (optional) | Fee schedule entries: fee type, amount, effective/end dates, jurisdiction, mandatory flag, violation code, label. **Always filter out stale (expired) schedule entries whose `end_date` is before the disposition date.** |
| `/api/payment-policies` | `jurisdiction_code` (optional) | Payment plan policy: min/max monthly, first-due offset days, return-to-court offset, restitution priority, account fee policy. |
| `/api/forms` | `jurisdiction_code` (optional) | Form metadata: form_id, label, jurisdiction, required fields, placeholder instructions. |
| `/api/financial-petitions` | `petition_id`, `case_number` | Financial petition records: petitioner name, income, obligations, balances, requested monthly amount, default status. |
| `/api/search` | `q` (search text) | General text search across all record types. |

**Query strategy:**

- For each target case/citation, fetch its case or citation record, its charges (if
  criminal), and its docket entries.
- Fetch the jurisdiction's fee schedules and payment policies.
- If forms are referenced in the answer template (e.g., CC-1375, CC-1379), look up
  their metadata via `/api/forms` filtered by jurisdiction.
- If petitions are involved, fetch them via `/api/financial-petitions`.
- When the prompt calls for form labels or account references, cross-check portal
  form metadata.

### Step 3 — Cross-Reference and Identify Conflicts

Compare **every** data point from local payloads against the portal records. Flag
every mismatch. The portal is the system of record for identity and form metadata;
local hearing notes and corroborating memos can override legacy/draft financial
worksheets.

Common conflict categories (canonical set):

| Conflict | What to compare | Typical source of truth |
|---|---|---|
| **Identity** | Defendant name spelling, DOB | Portal case/citation record (`use_cms`) for identity; corroborating memo can confirm DOB corrections. |
| **Counsel** | Counsel type and attorney name | Portal record or corroborating memo. A local `PD` label on a worksheet may be incorrect if a defense memo or judge clarified the attorney is appointed private counsel (not the public defender office). |
| **Status** | Disposition status (disposed / deferred / pending / continued) | Hearing notes and portal docket entries. A draft worksheet showing "disposed" is overridden if the judge did not sign a final order. |
| **Fee schedule** | Fee amounts and applicability | Portal fee schedules filtered to the disposition date. An older local worksheet or intake sheet may carry stale amounts (e.g., a 2023 drug assessment for a 2025 disposition). Always use **current** portal schedules. |
| **Departure** | Departure finding (none / durational / dispositional) | Hearing notes or courtroom audio. A legacy charge screen or draft sentence worksheet may carry a departure label that the judge expressly rejected in open court. |

For every conflict identified, document:
- Which case it applies to.
- What the conflicted (local/draft) value is.
- What the corrected value should be.
- How it was resolved (which source was used).

### Step 4 — Resolve Conflicts

Apply these precedence rules:

1. **Signed court order or on-the-record judge statement** (as captured in hearing
   notes) overrides any worksheet, queue extract, or legacy system value.
2. **Portal case/citation record** (CMS) is authoritative for defendant identity
   (name spelling, DOB) unless a corroborating memo with specific correction
   overrides it.
3. **Portal fee schedules** override any locally carried fee amounts. Use the
   schedule entry whose effective date covers the disposition date and whose
   `end_date` is null or after the disposition date.
4. **Portal payment policy** controls installment plan parameters (min/max monthly,
   first-due offset, account fee treatment, restitution priority).
5. **Portal form metadata** controls form IDs, labels, and required fields.
6. **Corroborating memo** (clerk audit memo, supervisor note) overrides worksheet
   labels that are contradicted by specific evidence (e.g., a calendar abbreviation
   "APD" that the judge clarified means appointed private, not public defender).
7. **Draft/worksheet only** materials that lack a signed order or portal confirmation
   must be held — do not post them.

### Step 5 — Reconcile Finances

For every disposed case/citation, build a reconciled fee entry:

1. **Start with mandatory fees** from the portal fee schedule for the jurisdiction:
   - Court costs (`court_cost`, `fee_type: "court_cost"`) — mandatory, amount per
     the schedule.
   - Crime lab fee (`fee_type: "assessment"`) — mandatory only for controlled-substance
     convictions where the schedule mandates it.
   - Fines — use the amount the judge pronounced, not a stale worksheet figure.
   - Drug assessment — use the current portal schedule amount for the disposition
     year, not an archived amount.
   - Public defender user fee — apply only when counsel is classified as
     `public_defender`; do NOT apply for `appointed_private` or `retained` counsel.
   - County surcharge — apply per the schedule (typically once per citation).
2. **Exclude unsupported charges.** The following are NEVER added unless a portal
   record or current policy explicitly supports them:
   - Account-management / payment-plan service charges
   - Collection referral fees
   - Late-payment fees / interest
   - DMV notice/reinstatement fees
   - Returned-check fees
   - Restitution (without a court order)
   - Court-appointed attorney fees (without an order)
   - Court reporter fees (without an order)
   - Traffic-school program fees (not ordered)
   - Copy/certification fees
   - Stale/archived fee amounts (end_date before disposition date)
3. **For held/pending cases**: fee status is `hold` (or equivalent), fee items are
   empty or zeroed, and the case total is `0.00`. Do not post financial entries for
   cases awaiting a signed order.
4. **For payment plan cases**: calculate the installment schedule using the total
   due and the approved monthly payment amount per the jurisdiction's payment policy.
   - `full_payment_count = floor(total_due / monthly_payment)` — number of full
     installments.
   - `final_payment_amount = total_due - (full_payment_count * monthly_payment)` —
     the smaller final payment (0 if the total divides evenly).
   - `total_installments = full_payment_count + (final_payment_amount > 0 ? 1 : 0)`.
   - `final_due_date` = first due date advanced by (total_installments - 1) months.
   - `return_to_court_date` = final due date + policy's `return_to_court_offset_days`.

### Step 6 — Build the Output

1. **Follow the answer template exactly.** Every required key at every nesting level
   must be present. Use the exact enum values defined in the template.
2. **Sort** all arrays per the template's ordering rules (typically by `case_number`,
   `citation_number`, or `petition_id` ascending; for excluded items, by item name
   ascending).
3. **Currency:** All money values as JSON numbers with exactly two decimal places
   (e.g., `150.00`, not `150` or `"$150.00"`).
4. **Dates:** ISO 8601 `YYYY-MM-DD`. Date-times: ISO 8601 local `YYYY-MM-DDTHH:MM:SS`.
   Use `null` for dates that should not be entered (e.g., no disposition date for
   pending cases).
5. **Placeholders:** For fields required by a form but genuinely missing from all
   case materials, use `"TBD from case file"` — do NOT invent identifiers, addresses,
   phone numbers, SSNs, driver license numbers, or contact details.
6. **Register/batch totals:** Sum financial values only from disposed/assessed cases,
   excluding held/pending matters. Counts must match: `assessed_case_count` is the
   number of disposed cases with financial entries; `held_case_count` is the number
   excluded from the register.

## Portal Query Patterns

When querying the portal, construct URLs as:

```
<TASK_ENV_BASE_URL>/api/cases?case_number=<case>
<TASK_ENV_BASE_URL>/api/charges?case_number=<case>
<TASK_ENV_BASE_URL>/api/docket-entries?case_number=<case>
<TASK_ENV_BASE_URL>/api/citations?citation_number=<citation>
<TASK_ENV_BASE_URL>/api/fee-schedules?jurisdiction_code=<code>
<TASK_ENV_BASE_URL>/api/payment-policies?jurisdiction_code=<code>
<TASK_ENV_BASE_URL>/api/forms?jurisdiction_code=<code>
<TASK_ENV_BASE_URL>/api/financial-petitions?petition_id=<id>
<TASK_ENV_BASE_URL>/api/financial-petitions?case_number=<case>
```

The portal returns JSON with a `count` integer and a `results` array. An empty
results array means no matching record was found — do not invent data in that case.

## Reconciliation Rules Reference

### Counsel Classification

| Portal/Local Label | Classification | Public Defender Fee? |
|---|---|---|
| `public_defender`, "PD" confirmed by hearing notes or portal | `public_defender` | Yes |
| `appointed_private`, "APD" clarified as appointed private by judge/memo | `appointed_private` | No |
| `retained`, "RET" | `retained` | No |
| `unknown` or genuinely ambiguous | `unknown` | No |

### Fee Schedule Precedence

For a given fee type and jurisdiction, prefer the schedule entry where:
- `effective_date <= disposition_date`
- `end_date` is `null` or `end_date >= disposition_date`
- Higher `priority` value among equally valid entries indicates the more current
  schedule.

Stale entries (with a past `end_date`) are for audit trail only and must not be
applied to current dispositions.

### Departure Status Resolution

| Situation | Departure Status |
|---|---|
| Judge expressly stated no departure / top-of-range | `no_departure` or `none` (per template enum) |
| Legacy/draft worksheet says departure but judge contradicted it on record | Follow the judge's on-record statement |
| Misdemeanor conviction in a jurisdiction that does not evaluate departure for misdemeanors | `not_evaluated_misdemeanor` |
| Case is continued/pending with no final sentence | `not_entered_pending` |
| No departure mentioned in any source | `not_applicable` or `none` (per template enum) |

### Docket Entry Summary Codes

Derive the summary code from the case facts:

| Condition | Summary Code |
|---|---|
| Guilty finding + no public defender fee (appointed private or retained) | `conviction_no_pd_fee` |
| Guilty finding + drug assessment applied | `conviction_drug_assessment` |
| Guilty finding + no departure | `conviction_no_departure` |
| Case deferred / order not signed | `hold_unsigned_order` |

### Excluded Financial Item Categories

When the template or local materials list items to exclude, tag each with the
appropriate reason:

| Reason | When to Use |
|---|---|
| `no_order_or_policy_support` | No court order or portal policy authorizes the charge. |
| `not_part_of_balance` | The item is outside the scope of the current balance (e.g., DMV reinstatement is a separate agency fee). |
| `stale_schedule` | The amount comes from an expired fee schedule. |
| `unsupported_post_disposition` | The fee type is not supported in the post-disposition context. |
| `not_current_policy` | Current payment policy does not include this fee. |
| `no_triggering_event` | The fee would require a triggering event (default, late payment, returned check, DMV referral) that has not occurred. |
| `not_in_hearing_order` | The hearing order did not include this charge. |

## Common Task Patterns

### Criminal Sentencing Closeout (AR)

Target cases with hearing notes + audit memo + finance queue extract. Output includes:
`audit_findings`, `case_dispositions` (with charge summaries), `fee_reconciliation`,
`docket_entries`, `register_totals`.

Key checks: identity (name/DOB), counsel classification, status/closeout action, fee
schedule currency, departure status, and whether any case is held unsigned.

### Traffic Violation Closeout with Payment Plans (OR)

Target citations with hearing closeout notes + local form excerpt. Output includes:
`matters` (disposition, financial entry, payment plan, form entry), `excluded_charges`,
`batch_totals`.

Key checks: speed tier → violation code → fee schedule mapping, payment plan installment
math, form ID/label from portal, account reference (citation number when no separate
case/court account exists), stale schedule exclusion.

### Post-Sentencing Field Packet (VA)

Single or multiple cases with sentencing intake facts + payment petition budget +
form field excerpt. Output includes: case memo, CC-1375 probation referral, CC-1379
license/installment order, budget review, placeholder fields, excluded financial items.

Key checks: license suspension start date basis (conviction date or release date per
the template), probation referral required only when ordered, installment amount
supported by budget analysis (compare requested amount to disposable income and policy
bands), placeholder for every missing identifier/contact, account fee excluded per
policy unless jurisdiction mandates it.

### Criminal Disposition Register (AR)

Multiple target cases with hearing notes + finance worksheet CSV. Output includes:
`case_audit`, `dispositions`, `fee_entries`, `docket_register` (entries + totals),
`exclusions`.

Key checks: audit flags for each case (amended charge, lab fee omission, missing DOB,
confused counsel label, no final order), DOB placeholder when genuinely missing,
continued/pending cases excluded from financial posting with a next-status-check date,
batch totals summing only disposed cases.

## Output Validation Checklist

Before returning the answer, verify:

- [ ] Every required top-level key from the answer template is present.
- [ ] Every required nested key within each item is present.
- [ ] All enum values match the template's allowed values exactly.
- [ ] All arrays are sorted per the template's ordering rules.
- [ ] All money values are numeric with exactly two decimal places.
- [ ] All dates are ISO format or `null` where appropriate.
- [ ] No fee appears that lacks portal schedule or policy support.
- [ ] No identifier or contact detail was invented — missing ones use `"TBD from case file"`.
- [ ] Portal query results were cross-referenced against every local payload.
- [ ] All identified conflicts are documented with their resolution source.
- [ ] Register totals add up correctly and exclude held/pending cases.
