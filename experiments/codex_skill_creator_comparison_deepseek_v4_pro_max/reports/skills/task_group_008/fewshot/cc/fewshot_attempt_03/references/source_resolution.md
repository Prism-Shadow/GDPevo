# Source Resolution Rules

Advisory environments often contain conflicting records imported from different
systems at different times. Resolve conflicts using the deterministic priority
chain below before any computation.

## Priority order

### Client profile facts

Fields drawn from client/family attributes:

| Priority | Source Type            |
|----------|------------------------|
| 1        | `SIGNED_PROFILE`       |
| 2        | `ATTORNEY_MEMO`         |
| 3        | `CRM_NOTE`             |
| 4        | `STALE_MARKETING_INTAKE` |

**Covered fields:** `age`, `marital_status`, `filing_status`, `planning_year`,
`annual_non_ira_income`, `marginal_tax_rate`, `beneficiary_count`,
`philanthropic_intent`, `family_transfer_priority`, `liquid_assets`,
`estate_value`, and any other household-profile facts.

### Financial account records

Fields drawn from retirement account data:

| Priority | Source Type       |
|----------|-------------------|
| 1        | `CUSTODIAN_EXPORT` |
| 2        | `SIGNED_PROFILE`   |
| 3        | `CRM_NOTE`         |

**Covered fields:** `traditional_balance`, `roth_balance`, `expected_return`,
`rmd_start_age`, `recommended_conversion_years`.

### Life insurance / policy records

| Priority | Source Type       |
|----------|-------------------|
| 1        | `SIGNED_PROFILE`   |
| 2        | `ATTORNEY_MEMO`    |
| 3        | `CUSTODIAN_EXPORT` |
| 4        | `CRM_NOTE`         |

### Trust candidate / asset records

| Priority | Source Type       |
|----------|-------------------|
| 1        | `ATTORNEY_MEMO`    |
| 2        | `SIGNED_PROFILE`   |
| 3        | `CRM_NOTE`         |

### Goal / intent facts

| Priority | Source Type       |
|----------|-------------------|
| 1        | `SIGNED_PROFILE`   |
| 2        | `ATTORNEY_MEMO`    |
| 3        | `CUSTODIAN_EXPORT` |
| 4        | `CRM_NOTE`         |
| 5        | `STALE_MARKETING_INTAKE` |

## Fallback rule

When the highest-priority source is silent on a specific field (the field is absent
from its `facts` block), fall through to the next source in the chain. Never mix
fields from different sources for the same conceptual group — but for a field not
present in the top source, take it from the next available source.

## Source resolution output fields

In the final JSON, `source_resolution` describes which source controlled:

- `controlling_profile_source`: the highest-priority source that provided the
  client profile facts used. Usually `SIGNED_PROFILE`.
- `controlling_account_source`: the highest-priority source for account data.
  Usually `CUSTODIAN_EXPORT`.
- `controlling_beneficiary_source`: for ILIT, the source for beneficiary count.
  Usually `SIGNED_PROFILE`.
- `controlling_policy_source`: for ILIT, the source for policy facts.
  Usually `SIGNED_PROFILE`.
- `controlling_goal_source`: for trust/estate plans, the source for goal facts
  such as `philanthropic_intent` and `family_transfer_priority`.
  Usually `SIGNED_PROFILE`.
- `controlling_asset_source`: for trust comparisons, the source for trust asset
  value. Usually `ATTORNEY_MEMO` when available, otherwise `SIGNED_PROFILE`.

## Identifying the controlling source

For each category, scan the available documents in priority order. The
controlling source is the highest-priority source present for that client. For
example, if both `SIGNED_PROFILE` and `CRM_NOTE` exist for the client,
`controlling_profile_source` = `"SIGNED_PROFILE"`.

If a source type is not present among the client's documents, do not emit it
as a controlling source.
