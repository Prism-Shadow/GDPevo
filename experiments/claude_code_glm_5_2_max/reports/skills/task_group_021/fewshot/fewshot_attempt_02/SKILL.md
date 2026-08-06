---
name: asteria-fleet-dq-audit
description: Reconcile and certify a data collection in the Asteria Fleet Data Quality Hub. Deduplicate overlapping source snapshots (CERTIFIED wins), normalize measures with reference aliases/conversions/fx, classify mismatches vs. unrecognized/ambiguous vs. quarantined, compute normalized totals and rankings, infer internal control codes per scoped public ID, and emit ONE answer JSON conforming exactly to the task's answer_template.json. Use whenever a task points at <TASK_ENV_BASE_URL> / the Asteria Fleet Data Quality Hub and asks for a reconciled audit plus a certification/close decision returned as a single JSON object.
---

# Asteria Fleet Data Quality Hub — Reconciliation & Certification Audit

This skill solves the recurring task family: *"audit collection X as of cutoff Y against the Asteria Fleet Data Quality Hub and return one certified JSON answer."* Every task in the family has the same shape — only the collection, cutoff, focus IDs, thresholds, and output contract change. The procedure below is parameterized by those inputs; it does **not** depend on any specific answer. Never copy values from another task's answer — re-derive everything for the current task's data.

## Inputs (always present in the task directory)

- `prompt.txt` — narrative of what to audit and report.
- `payloads/case_scope.json` — the **parameters**: `collection_id`, cutoff timestamp, focus/decision IDs, ranking limits and ordering rules, certification thresholds, status→action map, control-case anchors.
- `payloads/answer_template.json` — the **output contract**: a JSON Schema (or field contract) with required keys, `enum`s, `pattern`s, `minItems`/`maxItems`, ordering rules, and numeric precision. Emit EXACTLY this shape.
- `environment_access.md` — the **only** source of network access: base URL, bearer token, and the allow-list of endpoints.

## Golden rules (read first)

1. **One JSON object, exactly the template.** No extra keys, no missing keys, no commentary, no Markdown fences. Templates use `additionalProperties: false` — every key you emit must be in the schema.
2. **Discover, don't assume.** Fetch `/api/catalog/schema` and `/api/source-snapshots` at runtime to learn field names and snapshot statuses. Do not hardcode today's field names or row counts.
3. **The CERTIFIED snapshot wins.** Overlapping records across snapshots are reconciled by retaining the occurrence from the authoritative (CERTIFIED) snapshot.
4. **Quarantined records are excluded from normalized totals; valid mismatches are INCLUDED.** This is the most common accounting error.
5. **Control codes are inferred per-ID from evidence, never hardcoded.** The allowed code values come from the template; which code applies to which ID is derived from that ID's audit outcome.
6. **Respect ordering and precision exactly.** Lexicographic ascending, by-ID ascending, rank ascending; round money/quantity to the decimals declared in the template; counts are exact integers.
7. **Paginate everything.** Collections are explicitly larger than one page.

## Procedure

### 1. Connect
Read `environment_access.md`. Set `BASE_URL` and `Authorization: Bearer <token>`. Use ONLY the endpoints listed there. All reads are GET; the only write-shaped call is `POST /api/query`, which is a read-only query interface that still requires the bearer credential. See `references/endpoints.md`.

### 2. Load parameters and contract
Parse `case_scope.json` (parameters) and `answer_template.json` (contract). Note every required key, enum, pattern, `minItems`/`maxItems`, ordering rule, and precision declaration. Plan the output object against the contract BEFORE computing.

### 3. Resolve the source of truth
- `GET /api/catalog/collections` → find the collection whose stable ID equals `case_scope.collection_id`.
- `GET /api/source-snapshots` → list that collection's snapshots. The **authoritative** snapshot has status `CERTIFIED` (fall back to the newest non-STALE snapshot if none is CERTIFIED). `authoritative_snapshot_id` = its stable ID; `authoritative_row_count` = its row count.
- `scoped_raw_row_count` = in-scope raw rows (all snapshots within the cutoff; see the per-task contract for the exact denominator).

### 4. Fetch and scope the raw records
Fetch the relevant record endpoint (`/api/transactions/fuel`, `/api/transactions/freight`, `/api/maintenance/events`, or `/api/contacts`) **and page through every page**. Use `POST /api/query` to filter by collection and cutoff when the raw endpoint is large. Keep only rows whose business timestamp is `<= case_scope.cutoff_at` (maintenance: within `business_period.start..end`). `raw_row_count` = total in-scope raw rows across snapshots.

### 5. Deduplicate and pick survivors
Group raw rows by their stable logical key (logical transaction / charge / event / contact-cluster ID). Rows sharing a logical key across snapshots are one logical entity. For each group:
- `retained` occurrence = the one from the authoritative snapshot; others are duplicates.
- `duplicate_raw_count = raw_row_count − logical_count`.
Emit duplicate groups per the contract (`charge_id`/`logical_event_id`, `snapshot_ids` sorted + unique, `retained_snapshot_id`).

### 6. Normalize measures
- Units: apply `/api/reference/conversions` to bring every measure to the canonical unit declared in case_scope (volume→L, weight→KG, distance→KM).
- Currency: apply `/api/reference/fx` to convert each amount to the base currency (USD) at the rate valid on the record's business date.
Keep full precision through the pipeline; round only at emission.

### 7. Resolve canonical category / class
Map each record's raw description/alias/merchant to a canonical category via `/api/reference/aliases`. Outcomes per record:
- **exactly one** recognized → recognized class.
- **zero** recognized → *unrecognized*.
- **more than one** recognized → *ambiguous*.
Unrecognized and ambiguous both mean "cannot be assigned to exactly one recognized category."

### 8. Classify each logical record
- **Quarantine** if ANY of: unresolved class (unrecognized OR ambiguous), nonpositive/invalid quantity, nonpositive/invalid weight, nonpositive/invalid distance, or (contacts) no usable contact channel. Track per-reason sub-counts when the contract asks.
- **Mismatch (valid)** if recognized class ≠ expected class (expected class comes from the record's own declared/expected field). Mismatches are VALID.
- **Valid** otherwise.
`invalid_quantity_count`, `unrecognized_count`, `ambiguous_count` are reported separately when the contract includes them.

### 9. Exception accounting
An **exception** = a logical record that is a valid mismatch OR a quarantine. `exception_count = mismatch_count + quarantine_count` over distinct logical records (no overlap — mismatches are valid, quarantines are not). This drives the rankings.

### 10. Normalized totals
Sum over **valid** records only (exclude quarantined; **include** valid mismatches):
- volume / weight / distance in canonical units, spend in base currency.
- Group by canonical category (fuel_type / service_class) → one row per category, sorted by category ascending.
- `total_*` = sum of the group totals.
Round each emitted number to the decimals declared in the template (typically 2). `valid_transaction_count`/`valid_charge_count` = count of valid logical records. See `references/pipeline.md` for the accounting identities that must hold.

### 11. Rankings
Apply the ranking policy from `case_scope` exactly — the limit AND every tie-break:
- **Merchants (fuel):** `exception_count DESC`, then `merchant_id ASC`, limit `merchant_ranking_limit`.
- **Carriers (freight):** `mismatch_spend_usd DESC` (exposure = normalized USD on **valid** class mismatches only; quarantined charges excluded), then `carrier_id ASC`, limit `carrier_ranking_limit`.
- **Assets (maintenance):** sort keys from case_scope (e.g., `rejected_event_count DESC`, then `regression_event_count DESC`, then `asset_id ASC`), limit from case_scope.
Assign `rank` 1..N ascending. Reversing a tie-break changes the answer.

### 12. Control / decision code panels
For every public ID listed in a `case_scope` decision panel (reference alias IDs, transaction/charge IDs, event IDs, focus-cluster IDs, control-case IDs, focus-people anchors), infer the applicable internal code:
- The **allowed code values** and code field names come from `answer_template.json`. The human-readable expansions are intentionally NOT supplied — infer from evidence.
- Look up each ID's evidence via `POST /api/query` and the reference/contacts data, then map its audit outcome (which snapshot/source system it came from, validity, mismatch vs. quarantine reason, channel readiness, consent, record status, field provenance) onto the code enum for that panel.
- Code families you will meet (exact allowed values are in the template): reference-policy `RB-*`, source-basis/retention `SB-*`, ledger-disposition/routing `LD-*`, maintenance-source `MS-*`, history-route `HR-*`, identity `IC-*`, outreach `OR-*`, field-provenance `FP-*`.
- Emit one row per scoped ID, sorted by that ID ascending. See `references/codes_and_status.md`.

### 13. Certification / close status
Apply the certification rules declared in `case_scope`:
- **Threshold + action-map style** (e.g., partner onboarding): compute the gate metric (e.g., `quarantine_rate = quarantined_rows / canonical_entities`, rounded to the declared decimals), classify `PASS` / `PASS_WITH_EXCEPTIONS` / `HOLD` against `status_thresholds`, map status → action via `status_action_map`.
- **Gate style** (e.g., maintenance odometer regression): a `certification_gate` declares a condition and its status/action; a triggered gate ⇒ that status/action directly (e.g., any regression ⇒ HOLD / BLOCK_AND_REMEDIATE).
- **Default** (no explicit rules): infer conservatively — any quarantine / invalid / regression ⇒ `HOLD` / `BLOCK_AND_REMEDIATE`; a fully clean audit ⇒ `PASS` / `RELEASE`.
The status/action pair must be one of the template's allowed enum pairs.

### 14. Emit and validate
- Build ONE JSON object matching `answer_template.json` exactly: all required keys, no extras, correct enums/patterns, correct `minItems`/`maxItems`, declared ordering, declared precision.
- Run `python3 skill/scripts/validate_answer.py <answer.json> <answer_template.json>` as a pre-flight sanity check.
- Output only the JSON. No prose, no fences. See `references/output_contract.md`.

## Per-task focus areas
The contract varies; let it drive what you compute. Recurring panels:
- **Source/audit summary** — counts (raw, logical, duplicate, valid, mismatch, quarantine) + the authoritative snapshot ID.
- **Mismatch / quarantine ID lists** — complete, deduplicated, lexicographically ascending.
- **Normalized totals** — per category + grand totals, valid records only.
- **Focus rollups** — one row per focus asset/person/cluster with survivor + canonical fields + source-system provenance.
- **Rankings** — top-N with the declared sort and tie-breaks.
- **Decision/code panels** — one coded row per scoped public ID.
- **Status** — status + action from the certification rules.

## Common pitfalls
- Undercounting because you didn't paginate.
- Including quarantined records in normalized totals (or excluding valid mismatches).
- Retaining the wrong snapshot's occurrence (must be the CERTIFIED/authoritative one).
- Rounding too early, or to the wrong number of decimals.
- Reversed tie-break order in rankings.
- Hardcoding a control code instead of re-deriving it for the scoped ID.
- Emitting extra keys, missing keys, or any text outside the JSON.

## Reference files
- `references/endpoints.md` — endpoint catalog and runtime discovery checklist.
- `references/pipeline.md` — detailed phases 3–11 with the accounting identities.
- `references/codes_and_status.md` — control-code inference and certification status.
- `references/output_contract.md` — ordering, precision, and JSON emission rules.
- `scripts/validate_answer.py` — pre-flight output sanity check.
