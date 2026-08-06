# Asteria Fleet Data Quality Hub — Reconciliation Skill

## Purpose

Execute a data-quality reconciliation, audit, or certification task against the Asteria Fleet Data Quality Hub. The hub exposes a read-only REST API over fleet-domain collections (contacts, fuel transactions, freight charges, maintenance events). Each task reconciles overlapping source records, applies business rules, assigns internal control codes, and produces a single JSON answer conforming to a provided output contract.

## When to Use

Invoke this skill when the user prompt references:
- "Asteria Fleet Data Quality Hub" or a `<TASK_ENV_BASE_URL>` placeholder
- Reconciling fleet-domain records across source snapshots
- Producing a certification, audit, or readiness decision with control codes
- An `environment_access.md` file with hub connection details
- `payloads/case_scope.json` and `payloads/answer_template.json`

## Input Convention

Every task instance provides exactly these files — read them in this order:

1. **`environment_access.md`** — base URL, Authorization header, and allowed endpoints. Overrides any `localhost`, `127.0.0.1`, or `<TASK_ENV_BASE_URL>` references in the prompt. The `query_authorization_header` field carries the full `Authorization: Bearer <token>` string; include it verbatim on every request.
2. **`payloads/case_scope.json`** — task parameters: `collection_id`, business cutoff, focus entities, ranking limits, thresholds, and decision-panel IDs.
3. **`payloads/answer_template.json`** — output contract. This is a JSON Schema (draft 2020-12) that defines every required key, enum, pattern, min/maxItems, and ordering constraint. All ordering rules (lexicographic, rank-based, ascending/descending) are declared here — follow them exactly.
4. **`prompt.txt`** — natural-language task description. Read it last; let the structured payloads drive the execution plan.

## API Interaction

### Connection

Every request uses the `base_url` from `environment_access.md`. Append the endpoint path directly. Include the `query_authorization_header` value as the `Authorization` header on every call.

The hub is served from `http://task-env:9021/` inside the execution container. Do not use `localhost` or `127.0.0.1` — use the exact base URL from `environment_access.md` and the runtime note override.

### Discovery Phase — Always Run First

1. **`GET /api/catalog/collections`** — list available collections. Locate the one matching `case_scope.collection_id`. Note its metadata.
2. **`GET /api/catalog/schema`** — retrieve field definitions. Understand column names, types, and constraints before querying.
3. **`GET /api/source-snapshots`** — list all snapshots with their status, ingest time, row counts, and coverage windows. Identify which snapshot is authoritative (look for status fields like `CERTIFIED`, most recent ingest before the cutoff, or explicit authoritative markers). The authoritative snapshot is the one whose row is retained when duplicates span multiple snapshots.

### Data Retrieval

Use the domain-specific GET endpoints to pull raw records:

| Domain | Endpoint |
|---|---|
| Contacts | `GET /api/contacts` |
| Fuel transactions | `GET /api/transactions/fuel` |
| Freight charges | `GET /api/transactions/freight` |
| Maintenance events | `GET /api/maintenance/events` |

Use **`POST /api/query`** with `{"query": "<SQL>"}` for:
- Filtering by collection, snapshot, date range, or asset
- Aggregations (COUNT, SUM, GROUP BY)
- Joins across reference tables
- Any query too complex for a simple GET

Reference data endpoints (read without filters first, then use query for lookups):
- `GET /api/reference/aliases` — maps description/category aliases to canonical categories
- `GET /api/reference/conversions` — unit conversion factors
- `GET /api/reference/fx` — foreign exchange rates

### Pagination

If a GET endpoint returns partial results, use `POST /api/query` with `LIMIT`/`OFFSET` or iterate until all rows are retrieved. The underlying collection may be larger than a single response page — always verify you have the complete dataset before computing metrics.

## Reconciliation Rules

### Source Overlap Resolution

1. **Group raw rows by logical identifier.** The logical ID is the field that represents the same business entity across snapshots (e.g., a transaction ID, event ID, or charge ID). Raw rows sharing the same logical ID but appearing in different snapshots are duplicate occurrences of the same entity.
2. **Select the authoritative snapshot.** Among the snapshots containing a given logical ID, retain the row from the authoritative snapshot. The authoritative snapshot is determined from `/api/source-snapshots` metadata — prefer `CERTIFIED` status, then most recent ingest timestamp before the business cutoff.
3. **Count duplicates.** `duplicate_raw_count` = total raw rows − distinct logical IDs.

### Quarantine Rules

Apply quarantine rules per the task domain. Common quarantine conditions:

- **Missing or unparseable fields**: timestamp, odometer, email, phone
- **Invalid value ranges**: negative quantities, nonpositive weight/distance, extreme labor hours
- **Unresolvable references**: description that matches zero recognized categories (unrecognized) or more than one (ambiguous)
- **No usable contact channel**: no valid email and no valid phone
- **Category/class mismatch between expected and recognized**: these are NOT quarantined unless the mismatch makes the record unusable; they are reported separately as mismatches

Quarantined records are **excluded from normalized totals** (volume, spend, weight, distance). They are included in entity/canonical counts where the contract requires it.

### Canonical Entity Resolution

For contact/people domains:
- Group raw rows into clusters representing the same person (match on identity fields).
- Within each cluster, select a survivor row (the row from the most authoritative source, or the row with the richest contact data).
- Resolve canonical fields (name, email, phone, city, consent, status) by source-system precedence. When sources disagree, apply the precedence order declared in the task materials or inferred from source metadata.

### Control Code Assignment

Control codes are opaque internal Asteria codes drawn from the enums in the answer template. Assign them by examining the evidence for each decision target:

- **Identity codes** (IC-*): reflect the degree of identity match confidence across sources — how many sources agree, whether all fields align, or whether conflicts exist.
- **Outreach codes** (OR-*): reflect contact-channel readiness — whether the entity has email, phone, both, or neither, and whether consent is granted.
- **Field provenance codes** (FP-*): reflect which source system(s) supplied the canonical field values and how they were resolved.
- **Reference policy codes** (RB-*): reflect how a reference alias was resolved — unambiguous single match, ambiguous multi-match, or unrecognized.
- **Source basis codes** (SB-*): reflect the snapshot provenance of a retained transaction — single-source, multi-source with retained authoritative, or multi-source with conflicts.
- **Ledger disposition codes** (LD-*): reflect the accounting treatment — clean accrual, mismatch accrual, quarantined, or other routing decisions.
- **Maintenance source codes** (MS-*): reflect the source system provenance of a maintenance event.
- **History route codes** (HR-*): reflect whether the event enters the clean history, is excluded, or is flagged.

**Inference methodology**: For each decision target, inspect the raw rows, identify which conditions are met, and map the condition to a code. Codes are drawn exclusively from the `enum` lists in the answer template. Never invent codes. When the mapping is ambiguous, use the most conservative code (highest level of scrutiny or lowest confidence).

## Numeric Precision

- All counts are exact integers.
- Financial amounts (USD spend) are rounded to 2 decimal places.
- Physical measures (liters, kilograms, kilometers) are rounded to 2 decimal places unless the answer template specifies otherwise.
- Rates (e.g., quarantine rate) follow the precision in the answer template (commonly 4 decimal places).
- Use standard rounding (round half up).

## Output Rules

1. Produce exactly **one JSON object**. No markdown fences, no commentary, no trailing text.
2. Match the answer template structure exactly — every `required` key must be present, no `additionalProperties` beyond the schema.
3. All arrays with a declared `minItems`/`maxItems` must contain exactly that many elements.
4. Sorting:
   - String lists: **lexicographically ascending** (standard string sort).
   - Object arrays: by the primary key declared in the template or case scope, ascending unless "DESC" is specified.
   - Rankings: by the declared metric descending, with tie-breaking as specified in the case scope.
5. All IDs must match the `pattern` regex in the template. Use stable IDs from the public data — never fabricate IDs.

## Certification / Release Decision

Many tasks conclude with a status/action pair:

| Status | Action |
|---|---|
| `PASS` | `RELEASE` |
| `PASS_WITH_EXCEPTIONS` | `REVIEW_EXCEPTIONS` |
| `HOLD` | `BLOCK_AND_REMEDIATE` |

Apply thresholds from `case_scope.status_thresholds` or `case_scope.certification_gate`. When thresholds are not explicitly provided, infer from the quality metrics:
- Zero quarantine/mismatch events → `PASS` / `RELEASE`
- Issues present but below a stated rate threshold → `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`
- Hard failures (odometer regression, invalid timestamps, extreme values exceeding limits) → `HOLD` / `BLOCK_AND_REMEDIATE`

## Verification Checklist

Before submitting, confirm:
- [ ] Every required key from the answer template is present.
- [ ] All array cardinalities match the template constraints.
- [ ] All enum values are drawn from the template's allowed lists.
- [ ] Sorting follows the declared ordering rules.
- [ ] Numeric precision matches the template.
- [ ] Quarantined records are excluded from normalized totals but included in counts where the contract requires.
- [ ] The authoritative snapshot ID is recorded in the output.
- [ ] No IDs are fabricated — every ID comes from the public data or the case scope.
