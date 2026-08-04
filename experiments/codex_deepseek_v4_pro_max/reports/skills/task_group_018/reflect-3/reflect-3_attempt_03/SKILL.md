## When to Use

Use this skill when processing court closeout packages, disposition batches, post‑sentencing field packets, traffic‑violation financial closeouts, or financial‑supervision packets. The skill applies whenever you must reconcile hearing notes, clerk worksheets, audit memos, and petition summaries against a court operations portal to produce a structured JSON answer.

## Core Workflow

1. **Read everything first.** Open every payload file in the input directory and the answer template before querying the portal. Payloads often contain corrections, audit flags, or placeholder instructions that override portal data.
2. **Query every relevant portal endpoint.** At minimum check cases, charges, fee‑schedules, docket‑entries, payment‑policies, forms, and search. Use jurisdiction and case‑number filters to avoid noise.
3. **Reconcile conflicts, then build the answer.** Never assume the portal is ground truth. Cross‑check every field that the answer template requires.

## Authority Hierarchy

When two sources disagree on the same fact, resolve in this order:

1. Hearing notes / courtroom clerk notes (highest authority)
2. Audit memo / supervisor worksheet notes
3. Defense‑cover memo or corroborating memo
4. Current fee schedule (portal, effective‑date still active)
5. Portal CMS case / charge record (lowest — often stale or draft)

Record every conflict as an audit finding with the conflicted source value, the corrected value, and which resolution source was used.

## Fee Schedule Rules

- **Use the current schedule.** A fee with a non‑null `end_date` that is before the disposition date is stale; use the active record (null `end_date`) instead.
- **Only post fees supported by both the schedule and the hearing order.** A fee that appears in the schedule but was waived or omitted in open court must be excluded.
- **PD user fees apply only to public‑defender cases.** If counsel is appointed‑private, do not post a PD user fee even if the queue or an import job labels it "PD."
- **Lab / drug‑assessment fees follow the conviction charge.** If the original drug charge was amended to a non‑drug count, the lab fee does not apply.
- **Never add account‑management, collection, late, DMV, restitution, copy, or certification fees unless the portal record or current schedule directly supports them for the specific matter.**

## Counsel Classification

- Raw labels such as "APD", "APPT PRIVATE", or "PD conflict label on intake" are **not** reliable. Check the portal `counsel_type` field and corroborate with hearing notes or defense memos.
- `counsel_type: "appointed_private"` → no PD user fee, attorney may be different from the PD office.
- `counsel_type: "public_defender"` → PD user fee applies if the schedule mandates it.
- `counsel_type: "retained"` → no PD user fee, no appointed‑counsel fee.

## Disposition & Status Rules

- **If no final order was signed in open court, the case is not disposed.** Mark it as deferred/continued and set closeout action to `hold_unsigned_order`. Do not create financial register entries.
- **Charge disposition in the portal may be stale.** If the hearing notes record a guilty adjudication but the portal shows "nolle prosequi" or "dismissed", the hearing notes control.
- **Plea and verdict can differ.** A bench‑trial guilty finding with a not‑guilty plea is a conviction; use `bench_trial_guilty` as the outcome.
- **Departure findings.** If the judge expressly says "no departure" or "top‑of‑range" on the record, correct any portal departure tag to `no_departure` even if the charge screen carries a dispositional departure.

## Identity Verification

- DOB and name inconsistencies between the finance queue, portal CMS, and hearing notes must be flagged. Prefer the portal CMS identity record when it matches the hearing notes or defense memo. If the CMS has a null DOB and no paper jacket is available, use `"TBD from case file"` as the placeholder.

## Payment Plan Math

For installment agreements:
- `first_due_date` = relevant date (conviction, petition submission, or order date) + policy `first_due_days`.
- `total_installments` = ceiling of (total_due / monthly_payment).
- Number of full regular payments = `total_installments − 1`.
- `final_payment_amount` = total_due − (full_regular_payments × monthly_payment).
- `final_due_date` = first_due_date + (full_regular_payments × 1 month).
- `return_to_court_date` = final_due_date + policy `return_to_court_offset_days`.
- If the policy sets `min_monthly` and `max_monthly`, the approved amount must fall within that band.

Budget review:
- `monthly_disposable_income` = `monthly_income − monthly_obligations`.
- Classify as `supported_by_budget` when disposable income comfortably exceeds the installment and the amount is within the policy band.
- Classify as `below_policy_minimum` when the requested amount is less than the policy floor.
- Classify as `unsupported_by_budget` when disposable income cannot cover the minimum.

## Placeholder Handling

- Fields that the template or form requires but that are genuinely absent from **all** available materials (case file, petition, portal, hearing notes) must be set to `"TBD from case file"`.
- Typical placeholder fields: SSN, driver‑license number, mailing address, residence address, phone number, probation officer name, probation office location.
- Never invent missing identifiers, contact details, or office names.

## Excluded Charges & Financial Items

For every charge or fee that appears in the intake worksheet, queue, or counter note but is not supported:
- Record it in the excluded‑charges or excluded‑financial‑items section.
- Reason codes: `stale_schedule`, `not_current_policy`, `no_triggering_event`, `not_in_hearing_order`, `no_order_or_policy_support`.
- Assign the exclusion to the specific matter (`applies_to`) or to `"all"`.

## Form Metadata

- Use the portal `/api/forms` endpoint to confirm form IDs, labels, and revision dates.
- Local form excerpts in payloads may describe field labels; cross‑reference with the portal form metadata.
- When a citation has no separate circuit case or account number, the citation number itself serves as the account reference.

## Output Formatting

- **Currency:** Numbers in dollars to two decimal places (e.g., `150.00`).
- **Dates:** ISO 8601 `YYYY-MM-DD`. Date‑times: `YYYY-MM-DDTHH:MM:SS`.
- **Sorting:** Follow the ordering rules declared in the answer template (usually by case‑number or citation‑number ascending). Within equal case‑numbers, sort secondary keys alphabetically.
- **Enums:** Use the exact enum values provided in the template. Do not substitute prose or free‑text where an enum is expected.
- **null values:** Use JSON `null` for genuinely absent dates. Do not use string `"null"`.
- **Register totals:** Only include cases with `fee_status: "post"`. Sum across all posted cases.

## Common Pitfalls

- Trusting the portal charge `disposition` field without checking hearing notes.
- Applying a lab or drug‑assessment fee after the underlying drug count was amended away.
- Treating an "APD" label as public defender when the judge clarified it is appointed private.
- Forgetting to omit the PD user fee for appointed‑private or retained‑counsel cases.
- Using a stale fee amount because the schedule had a prior `end_date`.
- Creating financial entries for cases where the judge never signed the final order.
- Inventing a driver‑license number, SSN, or address when the materials say it is missing.
- Including unsupported post‑disposition fees (late, collection, DMV) that were never ordered.
