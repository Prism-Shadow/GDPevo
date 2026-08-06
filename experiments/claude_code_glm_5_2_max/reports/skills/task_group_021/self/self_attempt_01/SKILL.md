---
name: asteria-fleet-dq-audit
description: Audit and certify an Asteria Fleet Data Quality Hub collection (fuel purchases, freight charges, maintenance events, or contacts). Reconcile overlapping source records against the authoritative snapshot, normalize units and currency, infer opaque internal control codes, and emit exactly one JSON object that matches the task's answer_template. Use whenever a task points at the Asteria Fleet Data Quality Hub and stages payloads/case_scope.json + payloads/answer_template.json.
---

# Asteria Fleet Data Quality Hub — Audit & Certification

## When to use
A task that:
- Points at the "Asteria Fleet Data Quality Hub" at a `<TASK_ENV_BASE_URL>`,
- Stages `payloads/case_scope.json` (scope) and `payloads/answer_template.json` (output contract), and
- Asks you to audit / reconcile / certify a collection and return one JSON object.

## Inputs (read in this order — read every payload fully)
1. `prompt.txt` — the business ask and which hub interfaces are relevant.
2. `payloads/case_scope.json` — collection_id, cutoff / as_of, canonical units, base currency, focus IDs, decision-panel IDs, ranking policy, certification thresholds / gate, status→action map.
3. `payloads/answer_template.json` — the output contract: required keys, enums, minItems/maxItems, regex patterns, ordering descriptions, numeric precision. **This is law.**
4. `environment_access.md` — base URL, auth token, allowed endpoints. The ONLY source for network access; never invent endpoints or credentials.

The answer_template is the single source of truth for output shape. case_scope supplies the variable inputs (which IDs, which thresholds, which ranking policy).

## Procedure (8 phases)

### A. Load & internalize inputs
Read all four inputs. Extract: collection_id, cutoff/as_of, canonical units, base currency, every focus/decision-panel ID list, the ranking sort policy, certification thresholds + status→action map, and the full output contract (every required key, enum, count, ordering, and precision rule).

### B. Connect & catalog  (see reference/hub_access.md)
Using environment_access.md:
- `GET /api/catalog/collections` — confirm the collection exists; note its family & source_systems.
- `GET /api/catalog/schema` — list the queryable views and their fields.
- `GET /api/source-snapshots?collection=<collection_id>` — list snapshots; pick the **authoritative** one (`snapshot_status` = CERTIFIED, matching the business cutoff). Its `snapshot_id` is reported as `authoritative_snapshot_id`.

### C. Pull all rows + reference data (paginate fully)
Collections are larger than one page — page through **completely** (limit/offset for GETs; LIMIT/OFFSET in SQL; honor the `truncated` flag). Pull domain rows plus the reference views: aliases, unit conversions, FX rates. See reference/data_and_reconciliation.md for the view per domain. Never sample.

### D. Reconcile & audit  (see reference/data_and_reconciliation.md)
- Resolve overlapping source records by the authoritative snapshot (every row carries a `snapshot_id`).
- Detect cross-snapshot logical duplicates; retain the authoritative occurrence.
- Detect expected-vs-recognized class/category **mismatches** via the alias map.
- Detect **unrecognized** (0 canonical) and **ambiguous** (>1 canonical) aliases → quarantine / unrecognized.
- Detect **invalid quantities** (nonpositive/invalid volume, weight, distance, odometer; invalid/missing timestamp; invalid labor) → quarantine or invalid_event.
- Normalize units to the canonical unit via conversions; convert currency to USD via FX.
- Compute normalized totals **excluding quarantined** items. Valid class mismatches stay in totals.

### E. Focus rollups & rankings
Compute the focus-area rollups (focus assets / people / clusters) and the ranking arrays. Follow the case_scope sort policy **exactly** (primary sort DESC + tie-breaks; `rank` ascending). See reference/domain_map.md for per-domain focus/ranking.

### F. Infer opaque control codes  (see reference/domain_map.md)
For every public ID in the case_scope decision panels, infer the applicable internal control code from the shared records + the reconciled audit. Code expansions are intentionally NOT in the task materials. Use ONLY the enum values the answer_template allows. One row per scoped ID, sorted by ID ascending.

### G. Certification / release decision
Apply case_scope thresholds + status→action map (or `certification_gate`):
- status ∈ {PASS, PASS_WITH_EXCEPTIONS, HOLD} → action ∈ {RELEASE, REVIEW_EXCEPTIONS, BLOCK_AND_REMEDIATE}.
- e.g. quarantine_rate ≤ `pass_max_quarantine_rate` → PASS; ≤ `pass_with_exceptions_max_quarantine_rate` → PASS_WITH_EXCEPTIONS; else HOLD.

### H. Assemble & validate output  (see reference/output_contract.md)
Build exactly one JSON object matching answer_template, then validate **before** emitting:
- All required keys present; no extra keys (additionalProperties:false at every level).
- Every enum value contract-allowed; every array within minItems/maxItems.
- Every ID list deduplicated and sorted per the contract.
- Numeric precision exact (2 dp for measures & USD; 4 dp for rates; counts are integers).
- Count partitions sum correctly; every case_scope decision-panel ID appears in the output.
Emit the JSON object only — no commentary, no Markdown.

## Core rules (always)
- The answer_template is the contract. When the contract and your intuition conflict, the contract wins.
- One JSON object. No commentary. No Markdown. No extra keys.
- Read environment_access.md for all network access; never hardcode credentials or invent endpoints.
- Page through all rows; never sample a collection.
- Authoritative snapshot (CERTIFIED) resolves overlaps; quarantined items never enter normalized totals; valid mismatches do.
- Infer control codes from evidence; never guess outside the contract's enum.
- Validate against the template before emitting.

## Reference files
- `reference/hub_access.md` — base URL/auth, endpoint list, GET pagination, `/api/query` SQL DSL, response shapes.
- `reference/data_and_reconciliation.md` — the 8 views, reference-data semantics, snapshots, reconcile/audit/normalize rules, certification math.
- `reference/output_contract.md` — ordering, precision, enums, partition integrity, and a pre-emit self-check.
- `reference/domain_map.md` — the known collection families (fuel, freight, maintenance, contacts) → endpoints, views, control-code families, focus/ranking, contract shape, and the code-inference method.
