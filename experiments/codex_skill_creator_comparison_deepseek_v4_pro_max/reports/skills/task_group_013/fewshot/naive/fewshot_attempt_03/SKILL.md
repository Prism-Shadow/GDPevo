---
name: intake-coordinator
description: Solve healthcare intake coordination tasks against a REST API portal. Navigate patient/referral/transfer/chart/program endpoints, cross-reference records, interpret answer templates, apply classification rules, and assemble controlled-vocabulary JSON output.
---

# Intake Coordination Skill

This skill teaches a systematic workflow for solving healthcare intake coordination tasks that use a shared REST API portal. The tasks involve gathering data across patients, referrals, transfers, documents, charts, programs, ICD codes, and pharmacies, then applying classification rules and assembling a controlled-vocabulary JSON response per an answer template.

## Workflow

### Phase 1 — Discover the API shape

1. Call `GET /` and `GET /health` at the task environment base URL to confirm the portal is reachable and to discover any root-level metadata.
2. The portal serves these standard endpoints. Every task will use a subset:
   - `GET /patients` — list all patients
   - `GET /patients/{patient_id}` — single patient detail
   - `GET /referrals` — list all referrals
   - `GET /referrals/{referral_id}` — single referral detail
   - `GET /transfers` — list all transfers
   - `GET /transfers/{transfer_id}` — single transfer detail
   - `GET /documents` — list all documents
   - `GET /chart/{patient_id}` — patient chart record
   - `GET /programs/{program_code}/candidates` — program enrollment candidates
   - `GET /icd/{code}` — ICD-10 code metadata including chapter
   - `GET /pharmacies` — in-network pharmacy directory
   - `POST /query` — SQL-like query endpoint for cross-referencing

### Phase 2 — Read the answer template

Every task includes an `answer_template.json` (or similarly-named payload file) that defines:
- The exact JSON shape required (top-level keys, nested structures).
- Controlled-vocabulary enum values for every classification field. Use **only** these values.
- Sort ordering rules (typically ascending by ID for lists, unordered-set semantics for reason-code arrays).
- Which fields are required vs. nullable.
- Special validation notes like "uppercase IDs exactly as shown by the portal."

Read the template thoroughly before gathering any data. The template is the contract; the answer must conform to it.

### Phase 3 — Gather the domain data

Based on the task domain (patients, referrals, transfers, or programs), parallel-fetch the relevant endpoints:

**For patient intake tasks:**
- Fetch the roster or target list from payload files.
- `GET /patients` or `GET /patients/{id}` for each target patient.
- `GET /chart/{patient_id}` for clinical data (risks, vitals, labs, problems, diagnoses, medications).
- `GET /pharmacies` for pharmacy network data.
- `GET /documents` filtered to relevant patients for document/benefit records.
- `GET /icd/{code}` for any ICD codes referenced.

**For referral audit tasks:**
- `GET /referrals` (or filter by batch if the API supports it).
- `GET /patients/{id}` for each patient linked to a referral.
- `GET /documents` to find records and imaging attached to referrals.
- `GET /icd/{code}` for each ICD code on each referral.
- Cross-reference referral insurance IDs across patients; same insurance ID on different patients is an anomaly.

**For transfer review tasks:**
- `GET /transfers` filtered to the batch.
- `GET /transfers/{transfer_id}` for detail (packet documents, requested start date).
- `GET /documents` for document freshness checks.
- `GET /patients/{id}` and `GET /chart/{id}` for clinical context.

**For program enrollment tasks:**
- `GET /programs/{program_code}/candidates` for the candidate list.
- `GET /chart/{patient_id}` for each candidate to check eligibility criteria, consent, chart readiness.

**Use `POST /query` for cross-referencing.** The `/query` endpoint accepts SQL-like syntax and is the preferred way to join records across domains without fetching and filtering manually. Examples of useful queries:
- Find all documents for patients in a specific roster.
- Find referrals that share an insurance ID.
- Find stale documents based on date thresholds.
- Cross-reference pharmacy IDs against the network.

### Phase 4 — Classify each item

Apply classification rules consistently. Every value must come from the answer template's allowed enum set.

#### Insurance status

| Status | Condition |
|--------|-----------|
| `valid` | Insurance record present, active, coverage includes the service line |
| `invalid` | Insurance record present but expired, denied, or service line excluded |
| `missing` | No insurance record found |

#### Prescription benefit (PBM) status

| Status | Condition |
|--------|-----------|
| `valid` | PBM record present, active, policy matches |
| `invalid` | PBM record present but invalid, expired, or policy mismatch |
| `missing` | No PBM record found |

#### Pharmacy network status

Cross-reference the patient's pharmacy ID against `GET /pharmacies`. The pharmacy endpoint returns in-network pharmacies.

| Status | Condition |
|--------|-----------|
| `in_network` | Pharmacy found in the in-network directory |
| `out_of_network` | Pharmacy ID present but not in the directory |
| `unknown` | No pharmacy associated with the patient |

#### Lifestyle risk

Derived from patient chart indicators: smoking status, BMI, activity level, substance use, and social determinants documented in the chart.

| Level | Interpretation |
|-------|---------------|
| `low` | No significant lifestyle risk indicators |
| `medium` | One or two moderate indicators |
| `high` | Multiple or severe indicators |

#### Overall risk

Aggregate of insurance validity, clinical markers from chart, lifestyle risk, PBM status, and pharmacy network status. When any component is at its worst level, overall risk elevates.

| Level | Interpretation |
|-------|---------------|
| `low` | All components normal, no clinical flags |
| `medium` | Some components suboptimal but manageable |
| `high` | Multiple components compromised or severe clinical flags |

#### Registration / Readiness status

| Status | Meaning |
|--------|---------|
| `approved` / `ready` | All checks passed, no blockers |
| `hold` / `blocked` | Hard blockers without clinical ambiguity |
| `clinical_review` / `under_review` | Issues requiring clinical judgment or clarification |
| `rejected` / `admin_followup` | Unresolvable blockers or administrative follow-up needed |

#### Blocker / Issue / Reason codes

The answer template defines the exact set of allowed codes for each task type. Derive each code from specific evidence:

- **Coverage codes** (`coverage_expired`, `coverage_pending`, `excluded_service_line`): From insurance record fields.
- **PBM codes** (`pbm_invalid`, `pbm_missing`, `pbm_policy_mismatch`): From PBM/benefit record fields.
- **Contact codes** (`emergency_contact_missing`, `preferred_contact_unavailable`, `missing_address`): From patient demographic fields.
- **Pharmacy codes** (`pharmacy_out_of_network`, `pharmacy_unknown`): From pharmacy cross-reference.
- **Risk codes** (`overall_risk_high`): When overall risk is `high`.
- **ICD codes** (`icd_chapter_mismatch`, `narrative_mismatch`, `laterality_mismatch`): From ICD cross-reference. Use `GET /icd/{code}` to get the chapter, then compare against the expected specialty chapter.
- **Document codes** (`missing_records`, `missing_imaging`): From document cross-reference. A referral/transfer with no attached records or imaging.
- **Authorization codes** (`auth_blocker`): From referral authorization field. Statuses: `pending`, `denied`, `not_submitted`.
- **Duplicate codes** (`duplicate_referral`, `shared_insurance_anomaly`): Same patient has multiple referrals; same insurance ID on different patients.
- **Schedule codes** (`already_scheduled`, `scheduled_before_clearance`): An appointment exists before the referral was cleared.
- **Program codes** (`meets_dmhtn_criteria`, `consent_declined`, `consent_missing`, `chart_not_active`, `stale_active_problems`, `missing_recent_vitals`, `missing_recent_labs`, `missing_medication_list`, `wrong_target_condition`, `missing_active_dmhtn_diagnosis`, `recent_hospitalization_high_touch`, `low_adherence_high_touch`, `ckd_biweekly_monitoring`, `recent_ed_high_touch`): From chart and candidate data.

#### ICD chapter mismatch detection

The `/icd/{code}` endpoint returns an ICD-10 chapter range (e.g., `S00-T88` for injury codes, `M00-M99` for musculoskeletal). Orthopedic referrals expect musculoskeletal chapter codes. Pulmonary referrals expect respiratory chapter codes (`J00-J99`). Primary care expects codes from common outpatient chapters. A code outside the expected chapter for the service line is a `icd_chapter_mismatch`.

Common ICD-10 chapter ranges:
- `A00-B99` — Infectious
- `C00-D49` — Neoplasms
- `E00-E89` — Endocrine
- `F01-F99` — Mental
- `G00-G99` — Nervous
- `I00-I99` — Circulatory
- `J00-J99` — Respiratory
- `K00-K95` — Digestive
- `M00-M99` — Musculoskeletal
- `N00-N99` — Genitourinary
- `R00-R99` — Symptoms
- `S00-T88` — Injury
- `Z00-Z99` — Factors influencing health

#### Document freshness

Documents have received dates and freshness limits. Compare `received_date + freshness_limit_days` against the task reference date (typically the as-of date or the requested service/start date). If the document is older than its freshness limit relative to the reference date, it is stale.

Common freshness limits observed in the domain:
- `hbsag` — 30 days
- `monthly_labs` — 30 days
- `ppd_or_cxr` — 30 days
- `history_physical` — 365 days

Always read the freshness limit from the document or transfer record; do not hardcode values.

#### Duplicate detection

1. Group referrals/transfers by patient ID. If a patient has more than one referral in the batch, they form a duplicate group.
2. Group referrals by insurance ID. If the same insurance ID appears on referrals for different patients, that is a shared insurance anomaly.
3. The primary referral in a duplicate group is typically the earliest or lowest-ID one. The recommendation is `consolidate_to_primary` unless records show the referrals are for genuinely separate clinical needs (then `keep_separate`).

#### Capacity and feasibility

For transfer intake, the portal returns capacity data: chairs open, capacity status (`available`/`unavailable`). Feasibility logic:
- Packet complete + capacity available on requested start → `ready_on_requested_start`
- Packet incomplete + capacity available → `packet_not_ready_capacity_available`
- Packet incomplete + capacity unavailable → `packet_not_ready_capacity_unavailable`
- Packet complete + capacity unavailable → `capacity_unavailable`

#### Follow-up cadence

From program enrollment or referral action plans:

| Cadence | Trigger |
|---------|---------|
| `weekly` | High-touch (recent hospitalization, ED visit, low adherence) |
| `biweekly` | CKD monitoring or moderate risk |
| `monthly` | Standard stable enrollment |
| `deferred` | On hold pending chart/consent completion |
| `none` | Rejected or ineligible |

#### Outreach channel

Preferred contact method from patient record. If not specified, default based on patient demographics. Portal and email are common for engaged patients; phone for high-risk; SMS for younger demographics.

#### Priority tiering

| Tier | Meaning |
|------|---------|
| `tier_1_immediate` | Urgent referrals with clinical discrepancies that affect patient safety or scheduling |
| `tier_2_short_term` | Routine follow-up needed within days to weeks |
| `tier_3_administrative` | Administrative issues only, no clinical urgency |

### Phase 5 — Assemble the output

1. Start with the answer template as the structural skeleton.
2. Fill each field with the gathered and classified data.
3. **Sorting rules**: Patient/referral/transfer lists in ascending ID order. Reason-code and blocker-code arrays are unordered sets — list them alphabetically or in the order they were discovered, but do not assign meaning to order.
4. **Use exact IDs**: Referral IDs, patient IDs, insurance IDs, transfer IDs, group IDs must match the portal exactly, preserving case.
5. **Integer counts**: Summary counts must be exact integers that add up correctly. Every count must reconcile: the sum of status counts must equal total items, and cross-tabulation counts must match their constituent lists.
6. **Null vs. empty**: `null` only where the template allows it and the data is genuinely absent. Use `[]` for empty lists, `0` for zero counts.
7. Return only the JSON object. No prose, no markdown wrapping, no explanation.

### Phase 6 — Verify

Before finalizing, run these checks:

- [ ] Every required top-level key from the template is present.
- [ ] Every list is sorted per the template's ordering rule.
- [ ] Every enum value is from the template's allowed set.
- [ ] Summary counts reconcile: sum of status counts equals total items.
- [ ] No patient/referral/transfer from the target batch is missing.
- [ ] No extra patients/referrals/transfers beyond the target batch are included.
- [ ] All IDs match the portal exactly (case, punctuation).
- [ ] JSON is valid (no trailing commas, no unquoted keys).
- [ ] Response is JSON only — no surrounding prose.

## Common pitfalls

1. **Missing the template's enum values**: Never invent a reason code. If a finding doesn't match any allowed value, re-examine the data and the template's definition of each code.
2. **Sort order violations**: When the template says "ascending by referral_id", sort strictly. When it says "unordered set", order does not matter but consistency is good practice.
3. **Wrong chapter for ICD codes**: The portal returns the actual chapter; do not guess from the code prefix. An injury code may map to chapter `S00-T88` even when the treating specialty (e.g., orthopedics) normally works within chapter `M00-M99`. Always query the portal instead of guessing.
4. **Including patients not in the target batch**: Filter to only the roster/batch IDs specified in the task prompt or payload.
5. **Summary count errors**: Double-check every count. A mismatch between the list length and the summary count is the most common mistake.
6. **Hardcoding freshness thresholds**: Always read the freshness limit from the portal data; limits can vary by document type.
7. **Overlooking the `/query` endpoint**: For complex cross-referencing, `POST /query` is faster and less error-prone than fetching all records and filtering manually.
