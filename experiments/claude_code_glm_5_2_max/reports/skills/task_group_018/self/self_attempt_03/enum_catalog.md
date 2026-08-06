# Enum Catalog

This file consolidates the enum values observed across training task answer templates. When building an answer JSON, use only values from the applicable template's enums. This catalog is for reference during skill application — always defer to the specific answer_template.json for the task at hand.

---

## Common Enums Across Tasks

### Issue / Audit Types
- `identity` — DOB or name conflict between sources
- `counsel` — counsel classification conflict
- `status` — case status conflict (disposed vs. deferred)
- `fee_schedule` — fee amount stale or incorrect vs. current schedule
- `departure` — departure label conflict

### Resolution Sources
- `use_cms` — use the CMS/portal value
- `use_hearing_notes` — use the hearing/bench notes
- `use_corrob_memo` — use the corroborating memo or audit memo
- `use_fee_schedule` — use the current portal fee schedule
- `hold_unsigned_order` — hold until order is signed
- `verify_before_entry` — verify before making permanent entry

### Counsel Types
- `public_defender`
- `appointed_private`
- `retained`
- `unknown`

### Case Status
- `disposed`
- `deferred`
- `pending`
- `continued`

### Plea
- `guilty`
- `no_contest` (also seen as `no contest`)
- `not_guilty`
- `none` / `not_entered` / `not_applicable` / `no_plea_recorded`

### Charge Disposition
- `guilty`
- `nolle_prosequi`
- `deferred`
- `pending`
- `dismissed`

### Departure Status
- `no_departure` / `none`
- `durational_departure`
- `dispositional_departure`
- `not_applicable` / `not_evaluated_misdemeanor` / `not_entered_pending`

### Fee Status
- `post` — include in register
- `exclude` / `do_not_post_pending` — do not include
- `hold` — on hold pending resolution

### Fee Codes
- `fine`
- `court_cost`
- `drug_assessment` / `crime_lab_fee`
- `public_defender_user_fee`
- `county_surcharge`

### Exclusion Reason Codes
- `stale_schedule` — fee from expired schedule
- `unsupported_post_disposition` — no post-disposition triggering event
- `not_in_hearing_order` — not mentioned in the hearing record
- `not_current_policy` — current policy does not support the charge
- `no_triggering_event` — no event triggers the fee (e.g., no default, no DMV referral)
- `no_order_or_policy_support` — no order or policy authorizes the item
- `not_part_of_balance` — item is not part of the balance per policy

### Petition Classification
- `initial_installment`
- `subsequent_review`
- `deferred_payment`
- `exempt_no_payment`

### Support Classification
- `supportable` / `supported_by_budget`
- `below_policy_minimum`
- `above_policy_maximum`
- `unsupported_by_budget` / `needs_judge_review`

### Account Fee Treatment
- `excluded_by_policy`
- `included_by_policy`
- `verify_before_entry`

### Payment Application Order
- `fines_costs_only`
- `restitution_before_fines_costs`
- `fines_costs_before_restitution`

### CC-1375 Status
- `prepare_referral`
- `not_ordered`

### License Start Basis
- `conviction_date`
- `release_date`
- `petition_date`

### Placeholder Value
- `TBD from case file`

---

## Note

Each answer template may define slightly different enum names and allowed values. Always read the specific `answer_template.json` for the current task and use its exact enum values. This catalog helps anticipate what to expect but does not replace the template.
