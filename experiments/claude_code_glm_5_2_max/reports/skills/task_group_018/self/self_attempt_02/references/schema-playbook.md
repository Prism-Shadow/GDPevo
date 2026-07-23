# Schema playbook

Concrete reusable steps for turning `answer_template.json` into the final object. Generic — no task-specific final values.

## Turning the template into the object

1. Copy `required_top_level_keys` as the object's top-level keys (no more, no less).
2. For each section, read its `*_item` required keys and emit exactly those keys per item in that order.
3. For any key described as `enum: X` or `{type: enum, allowed: [...]}`, restrict the value to the listed vocabulary. If the template says "do not replace enum values with prose," treat that as a hard rule.
4. Apply every ordering rule: sort `audit_findings`/`case_audit`/`case_dispositions`/`dispositions`/`fee_*`/`docket_*`/`matters`/`petitions`/`probation_referrals`/`license_orders`/`exclusions`/`excluded_charges`/`placeholder_*` by the key the template names (with the stated tie-breaker).
5. Dates → `YYYY-MM-DD`; datetimes → `YYYY-MM-DDTHH:MM:SS`; money → number to two decimals; use `null` for a date **only** where the template's field rules permit it (e.g. "Use null where no disposition date should be entered").
6. Where the template defines a placeholder enum (`TBD from case file`), populate every genuinely-missing identifier/contact/license field with that exact token and list it in the placeholder section.

## Conflict-resolution hierarchy (apply when sources disagree)

1. Signed order / bench pronouncement / hearing closeout minute.
2. Clerk audit / corroborating memo / audio-clerk statement / review reminder.
3. Current portal record for the disposition year (current fee schedule, current payment policy, current form revision).
4. Sentencing intake / probation desk notes.
5. Finance queue / worksheet / petition counter note (stale/draft by default).

Record each conflict as an audit row: conflicted value, corrected value, issue type, and which source you trusted (the `resolution_source` / `recommended_resolution` enum).

## Hold / exclude / placeholder rules

- A matter with no signed final order (continued, deferred pending signature, draft plea, plea not accepted, no sentence pronounced) → hold/exclude/continue it: fee status `hold`/`do_not_post_pending`, register action `hold_unsigned_order`/`exclude_no_final_order`/`exclude_pending`, docket code the continued variant. Keep it out of posted/assessed totals; put it in the held/excluded count with its reason and next status-check date.
- Exclude every fee not supported by the order, the current schedule, or current policy (account-management, collection, late, returned-check, DMV, restitution, copy, certification, traffic-school, court-reporter, court-appointed-attorney fees with no triggering event; stale/archived amounts; obsolete service charges). List each with its reason code. Replace a stale amount with the current schedule amount in the posted line.
- "PD"-labeled counsel that is really county-appointed private, or retained, counsel → **not** public-defender-fee-eligible. Confirm counsel type before posting any user fee.
- Missing DOB → do not borrow from a similarly-named defendant; use the verify/placeholder action.
- Missing required form fields (SSN, address, phone, DL number, probation officer/office, account number) → exact placeholder token, listed in the placeholder section with the right reason code. Traffic matter with no case/account number → citation number as the account reference.

## Totals and schedule math

- Posted totals (case total, register/batch totals, `combined_amount_due`, `grand_total`, `batch_total_due`, `assessment_total`) = sum of **posted (held/verified)** items only. Held/continued cases are counted in the held/excluded count, not the assessed/disposed count or any money total.
- Counts: `assessed`/`disposed_case_count` + `held`/`excluded_pending_count` = number of target matters. Reconcile before returning.
- Payment plan: `amount_due` (− `down_payment`) ÷ `monthly_payment` = full installment count; remainder ≠ 0 → one final installment of the remainder; `total_installments` = full + (1 if remainder else 0); `final_due_date` from first due date + interval × count. Flag `unsupported_charge_total_included` only if the template asks for it.
- Support classification vs. policy band: requested/selected monthly below `minimum_monthly` → `below_policy_minimum`; above `maximum_monthly` → `above_policy_maximum`; exceeds disposable income (income − obligations) → `unsupported_by_budget`; else `supported`/`supported_by_budget`/`supportable`.
- License suspension: end date = start date + suspension months; start basis (conviction date / release date / petition date) chosen from the hearing note and current form/policy. Release date is memo context and does **not** replace conviction date for the suspension consequence unless the rule says so.
- Every money value to two decimals.

## Final pre-return checklist

- [ ] Top-level keys exactly `required_top_level_keys`; no markdown; pure JSON if required.
- [ ] Every enum key uses only allowed values; no prose substituted.
- [ ] All sort orders applied (correct primary + tie-breaker keys).
- [ ] ISO dates; ISO datetimes where required; two-decimal money; `null` only where permitted.
- [ ] Every held/continued/deferred matter excluded from posted totals and counted as held/excluded.
- [ ] Every excluded fee listed with a reason; every stale amount replaced with the current schedule amount.
- [ ] Every missing required form field is a placeholder and listed; no identifier/contact invented.
- [ ] Counts reconcile; money totals equal the sum of posted items.
- [ ] Every artifact named in the prompt's "Return…" sentence is present.
