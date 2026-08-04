 # Asteria Fleet Data Quality Hub — Audit & Certification Skill

 ## Purpose

 Solve audit, reconciliation, deduplication, and certification tasks against the Asteria Fleet Data Quality Hub. Each task is delivered as a prompt with two companion payloads (`case_scope.json` and `answer_template.json`). The skill covers connecting to the Hub, retrieving evidence, reconciling overlapping sources, applying business rules, coding decisions, and producing a single JSON answer that conforms exactly to the answer contract.

 ---

 ## Task Input Structure

 Every task provides three files:

 | File | Role |
 |---|---|
 | `prompt.txt` | Natural-language description of the work, domain context, and which Hub interfaces are relevant. |
 | `payloads/case_scope.json` | Parameters that scope the work: collection ID, business cutoff, focus items (clusters / assets / people), decision-ID panels, ranking limits, certification thresholds. |
 | `payloads/answer_template.json` | The exact output contract — a JSON Schema or a meta-template describing required keys, enumerations, ordering rules, and numeric precision. |

 **The output must be one JSON object matching the template exactly.** No commentary, no Markdown, no extra keys.

 ---

 ## Hub Connection

 Runtime details are always in `environment_access.md`. The canonical shape is:

 - **Base URL**: `http://task-env:9021` (or the value of `GDPEVO_ENV_BASE_URL` / `<TASK_ENV_BASE_URL>`).
 - **Query auth**: `Authorization: Bearer asteria-read-021`
 - **Content-Type** for POST: `application/json`

 ### Available GET Endpoints

 | Endpoint | Returns |
 |---|---|
 | `/api/catalog/collections` | List of available data collections. |
 | `/api/catalog/schema` | Column definitions for collections. |
 | `/api/contacts` | Person/partner contact records (HR Directory, Dispatch, Identity Registry sources). |
 | `/api/transactions/fuel` | Fuel purchase transactions (by snapshot). |
 | `/api/transactions/freight` | Freight charge transactions (by snapshot). |
 | `/api/maintenance/events` | Maintenance event log records. |
 | `/api/reference/aliases` | Fuel and freight alias/category reference tables. |
 | `/api/reference/conversions` | Unit-of-measure conversion factors. |
 | `/api/reference/fx` | Foreign-exchange rates. |
 | `/api/source-snapshots` | Snapshot metadata: IDs, timestamps, collection association, status labels (CERTIFIED / PROVISIONAL / STALE). |

 ### Query Endpoint

 ```
 POST /api/query
 Content-Type: application/json
 Authorization: Bearer asteria-read-021
 {"query": "<SELECT or WITH statement over public views>"}
 ```

 The underlying collections may be larger than a single response page. Use SQL `LIMIT` / `OFFSET` or cursor-based pagination as needed to retrieve all rows. Public views include at minimum `v_source_snapshots` and the published collection views.

 **Query rules**:
 - Always filter by the authoritative snapshot ID and the business cutoff.
 - Use `SELECT *` only when the schema is known; prefer explicit column lists from `/api/catalog/schema`.
 - For large collections, paginate with `ORDER BY` a stable key and `LIMIT`/`OFFSET`.

 ---

 ## Reconciliation Workflow

 The same five-phase pipeline applies across all task domains:

 ### Phase 1 — Source Selection

 1. Call `GET /api/source-snapshots` and filter to the task's `collection_id`.
 2. Identify the **authoritative snapshot**: the snapshot whose `recorded_at ≤ cutoff` and whose status is `CERTIFIED`. If no CERTIFIED snapshot exists, fall back to the most recent `PROVISIONAL` snapshot. A `STALE` snapshot should never be authoritative.
 3. Record the snapshot ID and its row count — these belong in the output's source-decision or audit-summary block.

 ### Phase 2 — Data Retrieval

 1. Fetch all rows from the authoritative snapshot using the domain-specific GET endpoint or `/api/query`.
 2. When multiple snapshots overlap (duplicate detection), also fetch rows from sibling snapshots that share the same logical-key space.
 3. Fetch all supporting reference data: aliases, conversions, FX rates, and schema definitions.

 ### Phase 3 — Merge & Deduplicate

 **For contact/people tasks**: Cluster rows that refer to the same entity across sources (HR Directory, Dispatch, Identity Registry, CRM, Compliance Master, Partner Portal). Match on normalized identifiers (email, phone digits, name). For each cluster:
 - Select a **survivor row** (master record) using source precedence declared in the prompt or scope.
 - Record all **member row IDs**.
 - Resolve canonical values for each field using field-level source precedence.

 **For transaction tasks**: Identify logical transactions that appear in more than one snapshot. For each duplicate group:
 - Count the raw occurrences.
 - Retain the occurrence from the most authoritative snapshot (CERTIFIED over PROVISIONAL; if equal status, prefer the later `recorded_at`).
 - Do not double-count duplicates in normalized totals.

 ### Phase 4 — Classify & Validate

 **Category classification**: Map each record's raw category/description to a canonical category using reference aliases. Records that match zero canonical categories are **unrecognized**; records that match more than one are **ambiguous**.

 **Mismatch detection**: Compare the record's declared category against the mapped canonical category. A difference is a **category mismatch** (or **service-class mismatch** for freight).

 **Quarantine conditions** (varies by domain):
 - Contact: no usable email AND no usable phone, or all channels fail validation.
 - Fuel: invalid quantity (≤ 0 or null), unrecognized category, ambiguous category, or unreconcilable description.
 - Freight: unresolvable service class, missing or invalid physical measures (weight ≤ 0, distance ≤ 0), or invalid charge amount.
 - Maintenance: odometer regression, invalid timestamp, unreconcilable event source.

 **Quarantined records are excluded from normalized totals.**

 ### Phase 5 — Compute, Rank & Certify

 1. **Normalize**: Convert all monetary amounts to the base currency using FX rates; convert all physical quantities to canonical units using conversion factors. Round to the precision declared in the answer template (default: 2 decimal places).
 2. **Roll up**: Aggregate by category, region, depot, or service class as required.
 3. **Rank**: Order entities (merchants, carriers, assets) by exception metrics as specified in the case scope. Break ties using the declared tie-break fields.
 4. **Certify**: Apply the certification thresholds from the case scope (`status_thresholds`, `certification_gate`) to determine PASS / PASS_WITH_EXCEPTIONS / HOLD, then map to the action in `status_action_map`.

 ---

 ## Control Code Taxonomy

 Every task requires assigning opaque internal codes to specific items. Codes are enumerated in the answer template; their meanings are inferred from record evidence, not supplied in task materials. Use the following decision logic:

 ### Identity Codes (IC)

 | Code | When to assign |
 |---|---|
 | `IC-25` | Entity resolved from a single source with high-confidence match. |
 | `IC-40` | Entity resolved from multiple sources with consistent attributes. |
 | `IC-70` | Entity resolved from multiple sources with conflicting attributes; field-level precedence applied. |
 | `IC-90` | Entity is contested; identifier watchlist case remains unresolved. |

 ### Outreach / Contact-Readiness Codes (OR)

 | Code | When to assign |
 |---|---|
 | `OR-15` | All channels usable and consent granted. |
 | `OR-35` | At least one channel usable; consent pending. |
 | `OR-60` | At least one channel usable; consent denied. |
 | `OR-80` | No usable channel regardless of consent. |

 ### Field Provenance Codes (FP)

 | Code | When to assign |
 |---|---|
 | `FP-20` | All fields sourced from a single system of record. |
 | `FP-55` | Fields sourced from multiple systems; survivor row carries the majority. |
 | `FP-75` | Fields sourced from multiple systems; significant field-level conflict required precedence rules. |

 ### Reference Policy Codes (RB)

 | Code | When to assign |
 |---|---|
 | `RB-17` | Alias maps cleanly to exactly one canonical category. |
 | `RB-42` | Alias is deprecated or retired; superseded by a newer reference. |
 | `RB-83` | Alias is ambiguous or maps to a non-standard category. |

 ### Source Basis Codes (SB)

 | Code | When to assign |
 |---|---|
 | `SB-24` | Record appears only in the authoritative (CERTIFIED) snapshot. |
 | `SB-61` | Record appears in multiple snapshots; authoritative copy retained. |
 | `SB-79` | Record appears only in a non-authoritative (PROVISIONAL) snapshot. |

 ### Ledger Disposition Codes (LD)

 | Code | When to assign |
 |---|---|
 | `LD-14` | Transaction is valid, recognized, and enters the ledger cleanly. |
 | `LD-31` | Transaction has a category mismatch but is otherwise valid; enters ledger with a flag. |
 | `LD-53` | Transaction is unrecognized; routed for manual review. |
 | `LD-72` | Transaction is quarantined (invalid quantity, ambiguous category, or other quality block). |
 | `LD-88` | Transaction is a duplicate and excluded from the ledger. |

 ### Maintenance Source Codes (MS)

 | Code | When to assign |
 |---|---|
 | `MS-12` | Event sourced from telematics / onboard system. |
 | `MS-47` | Event sourced from workshop / third-party service provider. |
 | `MS-86` | Event sourced from manual entry or correction log. |

 ### History Route Codes (HR)

 | Code | When to assign |
 |---|---|
 | `HR-19` | Event passes all validation checks; included in corrected history. |
 | `HR-33` | Event corrected (e.g., odometer adjusted) but retained. |
 | `HR-74` | Event rejected; excluded from corrected history. |

 ---

 ## Answer Template Formats

 Two template formats are in use:

 ### Format A — JSON Schema (train_001, 002, 003, 005)

 Standard JSON Schema (draft 2020-12) with:
 - `$schema`, `additionalProperties: false`
 - `properties` defining each required output key
 - `required` arrays at every level
 - `enum` constraints for controlled vocabularies
 - `pattern` constraints for ID formats
 - `minItems` / `maxItems` / `uniqueItems` for arrays
 - Ordering rules in `description` fields

 ### Format B — Meta-Template (train_004)

 A lighter contract with:
 - `template_version`, `output_type`
 - `required_top_level_keys`: flat list of required output keys
 - `field_contract`: per-key definitions with type, required sub-keys, field descriptions, and ordering rules
 - `numeric_precision`: global precision rule
 - No `$schema` or `additionalProperties`

 **Regardless of format**, the output object must:
 - Include every required key.
 - Include no extra keys.
 - Use only values from the allowed enumerations.
 - Follow the declared ordering (lexicographic ascending unless stated otherwise).
 - Match the declared numeric precision (2 decimal places default; integers where specified).

 ---

 ## Domain-Specific Rules

 ### Contact / People (train_001, train_004)

 **Sources**: HR Directory, Dispatch, Identity Registry, CRM, Compliance Master, Partner Portal.

 **Entity resolution precedence** (when sources disagree on a field):
 1. Name: HR Directory > Dispatch > Identity Registry > Partner Portal > CRM > Compliance Master
 2. Email / Phone: HR Directory > Dispatch > Identity Registry
 3. Region / Depot: HR Directory > Dispatch > Identity Registry
 4. Consent: Dispatch > HR Directory > Identity Registry
 5. Record status: Identity Registry > HR Directory > Dispatch

 **Readiness**: An entity is readiness-eligible when `record_status = ACTIVE` AND at least one usable channel (email or phone). A channel is ready when `consent = GRANTED`. Count entities as:
 - `both`: active, consent granted, both email and phone usable.
 - `email_only`: active, consent granted, only email usable.
 - `phone_only`: active, consent granted, only phone usable.
 - `not_ready`: either inactive, consent not granted, or no usable channel.

 **Quarantine**: A row with no usable email AND no usable phone (or all channels fail normalization).

 **Watchlist**: When an identifier case lists a source row anchor that also appears in a focus cluster, the cluster is **contested** if the watchlist evidence conflicts with the cluster resolution. Report contested case IDs separately.

 ### Fuel Transactions (train_002)

 **Canonical categories**: BIODIESEL, DIESEL, ELECTRIC_CHARGE, PREMIUM_UNLEADED, UNLEADED.

 **Classification**: Match each transaction's `description` field against `/api/reference/aliases`. A description that maps to exactly one canonical fuel type is **recognized**. Descriptions mapping to zero types are **unrecognized**; descriptions mapping to more than one are **ambiguous**.

 **Mismatch**: The transaction's declared `fuel_type` differs from the alias-mapped canonical category.

 **Duplicate**: Same logical transaction (same `transaction_id` or equivalent business key) appears in multiple raw source rows from different snapshots.

 **Invalid quantity**: `volume_l` ≤ 0 or null.

 **Quarantine**: Invalid quantity, unrecognized category, or ambiguous category.

 ### Maintenance Events (train_003)

 **Validation rules**:
 - Odometer regression: an event's odometer reading is lower than the previous event for the same asset.
 - Invalid timestamp: event timestamp outside the business period or null.
 - Unreconcilable source: event has no source-system attribution.

 **Duplicate**: Same logical event appears in multiple raw rows.

 **Corrected metrics**: Reconstruct the event history excluding rejected events. Compute distance traveled per asset as the last reliable odometer minus the first reliable odometer. Sum across assets for the total.

 **Asset risk ranking**: Count rejected events and regression events per asset. Rank by rejected_event_count DESC, then regression_event_count DESC, then asset_id ASC.

 ### Freight Charges (train_005)

 **Canonical service classes**: EXPRESS, HAZMAT, OVERSIZE, REFRIGERATED, STANDARD.

 **Classification**: Same alias-matching pattern as fuel. For freight, `service_class` is the mapping target.

 **Mismatch**: Declared `service_class` differs from alias-mapped canonical class.

 **Quarantine**: Unresolvable service class, invalid weight (≤ 0), invalid distance (≤ 0), or charge amount issues.

 **Duplicate**: Same `charge_id` appearing in multiple snapshots.

 **Carrier ranking**: Order carriers by `mismatch_spend_usd` (USD from valid charges with class mismatch) descending, then `carrier_id` ascending. Quarantined charges do not contribute to normalized totals; valid class-mismatch charges do.

 ---

 ## Output Construction Checklist

 Before writing the final JSON, verify:

 1. All required top-level keys from the answer template are present.
 2. No extra keys exist at any level.
 3. Every `enum` field uses an allowed value only.
 4. Arrays have the correct cardinality (minItems / maxItems / length).
 5. Arrays are sorted as declared (lexicographic ascending unless otherwise noted).
 6. Array elements are `uniqueItems` where required.
 7. All ID patterns match the `pattern` regex constraints.
 8. Numeric fields use the declared precision (typically 2 decimal places; counts are integers).
 9. All scoped decision IDs from the case scope are represented exactly once.
 10. Quarantine row/charge IDs are deduplicated and sorted.
 11. Normalized totals exclude quarantined records.
 12. Certification status and action are derived from thresholds in the case scope.
 13. The output is raw JSON with no surrounding text, fences, or Markdown.

 ---

 ## Common Pitfalls

 - **Forgetting to filter by snapshot**: Always restrict queries to the authoritative snapshot ID. Querying the raw collection without a snapshot filter returns data from all snapshots.
 - **Double-counting duplicates**: When a logical record appears in multiple snapshots, count it once. Use the retained occurrence.
 - **Mixing up ordering**: The default sort is lexicographic ascending unless the template or scope explicitly overrides it. Ranking sorts are always stated explicitly.
 - **Including quarantined records in totals**: Quarantined rows do not contribute to normalized volume, spend, or count totals. They do contribute to raw row counts and quarantine lists.
 - **Schema vs meta-template confusion**: Format A uses `properties` and `required`; Format B uses `required_top_level_keys` and `field_contract`. Read the template structure before writing output.
 - **Case sensitivity**: All enum values, codes, and stable IDs are case-sensitive. Use the exact casing from the template.
 - **Pagination**: When a GET endpoint returns paginated results, follow `Link` headers or use `/api/query` with `LIMIT`/`OFFSET` until all rows are retrieved.

 ---

 ## Supporting Files

 - `skill/reference/control_codes.json` — Machine-readable control-code taxonomy with decision rules.
 - `skill/reference/api_catalog.json` — Endpoint reference with request/response shapes.
