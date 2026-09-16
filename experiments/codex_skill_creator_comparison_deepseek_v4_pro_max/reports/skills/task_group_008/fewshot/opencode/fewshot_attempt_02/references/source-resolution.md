# Source Resolution Rules

Client records imported from different advisory systems at different times may conflict. These rules determine which source controls each fact category.

## Source priority hierarchy

For profile facts (age, filing status, marital status, income, beneficiary count, philanthropic intent, family transfer priority, marginal tax rate, liquid assets):

1. **SIGNED_PROFILE** — Most recent by `effective_date`. This is the client's signed planning profile and is the highest authority for household facts.
2. **ATTORNEY_MEMO** — Attorney call notes, typically more recent than CRM imports.
3. **CRM_NOTE** — Older CRM import, usually from late 2025. Use only when no SIGNED_PROFILE or ATTORNEY_MEMO exists for the fact.
4. **STALE_MARKETING_INTAKE** — Ranks below CRM notes, rarely present in the train data.

For account facts (balances, expected return, RMD start age, recommended conversion years):

1. **CUSTODIAN_EXPORT** — The authoritative source for retirement account data.

For estate value:

- **SIGNED_PROFILE** controls when available.
- **ATTORNEY_MEMO** controls when SIGNED_PROFILE does not include estate_value.
- **CRM_NOTE** rarely contains estate_value; use only as last resort.

For policy facts (death benefit, premium, contribution date, existing-policy-transfer):

- **SIGNED_PROFILE** controls policy facts (beneficiary count, policy parameters).
- There is no separate policy-specific source; life insurance API data is authoritative.

For trust/asset facts:

- **ATTORNEY_MEMO** controls for asset source in trust comparisons.
- **SIGNED_PROFILE** controls goal source.
- Trust candidate API data (asset value, growth rates, term years) is authoritative for numeric parameters.

## How to resolve a specific fact

When pulling a fact like `beneficiary_count`:

1. Check the most recent SIGNED_PROFILE document for the client. If it contains the fact, use it.
2. If not, check the ATTORNEY_MEMO for the client.
3. If not, check CRM_NOTE for the client.
4. If not, check STALE_MARKETING_INTAKE.
5. If no source has the fact, the fact is unavailable (unlikely in practice).

For `source_resolution` output fields:

- `controlling_profile_source`: The source type that provided the majority of profile facts used. In practice, this is `SIGNED_PROFILE` when it exists and covers the facts; otherwise `ATTORNEY_MEMO` or `CRM_NOTE`.
- `controlling_account_source`: Always `CUSTODIAN_EXPORT` when account data exists; otherwise `SIGNED_PROFILE` or `CRM_NOTE`.
- `controlling_beneficiary_source`: The source that resolved the beneficiary count.
- `controlling_policy_source`: The source that resolved policy parameters.
- `controlling_goal_source`: The source that resolved philanthropic intent and family transfer priority.
- `controlling_asset_source`: The source that resolved asset/trust parameters (typically `ATTORNEY_MEMO` for trust engagements).

## Train-example patterns

From the five train examples, the consistent pattern is:

- Profile facts: Use the SIGNED_PROFILE. In every train case, the SIGNED_PROFILE was more recent (February 2026) than the CRM_NOTE (November 2025) and contained all needed facts.
- Account facts: Use CUSTODIAN_EXPORT.
- The ATTORNEY_MEMO (January 2026) generally contains estate_value and priority hints but fewer fields than the SIGNED_PROFILE.
- When SIGNED_PROFILE exists with the needed facts, it controls; otherwise default to the next-best available source.
