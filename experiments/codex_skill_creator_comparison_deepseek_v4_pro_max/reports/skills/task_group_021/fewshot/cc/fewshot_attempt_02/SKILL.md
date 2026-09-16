---
name: asteria-fleet-dq-hub
description: Reconcile and certify fleet data-quality audits using the Asteria Fleet Data Quality Hub. Use this skill whenever the user mentions Asteria, Fleet Data Quality Hub, data reconciliation, fleet audits, cargo/fuel/freight/maintenance/contact/roster certification, partner onboarding, carrier accrual, fuel ledger, field-service roster, or any task that references an Asteria API with collections, snapshots, and an answer template. Even if the task is phrased generically, use this skill when the user points at a read-only API with catalog, schema, source-snapshots, and query endpoints.
---

# Asteria Fleet Data Quality Hub Reconciliation

Work through every fleet audit task using the same reusable pipeline: discover
the data landscape, load and reconcile records across overlapping sources,
assign internal control codes, and produce a JSON answer matching the supplied
answer template exactly.

## Core Workflow

Execute these phases in order; each phase depends on the previous one.

### Phase 1 — Read the case scope

Start by reading two files the task always provides:
- `case_scope.json` — collection ID, cutoff, focus items, decision panel IDs, thresholds
- `answer_template.json` — the output contract (JSON Schema or field-contract doc)

Extract exactly these items from the case scope and hold them in memory:

| Field | Purpose |
|---|---|
| `collection_id` | Which collection to query |
| `cutoff_at` / `business_cutoff` / `as_of` | Temporal boundary for records |
| `business_period` (if present) | Additional time window for scoping |
| `focus_*` arrays | Which entities/assets/clusters need individual reports |
| `*_decision_ids` arrays | Which public IDs need control-code panels |
| `status_thresholds` / `certification_gate` | How to map quality metrics to PASS/HOLD |
| `status_action_map` (if present) | Explicit mapping; otherwise infer from standard rules |
| `*_ranking_limit` | How many ranked items to return |

### Phase 2 — Discover the data landscape

Use the HTTP API at `<TASK_ENV_BASE_URL>`. The `environment_access.md` file
provides the base URL and authentication. All endpoints are read-only GET or
POST.

Execute these calls and keep the full responses for the rest of the task:

1. `GET /api/catalog/collections` — Find the target collection by
   `collection_id`. Record its `source_systems` and any `snapshot_policy`.

2. `GET /api/catalog/schema?collection_id=<id>` — Learn field names, types,
   and which fields represent timestamps, amounts, categories, and identifiers.

3. `GET /api/source-snapshots?collection_id=<id>` — List every snapshot. Each
   snapshot has a `snapshot_id`, a `status` (CERTIFIED, PROVISIONAL, STALE), a
   `row_count`, and a `loaded_at` timestamp.

4. Determine the **authoritative snapshot**:
   - If exactly one snapshot has status CERTIFIED, it is authoritative.
   - If multiple are CERTIFIED, pick the one with the latest `loaded_at`.
   - If no CERTIFIED exists, pick the PROVISIONAL with the latest `loaded_at`.
   - Record its `snapshot_id` as `authoritative_snapshot_id`.

### Phase 3 — Load all records

The primary data endpoint for a collection is a direct GET on
`/api/<collection_kind>/<collection_id>` or paginated via `POST /api/query`.
The task prompt and catalog response tell you which collection kind to use.

**Pagination**: Collections are often larger than a single response page. Use
`POST /api/query` for paginated retrieval:

```json
{
  "collection_kind": "<kind>",
  "collection_id": "<id>",
  "snapshot_ids": ["<snapshot_id>", ...],
  "limit": 500,
  "offset": 0
}
```

Loop with increasing `offset` until fewer than `limit` rows return or the
response is empty. Collect all rows into a single working set.

**Always load all snapshots** from `/api/source-snapshots`. You need the full
multi-snapshot picture to detect duplicates and assign source-basis codes.
Tag each row with its source `snapshot_id` as you accumulate.

### Phase 4 — Reconcile records

#### 4a. Row-level deduplication

When the same logical record (same primary ID) appears in multiple snapshots:

- Count every physical row as `raw_row_count`.
- A logical record is a distinct primary ID (`transaction_id`, `event_id`,
  `charge_id`, or the row's own stable identifier like `PAR-C*`, `FIE-C*`).
- `logical_count` = distinct primary IDs across all snapshots.
- `duplicate_raw_count` = `raw_row_count` - `logical_count`.

For each logical record with duplicates, retain the occurrence from the
**authoritative snapshot**. When the task asks for `retained_snapshot_id`,
report the authoritative snapshot ID.

For contact-oriented tasks: the primary ID is the row identifier. Clustering
into canonical people uses the hub's `cluster_id` field — look for it in the
schema or `/api/contacts` response. A cluster with multiple member rows is a
**duplicate cluster**.

#### 4b. Validation and quarantine

Validate every logical record against these rules:

- **Missing or unparseable timestamp**: Reject if the primary timestamp is null,
  empty, or cannot be parsed as ISO-8601.
- **Invalid timestamp**: Reject if after the cutoff or outside the business period.
- **Negative or zero quantity**: Reject if a physical measure (volume_l,
  weight_kg, distance_km, odometer_km, labor_hours) is null, zero, or negative.
- **Invalid range**: Reject if a value exceeds reasonable bounds (extreme_labor
  check: labor_hours well beyond the expected distribution).
- **Unresolvable category**: A description/alias mapping to zero or more than
  one canonical category.

Records failing validation go into the **quarantine set**. They are excluded
from normalized totals but still contribute to counts like `raw_row_count`,
`logical_count`, `quarantine_rate`, and exception rankings.

#### 4c. Category/class recognition

For fuel tasks: Map free-text `description` to canonical fuel types. The answer
template lists valid types: `BIODIESEL`, `DIESEL`, `ELECTRIC_CHARGE`,
`PREMIUM_UNLEADED`, `UNLEADED`. A description with no match is `unrecognized`;
a description matching multiple types is `ambiguous`.

For freight tasks: Use `GET /api/reference/aliases?collection_id=<id>`. Each
`alias_id` maps to a canonical `service_class` (`EXPRESS`, `HAZMAT`, `OVERSIZE`,
`REFRIGERATED`, `STANDARD`). No mapping → `unrecognized_alias`. Multiple
mappings for the same alias → `ambiguous_alias`.

#### 4d. Contact-specific reconciliation

For contact/roster tasks:

1. **Survivor selection**: Within each cluster, pick the survivor row by source
   precedence. For partner onboarding: Compliance Master > Partner Portal > CRM.
   For field service: HR Directory > Identity Registry > Dispatch. Within equal
   source precedence, prefer the highest lexicographic row ID.

2. **Canonical field selection**: Apply source-system precedence per field. Use
   the value from the highest-precedence source that has a non-null, valid
   value for that field. Fall through to lower-precedence sources.

3. **Quarantine for contacts**: A row is quarantined when it has no usable email
   AND no usable phone. "Usable" means non-null, non-empty, and well-formed.

4. **Readiness**: An entity is eligibility-eligible when ACTIVE AND has at least
   one usable contact channel. Among eligible entities:
   - `both` = usable email AND usable phone
   - `email_only` = usable email only
   - `phone_only` = usable phone only
   - `not_ready` = active but no usable channel
   - Inactive entities are excluded from readiness entirely.

#### 4e. Odometer regression (maintenance only)

1. Sort valid events by `(asset_id, event_timestamp)`.
2. For each asset, track the last valid odometer. If a later event has a lower
   odometer, flag it as a regression.
3. Regression events stay in `valid_event_count` but are reported separately in
   `regression_event_ids` and `regression_asset_ids`.
4. Corrected total distance: for each asset, compute
   `last_reliable_odometer - first_reliable_odometer`, skipping regressed
   readings.

### Phase 5 — Compute normalized totals

For financial audits (fuel, freight):

1. Apply unit conversions via `GET /api/reference/conversions` to bring all
   measures into the canonical unit (L, KG, KM).
2. Apply FX rates via `GET /api/reference/fx` to convert spend into the base
   currency (always USD in training data).
3. Sum across all valid, non-quarantined logical records.
4. Group by recognized category/class and sum within each group.
5. Round all numeric results to 2 decimal places unless the template specifies
   otherwise.

### Phase 6 — Focus-item reports

For every item in `focus_assets`, `focus_clusters`, `focus_people`, etc.,
produce the per-item breakdown required by the answer template:

- Count logical, valid, mismatch, quarantine, and exception records for that
  item.
- Report canonical values for that focus item (survivor row, email, phone, city
  for contacts; volume/spend for assets).
- Follow the exact field contract from the answer template.

### Phase 7 — Assign control codes

The hub's internal code systems encode policy decisions about each record.
Allowed code values are always listed in the answer template's enum fields.

See the detailed reference at [code_systems.md](references/code_systems.md) for
the complete decision tables. Here is the summary:

- **Identity codes (IC-*)**: IC-25 (single-source, uncontested), IC-40
  (quarantined), IC-70 (multi-source field-merged), IC-90 (multi-source
  corroborated).
- **Outreach codes (OR-*)**: OR-15 (inactive), OR-35 (dispatchable), OR-60
  (no usable contact), OR-80 (consent-blocked).
- **Field-provenance codes (FP-*)**: FP-20 (single-source), FP-55 (multi-source
  merged), FP-75 (quarantined).
- **Source-basis codes (SB-*)**: SB-24 (certified only), SB-61 (both, certified
  retained), SB-79 (provisional only).
- **Ledger-disposition codes (LD-*)**: LD-14 (unrecognized category), LD-31
  (valid, category mismatch), LD-53 (matched, certified-only), LD-72 (matched,
  provisional-only), LD-88 (ambiguous category).
- **Reference-policy codes (RB-*)**: RB-17 (clean one-to-one alias mapping),
  RB-42 (contested alias mapping, recognized but non-straightforward), RB-83
  (unrecognized alias, no reference entry).
- **Maintenance-source codes (MS-*)**: MS-12 (provisional only), MS-47
  (certified only), MS-86 (multi-snapshot).
- **History-route codes (HR-*)**: HR-19 (odometer regression), HR-33 (clean,
  single-source), HR-74 (clean, multi-source).

**Code assignment priority**: Quarantine overrides all. Mismatch/unrecognized
category overrides source-basis. Source multiplicity determines source-basis
before category-match determines ledger-disposition.

### Phase 8 — Certification decision

Map the computed quality metrics to a certification status using the thresholds
from the case scope.

**Standard thresholds** (when `status_thresholds` is present):
```
quarantine_rate == 0.0  →  PASS  →  RELEASE
0.0 < quarantine_rate <= pass_with_exceptions_max  →  PASS_WITH_EXCEPTIONS  →  REVIEW_EXCEPTIONS
quarantine_rate > pass_with_exceptions_max  →  HOLD  →  BLOCK_AND_REMEDIATE
```

**Gate-based thresholds** (when `certification_gate` is present):
The gate specifies a single condition and consequence. For example, if
`odometer_regression_status: HOLD`, any odometer regression triggers HOLD.

If the case scope provides an explicit `status_action_map`, use it. Otherwise
use the standard mapping:
- `PASS` → `RELEASE`
- `PASS_WITH_EXCEPTIONS` → `REVIEW_EXCEPTIONS`
- `HOLD` → `BLOCK_AND_REMEDIATE`

Match the answer template's exact field names for the certification object.
Different tasks use different names: `action` (fuel), `routing` (freight),
`next_action` (contacts). Copy the template's names verbatim.

### Phase 9 — Produce the JSON answer

1. Re-read the answer template. Note every required field, its type, any `enum`
   constraints, `minItems`/`maxItems`, `pattern` validations, and ordering rules
   (often in `x-ordering_rules` or `description` text).

2. **Ordering rules** (apply to every list unless contradicted by the template):
   - String ID lists: lexicographically ascending.
   - Ranked lists: by the specified sort keys.
   - Region/depot lists: lexicographically ascending by region/depot code.
   - Focus items: by their ID, ascending.
   - Decision panels: by the decision ID, ascending.

3. **Numeric precision**:
   - Counts: exact integers.
   - Rates: round to the decimal places specified in the schema (typically 4 for
     rates, 2 for amounts). Round half-up.

4. Produce a single JSON object. Do not wrap in Markdown. Do not include
   commentary. Use the exact field names from the answer template.

## Reference files

- [api_endpoints.md](references/api_endpoints.md) — Full API reference with
  request and response shapes
- [code_systems.md](references/code_systems.md) — Complete code assignment
  tables with decision trees

## Scripts

- [query.py](scripts/query.py) — Paginated query helper for `/api/query`
