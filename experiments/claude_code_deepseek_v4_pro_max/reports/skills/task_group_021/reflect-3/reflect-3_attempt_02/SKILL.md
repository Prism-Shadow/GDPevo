# Asteria Fleet Data Quality Hub — Audit & Certification Skill

## Overview

Use this skill to process Asteria Fleet data-quality audit and certification tasks. Every task reconciles overlapping source records from a shared read-only data hub, detects data-quality issues, normalises values against reference tables, assigns internal control codes, and returns a single JSON object conforming to a supplied answer contract.

## Step 1 — Discover the collection and its schema

Read the task's `case_scope.json` for the `collection_id` and business cutoff or as-of date. Read `environment_access.md` for the base URL, authorization header, and the list of allowed endpoints.

**Catalog.** Call `GET /api/catalog/collections` to confirm the collection exists and to learn its source systems, approximate row count, and time range.

**Schema.** Call `GET /api/catalog/schema` to list every available logical view and its fields. Match the task domain — contacts, fuel transactions, freight charges, maintenance events — to the correct view (`v_contacts`, `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`, `v_reference_aliases`, `v_unit_conversions`, `v_fx_rates`, `v_source_snapshots`). Study the `meaning` annotations on each field; they describe the business purpose and expose aliases (e.g., `purchased_description` in fuel is the text you match against reference aliases).

## Step 2 — Load source-snapshot metadata

Query `v_source_snapshots` for the target `collection_id`. Each row describes one snapshot: its `source_system`, `snapshot_status` (`CERTIFIED` / `PROVISIONAL` / `STALE`), `business_cutoff`, `row_count`, and `checksum`.

You will use this to:
- Pick the authoritative snapshot (prefer `CERTIFIED` with a `business_cutoff` matching the task's cutoff; when multiple CERTIFIED snapshots exist, use the one from the most-trusted source system named in the task prompt).
- Count authoritative rows and scoped raw rows.
- Resolve overlapping records (same logical ID appearing in multiple snapshots).

## Step 3 — Load reference data

Reference tables supply canonical mappings, unit conversions, and currency rates. Load all of them before processing any transaction data.

**Aliases (`v_reference_aliases`).** Filter by `domain` matching the task family (`'fuel'`, `'freight'`). Each row maps an `alias_text` (a free-text description fragment) to a `canonical_value` (a recognised category such as `DIESEL` or `EXPRESS`). Pay attention to `reference_status` (`ACTIVE`, `INACTIVE`, `PROVISIONAL`) and `valid_from`/`valid_to` dates — only active, in-range aliases apply at the business cutoff.

**Unit conversions (`v_unit_conversions`).** Filter by `kind` (`'volume'`, `'weight'`, `'distance'`, `'odometer'`). Each row gives a `factor` from `from_unit` to `to_unit`. The canonical unit is always the row where `from_unit` equals `to_unit` with a factor of 1.0.

**FX rates (`v_fx_rates`).** Each row gives a `rate_date`, `currency`, `usd_per_unit`, and `rate_status`. Prefer `CERTIFIED` rates for the transaction's service/purchase date; fall back to `PROVISIONAL`. USD transactions have an implicit rate of 1.0.

## Step 4 — Load and deduplicate the primary data

Query the primary view for the target `collection_id`, ordering by the logical ID column and `snapshot_id`. Load every row; the underlying collection may be larger than a single page but the query endpoint returns all matching rows.

**Deduplication.** When the same logical ID (`row_id`, `transaction_id`, `charge_id`, `event_id`) appears in more than one snapshot, retain the occurrence from the authoritative snapshot chosen in Step 2. Record:
- `duplicate_raw_count` — the number of discarded raw occurrences (total raw rows minus one per logical ID).
- For tasks that require duplicate groups: list the logical ID, the set of `snapshot_ids` it appeared in, and the `retained_snapshot_id`.

## Step 5 — Detect and classify issues

Walk every retained logical record and flag problems. A record can carry more than one issue; each issue type is counted independently. The union of all flagged records forms the invalid/quarantine set for that task.

### Contact records

| Issue | Condition |
|---|---|
| No usable contact | Normalised email is empty/`none`/`n/a`/`null` **and** normalised phone digits are empty/`none`/`n/a`/`null`. |
| Inactive record | `record_status` is `INACTIVE` on every source row for the entity. |

Normalise email by trimming, applying NFKC Unicode normalisation, and lowercasing. Normalise phone by stripping every non-digit character.

### Fuel transactions

| Issue | Condition |
|---|---|
| Invalid quantity | `quantity` ≤ 0. |
| Unrecognised description | `purchased_description` contains **no** active alias text (case-insensitive substring match). |
| Ambiguous description | `purchased_description` matches aliases that resolve to **more than one** distinct canonical fuel type. |

When a description is ambiguous, resolve it by picking the **longest** matching `alias_text` (the most specific match). Record the ambiguous count separately from the completely unrecognised count.

### Freight charges

| Issue | Condition |
|---|---|
| Invalid weight | `billed_weight` ≤ 0. |
| Invalid distance | `distance` ≤ 0. |
| Unrecognised alias | `description` contains no active alias text. |
| Ambiguous alias | `description` matches aliases that resolve to more than one canonical service class. |

Apply the same longest-match disambiguation rule as for fuel.

### Maintenance events

| Issue | Condition |
|---|---|
| Missing timestamp | `event_time_raw` is `null` or empty. |
| Invalid timestamp | `event_time_raw` cannot be parsed as ISO-8601, or falls outside the declared business period. |
| Invalid odometer | `odometer_value` is `null` or negative. |
| Negative labour | `labour_hours` < 0. |
| Extreme labour | `labour_hours` > 24. |

**Odometer regression.** After removing all invalid events, group the remaining events by `asset_id`, sort by timestamp ascending, and flag every event whose odometer reading is **lower** than the previous reading for the same asset. Before comparing, convert `MI` readings to `KM` (× 1.609344). Regression events are **not** removed from the valid set; they are reported separately in `corrected_metrics` and contribute to the asset risk ranking.

## Step 6 — Reconcile canonical entities (contacts only)

For contact-family tasks, the source records arrive in groups of three — one row from each source system snapshot. Each group represents the **same** logical person. Build one canonical entity per group:

1. **Survivor selection.** Prefer the source system named in the task prompt as authoritative (typically the one whose snapshot carries the `master_hint`). Within that source, prefer a verified row (`verified_flag` = 1). Fall back to the first row in the group.

2. **Canonical email.** Take from the most authoritative source (`Identity Registry` / `Compliance Master` > `HR Directory` / `Partner Portal` > `Dispatch` / `CRM`). Normalise with NFKC, trim, and lowercase.

3. **Canonical phone.** Same source priority. Strip all non-digit characters; the result is a digit string.

4. **Canonical city.** Majority vote across the source rows. Break ties by preferring the authoritative source.

5. **Canonical consent.** Best-of: `GRANTED` > `DENIED` > `PENDING` > `UNKNOWN`.

6. **Canonical record status.** `ACTIVE` if any source row is `ACTIVE`; otherwise `INACTIVE`.

**Special grouping hints.** Some rows carry a `master_hint` field. A shared hint value (e.g., `SHARED-HELPDESK`) signals that rows across multiple groups belong to the **same** canonical entity and must be merged into one. A `NOISY-` prefix marks a row as carrying unreliable field data; the row still contributes to counts but its hint value may override normal precedence.

## Step 7 — Assign control codes

Every task requires internal Asteria control codes drawn from fixed enums. Derive them from the reconciled data, not from hard-coded mappings.

### Identity codes (`IC-25`, `IC-40`, `IC-70`, `IC-90`)

Compare the normalised `person_or_org_name` values across all source rows in the entity:
- **IC-90** — all names are identical after NFKC normalisation and lowercasing.
- **IC-70** — two distinct normalised forms.
- **IC-40** — three or more distinct normalised forms.
- **IC-25** — reserved; not observed in training.

### Outreach codes (`OR-15`, `OR-35`, `OR-60`, `OR-80`)

Derived from the consent status across the entity's rows:
- **OR-15** — at least one row has `GRANTED` consent.
- **OR-60** — no `GRANTED`, but at least one `DENIED`.
- **OR-35** — no `GRANTED` or `DENIED`, but at least one `PENDING`.
- **OR-80** — all rows have `UNKNOWN` consent.

### Field-provenance codes (`FP-20`, `FP-55`, `FP-75`)

Derived from the `verified_flag` counts:
- **FP-20** — every row in the entity is verified (`verified_flag` = 1).
- **FP-55** — at least one row is verified, but not all.
- **FP-75** — no row is verified.

### Reference-policy codes (`RB-17`, `RB-42`, `RB-83`)

Derived from the alias `reference_status`:
- **RB-17** — `ACTIVE`.
- **RB-42** — `PROVISIONAL`.
- **RB-83** — `INACTIVE` or missing.

### Source-basis codes (`SB-24`, `SB-61`, `SB-79`)

Derived from which snapshot supplied the retained record:
- **SB-24** — the authoritative CERTIFIED snapshot.
- **SB-61** — a PROVISIONAL snapshot.
- **SB-79** — any other snapshot.

### Ledger-disposition codes (`LD-14`, `LD-31`, `LD-53`, `LD-72`, `LD-88`)

Derived from the record's issue status and `record_status`:
- **LD-14** — quarantined (invalid quantity, unrecognised, or ambiguous).
- **LD-53** — valid but has an expected-vs-actual category mismatch.
- **LD-31** — valid, no mismatch, `record_status` is `POSTED` or `BILLED`.
- **LD-72** — valid, no mismatch, `record_status` is `REVIEW`.
- **LD-88** — any other valid record.

### Maintenance-source codes (`MS-12`, `MS-47`, `MS-86`)

Derived from the event's retained snapshot:
- **MS-12** — from the CERTIFIED / Maintenance ERP snapshot.
- **MS-47** — from the PROVISIONAL / Mobile Work Orders snapshot.
- **MS-86** — from any other source.

### History-route codes (`HR-19`, `HR-33`, `HR-74`)

Derived from the event's `event_status`:
- **HR-19** — `COMPLETED` or `CLOSED`.
- **HR-33** — `OPEN`.
- **HR-74** — any other status.

## Step 8 — Compute normalised totals (transactions only)

For each non-quarantined valid transaction, convert physical measures and currency to the canonical units declared in the case scope:

1. **Volume / weight / distance.** Multiply the raw quantity by the unit-conversion factor from Step 3. The canonical units are `L` (litres) for fuel volume, `KG` (kilograms) for freight weight, `KM` (kilometres) for distance.

2. **Spend.** Multiply the raw `amount` by the `usd_per_unit` FX rate for the transaction's service/purchase date and currency. Round to 2 decimal places.

3. **Aggregate.** Group by recognised fuel type or service class. Sort groups by the canonical category label ascending. For each group report the transaction/charge count, the summed normalised volume/weight/distance, and the summed normalised USD spend.

Do **not** include quarantined transactions in normalised totals.

## Step 9 — Channel readiness (contacts only)

For each non-quarantined canonical entity:

- An entity is **readiness-eligible** when it is `ACTIVE` and has at least one usable email or phone.
- A channel is **ready** only when the canonical consent is `GRANTED`.

Count entities into four mutually exclusive buckets:

| Bucket | Condition |
|---|---|
| `both` | Eligible, consent GRANTED, usable email AND usable phone. |
| `email_only` | Eligible, consent GRANTED, usable email only. |
| `phone_only` | Eligible, consent GRANTED, usable phone only. |
| `not_ready` | Eligible but consent is NOT GRANTED. |

For the readiness partition control codes, collect the consent statuses of all entities falling into each bucket and apply the outreach-code rule from Step 7.

## Step 10 — Compute rankings

When the case scope requests a ranked list (merchants, carriers, assets), sort by the primary key descending, then by tie-breakers, then by ID ascending. The scope defines the sort keys and tie-break order. For exception-based rankings, an exception is the union of mismatches and quarantined records.

## Step 11 — Determine certification / reconciliation status

Apply the thresholds or gating rules declared in the case scope:

- **Contact certification.** Compare the computed `quarantine_rate` against `pass_max_quarantine_rate` and `pass_with_exceptions_max_quarantine_rate`. Map the result through the `status_action_map`.
- **Reconciliation.** If the scope provides no explicit thresholds, use a reasonable default (e.g., HOLD when exceptions exceed a material fraction of the population).
- **Odometer regression.** If the scope declares `odometer_regression_status: HOLD`, any observed regression forces HOLD regardless of other metrics.

## Step 12 — Format and validate the answer

1. Build one JSON object whose top-level keys match the answer template **exactly**. Include every required key; omit every key not in the template.
2. Sort every ID list lexicographically ascending.
3. Sort every object array by the key specified in the template's `x-ordering_rules` or description annotations.
4. Round numeric values to the declared precision (2 decimal places for monetary and physical measures, 4 decimal places for rates).
5. Use stable IDs (snapshot IDs, row IDs, transaction IDs) exactly as they appear in the public data — do not synthesise or abbreviate them.
6. Output only the JSON object. No markdown fences, no commentary, no trailing text.

## Quick-reference: source-system precedence for contacts

When multiple source systems contribute to a contact entity, prefer them in this order for field selection:

1. Identity Registry / Compliance Master (verified master)
2. HR Directory / Partner Portal (operational source)
3. Dispatch / CRM (transactional source)

This matches the `master_hint` convention: the Compliance Master or Identity Registry row carries a hint pointing to the preferred Partner Portal or HR Directory row as the display survivor.

## Quick-reference: normalisation functions

```
normalise_name(s):  trim → collapse internal whitespace → preserve Unicode
normalise_email(s): trim → NFKC → lowercase
normalise_phone(s): strip every non-digit character → empty string if no digits remain
is_usable(email, phone): normalised email is non-empty and not 'none'/'n/a'/'null'
                         OR normalised phone digits are non-empty
```

## Quick-reference: snapshot precedence

When the same logical record appears in multiple snapshots:
1. Prefer the snapshot from the most authoritative source system named in the task.
2. Within that system, prefer `CERTIFIED` over `PROVISIONAL`.
3. Break remaining ties by `ingested_at` descending (most recently ingested).
