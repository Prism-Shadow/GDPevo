---
name: asteria-fleet-dq-certification
description: Audit and certify an Asteria Fleet Data Quality Hub collection (fuel, freight, contacts, or maintenance) against a staged case scope and JSON answer template. Reconcile overlapping source snapshots, classify and quarantine bad rows, normalize units and currency, compute ranked rollups, assign opaque internal control codes, and emit one JSON object with the certification decision. Use when a task provides prompt.txt + payloads/case_scope.json + payloads/answer_template.json pointing at the Asteria Fleet Data Quality Hub.
---

# Asteria Fleet DQ Hub Certification

## When to use
Use this skill for any task that:
- Points at the "Asteria Fleet Data Quality Hub" via the placeholder `<TASK_ENV_BASE_URL>`, and
- Stages `prompt.txt`, `payloads/case_scope.json`, and `payloads/answer_template.json`, and
- Asks for a reconciled audit / certification / readiness brief returned as a single JSON object matching the template.

The canonical shapes are: fuel-purchase normalization, freight-charge accrual reconciliation, partner/contact-master certification, field-service roster contact-readiness, and maintenance-log integrity. A new collection maps to one of these families via the catalog `family` field (`fuel`, `freight`, `contacts`, `maintenance`).

## Inputs
- `prompt.txt` — narrative of what to audit and which interfaces to use.
- `payloads/case_scope.json` — parameters: `collection_id`, cutoff timestamp, focus / decision-panel stable IDs, ranking policy, numeric precision, certification thresholds or gate, and the status→action map.
- `payloads/answer_template.json` — the exact output contract (JSON Schema or field contract). Authoritative for required keys, enums, patterns, ordering, and precision. `additionalProperties: false` is pervasive — never add keys.
- `environment_access.md` — the ONLY source for the hub base URL, the bearer token, and the allow-list of endpoints. Read it at runtime; do not hardcode credentials.

## Connection (detail in `references/hub_interfaces.md`)
- Base URL and `Authorization: Bearer <token>` come from `environment_access.md`.
- Primary data access: `POST /api/query` with `{"query": "<SQL>"}` over logical views (`v_fuel_transactions`, `v_freight_charges`, `v_contacts`, `v_maintenance_events`, `v_source_snapshots`, `v_fx_rates`, `v_reference_aliases`, `v_unit_conversions`). Response: `{columns, row_count, rows, truncated}`. Page with `LIMIT n OFFSET m`; stop when `truncated` is false.
- Reference data: `GET /api/reference/fx` (unfiltered), `GET /api/reference/aliases?domain=<fuel|freight|...>`, `GET /api/reference/conversions?kind=<volume|weight|distance|...>`. All paginate as `{items, limit, offset, total}`.
- Discovery: `GET /api/catalog/collections`, `GET /api/catalog/schema`.

## Operating procedure

### Phase 0 — Intake & integrity
1. Read all three staged files. Parse `case_scope.json` and `answer_template.json`.
2. Confirm the staged task directory contains only the expected files; if anything unexpected is present, stop and surface it — never fold stray material into the answer.
3. From the scope extract: `collection_id`, cutoff, focus IDs, decision-panel ID lists, ranking policy (sort keys + tie-breaks), precision, and the certification gate/thresholds. From the template extract: every required key, enum, pattern, `minItems`/`maxItems`, and ordering rule.

### Phase 1 — Discover hub structure
1. `GET /api/catalog/collections`; confirm the `collection_id` exists and note its `family` and `source_systems`.
2. `GET /api/catalog/schema`; note the fields of the view for that family.
3. Query `v_source_snapshots` for the collection (`SELECT ... FROM v_source_snapshots WHERE collection_id='<id>'`). Note each snapshot's `snapshot_id`, `snapshot_status` (CERTIFIED/PROVISIONAL/STALE), `business_cutoff`, `created_at`, `row_count`, `checksum`.

### Phase 2 — Reconcile source records
1. Choose the AUTHORITATIVE snapshot: prefer `CERTIFIED` over `PROVISIONAL` over `STALE`; break ties by newest `created_at` (then `ingested_at`). It resolves overlapping logical records. Record its `snapshot_id` as `authoritative_snapshot_id`.
2. Pull all in-scope raw rows for the collection across snapshots (via the family's view, `WHERE collection_id='<id>' AND <cutoff filter>`). Apply the business cutoff to the correct timestamp field exactly as the scope states.
3. Deduplicate: rows representing the same logical entity/transaction across snapshots collapse to one logical record. The retained occurrence is the one from the authoritative snapshot (record `retained_snapshot_id` / `survivor_row_id` / `master_id`). `raw_row_count` = all rows; `logical_*_count` = deduped; `duplicate_raw_count` = raw − logical (per the template's definition).

### Phase 3 — Classify (family-specific; see `references/reconciliation.md`)
Apply the classification the template's counts require. Categories recurring across families:
- **Recognized** — description/alias maps to exactly one canonical category (fuel type / service class).
- **Unrecognized** — zero alias matches.
- **Ambiguous** — more than one alias match.
- **Mismatch** — recognized canonical category differs from the source's `expected_*` field. Mismatches are VALID (they enter normalized totals) unless the task says otherwise.
- **Quarantine** — row cannot enter totals: unrecognized/ambiguous category, invalid/nonpositive quantity/weight/distance, invalid timestamp/odometer/labor, or no usable contact channel. Quarantined rows are EXCLUDED from normalized totals and from "valid" counts.
- **Contacts only**: duplicate-cluster merge, survivor selection, contested-identifier cases, channel readiness (usable email/phone + consent GRANTED + record ACTIVE).
- **Maintenance only**: missing/invalid timestamp, invalid odometer, negative/extreme labor, odometer regression (regressions go in `corrected_metrics`, not `invalid_event_ids`, unless stated).

### Phase 4 — Normalize
1. Units: convert quantity/weight/distance to the scope's canonical unit (`L`, `KG`, `KM`) using `v_unit_conversions` (`factor`; respect `valid_from`/`valid_to` and `precision`).
2. Currency: convert `amount` to the scope's base currency (USD) using `v_fx_rates` (`usd_per_unit`) matched by `currency` and the relevant date (rate_date ≤ transaction date; acceptable `rate_status`).
3. Precision: round every numeric output to the decimal places declared in the scope/template (typically 2 for money/volume/distance; 4 for rates such as `quarantine_rate`). Counts are exact integers — never float.
4. Exclude quarantined rows from all normalized totals. Include valid mismatches.

### Phase 5 — Aggregate & rank
1. Build the required totals (overall + per-category/per-class/per-fuel-type), counts, and rollups (per asset / region / depot / carrier / merchant).
2. Rankings: apply the scope's `primary_sort` + `tie_breaks` exactly. `rank` is 1-indexed. Honor `limit` / `merchant_ranking_limit` / `carrier_ranking_limit`.
3. For "exception" rankings, an exception is usually a distinct logical record that is a valid mismatch OR quarantined — read each template's definition; do not assume.

### Phase 6 — Code panels (see `references/code_panels.md`)
For every public ID in the scope's decision panels / focus clusters / control cases, assign the opaque internal control code(s) the template requires.
- Allowed values come from THIS task's `answer_template.json` enums — do not import values from other tasks.
- Expansions are deliberately not supplied; infer each code from the underlying record's evidence (source system, snapshot status/basis, field-precedence system, validity/mismatch/quarantine outcome).
- Never guess; if evidence is insufficient, re-query the hub. One coded object per scoped ID, sorted as the template requires.

### Phase 7 — Certify
1. Compute the gate metric the scope defines (e.g., `quarantine_rate = quarantined / canonical_entities`, or an odometer-regression flag).
2. Map to status via the scope's `status_thresholds` / `certification_gate` (PASS / PASS_WITH_EXCEPTIONS / HOLD).
3. Map status → action via the scope's `status_action_map` (RELEASE / REVIEW_EXCEPTIONS / BLOCK_AND_REMEDIATE). Some scopes hard-code the gate (e.g., any regression ⇒ HOLD ⇒ BLOCK_AND_REMEDIATE).
4. Match the template's exact key names (`status`/`action`, or `status`/`routing`, or `status`/`next_action`).

### Phase 8 — Emit
1. Produce exactly ONE JSON object. No commentary, no Markdown, no trailing text.
2. Conform exactly to `answer_template.json`: every required key present, no extra keys (`additionalProperties: false`), correct types/enums/patterns and `minItems`/`maxItems`.
3. Ordering: sort every ID list lexicographically ascending unless the template says otherwise; sort object arrays by the template's stated key; apply tie-breaks.
4. Deduplicate all ID sets. Round numerics to the declared precision.

## Cross-cutting rules (gotchas)
- **Read `environment_access.md` at runtime** for base URL, token, and allowed endpoints. Use only those endpoints.
- **Quarantined rows are excluded from normalized totals; valid mismatches are included.** The most common error.
- **`additionalProperties: false` everywhere** — never add helper or extra keys.
- **Pagination truncates**: both `/api/query` (`truncated`, `LIMIT/OFFSET`) and GET reference endpoints (`limit/offset/total`). Always page to completion; never assume a single response is complete (collections routinely span multiple pages).
- **The authoritative snapshot resolves overlaps** — duplicates collapse to the authoritative-snapshot occurrence.
- **The cutoff is a filter** — apply it to the correct timestamp field before counting.
- **Counts are exact integers**; only declared numeric fields are rounded floats.
- **Codes are inferred from evidence, constrained by the current template's enum** — not memorized.
- **Stable IDs only** — use IDs present in the public data or the scope; preserve required ordering.

## References
- `references/hub_interfaces.md` — endpoint catalog, request/response envelopes, SQL query contract, pagination, view field reference.
- `references/reconciliation.md` — per-family classify / normalize / rank specifics.
- `references/code_panels.md` — opaque code vocabulary and inference method.
