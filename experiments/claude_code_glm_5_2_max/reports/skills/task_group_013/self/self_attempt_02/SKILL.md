---
name: cedar-ridge-intake-audit
description: Audit and verify Cedar Ridge intake work (patient access verification, referral readiness, dialysis transfer review, chronic-care enrollment panels, referral-to-chart activation) against the Cedar Ridge Intake Coordination Portal. Use whenever a task points at the Cedar Ridge Intake Coordination Portal and asks for a single JSON object following an answer_template.json — covers roster/patient access, referral batch readiness, transfer packet review, program enrollment panels, and referral chart activation.
---

# Cedar Ridge Intake Audit

This skill completes Cedar Ridge intake-coordination audit tasks. Each task gives a prompt plus an `input/payloads/answer_template.json` that defines the **exact** JSON shape required, and asks you to query the Cedar Ridge Intake Coordination Portal and return **one JSON object, nothing else**.

The portal holds the source of truth; the template holds the output contract. Your job is: read the prompt → identify the work family → pull portal records → apply the decision rules → emit template-conformant JSON.

## Operating procedure (every task)

1. **Read the prompt.** Identify the work family and the target identifier:
   - Patient access verification → a **roster id** (e.g. `NPI-*`) + patient list + service line.
   - Referral readiness audit → a **batch id** (e.g. `ORTHO-*`, `PULM-*`) of referrals.
   - Dialysis transfer review → a **transfer batch id** (e.g. `DIAL-*`).
   - Chronic-care enrollment panel → a **program code** (e.g. `DMHTN-*`).
   - Referral-to-chart activation → a **batch id** of referrals.
2. **Read `answer_template.json` end to end.** It is the contract: required top-level keys, required fixed values (e.g. `task_id`, `batch_id`, `roster_id`, `program_code`), per-field enums, list orderings, and required count keys. Every value you emit must come from the template's allowed values; every list must use the template's ordering; every required key must be present.
3. **Resolve the base URL** from `environment_access.md` (the prompt's `<TASK_ENV_BASE_URL>` placeholder). Use only the endpoints listed there. Do **not** hit `/health` or any reset/reseed endpoint.
4. **Pull the data.** Prefer the read-only SQL endpoint (`POST /query`) for bulk/relational queries; use the REST endpoints for per-record detail. See `reference/schema.md` for the full table map and request formats.
5. **Apply the decision rules** for the work family (see `reference/decision_rules.md`). Compute each field from the raw records. Watch for **distractor records** that belong to a different service line/batch/program — only act on records relevant to the target identifier.
6. **Assemble the JSON** exactly to the template: fixed required values verbatim, enums only from allowed sets, lists ordered as specified, arrays that the template calls "unordered set" sorted for determinism (typically ascending by id or alphabetical by code — match the template's stated ordering where given).
7. **Emit JSON only.** No prose, no markdown fences, no commentary. A single JSON object.

## Portal access (essentials)

- Base URL: from `environment_access.md` (e.g. `http://task-env:9013/`). No auth.
- `GET /` — landing page (lists available batches/programs; useful for discovery).
- `GET /patients`, `GET /patients/{patient_id}` — patient identity + assembled record.
- `GET /referrals`, `GET /referrals/{referral_id}` — referral rows (supports `?batch_id=`).
- `GET /transfers`, `GET /transfers/{transfer_id}` — transfer requests (supports `?batch_id=`).
- `GET /documents` — packet documents (filter client-side by `referral_id`/`transfer_id`/`patient_id`).
- `GET /chart/{patient_id}` — assembled chart (active_problems, meds_allergies, recent_vitals_labs, chart_artifacts, clinical_history, patient).
- `GET /programs/{program_code}/candidates` — program candidate list.
- `GET /icd/{code}` — ICD-10 metadata (description, chapter, service_family, laterality).
- `GET /pharmacies` — pharmacy directory (network_status).
- `POST /query` — read-only SQL. Body `{"sql":"SELECT ..."}`. Returns `{"columns","rows","row_count","truncated"}`. **Use single-quoted SQL string literals** (e.g. `WHERE batch_id='<batch_id>'`) so inner quotes do not break the JSON payload. Only `SELECT`. If `truncated` is true, re-query with a tighter filter or `LIMIT` paging.

Full schema and column meanings: `reference/schema.md`.

## Output discipline (non-negotiable)

- **One JSON object.** No text before or after. No code fences.
- **Fixed required values** (task_id, batch_id, roster_id, program_code, requested_service_date source, etc.) must match the template exactly — copy them from the prompt/template, not from memory.
- **Enums only.** If a field has `allowed_values`, never invent a value outside that set. Unknown/missing → use the template's `unknown`/`none`/`null`/`not_applicable` option where one exists.
- **Ordering.** Lists whose ordering is specified (e.g. "ascending by referral_id", "alphabetical by code") must be sorted that way. "Unordered set" arrays should be sorted deterministically (ascending id / alphabetical) for reproducibility.
- **Counts are integers.** Summary count objects must include every required key (even zero counts) with integer values.
- **Dates** are `YYYY-MM-DD` strings.
- **IDs** are uppercase strings exactly as the portal returns them.

## Work families and where the rules live

Each family has its own decision logic in `reference/decision_rules.md`. Summary:

- **Patient access verification** (`NPI-*` roster, primary care intake): per patient compute `insurance_status`, `prescription_status`, `pharmacy_status`, `lifestyle_risk`, `overall_risk`, `registration_status`, `blocked_reason_codes`, plus a cohort summary. Driven by `coverage`, `pbm`, `patient_pharmacy`+`pharmacies`, `lifestyle`, `clinical_history`, `patients`, and the roster's `service_line`/`requested_service_date`.
- **Referral readiness audit** (`ORTHO-*` etc.): per referral compute `readiness_status`, `issue_codes`, `priority_tier`; plus batch-level `icd_discrepancies`, `duplicate_groups`, `shared_insurance_anomalies`, `blocker_sets`, `ready_to_schedule`, `action_plan`, and summary counts. Driven by `referrals`, `icd_codes` (for discrepancies), and the referral's own `records_received`/`imaging_received`/`auth_*`/`appointment_scheduled` flags.
- **Dialysis transfer review** (`DIAL-*`): per transfer compute packet `completeness`, `missing_required_documents`, `stale_documents`, `requested_start` feasibility vs chair capacity, `final_intake_decision`, `next_contact_*`, plus cohort summary. Driven by `transfer_requests`, `documents` (packet), `facility_capacity`, `patients`.
- **Chronic-care enrollment panel** (`DMHTN-*`): per candidate compute `eligible`, `enrollment_status`, `reason_codes`, `follow_up_cadence`, `missing_chart_artifacts`, `outreach_channel`, `initial_monitoring_package`, plus summary counts. Driven by `program_candidates`, `chart_artifacts`, `clinical_history`, `patients`. Program identity (e.g. DMHTN = diabetes+hypertension) determines the required target condition and diagnosis.
- **Referral-to-chart activation** (`PULM-*` etc.): per referral compute `readiness_status`+`blocker_codes`; plus `clinical_code_discrepancy_referrals`, `blocker_sets`, `duplicate_handling` (groups vs cleared), `ready_referral_chart_needs` (chart_action + artifacts_to_create), `correspondence_queue`, `priority_order`. Driven by `referrals`, `icd_codes`, `chart_artifacts`, `patients`.

## Important pitfalls observed

- **Distractor records.** A patient may carry an unrelated referral/transfer/program membership that does not belong to the target batch/roster/program. Filter strictly by the target identifier; ignore `notes` like "distractor referral".
- **`missing_records`/`missing_imaging` come from referral flags**, not from the `documents` table (referral readiness audits use `referrals.records_received` / `imaging_received`). The `documents` table is for transfer packets and chart artifacts.
- **ICD discrepancy = service-family mismatch.** Compare `icd_codes.service_family` to the referral's `service_line`; a code from another family (e.g. a cardiology code in a pulmonary batch) is a clinical code discrepancy. `narrative_mismatch`/`laterality_mismatch` additionally compare the code description/laterality to the referral narrative.
- **Duplicate vs cleared.** True duplicates share `(patient_id, icd10_code)` within the batch. Referrals merely *flagged* "possible duplicate" but with distinct keys are **cleared**, not duplicates.
- **Freshness limits are clinical constants, not in the portal.** Dialysis packet freshness windows must be applied per doc type (see `reference/decision_rules.md`); they are inferred standards, applied consistently.
- **Required values can be hidden in the environment.** `requested_service_date` and `service_line` for a roster live in `intake_rosters`, not the prompt — read them from the portal.

When a rule in `reference/decision_rules.md` is marked *(inferred rubric)*, it was distilled from the training data rather than read verbatim from the portal; apply it consistently so output is reproducible.
