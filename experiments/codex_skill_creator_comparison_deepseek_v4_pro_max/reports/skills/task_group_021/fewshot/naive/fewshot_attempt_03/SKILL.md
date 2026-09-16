---
name: asteria-fleet-data-quality
description: Reconcile multi-source fleet data through the Asteria Data Quality Hub, resolve duplicate entities, assign quality and control codes, apply certification thresholds, and produce structured answer objects for partner contacts, fuel purchases, maintenance events, field service rosters, and freight charges.
---

This skill covers data reconciliation tasks against the Asteria Fleet Data Quality Hub, a read-only REST API for cross-source fleet business data. The hub surfaces overlapping record snapshots from multiple operational systems and requires you to resolve canonical entities, detect quality issues, assign internal control and policy codes, and produce structured certification decisions.

## Hub Connection

The hub is always at the base URL supplied in `environment_access.md`. All endpoints return JSON.

**Always start by reading `environment_access.md`** for the base URL, any query authentication token, and the list of allowed endpoints for the current task.

Standard endpoints (availability varies by task; only use those listed in `environment_access.md`):

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Connectivity check |
| GET | `/api/catalog/collections` | List available data collections |
| GET | `/api/catalog/schema` | Field definitions for all collections |
| GET | `/api/contacts` | Partner/field-service contact records |
| GET | `/api/transactions/fuel` | Fuel purchase transactions |
| GET | `/api/transactions/freight` | Freight charge transactions |
| GET | `/api/maintenance/events` | Maintenance event records |
| GET | `/api/reference/aliases` | String-to-category reference mappings |
| GET | `/api/reference/conversions` | Unit conversion factors |
| GET | `/api/reference/fx` | Currency exchange rates |
| GET | `/api/source-snapshots` | Available data snapshots |
| POST | `/api/query` | Read-only SQL queries (requires auth) |

The POST `/api/query` endpoint requires an `Authorization: Bearer` header when a token is specified in `environment_access.md`. Use it for aggregations, filtering, and joining when GET endpoints return paginated results or when you need to isolate specific subsets.

## General Workflow

Every reconciliation task follows the same sequence. Execute each phase in order and build up results incrementally.

### Phase 1: Discover

1. Call `GET /api/catalog/collections` to confirm the target collection exists.
2. Call `GET /api/catalog/schema` to learn the field names, types, and source systems for every collection you will touch.
3. Call `GET /api/source-snapshots` to list available snapshots.
4. Read `case_scope.json` for the collection ID, cutoff timestamp, and task-specific parameters (focus entities, decision panels, thresholds, ranking rules).

**Snapshot authority rule:** Every collection has two snapshots: `{collection_id}-certified` and `{collection_id}-provisional`. The `-certified` snapshot is always authoritative. When a logical entity (transaction, event, charge) appears in both, keep the certified row and discard the provisional duplicate.

### Phase 2: Retrieve

Pull the full dataset using the relevant GET endpoint or `POST /api/query`. For large collections that exceed a single response page, use SQL via `/api/query` with `LIMIT` and `OFFSET`, or filter by the business cutoff from `case_scope.json`.

Apply the cutoff: only rows with timestamps at or before the cutoff are in scope.

### Phase 3: Reconcile

This is the core phase and varies by domain, but the sub-steps are consistent across all five task types.

#### 3a. Deduplicate Overlapping Rows

Identify rows that represent the same logical entity across snapshots or source systems. The de-duplication key depends on the domain:

- **Contacts:** Same person = same normalized email. Normalize by trimming whitespace and lowercasing. Group all rows sharing a normalized email as a duplicate cluster. Pick a survivor row; prefer the row from the highest-priority source system and the one with the most complete data.
- **Transactions / Charges:** Same logical transaction = same transaction/charge ID appearing in multiple snapshots. Keep the certified-snapshot row; the provisional copy is a duplicate.
- **Events:** Same logical event = same event ID appearing in multiple snapshots. Keep the certified-snapshot row.

#### 3b. Resolve Canonical Fields

When duplicate cluster members disagree on a field value, resolve using source system precedence. The general precedence hierarchy (strongest first):

1. Compliance Master (contacts) / HR Directory (field service)
2. Partner Portal (contacts) / Identity Registry (field service) / Dispatch (field service)
3. CRM (contacts)

For contacts specifically: canonical email is the lowest-index (earliest) distinct normalized value in the cluster. Canonical phone is the digits-only form. Canonical city comes from the highest-precedence source that has a non-empty city value.

For field service roster contacts, there are three explicit source systems: HR Directory, Dispatch, Identity Registry. When they conflict on a field, use field-level precedence: the source that most consistently agrees with the majority across other clusters wins for that field.

#### 3c. Match Against Reference Aliases

For fuel and freight tasks, every transaction/charge has a description (or alias) that must be mapped to a canonical category.

1. Call `GET /api/reference/aliases` to get all alias-to-category mappings.
2. For each record, look up its description/alias in the reference.
3. Outcomes:
   - **Recognized:** Exactly one category match - assign that category.
   - **Unrecognized:** Zero matches - the record cannot be classified; quarantine it.
   - **Ambiguous:** Multiple matches - the record cannot be classified to a single category; quarantine it.

4. Compare the recognized category against the record's declared category field:
   - **Match:** The record is consistent.
   - **Mismatch:** Expected (from alias) != actual (in record). Flag as a category/class mismatch.

#### 3d. Validate Physical Measures

Check numeric fields for sanity:

- Volumes, weights, distances: must be positive (> 0). Zero or negative values are invalid.
- Odometer readings: must be present, parseable, positive, and monotonically increasing per asset within the period. An odometer regression is when a later reading for the same asset is less than an earlier reading.
- Labor hours: must be non-negative (>= 0). Negative labor is invalid. Extreme labor (above a reasonable threshold, discovered from the data distribution) is also flagged.
- Timestamps: must be present, parseable as ISO-8601, and fall within the business period.

Records with invalid measures or timestamps are excluded from valid/authoritative counts but may still appear in issue lists.

#### 3e. Assess Contact Usability (Contact Tasks Only)

For contact-oriented tasks, evaluate whether each canonical person is reachable:

- **Usable email:** Non-empty, contains `@`.
- **Usable phone:** Non-empty after stripping non-digit characters.
- **Active:** `record_status` is `ACTIVE` (case-insensitive).
- **Consent:** `consent_status` is `GRANTED` (case-insensitive).

A person is **quarantined** when they have no usable email AND no usable phone, regardless of status.

A person is **readiness-eligible** when they are ACTIVE and have at least one usable channel (email or phone).

A channel is **ready** (dispatchable) when consent is GRANTED. Count readiness partitions mutually exclusively:
- `both`: active, usable email, usable phone, consent granted
- `email_only`: active, usable email, no usable phone, consent granted
- `phone_only`: active, no usable email, usable phone, consent granted
- `not_ready`: active, at least one usable channel, but consent is not GRANTED (PENDING, DENIED, UNKNOWN), OR any active person with no usable channels, OR any inactive person

### Phase 4: Assign Codes

The hub uses compact internal codes for identity resolution, provenance tracking, outreach posture, reference policy, source retention, ledger routing, maintenance source, and history routing. These codes are **not explicitly documented** in the task materials; you must infer them from the data patterns visible in the hub records and from how the answer template constrains them.

#### Code Inference Strategy

For every code family, examine the data to find the distinguishing characteristic that separates records assigned one code value from those assigned another. Common code families and their typical determinants:

**Identity codes (IC-25, IC-40, IC-70, IC-90):**
- IC-25: Cluster where all member rows agree on identity fields (name, email, phone) - clean multi-source agreement.
- IC-40: Rows that are quarantined (no usable contact) - unresolvable identity.
- IC-70: Cluster where members disagree on some identity fields but a clear survivor was chosen - resolved conflict.
- IC-90: Cluster where members have conflicting identity that cannot be automatically resolved - contested.

**Outreach codes (OR-15, OR-35, OR-60, OR-80):**
- OR-15: Inactive exclusion - person is INACTIVE.
- OR-35: Channel-ready persons (either both, email_only, or phone_only) - consent granted, usable channel.
- OR-60: Quarantined rows - no usable contact channel.
- OR-80: Not-ready persons - active with usable channel but consent not granted, or other blocked states.

**Field provenance codes (FP-20, FP-55, FP-75):**
- FP-20: All cluster fields trace to a single source system.
- FP-55: Fields in a multi-source cluster were resolved using source precedence, with at least two sources contributing different fields.
- FP-75: Quarantined rows - fields cannot be verified or provenance is indeterminate.

**Reference policy codes (RB-17, RB-42, RB-83):**
- Look at the alias mapping from `/api/reference/aliases`. Each alias entry may carry metadata hinting at its reliability.
- RB-17: Direct, unambiguous alias with a single clear mapping.
- RB-42: Alias that required disambiguation (one of several possible but resolved).
- RB-83: Alias that has an exceptional or edge-case mapping (non-standard, legacy, or override).

**Source basis codes (SB-24, SB-61, SB-79):**
- SB-24: Record appears only in the provisional snapshot (not in certified); retained as best available.
- SB-61: Record appears only in the certified snapshot (unique to certified).
- SB-79: Record appears in both snapshots (certified copy retained, provisional discarded).

**Ledger disposition codes (LD-14, LD-31, LD-53, LD-72, LD-88):**
These reflect the accounting treatment of a transaction/charge:
- LD-14: Unrecognized category - cannot be classified; excluded from totals.
- LD-31: Category mismatch - recognized but expected != actual; accrual exposure.
- LD-53: Quarantined - invalid measures or ambiguous alias; excluded.
- LD-72: Clean valid record - recognized, matched, valid measures.
- LD-88: Ambiguous alias - matches multiple categories; excluded.

**Maintenance source codes (MS-12, MS-47, MS-86):**
- MS-12: Event from a specific diagnostic/maintenance system (determine from schema or snapshot metadata).
- MS-47: Event from another maintenance tracking system.
- MS-86: Event from a third operational system.

**History route codes (HR-19, HR-33, HR-74):**
- HR-19: Event that failed validation (bad timestamp, bad odometer, negative/extreme labor).
- HR-33: Valid event with no issues, from certified snapshot.
- HR-74: Valid event from provisional snapshot, or event with minor issues.

For each concrete task, verify your code assignments against the patterns visible in the data. For example, examine the `source_system` field, the `snapshot_id` field, and whether a record's category matches its expected category from the alias lookup. The correct code for a record is determined by these observable properties, not by rote memorization of train answers.

### Phase 5: Compute Metrics

#### Quality Summary (Contact Tasks)

- `raw_row_count`: Total rows in the collection at or before the cutoff.
- `canonical_entity_count`: Count of resolved canonical entities (one per duplicate cluster + singletons).
- `readiness_eligible_entity_count`: Canonical entities that are ACTIVE and have at least one usable channel.
- `duplicate_cluster_count`: Number of clusters with >1 member row.
- `quarantine_rate`: `quarantine_row_ids.length / canonical_entity_count`, rounded to 4 decimal places.

#### Audit Summary (Transaction/Charge Tasks)

- `raw_row_count`: Total rows in the collection at or before cutoff.
- `logical_{transaction,charge}_count`: Distinct IDs in the collection.
- `duplicate_raw_count`: Raw rows that are duplicates (total raw - logical count).
- `valid_{transaction,charge}_count`: Logical entities that are recognized, matched, and have valid measures.
- `mismatch_count`: Valid logical entities where expected category != actual category.
- `unrecognized_count`: Logical entities whose description/alias has zero recognized category matches.
- `ambiguous_count`: Logical entities whose description/alias has >1 recognized category match.
- `invalid_quantity_count` (fuel): Logical entities with non-positive volume.
- `quarantine_count`: Logical entities excluded from valid totals for any reason.
- Quarantine reason breakdowns (freight): `unrecognized_alias`, `ambiguous_alias`, `invalid_distance`, `invalid_weight`.

#### Normalized Totals (Transaction/Charge Tasks)

Sum physical measures and spend only over valid entities (recognized, matched, valid measures). Apply unit conversions via `/api/reference/conversions` and currency conversions via `/api/reference/fx` as needed. Round to 2 decimal places for all monetary and physical-measure fields. Group subtotals by the recognized canonical category, sorted alphabetically by category name.

#### Corrected Metrics (Maintenance Tasks)

- `valid_event_count`: Events that pass all validation checks.
- `total_distance_km`: Sum of (last reliable odometer - first reliable odometer) per asset, rounded to 2 decimal places.
- `regression_asset_ids`: Assets where at least one odometer regression was detected.
- `regression_event_ids`: Events that are part of an odometer regression.

### Phase 6: Complete Decision Panels

The `case_scope.json` specifies lists of IDs for which you must report codes. For each:

1. Retrieve the full record for that ID from the hub data.
2. Determine the applicable code by examining the record's properties (snapshot provenance, category match status, alias mapping characteristics).
3. Report in the answer template's required order (always lexicographically ascending by ID, unless otherwise specified).

**Reference decisions:** Map each scoped alias/reference ID to its `reference_policy_code` (RB-17, RB-42, RB-83).

**Transaction/Charge decisions:** Map each scoped transaction/charge ID to its `source_basis_code` (SB-24, SB-61, SB-79) and `ledger_disposition_code` (LD-14, LD-31, LD-53, LD-72, LD-88).

**Event decisions:** Map each scoped event ID to its `maintenance_source_code` (MS-12, MS-47, MS-86) and `history_route_code` (HR-19, HR-33, HR-74).

**Control cases (field service):** For each `control_case_id`, examine the `evidence_row_ids` from `case_scope.json`. Determine the `control_code` based on the `control_family` (IDENTITY, OUTREACH, FIELD_PROVENANCE) and the observable properties of those rows.

### Phase 7: Rank and Roll Up

#### Region Rollup (Contact Tasks)

Count canonical entities per region (the canonical city's mapped region). Sort lexicographically by region name. The region set is typically the enum listed in the answer template.

#### Depot Readiness (Field Service)

For each `depot_code` (the `region` field value), tally total persons, dispatchable (consent GRANTED, active, usable channel), and the three blocking reasons (blocked_consent, blocked_no_contact, blocked_inactive). The four disposition counts must sum to `total_person_count`.

#### Merchant/Carrier/Asset Ranking

- **Merchants (fuel):** Rank by `exception_count` descending, break ties with `merchant_id` ascending. An exception is a logical transaction with a category mismatch or a quarantine condition.
- **Carriers (freight):** Rank by `mismatch_spend_usd` descending, break ties with `carrier_id` ascending. Mismatch spend is the USD total of valid charges whose recognized service class differs from the expected class.
- **Assets (maintenance):** Rank by `rejected_event_count` descending, then `regression_event_count` descending, then `asset_id` ascending.

### Phase 8: Certify

Map the computed quality metrics to certification thresholds:

- If `quarantine_rate == 0` (or no issues detected): `PASS` / `RELEASE`.
- If `0 < quarantine_rate <= pass_with_exceptions_max_quarantine_rate`: `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`.
- If `quarantine_rate > pass_with_exceptions_max_quarantine_rate`: `HOLD` / `BLOCK_AND_REMEDIATE`.

For maintenance tasks, any odometer regression forces `HOLD` / `BLOCK_AND_REMEDIATE` regardless of other metrics.

For field service roster tasks, the release decision follows the same PASS / PASS_WITH_EXCEPTIONS / HOLD model based on the dispatchable ratio and the number of contested identifier cases.

## Answer Construction

Assemble the final JSON object to conform exactly to `answer_template.json`. Key rules:

- Every field in `required` arrays must be present.
- No additional properties beyond those in the schema.
- All arrays must be sorted as specified: lexicographically ascending by ID unless the template or `case_scope.json` specifies otherwise (e.g., ranking arrays use the ranking sort).
- Numeric precision: integers are exact; floating-point values use the specified `multipleOf` or the documented decimal places (typically 2 for money/measures, 4 for rates).
- All IDs must match the patterns in the schema (e.g., `^PAR-C[0-9]{5}$`, `^FT-202601-[0-9]{6}$`).

## Task-Type Reference

### Partner Onboarding Contact Certification

- **Collection endpoint:** `/api/contacts`
- **Deduplication key:** Normalized lowercase email
- **Quarantine condition:** No usable email AND no usable phone
- **Readiness eligibility:** ACTIVE AND (usable email OR usable phone)
- **Channel readiness:** Channel is ready only when consent is GRANTED
- **Focus clusters:** Each has a `seed_row_id`; resolve full cluster from normalized email grouping
- **Survivor selection:** Prefer rows from Compliance Master, then Partner Portal, then CRM; within same source, prefer the row with the most non-empty fields
- **Canonical city:** From highest-precedence source with non-empty city; source system must be reported
- **Key output arrays:** `focus_clusters` (5 items), `region_rollup` (6 items), `quarantine_row_ids`, `control_codes`

### Fuel Purchase Audit

- **Collection endpoint:** `/api/transactions/fuel`
- **Reference endpoint:** `/api/reference/aliases` (maps fuel descriptions to fuel types)
- **Deduplication key:** `transaction_id` across snapshots
- **Quarantine conditions:** Unrecognized description, ambiguous description, invalid (<=0) volume
- **Mismatch:** Expected fuel type (from alias) != recorded fuel type
- **Normalized volume:** Convert to liters using `/api/reference/conversions`
- **Normalized spend:** Convert to USD using `/api/reference/fx`
- **Fuel type totals:** Exactly 5 rows: BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED (alphabetical order)
- **Key output arrays:** `mismatch_transaction_ids`, `unrecognized_transaction_ids`, `focus_assets` (4 items), `policy_decision_panel`

### Maintenance Event Audit

- **Collection endpoint:** `/api/maintenance/events`
- **Deduplication key:** `event_id` across snapshots
- **Issue types:** missing_timestamp, invalid_timestamp, invalid_odometer, negative_labor, extreme_labor, odometer_regression
- **Odometer regression:** Detected per asset; any event where a later reading < earlier reading within the period
- **Corrected distance:** Sum of (last valid - first valid) odometer per asset, in km, 2 decimal places
- **Duplicate groups:** Groups of event IDs appearing in multiple snapshots
- **Key output arrays:** `event_decision_panel` (8 items), `duplicate_groups`, `invalid_event_ids`, `corrected_metrics`, `asset_risk_ranking`

### Field Service Roster Readiness

- **Collection endpoint:** `/api/contacts`
- **Source systems:** HR Directory, Dispatch, Identity Registry
- **Deduplication:** Multi-source merge; same person may appear in multiple sources with different row IDs
- **Merge key:** Normalized cross-source identity matching (name + email + phone similarity)
- **Focus people:** 5 predefined anchors; resolve full merge cluster and all canonical fields
- **Resolution outcomes:** FIELD_LEVEL_PRECEDENCE_APPLIED (multi-source, conflicts resolved), SINGLE_SOURCE (only one source), CONTESTED_NO_AUTOMERGE (identifier conflict, cannot resolve), NO_USABLE_CONTACT (quarantined)
- **Identifier watchlist:** 3 predefined cases; if the anchor row's merge cluster cannot be resolved, the case remains in `contested_cluster_ids`
- **Dispatchable:** ACTIVE, usable channel, consent GRANTED
- **Policy control cases:** 11 cases across IDENTITY, OUTREACH, FIELD_PROVENANCE families
- **Key output arrays:** `focus_people` (5 items), `contested_cluster_ids`, `dispatchable_master_ids`, `readiness_by_depot`, `policy_control_cases` (11 items)

### Freight Charge Accrual

- **Collection endpoint:** `/api/transactions/freight`
- **Reference endpoint:** `/api/reference/aliases` (maps freight aliases to service classes)
- **Deduplication key:** `charge_id` across snapshots
- **Quarantine conditions:** Unrecognized alias, ambiguous alias, invalid (<=0) distance, invalid (<=0) weight
- **Mismatch:** Expected service class (from alias) != recorded service class
- **Normalized weight:** Convert to kg using `/api/reference/conversions`
- **Normalized distance:** Convert to km using `/api/reference/conversions`
- **Normalized spend:** Convert to USD using `/api/reference/fx`
- **Service class totals:** Exactly 5 rows: EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD (alphabetical order)
- **Carrier ranking:** By mismatch_spend_usd descending (valid mismatches only, not quarantined)
- **Key output arrays:** `class_mismatch_charge_ids`, `quarantine_charge_ids`, `duplicate_groups`, `decision_panels`, `carrier_ranking` (5 items)

## Troubleshooting

**API returns empty or unexpected results:** First call `/health` to verify connectivity. Then call the catalog endpoints to confirm the collection name. Collection IDs in `case_scope.json` match the catalog exactly. The query endpoint may return 401 if the auth token is missing; check `environment_access.md` for the correct header.

**Data exceeds single response page:** Use `POST /api/query` with SQL `SELECT * FROM collection_id WHERE timestamp <= 'cutoff' ORDER BY id` plus `LIMIT`/`OFFSET` to page through results. Alternatively, filter by the specific IDs needed from `case_scope.json` if the task only requires those.

**Cannot determine code values:** Examine the concrete records from the API. Compare the record's `source_system`, `snapshot_id`, category match status, and field completeness against the code families described in Phase 4. The data itself reveals the code logic -- for instance, a record with `snapshot_id` ending in `-certified` and no provisional twin gets `SB-61`, while one present in both gets `SB-79`.

**Odometer regression detection:** Group events by `asset_id`, sort by `event_timestamp` ascending, and compare consecutive `odometer_reading` values. Any pair where a later reading is strictly less than an earlier reading is a regression.
