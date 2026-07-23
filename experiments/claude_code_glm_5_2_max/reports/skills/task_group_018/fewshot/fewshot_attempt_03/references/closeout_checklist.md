# Closeout Output Self-Check

Run this against the assembled JSON before returning it. Each item maps to a failure mode seen across closeout batches.

## Shape
- [ ] Every required top-level key from `answer_template.json` is present.
- [ ] No extra top-level keys beyond what the template implies.
- [ ] Each item has exactly the keys the template lists for that item shape (no missing, no invented keys).
- [ ] Output is pure JSON — no markdown fences, no commentary, no trailing prose.

## Enums
- [ ] Every enum field's value is a token from the template's allowed set, spelled **exactly** as listed (case and underscores).
- [ ] No enum value was replaced with prose or a paraphrase.
- [ ] `verify_before_entry` / `not_applicable` / `none` / `null` used only where the template permits them for that field.

## Ordering
- [ ] Every array sorted per its ordering rule (case_number / citation_number / petition_id ascending; excluded items and missing_fields alphabetical).
- [ ] Re-sorted after the last edit (a mid-edit addition can break ordering).

## Numbers / dates
- [ ] All currency to two decimals (e.g. `0.00`, `150.00`), as numeric values not strings.
- [ ] All dates ISO `YYYY-MM-DD`; all datetimes ISO local `YYYY-MM-DDTHH:MM:SS`.
- [ ] `null` dates only where the template explicitly allows null (e.g. continued/excluded matter disposition_date, not-ordered probation report_datetime).
- [ ] Integer fields (counts, installments) are integers, not floats.

## Reconciliation correctness
- [ ] No stale/archived/`OLD` fee-schedule amount survived into the output (current schedule only).
- [ ] No `public_defender_user_fee` on an `appointed_private` or `retained` case.
- [ ] `drug_assessment` present only on the controlled-substance conviction, at the current amount.
- [ ] Identity (name spelling, DOB) taken from the portal/CMS, not the local typo.
- [ ] Counsel classification follows the bench/memo clarification, not the queue label.
- [ ] A matter with no signed final order is **not** in the disposed register: status deferred/continued/pending, no sentencing financial entry, fee_status hold/exclude/do-not-post, counted as held/excluded.
- [ ] Departure status reflects the judge's finding, not a legacy worksheet label.
- [ ] All unsupported fee classes excluded and listed with correct reason codes; none silently dropped.

## Totals
- [ ] Per-matter `case_total`/`total_due` equals the sum of its corrected posted fee items (not the queued total).
- [ ] Batch/register totals sum **posted** matters only.
- [ ] Held/excluded matters contribute `0.00` and increment the held/excluded counter, not the assessed/disposed counter.
- [ ] `grand_total` / `batch_total_due` reconciles to the sum of posted per-matter totals.

## Schedule math
- [ ] `total_installments` = full payments + 1 only when a nonzero remainder exists.
- [ ] `final_payment_amount` = remainder (or equals the regular installment when balance divides evenly).
- [ ] `final_due_date` is first_due_date advanced by (total_installments − 1) intervals.
- [ ] Support classification matches the policy band and disposable income.

## Placeholders & non-invention
- [ ] Every form-required-but-absent field is the exact placeholder text (e.g. `TBD from case file`), not an invented value.
- [ ] No invented SSN, DL#, address, phone, attorney, judge, probation officer, or date appears.
- [ ] Placeholder fields, if the schema lists them, each carry the right reason code and are sorted.
- [ ] Payment-application order follows policy + restitution existence, not guesswork.

If any box is unchecked, fix and re-run. Do not return the output with a known failed check.
