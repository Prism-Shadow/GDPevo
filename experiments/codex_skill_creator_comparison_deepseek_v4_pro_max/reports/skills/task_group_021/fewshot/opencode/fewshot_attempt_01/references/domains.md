# Domain-specific patterns

## Contents

- [Contact matching and deduplication](#contact-matching-and-deduplication)
- [Fuel transaction audit](#fuel-transaction-audit)
- [Freight charge audit](#freight-charge-audit)
- [Maintenance event audit](#maintenance-event-audit)
- [Decision code assignment patterns](#decision-code-assignment-patterns)
- [Cross-domain constants](#cross-domain-constants)

---

## Contact matching and deduplication

Used in partner-onboarding certification and field-service roster tasks.

### Source systems and precedence

Contact records arrive from multiple source systems. The same real-world
person may appear in multiple systems under different `row_id` values.
Identify them by shared attributes.

**Matching keys (in priority order):**

1. Normalized email (trimmed, NFKC-normalized, lowercase) — strongest signal.
2. Digits-only phone — strong but not unique.
3. Name similarity (NFKC-normalized, case-folded) — used when email/phone are absent.

Rows that share at least one key and belong to different source systems form a
**cluster**. All rows in a cluster represent the same canonical person.

### Survivorship

When a cluster contains rows from multiple source systems, select a **survivor
row** whose `row_id` becomes the stable identifier:

1. Prefer the row from the system with the highest field-level precedence for
   the most important fields (name, contact channels).
2. Within the same system, prefer the row with the most complete contact
   channels (both email and phone populated).
3. Break ties by lexicographic `row_id` ascending.

**Field-level source-system precedence (contacts):**

| Field | Precedence (highest first) |
|---|---|
| `name` | HR Directory → Identity Registry → Dispatch → Compliance Master → CRM → Partner Portal |
| `email`, `phone` | Identity Registry → HR Directory → Dispatch → Compliance Master → CRM → Partner Portal |
| `city`, `region` | Compliance Master → HR Directory → Dispatch → Identity Registry → CRM → Partner Portal |
| `consent_status` | Identity Registry → HR Directory → Dispatch → CRM → Compliance Master → Partner Portal |
| `record_status` | HR Directory → Identity Registry → Dispatch → Compliance Master → CRM → Partner Portal |

When a field is missing in the highest-precedence source, fall through to the
next source that has a non-null, non-empty value for that field.

**Canonical field resolution:** For each field of the canonical person, take the
value from the highest-precedence source system that provides a non-null,
non-empty value. The `name_source_system`, `contact_source_system`,
`depot_source_system`, and `consent_source_system` fields report which source
supplied the surviving value for that category.

### Quarantine rules for contacts

A row is quarantined when both `email` and `phone` are null or empty after
normalization. Quarantined rows are excluded from readiness calculations but
remain in canonical-entity counts.

### Channel readiness

For each canonical person that is `ACTIVE` and has at least one usable channel
(email or phone non-empty):

- **`both`**: email non-empty AND phone non-empty AND consent is `GRANTED`.
- **`email_only`**: email non-empty AND phone empty AND consent is `GRANTED`.
- **`phone_only`**: phone non-empty AND email empty AND consent is `GRANTED`.
- **`not_ready`**: neither channel usable OR consent not `GRANTED`.

Each person counts in exactly one bucket.

### Identifier watchlist (field-service roster)

The case scope supplies watchlist rows via `identifier_watchlist`. For each
identifier case, check whether the anchor row resolves to a cluster that
contains rows from a different identifier case. If the anchor row shares
matching keys with rows from another identifier case, the case is **contested**
and listed in `contested_cluster_ids`.

### Focus people resolution

Resolve the focus-person clusters specified in the case scope. Each focus
person is anchored to a `source_row_anchor`. Find the cluster containing that
row. Report all `member_row_ids`, the `master_id` (survivor `row_id`),
canonical fields, source-system provenance for each field category, and the
`resolution_outcome`:

- `FIELD_LEVEL_PRECEDENCE_APPLIED` — multi-source cluster, survivor selected
  via field-level precedence rules.
- `SINGLE_SOURCE` — only one source system contributed rows.
- `CONTESTED_NO_AUTOMERGE` — watchlist conflict prevents clean resolution.
- `NO_USABLE_CONTACT` — the canonical person has no usable contact channel.

### Depots and readiness by depot

The `region` field functions as the depot code. Partition canonical people by
region and report the readiness breakdown per depot. `total_person_count`
includes all canonical people in that region regardless of readiness.
`dispatchable_person_count` counts those with consent GRANTED, record ACTIVE,
and at least one usable channel. `blocked_consent_count` counts ACTIVE people
with a usable channel but non-granted consent. `blocked_no_contact_count`
counts people with no usable channel. `blocked_inactive_count` counts INACTIVE
people with a usable channel.

## Fuel transaction audit

### Category matching via aliases

The `/api/reference/aliases` endpoint maps free-text `description` values to
canonical fuel types: `BIODIESEL`, `DIESEL`, `ELECTRIC_CHARGE`,
`PREMIUM_UNLEADED`, `UNLEADED`.

For each transaction:

1. Look up `description` in the alias table, matching `raw_description`
   case-insensitively.
2. If exactly one alias matches → recognized, with that `canonical_category`.
3. If zero aliases match → unrecognized.
4. If multiple aliases match with different canonical categories → ambiguous.

### Mismatch detection

Compare `expected_fuel_type` with the recognized canonical category. If they
differ, flag as a mismatch. Unrecognized and ambiguous transactions are not
mismatches — they have no recognized category to compare.

### Quantity validation

`quantity` must be strictly positive. Zero, null, or negative values are
invalid and cause quarantine.

### Unit normalization

Convert all volumes to liters using `/api/reference/conversions`. Look up the
factor from `quantity_unit` to `L`. Multiply `quantity` by the factor.

### Currency normalization

Convert all spend to the base currency (USD) using `/api/reference/fx`. If a
transaction's `currency` is not the base, multiply `spend` by the rate for
that `currency` to `base_currency`. If already in the base currency, use as-is.

### Quarantine for fuel

A transaction is quarantined when:

- Its description has zero recognized canonical categories (unrecognized).
- OR its description matches multiple canonical categories (ambiguous).
- OR its quantity is ≤ 0 (invalid).

Quarantined transactions are excluded from normalized totals but counted in
exception statistics and the exception merchant ranking.

### Exception merchant ranking

An **exception** is a logical transaction that is quarantined or has a
category mismatch. Count exceptions per merchant. Rank by `exception_count`
descending, then `merchant_id` ascending. Take the top N as specified in
`case_scope.merchant_ranking_limit`.

### Focus assets

For each requested focus asset, report `logical_transaction_count` (all
transactions for that asset), `valid_transaction_count` (non-quarantined),
`mismatch_count`, `quarantine_count`, `exception_count` (mismatch +
quarantine), and the normalized `volume_l` and `spend_usd` for valid
transactions only.

## Freight charge audit

### Category matching via aliases

Same pattern as fuel, but canonical categories are service classes: `EXPRESS`,
`HAZMAT`, `OVERSIZE`, `REFRIGERATED`, `STANDARD`.

The charge carries an `alias_id` field. Look up that `alias_id` in the alias
table to find the `canonical_category`. If the alias maps to exactly one
canonical category, the charge is recognized. If zero or multiple, it is
unrecognized or ambiguous respectively.

Note: a single `alias_id` may map to multiple rows in the alias table with
different `canonical_category` values. Count distinct canonical categories
for that alias. If the count is 1, recognized; if 0, unrecognized; if >1,
ambiguous.

### Mismatch detection

Compare `expected_service_class` with the recognized canonical category. If
they differ, flag as a mismatch.

### Physical measure validation

Both `billed_weight` and `distance` must be strictly positive. Zero, null, or
negative values for either field cause quarantine.

### Unit normalization

Convert weight to KG and distance to KM using `/api/reference/conversions`.

### Currency normalization

Same as fuel — convert to the base currency via `/api/reference/fx`.

### Quarantine for freight

A charge is quarantined when any of these holds:

- Its alias is unrecognized (no canonical class) → `unrecognized_alias`.
- Its alias is ambiguous (multiple canonical classes) → `ambiguous_alias`.
- Its `billed_weight` is ≤ 0 → `invalid_weight`.
- Its `distance` is ≤ 0 → `invalid_distance`.

Break down quarantine counts by reason in `quarantine_reason_counts`.

### Carrier ranking

Carriers are ranked by accrual exposure: normalized USD spend on valid
charges whose recognized service class differs from the expected class.
Sort by `mismatch_spend_usd` descending, then `carrier_id` ascending.
Take the top N from `case_scope.carrier_ranking_limit`.

### Duplicate charge groups

A charge may appear in multiple snapshots with the same `charge_id`. When it
does, report it in `duplicate_groups` with the `charge_id`,
`raw_occurrence_count` (number of snapshots), `snapshot_ids` (sorted
lexicographically), and `retained_snapshot_id` (always the CERTIFIED one).

## Maintenance event audit

### Validation rules

Each event is checked independently:

| Condition | Issue |
|---|---|
| `event_timestamp` is null or empty string | `missing_timestamp` |
| `event_timestamp` present but unparseable as ISO-8601 | `invalid_timestamp` |
| `odometer_km` is null, negative, or > 999999 | `invalid_odometer` |
| `labor_hours` is null or negative | `negative_labor` |
| `labor_hours` > 100 | `extreme_labor` |

Events that fail any check are **rejected** and listed in `invalid_event_ids`.

### Odometer regression detection

For each asset, collect its valid (non-rejected) events. Sort by
`event_timestamp` ascending. Walk the sequence: if an event's `odometer_km` is
strictly less than the running maximum odometer seen so far for that asset,
flag it as a regression.

Regressions are reported in `corrected_metrics.regression_event_ids` and
`corrected_metrics.regression_asset_ids`. They do NOT enter `invalid_event_ids`
— only the validation failures above enter that array.

### Corrected distance

For each asset, compute `last_reliable_odometer - first_reliable_odometer`.
A "reliable" odometer comes from a valid (non-rejected) event. Sum across all
assets. Round to the declared precision (typically 2 decimal places).

### Asset risk ranking

Rank by `rejected_event_count` descending, then `regression_event_count`
descending, then `asset_id` ascending. Take the top N from the case scope.
Rank position starts at 1.

### Duplicate event groups

Events with the same `event_id` appearing in multiple snapshots are duplicates.
Group by `event_id`. Report each group with the logical event ID, all
snapshot IDs (sorted lexicographically), the retained event ID, and the
retained snapshot ID (always CERTIFIED).

## Decision code assignment patterns

These are the code families and their meanings, extracted from the training
evidence. Within each family, map data attributes to codes consistently.

### Identity codes (IC-25, IC-40, IC-70, IC-90)

Assigned based on source-system overlap and data completeness:

- **IC-25**: Single-source cluster, clean resolution, no ambiguity.
- **IC-40**: Single row with no usable contact channels (quarantined person).
- **IC-70**: Multi-source cluster, field-level precedence resolved cleanly,
  all key fields populated.
- **IC-90**: Multi-source cluster with partial data, missing fields, or
  contested identity resolution.

### Outreach codes (OR-15, OR-35, OR-60, OR-80)

Assigned based on contact usability and consent:

- **OR-15**: INACTIVE record (excluded from outreach).
- **OR-35**: GRANTED consent with usable channels (both, email-only, or
  phone-only).
- **OR-60**: No usable contact channels (quarantined).
- **OR-80**: PENDING, DENIED, or UNKNOWN consent, but usable channels exist.

### Field-provenance codes (FP-20, FP-55, FP-75)

Assigned based on source-system diversity for field resolution:

- **FP-20**: All surviving field values from a single source system.
- **FP-55**: Surviving fields from two different source systems, resolution
  unambiguous.
- **FP-75**: Surviving fields from three or more source systems, or
  resolution contested / partial.

### Reference-policy codes (RB-17, RB-42, RB-83)

Used in fuel and freight audits for alias references:

- **RB-17**: Alias maps to exactly one canonical category with PATTERN or
  FUZZY match type.
- **RB-42**: Alias maps to exactly one canonical category with EXACT match
  type.
- **RB-83**: Alias maps to zero canonical categories (unrecognized) or
  multiple (ambiguous).

### Source-basis codes (SB-24, SB-61, SB-79)

Used in fuel and freight audits for transaction provenance:

- **SB-24**: Row exists only in a PROVISIONAL snapshot (no CERTIFIED
  equivalent).
- **SB-61**: Row retained from the CERTIFIED snapshot.
- **SB-79**: Row retained from the CERTIFIED snapshot but with ambiguous or
  unrecognized category (degraded signal).

### Ledger-disposition codes (LD-14, LD-31, LD-53, LD-72, LD-88)

Used in fuel and freight audits for how a transaction enters the ledger:

- **LD-14**: Unrecognized (zero canonical category matches).
- **LD-31**: Valid, recognized, category mismatch.
- **LD-53**: Invalid quantity (≤ 0).
- **LD-72**: Valid, recognized, category matched.
- **LD-88**: Ambiguous (multiple canonical category matches).

### Maintenance-source codes (MS-12, MS-47, MS-86)

Used in maintenance-event audits:

- **MS-12**: Event from PROVISIONAL snapshot only (no CERTIFIED equivalent).
- **MS-47**: Valid event from CERTIFIED snapshot.
- **MS-86**: Valid event from CERTIFIED snapshot that triggered an odometer
  regression or was near a regression boundary.

### History-route codes (HR-19, HR-33, HR-74)

Used in maintenance-event audits:

- **HR-19**: Valid event with an odometer regression.
- **HR-33**: Valid event from PROVISIONAL-only source (no regression).
- **HR-74**: Valid event from CERTIFIED snapshot with no regression.

## Cross-domain constants

### Certification thresholds

All tasks use the same mechanical certification logic:

```
if quarantine_rate <= pass_max_quarantine_rate:
    status = "PASS", action = "RELEASE"
elif quarantine_rate <= pass_with_exceptions_max_quarantine_rate:
    status = "PASS_WITH_EXCEPTIONS", action = "REVIEW_EXCEPTIONS"
else:
    status = "HOLD", action = "BLOCK_AND_REMEDIATE"
```

Additionally, maintenance tasks apply the `odometer_regression_status` and
`odometer_regression_action` from the case scope as a gate: any detected
regression forces that status regardless of other metrics.

### General patterns in the training evidence

- **Quarantine rate computation for contacts:** quarantined rows / canonical
  entity count, rounded to 4 decimal places.
- **Readiness-eligible count:** canonical entities that are ACTIVE and not
  quarantined.
- **Duplicate cluster count:** number of clusters with more than one member
  row (multi-source or multi-row groups).
- **Canonical entity count:** total number of resolved clusters (including
  single-row clusters).
- **Raw row count:** total rows across all snapshots before deduplication.
