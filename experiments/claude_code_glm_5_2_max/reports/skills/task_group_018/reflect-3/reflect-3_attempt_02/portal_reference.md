# Portal Endpoint Quick Reference

## Base URL
From `environment_access.md`. Credentials: none required within network.

## Endpoints

### GET /api/jurisdictions
Returns list of jurisdictions with `jurisdiction_code`, `policy_ref`, `state`, `county`, `court_name`.

### GET /api/cases
Full case list. Filter by searching for specific case_number. Key fields: `defendant_dob`, `counsel_type`, `attorney_name`, `attorney_label_raw`, `status`, `disposition_date`.

### GET /api/charges
Use `?case_number=<id>` to get charges for a specific case. Key fields: `offense_code`, `plea`, `disposition`, `fine_amount`, `jail_days_imposed`, `jail_days_suspended`, `probation_months`, `departure_type`, `departure_reason`, `assessment_code`, `severity`, `statute`.

### GET /api/docket-entries
Docket entries for cases. Key fields: `entry_type`, `entry_date`, `text`, `source`.

### GET /api/fee-schedules
All fee schedule entries. **Critical**: Check `effective_date` and `end_date`. An entry with `end_date` is stale; use the entry with `end_date = null` and matching `jurisdiction_code`. Key fields: `fee_type`, `amount`, `jurisdiction_code`, `violation_code`, `mandatory`, `notes`.

### GET /api/payment-policies
Payment policies by jurisdiction. Key fields: `min_monthly`, `max_monthly`, `account_fee`, `first_due_days`, `return_to_court_offset_days`, `restitution_priority`.

### GET /api/forms
Form metadata. Key fields: `form_id`, `form_name`, `label`, `placeholder_instruction`, `required_fields`, `revision_date`.

### GET /api/financial-petitions
Petition records. Key fields: `fines_costs_balance`, `restitution_balance`, `income_monthly`, `obligations_monthly`, `requested_monthly`, `petition_sequence`, `submitted_date`.

### GET /api/citations
Traffic citations. Key fields: `violation_code`, `speed_mph`, `zone_mph`, `plan_approved`, `monthly_payment`, `first_due_date`.

### GET /api/search?q=<query>
Cross-entity search. Returns cases, docket entries, and financial petitions matching the query. Best for looking up a specific case_number or petition_id.

## Cross-Reference Patterns

### Identity Resolution
1. Get CMS case record → extract `defendant_dob`, `defendant_first`, `defendant_last`.
2. Compare against finance queue / worksheet values.
3. If conflict: CMS wins. Record in audit findings with `resolution_source: use_cms`.

### Counsel Classification
1. Get CMS `counsel_type` and `attorney_label_raw`.
2. Compare against hearing notes and audit memo.
3. If hearing notes/memo say "appointed private" but CMS says "public_defender": use hearing notes.
4. This determines whether PD user fee applies: only when `counsel_type = public_defender`.

### Fee Amount Resolution
1. Get fee schedule entries for the jurisdiction.
2. Filter to entries where `effective_date ≤ disposition_date` and `end_date` is null.
3. Match on `fee_type` and `jurisdiction_code`.
4. If finance queue uses an amount from an expired schedule entry (has `end_date`), flag as audit finding and use current amount.

### Departure Resolution
1. Get charge record `departure_type` from portal.
2. Compare against hearing notes.
3. If judge said "no departure" / "top of the range" on the record: override CMS departure. Set to `no_departure` / `none`.
4. Record in audit findings with `resolution_source: use_hearing_notes`.

### Case Status Resolution
1. Get CMS `status` from case record.
2. Compare against hearing notes (was the order signed?).
3. If no signed order: status should be `deferred` / `pending`, regardless of what worksheet says.
4. Financial entries go to `hold` / `do_not_post_pending` for deferred cases.

### Payment Plan Calculation
1. Get payment policy for the jurisdiction.
2. Get petition data for balances and requested amount.
3. Compute disposable income: `income_monthly - obligations_monthly`.
4. Verify requested amount is within `[min_monthly, max_monthly]`.
5. Calculate schedule using the formula in SKILL.md step 4.
