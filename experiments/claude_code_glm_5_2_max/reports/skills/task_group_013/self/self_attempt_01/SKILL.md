---
name: cedar-ridge-intake-coordination
description: Solve Cedar Ridge Intake Coordination Portal tasks — query the read-only portal (REST + SQL), map the evidence to the supplied answer_template.json, and return a single JSON object. Use whenever a task names the Cedar Ridge Intake Coordination Portal and provides an answer_template.json: new-patient access verification (roster), referral readiness/activation audit (batch), dialysis transfer review (batch), or chronic-care enrollment panel (program).
---

# Cedar Ridge Intake Coordination

The Cedar Ridge Intake Coordination Portal is a shared, read-only store of intake,
referral, transfer, chart, and program data. A task in this family gives you a
**prompt** (`prompt.txt`) and an **answer template** (`input/payloads/answer_template.json`),
and asks for one JSON object built from portal evidence.

The work is always the same shape: **scope → gather → map → summarize → emit JSON**.
The rules below are reusable across every batch, roster, and program. Do not hardcode
any task-specific final values (statuses, reason codes, counts, dates) — derive every
value from the portal and the template.

## 1. Read the contract first

Before touching the network, read `prompt.txt` and `answer_template.json` end to end.
The template is the contract. From it, extract:

- **Scope identifier and entity list** — the `roster_id` / `batch_id` / `program_code`
  named in the prompt, plus which entities (patient_ids, referrals, transfers, candidates)
  must be covered. The prompt always supplies the identifier; the entity list comes from
  the portal (or from a roster payload, if one is staged).
- **Required top-level keys** and any **constant values** the template pins
  (`task_id`, `batch_id`, `roster_id`, `program_code`). Emit those constants verbatim.
- **Per-item keys** and the **controlled vocabulary** (`allowed_values` / `allowed`)
  for every enum, reason code, and blocker code. You may only emit values from these lists.
- **List ordering** per field — ascending by id, alphabetical by code, or "unordered set".
- **Summary count keys** — which buckets the cohort summary must contain (include zero counts).

## 2. Connect through the documented access only

Resolve the base URL from `environment_access.md` (it points at the running portal).
Use **only** the endpoints listed there — the REST `GET` collection plus `POST /query`
(read-only SQL). No authentication. Never call `/health` or any reset/reseed endpoint.
See `references/endpoint_catalog.md` for params and response shapes.

## 3. Scope, then gather evidence per entity

Filter by the prompt's scope identifier and ignore everything else. The portal contains
**distractor rows** (rows whose `notes`/`status_note` literally say "distractor") and rows
belonging to **other batches/rosters/programs**. Filter strictly on the scope identifier;
an out-of-scope row is noise even if it looks relevant.

Evidence-gathering pattern (pick REST or SQL per need — they expose the same tables):

- **List + filter**: `GET /referrals?batch_id=…`, `GET /transfers?batch_id=…`,
  `GET /programs/{code}/candidates`, `GET /patients?q=…`. List responses are paginated
  (`limit`, default low) — raise `limit` or page until you have the full scoped set.
- **Patient detail is the hub**: `GET /patients/{id}` aggregates coverage, pbm, pharmacies,
  lifestyle, clinical_history, rosters, referrals, transfers, documents, chart_artifacts,
  and program_candidates for that patient. Use it as the primary source for patient-scoped
  tasks instead of re-joining by hand.
- **Detail lookups**: `GET /chart/{id}` (active problems, meds/allergies, recent vitals/labs,
  chart artifacts), `GET /icd/{code}` (chapter, description, laterality, service_family),
  `GET /pharmacies` (network_status by pharmacy_id).
- **Reconcile with SQL**: `POST /query` with a JSON body `{"sql": "SELECT …"}`. Use it for
  cross-entity grouping (duplicates, shared insurance), counts, and joins across the full
  table set — see `references/data_model.md` for tables/columns. Response is
  `{columns, row_count, rows, truncated}`; check `truncated` and raise limits if set.

## 4. Map evidence → controlled values with deterministic rules

Apply the **same** rule to every entity so results are consistent and auditable. The
field-to-enum mappings are fixed per task family and live in `references/decision_rules.md`
(e.g. coverage → `insurance_status`; ICD `service_family` vs referral `service_line` →
`icd_chapter_mismatch`; `records_received`/`imaging_received` → missing-records/imaging
blockers; `auth_status` → auth blocker; `facility_capacity.open_chairs` → feasibility;
`existing_chart` + chart artifacts → `chart_action`). Never infer a status you cannot
trace to a field; when evidence is genuinely absent, use the template's "missing/unknown"
enum rather than guessing.

## 5. Detect cross-entity anomalies

Group across the scoped set, not per row:

- **Duplicate referrals**: same `patient_id` + same `service_line` + overlapping
  ICD/reason within the batch → one `duplicate_group`, pick a `primary_referral_id`,
  recommend `consolidate_to_primary` or `keep_separate`.
- **Shared insurance**: group referrals by `insurance_id`; an id shared across **different**
  `patient_id`s is an anomaly (`verify_distinct_patient_policy_id`), across the **same**
  patient is `legitimate_duplicate_same_patient`.
- SQL `GROUP BY … HAVING COUNT(*) > 1` is the reliable way to find both.

## 6. Ordering, IDs, and counts

- Order every list exactly as the template specifies. For "unordered set" arrays
  (reason codes, blocker codes, issue codes), emit a stable sorted order anyway so output
  is deterministic.
- Use **uppercase IDs exactly as the portal returns them** (`REF0035`, `P001`, `TR0026`).
  Do not reformat or lowercase.
- **Cohort summary must reconcile**: every count is an integer, every required bucket is
  present (zero where applicable), and totals add up
  (e.g. `total_patients` == sum of `counts_by_registration_status`).
  See `references/output_contract.md`.

## 7. Emit one JSON object, JSON only

The final answer is a **single JSON object** conforming to the template. No prose, no
markdown fences, no trailing commentary, no keys outside the template. Re-validate before
finalizing: every required key present, every enum value in `allowed_values`, every list
correctly ordered, every count correct, no pinned constant changed.

## References

- `references/endpoint_catalog.md` — portal endpoints, query params, response shapes.
- `references/data_model.md` — SQL tables/columns and the field → concept map.
- `references/decision_rules.md` — per-task-family evidence → enum/code mappings.
- `references/output_contract.md` — JSON discipline and the pre-submit self-check.
