## When to Use

Use this skill when working with the **Cedar Ridge Intake Coordination Portal**, a healthcare-intake REST API for verifying patient access, auditing referrals, reviewing transfer requests, and preparing chronic-care enrollment panels. The portal surfaces patient records, referral entries, transfer packets, chart data, ICD metadata, document flags, authorization fields, pharmacy networks, program candidates, and facility capacity through discrete GET endpoints and a read-only SQL query interface.

## Environment Setup

The portal base URL is injected via the placeholder `<TASK_ENV_BASE_URL>`, which must be replaced before any network call. In training and evaluation environments this resolves to `http://task-env:9013/`. All endpoints listed below are relative to that base URL. No authentication headers are required.

## Available API Endpoints

### GET Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Portal root; returns the available endpoint index / health check. |
| `GET /patients` | List all patients. |
| `GET /patients/{patient_id}` | Detail for one patient (includes demographics, insurance, pharmacy, risk, contacts). |
| `GET /referrals` | List all referrals. |
| `GET /referrals/{referral_id}` | Detail for one referral (includes ICD codes, documents, authorization, scheduling). |
| `GET /transfers` | List all dialysis transfer requests. |
| `GET /transfers/{transfer_id}` | Detail for one transfer (includes packet documents, requested start, capacity data). |
| `GET /documents` | List all document records. |
| `GET /chart/{patient_id}` | Chart record for a patient (problems, vitals, labs, medications, allergies, consent). |
| `GET /programs/{program_code}/candidates` | Candidate list for a chronic-care program. |
| `GET /icd/{code}` | ICD-10 metadata for a code (chapter, description, laterality indicators). |
| `GET /pharmacies` | List all pharmacies with network membership information. |

### SQL Query Endpoint

```
POST /query
Content-Type: application/json
Body: {"sql": "<string>", "params": ["<value>"]}
```

The SQL endpoint is **read-only**. Use it to explore the schema, cross-reference records, or aggregate data that spans multiple GET resources. Always begin a new session by discovering the available tables:

```
curl -s -X POST '<TASK_ENV_BASE_URL>/query' \
  -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT name FROM sqlite_master WHERE type = ? ORDER BY name","params":["table"]}'
```

## General Workflow for Portal Tasks

1. **Read the prompt and answer template** — the task prompt describes the business goal, and `answer_template.json` defines the exact output schema. The answer template is the single source of truth for field names, enum values, ordering rules, and required keys.

2. **Exploratory queries** — use `GET /` to verify connectivity, then issue targeted GET requests or SQL queries to discover the scope of data relevant to the task (e.g., filter referrals by batch, list program candidates, pull patient charts).

3. **Reconcile and evaluate** — for each record, cross-check related entities:
   - Referral → patient identity, ICD code metadata, document flags, authorization status
   - Patient → insurance validity, pharmacy network, lifestyle/overall risk scores, chart completeness
   - Transfer → packet document completeness, document freshness/staleness, requested-start vs. chair capacity
   - Program candidate → eligibility criteria, chart artifacts, consent status, monitoring needs

4. **Apply business rules** — determine readiness, registration, or enrollment disposition per record using the controlled vocabulary in the answer template. Blocked reason codes, issue codes, and action codes are always drawn from the template's allowed lists.

5. **Assemble the JSON response** — build the output object to match the answer template exactly. Include all required top-level keys, sort lists as specified, use only enumerated values, and provide cohort/count summaries.

## Answer Template Conventions

Every task includes an `answer_template.json` that defines the required output shape. Pay careful attention to these metadata cues:

- **`required_value` / `expected_value` / `constant`** — the field must carry that exact literal string.
- **`allowed_values`** — only values from this list may appear; no free-form text.
- **`type: "enum"` or `type: "enum_or_null"`** — the field must use one of the listed values (or `null` when permitted).
- **`ordering`** — lists must follow the specified sort (e.g., "ascending referral_id", "ascending patient_id", "alphabetical by code", "highest priority first"). Unordered-set fields treat arrays as sets; produce a deterministic order but do not depend on order for correctness.
- **`required_top_level_keys` / `required_keys`** — every listed key must be present.
- **`numeric_precision` / `integer counts`** — count fields must be integers, never floats.
- **`format: "YYYY-MM-DD"`** — date fields use ISO 8601 date format.

## Common Ordering and Formatting Rules

- Referral and patient IDs are always uppercase (e.g., `R001`, `P003`).
- Lists of IDs default to ascending sort unless the template specifies otherwise.
- "Unordered set" arrays should be emitted in a deterministic order (sorted alphabetically or by ID) but their order is not semantically meaningful.
- Reason-code and blocker-code arrays are unordered sets.
- Count objects must include a key for every status/risk/category enumerated in the template, even when the count is zero.
- The final response must be pure JSON with no prose, commentary, or markdown wrappers.

## Portal Data Model

The portal exposes the following logical entities and their relationships:

- **Patient**: demographics, insurance carrier + status, prescription benefit (PBM) status, preferred pharmacy, lifestyle risk score, overall risk score, emergency contacts.
- **Referral**: batch association, referring provider, ICD-10 codes, clinical narrative, laterality, document flags (records, imaging), authorization status, scheduling status, urgency.
- **Transfer**: patient link, packet documents with received dates, requested start date, facility capacity snapshot.
- **Chart**: active problems, vitals, labs, medications, allergies, consent — per patient.
- **ICD Code**: chapter classification, description, laterality markers.
- **Pharmacy**: network membership.
- **Program Candidate**: patient link, eligibility signals, enrollment disposition.

Use SQL queries to join these entities when the GET endpoints do not provide a direct filtered view. For example, filter referrals by batch_id, list documents for a specific set of referral IDs, or aggregate patient counts by risk category.

## Common Task Patterns

### Patient Access Verification

Evaluate each patient's insurance validity, PBM status, pharmacy network, and risk scores. Registration status depends on these signals and any applicable blocked reason codes. Produce a cohort summary with counts by status and risk.

### Referral Audit / Readiness

For each referral in a batch, check ICD code chapter alignment with the service line, narrative consistency, laterality, duplicates, insurance anomalies, missing records/imaging, and authorization blockers. Classify each referral as ready, blocked, under_review, or admin_followup. Build duplicate groups, blocker sets, a ready-to-schedule list, and an action plan with priority tiers.

### Transfer Review

Assess each dialysis transfer's packet completeness (which required documents are present/missing) and document freshness (whether time-sensitive labs and exams have expired). Evaluate requested-start feasibility against open chair capacity. Assign final intake decisions and next-contact routing.

### Chronic-Care Enrollment Panel

For each program candidate, evaluate eligibility against clinical criteria (diagnosis match, recent hospitalization, ED visits, adherence), check chart artifact completeness, determine follow-up cadence and outreach channel, and assign an initial monitoring package. Produce a cohort summary with counts by status and category.

### Referral-to-Chart Activation

Reconcile a referral batch, identify clinical code discrepancies, duplicate groups, and blocker sets (authorization, records, imaging). For ready referrals, determine what chart artifacts need creation or update. Build a correspondence queue and a priority-ordered follow-up list for non-ready referrals.

## Error Handling

- If a GET endpoint returns an empty response or 404 for a known ID, treat the record as missing and reflect that in the output using the appropriate "missing" or "unknown" enum value.
- If an SQL query fails, check the table and column names against the schema; use `SELECT name FROM sqlite_master WHERE type='table'` and `PRAGMA table_info(<table>)` to verify.
- Always validate output against the answer template before submitting: confirm all required keys are present, all list lengths match expectations, all enum values are from the allowed set, and all count integers sum correctly.
