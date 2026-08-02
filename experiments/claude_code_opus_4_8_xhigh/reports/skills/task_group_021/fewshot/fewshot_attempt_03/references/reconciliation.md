# Reconciliation methodology

Every task in this family is the same shape: **reconcile overlapping source snapshots
of one collection as of a business cutoff, detect data-quality defects, normalize, and
produce a certified audit**. The output keys differ per family, but the engine is shared.

## 0. Universal steps
1. Parse `case_scope.json`: `collection_id`, cutoff (`business_cutoff` / `cutoff_at` /
   `as_of` + `business_period`), focus/anchor lists, ranking limits, thresholds,
   ordering rules. **Every scoped/focus/anchor ID in the output must come from the
   scope or the public data — never invent IDs.**
2. List snapshots. The **authoritative snapshot = the CERTIFIED one**,
   id `<collection_id>-certified`. Report it as `authoritative_snapshot_id`.
   The catalog also holds unrelated collections (other periods, archives, and
   context-only `quote`/`telematics` families) — ignore them; operate **only** on the
   exact `collection_id` from the scope.
3. `raw_row_count` = all in-scope raw rows across snapshots (respect the cutoff/period).
   `logical_*_count` = distinct business keys after dedup.
   `duplicate_raw_count` = raw − logical.

## 1. Snapshot precedence & de-duplication (fuel / freight / maintenance)
Group raw rows by business key (`transaction_id` / `charge_id` / `event_id`).
For a key present in more than one snapshot, **retain the CERTIFIED occurrence** and
drop the others (they are cross-snapshot duplicates).
- A key in the CERTIFIED snapshot only → single, certified-sourced.
- A key in both CERTIFIED and PROVISIONAL → duplicate; retained = certified.
- A key in the PROVISIONAL snapshot only → retained = provisional (no certified copy).

This 3-way "retention basis" drives the `SB-*` (fuel/freight source-retention) and
`MS-*` (maintenance source) codes — see `codebook.md`.

## 2. Category / class resolution via aliases (fuel & freight)
Resolve each record's free-text description to a canonical category.
- Pull `v_reference_aliases WHERE domain='<fuel|freight>'`.
- **Only aliases that are authoritative *as of the cutoff* count**: `reference_status =
  'ACTIVE'` AND `valid_from <= cutoff_date <= COALESCE(valid_to, +inf)`.
  Exclude INACTIVE, PROVISIONAL, expired, and not-yet-effective aliases.
- Match `alias_text` against the description on **word/token boundaries**, case-insensitive
  (not raw substring — e.g. "biodieseline" must NOT match "biodiesel").
- Count the set of *distinct canonical_values* matched:
  - exactly one → recognized class. If it differs from the record's expected class
    (`expected_fuel_type` / `expected_service_class`) → **class mismatch** (still valid,
    still enters normalized totals).
  - zero → **unrecognized** (quarantine).
  - two+ → **ambiguous** (quarantine).

## 3. Quarantine rules
A record is quarantined (excluded from normalized totals) when:
- **fuel/freight:** unrecognized class, OR ambiguous class, OR a non-positive/invalid
  physical measure (`quantity<=0`; `billed_weight<=0`; `distance<=0`).
  Track reason counts separately (`unrecognized_alias`, `ambiguous_alias`,
  `invalid_weight`, `invalid_distance`).
- **maintenance:** missing/unparsable `event_time_raw`; odometer outside a valid range
  (e.g. negative); labor outside a valid range (negative labor, or implausibly large
  "extreme" labor hours). These become `invalid_event_ids`. Track `missing_timestamp`,
  `invalid_timestamp`, `invalid_odometer`, `negative_labor`, `extreme_labor`,
  `odometer_regression` counts (the template names them, which tells you which defect
  classes to detect).
- **contacts:** a row/person with **no usable contact channel** (no usable email AND no
  usable phone after normalization) is quarantined. Empty string, whitespace, `N/A`,
  and null all count as "no channel".

## 4. Normalization (only over valid, non-quarantined records)
- **volume/weight/distance/odometer:** value × conversion `factor` for
  (`kind`, `from_unit`→canonical). Identity units have factor 1.
- **money:** `amount × usd_per_unit`, using the **CERTIFIED** FX row for the record's
  business date and currency. USD is not exempt — look up its rate too.
- Round per the answer contract (usually 2 dp for money/volume/weight/distance; km to 2 dp
  for maintenance distance). Round only at the reported total, after summing.
- **Corrected distance (maintenance):** per asset, over the reconstructed valid history
  (ordered by event time), sum (last reliable odometer − first reliable odometer);
  then sum across assets. An **odometer regression** = an event whose odometer is lower
  than the prior reliable reading for that asset in sequence (report these events/assets;
  they do not become `invalid_event_ids`).

## 5. Identity resolution & canonicalization (contacts)
- Cluster raw rows into people by matching normalized identifiers (email lowercased +
  NFKC + trimmed; phone reduced to digits; name compared case-insensitively).
  `canonical_person_count` counts resolved people **including** quarantined ones.
  `merged_duplicate_cluster_count` = clusters with >1 row.
- **Master / survivor row** = the cluster member carrying a non-null `master_hint`
  (fallback: most recent `business_updated_at`, then a CERTIFIED source). Report its
  `row_id` as `survivor_row_id` / `master_id`.
- **Field-level precedence:** each canonical field is taken from the highest-precedence
  source system that supplies a usable value for that field, so different fields can come
  from different source rows (`*_source_system` names the winner). When fields are drawn
  from more than one source, `resolution_outcome = FIELD_LEVEL_PRECEDENCE_APPLIED`;
  a lone row is `SINGLE_SOURCE`; a shared/contested identifier that must not auto-merge is
  `CONTESTED_NO_AUTOMERGE`; a person with no channel is `NO_USABLE_CONTACT`. Determine the
  per-field precedence empirically for the collection's specific source systems, then keep
  it consistent across all people.
- Canonical field formatting: `canonical_email` trimmed+NFKC+lowercase;
  `canonical_phone_digits` digits only (string); `canonical_name` Unicode-preserving,
  whitespace-trimmed, properly cased; `canonical_city` / `depot_code`(=region) as the
  chosen source's value.

## 6. Contact readiness (contacts)
Over resolved people:
- **readiness-eligible** = `record_status=ACTIVE` AND at least one usable channel.
- Disposition precedence (mutually exclusive):
  1. no usable channel → quarantined / `blocked_no_contact` (→ `OR-60`, `FP-75`)
  2. else INACTIVE → `blocked_inactive` / inactive-exclusion (→ `OR-15`)
  3. else consent GRANTED → **dispatchable / ready** (→ `OR-35`)
  4. else (PENDING/DENIED/UNKNOWN) → `blocked_consent` / not_ready (→ `OR-80`)
- `channel_readiness` (partition of readiness-eligible people): `both` / `email_only` /
  `phone_only` (ready buckets, consent granted) vs `not_ready` (eligible but consent not
  granted). Inactive and no-channel people are **outside** the readiness-eligible set.
- `quarantine_rate` = quarantined rows ÷ canonical entities, rounded to 4 dp.

## 7. Exception ranking (fuel merchants / freight carriers / maintenance assets)
- fuel/freight: an **exception** = a retained record that is a *valid class mismatch* OR
  is *quarantined*. Rank the grouping entity (merchant_id / carrier_id) by the metric the
  contract names (fuel: exception_count desc; freight: mismatch_spend_usd desc where
  mismatch_spend = normalized USD on valid class-mismatch charges), tie-break by ID ascending.
- maintenance: rank assets by `rejected_event_count` desc, then `regression_event_count`
  desc, then `asset_id` asc; keep `limit` from scope.

## 8. Certification status → action
Status/action vocabulary is fixed:
`PASS→RELEASE`, `PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS`, `HOLD→BLOCK_AND_REMEDIATE`.
- **contacts:** apply `status_thresholds` + `status_action_map` from the case scope,
  e.g. `quarantine_rate == pass_max` → PASS; `<= pass_with_exceptions_max` →
  PASS_WITH_EXCEPTIONS; above → HOLD.
- **maintenance:** apply the `certification_gate` — any odometer regression present ⇒
  HOLD / BLOCK_AND_REMEDIATE.
- **fuel/freight:** no numeric threshold is given; the conservative gate observed is
  HOLD / BLOCK_AND_REMEDIATE whenever unresolved quarantine exceptions exist. Prefer any
  explicit gate the scope provides; otherwise: clean ⇒ PASS, only valid mismatches ⇒
  PASS_WITH_EXCEPTIONS, any quarantine ⇒ HOLD.

## Cross-checks before emitting
- Snapshot `row_count`s should reconcile with your `raw_row_count`.
- Partitions must sum to their totals (readiness buckets = eligible; per-depot dispositions
  = total_person_count; fuel_type/service_class rows cover the full valid set).
- Re-derive each control code from the record evidence, not from memory of a prior task.
