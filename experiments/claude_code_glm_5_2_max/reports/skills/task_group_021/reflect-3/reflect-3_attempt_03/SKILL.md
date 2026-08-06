# Asteria Fleet Data Quality Hub — Audit & Certification Skill

## Purpose

Solve data-quality audit and certification tasks against the Asteria Fleet Data Quality Hub. Each task asks you to reconcile overlapping source records, identify data-quality issues, compute normalized metrics, assign internal control codes, and produce a certification or release decision. The answer is always a single JSON object conforming to a strict schema supplied in `payloads/answer_template.json`.

## Entry Instructions

1. **Read the task materials.** Open `payloads/case_scope.json` and `payloads/answer_template.json` from the task's input directory. The case scope gives you the collection ID, business cutoff, seed/stable IDs, decision panels, certification thresholds, and action maps. The answer template is a JSON Schema that your output must satisfy exactly.

2. **Read `environment_access.md`** for the base URL, auth token, and allowed endpoints.

3. **Discover the catalog and schema.** `GET /api/catalog/collections` lists collections by family (contacts, fuel, freight, maintenance, …) with approximate record counts and source systems. `GET /api/catalog/schema` describes every logical view (`v_contacts`, `v_fuel_transactions`, `v_freight_charges`, `v_maintenance_events`, `v_reference_aliases`, `v_source_snapshots`, `v_unit_conversions`, `v_fx_rates`) and its fields.

4. **Query all required data** using `POST /api/query` with body `{"query": "<SQL>"}`. Paginate with `LIMIT 500 OFFSET n`. Key queries per task:
   - Source snapshots: `SELECT * FROM v_source_snapshots WHERE collection_id = '<id>'`
   - Transaction / event / contact rows: `SELECT * FROM <view> WHERE collection_id = '<id>' ORDER BY <id_col>, snapshot_id`
   - Reference aliases: `SELECT * FROM v_reference_aliases WHERE domain = '<domain>'`
   - Unit conversions: `SELECT * FROM v_unit_conversions WHERE kind = '<kind>'`
   - FX rates: `SELECT * FROM v_fx_rates`

5. **Determine the authoritative snapshot.** Among snapshots whose `business_cutoff` matches the case scope, prefer `CERTIFIED` over `PROVISIONAL` over `STALE`. Break ties by earliest `created_at`. The authoritative snapshot resolves overlapping records.

6. **Deduplicate into logical records.** Group raw rows by the primary ID column (row_id, transaction_id, charge_id, event_id). For each logical entity keep the row from the authoritative snapshot; count the rest as duplicates.

7. **Reconcile / merge sources.** The reconcilation logic varies by collection family:

   - **Contacts family** — Cluster rows by normalised email (NFKC, lowercase, trimmed). Use Union-Find for transitive merging. Do NOT cluster by phone (shared helpdesk numbers cause false merges). For each canonical person, pick the survivor from the highest-priority source system. For canonical field values, apply source-system precedence: `Compliance Master > Partner Portal > CRM` (or `Identity Registry > HR Directory > Dispatch` for roster tasks). Handle sentinel null values (`None`, `none`, `NULL`, `N/A`, empty, whitespace) — they are not usable contact channels. Quarantine = entity with no usable email AND no usable phone. Readiness-eligible = active + at least one usable channel. Channel ready = eligible + consent GRANTED.

   - **Fuel / Freight family** — For each logical transaction/charge, match its description against reference aliases to determine the *recognised* category. Use greedy longest-match to avoid ambiguity (e.g., "bio diesel" should match the longer alias "bio diesel" → BIODIESEL, not also "diesel" → DIESEL). Only include aliases that are `ACTIVE` and valid for the cutoff period (`valid_from ≤ cutoff_date ≤ valid_to`). Classify: exactly one match and matches expected → valid; one match but differs from expected → mismatch (still valid for totals); zero matches → unrecognized; >1 match → ambiguous. Quarantine = unrecognized OR ambiguous OR invalid quantity/weight/distance. Mismatches are NOT quarantined — they enter normalized totals.

   - **Maintenance family** — Validate each event: parse timestamps, check odometer ≥ 0, labor ≥ 0 and ≤ threshold, detect odometer regression (later event with lower odometer for same asset). Invalid events are excluded from corrected metrics but reported in issue_counts. Odometer regression events also count toward regression counts and drive HOLD certification.

8. **Compute normalized metrics.** Convert quantities to canonical units using `v_unit_conversions` factors. Convert amounts to USD using certified FX rates from `v_fx_rates` with `rate_date ≤ transaction_date` (for USD, rate ≈ 1.0 — use 1.0). Round volumes/distances to 2 decimal places. Only include valid (non-quarantined) records in totals.

9. **Assign internal control codes.** These compact codes are opaque but follow observable patterns. Best-effort mapping from training:

   | Code family | Values | Likely meaning |
   |---|---|---|
   | IC (Identity) | IC-25, IC-40, IC-70, IC-90 | Verification strength: 0 verified → 25, 1 → 40, 2 → 70, 3+ → 90 |
   | FP (Field Provenance) | FP-20, FP-55, FP-75 | Source authority: CRM/low → 20, Partner Portal/HR → 55, Compliance Master/Registry → 75 |
   | OR (Outreach) | OR-15, OR-35, OR-60, OR-80 | Contact readiness: no channel/UNKNOWN → 15, PENDING → 35, DENIED → 60, GRANTED → 80 |
   | RB (Reference Basis) | RB-17, RB-42, RB-83 | Permanent ACTIVE → 83, time-bounded/PROVISIONAL → 42, INACTIVE/not-yet-valid → 17 |
   | SB (Source Basis) | SB-24, SB-61, SB-79 | From authoritative/certified → 79, provisional → 24, mixed → 61 |
   | LD (Ledger Disposition) | LD-14, LD-31, LD-53, LD-72, LD-88 | Accepted → 88, class mismatch → 53, unrecognized/ambiguous → 31, rejected → 14 |
   | MS (Maintenance Source) | MS-12, MS-47, MS-86 | Snapshot authority level |
   | HR (History Route) | HR-19, HR-33, HR-74 | Accepted → 74, flagged → 33, rejected → 19 |

   **Important:** These mappings are inferred from observed patterns and may not be fully correct. Validate them against the specific data characteristics of each collection.

10. **Determine certification / release status.** Apply the thresholds from `case_scope.json`:
    - Compare quarantine rate (or exception count) against `status_thresholds`.
    - Map the resulting status through `status_action_map` (or `certification_gate` for maintenance).
    - If odometer regressions exist → typically HOLD + BLOCK_AND_REMEDIATE (per `certification_gate`).

11. **Assemble the answer JSON** strictly matching `answer_template.json`. Pay attention to:
    - Required fields and their types.
    - Enum constraints on code fields.
    - `minItems`/`maxItems` for arrays (especially focus-cluster, decision-panel, and ranking arrays).
    - Sorting rules stated in descriptions or `x-ordering_rules` (usually lexicographic ascending by stable ID, or by count descending with ID ascending tiebreak).
    - Numeric precision (round to stated decimal places).

12. **Validate before submitting.** Check your JSON against the schema. Common mistakes:
    - Missing or extra top-level keys.
    - Wrong enum values in control codes.
    - Arrays with wrong number of items.
    - Floating-point where integer is expected.
    - Not rounding to required precision.

## Supporting Reference Files

- `reference/alias_matching.md` — Greedy longest-match algorithm for fuel/freight alias recognition
- `reference/control_codes.md` — Control code enumeration and inference rules
- `reference/quarantine_rules.md` — Quarantine criteria by collection family

## Key Gotchas

- **Phone numbers are NOT reliable cluster keys** for contacts — shared helpdesk numbers cause over-clustering.
- **`master_hint` on Compliance Master rows** signals contested identity (shared alias), not a merge instruction.
- **Alias validity dates** must be checked against the cutoff: FUA-016 ("priority" → PREMIUM_UNLEADED) starts 2026-03-01, so it is NOT valid for a January audit.
- **Sentinel null values** (`None`, `none`, `NULL`, `N/A`, empty string, whitespace) must be treated as absent, not as real data.
- **FX rate for USD** is sometimes ≈1.005 in the API but should be treated as 1.0 for base-currency conversion.
- **Mismatches ≠ quarantine.** A fuel/freight transaction whose recognised category differs from expected is still valid for normalized totals. Only unrecognized/ambiguous/invalid-measure records are quarantined.
- **ODOMETER_REGRESSION** in maintenance is reported in `corrected_metrics.regression_event_ids`, NOT in `invalid_event_ids` (sequence-only regressions vs. truly invalid events).
