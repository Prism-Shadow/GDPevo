 # Asteria Fleet Data Quality Hub Reconciliation Skill

 Use this skill when a task requires auditing, reconciling, certifying, or normalizing data from the Asteria Fleet Data Quality Hub. The hub is a read-only HTTP API that exposes fleet-domain records (contacts, fuel purchases, freight charges, maintenance events, and reference data) across multiple source snapshots, with an authenticated SQL query interface for ad-hoc exploration.

 ## Prerequisites

 The task will supply these files (or equivalents):

 - `payloads/case_scope.json` — the operational parameters: collection ID, cutoff timestamp, focus entities, thresholds, decision-panel selections, ranking limits.
 - `payloads/answer_template.json` — the JSON Schema contract the output must conform to. Every property, `required` list, `enum` constraint, and ordering rule is mandatory.
 - `environment_access.md` — contains `GDPEVO_ENV_BASE_URL` (the hub's base URL) and the fixed `Authorization: Bearer asteria-read-021` header for query and data endpoints.

 Read all three files before issuing any API call.

 ## Hub Endpoints

 All endpoints are GET unless noted. Append paths to `GDPEVO_ENV_BASE_URL`. The auth header is always `Authorization: Bearer asteria-read-021`.

 ### Discovery

 | Endpoint | Returns |
 |---|---|
 | `/api/catalog/collections` | List of available collections, each with `collection_id`, snapshot IDs, row counts, and cutoff metadata. |
 | `/api/catalog/schema` | Column names and types for every view/table in the catalog. |
 | `/api/source-snapshots` | Snapshot metadata: `snapshot_id`, `collection_id`, `source_system`, `is_authoritative`, `ingested_at`, row counts. |

 ### Domain Data

 | Endpoint | Returns |
 |---|---|
 | `/api/contacts` | Contact records: `row_id`, `collection_id`, `snapshot_id`, name fields, email, phone, city, region, consent flags, active status, cluster assignments, source system. |
 | `/api/transactions/fuel` | Fuel purchase records: `row_id`, `transaction_id`, `collection_id`, `snapshot_id`, `asset_id`, `merchant_id`, description, expected and actual fuel categories, quantity, unit, unit price, currency, timestamp. |
 | `/api/transactions/freight` | Freight charge records: `row_id`, `charge_id`, `collection_id`, `snapshot_id`, `carrier_id`, `service_class` (actual and expected), billed weight, distance, spend, currency, timestamp. |
 | `/api/maintenance/events` | Maintenance event records: `row_id`, `event_id`, `collection_id`, `snapshot_id`, `asset_id`, `work_order_id`, description, event timestamp, source system. |

 ### Reference Data

 | Endpoint | Returns |
 |---|---|
 | `/api/reference/aliases` | Alias mappings: `alias_id`, `canonical_value`, `raw_value`, `domain`, `collection_id`, `snapshot_id`, `source_system`. |
 | `/api/reference/conversions` | Unit conversion factors: from unit, to unit, factor. |
 | `/api/reference/fx` | FX rates: from currency, to currency, rate, effective date. |

 ### Ad-Hoc SQL

 **POST** `/api/query`
 - `Content-Type: application/json`
 - `Authorization: Bearer asteria-read-021`
 - Body: `{"query": "<SQL SELECT or WITH statement>"}`

 Use this for cross-reference joins, aggregation, and any exploration beyond single-entity GET endpoints. Public views follow the naming convention `v_<entity>` (e.g., `v_contacts`, `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`, `v_source_snapshots`, `v_reference_aliases`, `v_reference_conversions`, `v_reference_fx`).

 ## General Workflow

 ### 1. Read the Case Scope

 Extract these parameters from `case_scope.json`:
 - `collection_id` — limits all queries.
 - `cutoff_at` or `business_cutoff` — ISO-8601 UTC; filter all rows to `<=` this timestamp.
 - Focus entity lists (clusters, assets, carriers, aliases, etc.).
 - Decision-panel ID lists (reference, transaction, event, source, ledger).
 - Thresholds and ranking limits.
 - Any `status_action_map` mapping statuses to routing actions.

 ### 2. Discover the Collection

 Call `/api/catalog/collections` and `/api/source-snapshots` to find:
 - Which snapshots belong to the target `collection_id`.
 - Which snapshot is marked authoritative.
 - Snapshot row counts and source systems.

 If multiple snapshots exist for the collection, identify the **authoritative snapshot** (or the one named `<collection_id>-certified`). Rows from non-authoritative snapshots represent duplicates that need deduplication.

 ### 3. Query Domain Data

 Fetch all relevant domain records for the collection using the GET endpoints, filtering by `collection_id`. If the data volume is large, use `/api/query` with `WHERE collection_id = '<id>'` to retrieve subsets.

 ### 4. Reconcile

 Apply the reconciliation patterns in the section below as dictated by the task domain.

 ### 5. Assign Decision Codes

 Assign identity, outreach, field-provenance, reference-basis, source-basis, and ledger-disposition codes as required by the answer contract. See the Code Assignment section.

 ### 6. Produce Output

 Construct a single JSON object matching `payloads/answer_template.json` exactly. Respect all `required`, `additionalProperties: false`, `enum`, `pattern`, `minItems`/`maxItems`, and ordering constraints. Return only the JSON object — no commentary or Markdown.

 ## Reconciliation Patterns

 ### Snapshot Deduplication

 When multiple snapshots cover the same logical entities (same `transaction_id`, `charge_id`, `event_id`, `contact` cluster), only the row from the **authoritative** snapshot is retained. Rows from non-authoritative snapshots are dropped from valid/retained counts but contribute to `raw_row_count` and `duplicate_raw_count`.

 Counts:
 - `raw_row_count` = total rows across all snapshots for the collection.
 - `logical_<entity>_count` = distinct logical IDs across all snapshots.
 - `duplicate_raw_count` = `raw_row_count` − `logical_<entity>_count`.
 - `valid_<entity>_count` = retained (authoritative) rows that pass all quality filters.

 ### Contact Survivor Selection

 For contact reconciliation, contacts are pre-clustered by the hub (cluster assignments are in the contact records). For each focus cluster:
 1. Identify all member `row_id`s within the cluster.
 2. Select the **survivor** (canonical row):
    - Prefer the row with the most non-null fields among {first_name, last_name, email, phone_digits, city, region}.
    - Break ties by choosing the newest `ingested_at`.
    - If still tied, choose the lowest `row_id` lexicographically.
 3. Extract canonical values (email, phone_digits, city) from the survivor.
 4. The `city_source_system` is the `source_system` of the survivor row.

 ### Quarantine Logic

 A row is quarantined when it fails a mandatory quality check:

 **Contacts**: Missing `first_name` or `last_name`, or missing both `email` and `phone_digits`, or `active = false`.

 **Fuel transactions**: Invalid quantity (≤ 0 or null), or the description cannot be mapped to any recognized fuel category (unrecognized), or the description maps to more than one category (ambiguous).

 **Freight charges**: Invalid billed weight or distance (≤ 0 or null), or service class mismatch where the mismatched row also has a data-quality issue.

 **Maintenance events**: Missing `work_order_id` with no recognizable work-order pattern in the description.

 Quarantine rates are computed as `quarantine_count / logical_<entity>_count`.

 ### Category / Service-Class Matching

 For fuel and freight domains, each row carries an `expected_<category>` (from the source system) and an `actual_<category>` (determined by the hub's classification engine). A **mismatch** occurs when expected ≠ actual. Mismatches are tracked separately from quarantines.

 For fuel **descriptions**, map each description text to zero, one, or more recognized fuel categories. Use the reference alias tables to resolve raw descriptions to canonical categories. A description with zero matches is **unrecognized**; with more than one match is **ambiguous**. Both contribute to `unrecognized_transaction_ids` (the union, sorted).

 ### Unit Normalization

 **Volume**: Convert all fuel quantities to the canonical unit (liters) using `/api/reference/conversions`. Look up the conversion factor from the transaction's `unit` to the canonical unit. Multiply: `volume_canonical = quantity × factor`.

 **Currency**: Convert all monetary amounts to the base currency (USD) using `/api/reference/fx`. For each transaction, find the FX rate from the transaction's `currency` to the base currency, effective on or before the transaction date. Multiply: `spend_base = spend × rate`.

 **Weight**: Convert freight billed weight to kilograms using conversion factors.

 **Distance**: Convert freight distance to kilometers using conversion factors.

 ### Aggregation and Ranking

 **Group-by rollups**: Aggregate valid (non-quarantined) rows by the dimension requested in the output schema (fuel type, service class, region, asset, carrier, merchant). Sum counts and numeric measures (volume, spend, weight, distance). Round all monetary and measure values to 2 decimal places.

 **Rankings**: When the output schema requests a top-N ranking, sort by the primary metric descending, then by the entity ID ascending as a tiebreaker. Entity IDs sort lexicographically (standard string order).

 ## Code Assignment

 Codes are opaque alphanumeric identifiers defined by the answer template's `enum` constraints. Assign them based on the data characteristics derived during reconciliation.

 ### Identity Codes (IC-*)

 Assigned to focus-cluster decisions and quarantine results. The code reflects the quality of identity resolution:

 - **IC-25**: Single source, high confidence — all cluster members come from one source system with complete identity fields.
 - **IC-40**: Multi-source, medium confidence — cluster members span multiple source systems; the survivor has complete fields but members disagree on some attributes.
 - **IC-70**: Standard resolution — typical multi-source cluster with minor discrepancies resolved by survivor selection.
 - **IC-90**: Low confidence — cluster has missing fields in all members, or the survivor was chosen from incomplete records.

 Infer the appropriate code by counting the unique source systems in the cluster and checking field completeness of the survivor.

 ### Outreach Codes (OR-*)

 Assigned to focus decisions, anchored control cases, quarantine results, readiness partitions, and inactive exclusions:

 - **OR-15**: Inactive entity — contact is marked inactive and excluded from readiness.
 - **OR-35**: Channel-ready — entity has email and/or phone with consent granted.
 - **OR-60**: Quarantined — entity failed quality checks.
 - **OR-80**: Not ready — entity is active but lacks usable contact channels or consent.

 ### Field Provenance Codes (FP-*)

 Assigned to focus decisions, anchored cases, and quarantine results:

 - **FP-20**: Single authoritative source — the canonical value comes from the authoritative snapshot's source system.
 - **FP-55**: Survivor-selected — the canonical value was chosen by survivor-selection logic from multiple candidate rows.
 - **FP-75**: Multi-source with conflict — the value was reconciled from sources that disagreed.

 ### Reference Basis Codes (RB-*)

 Used for reference/alias reconciliation decisions:

 - **RB-17**: Clean alias — the alias maps to a single consistent canonical value across all snapshots.
 - **RB-42**: Alias with variance — the alias appears in multiple snapshots with different raw values but resolves to the same canonical.
 - **RB-83**: Contested alias — the alias has conflicting canonical mappings across snapshots; retention decision required.

 ### Source Basis Codes (SB-*)

 Used for cross-snapshot source retention decisions:

 - **SB-24**: Certified retained — the charge/event is present in both snapshots; the certified row is retained.
 - **SB-61**: Provisional only — the charge/event appears only in the provisional snapshot; retained from provisional.
 - **SB-79**: Certified only — the charge/event appears only in the certified snapshot; retained from certified.

 ### Ledger Disposition Codes (LD-*)

 Used for freight ledger routing decisions:

 - **LD-14**: Standard domestic — domestic lane, standard service class.
 - **LD-31**: Standard international — international lane, standard service class.
 - **LD-53**: Express domestic — domestic lane, express service.
 - **LD-72**: Special handling — HAZMAT, OVERSIZE, or REFRIGERATED service class.
 - **LD-88**: Exception — quarantined or mismatched charge requiring manual review.

 ### Decision Code Inference

 To determine the correct code for any entity:
 1. Query the entity's full record set from the hub (all snapshots).
 2. Examine the relevant attributes (source systems, field completeness, snapshot membership, service class, lane type).
 3. Match the observed characteristics to the code definitions above.
 4. Select the code whose definition best fits the evidence from the data.

 Always verify that the chosen code exists in the answer template's `enum` for that field.

 ## Output Conventions

 - All monetary values: round to 2 decimal places.
 - All measurement values (liters, kilograms, kilometers): round to 2 decimal places.
 - All rates (quarantine, exception): round to 4 decimal places.
 - ID lists: sorted lexicographically (standard string sort) unless the template specifies another ordering.
 - Ranking arrays: exactly the `minItems`/`maxItems` count, ordered by the primary metric descending, then entity ID ascending.
 - Arrays with `minItems` = `maxItems` (e.g., fuel_type_totals with exactly 5 entries): produce exactly one entry per expected category value, sorted by the category field ascending.
 - `null` and missing fields: never emit `null` for required fields. Omit optional fields entirely when they have no value, unless the template requires them.
 - Timestamps: all in ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).

 ## Error Handling

 - If the hub is unreachable, report the connection error and stop.
 - If a required collection or snapshot is not found, report the missing resource and stop.
 - If a requested entity ID (focus cluster, asset, charge, alias) has no matching records, include it in the output with zero counts or an empty result as appropriate for the schema.
 - If the answer template contains constraints that cannot be satisfied (e.g., a required `enum` value that doesn't match any observed data), use the closest-matching code and note the ambiguity.
