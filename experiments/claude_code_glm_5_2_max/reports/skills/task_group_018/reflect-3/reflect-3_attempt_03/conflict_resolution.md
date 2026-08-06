# Conflict Resolution Patterns

When local payloads (hearing notes, worksheets, petitions) disagree with the Court Operations Portal, apply these rules to decide which source wins.

## Pattern 1: Identity mismatch (name spelling, DOB)

- **Portal is authoritative** for identity unless the hearing notes contain an explicit on-the-record correction.
- Typical case: worksheet has misspelled name or wrong DOB, portal has correct data from AOC-CMS.
- Resolution source: `use_cms` or `use_cms_identity`.

## Pattern 2: Counsel type mislabel

- Common scenario: worksheet or calendar says "PD" but the record shows appointed-private counsel.
- Judge clarification on the record ("J. Sale is appointed private counsel, county pay") overrides the worksheet label.
- Portal `counsel_type` field is usually correct; verify with hearing notes if there is a contradiction.
- Impact: Public Defender User Fee only applies for `public_defender` counsel type.

## Pattern 3: Stale or archived fee amounts

- Worksheets often carry fee amounts from prior-year schedules.
- Always check the fee-schedule endpoint for the current amount (end_date = null).
- Example: Drug Crime Assessment was $125 in 2023 but $250 in 2025.
- Resolution source: `use_fee_schedule`.

## Pattern 4: Draft/unsigned disposition

- If the judge did not sign the order, the case status is `deferred` or `pending`.
- Do NOT create a sentencing financial register entry or post any fees.
- Resolution source: `hold_unsigned_order` or `exclude_pending`.

## Pattern 5: Departure flag from draft worksheet

- Legacy CMS records may carry a departure label from a draft sentence worksheet.
- If the judge explicitly stated on the record "this is top of the range, no departure," override the draft.
- Resolution source: `use_hearing_notes`.
- Result: `no_departure` or `none` in the departure_status field.

## Pattern 6: Amended charge changes fee applicability

- When the state amends a count (e.g., controlled substance → misdemeanor theft):
  - The original count is amended away (`dismissed_or_amended_away_counts = 1`)
  - Drug-crime assessment fees and lab fees do NOT apply to the amended (non-drug) charge
  - Only court costs and any fine on the new charge apply
- Resolution source: `use_hearing_notes`.

## Pattern 7: Omitted mandatory fee

- Worksheets sometimes omit mandatory assessments (e.g., crime lab fee for drug convictions).
- If the fee schedule marks the fee as mandatory for the violation type AND the judge mentioned it, add it.
- Resolution source: `use_hearing_notes` supplemented by `use_fee_schedule`.

## Pattern 8: Missing DOB or identifier

- If DOB is absent from both the portal (null) and hearing notes:
  - Use placeholder: `"TBD from case file"`
  - Set identity_action to `use_placeholder_verify`
  - Set recommended_resolution to `verify_before_entry`
- Never borrow a DOB from a different defendant's case.

## Pattern 9: Account-management or stale local fees

- Counter worksheets may carry account-management fees, payment-plan service charges, or obsolete local fees.
- Check the current payment policy: if `account_fee = 0`, exclude the fee.
- Old plan service charges from prior form revisions are excluded unless current policy authorizes them.
- Resolution source: `excluded_by_policy` or `no_order_or_policy_support`.

## Pattern 10: Charge disposition mismatch

- Portal may show `nolle_prosequi` or `dismissed` while hearing notes say the court found guilt.
- Hearing notes (the actual courtroom record) override stale CMS data.
- Example: portal disposition "nolle prosequi" but notes say "no-contest plea accepted, guilt adjudicated" → correct disposition is `guilty`.
