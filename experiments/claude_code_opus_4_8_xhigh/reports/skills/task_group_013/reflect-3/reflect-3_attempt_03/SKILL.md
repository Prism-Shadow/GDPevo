---
name: cedar-ridge-intake-reconciliation
description: >-
  Solve Cedar Ridge Intake Coordination Portal reconciliation tasks — the family of
  jobs that point at a shared healthcare intake portal (patients, referrals, transfers,
  charts, coverage, PBM, pharmacies, ICD codes, program candidates) and ask for ONE
  strict JSON object that follows a provided answer_template.json. Covers new-patient
  access verification, referral readiness audits, transfer/dialysis intake review,
  chronic-care enrollment panels, and referral-to-chart activation. Use whenever a task
  references the Cedar Ridge / intake-coordination portal, gives an answer_template with
  enum allowed_values and ordering rules, and wants patient/referral/transfer-level
  status derivation plus cohort summary counts.
---

# Cedar Ridge Intake Coordination reconciliation

These tasks all have the same shape: a healthcare **intake-coordination portal** exposes
read-only data; you must reconcile a named cohort against deterministic business rules and
return **one JSON object that exactly follows `input/payloads/answer_template.json`**. The
template is a strict contract, and the output is machine-graded field-by-field, so precision
and normalization matter as much as the logic.

## The template is the spec — read it first

Before touching data, read `input/payloads/answer_template.json` in full and extract:

- **Top-level required keys** and their order.
- **Per-item required keys** for every list section.
- **Enum `allowed_values`** for each field — you may ONLY emit these controlled values.
- **Ordering rules** (e.g. "ascending by patient_id", "ascending referral_id",
  "alphabetical by code", "unordered set", "highest priority first").
- **Count-object keys** in the summary — every listed key must appear, even when its value is `0`.

Mirror the template exactly: same key names, same nesting, same constant values it pins
(`task_id`, `roster_id`/`batch_id`/`program_code`, service line, etc.). Do not add prose,
extra keys, or free-text explanation fields. **Output JSON only.**

## Workflow

1. **Parse the template** (above) and note every field you must produce.
2. **Identify the cohort**: the roster_id / batch_id / program_code and the exact member IDs.
   Get member IDs from the prompt, the target payload, or by querying the portal
   (e.g. a program's candidate list, or all referrals/transfers in a batch). Include a row
   for *every* current member and nothing else.
3. **Pull data** from the portal (see "Portal access"). Prefer the read-only SQL endpoint for
   bulk pulls and joins; use the REST detail endpoints when you want pre-joined context.
4. **Derive per-record fields** by applying the rule families below.
5. **Detect cross-record anomalies** (duplicates, shared insurance) across the whole cohort.
6. **Assemble code sets** (blocker / reason / issue / action codes) using ONLY the template's
   enum values; treat these arrays as unordered sets.
7. **Assign the status/decision** via the decision ladder, then **priority tier / cadence**.
8. **Compute every summary count by iterating your per-record results** — never hand-tally.
   Initialize each enum key to 0 so zero-count keys are present.
9. **Normalize and order** all lists per the template, then emit JSON only.
10. **Self-check**: every required key present; every value in-enum; lists ordered; counts
    reconcile to the rows; IDs uppercase and verbatim.

## Portal access

The task's environment file gives a base URL (referred to here as `<BASE_URL>`). The portal is
read-only and needs no credentials. Two equivalent access paths:

- **REST GET** list + detail endpoints. List endpoints accept filters (e.g. batch id, query,
  limit). Detail endpoints (`/<resource>/{id}`) return the record joined with related data
  (patient, ICD metadata, documents, etc.). A program's members come from its candidates endpoint.
- **Read-only SQL** via `POST <BASE_URL>/query` with body `{"sql": "SELECT ..."}`. Only `SELECT`
  is allowed. This is the fastest way to reconcile — discover the schema from
  `sqlite_master`, then join tables directly. See `references/portal-schema.md`.

Pull the whole cohort's supporting rows up front (coverage, pbm, pharmacy, lifestyle, clinical
history, documents, chart artifacts, ICD codes, capacity) rather than record-by-record.

## Rule families

Apply only those relevant to the current template. Full derivations and enum-mapping tables are
in `references/rule-cheatsheet.md`. Where a task pins a specific service line / service date /
"as-of" date, take it from the cohort's own record in the portal (roster/batch/program), not from
the calendar.

### Coverage / insurance validity
From the `coverage` row(s) for the requested **service line** and **service date**:
- `missing` — no coverage row.
- `valid` — `status = active` AND service line ∈ `service_lines` AND not expired
  (`termination_date` ≥ service date, `effective_date` ≤ service date).
- `invalid` — otherwise (expired/terminated, pending, or service line not covered).
Reason codes: `coverage_expired` (expired or terminated before service date),
`coverage_pending` (status pending), `excluded_service_line` (service line not in `service_lines`).

### PBM / prescription validity
From the `pbm` row: `valid` when `active = 1` AND `formulary_status = covered` AND
`status = approved` AND the PBM policy number matches the coverage policy number.
Codes: `pbm_missing` (no row), `pbm_policy_mismatch` (policy differs / specialty mismatch flag),
`pbm_invalid` (not active / not covered / not approved).

### Preferred pharmacy network
Take the patient's **rank-1** preferred pharmacy (lowest `preference_rank`) and read its
`network_status`: `in_network` / `out_of_network`; `unknown` (code `pharmacy_unknown`) if none.

### Lifestyle & overall risk
Lifestyle risk = count of present risk factors, then bucket:
`smoking_status = Current` (+1), `alcohol_use = Heavy` (+1),
`exercise_frequency` is `None`/null (+1), `sleep_hours < 6` (+1) → 0 = low, 1–2 = medium, 3+ = high.
Overall risk composites lifestyle with **clinical acuity** (`recent_hospitalization`, non-empty
`risk_flags`, chronic-condition count). Clinical acuity is usually low in these cohorts, so overall
risk skews toward the milder buckets — escalate conservatively rather than defaulting everything to
high. `overall_risk_high` is a reason code when overall risk is high.

### Contact / demographic completeness
Flag `missing_address` (null address), `emergency_contact_missing`
(`emergency_contact_present = 0`), and `preferred_contact_unavailable` (the preferred channel's
field is null — e.g. prefers email but email is null; prefers phone/sms but phone is null).

### ICD coding discrepancies
Resolve `icd10_code` in `icd_codes`. A code carries an authoritative `service_family`, `chapter`,
and `laterality`. **`icd_chapter_mismatch` = the code's `service_family` ≠ the referral's
`service_line`** (report observed = code chapter, expected = the service line's canonical chapter).
A code whose family matches the service line is NOT a chapter mismatch even if its chapter letter
differs (e.g. injury `S`-codes are legitimately orthopedic). `laterality_mismatch` /
`narrative_mismatch` only when the referral narrative explicitly contradicts the code's
laterality / description.

### Duplicates & shared insurance (across the cohort)
- **Duplicate group** = the *same patient_id with the same icd10_code* on more than one referral.
  Keep the lowest referral_id as primary; recommend `consolidate_to_primary`.
- **Shared insurance anomaly** = the *same insurance_id* on more than one referral. If the patients
  differ → `verify_distinct_patient_policy_id`; if it is the same patient →
  `legitimate_duplicate_same_patient`. A shared insurance_id across *different* patients is NOT a
  duplicate; a "possible duplicate" note in the data can be a decoy — classify by the rules, not the note.

### Operational blockers (referrals)
`records_missing` (`records_received = 0`), `imaging_missing` (`imaging_received = 0`),
`authorization_blocked` / `auth_blocker` (`auth_required = 1` AND `auth_status` ∈
{`pending`, `denied`, `not_submitted`}), `scheduled_before_clearance` / `already_scheduled`
(`appointment_scheduled = 1` while not yet cleared).

### Document / packet completeness & freshness (transfers)
The template's `missing_required_documents` enum lists the required document set. A required item
counts as **satisfied only when present AND finalized** (draft/absent → missing). Some doc types
are **time-limited**: a satisfied doc is `stale` when its age exceeds a freshness limit, where age =
(operative reference date − `received_date`). Use the **requested start / service date** as the
freshness reference (data can carry received dates well after "today"). Freshness limits are
portal policy — infer them from the data and use clinical defaults (e.g. monthly labs ≈ 30 days,
history & physical ≈ 180, immunology/imaging screens ≈ 365).

### Capacity & feasibility (transfers)
Capacity for a requested date = **sum of `open_chairs` across all facility locations** for that
date and the requested modality; 0 (or no row) → `unavailable`. Feasibility is the packet × capacity
matrix: complete + available → ready-on-start; incomplete + available → packet-not-ready-capacity-available;
incomplete + unavailable → packet-not-ready-capacity-unavailable; complete + unavailable → capacity-unavailable.

### Chart artifacts & activation
`chart_action`: `create_chart` when the patient has no active chart (`existing_chart = 0`) — list the
required artifacts to create; `update_chart` when a chart exists but required artifact types are
absent — list the absent ones; `no_chart_action` when complete. Order `artifacts_to_create`
alphabetically by the enum string. Distinguish **absent** artifacts (a row of that type does not
exist) from **stale** ones (a row exists with `status = stale`) — the template's reason codes model
staleness separately from absence.

### Program eligibility & enrollment
Eligible when the candidate's `target_condition` matches the program's condition AND the required
active diagnosis is present (else `wrong_target_condition` / `missing_active_dmhtn_diagnosis`-style
codes). `consent_status` drives disposition: an active **decline** blocks enrollment, a **missing**
consent is a recoverable hold. Chart activity + required/fresh artifacts gate a clean enrollment
(`chart_not_active`, `stale_active_problems`, `missing_recent_vitals/labs`, `missing_medication_list`).
High-touch triggers (recent hospitalization, recent ED, low adherence, CKD) raise follow-up cadence
and the monitoring-package tier and shorten the first check-in.

### Decision / readiness ladder & priority tiers
Derive the status from the code set with a fixed precedence:
- **Hard operational blocker** (missing records/imaging, auth blocked, expired/excluded coverage) →
  `blocked` / `rejected`.
- **Coding or clinical review needed** (ICD discrepancy, high clinical risk) → `under_review` /
  `clinical_review`.
- **Administrative only** (secondary duplicate, already scheduled, shared-insurance verification,
  pending coverage, missing contact/address) → `admin_followup` / `hold`.
- **Nothing pending** → `ready` / `approved`.
Purely administrative flags (shared insurance, primary-of-a-duplicate) may still be schedulable — a
record can be `ready`/`approved` while carrying an issue code that is tracked for follow-up.
Priority tiers: `tier_1_immediate` (urgent or time-critical, e.g. an appointment scheduled before
clearance), `tier_2_short_term` (routine clinical follow-up), `tier_3_administrative` (admin cleanup).
Map each code to its action/reason/blocker enum (see `references/rule-cheatsheet.md`).

## Output & normalization conventions

- Emit **JSON only** — no prose, no trailing commentary.
- Include **every required key**; pin the constants the template fixes.
- Use **only enum `allowed_values`**; never invent status/code strings.
- **Code arrays are unordered sets** — de-duplicate; order is not graded but keep them clean.
- **Order every list** exactly as the template says (usually ascending by the record's id;
  alphabetical where stated; ranked where stated).
- **IDs stay uppercase and verbatim** as the portal shows them.
- **Counts are integers**, computed by iterating your rows; every enum key present (0 if none).
- Cross-check that per-record statuses and the summary counts reconcile before finishing.

## Calibration note

The deterministic rules above (validity, network, duplicates, shared insurance, blockers, coding
family, capacity, chart action) transfer directly. The *policy* details — exact risk/freshness
thresholds, which contact owner/route a follow-up gets, and the precedence between `hold` and
`clinical_review` — are portal-specific. Fix them from the template's enum lists and observed data,
apply one consistent model across the whole cohort, and keep per-record status and summary counts
internally consistent.
