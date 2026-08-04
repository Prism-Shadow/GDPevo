 # Asteria Fleet Data Quality Hub — Reusable Solving Patterns

 ## Environment

 The task environment provides a read-only data hub at a base URL supplied as `<TASK_ENV_BASE_URL>` or `GDPEVO_ENV_BASE_URL`. Runtime access details (exact base URL, query credential) arrive separately in an `environment_access.md` payload. Expect these interfaces:

 - `GET /api/catalog/collections` — list available collections with row-count estimates, source systems, and date ranges.
 - `GET /api/catalog/schema` — discover the logical views (`v_contacts`, `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`, `v_fx_rates`, `v_reference_aliases`, `v_source_snapshots`, `v_unit_conversions`) and their field names, types, and meanings.
 - `POST /api/query` — run read-only SQL (`SELECT` / `WITH`) over the public views. Required header: `Authorization: Bearer <credential>`. The body is `{"query": "<SQL string>"}`. Results are paginated; check the `truncated` flag and use `LIMIT`/`OFFSET` or targeted `WHERE` clauses to stay under limits.
 - `GET /api/contacts`, `GET /api/transactions/fuel`, `GET /api/transactions/freight`, `GET /api/maintenance/events`, `GET /api/reference/aliases`, `GET /api/reference/conversions`, `GET /api/reference/fx`, `GET /api/source-snapshots` — direct GET endpoints also exist and may surface pre-joined or filtered views.

 Always begin by calling `/api/catalog/collections` and `/api/catalog/schema` to understand which views and fields are available for the collection named in the case scope.

 ## Snapshot Model

 Every collection is built from one or more source snapshots. Query `v_source_snapshots` filtered by `collection_id` to list them.

 - **CERTIFIED** snapshots come from the authoritative source system and carry the highest trust.
 - **PROVISIONAL** snapshots come from secondary feeds and may add coverage but are less authoritative.
 - Each snapshot has a `business_cutoff` (the as-of date for the data it contains), a `created_at` timestamp, a `row_count`, and a `snapshot_status`.

 **Deduplication rule**: When the same logical record (same `transaction_id`, `charge_id`, `event_id`, or matching `source_record_id`) appears in multiple snapshots, retain the CERTIFIED occurrence and discard the PROVISIONAL duplicate. Count the discarded raw rows separately. The authoritative snapshot ID is the CERTIFIED one.

 ## Reference Data

 ### Aliases (`v_reference_aliases`)

 Aliases map free-text descriptions to canonical categories. Key fields:

 - `domain` — groups aliases by business area (`fuel`, `freight`, etc.).
 - `alias_text` — the text token to match in source descriptions.
 - `canonical_value` — the standardised category.
 - `valid_from` / `valid_to` — business-date range; the alias only applies when the case cutoff falls within this window.
 - `reference_status` — `ACTIVE`, `INACTIVE`, or `PROVISIONAL`.

 **Matching rules**:
 1. Lowercase both the description and alias text before comparing.
 2. Use **substring matching**: the alias text must appear anywhere inside the description.
 3. Exclude aliases whose `reference_status` is `INACTIVE`.
 4. Exclude aliases whose `valid_from` is after the business cutoff, or whose `valid_to` is before the business cutoff.
 5. When multiple aliases match the same description, apply **subsumption filtering**: if one matching alias's text is entirely contained within another matching alias's text, remove the shorter one (it is subsumed). This prevents false ambiguity when, for example, both `"diesel"` and `"bio diesel"` match a description — `"diesel"` is subsumed inside `"bio diesel"` and is dropped.
 6. After filtering, if all remaining aliases point to the same canonical value, the description is **recognised** as that category. If they point to different canonical values, the description is **ambiguous** (cannot be assigned to exactly one category). If no aliases remain, the description is **unrecognised**.

 ### Unit Conversions (`v_unit_conversions`)

 Each row defines a multiplier from a source unit to a canonical unit for a given measurement `kind` (`volume`, `distance`, `weight`, `odometer`). Apply: `canonical_value = source_value × factor`. Common factors:

 - Volume: `US_GAL → L` ≈ 3.785411784, `IMP_GAL → L` = 4.54609
 - Distance/odometer: `MI → KM` = 1.609344
 - Weight: `LB → KG` ≈ 0.45359237

 ### FX Rates (`v_fx_rates`)

 Use only rows with `rate_status = 'CERTIFIED'`. Look up the rate by `(rate_date, currency)` where `rate_date` matches the transaction's business date (the date portion of `purchased_at`, `service_date`, etc.). Convert: `amount_usd = amount × usd_per_unit`. USD amounts pass through unchanged.

 ## Contact / People Tasks

 Contact collections merge rows from multiple source systems (e.g. Partner Portal, CRM, Compliance Master; or HR Directory, Dispatch, Identity Registry). Each source system typically contributes one snapshot.

 ### Grouping & Deduplication

 1. Parse `source_record_id` to find the entity key. Common formats: `PA-####-#`, `CR-####-#`, `CO-####-#` where the numeric middle segment is the shared entity ID. Rows that share the same entity key across sources belong to the same canonical person.
 2. Rows with `source_record_id` starting with `NC-` are **quarantine candidates** — they have no usable email or phone. Collect all such row IDs into the quarantine list.
 3. Rows whose `master_hint` is `SHARED-HELPDESK` all share the same phone number; treat them as **one canonical entity** (a shared-service desk), regardless of differing names or emails.
 4. Rows with a `master_hint` like `NOISY-##` appear once each; treat each as a **single-source canonical entity**.
 5. All remaining rows are **singletons** — one canonical entity per row.

 ### Canonical Field Selection

 For each canonical entity (cluster of 1–N source rows):

 - **Survivor row**: prefer the row from the CERTIFIED source with `verified_flag = 1` and `GRANTED` consent. Among CERTIFIED sources, prefer Partner Portal / HR Directory.
 - **Canonical email**: from the survivor row, trimmed and lowercased (Unicode NFKC).
 - **Canonical phone**: digits only, stripped from the survivor row's phone. If the survivor has a country-code prefix and another CERTIFIED row has a cleaner version, prefer the cleaner digits.
 - **Canonical city**: when two CERTIFIED sources agree on a city, use that value. When they disagree, prefer Partner Portal / HR Directory.
 - **City source system**: the name of the source system that supplied the chosen city (`Partner Portal`, `HR Directory`, `Compliance Master`, `Identity Registry`, or `CRM` / `Dispatch`).

 ### Usability & Quarantine

 A row has **usable email** when its email field is non-empty, not whitespace-only, not a sentinel (`none`, `null`, `n/a`, `N/A`, `NULL`), and contains `@`. A row has **usable phone** when its phone field yields at least one digit after stripping non-numeric characters and is not a recognised sentinel. A row with **neither** usable email nor usable phone is quarantined.

 ### Channel Readiness

 An entity is **readiness-eligible** when at least one of its rows is `ACTIVE` and that row has a usable email or phone. Among readiness-eligible entities:

 - Count how many have `GRANTED` consent **and** both usable email and phone → `both`.
 - Count how many have `GRANTED` consent **and** usable email only → `email_only`.
 - Count how many have `GRANTED` consent **and** usable phone only → `phone_only`.
 - All other eligible entities (non-granted consent, inactive, or no usable channel) → `not_ready`.

 ### Region Rollup

 For every canonical entity, pick its region from the survivor (or the best available source). Count canonical entities per region and report all six expected regions (`BE`, `England`, `MD`, `ON`, `SG`, `TX`) in lexicographic order, including regions with zero entities.

 ### Control Codes (Contact Domain)

 The answer contract will list the allowed code values. Infer them from the data:

 - **identity_code** (`IC-25`, `IC-40`, `IC-70`, `IC-90`): reflects how many source systems agree on the person's identity fields (email, phone). Higher codes mean stronger consensus.
 - **outreach_code** (`OR-15`, `OR-35`, `OR-60`, `OR-80`): reflects the canonical consent status — `GRANTED`, `PENDING`, `DENIED`, or `UNKNOWN`/no-contact.
 - **field_provenance_code** (`FP-20`, `FP-55`, `FP-75`): reflects which source system supplied the chosen city value.

 Apply the correct code to every focus-cluster decision, anchored control case, quarantine result, readiness partition, and inactive exclusion as specified by the answer contract.

 ### Certification Decision

 Compute `quarantine_rate = quarantine_row_count / canonical_entity_count`. Compare against the thresholds in the case scope's `status_thresholds`:

 - `quarantine_rate ≤ pass_max_quarantine_rate` → `PASS` / `RELEASE`
 - `quarantine_rate ≤ pass_with_exceptions_max_quarantine_rate` → `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`
 - Otherwise → `HOLD` / `BLOCK_AND_REMEDIATE`

 ## Fuel / Freight Transaction Tasks

 ### Data Preparation

 1. Deduplicate by `transaction_id` / `charge_id`, preferring CERTIFIED over PROVISIONAL.
 2. Flag rows with non-positive quantity/weight/distance (≤ 0) as **invalid** (quarantined, excluded from normalised totals).
 3. Match `purchased_description` / `description` against the relevant alias domain using the alias matching rules above.
 4. Descriptions that yield zero matches → **unrecognised**. Descriptions that yield multiple canonical values → **ambiguous**. Both are quarantined.
 5. Compare `expected_fuel_type` / `expected_service_class` against the recognised canonical category. Differences are **mismatches** — they stay in normalised totals but under their recognised category.

 ### Normalised Totals

 Compute totals **only from valid (non-quarantined) transactions**:

 - Convert every quantity to the canonical unit using `v_unit_conversions`.
 - Convert every amount to the base currency (USD) using CERTIFIED FX rates.
 - Sum by recognised fuel type / service class, sorted alphabetically.
 - Round all monetary and volumetric values to 2 decimal places.

 ### Exception Counting

 An **exception** is any logical transaction that is either a category mismatch or quarantined (invalid quantity, unrecognised, or ambiguous). Distinct transactions can only count once even if they qualify under multiple conditions.

 ### Merchant / Carrier Ranking

 Rank by `exception_count` descending, then by `merchant_id` / `carrier_id` ascending (lexicographic). Report the top N as specified in the case scope (typically 5). Include breakdowns of `mismatch_count` and `quarantine_count`.

 ### Focus Assets

 For each requested asset ID:

 - Count logical transactions (valid + quarantined) for that asset.
 - Count valid transactions, mismatches, and quarantined separately.
 - Sum volume and spend from valid transactions only.

 ### Policy / Decision Panels

 The case scope supplies lists of public stable IDs (reference alias IDs, transaction IDs, charge IDs) that need coded decisions. Use the allowed compact code values from the answer contract. Typical code families:

 - **Reference policy codes** (`RB-17`, `RB-42`, `RB-83`): reflect whether the alias is ACTIVE and in-range, PROVISIONAL, or INACTIVE/expired relative to the business cutoff.
 - **Source basis codes** (`SB-24`, `SB-61`, `SB-79`): reflect whether the retained row comes from a CERTIFIED snapshot, a PROVISIONAL snapshot, or has a REVIEW record status.
 - **Ledger disposition / routing codes** (`LD-14`, `LD-31`, `LD-53`, `LD-72`, `LD-88`): reflect the transaction's final state — clean POSTED, category mismatch, invalid quantity, unrecognised description, or REVIEW status.

 Infer the exact code mapping from the intersection of the record's properties and the allowed enum values. Assign one code per decision row; the contract specifies which code families apply to which panel.

 ### Reconciliation / Close Status

 Based on the volume or rate of exceptions relative to the total logical count. Typical thresholds:
 - Low exception rate → `PASS` / `RELEASE`
 - Moderate → `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`
 - High or regression detected → `HOLD` / `BLOCK_AND_REMEDIATE`

 ## Maintenance Event Tasks

 ### Issue Detection

 Scan every retained (deduplicated) event for:

 - **missing_timestamp**: `event_time_raw` is `NULL`.
 - **invalid_odometer**: `odometer_value` is non-positive (≤ 0).
 - **negative_labor**: `labor_hours` is negative.
 - **extreme_labor**: `labor_hours` exceeds 24 (an implausibly long single work order).

 Events with any of these issues are **rejected** (invalid) and excluded from corrected metrics.

 ### Odometer Regression

 For each asset, collect all non-rejected events with valid timestamps and positive odometer readings. Convert odometer to KM (× 1.609344 if unit is `MI`). Sort by `event_time_raw` ascending. An **odometer regression** occurs when a later event has a lower odometer reading than an earlier event for the same asset. Collect both the regression asset IDs and the regression event IDs.

 ### Corrected Distance

 Total distance = sum over every asset of (last reliable odometer − first reliable odometer) in KM, using only assets with at least two reliable events. Round to 2 decimal places.

 ### Asset Risk Ranking

 Rank assets by `rejected_event_count` descending, then `regression_event_count` descending, then `asset_id` ascending. Return the top N.

 ### Event Decision Panel

 For each scoped public event ID, assign:

 - **maintenance_source_code** (`MS-12`, `MS-47`, `MS-86`): reflects which source system or snapshot type the retained event row comes from.
 - **history_route_code** (`HR-19`, `HR-33`, `HR-74`): reflects whether the event is valid, involved in a regression, or rejected.

 ### Certification Gate

 If any odometer regression is detected, the case scope may hard-code a `HOLD` / `BLOCK_AND_REMEDIATE` outcome. Otherwise, base the decision on the proportion of rejected events.

 ## General Output Rules

 - Return **exactly one JSON object** conforming to the supplied answer template / JSON Schema.
 - All stable-ID lists must be sorted lexicographically and deduplicated.
 - All arrays with explicit ordering rules in the contract (e.g. "sorted by cluster_id ascending") must follow those rules exactly.
 - Numeric precision: counts are exact integers; monetary and volumetric values are rounded to 2 decimal places; rates and proportions use 4 decimal places where specified.
 - Do not include commentary, Markdown, or extra whitespace outside the JSON structure.
 - Use only stable IDs that are present in the public data or supplied in the case scope.
