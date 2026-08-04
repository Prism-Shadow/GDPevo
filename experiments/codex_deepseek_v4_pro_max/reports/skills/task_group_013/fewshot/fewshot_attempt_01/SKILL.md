## Overview

This skill equips an agent to complete healthcare intake coordination tasks against the **Cedar Ridge Intake Coordination Portal**, a REST API that surfaces patient records, referrals, transfers, documents, chart data, clinical programs, ICD metadata, and a read-only SQL query endpoint. The portal is shared across multiple intake workflows: primary care access verification, specialty referral readiness audits, dialysis transfer review, chronic-care enrollment panels, and referral-to-chart activation.

Use this skill whenever a prompt references the Cedar Ridge Intake Coordination Portal, a `<TASK_ENV_BASE_URL>` placeholder, or any intake/referral/transfer/program task that follows the answer-template pattern described below.

## Workflow

### 1. Resolve the environment

- Locate `environment_access.md` in the working directory.
- Read the full contents of `environment_access.md`.
- Extract the base URL from the line that starts with `GDPEVO_ENV_BASE_URL=` (or the equivalent key). Assign this value as `BASE_URL`.
- Note every allowed endpoint and its method. The available endpoints typically include:
  - `GET /` — portal root / health check
  - `GET /patients` — list all patients
  - `GET /patients/{patient_id}` — single patient
  - `GET /referrals` — list all referrals
  - `GET /referrals/{referral_id}` — single referral
  - `GET /transfers` — list all transfers
  - `GET /transfers/{transfer_id}` — single transfer
  - `GET /documents` — list all documents
  - `GET /chart/{patient_id}` — chart data for a patient
  - `GET /programs/{program_code}/candidates` — candidates for a program
  - `GET /icd/{code}` — metadata for an ICD-10 code
  - `GET /pharmacies` — pharmacy network listing
  - `POST /query` — read-only SQL query with `{"sql": "...", "params": [...]}`
- Confirm connectivity with `curl -s "$BASE_URL/"` before proceeding.

### 2. Understand the task

- Read the task `prompt.txt`. Identify:
  - The task type (access verification, referral audit, transfer review, enrollment panel, chart activation).
  - The target roster / batch / program code.
  - The list of patient IDs, referral IDs, or transfer IDs in scope.
  - Any special business rules mentioned.
- Read `payloads/answer_template.json`. Treat every field as a mandatory output constraint:
  - **Top-level keys** — all required keys must appear in the final JSON.
  - **Enums** — use only the `allowed_values` listed; do not invent new ones.
  - **Ordering** — obey any `ordering` directive (e.g., "ascending by patient_id", "alphabetical by doc_type", "unordered set").
  - **Required patient/referral IDs** — every ID listed under `required_patient_ids` or equivalent must have a result row.
  - **Constant values** — if a field has `required_value` or `constant`, output that exact value unchanged.
- If the template references data that must come from the portal (e.g., `requested_service_date` from a roster record), note where each piece of data lives.

### 3. Gather data from the portal

Use the endpoints documented in `environment_access.md`. Always prefer targeted GET calls first; use `POST /query` for cross-entity joins or bulk filtering.

**Recommended data-gathering sequence:**

1. **Discover schema with SQL.** Call `POST /query` with `{"sql": "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name", "params": []}` to list all tables and their columns. Use `PRAGMA table_info(tablename)` to inspect column names and types. This reveals entity relationships (foreign keys), field names used in SQL, and how tables join.

2. **Fetch entity records.** For each entity type needed (patients, referrals, transfers, documents, chart, programs), call the corresponding `GET` endpoint. For known IDs, call the single-resource endpoints directly (e.g., `GET /patients/{patient_id}`). For bulk reads, call the list endpoints (e.g., `GET /patients`, `GET /referrals`) and filter client-side, or use `POST /query` with a `WHERE` clause.

3. **Resolve codes and metadata.** For ICD-10 codes found on referrals, call `GET /icd/{code}` to obtain chapter, description, and laterality. For pharmacy network checks, call `GET /pharmacies` to build a lookup set.

4. **Reconcile with SQL when needed.** When a business rule requires checking relationships across entities (e.g., "is this insurance_id shared by two different patients?"), write a targeted SQL query via `POST /query`.

### 4. Apply business rules

Each task type has its own business logic. Apply the rules consistently based on the portal data:

**Insurance / coverage:**
- `valid` — coverage is active and service line is included.
- `invalid` — coverage has expired, is pending, or the service line is excluded.
- `missing` — no insurance record exists for the patient.

**Prescription / PBM:**
- `valid` — prescription benefit is active and policy matches.
- `invalid` — PBM record exists but is invalid (policy mismatch, expired).
- `missing` — no PBM record.

**Pharmacy network:**
- Compare the patient's preferred pharmacy against the `/pharmacies` endpoint results.
- `in_network` — pharmacy is present and network status shows in-network.
- `out_of_network` — pharmacy is present but out-of-network.
- `unknown` — no pharmacy record or unrecognized pharmacy identifier.

**Lifestyle risk:** derive from patient chart or intake data. Use documented thresholds (e.g., smoking status, BMI ranges, activity level) present in the portal records.

**Overall risk:** aggregate lifestyle risk, insurance gaps, clinical history, and chart completeness. Apply the portal's documented risk rules.

**Registration / readiness status:**
- `approved` / `ready` — no blockers; all criteria met.
- `hold` — incomplete data or pending items that can be resolved.
- `clinical_review` / `under_review` — clinical discrepancy or risk factors require review.
- `rejected` / `blocked` — hard blockers (expired coverage, excluded service line, missing critical documents, denied authorization).
- `admin_followup` — non-clinical issue (insurance anomaly, duplicate).

**Blocked reason codes:** assign codes only from the `allowed_values` in the answer template. A patient may have multiple codes. Typical mappings:
- `coverage_expired` — insurance end date is in the past.
- `coverage_pending` — insurance start date is in the future.
- `excluded_service_line` — the service line is not in the patient's covered services.
- `pbm_invalid` / `pbm_missing` / `pbm_policy_mismatch` — prescription benefit issues.
- `pharmacy_out_of_network` / `pharmacy_unknown` — pharmacy network issues.
- `emergency_contact_missing` / `missing_address` / `preferred_contact_unavailable` — contact data gaps.
- `overall_risk_high` — overall risk assessed as high.
- For referrals: `icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch`, `duplicate_referral`, `shared_insurance_anomaly`, `missing_records`, `missing_imaging`, `auth_blocker`, `already_scheduled`.
- For transfers: stale documents (any document past its freshness_limit_days relative to the requested start date), missing required documents.
- For programs: `consent_declined`, `consent_missing`, `chart_not_active`, `wrong_target_condition`, etc.

**Packet/document completeness (transfers):**
- Compare the documents attached to a transfer against a required-document checklist.
- Flag any missing required documents as `missing_required_documents`.
- For each received document, compute its age relative to the requested start date. If the age exceeds `freshness_limit_days`, flag it as stale.

**Duplicate handling:**
- Identify referrals with matching patient_id-plus-service combinations.
- Group them, designate a primary, and recommend `consolidate_to_primary` or `keep_separate`.

**Priority tiers:**
- `tier_1_immediate` — urgent clinical need or time-sensitive issue.
- `tier_2_short_term` — needs action within days, not hours.
- `tier_3_administrative` — paperwork, insurance verification, low urgency.

### 5. Build the output

- Start with the exact top-level keys from the answer template.
- Fill in constant fields (`task_id`, `batch_id`, `roster_id`, `program_code`) with the values specified in the template's `required_value` or `constant` field.
- For each patient/referral/transfer in scope, produce one result object containing every key listed under the item schema.
- Use only exact enum values from the template; do not abbreviate, rephrase, or invent.
- Order list items as specified (ascending ID, alphabetical, unordered-set — which means any stable order is fine but do not imply ranking).
- When a list directive says "unordered set", the order does not matter, but be consistent.

### 6. Compute summary/cohort counts

- Count `total_patients` (or `total_referrals`, `total_transfers`, `total_candidates`) as the number of entities in scope.
- Count by registration status, readiness status, risk level, decision, follow-up cadence, outreach channel, and monitoring package as specified.
- For breakdowns that require cross-tabulation (e.g., counts by urgency AND readiness status), generate one row per combination with a non-zero count.
- Every count key listed in the template must appear in the summary, even when the count is zero.

### 7. Validate and output

- Confirm every required top-level key is present.
- Confirm every patient/referral/transfer ID from the scope appears exactly once.
- Confirm all enum values are from the allowed set.
- Confirm ordering matches the template directives.
- Confirm all summary counts sum correctly.
- Output **only** the JSON object. Do not wrap in markdown fences, do not add prose before or after.

## Important constraints

- **Do not** include prose outside the JSON in the final response.
- **Do not** guess data values; every value must be derived from portal API responses or the answer template constraints.
- **Do not** skip entities: every patient, referral, or transfer in the declared scope must have a result row.
- **Do not** use field names or values that are not in the answer template's allowed sets.
- If a data point is unavailable from the portal, use the most appropriate "missing" or "unknown" enum value rather than `null`, unless the template explicitly allows `null`.
- Treat the answer template as the authoritative schema. When the prompt and template appear to conflict, the template's required keys and allowed values take precedence.

## Example curl patterns

```bash
# Health check
curl -s "$BASE_URL/"

# List all patients
curl -s "$BASE_URL/patients"

# Single patient
curl -s "$BASE_URL/patients/{patient_id}"

# List referrals
curl -s "$BASE_URL/referrals"

# Chart data
curl -s "$BASE_URL/chart/{patient_id}"

# ICD metadata
curl -s "$BASE_URL/icd/{icd10_code}"

# Pharmacy list
curl -s "$BASE_URL/pharmacies"

# Program candidates
curl -s "$BASE_URL/programs/{program_code}/candidates"

# SQL query — list tables
curl -s -X POST "$BASE_URL/query" \
  -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name","params":[]}'

# SQL query — join referrals with patients
curl -s -X POST "$BASE_URL/query" \
  -H 'Content-Type: application/json' \
  -d '{"sql":"SELECT * FROM referrals WHERE batch_id = ?","params":["{batch_id}"]}'
```

## Task type reference

The portal supports these intake workflows. When a prompt matches one of these patterns, apply the corresponding entity focus:

| Task type | Primary entity | Key endpoints |
|---|---|---|
| New Patient Access Verification | Patient + Insurance + Pharmacy | `/patients`, `/chart`, `/pharmacies`, `POST /query` |
| Referral Readiness Audit | Referral + Patient + Documents + ICD | `/referrals`, `/patients`, `/icd`, `/documents`, `POST /query` |
| Dialysis Transfer Review | Transfer + Documents + Chart | `/transfers`, `/documents`, `/chart`, `POST /query` |
| Chronic-Care Enrollment Panel | Program candidates + Chart | `/programs/{code}/candidates`, `/chart`, `/patients` |
| Referral-to-Chart Activation | Referral + Patient + Chart + Documents + ICD | `/referrals`, `/patients`, `/chart`, `/documents`, `/icd`, `POST /query` |
