# Freight charges reference

## Relevant logical view

`v_freight_charges` — fields: `collection_id`, `charge_id`, `snapshot_id`, `invoice_id`, `invoice_line_no`, `carrier_id`, `lane_id`, `service_date`, `expected_service_class`, `description`, `billed_weight`, `weight_unit`, `distance`, `distance_unit`, `currency`, `amount`, `record_status`, `business_updated_at`, `ingested_at`.

## Reference data for freight

Use `/api/reference/aliases` filtered to `domain = "freight_service_class"`. Each alias row maps an `alias_text` to a `canonical_value` (the recognized service class). The recognized service classes are: EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD.

Use `/api/reference/conversions` filtered to `kind = "weight"` (for weight_unit to KG) and `kind = "distance"` (for distance_unit to KM).

Use `/api/reference/fx` filtered to the latest PUBLISHED rate on or before the cutoff.

## Category matching

Same pattern as fuel: match the `description` (lowercased, trimmed) against `alias_text` for domain `freight_service_class`. The match succeeds when the description contains the alias_text as a substring.

- **One match** → recognized service class is the alias's canonical_value
- **Zero matches** → **unrecognized alias** (quarantine)
- **More than one match across different canonical values** → **ambiguous alias** (quarantine)

## Quarantine reasons (freight)

A charge is quarantined for any of:
- `unrecognized_alias` — description matches zero aliases
- `ambiguous_alias` — description matches multiple canonical classes
- `invalid_weight` — `billed_weight` is missing, 0, or negative
- `invalid_distance` — `distance` is missing, 0, or negative

A charge may have multiple quarantine reasons but is counted only once in `quarantine_count`. The `quarantine_reason_counts` break down the reasons across all quarantined charges (a charge may contribute to multiple reason counts).

Charges with unrecognized/ambiguous aliases are quarantine charges, not tracked separately as "unrecognized" — unlike fuel where they go to a separate unrecognized list.

## Class mismatches

A mismatch occurs when `expected_service_class` differs from the recognized service class. Mismatched charges are still valid for normalized totals — they contribute to spend, weight, and distance under their recognized service class.

## Duplicate handling

Duplicate raw rows occur when the same `charge_id` appears in both certified and provisional snapshots. Retain the certified-snapshot occurrence. Each duplicate group has `raw_occurrence_count >= 2`. Report the `snapshot_ids` that contain the charge (always the certified and provisional pair, sorted lexicographically) and the `retained_snapshot_id` (always the certified one).

## Unit conversion and normalization

1. Convert `billed_weight` to KG using the valid weight conversion factor.
2. Convert `distance` to KM using the valid distance conversion factor.
3. Convert amounts to USD using the fx rate for the charge's currency effective on `service_date`.

## Carrier ranking

For the carrier ranking, `mismatch_spend_usd` is the normalized USD on valid charges whose recognized service class differs from the expected class. Order carriers by `mismatch_spend_usd` descending, then `carrier_id` ascending to break ties. `exception_count = mismatch_count + quarantine_count` per carrier.

## Control code assignment for freight

Same code families as fuel (RB, SB, LD). See [control-codes.md](control-codes.md). Apply per the scoped reference and charge IDs based on:
- **RB codes**: whether the freight alias is well-established, newly added, or stale
- **SB codes**: which snapshot the charge was retained from
- **LD codes**: the charge's mismatch/quarantine/valid classification
