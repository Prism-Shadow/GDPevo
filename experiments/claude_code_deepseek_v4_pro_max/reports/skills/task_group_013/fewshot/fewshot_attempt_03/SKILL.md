# Cedar Ridge Intake Coordination — Agent Skill

## Overview

This skill covers healthcare-intake audit, verification, and enrollment-panel tasks that run against the **Cedar Ridge Intake Coordination Portal** — a REST API serving patient, referral, transfer, document, chart, ICD, pharmacy, program-candidate, and SQL-query endpoints.

When you receive a task that references this portal, follow the workflow below. It is designed to be reusable across different batch types (new-patient rosters, referral audits, transfer reviews, chronic-care enrollment panels, and referral-to-chart activation).

---

## Step 1 — Parse the task prompt

Read the provided `prompt.txt` (or equivalent task description) and identify:

| Signal | What to extract |
|---|---|
| **Task family** | One of: new-patient access verification, referral audit, transfer review, chronic-care enrollment panel, referral-to-chart activation. |
| **Batch / roster / program identifier** | e.g. `NPI-JUN-01`, `ORTHO-JUN-01`, `DIAL-WINTER-01`, `DMHTN-2026A`, `PULM-JUN-02`. |
| **Answer template** | Path to the `answer_template.json` that defines the exact output shape, required keys, allowed enum values, list ordering rules, and summary-count keys. |
| **Relevant endpoints** | Which of the portal's endpoints are needed for this task family (see Step 2). |
| **Supplemental inputs** | Any additional payload files (e.g. `target_roster.json`) that list IDs or parameters. |

---

## Step 2 — Understand the API surface

All tasks use the same base URL, provided in the task prompt as `<TASK_ENV_BASE_URL>`. The full endpoint catalog is documented in `environment_access.md`:

| Method | Endpoint | Returns |
|---|---|---|
| `GET` | `/` | Portal root / health |
| `GET` | `/patients` | All patient records |
| `GET` | `/patients/{patient_id}` | Single patient record |
| `GET` | `/referrals` | All referral records |
| `GET` | `/referrals/{referral_id}` | Single referral record |
| `GET` | `/transfers` | All transfer records |
| `GET` | `/transfers/{transfer_id}` | Single transfer record |
| `GET` | `/documents` | All document metadata |
| `GET` | `/chart/{patient_id}` | Chart record for a patient |
| `GET` | `/programs/{program_code}/candidates` | Candidate list for a chronic-care program |
| `GET` | `/icd/{code}` | ICD-10 code metadata (chapter, description, laterality) |
| `GET` | `/pharmacies` | Pharmacy network directory |
| `POST` | `/query` | Read-only SQL query endpoint |

**Which endpoints to use by task family:**

- **New-patient access verification**: `/patients`, `/pharmacies`, `/chart/{patient_id}`, optionally `/query`.
- **Referral audit**: `/referrals`, `/patients`, `/icd/{code}`, `/documents`, `/query`.
- **Transfer review**: `/transfers`, `/patients`, `/documents`, `/query`.
- **Chronic-care enrollment panel**: `/programs/{program_code}/candidates`, `/patients`, `/chart/{patient_id}`, optionally `/query`.
- **Referral-to-chart activation**: `/referrals`, `/patients`, `/chart/{patient_id}`, `/icd/{code}`, `/documents`, `/query`.

Always fetch data from **all** relevant endpoints before beginning analysis. A full picture prevents silent errors.

---

## Step 3 — Fetch data from the portal

1. Resolve `<TASK_ENV_BASE_URL>` to the actual base URL (typically done by reading `environment_access.md`).
2. Use `curl` or an HTTP client to call every endpoint identified in Step 2.
3. For list endpoints (`/patients`, `/referrals`, `/transfers`, `/documents`, `/pharmacies`), fetch the full collection and filter client-side by the batch/roster identifier.
4. For single-resource endpoints, iterate over the IDs listed in the task's supplemental inputs (e.g. `target_roster.json`, or the IDs returned by a list endpoint filtered by batch).
5. For `/icd/{code}`, call it for every ICD-10 code that appears in the relevant referral or chart records.
6. For `/chart/{patient_id}`, call it for every patient in scope.
7. If direct endpoint data is insufficient or ambiguous, use `POST /query` with a SQL `SELECT` to reconcile records. The `/query` endpoint is read-only and accepts standard SQL.

---

## Step 4 — Read and internalize the answer template

The `answer_template.json` file is the authoritative specification for the output. Study it before writing any answer. Pay close attention to:

- **Required top-level keys** — every one must be present.
- **Enum allowed values** — never use a value outside the listed set. If you cannot determine the correct enum value from the data, re-examine the data; never invent values.
- **List ordering rules** — templates specify ordering (e.g. "ascending by patient_id", "ascending by referral_id", "alphabetical by code", "unordered set", "highest priority first"). Follow the ordering exactly.
- **Numeric precision** — integer counts only; no floats.
- **Nullability** — some fields allow `null`; others do not. The template indicates which with types like `"enum_or_null"` or explicit notes.
- **Constant / required_value fields** — some fields have a fixed value (e.g. `task_id`, `roster_id`, `batch_id`, `program_code`). Copy the required value exactly from the template or from the task inputs.

---

## Step 5 — Cross-reference and analyze

The core of every task is **cross-referencing records across endpoints**. Common patterns:

### Patient ↔ Insurance / Pharmacy
- Match each patient's insurance fields against known valid/invalid/expired patterns.
- Match each patient's pharmacy against the `/pharmacies` network directory to determine `in_network`, `out_of_network`, or `unknown`.

### Referral ↔ ICD metadata
- For each referral's ICD-10 code, call `/icd/{code}` to get the chapter.
- Compare the observed chapter against the expected chapter for the service line (e.g. orthopedics expects chapter M00-M99; a code in S00-T88 is a chapter mismatch).
- Check narrative descriptions and laterality fields for mismatches.

### Referral ↔ Documents
- Cross-reference referral IDs against `/documents` to identify missing records or missing imaging.
- Check authorization status fields on referrals.

### Transfer ↔ Documents ↔ Capacity
- For each transfer, check which required documents are present vs. missing.
- Check document received dates against freshness limits (e.g. 30 days for labs/vaccines, 365 days for history & physical).
- Compare requested start date against available chair capacity.

### Program candidates ↔ Chart
- For each candidate from `/programs/{program_code}/candidates`, fetch `/chart/{patient_id}`.
- Check for active DM/HTN diagnosis, recent vitals, recent labs, medication list, active problems, consent status.

### Duplicate detection
- Group referrals by patient ID, ICD code, and/or insurance ID to find duplicates.
- For shared insurance IDs across different patients, flag as anomalies needing verification.

### Risk assessment
- Combine insurance validity, PBM status, pharmacy network status, lifestyle factors, and missing contacts into an overall risk level.
- Use the template's allowed enum values for risk levels.

---

## Step 6 — Build the output JSON

Construct the answer by following the template structure **key by key, top to bottom**:

1. **Top-level identifiers** — fill in `task_id`, `batch_id` / `roster_id` / `program_code`, and any date fields from the task inputs or from data fetched from the portal.
2. **Per-entity results** — iterate over every entity (patient, referral, transfer, candidate) in the order specified by the template. For each entity, populate every required field using only the allowed enum values.
3. **Derived lists** — build lists like `icd_discrepancies`, `duplicate_groups`, `shared_insurance_anomalies`, `blocker_sets`, `ready_to_schedule`, `action_plan`, `correspondence_queue`, `priority_order` by applying the cross-reference rules from Step 5.
4. **Summary / cohort_summary** — compute integer counts for every key listed in the template's summary section. Every count key must be present, even if the count is zero. Verify that counts sum correctly (e.g. status counts should sum to `total_patients`).

**Critical rules:**

- Never include prose, explanations, or markdown outside the JSON object. The final response must be pure JSON.
- Use **only** the controlled values (enum members) defined in the template. If a value is not listed, it is not valid.
- Treat reason-code and blocker-code arrays as **unordered sets** unless the template specifies otherwise. Duplicate codes within a single entity's array are an error.
- Order entity lists exactly as the template specifies (typically ascending by ID).
- Every key declared as `required` in the template must appear in the output, even if its value is an empty list `[]` or zero count.
- For fields with a `required_value` or `constant` in the template, use that exact value — do not derive it from data.

---

## Step 7 — Validate before returning

Before finalizing:

1. Check that every `required_top_level_key` from the template is present.
2. Check that every per-entity `required_keys` / `item_required_keys` is present on every entity.
3. Check that every summary count key is present with an integer value.
4. Verify that list lengths match expectations (e.g. number of patient results equals `total_patients`).
5. Verify that summary counts are internally consistent (status counts sum to total; risk counts sum to total).
6. Spot-check enum values against the template's allowed lists — one typo invalidates the answer.
7. Confirm the output is valid JSON (no trailing commas, no unquoted keys).
