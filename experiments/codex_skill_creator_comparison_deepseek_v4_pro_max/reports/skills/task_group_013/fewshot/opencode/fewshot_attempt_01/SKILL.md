---
name: cedar-ridge-intake
description: Query the Cedar Ridge Intake Coordination Portal REST API to complete healthcare intake-coordination workflows. Use this skill whenever the task involves the Cedar Ridge portal, Cedar Ridge intake, patient access verification, referral batch audits, dialysis transfer review, chronic-care enrollment panels, referral-to-chart activation, or any prompt that mentions a TASK_ENV_BASE_URL pointing to a Cedar Ridge Intake Coordination Portal. The skill documents every available endpoint, response shapes, and the decision-logic patterns needed to produce compliant JSON answers from portal data.
---

# Cedar Ridge Intake Coordination Portal

Use the shared read-only REST API at the base URL provided in the task prompt (typically `<TASK_ENV_BASE_URL>`) to retrieve patient, referral, transfer, chart, coverage, pharmacy, document, and program-candidate records. The portal also includes a read-only SQL endpoint for ad-hoc reconciliation.

Every task follows the same core pattern:

1. Read the answer template (always supplied as `input/payloads/answer_template.json` or described in the prompt) to understand the exact output shape and controlled vocabularies.
2. Pull all relevant records from the portal via the endpoints documented below.
3. Apply the decision logic for the workflow type (see [references/decision-logic.md](references/decision-logic.md)).
4. Assemble the JSON response using only values from the template's enumerated sets.
5. Return JSON only — no prose outside the JSON object unless the template or prompt explicitly allows it.

Do not guess at controlled values. Every status, reason code, tier, and channel must be drawn from the enumerated sets defined in the answer template. When the template specifies ordering (ascending by ID, alphabetical, unordered set), follow it exactly.

## Endpoint reference

Full field-level documentation lives in [references/api-reference.md](references/api-reference.md). The endpoints are:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Portal landing page (HTML) |
| GET | `/patients` | List/search patients |
| GET | `/patients/{patient_id}` | Full patient record with coverage, PBM, pharmacy, lifestyle, rosters, referrals, transfers, program candidates, chart artifacts, documents |
| GET | `/referrals` | List/search referrals (filter by `batch_id`, `service_line`) |
| GET | `/referrals/{referral_id}` | Single referral record |
| GET | `/transfers` | List/search transfers (filter by `batch_id`) |
| GET | `/transfers/{transfer_id}` | Single transfer record |
| GET | `/documents` | List/search documents |
| GET | `/chart/{patient_id}` | Patient chart with active problems, chart artifacts, medications/allergies, recent vitals/labs, clinical history |
| GET | `/programs/{program_code}/candidates` | Candidates for a chronic-care program |
| GET | `/icd/{code}` | ICD-10 metadata (chapter, description, laterality, service_family) |
| GET | `/pharmacies` | Pharmacy directory with network status |
| POST | `/query` | Read-only SQL (send `{"sql": "SELECT ..."}` in the request body) |

The `/patients/{patient_id}` endpoint is the richest — it returns a composite object containing `patient`, `coverage[]`, `pbm[]`, `pharmacies[]`, `lifestyle`, `clinical_history`, `rosters[]`, `referrals[]`, `transfers[]`, `program_candidates[]`, `chart_artifacts[]`, and `documents[]` all in one call. Prefer this endpoint when you need multiple facets of a patient at once.

## General workflow approach

### 1. Scope the data pull

Identify which records you need from the prompt. Common starting points:

- **Batch/roster ID given**: pull referrals or transfers filtered by that batch, then pull each referenced patient's full record.
- **Program code given**: pull the candidate list, then pull each candidate's full patient and chart records.
- **Roster ID given**: pull the roster from the SQL endpoint or patient records, then pull each patient.

Use the SQL endpoint (`POST /query`) when you need to cross-reference records that lack a direct REST filter. The SQL schema mirrors the REST response shapes — table names follow the same naming. Example tables include `intake_rosters`, `referrals`, `transfers`, `documents`, `patients`, `coverage`, `pbm`, `pharmacies`, `chart_artifacts`, `program_candidates`, `clinical_history`, `lifestyle`. Run `SELECT name FROM sqlite_master WHERE type='table'` to discover all available tables.

### 2. Pull all records in parallel

When you have multiple patient IDs, fetch them concurrently. The `/patients/{id}` endpoint gives you nearly everything you need per patient in one call. Supplement with `/chart/{id}` when the task needs detailed chart artifact data beyond what the patient endpoint provides, or `/icd/{code}` for ICD metadata.

### 3. Apply decision logic

See [references/decision-logic.md](references/decision-logic.md) for workflow-specific rules. Every workflow has a predictable shape:

- Pull records → evaluate each entity against criteria → assign statuses and codes from the template's allowed values → aggregate counts → return JSON.

The decision logic reference covers the five core workflow patterns seen in this portal: patient access verification, referral batch auditing, dialysis transfer review, chronic-care enrollment panels, and referral-to-chart activation.

### 4. Assemble the output

Follow the answer template exactly. Key conventions across all templates:

- **Lists ordered ascending by ID** unless the template says "unordered set" — in that case any order is fine but sort alphabetically for consistency.
- **Reason codes and blocker codes are unordered sets** — sort alphabetically for reproducibility.
- **Count fields are always integers.**
- **Null is used for fields with no applicable value** (e.g., `first_checkin_days: null` for not_applicable packages).
- **Empty arrays (`[]`) for empty lists**, never omit them.

### 5. Validate before returning

Before writing the final answer, spot-check:

- Every patient/transfer/referral ID from the input is represented.
- Every string value is from the template's allowed_values lists.
- All counts in the summary add up to the total.
- Array orderings match the template specification.

## Important portal behaviors

- The portal returns **all records unfiltered** when no query params are given. Always filter with `?batch_id=...` or `?q=...` when you know the scope.
- Patient IDs use the format `P` followed by a zero-padded number (e.g., `P001`, `P026`).
- Referral IDs use `REF` + zero-padded number. Transfer IDs use `TR` + zero-padded number.
- Document freshness/status is evaluated against the current simulated date implied by the environment — use the most recent `received_date` for each `doc_type` per patient.
- The SQL endpoint returns `{"columns": [...], "rows": [...], "row_count": N, "truncated": false}`.
- All endpoints return JSON; the root `/` returns HTML.

See [references/api-reference.md](references/api-reference.md) for complete field-by-field documentation of every endpoint response shape. See [references/decision-logic.md](references/decision-logic.md) for the decision rules that map raw portal data into the controlled vocabularies used in answer templates.
