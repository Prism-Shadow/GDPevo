# Reconciliation, normalization & output rules

Cross-cutting rules that apply to every collection family. Family-specific
quarantine conditions and outputs are in `playbooks.md`.

## Authoritative snapshot & deduplication

1. Authoritative snapshot = `snapshot_status` CERTIFIED with `business_cutoff`
   matching the case-scope cutoff. Report its `snapshot_id` as
   `authoritative_snapshot_id`.
2. Page every in-scope snapshot's rows (within cutoff). `raw_row_count` = total
   raw rows across all in-scope snapshots.
3. Group rows by logical key (`transaction_id` / `charge_id` / `event_id` /
   contact identity). When a logical record appears in ≥2 snapshots, **retain
   the authoritative-snapshot occurrence**; the others are duplicates.
   `duplicate_raw_count` = dropped duplicates; logical count = raw − duplicates.
4. Report duplicate groups the way the contract asks: logical id, the snapshot
   ids involved (sorted lexicographically), and the retained snapshot id
   (authoritative). For freight, one group per `charge_id` with >1 raw
   occurrence; for maintenance, one per `logical_event_id` with retained event
   + snapshot.

## Cutoff filtering

Keep only records whose business date is `<=` the case-scope cutoff. Business
date by family:

- Fuel — `purchased_at`.
- Freight — the charge's business date field (per schema).
- Maintenance — the event timestamp (per schema).
- Contacts — `business_updated_at` / `ingested_at` as the case scope directs.

Snapshots themselves also carry `business_cutoff`; match it to the case scope.

## Disposition model (quarantine vs mismatch vs valid)

For each **logical** record, determine exactly one disposition:

- **Quarantine** (unusable; family conditions in playbooks) → excluded from
  normalized totals **and** from mismatch exposure.
- **Mismatch** (valid; recognized category/class ≠ expected category/class) →
  included in normalized totals **and** in mismatch exposure.
- **Valid / clean** → included in normalized totals.

Derived counts:
- `valid_transaction_count` / `valid_charge_count` / `valid_event_count` =
  logical count − quarantined count. (Mismatches are valid, so they stay in.)
- `exception` count (per merchant / carrier / asset, and overall) = distinct
  logical records that are a mismatch **or** quarantined.
- Mismatch ID lists = all mismatch logical ids, sorted lexicographically.
- Quarantine ID lists = all quarantined logical ids, sorted lexicographically.
- For fuel, `unrecognized` = descriptions that map to zero OR >1 recognized
  category (cannot assign exactly one); report separately and exclude from
  normalized totals (they are part of quarantine).

## Normalization (units & currency)

- Convert each valid/mismatch record's quantity/weight/distance to the canonical
  unit in `case_scope` (`L` / `KG` / `KM`) using `/api/reference/conversions`.
- Convert each record's amount to base currency `USD` using `/api/reference/fx`.
- Never normalize quarantined records.
- Sum normalized values per category/class and overall.

## Ordering rules (from the contract — obey exactly)

- ID lists (mismatch, unrecognized, quarantine, regression, member_row_ids,
  dispatchable_master_ids, contested_cluster_ids, evidence_row_ids): sorted
  **lexicographically ascending**, deduplicated.
- `fuel_type_totals` / `service_class_totals`: exactly one row per
  fuel_type/service_class, sorted by that key **ascending**.
- Ranked arrays obey the contract's sort key + tie-breaks. Common ones:
  - Fuel merchant ranking: `exception_count DESC`, then `merchant_id ASC`; limit
    from `case_scope` (typically 5).
  - Freight carrier ranking: `mismatch_spend_usd DESC` (exposure = normalized
    USD on **valid** class-mismatch charges), then `carrier_id ASC`; limit 5.
  - Maintenance asset-risk ranking: `rejected_event_count DESC`,
    `regression_event_count DESC`, `asset_id ASC`; limit 5; include a `rank`
    field (1-based).
  - Focus arrays: by `cluster_id` / `focus_person_id` / `asset_id` /
    `control_case_id` / `event_id` / `reference_id` / `alias_id` / `charge_id`
    ascending, as the contract states.
- `region_rollup` / `readiness_by_depot`: sorted by region/depot_code
  lexicographically.

## Numeric precision

- Liters / kilograms / kilometers / USD: round to **2 decimal places**.
- `quarantine_rate` (contacts): quarantined rows ÷ canonical entities, rounded
  to **4 decimal places**.
- `total_distance_km` (maintenance): exactly 2 decimals.
- Counts: exact integers; never floating point.
- Round **once**, at the final aggregation step (sum raw values, then round the
  sum), not after each addition.

## Certification

- Compute the quality metric the case scope thresholds (typically
  `quarantine_rate`, or a regression flag).
- Apply thresholds: `pass_max_quarantine_rate` (≤ → PASS),
  `pass_with_exceptions_max_quarantine_rate` (≤ → PASS_WITH_EXCEPTIONS),
  otherwise HOLD. Exact threshold semantics follow the case scope.
- If the case scope specifies a **fixed gate** (e.g. an odometer-regression gate
  forced to `HOLD` / `BLOCK_AND_REMEDIATE`), honor it over the computed
  threshold.
- Map `status` → `action` via the case-scope `status_action_map`
  (PASS→RELEASE, PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS,
  HOLD→BLOCK_AND_REMEDIATE; field names vary slightly by contract, e.g.
  `next_action` / `action` / `routing`).

## Output discipline

- Emit **one** JSON object. Only the contract's required top-level keys; no
  extra keys (`additionalProperties: false` is enforced).
- Match enums, `pattern`s, `minItems`/`maxItems` exactly.
- No commentary, no Markdown, nothing outside the JSON object.
- Validate the object against `answer_template.json` before returning.
