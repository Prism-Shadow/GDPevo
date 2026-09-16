# Vendor Compliance Review Patterns

Two variants share the same underlying compliance endpoints: vendor
onboarding release and post-account-change payment release. Both require
cross-referencing vendor records against compliance ownership, screening,
registry, and bank data.

## Workflow

1. Read the batch payload to get the target business IDs.
2. Fetch /vendors or /api/vendors to get vendor records. Filter to the
   target business IDs.
3. For each business ID, fetch in parallel:
   - /api/compliance/ownership/{business_id}
   - /api/compliance/screening/{business_id}
   - /api/compliance/registry/{business_id}
   - /api/compliance/bank/{business_id}
4. Optionally fetch /compliance/objects or /api/compliance/objects for a
   bulk view.

## Decision Rules

Derive decision per business_id by evaluating compliance evidence:

### approve / release

A business can be approved when ALL of:
- Vendor status is `active` (not `on_hold`).
- No active sanctions hits, PEP flag is false, and no shell-company flag.
- Bank account status is `active` with no name mismatch.
- License is not expired (license_expiry_date after the review/as_of date).
- No missing required documents (screening status is `complete` or `run`,
  not `not_run`).
- Tax ID is valid (present and not flagged).

### escalate

A business must be escalated when ANY of:
- `confirmed_pep` is true.
- `sanctions_confirmed` is true.
- Vendor status is `on_hold` (vendor_on_hold).
- Bank account_status is `closed` (bank_closed).
- `shell_company_suspected` is true.

### hold / awaiting_information

A business is held/awaiting when it is not approvable and not an
escalation, typically because:
- `screening_not_run`: screening status is `not_run`.
- `missing_required_documents`: required compliance documents absent.
- `bank_name_mismatch`: bank account_status is `name_mismatch`.
- `expired_license`: license expiry date before the review date.

If both escalation and hold conditions apply, escalation takes priority.

## Hard-Stop Flags

Map compliance findings to hard-stop flag enum values:

| Condition | Flag |
|-----------|------|
| Bank account_status is `closed` | `bank_closed` |
| Bank account_status is `name_mismatch` | `bank_name_mismatch` |
| Screening pep_flag is true | `confirmed_pep` |
| License expiry before review date | `expired_license` |
| Required documents missing | `missing_required_documents` |
| Screening sanctions_flag is true | `sanctions_confirmed` |
| Screening status is `not_run` | `screening_not_run` |
| Screening shell_company_flag is true | `shell_company_suspected` |
| Vendor status is `on_hold` | `vendor_on_hold` |

Sort flags alphabetically per business. Use an empty list when none apply.

## UBO Counts

From /api/compliance/ownership/{business_id}, count unique
beneficial-owner names at or above the reporting threshold (typically 25%
ownership). Report 0 when no owners meet the threshold or no ownership
data exists.

## Follow-Up Business IDs

List every business_id whose decision is not `approve`, sorted ascending.

## Overall Release Ready

True only when every target business has decision `approve`.

## Account-Change Review Variant

When the task is a payment release after account-change events:

1. Read the account-change batch for requested bank_last4 per business.
2. Compare requested bank_last4 against the vendor record bank_last4 and
   the compliance bank endpoint.
3. Check risk_score from vendor or compliance records; flag any >= 70.

Additional lists for this variant:
- `bank_mismatch_ids`: business IDs where compliance bank_account_status
  is `name_mismatch`.
- `invalid_tax_ids`: business IDs whose tax_id is missing or flagged.
- `expired_license_ids`: business IDs whose license is expired relative to
  as_of_date.
- `review_queue_ids`: business IDs whose decision is not `release`.
- `risk_score_override_flags`: business IDs with risk_score >= 70.
