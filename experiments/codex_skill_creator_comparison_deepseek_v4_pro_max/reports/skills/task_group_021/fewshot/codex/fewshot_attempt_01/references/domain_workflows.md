# Domain-Specific Reconciliation Rules

## Partner/People Contact Reconciliation

### Collection IDs
partner_onboarding_YYYYwNN or field_service_roster_YYYYwNN

### Source Systems
Records come from multiple source systems. The same person may appear in multiple systems with differing field values. Common source systems: CRM, Compliance Master, Partner Portal, HR Directory, Dispatch, Identity Registry.

### Field-Level Precedence
When a person appears in multiple sources, resolve each field by source-system precedence. The common precedence chains:

- **Name**: HR Directory > Dispatch > Identity Registry (or CRM > Partner Portal > Compliance Master)
- **Contact (email/phone)**: Identity Registry > Dispatch > HR Directory (or Partner Portal > Compliance Master > CRM)
- **Depot/Region**: HR Directory > Dispatch > Identity Registry
- **Consent**: Identity Registry > Dispatch > HR Directory
- **City**: Compliance Master > CRM > Partner Portal

Read the source_system field on each row to determine which source it came from. Apply precedence to select the canonical value for each field.

### Duplicate Clustering
Rows sharing a common email domain or phone pattern that suggest the same person. Cluster by matching on normalized email (lowercase, trimmed) or phone (digits only).

### Survivor Selection
Within a cluster, the survivor (master_id) is the row with the lexicographically highest row_id.

### Quarantine Rules
A row is quarantined when it has no usable email AND no usable phone (both missing, null, or structurally invalid).

### Readiness Rules
An entity is readiness-eligible if active (record_status == ACTIVE) and has at least one usable contact channel (email or phone). A channel is ready when consent_status == GRANTED.

### Channel Readiness Partitions
- **both**: Active, usable email AND phone, consent GRANTED.
- **email_only**: Active, usable email only, consent GRANTED.
- **phone_only**: Active, usable phone only, consent GRANTED.
- **not_ready**: Inactive, or no usable channels, or active with channels but consent not GRANTED.

### Focus People Output
For each focus person (identified by source_row_anchor in case_scope), report:
- member_row_ids: all row_ids in the cluster, sorted lexicographically.
- master_id: the survivor row_id.
- canonical_name, canonical_email, canonical_phone_digits, canonical_city: resolved canonical values.
- depot_code: canonical region value.
- canonical_consent_status, canonical_record_status: resolved status values.
- *_source_system: which source system each field was drawn from.
- resolution_outcome: FIELD_LEVEL_PRECEDENCE_APPLIED, SINGLE_SOURCE, CONTESTED_NO_AUTOMERGE, or NO_USABLE_CONTACT.

### Identifier Watchlist
When multiple identifier cases reference the same source row as their anchor, those cases are contested. A case is resolved (not contested) if its anchor row can be cleanly merged into a cluster. Contested cases are those where identifier resolution reveals conflicts that prevent automatic merging.

### Control Code Assignment
Identity codes (IC-xx): Depends on whether evidence rows span one source system (IC-25) or multiple (IC-70, IC-90). Quarantine identities get IC-40.
Outreach codes (OR-xx): Depends on record_status and consent. Assign per the readiness partition the person falls into.
Field-provenance codes (FP-xx): Depends on whether canonical fields come from one source (FP-20) or multiple (FP-55). Quarantine gets FP-75.

## Fuel Transaction Reconciliation

### Collection IDs
fuel_purchases_YYYY_MM

### Expected vs Actual Category
Each fuel transaction has an expected_fuel_type and a description. Match the description against reference aliases (GET /api/reference/aliases) to determine the recognized (actual) fuel type. Categories: BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED.

### Unrecognized Descriptions
- **Zero-match** (unrecognized): description matches no alias. Quarantined, LD-14.
- **Multi-match** (ambiguous): description matches multiple aliases with different categories. Quarantined, LD-88.

### Category Mismatch
Valid transaction where recognized fuel_type != expected_fuel_type. Mismatched transactions are still valid and enter normalized totals under the recognized fuel type. Flagged as mismatch but not quarantined.

### Invalid Quantity
Volume <= 0 is invalid. Quarantined.

### Unit Normalization
Convert all volumes to liters (L) using the conversions reference. Convert all spend to USD using the FX reference. Round to 2 decimal places unless otherwise specified.

### Focus Asset Rollups
For each focus asset_id, compute: logical_transaction_count (all), valid_transaction_count, mismatch_count, quarantine_count, exception_count (= mismatch + quarantine), volume_l (valid only), spend_usd (valid only).

### Merchant Exception Ranking
A merchant exception is a logical transaction with a category mismatch or quarantine condition. exception_count = mismatch_count + quarantine_count. Rank by exception_count descending, merchant_id ascending.

### Control Code Assignment
- **Reference decisions** (FUA-xxx): RB-42 for clean aliases, RB-17 for ambiguous aliases, RB-83 for unrecognized aliases.
- **Transaction source-basis**: SB-24 (CERTIFIED-only), SB-61 (both snapshots, retained CERTIFIED), SB-79 (PROVISIONAL-only).
- **Transaction ledger-disposition**: LD-53 (valid, single-snapshot), LD-72 (valid, dual-snapshot retained), LD-31 (valid mismatch), LD-14 (quarantined unrecognized), LD-88 (quarantined ambiguous).

## Freight Charge Reconciliation

### Collection IDs
freight_charges_YYYY_MM

### Expected vs Actual Service Class
Each freight charge has an expected_service_class and an alias_id. Resolve alias_id against reference aliases (GET /api/reference/aliases) to determine recognized service_class. Classes: EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD.

### Quarantine Reasons (mutually exclusive per charge)
- **ambiguous_alias**: alias maps to multiple service classes.
- **unrecognized_alias**: alias maps to zero service classes.
- **invalid_weight**: billed_weight <= 0.
- **invalid_distance**: distance <= 0.

A charge is quarantined if any of these conditions apply. Count each reason separately in quarantine_reason_counts.

### Class Mismatch
Valid charge where recognized service_class != expected_service_class. Mismatched charges are valid and enter normalized totals. Mismatch_spend_usd = spend on mismatched charges only.

### Unit Normalization
Convert weight to KG and distance to KM using conversions reference. Convert spend to USD using FX reference.

### Duplicate Resolution
When a charge_id appears in both CERTIFIED and PROVISIONAL, retain the CERTIFIED copy. Report each duplicate group with charge_id, raw_occurrence_count (= 2), snapshot_ids (both, sorted), and retained_snapshot_id (the CERTIFIED one).

### Carrier Ranking
mismatch_spend_usd = USD spend on valid charges with class mismatch for this carrier. Quarantined charges excluded. Rank by mismatch_spend_usd descending, carrier_id ascending. exception_count = mismatch_count + quarantine_count.

### Control Code Assignment
Same families as fuel (RB, SB, LD) applied to freight equivalents.
- **Reference rows** (FRA-xxx): RB codes by alias mapping clarity.
- **Source retention** (FC-xxx): SB codes by snapshot provenance.
- **Ledger routing** (FC-xxx): LD codes by charge disposition.

## Maintenance Event Reconciliation

### Collection IDs
maintenance_events_YYYY_qN

### Business Period
Filter events to the business_period from case_scope (start/end ISO-8601). Events outside the period are excluded from scoped analysis but counted in the raw authoritative count.

### Snapshot Resolution
CERTIFIED is authoritative. PROVISIONAL may contain additional events. When event_id appears in both, retain CERTIFIED copy. scoped_raw_row_count = sum of all raw rows across snapshots. authoritative_row_count = CERTIFIED snapshot row count (unfiltered).

### Invalid Events (mutually exclusive categories)
- **missing_timestamp**: timestamp field is null/missing.
- **invalid_timestamp**: timestamp cannot be parsed into a valid ISO-8601 date.
- **invalid_odometer**: odometer_km is null, negative, or outside expected range.
- **negative_labor**: labor_hours < 0.
- **extreme_labor**: labor_hours exceeds a reasonable threshold (e.g., > 24 in a single event).

An event can have multiple issues. Count each issue category independently. An event is invalid (rejected) if any issue is present.

### Odometer Regression
Within each asset, sort valid events by timestamp ascending. If a later event has a lower odometer_km than an earlier event, it is a regression. Regression events are still valid (included in corrected_metrics) but flagged separately. Count regression events and identify regression asset_ids.

### Corrected Distance
Sum across assets of (last reliable odometer reading - first reliable odometer reading) in the reconstructed history. Exclude invalid events. Include regression events (they have valid readings). Round to the declared decimal places.

### Asset Risk Ranking
rejected_event_count = count of invalid events for this asset. regression_event_count = count of regression events for this asset. Rank by rejected_event_count descending, regression_event_count descending, asset_id ascending. Limit to the number specified in case_scope.

### Control Code Assignment
- **maintenance_source_code** (MS-xx): MS-12 for PROVISIONAL-only events, MS-47 for valid CERTIFIED events, MS-86 for invalid CERTIFIED events.
- **history_route_code** (HR-xx): HR-19 for rejected (invalid) events, HR-33 for duplicate events (appears in both snapshots), HR-74 for valid non-duplicate events.

### Certification Gate
Presence of any odometer regression events triggers HOLD / BLOCK_AND_REMEDIATE.
