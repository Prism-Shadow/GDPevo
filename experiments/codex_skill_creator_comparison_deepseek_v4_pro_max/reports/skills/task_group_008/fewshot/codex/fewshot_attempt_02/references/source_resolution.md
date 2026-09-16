# Source Resolution

Multiple source documents per client can contain conflicting facts.  Resolve
conflicts using the hierarchy below, then populate the `source_resolution`
section of the output JSON.

## Document Source Priority

Highest priority first:

1. **SIGNED_PROFILE** — Most recent signed household planning profile.
   Contains the most complete fact set and represents the client's stated
   preferences.  Use this for client demographics (age, marital_status,
   filing_status), income (annual_non_ira_income, marginal_tax_rate),
   beneficiary_count, philanthropic_intent, family_transfer_priority, and
   financial totals (liquid_assets, estate_value).

2. **ATTORNEY_MEMO** — Attorney planning call notes.  Less complete than
   signed profile but more recent than CRM.  May only contain estate_value,
   family_transfer_priority, and philanthropic_intent.  Use these fields only
   when the signed profile does not have them.

3. **CRM_NOTE** — Older CRM import (typically dated 2025).  Contains a
   subset of facts and may be stale.  Use only when no newer source covers
   a required field.

When a field appears in multiple documents, use the value from the
highest-priority document that contains it.  Do not average or merge
numeric values; pick one source.

## Account Balance Priority

- **CUSTODIAN_EXPORT** is always authoritative for `traditional_balance`,
  `roth_balance`, `expected_return`, `rmd_start_age`, and
  `recommended_conversion_years`.  These come from `/api/retirement-accounts`,
  not from source documents.

## Controlling Source Fields

The answer template asks for controlling-source enums such as:

- `controlling_profile_source` — Which source document type provided the
  dominant facts used for client demographics and preferences.
  In practice this is always `SIGNED_PROFILE` when present, falling back to
  `ATTORNEY_MEMO` if no signed profile exists, then `CRM_NOTE`.

- `controlling_account_source` — Always `CUSTODIAN_EXPORT`.

- `controlling_beneficiary_source` — The document type that supplied the
  `beneficiary_count` used in calculations.  Usually `SIGNED_PROFILE`.

- `controlling_policy_source` — For life insurance facts, `SIGNED_PROFILE`
  when one exists for the client.

- `controlling_goal_source` — The document type that supplied
  `philanthropic_intent` and `family_transfer_priority`.  Usually
  `SIGNED_PROFILE`.

- `controlling_asset_source` — For trust comparisons, `ATTORNEY_MEMO` when
  it provides the estate_value used alongside trust-candidate data.

## Enum Values

All source-type enum values that may appear in answers:

- `SIGNED_PROFILE`
- `ATTORNEY_MEMO`
- `CUSTODIAN_EXPORT`
- `CRM_NOTE`
- `STALE_MARKETING_INTAKE`
