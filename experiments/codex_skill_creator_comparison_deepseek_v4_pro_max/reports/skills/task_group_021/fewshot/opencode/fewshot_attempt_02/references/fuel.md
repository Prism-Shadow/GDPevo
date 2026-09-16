# Fuel transactions reference

## Relevant logical view

`v_fuel_transactions` — fields: `collection_id`, `transaction_id`, `snapshot_id`, `asset_id`, `merchant_id`, `purchased_at`, `expected_fuel_type`, `purchased_description`, `quantity`, `quantity_unit`, `currency`, `amount`, `record_status`, `business_updated_at`, `ingested_at`.

## Reference data for fuel

Use `/api/reference/aliases` filtered to `domain = "fuel_type"`. Each alias row maps an `alias_text` to a `canonical_value` (the recognized fuel type). The recognized fuel types are: BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED.

Use `/api/reference/conversions` filtered to `kind = "fuel_volume"`. These map from source `quantity_unit` (GAL, L, etc.) to the canonical unit L via a `factor`.

Use `/api/reference/fx` filtered to the latest PUBLISHED rate on or before the cutoff. Convert amounts to USD by multiplying `amount * usd_per_unit` for the matching currency and rate_date.

## Category matching

For each transaction, match the `purchased_description` (lowercased, trimmed) against the alias_text in the valid reference aliases. A match succeeds when the description contains the alias_text as a substring. After finding all matches:

- **One match** → the transaction's recognized fuel type is the alias's `canonical_value`
- **Zero matches** → the transaction is **unrecognized** (goes to `unrecognized_transaction_ids`)
- **More than one match across different canonical values** → the transaction is **ambiguous** (also goes to `unrecognized_transaction_ids`)

Both unrecognized and ambiguous are included in `unrecognized_count`. The unrecognized list includes both zero-match and ambiguous cases combined.

## Category mismatches

A mismatch occurs when `expected_fuel_type` (from the source) differs from the recognized fuel type (from alias matching). Mismatched transactions are still valid for normalized totals — they contribute to spend and volume under their recognized fuel type.

## Quarantine (fuel)

A transaction is invalid quantity (and thus quarantined/excluded from totals) when:
- `quantity` is missing, 0, or negative
- The transaction record_status is not ACTIVE

Transactions with unrecognized/ambiguous descriptions are not quarantined — they are tracked separately in `unrecognized_transaction_ids`. They are excluded from normalized totals.

## Duplicate handling

Duplicate raw rows occur when the same `transaction_id` appears in both the certified and provisional snapshots. Retain the certified-snapshot occurrence and exclude the provisional one. Count excluded rows as `duplicate_raw_count`.

## Unit conversion and normalization

1. For each valid transaction, look up `quantity_unit` in the valid conversion table filtered to the cutoff.
2. Convert to canonical liters: `volume_l = quantity * factor`.
3. Convert to USD: look up the fx rate for the transaction's currency effective on `purchased_at`. Use the rate whose `rate_date` is on or before `purchased_at` and with `rate_status = "PUBLISHED"`. If multiple rates exist for the same date/currency, use the most recent `published_at`.

## Merchant exception ranking

A merchant exception is a logical transaction with a category mismatch or quarantine condition:
- Count distinct transactions with mismatches as `mismatch_count` per merchant
- Count distinct transactions quarantined as `quarantine_count` per merchant
- `exception_count = mismatch_count + quarantine_count` per merchant
- Rank merchants by `exception_count` descending, then `merchant_id` ascending
- Take only the top `merchant_ranking_limit` (typically 5)

## Control code assignment for fuel

See [control-codes.md](control-codes.md) for RB, SB, and LD code rules. Assign per the scoped reference and transaction IDs based on:
- **RB codes**: whether the fuel alias is well-established in the reference table, newly added, or stale/missing
- **SB codes**: which snapshot the transaction was retained from
- **LD codes**: the transaction's mismatch/quarantine/valid classification
