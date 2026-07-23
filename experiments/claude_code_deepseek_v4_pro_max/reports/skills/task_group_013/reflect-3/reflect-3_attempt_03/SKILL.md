# Cedar Ridge Intake Coordination — Task Solver

## Overview

This skill covers solving structured data-reconciliation tasks against the Cedar Ridge Intake Coordination Portal REST API. Each task provides a prompt describing a clinical-intake scenario, an answer template specifying the exact JSON output shape, and access to a shared read-only API with patient, referral, transfer, chart, document, and program data.

## Workflow

### 1. Read all inputs first

Before making any API call, read every file in the task's `input/` directory:

- **`prompt.txt`** — The task description. Identifies the target entity (roster ID, batch ID, transfer batch, program code) and the clinical scenario. Note any overrides for the base URL.
- **`payloads/answer_template.json`** — The required JSON output shape. This is your contract. Study every required key, every allowed enum value, every ordering constraint, and every data type before you write a single line of output.
- **`payloads/target_roster.json`** or similar — If present, lists the specific entity IDs the task operates on.

### 2. Map the template to data sources

For each section of the answer template, identify which API endpoints provide the raw data. The pattern is consistent across tasks:

| Template concern | Typical data sources |
|---|---|
| Entity identity (batch, roster, program) | Direct entity endpoints, SQL query |
| Patient-level fields | `GET /patients/{id}` — returns patient demographics, coverage, PBM, pharmacies, clinical history, lifestyle, chart artifacts, documents, referrals, transfers, rosters |
| Referral-level fields | `GET /referrals?batch_id=...` or the patient detail's nested `referrals` array |
| Transfer-level fields | `GET /transfers?batch_id=...` or the patient detail's nested `transfers` array |
| Document / packet status | `GET /documents` (filter by transfer_id or referral_id) |
| ICD code metadata | `GET /icd/{code}` — returns chapter, description, laterality, service_family |
| Chart details | `GET /chart/{patient_id}` — returns chart artifacts, recent vitals/labs, active problems |
| Pharmacy networks | `GET /pharmacies` — network_status per pharmacy |
| Program candidates | `GET /programs/{program_code}/candidates` |
| Cross-entity queries | `POST /query` with SQL — useful for verifying relationships across tables |

### 3. Gather data exhaustively

Query every relevant endpoint before building the answer. For patient-level tasks, fetch each patient by ID individually (`GET /patients/{id}`) — the detail response includes nested coverage, PBM, pharmacy, lifestyle, chart artifacts, and clinical history that the list endpoint omits.

For batch-level tasks, use the filtered list endpoints (`?batch_id=...`) to get entity lists, then fetch supporting data (patient details, ICD metadata, documents, charts) for every entity in the batch.

**The SQL endpoint** (`POST /query`) accepts `{"sql": "SELECT ..."}` and returns columns + rows. Use it to verify counts, cross-reference relationships, or fetch data not conveniently available through other endpoints. Only SELECT is allowed.

### 4. Derive business rules from data patterns

The API data encodes consistent business rules. Infer them by comparing records across patients/entities before writing the answer. Key patterns observed:

**Insurance validity:**
- Coverage `status` of `"active"` with the relevant `service_line` listed in `service_lines` → valid
- Coverage `status` of `"expired"` → invalid (coverage_expired reason)
- Coverage `status` of `"pending"` → invalid (coverage_pending reason)
- Service line missing from coverage → excluded_service_line issue
- No coverage records at all → missing

**Prescription benefit (PBM) validity:**
- PBM `active: 1`, `status: "approved"`, `formulary_status: "covered"` → valid
- PBM `active: 0` or `status: "rejected"` → invalid (pbm_invalid)
- PBM policy_number differs from coverage policy_number → pbm_policy_mismatch
- No PBM record → missing (pbm_missing)

**Pharmacy network:**
- Pharmacy `network_status: "in_network"` → in_network
- `network_status: "out_of_network"` → out_of_network
- No pharmacy assigned → unknown

**Document/packet completeness:**
- A document counts as present only if `finalized: 1` and `status: "final"`. Documents with `finalized: 0` or `status: "draft"` are NOT complete — treat them as missing.
- For transfer packets: the `transportation` field on the transfer record itself may serve as evidence that transportation is arranged (if the value is non-null like `"family"`, `"ride_share"`, `"medical_transport"`). A null transportation field means the transportation document is missing.

**Document freshness/staleness:**
- Some document types have recency requirements measured from the requested service/start date.
- Monthly labs are expected within ~30 days.
- Annual documents (H&P, PPD/CXR, HBsAg) are expected within ~365 days.
- Hep B antibody core is typically lifetime.
- When a document exists but is older than its freshness window, classify it as stale (not missing).

**ICD / clinical code matching:**
- Compare the ICD code's `service_family` against the referral's `service_line`. A mismatch → clinical_code_discrepancy.
- Compare the ICD code's `chapter` against the expected chapter for the service line.
- Compare `laterality` from ICD metadata against the referral's narrative/diagnosis text.
- A generic diagnosis description (e.g., "specialty consultation") that doesn't reflect the specific ICD description may constitute a narrative_mismatch — but if ALL referrals in a batch share the same generic description, it is likely a data-design artifact, not a per-referral discrepancy.

**Duplicate detection:**
- Same patient ID appearing in multiple referrals within the same batch → duplicate group.
- Same insurance ID on different patients → shared_insurance_anomaly.
- A referral with `appointment_scheduled: 1` and a future `appointment_date` may indicate the referral was scheduled before clearance was complete → scheduled_before_clearance.

**Eligibility and enrollment:**
- Candidates whose `target_condition` does not match the program's target → ineligible (wrong_target_condition).
- Candidates whose chronic conditions don't include the program's target diagnoses → missing_active_diagnosis.
- `consent_status: "declined"` → hard reject regardless of other factors.
- `consent_status: "missing"` → hold/defer (obtainable).
- `existing_chart: 0` with no chart artifacts → chart_not_active.
- Risk flags like `recent_ed_visit`, `recent_hospitalization: 1`, or low adherence scores → high-touch monitoring.

### 5. Build the answer JSON

Follow these rules for every answer:

- **Include every required top-level key** from the template. Missing a required key is a scoring failure.
- **Use only allowed enum values** from the template's `allowed_values` lists. Never invent strings.
- **Respect ordering constraints.** Lists annotated with "ascending by X" must be sorted. Lists annotated as "unordered set" should be treated as sets — order doesn't matter, but use a consistent sort for readability.
- **Use uppercase IDs exactly as they appear** in API responses (e.g., `"P001"`, `"REF0001"`, `"TR0001"`).
- **Compute summary counts from patient-level data.** Every count in the summary must be internally consistent with the individual results. Re-verify totals after building all rows.
- **Null vs. empty:** When a field is `null`-able per the template and no value applies, use `null` (JSON null), not an empty string or omitted key.
- **Empty arrays vs. omitted:** When a list has no items, use `[]`, not a missing key.
- **Boolean fields:** Use JSON `true`/`false`, not strings.
- **Date format:** Always `YYYY-MM-DD`.

### 6. Verify consistency

Before finalizing, cross-check:

1. Do the summary counts match the per-entity data? Sum each category across patient rows and compare.
2. Are all lists sorted as the template requires?
3. Does every enum value match an `allowed_values` entry?
4. Are blocked_reason_codes and issue_codes consistent with the entity's readiness_status? (e.g., a "ready" entity should have no blocker codes)
5. Are duplicate groups, shared insurance anomalies, and blocker sets internally consistent with the per-referral/transfer findings?

## Common pitfalls

- **Treating draft documents as present.** Always check `finalized` and `status` fields. Draft documents (`finalized: 0` or `status: "draft"`) are not complete.
- **Assuming coverage validity from `status` alone.** Coverage must be active AND include the relevant service_line. An active policy that doesn't cover the service is still an issue (excluded_service_line).
- **Ignoring the `existing_chart` field.** A patient may have chart artifacts in the patient record but `existing_chart: 0` — this indicates the chart itself needs creation.
- **Overlooking stale documents.** A document can be present AND finalized but still too old to meet freshness requirements. Check received dates against the service/start date.
- **Mixing up missing vs. stale.** Missing = no finalized document exists. Stale = document exists but is too old.
- **Forgetting to cross-reference PBM policy_number with coverage policy_number.** A mismatch is a distinct issue (pbm_policy_mismatch) separate from PBM active/status checks.
- **Assuming all referrals with "possible duplicate" notes are actual duplicates.** Check whether another referral actually shares the same patient ID. If not, clear the duplicate review.
