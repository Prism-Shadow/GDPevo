# Alias Reference Domains and Lookup Strategy

The hub's `v_reference_aliases` view maps free-text descriptions to canonical
category values. Each alias row has a `domain`, `alias_text`, `canonical_value`,
`valid_from`, `valid_to`, and `reference_status`.

## Alias Domains

| Domain   | Used By | Canonical Values |
|----------|---------|------------------|
| `fuel`   | Fuel transactions (`v_fuel_transactions.purchased_description`) | BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED |
| `freight` | Freight charges (`v_freight_charges.description`) | EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD |

## Lookup Strategy

For each transaction/charge row:

1. Load all aliases for the relevant domain:
   ```
   SELECT * FROM v_reference_aliases WHERE domain = '<fuel|freight>'
   ```
2. Filter aliases by date: a row's `purchased_at` or `service_date` must fall within the alias's `valid_from`–`valid_to` range (inclusive). If `valid_to` is null, the alias is unbounded on the high end.
3. Normalize the transaction's description field: Unicode NFKC, strip whitespace, lowercase.
4. Match the normalized description against each alias's `alias_text` (also normalized). Match is exact after normalization. Prefer aliases with `reference_status = 'active'` when available.
5. Count distinct `canonical_value` results:
   - **0 matches**: unrecognized — quarantine the row.
   - **1 distinct canonical value**: recognized. If it differs from `expected_fuel_type` / `expected_service_class`, flag as mismatch.
   - **2+ distinct canonical values**: ambiguous — quarantine the row.

## Handling Edge Cases

- Aliases are case-insensitive after normalization.
- Leading/trailing whitespace in both alias_text and the description is stripped before comparison.
- When `expected_fuel_type` or `expected_service_class` is null/empty, treat any single recognized canonical value as a match (no mismatch); treat unrecognized/ambiguous as quarantine.
- The alias `reference_status` field may contain values like `active`, `inactive`, or `superseded`. Prefer active aliases; fall back to others only if no active alias matches.
