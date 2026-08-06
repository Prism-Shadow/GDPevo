# Reconciliation Field Guide

The recurring conflict classes across court closeout batches, with the canonical resolution for each. The exact enum tokens for an output come from the task's own `answer_template.json` — this guide names the categories and the standard handling; always map to the template's enum set verbatim.

## Identity (name / DOB)
- **Conflict:** Local worksheet/queue lists a misspelled surname (a dropped/extra letter or transposition) or a DOB off by one day.
- **Resolution:** Use the portal/CMS value as canonical. Record an `identity` audit finding when the schema has an audit section (conflicted_value = local, corrected_value = CMS, resolution_source = `use_cms` / `use_cms_identity`).
- **Missing DOB:** If the bench card left DOB blank and it cannot be confirmed from the portal, emit the prescribed placeholder (`TBD from case file`) and an `identity_action` of `use_placeholder_verify` / `verify_before_entry`. **Never** borrow a DOB from a similarly-named defendant in search results.

## Counsel classification
- **Conflict:** Local queue/label says `PD` or `APD` but a bench/corroboration memo clarifies the attorney is appointed-private (county-pay) or retained, not the public defender office.
- **Resolution:** Use the record-clarified classification (`appointed_private`, `retained`, `public_defender`). Record a `counsel` finding where supported.
- **Consequence:** An `appointed_private` case is **not** public-defender-user-fee eligible — do not add a `public_defender_user_fee` to it. Only `public_defender` cases carry that fee (and only when the bench did not waive it).

## Case status / closeout action
- **Conflict:** Local draft worksheet says "disposed/guilty/fine" but the docket shows the final order was never signed, or the matter was continued for status.
- **Resolution:** If no signed final order → status `deferred`/`continued`/`pending`, closeout action `hold_unsigned_order`/`no_closeout`, disposition `pending`/`continued_pending`, **no sentencing financial register entry**. Such matters are excluded from the disposed/assessed totals and counted as held/excluded.
- **Outcome mapping:** bench trial guilty → `bench_trial_guilty` (plea `not_applicable`); guilty plea → `guilty_plea` (plea `guilty`); no-contest adjudicated guilty → `no_contest_guilty` (plea `no_contest`); continued with no plea → `continued_pending` (plea `not_entered`).

## Departure status
- **Conflict:** Legacy/draft worksheet labels a sentence a "departure / mitigating" when the judge expressly called it top-of-range / presumptive.
- **Resolution:** Use `no_departure` (or `none`) when no departure finding was made. Reserve `durational_departure` / `dispositional_departure` for cases where a departure was actually entered. Misdemeanor-only outcomes where departure isn't evaluated use `not_evaluated_misdemeanor`; pending/continued matters use `not_entered_pending` / `not_applicable`.

## Fees / fee schedule
- **Conflict:** Local queue used an archived/`OLD` or prior-year amount (e.g. a drug assessment of 125 from a 2023 schedule vs the current 250).
- **Resolution:** Use the amount from the current schedule row effective on the disposition date. Record a `fee_schedule` finding when supported.
- **Missing fee:** If the local queue omitted a fee the bench expressly did not waive (e.g. a public-defender user fee on a PD case), add it from the current schedule.
- **Eligibility:** Only post `public_defender_user_fee` on `public_defender` cases without a waiver. Only post `drug_assessment` on the controlled-substance conviction. `court_cost` is mandatory on disposed matters (not on held/continued matters).
- **Unsupported fee classes to exclude** (unless portal record + current policy + triggering event all support them):
  account-management / account fee, collection / collection-referral, late-payment, returned-check, DMV notice/reinstatement, restitution (when no order), copy, certification, traffic-school, court-reporter, court-appointed-attorney. Each excluded item is listed in the schema's exclusion section with a reason code (e.g. `no_order_or_policy_support`, `not_part_of_balance`, `not_current_policy`, `no_triggering_event`, `not_in_hearing_order`, `stale_schedule`, `unsupported_post_disposition`).

## Totals / register
- **Per-matter total** = sum of the *corrected* posted fee items (fine + court_cost + assessments + applicable user fee). It is not the queued total.
- **Batch/register totals** sum **posted** matters only. Held/excluded matters contribute `0.00` and increment the held/excluded counter (e.g. `held_case_count`, `excluded_pending_count`), not the assessed/disposed counter.
- Docket entry: disposed matters get a `sentencing_order`-type entry with a `summary_code` reflecting the financials (e.g. conviction-with/without-assessment, with/without-PD-fee, no-departure); held matters get a `disposition_hold`-type entry with `summary_code` `hold_unsigned_order`; continued/excluded matters get a `CONTINUED_NO_DISPOSITION` docket code and `exclude_no_final_order` register action with a null entry date.

## Payment plan / installment schedule
- Build the schedule from the **approved** monthly amount and the **corrected** total balance:
  - `full_payment_count` = ⌊balance / monthly⌋
  - `final_payment_amount` = balance − (monthly × full_payment_count)  (only when nonzero)
  - `total_installments` = full_payment_count + (1 if remainder else 0)
  - `final_due_date` = first_due_date + (total_installments − 1) intervals
  - `final_payment_amount` equals the regular monthly when the balance divides evenly (no separate remainder).
- Return-to-court date derives from the policy offset or the candidate return date in the materials — not invention.
- Plan sequence: most traffic plans are entered *after* disposition → `post_disposition` / agreement_sequence `post_disposition`. Petition-based installment orders on a first petition → `initial_installment`.

## Budget / support classification
- disposable = monthly_income − monthly_obligations.
- Classify approved/requested monthly amount against the policy band:
  - amount < `min_monthly` → `below_policy_minimum`
  - amount > `max_monthly` → `above_policy_maximum`
  - within band → `supportable` (post-sentencing packet schema: `supported_by_budget`)
  - insufficient disposable income to cover the amount → `unsupported_by_budget` / `needs_judge_review`
- Account fee: use the policy `account_fee` amount and treatment. If policy excludes it (`account_fee = 0` / excluded-by-policy), set `account_fee_amount = 0.00` and `account_fee_treatment = excluded_by_policy`; never carry a stale local account-maintenance/account-management fee row onto the order.

## Payment application order
- Determined by policy restitution priority and whether a restitution balance exists.
- No restitution → `fines_costs_only`.
- Restitution exists and policy prioritizes restitution → `restitution_before_fines_costs`; otherwise `fines_costs_before_restitution`.

## License suspension (CC-1379)
- Start basis is normally `conviction_date` (the order's effective date is the conviction date, not the release-from-confinement date — release date is memo context only).
- suspension_end_date = start + suspension_months (same day-of-month).
- `driver_license_number` is a placeholder (`TBD from case file`) when not present in the materials/portal.

## Probation referral (CC-1375)
- `cc1375_status = prepare_referral` when supervised probation was ordered (term > 0 and a report datetime exists); `not_ordered` when no supervised probation referral was signed (term 0, report datetime null).
- Probation officer / office location are placeholders when null in the materials.

## Placeholders
- Exact text the materials prescribe: `TBD from case file` (read per task — confirm the literal in `form_field_excerpt`/template).
- Apply to: SSN, driver license number, mailing/residence address, phone, probation officer, probation office location, and similar form-required-but-absent identifiers/contacts.
- Where the schema has a placeholder section, list each missing field with its reason code (`missing_identifier`, `missing_contact`, `missing_office_detail`, `missing_party_detail`). Sort per the template.

## Ordering (recurring)
- Most arrays sort by `case_number` / `citation_number` / `petition_id` ascending.
- `excluded_charges` / `excluded_financial_items` / `placeholder_fields.missing_fields` sort alphabetically by code/field name.
- Probation referrals and license orders sort by `case_number`.
- Always re-sort after building each array; an unsorted array fails the template.
