# Reconciliation pipeline (per family)

Every task follows the same spine: **snapshots → cutoff → dedup → validate/quarantine
→ normalize → recognize → survivorship → aggregate → decide**. The `family` of the
scoped collection (from `/api/catalog/collections`) tells you which view and which
answer shape applies:

- `contacts` → `v_contacts` (partner/field-service/dealer/warranty contact certification)
- `fuel` → `v_fuel_transactions`
- `freight` → `v_freight_charges`
- `maintenance` → `v_maintenance_events`

Read `payloads/answer_template.json` first — it is the contract. Compute exactly the
fields it names, nothing more, and obey every `description`/ordering/rounding note in it.

## Common steps

1. **Enumerate snapshots** for the scoped `collection_id` from `v_source_snapshots`.
   Identify the certified/authoritative snapshot (`"{collection}-certified"`).
2. **Scope by cutoff.** Keep raw rows whose business date
   (`business_updated_at`/`purchased_at`/`service_date`/`event_time_raw`) is on or
   before the scope cutoff (`business_cutoff`/`cutoff_at`/`business_period.end`), and
   snapshots created on or before `as_of` when present. `raw_row_count` /
   `scoped_raw_row_count` = every retained raw occurrence across snapshots.
3. **Dedup to logical entities.** Group raw rows by the logical id; a logical id in
   >1 snapshot is a cross-snapshot duplicate → retain the certified occurrence.
   `duplicate_raw_count = raw − logical`.
4. **Validate → quarantine** the logical entities (family rules below). Quarantined
   entities are excluded from normalized totals but still counted as canonical.
5. **Normalize** surviving entities (units + FX) and **recognize** categories.
6. **Aggregate** the requested rollups/rankings.
7. **Decide** certification status + action (see below).

## contacts

- **Identity resolution / clustering.** Rows for the same person cluster across the
  three source systems. Signals: shared `master_hint` (e.g. `MH-0000`), matching
  normalized email/phone, matching name. A clean cluster spans multiple *distinct*
  source systems for the *same* person → merge.
- **Field-level precedence (survivorship).** Assemble the canonical record field by
  field from the source systems by a fixed precedence, not by picking one row. In
  this environment contacts resolve name/depot from **HR Directory** and
  contact/consent from **Identity Registry** when present (observed precedence);
  confirm against a focus person whose expected outputs you can cross-check. The
  `master_id` is the retained public row id (the highest-sorting member row in the
  observed data). Preserve Unicode; email is trimmed + NFKC + lowercased; phone is
  digits only.
- **Quarantine** = no usable canonical contact channel (no usable email AND no usable
  phone). Empty/`N/A`/whitespace are not usable.
- **Contested identifier** = a shared contact identifier (e.g. a `SHARED-HELPDESK`
  phone/email) links rows that are clearly *different* people → do not auto-merge;
  the watchlist case stays contested.
- **Readiness** (case_scope wording): an entity is *eligible* only if `record_status`
  is ACTIVE and it retains ≥1 usable email or phone. A channel is *ready* only when
  its consent is GRANTED. Partition eligible entities into both / email_only /
  phone_only / not_ready (active+channel but consent not granted).
- **Region/depot rollup** groups canonical entities by the `region` field
  (`depot_key_field`).

## fuel / freight

- **Recognition via aliases.** Normalize the description (trim, collapse spaces,
  casefold) and match it to `v_reference_aliases.alias_text` within the row's
  `domain`, keeping only aliases *effective* at the cutoff:
  `reference_status = ACTIVE` **and** `valid_from <= date` **and**
  (`valid_to` is null or `>= date`). Distinct `canonical_value`s that match:
  - exactly one → recognized category;
  - **zero** → `unrecognized` (a.k.a. `unrecognized_alias`);
  - **more than one** → `ambiguous` (a.k.a. `ambiguous_alias`).
  (Beware aliases that are INACTIVE or not-yet/te no-longer effective at the cutoff —
  e.g. a term whose only live mappings fall outside the window is unrecognized.)
- **Mismatch** = a *valid* row whose recognized category ≠ `expected_fuel_type` /
  `expected_service_class`.
- **Quarantine** = unresolved class (unrecognized or ambiguous) OR invalid physical
  measure: fuel → non-positive `quantity` (`invalid_quantity`); freight →
  non-positive `billed_weight` (`invalid_weight`) or non-positive `distance`
  (`invalid_distance`). Report the `quarantine_reason_counts` the template lists.
- **Valid** rows (recognized, positive measures) feed normalized totals — including
  valid mismatches. Quarantined rows never do.
- **Exceptions.** An entity is an *exception* if it is a valid mismatch OR is
  quarantined. Merchant/carrier rankings order by exception (or mismatch-exposure)
  metric desc, then id asc, limited by the scope's ranking limit.
- **Normalized totals** = Σ over valid rows of converted volume/weight/distance and
  USD spend, broken out by recognized category (one row per canonical category).

## maintenance

- **Dedup** cross-snapshot by `event_id`, retaining the certified occurrence; report
  `duplicate_groups` (logical id, the snapshot_ids it appears in sorted, retained
  event id + retained snapshot id).
- **Issue / validity checks** feed both `issue_counts` and `invalid_event_ids`:
  missing timestamp (`event_time_raw` null/blank), invalid/unparsable timestamp,
  invalid odometer (out of range / non-positive after `odometer`→km conversion),
  negative labor (`labor_hours < 0`), extreme labor (implausibly large, e.g. a
  multi-hour ceiling like 120h). `invalid_event_ids` = events rejected for
  missing/unparsable time, invalid odometer range, or invalid labor range.
- **Odometer regression** is a *sequence-only* problem (per asset, sorted by time the
  odometer goes backwards). Regressions are reported in `corrected_metrics`
  (`regression_asset_ids`, `regression_event_ids`) and drive the cert gate — they are
  **not** put in `invalid_event_ids`.
- **corrected distance** = Σ over assets of (last reliable odometer − first reliable
  odometer) in km over the reconstructed valid history, at the scope's precision.
- **asset_risk_ranking** orders by the scope's policy (e.g. `rejected_event_count`
  desc, then `regression_event_count` desc, then `asset_id` asc), limited.

## Certification / close / release decision

The status→action map is universal:
`PASS → RELEASE`, `PASS_WITH_EXCEPTIONS → REVIEW_EXCEPTIONS`, `HOLD → BLOCK_AND_REMEDIATE`.
Determine `status` from what the scope provides:

- **Explicit thresholds** (e.g. contacts `status_thresholds` on a quarantine rate):
  `quarantine_rate = quarantined_rows / canonical_entities`, rounded as the template
  says. `PASS` if `rate <= pass_max`, else `PASS_WITH_EXCEPTIONS` if
  `rate <= pass_with_exceptions_max`, else `HOLD`.
- **Explicit gate** (maintenance `certification_gate`): if the gated condition holds
  (e.g. any odometer regression) emit the gate's status/action (`HOLD` /
  `BLOCK_AND_REMEDIATE`).
- **No explicit rule given** (fuel/freight): `PASS` only when there are no exceptions;
  `HOLD` when material data-quality exceptions exist (unresolved
  quarantines and/or class mismatches); `PASS_WITH_EXCEPTIONS` for a small tolerated
  residue. Compute the exception rate and apply the same thresholds the family uses
  (~0 for PASS, ~4% tolerance) — heavy mismatch/quarantine populations land on HOLD.
