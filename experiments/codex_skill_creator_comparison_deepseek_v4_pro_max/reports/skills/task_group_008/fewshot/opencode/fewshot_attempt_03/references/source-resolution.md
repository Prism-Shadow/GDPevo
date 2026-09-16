# Source Conflict Resolution

## Source type priority order

When multiple source documents for the same client disagree on a fact, use the highest-priority source that contains the fact. Priority is determined by recency and reliability:

| Priority | Source Type | Rule |
|----------|-------------|------|
| 1 (highest) | `SIGNED_PROFILE` | Most recent signed planning profile. Authoritative for demographics, income, tax rate, beneficiary count, priorities, estate value, liquid assets. |
| 2 | `ATTORNEY_MEMO` | Attorney planning call notes. Authoritative for estate value, beneficiary count, and family/philanthropic priorities when no SIGNED_PROFILE carries the fact. Also authoritative for trust-related asset facts. |
| 3 | `CUSTODIAN_EXPORT` | Authoritative for account balances and expected returns. Used as the `controlling_account_source`. |
| 4 | `CRM_NOTE` | Older CRM import. Use only when no SIGNED_PROFILE or ATTORNEY_MEMO carries the fact. Generally stale. |
| 5 (lowest) | `STALE_MARKETING_INTAKE` | Pre-engagement marketing intake. Lowest priority, used only when no other source exists. |

## Resolving specific fact categories

### Profile facts (income, tax rate, demographics, priorities)

The `SIGNED_PROFILE` is the primary controlling source. When the signed profile carries a fact, that value wins. If the signed profile is missing a fact that an `ATTORNEY_MEMO` carries, use the attorney memo. If both are missing, descend to `CRM_NOTE`.

The `controlling_profile_source` in the output must name the source type that provided the majority of profile facts used — normally `SIGNED_PROFILE`.

### Account facts (balances, expected returns)

Account records from `/api/retirement-accounts` always carry `source_type: "CUSTODIAN_EXPORT"`. The `controlling_account_source` must be `CUSTODIAN_EXPORT`.

### Beneficiary facts

Use `beneficiary_count` from `SIGNED_PROFILE`. If not present, fall back to `ATTORNEY_MEMO`, then `CRM_NOTE`. The `controlling_beneficiary_source` reflects whichever source supplied the count.

### Policy facts (life insurance)

Life insurance records from `/api/life-insurance` are the single source of truth for death benefit, annual premium, and contribution date. The `controlling_policy_source` reflects the `source_type` from the source document that provided supporting facts about the policy context — normally `SIGNED_PROFILE`.

### Goal and asset facts (for trust comparisons)

`SIGNED_PROFILE` controls goal-related facts (philanthropic_intent, family_transfer_priority). `ATTORNEY_MEMO` may control asset-specific facts for trust planning. The `controlling_goal_source` and `controlling_asset_source` reflect these respective sources.

## General rules

- Resolve point-by-point: a document can control one fact while another controls a different fact for the same client.
- When two documents of equal priority disagree, prefer the one with the more recent `effective_date`.
- If a fact only appears in one document, use that document's value regardless of priority.
- CRM data is generally stale but still usable as a last resort when no higher-priority document carries the fact.
