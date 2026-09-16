---
name: asteria-fleet-dq-hub
description: Use this skill when the user needs to reconcile, audit, certify, or normalize data through the Asteria Fleet Data Quality Hub REST API. This skill covers fleet data domains (fuel, freight, maintenance, field-service roster, partner onboarding) where the task involves reading a collection catalog, resolving overlapping source snapshots, classifying records, producing canonical entity results, assigning opaque control codes, and making certification decisions. Use it whenever the user mentions Asteria, fleet data quality, data reconciliation, source-snapshot resolution, or any of the Asteria data domains even if they do not explicitly name the hub.
---

# Asteria Fleet Data Quality Hub Reconciliation

## Hub access

The hub base URL and allowed endpoints are in the task's `environment_access.md`, typically at the variable value supplied for the task environment base URL. Common interfaces:

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/catalog/collections` | GET | List available data collections |
| `/api/catalog/schema` | GET | Field layout for a collection |
| `/api/source-snapshots` | GET | Snapshot metadata (status, source system) |
| `/api/query` | POST | SQL SELECT against collection tables |
| `/api/contacts` | GET | Contact records for people-domain tasks |
| `/api/transactions/fuel` | GET | Fuel-purchase transactions |
| `/api/transactions/freight` | GET | Freight-charge transactions |
| `/api/maintenance/events` | GET | Maintenance-event records |
| `/api/reference/aliases` | GET | Alias-to-canonical-category mappings |
| `/api/reference/conversions` | GET | Unit-conversion factors |
| `/api/reference/fx` | GET | Foreign-exchange rates |

Always check the case scope for the `collection_id` first, then use the catalog and schema endpoints to understand what columns are available before querying. When the task directs you to a domain-specific transaction endpoint, prefer it over generic `/api/query` for that table, but use `/api/query` for anything custom or for filtered bulk reads.

## Reconciliation workflow

Follow this ordered process every time. Adapt the specific classifications to the domain, but keep the sequence.

### 1. Source selection

Read `/api/source-snapshots`. Identify the authoritative snapshot for the collection: it is the one whose ID contains `certified`. This snapshot's rows take precedence over those from `provisional` or any other snapshot when the same logical ID appears in both. Note the authoritative snapshot ID for the answer.

### 2. Raw-data acquisition

Collect every row from the scoped collection. If the collection has a dedicated GET endpoint, use it. Otherwise use `POST /api/query` with a SQL SELECT. Check the schema first to know the table name and columns.

If the data is paginated (response includes a `next_offset` or the result set is truncated), fetch every page. Accumulate all rows locally before any classification.

Also collect any reference data the task needs:
- Aliases (`/api/reference/aliases`) for category resolution.
- Conversions (`/api/reference/conversions`) when raw units differ from canonical units.
- FX rates (`/api/reference/fx`) when raw currency differs from the base.
- Contacts (`/api/contacts`) for people-domain tasks.

### 3. Deduplication

For each logical ID that appears in more than one snapshot, discard the non-certified occurrence and keep the certified one. Count the discarded rows as duplicates. A "logical ID" is the unique business key in the collection schema (transaction ID, event ID, charge ID, etc.); if the schema does not define one, treat every row as distinct.

### 4. Classification

Classify every retained logical record. The exact buckets differ by domain but follow this pattern:

| Bucket | Rule |
|---|---|
| **Valid** | Passes all quality checks. Category resolves to exactly one canonical type, numeric fields are present and in range. |
| **Mismatch** | The expected category (from a source field) differs from the recognized canonical category from aliases. The record is valid, enters normalized totals, but is an exception. |
| **Unrecognized** | The alias/category field has no mapping in the reference tables. Quarantined. |
| **Ambiguous** | The alias/category field maps to more than one canonical category. Quarantined. |
| **Invalid** | A required numeric field is missing, nonpositive when positive is required, or outside the domain's valid range. Quarantined. |

For people/contact domains, add:
- **Quarantine (unusable contact)**: the source row has no usable email AND no usable phone after reconciliation.
- **Active/Inactive**: determined by the record status field. Only ACTIVE entities are eligible for dispatch/readiness.

### 5. Normalized totals

Sum only valid records (including mismatches that are otherwise valid). Exclude all quarantined records (unrecognized, ambiguous, invalid, and unusable contacts).

Apply conversions: `canonical_value = raw_value * conversion_factor` from `/api/reference/conversions`. Apply FX: `usd_value = raw_value * fx_rate` from `/api/reference/fx`.

Round all computed numeric totals to 2 decimal places unless the answer template specifies a different precision.

### 6. Canonical entity resolution (people/contact domains)

When records from multiple source systems represent the same person:

**a) Clustering** - Group rows that share the same entity. For partner onboarding and field-service roster, the case scope supplies seed/anchor row IDs (every nth row) that kick off each cluster. Include every source row that belongs to the same person.

**b) Survivor selection** - Within each cluster, choose the master ID from the highest-precedence source system. Source precedence chains are domain-specific:
- Partner onboarding: Compliance Master > CRM > Partner Portal.
- Field-service roster: HR Directory > Dispatch > Identity Registry.

If a cluster contains rows from only one source, the survivor is the highest-ID row from that source.

**c) Field-level precedence** - For each canonical field (name, email, phone, city, depot/region, consent, status), take the value from the highest-precedence source system that provides a usable, non-null value for that field. Document which source supplied each canonical field.

**d) Member row IDs** - The deduplicated, lexicographically sorted list of all source row IDs that belong to the cluster.

**e) Resolution outcome** - `FIELD_LEVEL_PRECEDENCE_APPLIED` when the cluster spans multiple sources. `SINGLE_SOURCE` when all rows come from one source. `CONTESTED_NO_AUTOMERGE` when identifier watchlist rows conflict with other identifiers. `NO_USABLE_CONTACT` when no usable channel exists.

### 7. Control-code assignment

Control codes are opaque labels (e.g., `IC-25`, `OR-60`, `FP-55`, `RB-42`, `SB-61`, `LD-72`, `MS-47`, `HR-74`). The task never defines what each code means; you infer the correct one from the data.

**How to determine a code:**

For every record that needs a code, inspect:
- Which snapshot the record came from (certified vs provisional)
- Which source system the record originated from (CRM, Compliance Master, Partner Portal, HR Directory, Dispatch, Identity Registry)
- The record's classification (valid/clean, mismatch, quarantined, duplicate, singleton, clustered)
- The record's role in the reconciliation (focus cluster, anchored control case, quarantine, readiness partition, inactive exclusion, reference row, source-retention row, ledger-routing row)

Then read `/api/source-snapshots` metadata and `/api/reference/aliases` (or other reference endpoints). These reference tables contain mappings from business IDs to reference-category codes. Look for patterns: different source systems produce different provenance codes; different classifications produce different disposition codes. Assign each record the code that matches its characteristics.

Always use only the allowed enum values listed in the answer template for each code family.

**Code families by domain:**

| Family | Values | Used in |
|---|---|---|
| Identity (`IC-`) | IC-25, IC-40, IC-70, IC-90 | People-domain focus decisions, quarantines, policy controls |
| Outreach (`OR-`) | OR-15, OR-35, OR-60, OR-80 | People-domain readiness, quarantines, inactive exclusions, policy controls |
| Field provenance (`FP-`) | FP-20, FP-55, FP-75 | People-domain focus decisions, quarantines, policy controls |
| Reference policy (`RB-`) | RB-17, RB-42, RB-83 | Fuel, freight alias reference decisions |
| Source basis (`SB-`) | SB-24, SB-61, SB-79 | Fuel, freight transaction source decisions |
| Ledger disposition (`LD-`) | LD-14, LD-31, LD-53, LD-72, LD-88 | Fuel, freight ledger-routing decisions |
| Maintenance source (`MS-`) | MS-12, MS-47, MS-86 | Maintenance event decisions |
| History route (`HR-`) | HR-19, HR-33, HR-74 | Maintenance event decisions |

### 8. Certification decision

Count the quarantine/exception rate using the metric defined in the case scope. For contact-domain tasks, compute `quarantine_rate = quarantine_rows / canonical_entities`. Compare against thresholds:

- If rate <= `pass_max_quarantine_rate` -> PASS
- Else if rate <= `pass_with_exceptions_max_quarantine_rate` -> PASS_WITH_EXCEPTIONS
- Else -> HOLD

Map status to action using `status_action_map` from the case scope. The standard mapping is PASS -> RELEASE, PASS_WITH_EXCEPTIONS -> REVIEW_EXCEPTIONS, HOLD -> BLOCK_AND_REMEDIATE.

For audit-style tasks (fuel, freight, maintenance), use the same PASS / PASS_WITH_EXCEPTIONS / HOLD pattern based on the exception rate relative to the overall valid count.

### 9. Output

Return a single JSON object. Match the `answer_template.json` schema exactly. Requirements that always apply:

- Every required key must be present with the exact type and constraints.
- Arrays must be sorted as directed: lexicographically ascending unless the template says otherwise.
- Use only stable IDs from the public data or the case scope.
- Do not wrap the JSON in Markdown code fences. Output raw JSON only.

## Domain reference

### Fuel purchases

- Table: fuel transaction records keyed by `transaction_id`.
- Canonical categories: UNLEADED, PREMIUM_UNLEADED, DIESEL, BIODIESEL, ELECTRIC_CHARGE. Resolved via `/api/reference/aliases` mapping merchant fuel-type aliases.
- Volume: convert to liters (L). Spend: convert to base currency (USD).
- Quarantine: unrecognized alias, ambiguous alias, nonpositive quantity.
- Mismatch: merchant's claimed fuel category != recognized canonical category.
- Exception: any mismatch or quarantine on the same logical transaction.
- Merchant ranking: top N by exception_count descending, merchant_id ascending for ties.

### Freight charges

- Table: freight charge records keyed by `charge_id`.
- Canonical categories: STANDARD, EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED. Resolved via `/api/reference/aliases` mapping carrier class aliases.
- Weight: convert to kilograms (KG). Distance: convert to kilometers (KM). Spend: convert to USD.
- Quarantine: unrecognized alias, ambiguous alias, invalid weight (<= 0), invalid distance (<= 0).
- Mismatch: expected service class != recognized canonical service class.
- Carrier ranking: top N by mismatch_spend_usd descending, carrier_id ascending for ties.

### Maintenance events

- Table: maintenance event records keyed by `event_id`.
- Authoritative snapshot: the one marked CERTIFIED in snapshot metadata.
- Issues: missing timestamp, invalid timestamp (outside business period), invalid odometer (<= 0 or regression), negative labor hours, extreme labor hours (above domain threshold), odometer regression (odometer decreases from one event to the next for the same asset).
- Corrected distance: sum across assets of (last reliable odometer minus first reliable odometer) using only events without odometer issues.
- Asset risk ranking: by rejected_event_count descending, then regression_event_count descending, then asset_id ascending.

### Field-service roster

- Source systems: HR Directory, Dispatch, Identity Registry.
- Precedence: HR Directory > Dispatch > Identity Registry.
- Dispatchable: ACTIVE, consent GRANTED, and has usable email or phone.
- Identifier watchlist: a watchlist case is contested when its anchor row is in a cluster where at least one other source system row has a different identifier.
- Depot: the `region` field in the public data.

### Partner onboarding

- Source systems: CRM, Compliance Master, Partner Portal.
- Precedence: Compliance Master > CRM > Partner Portal.
- Quarantine: no usable email AND no usable phone.
- Readiness eligibility: ACTIVE and at least one usable channel (email or phone).
- Channel readiness: a channel is ready when consent is GRANTED.
- Readiness partition counts are mutually exclusive per entity.

## Pagination

When a query response includes `next_offset` or `next_page`, continue fetching. For SQL with LIMIT/OFFSET, increment offset by the limit for each subsequent page. For cursor-based pagination, pass the cursor value in the next request. Collect all rows before proceeding.

## Precision rules

- All currency, volume, weight, and distance totals: round to 2 decimal places.
- Rates and ratios: round to 4 decimal places (0.xxxx).
- All integer counts: exact.
- Phone: strip every non-digit character. Keep as a string.
- Email: trim whitespace, normalize to NFKC, convert to lowercase.
- Names: preserve Unicode as-is (do not strip diacritics or decompose).
