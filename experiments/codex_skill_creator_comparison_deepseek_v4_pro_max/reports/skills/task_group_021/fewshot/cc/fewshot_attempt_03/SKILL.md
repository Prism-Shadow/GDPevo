---
name: asteria-dq-hub
description: Query and audit the Asteria Fleet Data Quality Hub API to reconcile multi-source fleet records, compute quality metrics, assign opaque control codes, and produce certification decisions. Use whenever the user mentions Asteria, fleet data quality, partner onboarding certification, fuel ledger audits, maintenance-log integrity, field-service roster readiness, freight-charge accrual reconciliation, or any task that references a Fleet Data Quality Hub, TASK_ENV_BASE_URL, or environment_access.md with Asteria API endpoints.
---

# Asteria Fleet Data Quality Hub

This skill teaches a systematic nine-phase workflow for auditing and certifying fleet data through the Asteria Fleet Data Quality Hub, a read-only REST API that serves multi-source operational records (contacts, fuel transactions, maintenance events, field-service rosters, freight charges) alongside reference data (aliases, unit conversions, FX rates) and source-snapshot metadata.

## When this skill triggers

The task prompt describes a business audit or certification scenario for Asteria Fleet Operations and references:

- A `<TASK_ENV_BASE_URL>` placeholder whose actual URL comes from `environment_access.md`
- A `case_scope.json` payload with collection, cutoff, focus entities, and decision panels
- An `answer_template.json` that defines the exact JSON output contract

When you see these signals, read [references/api-endpoints.md](references/api-endpoints.md) for the full endpoint catalog, then follow the nine-phase workflow below.

## Phase 1: Orient

Read all three input files before touching the network:

1. **Prompt** — identifies the business domain (partner onboarding, fuel ledger, maintenance integrity, roster readiness, or freight accrual) and what certification decision is needed
2. **case_scope.json** — contains `collection_id`, `business_cutoff` / `cutoff_at` / `as_of`, focus entities (clusters, assets, people, charge IDs), decision panels, thresholds, and ranking rules
3. **answer_template.json** — the exact JSON schema your output must conform to; note every required field, allowed enum values, sort order rules, and numeric precision (counts are integers, rates to 4 decimal places, physical/financial measures to 2 decimal places)

From `environment_access.md`, extract the `base_url` and note which endpoints are allowed. Substitute `<TASK_ENV_BASE_URL>` with the actual base URL in all API calls.

## Phase 2: Discover the hub

Call the API in this order to understand the data landscape:

1. `GET {base_url}/api/catalog/collections` — confirm the collection exists and note its metadata
2. `GET {base_url}/api/catalog/schema` — learn field names, types, and constraints for every collection; this tells you what fields are filterable in `/api/query`
3. `GET {base_url}/api/source-snapshots` — list snapshots for the target collection; each has a `snapshot_id`, `status` (CERTIFIED, PROVISIONAL, or STALE), and `row_count`

**Snapshot authority rule**: When the same logical record appears in multiple snapshots, the CERTIFIED snapshot takes precedence over PROVISIONAL, which takes precedence over STALE. Almost every task uses `{collection_id}-certified` as the authoritative snapshot. Record this ID — you will need it in the audit summary.

## Phase 3: Retrieve domain data

Use the collection-specific GET endpoint to pull all records. These endpoints may return paginated results — check for a `next` field or cursor in the first response and follow it until exhausted.

| Collection kind | Endpoint |
|---|---|
| Contacts (partner onboarding, field service) | `GET {base_url}/api/contacts` |
| Fuel transactions | `GET {base_url}/api/transactions/fuel` |
| Maintenance events | `GET {base_url}/api/maintenance/events` |
| Freight charges | `GET {base_url}/api/transactions/freight` |

When you need filtered access (by collection, snapshot, date range, asset ID), use:

```
POST {base_url}/api/query
```

The query endpoint accepts a JSON body with `collection`, `filter`, and `snapshot` fields. Use the catalog schema to determine valid field names for filter expressions.

## Phase 4: Retrieve reference data

Pull only the reference tables your domain needs:

- `GET {base_url}/api/reference/aliases` — maps free-text `description` to canonical categories (fuel types or service classes). A description mapping to exactly one category is recognized; zero categories is unrecognized; multiple categories is ambiguous. Use for fuel type matching and service class resolution.
- `GET {base_url}/api/reference/conversions` — unit conversion factors (gallons to liters, miles to km, pounds to kg). Apply conversions before summing totals.
- `GET {base_url}/api/reference/fx` — exchange rates by date and currency pair. To normalize spend to USD, multiply source `cost` by the rate for `{currency}→USD` on (or nearest before) the transaction date.

Fuel and freight tasks use all three. Contact and maintenance tasks typically only need aliases.

## Phase 5: Reconcile overlapping sources

Raw rows from the data endpoint may include duplicates where the same logical record appears in multiple snapshots:

1. Group all raw rows by logical identifier (row ID, transaction ID, event ID, charge ID)
2. For each group with multiple occurrences, retain the row from the CERTIFIED snapshot; discard rows from PROVISIONAL or STALE snapshots
3. Compute: `raw_row_count` = total rows received, `logical_count` = distinct logical IDs, `duplicate_raw_count` = `raw_row_count` minus `logical_count`
4. When the answer template requires a `duplicate_groups` array, emit one object per multi-occurrence logical ID listing all `snapshot_ids` (sorted lexicographically) and identifying the `retained_snapshot_id`

Some templates distinguish `raw_row_count` (all rows received) from `scoped_raw_row_count` (rows within a business period after source reconciliation). Read the template's field definitions carefully.

## Phase 6: Apply domain-specific quality rules

Filter records by the business cutoff first — records with timestamps after the cutoff are out of scope. Then apply the quality rules for your domain. See [references/quality-rules.md](references/quality-rules.md) for the complete rule tables.

The core distinction:

- **Quarantined**: excluded from all normalized totals (spend, volume, weight, distance, readiness aggregates). A record with any quarantine condition is quarantined, even if it also has a mismatch.
- **Mismatched (valid)**: still enters normalized totals, but is flagged in mismatch lists.
- **Invalid**: excluded from both validity counts and totals. These are records with fundamentally unusable data (null/missing required fields, impossible values).

A single logical record that matches multiple quarantine conditions counts as exactly one quarantine. After applying quality rules you will have counts for: valid records, mismatches, and quarantines, plus sorted ID lists for each.

## Phase 7: Compute aggregates and rankings

**Totals**: Sum physical measures and spend across valid records only. Apply unit conversions from `/api/reference/conversions` before summing, and FX conversions from `/api/reference/fx`. Round to 2 decimal places. Do not include quarantined records.

**Per-category rollups**: Group valid records by canonical fuel type or service class. The answer template specifies the exact set of categories — include every one, even if a category has zero valid records. Sort categories ascending by name.

**Per-entity rollups**: For focus assets, carriers, or merchants, compute per-entity counts (logical, valid, mismatch, quarantine, exception) and totals (volume, spend). Sort as specified by the case scope — typically by exception count descending with ties broken by ID ascending.

**Distance metrics (maintenance)**: For each asset, sort valid events by timestamp ascending. Track the running maximum odometer. If a later event's odometer is at least the running max, update the max; if it regresses, that event is flagged but skipped for distance accumulation. Total distance = sum over assets of (final_max minus first_valid_odometer).

**Exception counts**: An exception is a distinct logical record that is either a mismatch or quarantined. Count each record at most once. For rankings, `exception_count` = `mismatch_count` + `quarantine_count` at the entity level.

## Phase 8: Assign control codes

The hub uses opaque three-character family codes with numeric suffixes (e.g. IC-25, FP-55, OR-35, RB-42, SB-61, LD-31, MS-47, HR-33). These represent internal Asteria policy decisions. The task materials intentionally omit their definitions — you must infer the correct code for each decision by examining the underlying data rows.

### Code family table

| Prefix | Family | Domain context |
|---|---|---|
| IC | Identity | Contact deduplication — who a person is |
| OR | Outreach | Contact readiness — whether and how to reach someone |
| FP | Field Provenance | Which source system contributed each canonical field |
| RB | Reference Basis | Alias mapping quality — recognized vs unrecognized vs ambiguous |
| SB | Source Basis | Snapshot origin and data quality flags for retained records |
| LD | Ledger Disposition | Whether a charge is clean, mismatched, or quarantined; subclass of quarantine reason |
| MS | Maintenance Source | Data quality profile for a maintenance event (missing timestamps, invalid odometers, labor anomalies) |
| HR | History Route | How a maintenance event fits into asset history — clean, regressed, or with quality concerns |

### How to infer codes

For each scoped decision, examine the underlying data rows:

1. Note the **source system** for each field (if multiple sources contributed, field-level precedence was applied)
2. Note the **snapshot origin** (certified vs provisional)
3. Note the **data quality characteristics** (quarantined, mismatched, or clean)
4. Identify whether the entity is a **single source** match or a **multi-source merge**

Within each code family, codes with **higher numeric suffixes** generally indicate more complex or degraded situations. When a code family appears in a ranking or partition, every code from that family's enum must be used exactly once — so if the allowed enum has three codes, look for exactly three natural clusters in the data and assign codes accordingly.

Common mapping patterns observed across tasks:

- **IC**: Single-source records get lower suffixes; multi-source merged people get higher suffixes; quarantined contacts get their own code
- **OR**: GRANTED consent gets one code; PENDING gets another; DENIED/UNKNOWN gets another; inactive records get a distinct code
- **FP**: Single-source provenance gets lower suffixes; multi-source blends get higher suffixes; quarantined rows get a distinct code
- **RB**: Exactly-one-match aliases get one code; zero-match (unrecognized) get another; multi-match (ambiguous) get a third
- **SB**: Rows from certified snapshots with no issues get one code; rows with mismatches get another; rows in otherwise special situations get a third
- **LD**: Clean valid charges get one code; mismatches get another; quarantined charges get their own codes based on quarantine reason
- **MS**: Events with no quality issues get one code; events with minor issues get another; events with severe issues get a third
- **HR**: Events in clean history trajectories get one code; events flagged as regressions get another; events with other concerns get a third

Work systematically: group the scoped decisions by their data characteristics, identify the natural clusters, then map each cluster to a distinct allowed code.

## Phase 9: Apply certification thresholds and emit the answer

1. Compute the certification status using the thresholds or gates from `case_scope.json`:
   - For rate-based thresholds (e.g. `pass_max_quarantine_rate: 0.0`, `pass_with_exceptions_max_quarantine_rate: 0.04`), compute the actual rate as a float (quarantine_count / canonical_entity_count or logical_count) rounded to 4 decimal places, then compare
   - For gate-based decisions (e.g. `odometer_regression_status: HOLD`), check if the triggering condition is met and use the pre-mapped status
   - Map the status to the action using the `status_action_map` or equivalent mapping in the case scope

2. Build the JSON output object field by field, exactly matching the answer template's structure, required keys, allowed enum values, and ordering rules.

3. Verify before emitting:
   - Every required key is present
   - Arrays with `minItems = maxItems` have exactly that length
   - All ID lists and arrays are sorted lexicographically ascending unless a different ordering rule is explicitly stated
   - Numeric values use the declared precision: integers for counts, 2 decimal places for physical/financial measures, 4 decimal places for rates
   - Enum fields use only values from the allowed set

4. Output a single JSON object. Do not wrap it in Markdown code fences. Do not include any commentary, preamble, or closing text before or after the JSON.
