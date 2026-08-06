# Reconciliation pipeline (detailed)

Phases 3–11 of the SKILL procedure, with the accounting identities that must hold. All counts are over **logical** records unless flagged "raw".

## Source resolution
- `authoritative_snapshot_id` = stable ID of the CERTIFIED snapshot (newest non-STALE fallback).
- `authoritative_row_count` = row count of that snapshot (from its snapshot metadata).
- `scoped_raw_row_count` = in-scope raw rows across snapshots (see each contract for the exact definition; usually all rows within the cutoff).

## Fetch & scope
- Page to exhaustion. Keep rows with business timestamp `<= cutoff_at` (maintenance: within `business_period.start..end`).
- `raw_row_count` = total in-scope raw rows.

## Deduplication & survivorship
- Logical key = the stable logical ID (logical transaction / charge / event / contact-cluster).
- Rows sharing a logical key across snapshots = one logical entity.
- Survivor = the occurrence from the authoritative snapshot.
- Identities:
  - `duplicate_raw_count = raw_row_count − logical_count`
  - `logical_count` = number of distinct logical keys.
- Emit duplicate groups: `{logical_id, snapshot_ids (sorted + unique), retained_snapshot_id}`.

## Normalization
- volume → L, weight → KG, distance → KM via `/api/reference/conversions`.
- amount → USD via `/api/reference/fx` at the record's business-date rate.
- Carry full precision; round only at emission to the template's decimals.

## Classification (per logical record)
Decision tree, in order:
1. Unresolved class? (alias maps to 0 → unrecognized, or >1 → ambiguous) ⇒ **quarantine** (reason = `unrecognized_alias` / `ambiguous_alias`).
2. Invalid measure? (nonpositive or unparseable quantity/weight/distance) ⇒ **quarantine** (reason = `invalid_*`).
3. (Contacts only) no usable email AND no usable phone ⇒ **quarantine / no-usable-contact**.
4. Recognized class ≠ expected class ⇒ **valid mismatch**.
5. Otherwise ⇒ **valid**.

Sub-counts the contract may ask for: `unrecognized_count`, `ambiguous_count`, `invalid_quantity_count`, and per-reason quarantine counts (`unrecognized_alias`, `ambiguous_alias`, `invalid_weight`, `invalid_distance`).

- `mismatch_count` = count of valid mismatches.
- `quarantine_count` = count of quarantined logical records.

## Exception accounting
- `exception_count` (per merchant/carrier/asset) = distinct logical records that are a valid mismatch OR quarantined = `mismatch_count + quarantine_count` at that scope.
- `exception_transaction_count` (audit summary) = distinct logical transactions with a mismatch or quarantine.

## Normalized totals (valid records only)
- Include: valid records (including valid mismatches).
- Exclude: quarantined records.
- Per category (fuel_type / service_class): `count`, `volume/weight`, `distance`, `spend`, each rounded to the template's decimals.
- Grand totals = sum of category totals (then round to the template's decimals).
- `valid_transaction_count` / `valid_charge_count` = number of valid logical records.

### Identity checks (sanity)
- `valid_count = logical_count − quarantine_count`.
- `mismatch_count ≤ valid_count` (mismatches are a subset of valid).
- `exception_count = mismatch_count + quarantine_count` (no overlap: mismatches are valid, quarantines are not).
- `valid_count + quarantine_count = logical_count`.
- Per-category `count` values sum to `valid_count`; per-category totals sum to the grand total.

## Rankings
Apply the case_scope sort + tie-breaks + limit. Assign `rank` 1..N.
- Merchants: `exception_count DESC, merchant_id ASC`.
- Carriers: `mismatch_spend_usd DESC, carrier_id ASC` — exposure is normalized USD on **valid class mismatches only**.
- Assets: case_scope keys (e.g., `rejected_event_count DESC, regression_event_count DESC, asset_id ASC`).

Tie-breaks are part of the spec; reversing them changes the answer.
