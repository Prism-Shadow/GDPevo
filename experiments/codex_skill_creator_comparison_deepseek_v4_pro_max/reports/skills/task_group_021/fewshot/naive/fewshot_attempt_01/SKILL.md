---
name: asteria-data-quality-hub
description: Reconcile overlapping source records, detect data-quality issues, assign internal control codes, and produce certification decisions using the Asteria Fleet Data Quality Hub REST API. Covers snapshot reconciliation, canonical entity resolution, contact readiness, fuel/freight/maintenance audit, and JSON answer construction for Asteria business domains.
---

# Asteria Fleet Data Quality Hub Solver

Use this skill when a task asks you to reconcile records from the Asteria Fleet
Data Quality Hub, produce canonical entity results, audit transactions, assign
internal control codes, and return a structured JSON answer that follows an
answer template.

## Core Workflow

Follow this sequence for every Asteria hub task. Do not skip steps.

### Step 1 -- Read the inputs

Locate and read:

1. `prompt.txt` -- the task brief with collection, cutoff, and required outputs.
2. `payloads/case_scope.json` -- business parameters: collection ID, cutoff
   time, focus entities, decision-panel IDs, certification thresholds, and
   ranking rules.
3. `payloads/answer_template.json` -- the JSON schema and required keys. The
   final output must match this structure exactly (same key names, same
   ordering, same enum values, same array lengths).
4. `environment_access.md` -- base URL (`<TASK_ENV_BASE_URL>`), auth token,
   and allowed endpoints. Replace the placeholder in the prompt with the
   actual base URL before making any API call.

### Step 2 -- Discover the collection

Call these endpoints before fetching any data:

1. `GET /api/catalog/collections` -- list available collections. Confirm the
   requested `collection_id` exists.
2. `GET /api/catalog/schema` -- inspect the schema for the target collection.
   Note field names, types, and which fields are indexed or nullable.
3. `GET /api/source-snapshots` -- list snapshots for the collection. Each
   snapshot has a stable ID and a status (e.g. `CERTIFIED`, `PROVISIONAL`).
   The `CERTIFIED` snapshot is the authoritative source; when the same logical
   entity appears in multiple snapshots, retain the certified occurrence.

If the task references reference endpoints (`/api/reference/aliases`,
`/api/reference/conversions`, `/api/reference/fx`), call those now and store
the lookup tables for later use.

### Step 3 -- Fetch and page the data

Retrieve the primary data endpoint for the task domain:

| Task domain | Primary data endpoint |
|---|---|
| Contact / onboarding / roster | `GET /api/contacts` |
| Fuel transactions | `GET /api/transactions/fuel` |
| Freight charges | `GET /api/transactions/freight` |
| Maintenance events | `GET /api/maintenance/events` |

These endpoints may return paginated results. Use the pagination parameters
(`limit`, `offset`, or cursor) provided by the API response. Page through
every available record until the response indicates no more data. Do not
stop partway.

When the task requires SQL-level filtering (e.g., by asset IDs, date ranges,
or specific row criteria), use `POST /api/query` with the auth token shown in
`environment_access.md`. Send a JSON body with a `query` field containing the
SQL. Only query the collection tables documented in the schema; do not guess
table or column names.

### Step 4 -- Reconcile overlapping sources

Apply these rules to every raw record:

**Snapshot precedence**: When the same logical entity ID (event ID, charge ID,
transaction ID) appears in both a `CERTIFIED` and a `PROVISIONAL` snapshot,
keep the certified occurrence and discard the provisional one. Count the
discarded occurrence as a duplicate (`duplicate_raw_count`).

**Multi-source entity resolution (contacts/people)**: When multiple raw rows
from different source systems (e.g., HR Directory, Dispatch, Identity
Registry, CRM, Compliance Master, Partner Portal) refer to the same real-world
entity, merge them into one canonical entity. Use these rules:
- Entities are the same person when they share a stable identifier or when
  deterministic name+email or name+phone matching links them.
- When fields disagree across source systems, apply the precedence table
  below.
- The survivor/master row is the highest-precedence source-system row within
  the cluster. When multiple rows share the same top-precedence source, use
  the row with the lowest lexicographic ID.

**Field-level precedence** for contact/people tasks:

| Field | Source priority (highest first) |
|---|---|
| Name | HR Directory |
| Email | Identity Registry |
| Phone | Identity Registry |
| City | Compliance Master |
| Depot / region | HR Directory |
| Consent status | Identity Registry |
| Record status | HR Directory |

When a higher-precedence source has a non-null, non-empty value, use it. Fall
back through the priority chain until a usable value is found.

**Cross-snapshot duplicate resolution** for transaction/event tasks: When the
same logical ID appears in both certified and provisional snapshots, create a
duplicate-group entry listing both snapshot IDs and the retained snapshot.

### Step 5 -- Classify data-quality issues

Apply these quality checks. Each record can have at most one terminal
quarantine reason; check reasons in the order shown.

**Contact records**:
- *Quarantine*: No usable email AND no usable phone after canonical
  resolution. A usable email is non-null, contains `@`, and is not empty. A
  usable phone has at least one digit.
- *Inactive*: Record status is `INACTIVE` in its canonical source.

**Fuel transactions**:
- *Quarantine (unrecognized)*: The transaction description cannot be resolved
  to exactly one recognized fuel category. Count zero-match cases as
  `unrecognized_count` and multi-match cases as `ambiguous_count` separately.
- *Quarantine (invalid quantity)*: Quantity is null, zero, or negative.
- *Category mismatch*: The expected fuel category differs from the recognized
  category (computed by mapping the description through alias/conversion
  tables). This is not a quarantine; mismatched transactions still enter
  normalized totals.
- *Exception*: A logical transaction that has a category mismatch OR is
  quarantined.

**Freight charges**:
- *Quarantine (unrecognized alias)*: The service alias maps to zero recognized
  service classes.
- *Quarantine (ambiguous alias)*: The service alias maps to more than one
  recognized service class.
- *Quarantine (invalid weight)*: Billed weight is null, zero, or negative.
- *Quarantine (invalid distance)*: Distance is null, zero, or negative.
- *Class mismatch*: The expected service class differs from the recognized
  class. Mismatches are not quarantined and enter normalized totals.
- *Exception*: A charge is a valid class mismatch OR is quarantined.

**Maintenance events**:
- *Invalid (missing timestamp)*: Event timestamp is null.
- *Invalid (invalid timestamp)*: Event timestamp cannot be parsed or is
  outside the business period.
- *Invalid (invalid odometer)*: Odometer reading is null, negative, or exceeds
  a reasonable upper bound.
- *Invalid (negative labor)*: Labor hours are strictly negative.
- *Invalid (extreme labor)*: Labor hours exceed a reasonable threshold (e.g.,
  24 hours).
- *Odometer regression*: For a given asset, when events are ordered by
  timestamp, a later event has a strictly lower odometer reading than an
  earlier valid event. Regression events are not invalid (they still
  contribute to the valid event count) but are reported separately.

### Step 6 -- Compute normalized totals

Exclude quarantined records from all normalized totals. Include valid
mismatches (category/class mismatches that are not quarantined).

**Rounding**: All normalized monetary, volume, weight, and distance values are
rounded to exactly 2 decimal places. Use standard rounding (round half up).

**Unit conversions**: Apply conversions from `/api/reference/conversions` when
the raw data uses a unit different from the canonical unit declared in
`case_scope.json`. For monetary values in non-USD currencies, apply the FX
rates from `/api/reference/fx` as of the cutoff date.

### Step 7 -- Compute rankings

When the task requires ranked lists (top merchants, top carriers, top assets):

- Apply the ranking sort key from `case_scope.json`.
- Break ties with the declared tie-breakers.
- Always produce exactly the requested limit count (e.g., 5 merchants, 5
  carriers). Do not produce fewer than the limit unless fewer exist.

### Step 8 -- Assign control codes

Control codes are compact opaque labels that encode Asteria's internal
assessment of identity, outreach, field provenance, reference policy, source
retention, ledger routing, maintenance source, or history routing. See
[references/control_codes.md](references/control_codes.md) for the complete
reference.

Assign codes by reading the data characteristics of the relevant rows,
never by guessing. The answer template's `enum` constraints tell you exactly
which code families apply to this task. Each family has 3-5 valid values;
select one per decision entity.

**General assignment principles**:
- The same collection and snapshot context tends to produce consistent codes
  for similar data patterns.
- A cluster formed from multiple source systems typically gets a different
  identity code than a single-source cluster.
- Quarantined entities typically receive a distinct code combination from
  active, usable entities.
- Anchored control cases often share codes with the focus clusters they relate
  to, but not always; examine the seed rows directly.
- For policy/decision panels (reference, source, ledger), infer the code from
  the reconciled record's characteristics: which snapshot it came from,
  whether it was mismatched, quarantined, or clean.

### Step 9 -- Compute readiness and certification

**Contact readiness**: An entity is *readiness-eligible* when it is active AND
has at least one usable email or phone. Each eligible entity falls into
exactly one readiness partition:
- `both`: usable email AND usable phone, consent is granted
- `email_only`: usable email only, consent is granted
- `phone_only`: usable phone only, consent is granted
- `not_ready`: usable channel(s) exist but consent is NOT granted

**Readiness eligibility count**: Count of active entities with at least one
usable channel (regardless of consent). This is the denominator for
readiness partitions; it excludes inactive and quarantine entities.

**Certification thresholds**: Apply the gating rules from `case_scope.json`:
- Compute `quarantine_rate = quarantine_count / canonical_entity_count`
  (rounded to 4 decimal places for contact tasks).
- Compare against the thresholds (`pass_max_quarantine_rate`,
  `pass_with_exceptions_max_quarantine_rate`).
- For maintenance tasks, any odometer regression may gate to HOLD.

**Status/action mapping** (consistent across all Asteria tasks):
- `PASS` -> `RELEASE`
- `PASS_WITH_EXCEPTIONS` -> `REVIEW_EXCEPTIONS`
- `HOLD` -> `BLOCK_AND_REMEDIATE`
The task-specific field name for this varies (`certification_status`,
`reconciliation_status`, `release_decision`, `close_status`); use the key
from the answer template.

### Step 10 -- Assemble and return the answer

1. Fill every required key from the answer template.
2. Sort every array as specified by the template or accompanying ordering
   rules (default: lexicographic ascending).
3. Use only the enum values and patterns declared in the schema.
4. Return pure JSON. No markdown fences, no commentary, no trailing text.

## Domain-Specific Guidance

### Fuel and Freight Audit

The reference and alias endpoints are critical. Call them early:
- `GET /api/reference/aliases` returns the mapping from raw description/alias
  text to canonical categories/service classes.
- `GET /api/reference/conversions` provides unit-to-unit conversion factors.
- `GET /api/reference/fx` provides currency-to-USD rates.

A transaction/charge whose description resolves to exactly one canonical
category is *recognized*. Zero matches is *unrecognized*. More than one match
is *ambiguous*. Both unrecognized and ambiguous are quarantined.

### Maintenance Integrity

The maintenance endpoint likely returns data from two snapshots (certified and
provisional). The total raw count is the sum of rows across both snapshots.
After deduplication, the authoritative set is the certified snapshot's rows
plus any provisional-only rows.

For corrected distance: Sum across assets of (last reliable odometer reading
minus first reliable odometer reading) for the reconstructed Q1 history. Skip
invalid events entirely. Regression events are included but their odometer
values are not used for the min/max computation.

### Contact and Roster

The canonical email must be trimmed and NFKC-normalized to lowercase. The
canonical phone must be digits only. The canonical city preserves original
casing.

When the scope says `ALL_COLLECTION_ROWS`, process every row from the
collection. Do not filter by any source-system or status field.

## API Reference

All endpoints are prefixed with the base URL from `environment_access.md`.

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/health` | GET | None | Connectivity check |
| `/api/catalog/collections` | GET | None | List available collections |
| `/api/catalog/schema` | GET | None | Schema for collections |
| `/api/contacts` | GET | None | Contact/people records |
| `/api/transactions/fuel` | GET | None | Fuel purchase records |
| `/api/transactions/freight` | GET | None | Freight charge records |
| `/api/maintenance/events` | GET | None | Maintenance event records |
| `/api/reference/aliases` | GET | None | Description-to-category mapping |
| `/api/reference/conversions` | GET | None | Unit conversion factors |
| `/api/reference/fx` | GET | None | FX rates |
| `/api/source-snapshots` | GET | None | Snapshot metadata |
| `/api/query` | POST | Bearer token | Read-only SQL queries |

The read-only SQL query endpoint accepts:

```json
{"query": "SELECT ... FROM ... WHERE ..."}
```

Use the token from `environment_access.md` in the `Authorization: Bearer
<token>` header. Only query tables listed in the schema; do not attempt
INSERT, UPDATE, DELETE, DROP, or schema-modifying statements.

## Related Files

- [references/control_codes.md](references/control_codes.md) -- complete
  reference for every control code family, its values, and assignment
  patterns.
- [references/quality_patterns.md](references/quality_patterns.md) --
  detailed data-quality classification rules, quarantine conditions, and
  computation formulas.
