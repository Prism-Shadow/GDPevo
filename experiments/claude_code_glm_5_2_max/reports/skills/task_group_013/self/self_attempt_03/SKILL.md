---
name: cedar-ridge-intake-audit
description: Audit and reconcile a batch, roster, or program against the Cedar Ridge Intake Coordination Portal (REST + read-only SQL), then emit one template-conformant JSON object. Use when a task points at the Cedar Ridge portal and supplies an answer_template.json describing the required output shape.
---

# Cedar Ridge Intake Coordination — Batch Audit & Reconciliation

This skill solves a family of intake-coordination audit tasks against the **Cedar Ridge Intake Coordination Portal**. Each task scopes work to one identifier — a **roster** (new-patient access verification), a **referral batch** (readiness / activation audits), a **transfer batch** (dialysis packet review), or a **program code** (chronic-care enrollment panel) — and demands a single JSON object whose shape and controlled vocabularies are fixed by an `answer_template.json`.

The work is always: *read the template → pull the complete scoped record set → reconcile and cross-reference → classify each record with template-controlled values → aggregate cohort summaries → emit one JSON object that matches the template exactly.*

These instructions are reusable. They contain **no task-specific final values** (no patient classifications, no referral readiness, no computed counts). Apply the procedure to whatever scope key and template the task gives you.

## When to use

Use this skill when a task:
- Names the **Cedar Ridge Intake Coordination Portal** and gives a `<TASK_ENV_BASE_URL>` placeholder, **and**
- Hands you an `input/payloads/answer_template.json` (the output contract) and a scope key — a `roster_id`, `batch_id`, or `program_code`.

If either is missing, you do not have a Cedar Ridge intake-audit task — do not use this skill.

## Ground rules (read first)

1. **Resolve the base URL from `environment_access.md` only.** Do not invent a URL. The portal is on the network at the base URL recorded there (no auth). Use **only** the endpoints listed in that file. **Never** hit `/health` or any reset/reseed endpoint.
2. **The template is the contract.** Read `input/payloads/answer_template.json` *before* you query anything. It defines required top-level keys, per-record fields, every controlled vocabulary (`allowed_values`), list-ordering rules, and summary count buckets. Every value you emit must come from the template's allowed sets.
3. **One JSON object, no prose.** The final answer is a single JSON object. No commentary before or after. No extra fields. Use IDs exactly as the portal shows them (uppercase).
4. **Read any extra payload.** Some tasks include a second payload (e.g. a roster file listing target IDs and a note like "use the roster record in the environment for requested_service_date and service_line"). It tells you *where* to find data, not the values themselves.

## Critical portal gotchas (these cost correctness if missed)

- **GET list endpoints silently cap at 100 rows.** There is no `truncated` flag on GET responses, and the `count` field is the number *returned*, not the total. A batch with many documents, or the patients directory itself (which exceeds 100 rows), will be silently truncated. **Always** pass an explicit large `limit` (e.g. `?limit=1000`) **or** filter by `batch_id`/`patient_id`, and cross-check with a SQL `SELECT COUNT(*)`.
- **Distractor records are everywhere.** The portal mixes many batches/rosters. Out-of-scope records are deliberately present (often literally labelled "distractor"). Filter strictly to your scope key; never include a record whose `batch_id`/`roster_id`/`program_code` does not match.
- **The SQL body key is `sql`, not `query`.** `POST /query` with `{"query": ...}` returns `{"error":"sql is required"}`. Send `{"sql": "SELECT ..."}`. Check the `truncated` flag in the SQL response — if `true`, narrow the `WHERE` clause or split the query.
- **Endpoint ↔ SQL table names differ.** `/transfers` ↔ table `transfer_requests`; `/icd/{code}` ↔ `icd_codes`; `/programs/{code}/candidates` ↔ `program_candidates`; `/patients/{id}` bundles `patients`+`coverage`+`pbm`+`patient_pharmacy`/`pharmacies`+`lifestyle`+`clinical_history`+`chart_artifacts`+`documents`+`program_candidates`+`referrals`. See `reference/portal_endpoints.md`.

## Procedure

### Phase 1 — Parse the brief and the contract
1. Identify the **scope key and type**: `roster_id` (new-patient access), `batch_id` (referral readiness / activation, or transfer review), or `program_code` (enrollment panel). Note the literal value.
2. Read `answer_template.json`. Extract: required top-level keys; the per-record item schema and its `allowed_values`; list-ordering rules (ascending by id, alphabetical by code, or "unordered set"); the summary object's required count buckets; and any `required_value`/`constant` you must echo verbatim (e.g. `task_id`, `batch_id`, `roster_id`, `program_code`).
3. Read any second payload for IDs or data-location hints.
4. Note which entities the task needs (patients, referrals, transfers, documents, charts, ICD, pharmacies, programs, capacity) — that drives which endpoints you call.

### Phase 2 — Pull the complete, scoped record set
1. Fetch the **scoped list** for your entity, overriding the 100-cap: e.g. `GET /referrals?batch_id=<scope>&limit=1000`, `GET /transfers?batch_id=<scope>&limit=1000`, `GET /programs/<scope>/candidates`. For a roster, fetch roster rows via SQL: `SELECT patient_id, requested_service_date, service_line FROM intake_rosters WHERE roster_id='<scope>'`.
2. **Cross-check completeness**: run `SELECT COUNT(*) FROM <table> WHERE <scope column>='<scope>'` and confirm it equals the number of records you pulled. If a list still looks capped, switch to SQL for that set.
3. For each in-scope record, fetch the **detail bundle** that carries the per-record assessment data:
   - New-patient access (roster): `GET /patients/{id}` → `coverage` (insurance), `pbm` (prescription benefit), `pharmacies` (preferred-pharmacy network), `lifestyle` (lifestyle risk), `clinical_history` (overall risk), plus `emergency_contact_present`/`address`/`preferred_contact` for contact blockers.
   - Referral audits: `GET /referrals/{id}` → `referral` (service_line, urgency, auth_status, records_received, imaging_received, appointment_scheduled, insurance_id, icd10_code, diagnosis_description, referral_reason), `patient`, `icd` (chapter, service_family, laterality), `documents`.
   - Transfer review: `GET /transfers/{id}` → `transfer` (requested_start_date, modality), `patient`, `documents` (the packet), `capacity` (chair availability for the requested start).
   - Enrollment panel: `GET /programs/<code>/candidates` then `GET /chart/{id}` per candidate → `active_problems`, `recent_vitals_labs`, `meds_allergies`, `clinical_history` (recent_hospitalization, risk_flags), plus candidate fields `consent_status`, `adherence_score`, `existing_chart`, `target_condition`, `preferred_outreach`.
4. When an endpoint omits a field you need, fill it with a SQL join (e.g. `coverage.service_lines`, `pbm.status`, `documents.received_date`).

### Phase 3 — Reconcile and cross-reference (the audit layer)
- **Coding discrepancies (referral tasks):** for each referral, compare the ICD `chapter`/`service_family` against the referral's `service_line` (`icd_chapter_mismatch`), the ICD `description`/`laterality` against the referral narrative (`diagnosis_description`, `referral_reason`) (`narrative_mismatch`), and the ICD `laterality` against any laterality in the narrative (`laterality_mismatch`). Use `GET /icd/{code}` (or the `icd_codes` table) for the metadata.
- **Duplicates:** group referrals by `patient_id` (same patient, same service family). Designate the primary (earliest/lowest id) and recommend consolidation; non-duplicates stay separate.
- **Shared-insurance anomalies:** group by `insurance_id`; if one `insurance_id` maps to multiple distinct `patient_id`s, flag it; if it maps to the same patient across duplicate referrals, that is legitimate.
- **Blockers:** check `records_received`, `imaging_received`, `auth_status` (pending/denied/not_submitted), and `appointment_scheduled` (already-scheduled referrals need review, not re-booking).
- **Transfer packet completeness & freshness:** assemble the packet from `documents` for the `transfer_id`; compare against the required doc set in the template; for doc types the template marks as freshness-sensitive, compare `received_date` to the per-doc freshness limit and list stale ones with their limit.
- **Capacity feasibility:** sum `open_chairs` for the `requested_start_date` + `modality` across locations (the `/transfers/{id}` `capacity` bundle, or the `facility_capacity` table). Feasibility combines packet-readiness with capacity availability per the template's feasibility enum.
- **Enrollment eligibility:** check active DM/HTN diagnosis, consent status, chart currency/active-problems/vitals/labs/meds recency, recent hospitalization/ED and adherence (high-touch triggers), CKD (biweekly monitoring), and target-condition match.

### Phase 4 — Classify each record with template-controlled values
Map the evidence to the enum values the template allows — **never invent codes**:
- Access verification: `insurance_status`, `prescription_status`, `pharmacy_status`, `lifestyle_risk`, `overall_risk`, `registration_status`, and the `blocked_reason_codes` set.
- Referral audits: `readiness_status` (ready/blocked/under_review/admin_followup), `issue_codes`/`blocker_codes`, `priority_tier`.
- Transfer review: `packet_completeness_status`, `feasibility`, `final_intake_decision`, `next_contact_owner`, `next_contact_route`.
- Enrollment panel: `eligible`, `enrollment_status`, `reason_codes`, `follow_up_cadence`, `missing_chart_artifacts`, `outreach_channel`, `initial_monitoring_package`.
Apply the task's domain decision logic (e.g. `overall_risk_high` → hold/clinical_review; auth denied or missing records → blocked; consent declined → reject). If evidence doesn't cleanly fit, choose the closest allowed value and keep summary counts consistent with the per-record choices.

### Phase 5 — Aggregate cohort summaries
- Derive every summary count **from the per-record classifications** in Phase 4 — do not recompute independently.
- Buckets must reconcile: the sum of each status/risk/decision bucket equals the total record count. Cross-tabs (e.g. `counts_by_urgency_and_status`) must sum to the same total. All counts are integers.
- Include exactly the summary keys/buckets the template lists — no more, no less.

### Phase 6 — Emit and self-validate
1. Build one JSON object with exactly the template's required top-level keys.
2. Set the scope/identity fields (`task_id`, `batch_id`, `roster_id`, `program_code`) to the template's `required_value`/`constant`, verbatim.
3. Order every list as the template specifies. Treat reason/blocker/issue code arrays as **unordered sets**; order id lists **ascending**; order stale-document and artifact lists **alphabetically**.
4. Use only `allowed_values`. No extra fields. No prose outside the JSON.
5. Run the `reference/output_checklist.md` before submitting: enums in-range, required keys present, lists ordered, distractors excluded, summary buckets sum to totals, and the records-reviewed count matches the SQL scope count.

## Reference files
- `reference/portal_endpoints.md` — every endpoint's request/response shape, the SQL endpoint, the REST↔SQL table map, and the 100-cap / distractor / `truncated` details.
- `reference/output_checklist.md` — pre-submit validation steps for template conformance.

## Scope of this skill
This skill covers the five training archetypes — new-patient access verification, orthopedic referral readiness, dialysis transfer review, chronic-care enrollment panel, and pulmonary referral-to-chart activation — and generalizes to any future Cedar Ridge intake-audit task that supplies a scope key and an `answer_template.json`. It encodes the procedure and portal behavior only; it does **not** contain any task's computed answers.
