---
name: ehr-governance-packets
description: >-
  Produce normalized JSON for EHR / referral quality-governance tasks against a read-only
  EHR environment: duplicate-chart merge-readiness packets, specialty referral coordination
  packets, care-transition handoff packets, ServiceRequest quality checks, and referral-batch
  audits. Use whenever a prompt asks you to gather patient / duplicate-candidate / referral /
  ServiceRequest / provider / ICD-10 / service-code evidence and return one JSON object that
  conforms to a supplied answer_template.json. Triggers: "merge readiness packet", "referral
  coordination packet", "care transition packet", "duplicate review", "ServiceRequest quality",
  "referral batch audit", "normalized JSON conforming to input/payloads/answer_template.json".
---

# EHR quality-governance packets & audits

A family of tasks: you are given a short prompt, an `answer_template.json`, and read-only access
to an EHR/referral environment (patients, conditions, medications, allergies, encounters,
immunizations, disclosures, documents, service-requests, duplicate candidates, referrals,
audit-logs, providers, an ICD-10 reference, and a service-code reference). You return **one JSON
object that matches the template exactly**. The template — not your prose — defines the keys,
types, enums, `required_value` fields, and ordering. There is no scoring tool available while
solving a real task; rely on the rules below and on faithful reading of the environment.

## Universal workflow

1. **Read `answer_template.json` first, then the prompt.** The template is authoritative. Note
   every key, enum set, `required_value` (e.g. a fixed `task_id`), type (incl. nullable), array
   `set_semantics`, and each array's ordering rule. Your output must have exactly those keys/types.
2. **List the case objects** named in the prompt: patient id(s), duplicate-candidate id, referral
   id(s), ServiceRequest id, batch id, recipient/receiving provider id, etc.
3. **Gather evidence** from the read endpoints described in the task's own environment-access file
   (use whatever base URL and routes that file provides). Pull the relevant record families:
   patient demographics, active clinical lists, encounters, documents, immunizations, disclosures,
   the duplicate candidate / referral / ServiceRequest object, the provider directory, and the
   ICD-10 / service-code references for any codes involved. A record family that isn't relevant to
   the template can be skipped.
4. **Apply the domain rules** (below) that correspond to the packet type.
5. **Normalize and sort** every array per the template, set `required_value` fields, and emit
   **JSON only** — no commentary, no trailing prose.

## Reading records: status, normalized_key, faithfulness

- Condition/medication/allergy records carry `status` and a `normalized_key`. "Active" means
  `status == "active"`. Entries with `inactive` / `entered-in-error` are **not** active.
- **Active-key unions/lists** = the set of `normalized_key` values over **every active record**,
  deduped across sources and (for merges) across both patients, then sorted per the template
  (usually ascending/alphabetical).
  - Include **all** active keys — even generic-looking placeholder keys (e.g. `baseline_*`) and
    duplicated allergens. A *comprehensive* active list keeps everything active. (Dropping such
    placeholders from a comprehensive list is wrong.)
- **"excluded"/"distractor" key buckets** = records whose `status != active`, by `normalized_key`.
- **Copy verbatim**: ids, dates, phones, faxes, codes, descriptions, and `source` strings come
  straight from the environment; don't paraphrase them.

## Selection depends on the field's PURPOSE (the central judgment)

The same raw data feeds different fields with opposite selection criteria — always read what the
field is *for*:

- **Comprehensive / preservation lists** (merge unions, care-transition active lists): keep **all
  active records**, placeholders included.
- **Relevance-filtered lists** (referral-letter diagnosis/medication highlights): keep **only
  records tied to the stated reason** and drop placeholders/distractors.

## Distractor patterns to actively reject

See `references/field-conventions.md` for the full list. In brief: name collisions (same display
name but different DOB/insurance = different people), placeholder `normalized_key`s, routine
`chart_summary`/`ehr_export` documents, inactive records, audit-logs for other patients or
unrelated/test events, and soft coordination notes ("confirm …") that don't actually change a
complete record. Include or exclude each strictly by the field's purpose.

## Packet-type rules

### A. Duplicate merge-readiness / duplicate review
- Read the candidate for `status`, `match_signals`, `conflict_signals`, and `merge_preview`
  (`preferred_target_patient_id`/`source_patient_id`). **Validate** each signal against the two
  patients' actual demographics/conditions before emitting it.
- **Target/canonical** = the patient with `canonical_status == "active"` (the other has
  `duplicate`/`possible_duplicate`, or the candidate names the preferred target); **source** = the
  other. When no merge is decided, target/source are `null`.
- **Disposition ladder** (map to whatever enums the template gives):
  - Strong matches + only **trivial/normalizable** conflicts (address abbreviation like "St" vs
    "Street", a name nickname/variant) → clean **ready / merge-ready**. Still record the difference
    as a `conflict_signal`/`demographic_conflict`, but do **not** downgrade the disposition, set
    `manual_review_required`, or add a review note.
  - Strong matches **and** substantive conflicts (opposite-laterality problems, genuinely different
    given names, different phone) on an unresolved candidate → **needs_review / review_hold** with
    null merge target/source. (This is the correct outcome for a "twins-like" pair: same
    DOB/insurance/address but different name/phone and opposite-side problems — hold, do **not**
    jump to do_not_merge.)
  - Reserve **do_not_merge** for clear different-people-with-no-merge-value; reserve
    **merge/confirmed** for clean confirmed duplicates.
- **Reconciliation** (`patient_active_list_endpoints_over_duplicate_preview`): keys added =
  active keys from the patient endpoints **minus** the keys already in `merge_preview`, per category.
- **demographic_matches** = demographic fields whose values are equal across the two patients
  (dob, family_name, insurance_id, phone, sex). **demographic_conflicts** = fields that differ
  (given_name, address), including variant/abbreviation differences.
- **Evidence documents** follow the template's `document_selection_policy` (e.g.
  identity-verification + external clinical-continuity docs, status `final`). Routine
  `chart_summary`/`ehr_export` docs are excluded → put them in the distractor bucket and name the
  excluded type. **Evidence audit_ids** = audit entries for these patients that reference *this*
  case; other-patient / unrelated / test-tagged entries are distractors.
- **packet_contact**: `specialist_provider` = the provider matching the external continuity
  document's facility/service line; `primary_care_provider` = the patient's PCP block. Copy provider
  fields from the directory.

### B. Referral coordination packet (specialty letter)
- `patient_referral` from the referral object (batch_id, service_line, requested_date) + patient.
- **referral-relevant** conditions and **supporting** codes = **only** codes clinically tied to the
  referral reason: the referral's own `diagnosis_code` **and** the presenting symptom in the
  narrative. Comorbidities are `referral_relevant=false` even when one of their medications is still
  highlighted.
- **ICD validation** via the ICD reference: `valid_matches_narrative` when the code's chapter fits
  the service line **and** the narrative matches the code's `expected_terms`; also emit the chapter
  and `narrative_match`.
- **allergy_readiness**: a single fully-populated active allergy (allergen+reaction+severity+status)
  = `complete_documented`, ready, no follow-up — **even if** a coordination note says "confirm …"
  (that note is a soft distractor; the record is complete). Letter enums offering a fully-specified
  allergy statement confirm completeness.
- **recent_encounter_evidence** = the encounter whose notes/diagnoses match the referral reason
  (not necessarily the most recent visit).
- **medication_highlights** = **only referral-relevant** meds; exclude placeholder/distractor meds
  (e.g. a `baseline_*` med with an implausible route).
- **Letter-field enums**: choose each value to match the derived facts; the option names themselves
  are strong hints about the intended answers.

### C. Care-transition handoff packet
- Recipient = the named provider (from the directory). **disclosure** = the disclosure whose
  `recipient_provider_id == recipient` and `status == "permitted"`.
- **Handoff encounters** = the N (template length) most **relevant recent** encounters for *this*
  transition — those tied to the transition's condition/service (e.g. the numbered handoff/
  care-transition series about the surgical joint), **newest→oldest**. Not merely the most-recent
  encounters: exclude unrelated specialties, other body regions, and stale overflow beyond N.
  Record selected ids (newest→oldest) and all reviewed-but-excluded ids (ascending).
- **latest_immunization** = the immunization with the max date.
- **risk_flags** (from the template's `allowed_values`) derived from evidence: a condition
  (memory-loss → cognitive flag; hypertension → hypertension flag), a condition+medication combo
  (insulin + diabetes → insulin-dependent flag), an allergy (latex → latex-allergy flag), and
  encounter notes that explicitly **require** a plan/note (→ fall-risk-note-required,
  perioperative-glucose-plan-needed). `risk_flag_evidence` links each flag to its supporting
  active condition/medication keys (and the encounter carrying a note-based requirement).
- **Readiness**: `ready_with_risk_flags` when flags exist but nothing blocks; `blocking_issue_codes`
  come **only** from the template's `missing_*` / `not-permitted` enum — clinical requirements
  (glucose plan, fall-risk note) are risk flags, **not** blockers. `ready` only if no flags;
  `not_ready` only if a real blocker exists.

### D. ServiceRequest quality check
- Copy scalar fields verbatim. `service_code_valid` via the service-code reference (code active
  **and** its service_line consistent with the performer). `performer_service_line` from the
  performer provider. `reason_code_validation` per code (ordered by code): `valid` = code exists in
  the ICD reference; `chapter` = its ICD chapter; `matches_patient_evidence` = the patient has an
  active condition carrying that code (any source counts, including imaging/MRI reports).
- **SBAR coverage**: `complete=true` when all four sections (situation, background, assessment,
  recommendation) are present and non-empty; emit `sections_present` + `missing_sections`.

### E. Referral batch audit
- Scope the batch by filtering **all** referrals to the batch id yourself (a `batch_id` query
  param may be ignored by the server). `record_count` = row count (duplicate resubmissions count);
  `unique_patient_count` = distinct patient ids.
- **invalid / out-of-range codes** = codes whose ICD chapter is clinically wrong for the batch's
  service line (e.g. a Respiratory code in an orthopedic batch). Injury-chapter S-codes (meniscus
  tears, etc.) **are** acceptable for orthopedics — do not flag them as out-of-range. Use
  `unknown_code` only for codes absent from the ICD reference.
- **laterality/narrative mismatch**: compare the code (its `expected_terms` + laterality) to the
  narrative — `laterality_mismatch` (opposite side, same region), `missing_laterality` (same
  condition, no side stated), `narrative_mismatch` (different region/condition). **Do not
  over-flag**: a generic-symptom narrative that matches the code's region+side is not a mismatch,
  and prefer a single dominant `mismatch_type` per row rather than stacking types.
- **duplicate_groups** = same-patient resubmissions (a "-DUP" id / a "duplicate resubmission"
  coordination note); disposition = consolidate-under-original; tier all group rows as tier-1
  duplicate blockers.
- **insurance/patient anomalies** = shared insurance id across **different** patients (e.g. twins) →
  verify-membership, do-not-merge. Same display name but different insurance/DOB is a distractor,
  not an anomaly.
- **follow-up queues** from referral fields: authorization missing/pending from
  `authorization_status`; records-request = referrals lacking an office-note document; imaging
  follow-up = missing/pending imaging.
- **action_plan tiers**: Tier 1 = urgent-urgency coding errors + invalid/out-of-range codes +
  duplicate blockers; Tier 2 = routine coding/auth/document blockers; Tier 3 = administrative
  document completion only. `owner_provider_id` = the referral's receiving provider. Every referral
  needing action is tiered once; count fully-clean rows as validated-ready.
- **summary_counts** are **derived** from the sections above — compute them from your own arrays,
  never independently.

## Output discipline
- JSON only; exact template keys, types, enums, and `required_value`s.
- Sort each array as the template says (default alphabetical/ascending; honor "newest→oldest",
  "by code", or "by id" when stated). Treat `set_semantics` arrays as unordered sets of the
  correct members.
- When a value is genuinely absent, use the template's nullable/`missing` option rather than
  inventing one.
- Prefer the smallest correct set: false-positive members (extra ids, over-flagged rows, guessed
  controlled-vocabulary codes) cost as much as misses.
