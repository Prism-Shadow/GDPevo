# Output Schema Rules

The deliverable is **one JSON object matching `answer_template.json`**. The template is both the spec and the field reference — read it carefully each run; the enum lists and ordering rules change per matter.

## Hard format rules (consistent across all exemplars)

- **One object.** No markdown fence, no wrapper text, no trailing comments, no extra top-level keys beyond the required set.
- **Currency** → JSON numbers, two decimals (e.g. `150.00`, not `"150"` or `150`). No `$`.
- **Dates** → ISO `YYYY-MM-DD`. **Datetimes** → ISO local `YYYY-MM-DDTHH:MM:SS`. Use `null` for a date only where the schema explicitly allows it (e.g. `disposition_date` when null is expected; `report_datetime` for a not-ordered referral).
- **Booleans** → `true`/`false`, never strings.
- **Enums** → use the exact allowed value from the template's `enums`/`allowed` list. Never substitute prose for an enum slot. If no value fits, use the template's escape hatch: `verify_before_entry`, `hold`, `*_pending`, `other`, `not_applicable`, `verify_before_entry`. Prefer that over a free-form string.
- **Ordering** → apply the template's per-section ordering rules (`ordering_rules` / `instructions`). Typical: sort `audit`/`disposition`/`fee`/`docket` by `case_number` ascending; `matters`/`excluded_charges` by `citation_number`/`charge_code`; `petitions` by `petition_id`; `placeholder missing_fields` alphabetically; `exclusions` by `case_number`.
- **Totals computed last** and must reconcile: posted (non-excluded) lines only contribute to totals; held/unsigned/continued cases are excluded and tracked in their own count. `grand_total` = sum of the posted case totals. `unsupported_charge_total_included` / excluded totals are reported but never folded into posted totals.

## Enum classes you will commonly see (and how to choose)

- **issue_type / audit_flag** — `identity`, `counsel`, `status`, `fee_schedule`, `departure`; or `*_omitted`, `*_missing_verify`, `*_not_public_defender`, `no_final_order_pending`, `amended_non_lab_conviction`. Pick the one matching the *kind* of conflict, not the resolution.
- **resolution_source / recommended_resolution** — `use_cms`, `use_hearing_notes`, `use_corrob_memo`, `use_fee_schedule`, `hold_unsigned_order`, `verify_before_entry`, `exclude_pending`, `use_cms_identity`.
- **counsel_type / counsel_classification** — `public_defender`, `appointed_private`, `retained`, `unknown`. Resolved per bench/memo, not the queue label.
- **case_status / entry_status** — `disposed`/`disposed_enter` vs `deferred`/`pending`/`continued`/`pending_exclude`. Drives whether fees post.
- **fee_status** — `post`, `exclude`, `hold`, `do_not_post_pending`.
- **charge_disposition / primary_outcome** — `guilty`, `no_contest`, `nolle_prosequi`, `deferred`, `pending`, `dismissed`; or `guilty_plea`/`no_contest_guilty`/`bench_trial_guilty`/`continued_pending`.
- **departure_status** — `no_departure`/`none` when the judge said no departure; `not_evaluated_misdemeanor`/`not_applicable` for misdemeanors; `not_entered_pending` for unsigned matters. Never carry a draft "departure" label.
- **closeout_action / register_action** — `enter_disposition` / `enter_disposition_and_financials` vs `hold_unsigned_order` / `exclude_no_final_order`.
- **petition_classification / agreement_sequence** — `initial_installment` / `subsequent_review` / `deferred_payment` / `exempt_no_payment`; `post_disposition` vs `pre_disposition`.
- **support_classification** — compute disposable income (income − obligations), compare to policy min/max: `supportable` / `supported_by_budget` vs `below_policy_minimum` / `above_policy_maximum` / `unsupported_by_budget` / `needs_judge_review`.
- **account_fee_treatment** — `excluded_by_policy` unless current policy includes it; `verify_before_entry` if policy unclear.
- **payment_application_order** — from policy: `fines_costs_only` vs `restitution_before_fines_costs` vs `fines_costs_before_restitution`. Don't let a petitioner's question set this.
- **license_start_basis** — `conviction_date` (default for DUI suspension), `release_date`, `petition_date`. Release date is memo context, not the suspension start unless policy says so.
- **cc1375_status** — `prepare_referral` only if supervised probation ordered + report datetime exists; else `not_ordered`.
- **placeholder_value** — `TBD from case file`. Always the same string; varies only by the reason_code.

## Payment-schedule math

Given approved `monthly` amount, optional `down_payment`, and `first_due_date`, over a `balance = total_due − down_payment`:
- `full_installment_count = floor(balance / monthly)`
- `remainder = balance − monthly × full_installment_count`
- `final_payment_amount = remainder` (0.00 if it divides evenly — emit 0.00 unless the schema forbids)
- `total_installments = full_installment_count + (remainder > 0 ? 1 : 0)`
- `final_due_date = first_due_date + (total_installments − 1) months` (monthly interval)
- `return_to_court_date` from the matter/policy if set, else derived.
Court-approved monthly amount overrides the petitioner's *requested* amount.

## Self-check before returning

1. Every required top-level key present; no extras.
2. Every enum value is in the template's allowed list.
3. Every currency is a two-decimal number; every date is ISO.
4. Every excluded/unsupported item has a reason code; no excluded line appears in posted totals.
5. Every placeholder field carries `TBD from case file` + a reason; no invented identifier/contact.
6. Totals sum to posted lines; held/unsigned cases counted only in the excluded/pending totals.
7. Ordering rules applied per section.
