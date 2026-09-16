---
name: cedar-ridge-intake
description: Use this skill whenever the user mentions Cedar Ridge, intake coordination, patient access verification, referral auditing or readiness, dialysis transfer review, chronic-care enrollment panels, chart activation, or any task that involves processing batches of patients through a healthcare intake portal. The skill covers the Cedar Ridge Intake Coordination Portal API, classification rules for patient registration, referral readiness, transfer packet review, program enrollment eligibility, and chart activation workflows. Trigger this even if the user only mentions a batch ID, roster ID, program code, or portal URL without explicitly naming Cedar Ridge.
---

# Cedar Ridge Intake Coordination

This skill equips a Codex solver to work with the **Cedar Ridge Intake Coordination Portal** — a shared REST API that exposes patient, coverage, pharmacy, referral, transfer, chart, document, program, ICD, and capacity data for healthcare intake workflows.

## When to Use This Skill

The skill applies whenever a task involves:
- Processing a patient roster, referral batch, transfer batch, or program candidate list through the portal
- Producing a structured JSON assessment from portal data
- Determining insurance coverage validity, PBM status, pharmacy network status
- Scoring lifestyle risk and overall risk
- Classifying registration status, referral readiness, transfer intake decisions, or enrollment dispositions
- Auditing ICD code discrepancies, duplicate referrals, shared insurance anomalies
- Evaluating chart completeness and activation needs
- Matching transfer packets against document freshness requirements and chair capacity

## How the Portal Works

All data lives behind a single base URL (provided as `<TASK_ENV_BASE_URL>` in prompts). The portal is read-only; every endpoint returns JSON. There is also a read-only SQL endpoint for cross-entity reconciliation.

The portal home page (`GET /`) is an HTML dashboard that documents the available search forms, but the real work uses the JSON API endpoints directly.

## Workflow Pattern

When a task arrives, follow this general sequence:

1. **Identify the batch/roster/program**. The prompt or payloads will name it (e.g., `NPI-JUN-01`, `ORTHO-JUN-01`, `DIAL-WINTER-01`, `DMHTN-2026A`).

2. **Fetch the entity list**. Use the list endpoint (`/patients`, `/referrals`, `/transfers`, `/programs/{code}/candidates`) filtered by the batch identifier to get all rows.

3. **For each entity, fetch its detail view**. The detail endpoints (`/patients/{id}`, `/referrals/{id}`, `/transfers/{id}`, `/chart/{id}`) return nested objects that include linked coverage, PBM, pharmacy, documents, clinical history, lifestyle, referrals, rosters, capacity, ICD metadata, and chart artifacts — all in one call. The detail view is almost always sufficient; avoid querying sub-resources separately unless the detail view is missing something.

4. **Cross-reference with metadata endpoints** as needed: `/icd/{code}` for ICD chapter/service-family/laterality, `/pharmacies` for network lookups, `/documents` for document searches by patient/transfer/referral.

5. **Use the SQL endpoint** (`POST /query` with `{"sql": "SELECT ..."}`) when you need to reconcile records across tables in one query — for example, finding all referrals that share an insurance ID, or listing roster rows for a specific roster.

6. **Apply the classification rules** from [references/classification-rules.md](references/classification-rules.md) to each entity. These rules determine insurance/prescription/pharmacy status, lifestyle and overall risk, registration/referral/transfer decisions, and blocked reason codes.

7. **Populate the output template**. Every task provides an `answer_template.json` payload with the required JSON shape. Read it carefully — it defines the exact keys, enum values, ordering rules, and summary aggregations needed.

8. **Return only the JSON**. Most prompts ask for JSON only, with no prose. Prefer `python3 -m json.tool` to validate before returning.

## Reference Files

Read these as needed — they hold the detailed rules and data schemas:

- **[references/data-model.md](references/data-model.md)** — Full portal API reference: every endpoint, path parameters, query parameters, response shapes, and entity relationships. Read this when you need to know what an endpoint returns or how to filter.
- **[references/classification-rules.md](references/classification-rules.md)** — All business rules: insurance status, PBM status, pharmacy network, lifestyle risk, overall risk, registration status, referral readiness, transfer intake decisions, program enrollment eligibility, chart activation, blocked reason codes, issue codes, priority tier assignment, and document freshness thresholds. This is the most important reference; read it for every task.

## General Guidance

**Parallelize data fetches.** The detail views for different entities are independent — fetch them concurrently. The list endpoint and metadata lookups can also happen in parallel.

**Respect the templates.** The `answer_template.json` is authoritative for output shape. Follow its enum sets, ordering rules, and key requirements exactly. Do not invent new status values or reason codes not listed in the template.

**Use the SQL endpoint for reconciliation.** When you need to join across entities (e.g., find patients with shared insurance, list all referrals for a batch), `POST /query` is often more efficient than fetching individual detail views and filtering client-side.

**Ordering conventions.** Unless the template says otherwise, sort patient/referral/transfer lists ascending by their ID field. Blocked reason codes and issue codes are treated as unordered sets.

**Null handling.** When a field is null in the portal, treat it as absent/unknown. When a template field allows null (e.g., `priority_tier`), use null only when the field genuinely does not apply.

**Distractors.** The portal contains records from other batches, rosters, and programs. Always filter by the target batch/roster/program identifier. The detail views may include referrals, transfers, or program candidates from other batches — ignore them unless they are directly relevant to the current task's batch.
