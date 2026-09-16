# Placeholder and Exclusion Rules

## Placeholder Policy

**Rule**: Use `TBD from case file` for any form-required field that is absent from all available case materials (hearing notes, portal, petitions, intake sheets, memos).

**Never do**:
- Guess or invent identifiers
- Borrow identifiers from similarly named defendants in prior search results
- Substitute contact details from other cases
- Make up probation officer names, office locations, judge names, or attorney contact information

**When to use the placeholder**:

| Missing Field | Reason Code |
|---|---|
| SSN (absent from all intake) | `missing_identifier` |
| Driver license number (not in case file) | `missing_identifier` |
| Residence address | `missing_contact` |
| Mailing address | `missing_contact` |
| Phone number | `missing_contact` |
| Probation officer name | `missing_office_detail` |
| Probation office location | `missing_office_detail` |

**When NOT to use the placeholder**:
- DOB that is blank on a bench card but verifiable from the portal: query the portal for DOB
- DOB that is blank everywhere with explicit instruction "do not borrow": use `TBD from case file`
- Name: correct it using hearing notes or portal, never leave as placeholder

## Financial Item Exclusion

### Exclusion Categories

Items always excluded unless a portal record, current policy, or hearing order directly supports them:

| Item | Typical Reason |
|---|---|
| `account_management_fee` | `not_current_policy` or `no_order_or_policy_support` |
| `collection_fee` | `no_triggering_event` |
| `late_fee` or `late_payment_fee` | `no_triggering_event` |
| `dmv_fee` or `dmv_reinstatement_fee` | `no_triggering_event` or `not_part_of_balance` |
| `returned_check_fee` | `no_triggering_event` |
| `restitution` | `no_order_or_policy_support` |
| `court_appointed_attorney_fee` | `no_order_or_policy_support` |
| `court_reporter_fee` | `no_order_or_policy_support` |
| `traffic_school_fee` | `not_in_hearing_order` |
| `stale_2022_standard_fine` | `stale_schedule` |
| `statutory_maximum_substitution` | `unsupported_post_disposition` |

### Exclusion Reason Codes

| Reason Code | Meaning |
|---|---|
| `stale_schedule` | Amount comes from an outdated schedule; current schedule differs |
| `unsupported_post_disposition` | Not supported by the disposition record |
| `not_in_hearing_order` | Hearing record does not mention this item |
| `not_current_policy` | Current portal payment policy excludes this item |
| `no_triggering_event` | No event has occurred to trigger this fee (e.g., no late payment, no returned check) |
| `no_order_or_policy_support` | Neither a court order nor portal policy supports this item |
| `not_part_of_balance` | Item is not part of the collectible balance (e.g., DMV reinstatement is a separate agency fee) |

### Exclusion Scope

- `all`: Applies to every matter in the batch
- A specific case/citation number: Applies only to that matter

## Stale Amount Replacement

When a local worksheet or intake cover sheet carries a stale dollar amount:

1. Query the current portal fee schedule.
2. If the portal amount differs, replace with the portal amount.
3. Document the stale amount in `excluded_charges` or `excluded_financial_items` with reason `stale_schedule`.

Examples of stale amounts:

- Drug assessment: $125 in 2023 vs. $250 in current schedule
- Speed fine: $1,000 from 2022 SOF table vs. current tiered schedule amount
- Account-maintenance fee: $25 on counter worksheet that current policy excludes

## Traffic-Specific Exclusion

For traffic violation citations, these extra items are checked:

- **Statutory maximum** noted on intake cover sheet: exclude as `unsupported_post_disposition` unless the current schedule confirms the amount
- **Stale SOF table values**: exclude as `stale_schedule`
- **Traffic school program fee**: exclude as `not_in_hearing_order` unless hearing ordered traffic school
- **Account-management, collection, DMV, returned-check, late fees**: exclude if no triggering event exists

## Form Field Placeholder Handling

When building form entries (CC-1375, CC-1379, payment plan forms):

1. Fill every field that has data from hearing notes, portal, or petitions.
2. For fields that are required by the form but have no data in any source: use `TBD from case file`.
3. Document each placeholder in the output's placeholder section, sorted alphabetically by field name.
4. For probation referrals (CC-1375): if no probation was ordered, set `cc1375_status = not_ordered` rather than using placeholders for referral fields.

### Form Account Reference Rule

When no separate case number or account number exists for a traffic citation, use the citation number as the account reference. Do not invent an account number.
