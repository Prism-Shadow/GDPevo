# Cedar Ridge Intake Coordination — Agent Operating Procedure

## Purpose

This skill covers the reusable workflow for completing Cedar Ridge healthcare intake coordination tasks. Each task instance provides a natural-language prompt, an answer template JSON schema, and optionally additional input payloads. The agent queries a REST + SQL API to gather records, reconciles data across endpoints, applies business rules encoded in the template's controlled vocabularies, and returns a single JSON object conforming exactly to the template.

Do **not** hard-code task-specific values (roster IDs, batch IDs, patient lists, program codes, dates). Read them from the prompt and template. All tasks follow the same skeleton; this document describes the skeleton.

---

## Phase 1 — Orient

### 1.1 Read the environment manifest

Read `environment_access.md` (project root, or at the path noted in the prompt). It supplies:

- `base_url` — the root of the coordination portal API.
- `allowed_endpoints` — the exact HTTP method + path combinations available.
- Any credential or access notes.

Substitute every occurrence of `<TASK_ENV_BASE_URL>` in the prompt and any payload with the `base_url` from this file. No other base URLs are valid.

### 1.2 Read the prompt

The prompt (`prompt.txt`, or the path given) names:

- The task type (access verification, referral audit, transfer review, enrollment panel, referral-to-chart activation, etc.).
- The target batch/roster/cohort identifier.
- Any extra input payloads (e.g., a roster file or candidate list path).
- The output template path (`input/payloads/answer_template.json` or as specified).

### 1.3 Read the answer template

The answer template is the **source of truth** for every field, type, allowed value, ordering, and required key in the final output. Read it before querying the API — it tells you what to look for.

Pay attention to:

| Template feature | How to apply |
|---|---|
| `required_top_level_keys` | Every key in this list must appear in the final object. |
| `type: "enum"` with `allowed_values` / `allowed` | Only these exact strings may appear in that field. Never invent codes. |
| `type: "list"` with `ordering` | Sort as specified: `ascending <field>`, `alphabetical by <field>`, or `unordered set` (any order, no duplicates). |
| `required_value` / `expected_value` / `constant` | The field must hold this exact value. Copy it verbatim. |
| `format: "YYYY-MM-DD"` | All dates must use ISO-8601 calendar-date strings. |
| `numeric_precision: "integer counts"` | Summary counts are integers, never floats. |
| `type: "boolean"` | Use JSON `true` / `false` (not strings). |
| `type: "integer_or_null"` | The field is either a whole number or JSON `null`. |
| `type: "enum_or_null"` | The field is one of the allowed strings or JSON `null`. |
| `item_required_keys` | Every element in a list of objects must include these keys. |

### 1.4 Read additional input payloads

If the prompt or template references extra payload files (e.g., `target_roster.json`), read them. They may supply the target patient/referral list, service dates, or other task-scoped parameters. Incorporate those values when assembling the output (e.g., `requested_service_date` from the roster record).

---

## Phase 2 — Gather

### 2.1 Choose endpoints

From `environment_access.md`, the standard endpoints are:

| Method | Path | Typical use |
|---|---|---|
| `GET` | `/` | Health check / portal root. |
| `GET` | `/patients` | List all patients. |
| `GET` | `/patients/{patient_id}` | Single patient profile, insurance, demographics. |
| `GET` | `/referrals` | List all referrals (specialty intake batches). |
| `GET` | `/referrals/{referral_id}` | Single referral: ICD codes, urgency, status, documents, authorizations. |
| `GET` | `/transfers` | List all transfers (dialysis, facility transfers). |
| `GET` | `/transfers/{transfer_id}` | Single transfer: packet documents, requested start, patient, receiving facility. |
| `GET` | `/documents` | List all documents. Filter or correlate with patient/transfer IDs from other endpoints. |
| `GET` | `/chart/{patient_id}` | Patient chart: active problems, vitals, labs, medications, allergies, consent status. |
| `GET` | `/programs/{program_code}/candidates` | Candidates for a chronic-care program identified by program code. |
| `GET` | `/icd/{code}` | ICD-10 code metadata: chapter, description, laterality when applicable. |
| `GET` | `/pharmacies` | Pharmacy directory with network status. |
| `POST` | `/query` | Read-only SQL endpoint. Send `{"query": "<SQL>"}`. Use for cross-entity reconciliation when REST endpoints alone are insufficient. |

Only use endpoints listed in the manifest. Do not guess URLs.

### 2.2 Fan-out strategy

1. **Fetch the batch-level collection first** (e.g., `GET /referrals`, `GET /transfers`, `GET /programs/{code}/candidates`, `GET /patients`). Filter client-side to the target batch/roster.
2. **Drill into each record** — for each referral, transfer, or patient in the batch, fetch its detail endpoint and its associated chart (`GET /chart/{patient_id}`).
3. **Resolve code metadata** — for every ICD-10 code encountered, call `GET /icd/{code}` to retrieve chapter and laterality.
4. **Resolve pharmacy data** — when insurance or prescription benefit checks require network status, consult `GET /pharmacies`.
5. **Pull documents** — `GET /documents` and correlate by patient_id, transfer_id, or referral_id to assess completeness.

### 2.3 Use POST /query for reconciliation

When you need to join across entities or verify consistency, use the SQL endpoint:

```
POST /query
{"query": "SELECT ..."}
```

This is especially useful for:
- Finding referrals that share the same insurance policy across different patients.
- Listing documents associated with transfers or referrals.
- Checking for duplicate referrals (same patient, same specialty, overlapping dates).

The exact query syntax depends on the portal's schema. Explore with `SELECT * FROM <table> LIMIT 1` first to discover column names.

---

## Phase 3 — Reconcile

Apply business rules derived from the template's controlled vocabularies and the task prompt. These are the **reusable rule categories**; the specific codes and thresholds come from the template.

### 3.1 Insurance and benefits verification

- Compare each patient's insurance fields against the `valid` / `invalid` / `missing` enum in the template.
- Check prescription benefit (PBM) validity using the template's reason codes.
- Cross-reference the patient's pharmacy against the `/pharmacies` directory to determine `in_network` / `out_of_network` / `unknown`.

### 3.2 Clinical coding and narrative consistency

- For each referral, compare its ICD-10 codes against:
  - The ICD metadata (`/icd/{code}`) — chapter should match the referring specialty.
  - The referral narrative/description — the condition described should be consistent with the codes.
  - Laterality — if the code has a laterality component, it must match the narrative and the body site.
- Flag discrepancies using the issue codes from the template.

### 3.3 Duplicate detection

- Group referrals by patient + specialty + overlapping date windows.
- For each group, decide `consolidate_to_primary` vs `keep_separate` based on whether they are true duplicates or distinct episodes of care.
- Include a `primary_referral_id` (the one to keep) in each group.

### 3.4 Document / packet completeness

- For transfers and referrals, enumerate the required document types from the template.
- Compare against documents returned by the API; flag any missing.
- Check document freshness: each document type may have a `freshness_limit_days` in the template. If `received_date` is older than that limit, flag as stale.

### 3.5 Authorization status

- Check the authorization field on each referral.
- Map to the template's auth status enum (`pending`, `denied`, `not_submitted`).
- A denied or not-submitted authorization is a blocker.

### 3.6 Capacity and scheduling feasibility

- For transfers: compare `requested_start` date against facility chair capacity.
- Map to the capacity/feasibility enum in the template.

### 3.7 Chart activation readiness

- For referrals moving to scheduling: check whether the patient's chart exists and contains all required artifacts (demographics, active problems, medications, allergies, vitals, labs, consent).
- Chart action is `create_chart`, `update_chart`, or `no_chart_action` depending on what's missing.

### 3.8 Risk stratification

- When the template includes risk fields (`lifestyle_risk`, `overall_risk`), assess from patient chart data: vitals, labs, diagnoses, recent utilization, social history.
- Map to the template's `low` / `medium` / `high` enum.

### 3.9 Program eligibility

- For enrollment panels: each candidate is eligible (boolean) based on whether they meet the program's target condition criteria, have an active chart, and have not declined consent.
- Map to `enroll` / `hold` / `reject` based on eligibility + completeness.
- Assign reason codes, follow-up cadence, outreach channel, and monitoring package per the template's allowed values.

---

## Phase 4 — Assemble

### 4.1 Build the JSON skeleton

Start from the `required_top_level_keys` in the template. Populate each key in order.

### 4.2 Populate list fields

- Sort every list as specified by its `ordering` directive.
- For unordered sets, use any stable order but treat duplicates as set membership.
- Include every item identified in Phase 3. Empty lists use `[]`, never `null`.

### 4.3 Populate enum fields

- Use **only** strings from the field's `allowed_values` / `allowed` array.
- If a template defines `enum_or_null`, use `null` when no value applies (do not invent a placeholder string).

### 4.4 Build cohort summaries

Compute counts after all per-item results are finalized. Every count must reconcile with the item-level data. Common summary structures:

- `counts_by_<dimension>` — an object whose keys are enum values and values are integer counts.
- `total_<entity>` — the cardinality of the batch.
- Cross-tabulations — for compound summaries, produce the Cartesian product of the two dimensions, each entry with its count.

Double-check: sum of all status counts must equal `total_<entity>`. Sum of risk counts must equal the total. If any count does not add up, revisit the item-level data.

### 4.5 Include fixed fields

Copy `required_value` / `expected_value` / `constant` fields exactly from the template. The `task_id` (or equivalent identifier) must match the template's expected value.

---

## Phase 5 — Validate

Before returning, verify:

1. **All `required_top_level_keys` are present** in the output object.
2. **Every `required_value` / `expected_value` / `constant` matches** the template exactly.
3. **Every enum field** contains a value from its `allowed_values` / `allowed` list (or `null` when `enum_or_null`).
4. **Every list is ordered** as specified. Uppercase IDs match the portal exactly (do not downcase).
5. **All dates** are in `YYYY-MM-DD` format.
6. **Summary counts are integers** and reconcile with the item-level data.
7. **No prose, markdown, or explanation** appears outside the JSON object. The final response is the raw JSON only, unless the prompt explicitly allows wrapping.
8. **No extra keys** beyond those defined in the template. Do not add helper fields, comments, or debug data.

---

## Common pitfalls

- **Premature output**: Do not start writing JSON until all API calls are complete and all cross-references are resolved. Incomplete data leads to incorrect summaries.
- **Invented codes**: Never guess a reason code, status, or category. If the template does not list a value that fits, re-read the data — the correct mapping is within the allowed set.
- **Wrong base URL**: Always resolve `<TASK_ENV_BASE_URL>` from `environment_access.md`. Hard-coding `localhost` or a different port will fail.
- **ID casing**: Referral IDs, patient IDs, roster IDs, and batch IDs are case-sensitive. Preserve casing exactly as returned by the API.
- **SQL discovery**: The `POST /query` endpoint schema is not documented in advance. Use `SELECT * FROM <table> LIMIT 1` to explore before writing complex joins.
- **Stale freshness**: When a document has a `freshness_limit_days`, compute staleness as `(current_date - received_date) > freshness_limit_days`. Use the current date from context (today's date), not an arbitrary constant.
- **List ordering mismatch**: "Ascending by referral_id" means lexical sort on the ID string, not insertion order. Verify before finalizing.
- **Empty vs null**: An empty list is `[]`. An absent value is `null` (only when `enum_or_null` or `integer_or_null` permits it). Do not use `null` for required list fields.

---

## Supporting files

- `environment_access.md` — base URL and allowed endpoints (project root or per-instance).
- `input/payloads/answer_template.json` — output schema, controlled vocabularies, ordering rules.
- Additional payloads (e.g., `target_roster.json`) — task-scoped parameters referenced by the prompt.
