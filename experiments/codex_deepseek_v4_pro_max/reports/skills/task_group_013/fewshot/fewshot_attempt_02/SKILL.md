## When to use

Use this skill whenever the task involves the **Cedar Ridge Intake Coordination Portal** — a healthcare intake system that exposes patient, referral, transfer, chart, document, program, ICD, and pharmacy data through REST endpoints plus a read-only SQL query interface. This skill covers:

- Patient access verification (primary-care intake)
- Referral readiness audits (orthopedic, pulmonary, and similar service-line batches)
- Transfer review (dialysis and other facility transfer packets)
- Chronic-care enrollment panels (program-candidate eligibility and disposition)
- Referral-to-chart activation workflows

## Core principles

1. **Let the answer template drive the output.** Every task ships with an `input/payloads/answer_template.json` that defines the required JSON shape, allowed enum values, sort order, and mandatory keys. Read it first, produce output that matches it exactly, and never introduce values outside the template's controlled vocabularies.
2. **Explore the API before assuming anything.** The base URL for the portal is provided in the task prompt (typically as `<TASK_ENV_BASE_URL>`). Start every session by hitting `GET /` and inspecting what endpoints are live. The environment-access documentation lists standard endpoints, but the live server is authoritative.
3. **Use SQL only when REST can't give you the answer efficiently.** The `POST /query` endpoint accepts `{"sql": "...", "params": [...]}`. Use it for cross-table joins, aggregate counts, detecting duplicates, and reconciliation queries that would take many individual REST calls. Prefer parameterized queries.
4. **Preserve ordering rules from the template.** When the template says "ascending by patient_id," "ascending referral_id," or "alphabetical by code," follow that order in the output.

## API reference

All endpoints are relative to the provided base URL. The standard endpoints are:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | API root / discovery |
| GET | `/patients` | List all patients |
| GET | `/patients/{patient_id}` | Single patient record |
| GET | `/referrals` | List all referrals |
| GET | `/referrals/{referral_id}` | Single referral record |
| GET | `/transfers` | List all transfer requests |
| GET | `/transfers/{transfer_id}` | Single transfer record |
| GET | `/documents` | Document index or listing |
| GET | `/chart/{patient_id}` | Chart record for a patient |
| GET | `/programs/{program_code}/candidates` | Candidate list for a chronic-care program |
| GET | `/icd/{code}` | ICD-10 metadata for a given code |
| GET | `/pharmacies` | Pharmacy network listing |
| POST | `/query` | Read-only SQL endpoint |

The SQL endpoint accepts:
```json
{"sql": "<SQL string>", "params": ["<param1>", "<param2>", ...]}
```

To discover the database schema, start with:
```sql
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name
```
Then `PRAGMA table_info(<table>)` on any table of interest.

## Workflow for any intake task

### Phase 1 — Understand the ask

- Read the prompt (`input/prompt.txt`) to learn the batch/roster ID, service line, program code, or cohort scope.
- Read `input/payloads/answer_template.json` and note every required key, the sort order of lists, and all enumerated values.
- If an additional payload file exists (e.g., `target_roster.json`), read that too — it may specify the exact IDs to process.

### Phase 2 — Gather data

- Fetch the list-level resource first (e.g., `GET /referrals` or `GET /transfers`) to understand the full dataset.
- For each entity in scope, fetch its individual record by ID (`/referrals/{id}`, `/patients/{id}`, `/transfers/{id}`).
- Pull related resources: `GET /chart/{patient_id}` for chart data, `GET /icd/{code}` for ICD chapter/description metadata, `GET /documents` for document presence checks, `GET /pharmacies` for network lookups.
- Use `POST /query` for:
  - Finding which patients share the same insurance ID across different referrals
  - Counting entities grouped by status/category
  - Detecting duplicates (same patient, same service, overlapping dates)
  - Reconciling referral-to-patient joins when the REST responses are sparse
  - Checking document existence and date metadata in bulk

### Phase 3 — Analyze and decide

Apply the decision rules relevant to the task type (see sections below). For every decision output, use only the enumerated values defined in the answer template.

### Phase 4 — Produce the JSON answer

- Build the output JSON object matching the template's top-level keys.
- Sort all lists exactly as the template specifies.
- For unordered sets (reason codes, blocker codes, issue codes), output them in a consistent order (alphabetical or ascending) but do not attach meaning to the order.
- Fill every required key, using `null` or `[]` where the template permits them.
- Compute aggregate counts from the individual results — never hardcode them.
- Return **only** the JSON object. No prose, no markdown fences, no explanations.

## Decision rules by task type

### Patient access verification (primary care intake)

**Insurance status** is determined from the patient record and insurance-related fields. Map to one of: `valid`, `invalid`, `missing`.

**Prescription benefit (PBM) status** is determined from pharmacy benefit records. Map to: `valid`, `invalid`, `missing`.

**Pharmacy network status** is determined by checking the patient's preferred pharmacy against the network: `in_network`, `out_of_network`, `unknown`.

**Lifestyle risk** and **overall risk** are taken from patient chart data or computed from risk indicators in the record. Allowed: `low`, `medium`, `high`.

**Registration status** follows these rules:
- `approved` — insurance valid, PBM valid, pharmacy in-network, overall risk low
- `hold` — minor issues that can be resolved (e.g., missing contact info, pending coverage)
- `clinical_review` — at least one significant flag (out-of-network pharmacy, invalid PBM, high risk) but not all fatal
- `rejected` — hard blockers: expired coverage, excluded service line, multiple fatal flags

**Blocked reason codes** come from the controlled set in the template and describe each specific blocker affecting the patient.

### Referral readiness audit (orthopedic, pulmonary, etc.)

**ICD discrepancy detection:**
1. For each referral, extract the ICD-10 code.
2. Fetch `GET /icd/{code}` to get the ICD chapter/description.
3. Compare the chapter against the expected service-line chapter:
   - Orthopedic → M00-M99 (musculoskeletal)
   - Pulmonary → J00-J99 (respiratory)
   - If the chapter is unexpected, flag `icd_chapter_mismatch`.
4. Check the narrative/diagnosis description against the ICD code. If they describe different conditions, flag `narrative_mismatch`.
5. If the ICD code implies a specific laterality but the narrative/referral describes the opposite side, flag `laterality_mismatch`.

**Duplicate detection:**
- Use SQL to find referrals with the same patient_id and overlapping or similar service descriptions.
- Group duplicates, designate a primary (earliest or most complete), and recommend `consolidate_to_primary` or `keep_separate`.

**Shared insurance anomalies:**
- Query for insurance IDs that appear across different patient_ids. These need verification — the disposition is `verify_distinct_patient_policy_id` unless the patients are confirmed to be the same individual, in which case use `legitimate_duplicate_same_patient`.

**Authorization blockers:**
- Check the authorization field on each referral for status: `pending`, `denied`, or `not_submitted`.
- Any non-approved authorization is a blocker.

**Missing records/imaging:**
- Check document availability for each referral. If required document types are absent, flag `missing_records` or `missing_imaging`.

**Readiness status:**
- `ready` — no issues, can schedule
- `blocked` — one or more hard blockers (missing auth, missing records/imaging)
- `under_review` — ICD or clinical discrepancies that need clarification
- `admin_followup` — administrative issues only (insurance verification, duplicates)

**Priority tier:**
- `tier_1_immediate` — urgent referrals that need fast resolution
- `tier_2_short_term` — needs action but not critical
- `tier_3_administrative` — paperwork/verification follow-up

### Transfer review (dialysis/facility packets)

**Document completeness:**
- Each transfer has a packet of required documents. Check every required document type for presence.
- Classify as `complete` if all required documents are present, `incomplete` otherwise.

**Document freshness:**
- Each document type has a freshness limit in days (e.g., HBsAg: 30 days, history & physical: 365 days, monthly labs: 30 days, PPD/CXR: 30 days).
- Compute staleness: if `current_date - received_date > freshness_limit_days`, the document is stale.
- Report stale documents with their `received_date` and `freshness_limit_days`.

**Capacity feasibility:**
- Check the requested start date against available chairs/resources from the facility capacity endpoint.
- `capacity_status`: `available` or `unavailable`.
- `feasibility`:
  - `ready_on_requested_start` — packet complete + capacity available on requested date
  - `packet_not_ready_capacity_available` — packet incomplete, but capacity exists
  - `packet_not_ready_capacity_unavailable` — packet incomplete and no capacity
  - `capacity_unavailable` — packet ready but no capacity

**Intake decision:**
- `accept` — packet complete, capacity available, no clinical flags
- `hold` — minor issues, capacity available or pending
- `clinical_review` — significant gaps requiring nurse review

**Next contact:**
- `clinical_nurse` / `fax_referring_facility` — when clinical documents are missing or stale
- `intake_coordinator` / `phone_patient` — when patient information is incomplete
- `scheduling_coordinator` / `internal_queue` — when ready to schedule
- `none` / `none` — when no action is needed

### Chronic-care enrollment panel

**Candidate retrieval:**
- Fetch `GET /programs/{program_code}/candidates` for the full candidate list.
- For each candidate, fetch `GET /patients/{id}` and `GET /chart/{id}`.

**Eligibility:**
- `true` if the patient has a qualifying diagnosis for the program and an active chart.
- `false` if the diagnosis is wrong, missing, or the chart is inactive.

**Enrollment status:**
- `enroll` — eligible, consent present, chart active, monitoring package can be assigned
- `hold` — eligible but missing consent or chart artifacts that can be resolved
- `reject` — ineligible (wrong condition, no diagnosis) or consent declined

**Reason codes:** Select from the template's allowed set. Common logic:
- `meets_dmhtn_criteria` — patient has qualifying diagnosis and labs
- `consent_declined` / `consent_missing` — self-explanatory
- `chart_not_active` / `stale_active_problems` / `missing_recent_vitals` / `missing_recent_labs` / `missing_medication_list` — chart quality issues
- `wrong_target_condition` / `missing_active_dmhtn_diagnosis` — ineligibility reasons
- `recent_hospitalization_high_touch` / `low_adherence_high_touch` / `recent_ed_high_touch` — risk-stratification flags
- `ckd_biweekly_monitoring` — comorbidity requiring intensified monitoring

**Follow-up cadence:**
- `weekly` — high-touch patients (recent hospitalization, ED visit, low adherence)
- `biweekly` — moderate complexity (CKD comorbidity)
- `monthly` — standard, stable patients
- `deferred` — hold status, waiting on artifacts
- `none` — rejected or ineligible

**Missing chart artifacts:** List chart components that are absent or inactive. Allowed: `chart_record`, `active_problems`, `vitals`, `labs`, `medications`, `consent`.

**Outreach channel:**
- Choose based on patient contact preferences from the patient/chart record.
- Allowed: `phone`, `portal`, `sms`, `email`, `none`.

**Initial monitoring package:**
- `standard_dm_htn` — components: bp_cuff, glucometer, lab_order_a1c_cmp_lipid, ± medication_reconciliation; first_checkin_days: ~14–30
- `high_touch_dm_htn` — standard components plus medication_reconciliation and care_plan_setup; first_checkin_days: 7
- `deferred` — consent_packet and chart_update_request; first_checkin_days: null
- `not_applicable` — empty components; first_checkin_days: null

### Referral-to-chart activation

**Readiness assessment:** Same as referral readiness audit. Include `patient_id` with each referral.

**Blocker sets:**
- `authorization` — list referral_ids with auth issues
- `records` — list referral_ids missing records
- `imaging` — list referral_ids missing imaging

**Duplicate handling:**
- `duplicate_groups` — groups of referrals for the same patient with `keep_referral_id` designating the primary
- `cleared_duplicate_review_referrals` — referrals that were flagged as duplicates but cleared after review

**Ready referral chart needs:**
- For each `ready` referral, determine what chart artifacts need to be created based on the existing chart record.
- `chart_action`: `create_chart` if no chart exists, `update_chart` if chart exists but is incomplete, `no_chart_action` if chart is fully populated.
- `artifacts_to_create`: list missing artifacts (demographics, active_problems, medications, allergies, vitals, labs, consent), sorted alphabetically.

**Correspondence queue:**
- For each non-ready referral, determine the appropriate template and reasons:
  - `clinical_code_clarification` — ICD mismatch or narrative discrepancy
  - `auth_records_request` — authorization denied + records missing
  - `duplicate_resolution` — duplicate referrals
  - `appointment_hold_notice` — already scheduled before clearance

**Priority order:**
- Rank non-ready referrals from highest to lowest priority.
- `tier_1_immediate` items first, then `tier_2_short_term`, then `tier_3_administrative`.
- Within each tier, order by urgency or severity of blockers.

## Summary / cohort rollups

Every task requires a summary section. Compute all counts by iterating over the patient/referral/transfer results array:

- **Total count** — length of the results array
- **Counts by status** — group by the decision/registration/readiness field and count
- **Counts by risk** — group by risk levels
- **Counts by category** — group by cadence, channel, package type, or urgency
- **Cross-tabulations** — when the template specifies `counts_by_urgency_and_status`, produce one entry per observed combination

Use `POST /query` to verify aggregate counts against the raw data when feasible.

## Edge cases and reminders

- **IDs are case-sensitive.** Uppercase referral IDs, patient IDs, and batch/roster IDs exactly as the portal returns them.
- **Dates are in YYYY-MM-DD format.** Compute staleness and freshness using calendar-day arithmetic.
- **Empty lists vs. null.** When the template shows a list with no items, use `[]`. Use `null` only when the template explicitly allows it (e.g., `priority_tier` can be null, `first_checkin_days` can be null).
- **Unordered sets.** Issue codes, reason codes, and blocker codes are treated as unordered sets. Output them in a stable, predictable order (alphabetical) for consistency, but do not infer priority from the order.
- **SQL safety.** Always use parameterized queries with the `params` array. Never interpolate user-provided strings directly into SQL.
- **Rate limiting.** If the API returns paginated results or throttles, process sequentially. The portal is read-only — no destructive operations are permitted.
