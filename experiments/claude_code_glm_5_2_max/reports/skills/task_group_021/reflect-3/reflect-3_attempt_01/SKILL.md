---
name: asteria-fleet-data-quality-reconciliation
description: Solve Asteria Fleet Data Quality Hub reconciliation/certification tasks — reconcile overlapping source snapshots of fuel, freight, maintenance, and contact collections, compute quality/normalization metrics, infer opaque control codes, and emit the JSON certification answer. Read BEFORE acting on any task that names the "Asteria Fleet Data Quality Hub", mentions source-snapshot reconciliation, business cutoffs, canonical entities, quarantine, mismatch/unrecognized categories, channel readiness, or opaque Asteria control codes (IC/OR/FP, RB/SB/LD, MS/HR).
---

# Asteria Fleet Data Quality Hub Reconciliation

A family of tasks asks you to audit one Asteria Fleet collection, reconcile its
overlapping source records **as of a stated business cutoff**, and return a single
JSON object matching an `answer_template.json`. The five collection families are:

- **contacts** (`v_contacts`) — partner onboarding, dealer, warranty, field-service rosters
- **fuel** (`v_fuel_transactions`) — fuel/charging purchases
- **freight** (`v_freight_charges`) — carrier invoice charge lines
- **maintenance** (`v_maintenance_events`) — work-order events

Every collection is published as 2–3 **snapshots** (CERTIFIED + PROVISIONAL, sometimes a
second CERTIFIED source). Overlapping business records appear in more than one snapshot.
Your job is to collapse duplicates to logical records, classify data-quality issues,
normalize units/currency, infer opaque control codes, and certify.

This skill gives the **procedure** and the **decoded reconciliation rules**. It does NOT
contain candidate answers or task-specific final values — apply the rules to the live hub.

## 1. Inputs you are given

For each task directory `train_tasks/<task>/input/`:
- `prompt.txt` — the business framing.
- `payloads/case_scope.json` — **the authoritative specification**: collection_id,
  business cutoff, focus seeds/anchors, decision-panel IDs, thresholds, sort orders.
  Treat this as the source of truth for parameters.
- `payloads/answer_template.json` — the JSON-Schema the answer must match **exactly**
  (required keys, `enum`s, `pattern`s, item counts, ordering rules). Read it first.
- `environment_access.md` — hub base URL + bearer token + allowed endpoints.
- `judge_access.md` — a **train-only** judge endpoint. Ignore it when solving; it is not
  part of the procedure and must not be wired into test solving.

## 2. Hub access pattern

The hub exposes two query styles. Prefer SQL for bulk work:

**Read-only SQL** (POST `/api/query`, body `{"query": "<SQL>"}`):
- Returns `{"columns":[...], "rows":[[...]], "truncated":bool}`.
- SQLite-flavored. **Use single-quoted string literals** (e.g. `WHERE collection_id='x'`).
  Parameter binding via `?`/`params` is NOT supported.
- Paginate with `LIMIT n OFFSET m`. `truncated:true` means more rows exist.
- Whitelisted views only: `v_contacts`, `v_fuel_transactions`, `v_freight_charges`,
  `v_maintenance_events`, `v_fx_rates`, `v_reference_aliases`, `v_unit_conversions`,
  `v_source_snapshots`. `sqlite_master`, `information_schema`, `SHOW`, `DESCRIBE`,
  `LIKE`, and `LOWER()` are **rejected**.
- All `*` selects work: `SELECT * FROM v_freight_charges WHERE collection_id='...'`.

**REST** (GET, header `Authorization: Bearer <token>`):
- `/api/catalog/collections` — collection metadata (no filter).
- `/api/catalog/schema` — the 8 views + field meanings (no filter).
- `/api/source-snapshots?collection=<collection_id>` — snapshot list. **Filter key is
  `collection`**, not `collection_id`. (Other keys return `{"error":"invalid filter"}`.)
- `/api/contacts` — contacts (paginated).
- `/api/transactions/fuel`, `/api/transactions/freight`, `/api/maintenance/events` — raw rows.
- `/api/reference/aliases?domain=<fuel|freight>` — alias→canonical map.
- `/api/reference/conversions?kind=<volume|distance|weight|odometer>` — unit factors.
- `/api/reference/fx` — FX rates (no filter).

**Discovery order that always works**: read `case_scope.json` → GET schema (views+fields)
→ GET snapshots (`?collection=`) → SQL-query the relevant view filtering by
`collection_id` → fetch aliases/conversions/fx as needed.

## 3. Hub data model — field decoding

### Snapshots & source systems
Each snapshot carries `snapshot_id`, `snapshot_status` (CERTIFIED > PROVISIONAL > STALE),
`source_system`, `row_count`, `business_cutoff`, `created_at`, `ingested_at`, `checksum`.
Transaction/event/charge views carry `snapshot_id` but **not** `source_system` — join via
`v_source_snapshots`. Contact views DO carry `source_system`.

**Authoritative snapshot** = the one with the best `snapshot_status` (CERTIFIED first).
When two snapshots are both CERTIFIED (contacts), prefer by tie-break in the case scope
or by `snapshot_id` ascending. PROVISIONAL is supplementary feed data.

### Overlap rule (the core reconciliation)
The same business record appears in multiple snapshots. The **only field that differs**
between duplicate occurrences is typically `ingested_at` (and for maintenance,
`event_status`/`ingested_at`; for contacts, the whole row is a fresh source-system view).
Collapse by the business key:
- fuel: `transaction_id`
- freight: `charge_id`
- maintenance: `event_id`
- contacts: by **identity key** (see §6), not by `row_id` (each snapshot invents fresh `row_id`s)

`raw_row_count − logical_count = duplicate_raw_count`. The authoritative occurrence is
**retained**; the others are dropped. For contacts, every source-system row is retained as
a member of the cluster.

### Aliases (category resolution)
`v_reference_aliases` (`domain`, `alias_id`, `alias_text`, `canonical_value`,
`valid_from`, `valid_to`, `reference_status`, `published_at`). Map a free-text
description (`purchased_description` / `description`) to a **recognized canonical category**
by matching alias_text substrings (case-insensitive) in the description.

- An alias is **effective as-of the business cutoff** only if `valid_from <= cutoff_date`
  AND (`valid_to` is null OR `valid_to >= cutoff_date`) AND `reference_status != INACTIVE`.
- **The deliberate trap is a single alias_text that has more than one reference row**
  (e.g. an INACTIVE/expired one plus an ACTIVE one with later `valid_from`, or a short
  generic token like `priority` used as a catch-all). A naive `reference_status=ACTIVE`
  filter picks the wrong row when the cutoff falls before the new row's `valid_from`. The
  ONLY safe selection is the row **effective as-of the cutoff** per the rule above. Always
  GROUP alias rows by `alias_text` and check every row's validity window before deciding.
- **PROVISIONAL alias rows are candidate mappings not yet adopted** — treat a description
  whose only effective match is a PROVISIONAL alias as not-yet-recognized (do not promote it
  to a canonical category for reconciliation). Scan `reference_status` for PROVISIONAL rows
  in the live alias set rather than assuming any named text.
- A description that matches alias_texts leading to **two distinct canonical values** =
  ambiguous → unrecognized. A description with **no** effective alias match = unrecognized.
- Resolution detail: if all matched alias_texts agree on one canonical value (even several
  alias_texts), that is a **unique** match, not ambiguous (e.g. "ULSD road diesel" matches
  both "ulsd" and "road diesel" but both → DIESEL → unique).

### Unit conversions (`v_unit_conversions`, `kind/from_unit/to_unit/factor/precision`)
`value_canonical = value_raw * factor`. Canonical units: **L** (volume), **KM**
(distance & odometer), **KG** (weight).
- volume: US_GAL→L 3.785411784, IMP_GAL→L 4.54609, L→L 1.0
- distance: MI→KM 1.609344, KM→KM 1.0
- odometer: MI→KM 1.609344 (precision 1), KM→KM 1.0
- weight: LB→KG 0.45359237, KG→KG 1.0
Round volume/weight/distance totals to **2 decimals**; the `precision` field is the
per-value display precision, not the aggregate rounding.

### FX (`v_fx_rates`, `rate_date/currency/usd_per_unit/rate_status/published_at`)
`usd_amount = amount * usd_per_unit`. USD's own rate is 1.0.
- Match the rate by `currency` + `rate_date` == the transaction's business date
  (`purchased_at`/`service_date` date portion). If the exact date is missing, use the
  latest prior available date.
- **Prefer the CERTIFIED rate** over PROVISIONAL for the same currency+date — when two rows
  share a currency+date, keep the one with the better `rate_status` (CERTIFIED > PROVISIONAL)
  and, on a tie, the later `published_at`. Verify the live `v_fx_rates` rows rather than
  assuming any fixed publish time.

## 4. Universal certification gate

Status/action mapping (always present in case_scope as `status_action_map` or
`status_thresholds`/`certification_gate`):
- PASS → RELEASE
- PASS_WITH_EXCEPTIONS → REVIEW_EXCEPTIONS
- HOLD → BLOCK_AND_REMEDIATE

Thresholds (contact tasks) use `quarantine_rate = quarantined_rows / canonical_entity_count`
rounded to 4 decimals: PASS if `<= pass_max_quarantine_rate` (usually 0.0);
PASS_WITH_EXCEPTIONS if `<= pass_with_exceptions_max_quarantine_rate` (usually 0.04); else HOLD.

Transaction/maintenance gates: the case_scope states the exact gate (e.g. maintenance's
`certification_gate` directly says `HOLD`/`BLOCK_AND_REMEDIATE`; freight/fuel infer HOLD
when invalid physical measures exist, else PASS_WITH_EXCEPTIONS if any mismatch/quarantine,
else PASS). **When the scope states the gate explicitly, use it verbatim.**

## 5. Reconciliation per family

### Fuel & freight (parallel pipeline)
1. Collapse snapshots → logical records (retain CERTIFIED occurrence per business key).
2. Resolve each `description` → recognized canonical category via effective aliases.
3. Classify per logical record:
   - **mismatch**: recognized category (unique) ≠ `expected_fuel_type`/`expected_service_class`.
   - **unrecognized**: no or ambiguous alias match → also quarantined.
   - **invalid quantity/measure**: `quantity <= 0` (fuel), `billed_weight <= 0` or
     `distance <= 0` (freight) → quarantined.
   - **quarantine** = unrecognized OR invalid measure. Quarantined records are EXCLUDED
     from normalized totals; valid mismatches ARE included in totals.
4. Normalize: volume→L, weight→KG, distance→KM, amount→USD (certified FX).
5. Aggregates: per-category totals (sorted by category), total volume/weight/distance/spend,
   focus-asset rollups, **merchant/carrier exception ranking** (exception_count = distinct
   logical records with a mismatch OR quarantine; sort by exception_count desc then id asc
   for merchants; for carriers by mismatch_spend_usd desc then carrier_id asc — mismatch
   spend = USD on valid class-mismatch records only).
6. Duplicate groups (freight: one object per charge_id with >1 raw occurrence, retained
   snapshot = authoritative).

### Maintenance
1. Collapse snapshots → 1 retained row per `event_id` (retain CERTIFIED).
2. Issue counts (**row-level unless scope says logical**): missing event_time_raw (null/blank),
   invalid timestamp (unparseable, e.g. `2026-99-45 25:61`), invalid odometer (<=0),
   negative labor (<0), extreme labor (a sentinel cap stated in the case_scope; flag any
   labor value at/above it), odometer regression (later event's odometer < earlier event's
   max for the same asset, chronological by time). Pull the concrete labor cap from the
   case_scope rather than assuming a fixed value.
3. `invalid_event_ids` = events rejected for missing/unparseable time or invalid
   odometer/labor range. **Sequence-only regressions go in `corrected_metrics`, not invalid_event_ids.**
4. `corrected_metrics.total_distance_km` = Σ over assets of (last reliable odometer − first
   reliable odometer) in the **reconstructed** Q1 history, odometer converted to KM, kept
   monotonically non-decreasing (drop regressed readings), 2 decimals.
5. `asset_risk_ranking`: sort by rejected_event_count DESC, regression_event_count DESC,
   asset_id ASC; top 5.
6. `duplicate_groups`: one per event_id in >1 snapshot — `logical_event_id`, all `snapshot_ids`
   (sorted), `retained_event_id`, `retained_snapshot_id` (authoritative).
7. `event_decision_panel`: one coded decision per scoped event_id (sorted asc).

### Contacts (partner/dealer/warranty/field-service)
1. Build **clusters** of the same logical person across source systems using the **identity
   key**: the numeric token in the clean `@example-fleet.com` email local-part
   (e.g. `sofia.smith.0` → token 0; token is stable across all 3 source-system rows of one
   person). Rows whose email is a placeholder (`null`/`none`/`n/a`/blank) or a `.part.NNN`/
   `.fiel.NNN` `@mail.example` decoy do NOT share a token — treat each as its own
   single-source identity (these are deliberately-distinct decoys, NOT the 3rd snapshot of a
   clean person).
2. Canonical fields per cluster: pick by survivorship precedence — prefer authoritative
   snapshot, then `verified_flag=1`, then source priority (contacts: Compliance Master >
   Partner Portal/HR Directory > CRM/Dispatch; field-service: HR Directory > Identity
   Registry > Dispatch). **Email** = NFKC-trim-lowercase. **Phone** = digits only, stripping
   spurious country codes (+1/+44/+21 leading) to the canonical 10-digit form. **City/name**
   = trimmed NFKC; name title-cased.
3. **Quarantine** = cluster has no usable email AND no usable phone.
4. **Channel readiness** (over readiness-eligible = ACTIVE + ≥1 usable email/phone): bucket
   by which channels are usable AND consent is GRANTED:
   both / email_only / phone_only / not_ready (consent not GRANTED).
5. **Contested / no-automerge**: a shared identifier (any `master_hint` value shared by
   >1 distinct identity, or a phone number shared across distinct identities, or any field
   the case flags as a shared business line) is contested → `CONTESTED_NO_AUTOMERGE`. Same
   name+phone across sources that genuinely disagree = do not merge. Detect these by
   scanning the live data: any identifier value used by rows belonging to >1 identity key is
   contested — do not hardcode specific hint strings.

## 6. Opaque control codes — inference

Codes are **not documented** in the task materials; infer them from record characteristics.
The allowed enum values come from each task's `answer_template.json`. Use these mappings as
the starting interpretation and confirm against the enum set:

**Contacts (IC/ OR/ FP)**:
- `identity_code` (IC-25/40/70/90): single-source identity → **IC-25**; 2 merged sources →
  **IC-40**; 3+ merged sources → **IC-70**; contested/conflicting identity (shared
  identifier across distinct people) → **IC-90**.
- `outreach_code` (OR-15/35/60/80): consent status GRANTED→**OR-80**, PENDING→**OR-60**,
  DENIED→**OR-35**, UNKNOWN→**OR-15**.
- `field_provenance_code` (FP-20/55/75): authoritative source verified_flag=1 → **FP-75**;
  ≥2 contributing source systems → **FP-55**; single unverified source → **FP-20**.

**Fuel/freight (RB / SB / LD)**:
- `reference_policy_code` / reference-row decision (RB-17/42/83): ACTIVE alias effective
  as-of cutoff → **RB-83**; ACTIVE but not-yet-effective-as-of-cutoff OR PROVISIONAL →
  **RB-42**; INACTIVE/expired → **RB-17**. (The reference set is seeded so that across the
  scoped alias_ids each of RB-17/42/83 appears at least once — apply the as-of rule per row
  to distribute them, do not hardcode.)
- `source_basis_code` / source-retention (SB-24/61/79): retained occurrence from the
  CERTIFIED/authoritative snapshot → **SB-79**; from PROVISIONAL → **SB-24**.
- `ledger_disposition_code` / ledger-routing (LD-14/31/53/72/88): quarantined → **LD-14**;
  valid class mismatch → **LD-72**; REVIEW record_status → **LD-53**; non-USD currency →
  **LD-31**; clean POSTED/BILLED USD → **LD-88**.

**Maintenance (MS / HR)**:
- `maintenance_source_code` (MS-12/47/86): retained from authoritative snapshot → **MS-86**;
  from provisional → **MS-47**; (MS-12 reserved for the third/legacy source when present).
- `history_route_code` (HR-19/33/74): rejected/invalid event → **HR-19**; regression event →
  **HR-33**; clean sequenced event → **HR-74**.

When a record could match two rules, prefer the **most specific / most severe** applicable
code, and always pick a value from that field's enum.

## 7. Output discipline

- Produce **one JSON object** matching `answer_template.json` exactly: every `required`
  key present, no extra top-level keys beyond the template, every array at its
  `minItems/maxItems`, every value from its `enum`, every string matching its `pattern`.
- **Sort/Ordering** is graded — follow each field's `description`/`x-ordering_rules`:
  IDs lexicographically ascending; cluster/asset arrays by their stated sort key; ranking
  arrays by rank ascending. Member-row-id lists are deduped + lexicographically sorted.
- Numeric precision: counts are exact integers; currency/volume/distance/odometer rounded
  to the stated decimals (usually 2; quarantine_rate to 4). No floats where the contract
  says integer.
- Stable IDs only: use IDs present in the live hub or supplied in the case_scope. Never
  invent canonical classes, snapshot IDs, or codes outside the enums.
- No commentary, no Markdown wrapper — the answer is bare JSON.

## 8. Transferable procedure (run this for every task)

1. Read `case_scope.json` + `answer_template.json` fully. Note item counts, enums, sort rules,
   the cutoff date, and the certification gate/thresholds.
2. GET `/api/catalog/schema`; identify the family's view and its fields.
3. GET `/api/source-snapshots?collection=<collection_id>`; pick the authoritative snapshot;
   record `authoritative_snapshot_id`.
4. SQL-dump the family view `WHERE collection_id='<id>'` (paginate). Fetch aliases
   (`?domain=`), conversions (`?kind=`), fx as the family needs.
5. Collapse snapshots → logical records by business key; compute `duplicate_raw_count`.
6. Apply family-specific classification (mismatch/unrecognized/invalid/quarantine;
   issue_counts; regressions).
7. Normalize units + FX; aggregate totals, per-category rows, focus rollups, rankings.
8. Infer control codes per the §6 mappings for every scoped decision-panel ID.
9. Compute the certification status/action from the scope's gate/thresholds.
10. Assemble the JSON to the template, enforce ordering & precision, and emit bare JSON.

Supporting reference tables live next to this file in `reference/`.
