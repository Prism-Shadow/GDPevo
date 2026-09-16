## Source Conflict Resolution

Clients may have multiple source documents with conflicting facts. Resolve conflicts using the priority order below.

### Priority Hierarchy (highest to lowest)

1. **SIGNED_PROFILE** — Most authoritative. Signed by the client. Controlling source for profile facts.
2. **ATTORNEY_MEMO** — Attorney-authored planning notes. May control asset valuations when memo date is more recent than the profile.
3. **CUSTODIAN_EXPORT** — Authoritative for account balances and retirement account facts.
4. **CRM_NOTE** — Older CRM import. Use only when no SIGNED_PROFILE or ATTORNEY_MEMO exists for a given fact.
5. **STALE_MARKETING_INTAKE** — Least reliable. Avoid unless absolutely no other source covers a fact.

### Resolution Rules by Fact Category

**Profile facts** (income, tax rate, beneficiary count, intent, age, filing status, liquid assets, estate value):
Take from SIGNED_PROFILE. If absent, fall through ATTORNEY_MEMO, then CRM_NOTE.

**Account facts** (traditional_balance, roth_balance, expected_return, rmd_start_age, recommended_conversion_years):
Take from CUSTODIAN_EXPORT via /api/retirement-accounts. Never override with profile documents.

**Beneficiary count** (for ILIT / gift plans):
Take from SIGNED_PROFILE facts.beneficiary_count. Do not use CRM_NOTE if SIGNED_PROFILE exists.

**Policy facts** (insurance death_benefit, annual_premium, planned_contribution_date):
Take from /api/life-insurance endpoint, which is authoritative. Check is_existing_policy_transfer: if true, apply THREE_YEAR_LOOKBACK risk flag.

**Trust asset facts** (asset_value, expected_growth_rate, terms, rates):
Take from /api/trust-candidates endpoint.

### source_resolution Output Rules

- **controlling_profile_source**: SIGNED_PROFILE when one exists for the client, else best available from hierarchy.
- **controlling_account_source**: CUSTODIAN_EXPORT when retirement accounts exist.
- **controlling_beneficiary_source**: SIGNED_PROFILE when it has beneficiary_count.
- **controlling_policy_source**: SIGNED_PROFILE when life insurance data aligns with signed profile.
- **controlling_goal_source**: SIGNED_PROFILE for intent facts.
- **controlling_asset_source**: ATTORNEY_MEMO when it provides asset context not in the profile.
