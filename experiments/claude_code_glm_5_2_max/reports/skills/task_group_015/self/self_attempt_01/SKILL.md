---
name: ehr-quality-governance-packet
description: Produce a normalized JSON packet or audit from the read-only EHR quality-governance API. Covers duplicate-chart merge readiness, referral coordination, care-transition handoff, duplicate-review + service-request quality, and referral batch audit. Use whenever a task points at the shared EHR environment base URL (task-env), supplies case objects such as candidate/patient/referral/batch/provider/service-request IDs, asks you to verify evidence against that environment, and requires a single JSON object conforming to a provided answer_template.json. Do NOT use for tasks that do not target this EHR environment or that do not supply an answer template.
---

# EHR Quality-Governance Packet Generation

This skill produces one normalized JSON object per task from the shared read-only EHR
quality-governance environment. Five task archetypes share one environment, one endpoint
contract, and one output discipline:

1. **Duplicate-chart merge readiness packet** — reconcile a duplicate candidate against both
   patients' active clinical lists; name canonical target/source, disposition, and key unions.
2. **Referral coordination packet** — reconcile one referral against the patient's active chart;
   validate the diagnosis code set, allergy/authorization/document readiness, and letter fields.
3. **Care-transition handoff packet** — select the most relevant handoff encounters, derive risk
   flags with evidence, and gate the packet on a permitted disclosure.
4. **Duplicate-review + service-request quality** — validate a duplicate candidate outcome and a
   draft ServiceRequest's codes/SBAR coverage.
5. **Referral batch audit** — classify every referral in a batch by code validity, laterality,
   duplicates, follow-up queues, and Tier 1/2/3 action plan with reconciling summary counts.

## The environment is the only source of truth

- Read environment data **only** over the network via the base URL recorded in
  `environment_access.md`. Do not read any local source files for environment data. The network
  API is authoritative.
- Use **GET** requests **only** to the allowed endpoints listed in `environment_access.md`. No
  authentication. No other hosts. No mutations.
- See `environment_contract.md` for the full endpoint map, record field shapes, value
  vocabularies, the service-line→ICD-10 chapter map, and the duplicate signal vocabulary.

## Operating workflow

Run these steps for every task. The answer template is the contract; the environment is the
evidence; the two together fully determine the output.

### 1. Extract case objects from the prompt
Pull every identifier the prompt names: `candidate_id`, `patient_id`(s), `referral_id`,
`batch_id`, `provider_id`, `service_request_id`, `service_line`, and any requested outputs.
These are the fetch keys. Also note the packet/audit *type* (which of the five archetypes) and
the explicit exclusions the prompt states (e.g., "exclude stale records," "no procedural notes").

### 2. Read the answer template first — it is the contract
Open `input/payloads/answer_template.json` before fetching anything. Extract:
- Required top-level keys and required sub-keys (emit every one).
- `allowed_values` / `enum` sets — output values are **constrained to these**; never invent.
- `set_semantics: true` — the array is a set; order is normalized by the evaluator (but sort it
  anyway per the ordering rules).
- Ordering rules (e.g., `sort ascending`, `newest to oldest`, `sort_by_code`).
- Nullability (`"type": ["string","null"]`) — emit `null` only where allowed.
- Fixed `required_value` fields (e.g., `task_id`) — copy verbatim.
- Any field the template asks for that is **not** directly in the API (e.g.,
  `normalized_key` unions, `reason_code_validation`, `risk_flag_evidence`) — these are computed,
  not fetched.

### 3. Fetch environment evidence
Map case objects to endpoints and pull the records you need (see `environment_contract.md`).
Always fetch the **detail** endpoints for the named case objects plus the **active clinical
lists** for every involved patient, the provider directory for every named/referenced provider,
and the ICD-10 / service-code directories for every code you must validate. When a task names a
batch, fetch the referral list and filter to that `batch_id`.

### 4. Normalize and reconcile
See `rules.md` for the full rule set. Essentials:
- Use each record's **`normalized_key`** field as the canonical key for conditions, medications,
  and allergies — never the free-text name or the code.
- **Active only**: include only `status == "active"` records in active lists. Route inactive /
  entered-in-error / draft records to `excluded_distractors`.
- **Reconcile sources** when two exist: the patient active-list endpoints are **authoritative**
  over any preview/summary (e.g., a duplicate candidate's `merge_preview`). Compute unions from
  the active endpoints, then report what the preview was missing.
- Dedup, then sort every array per the template's ordering rule.

### 5. Validate codes, identity, and quality signals
- **ICD-10**: unknown code → invalid/unknown; chapter ≠ expected chapter for the service line →
  wrong-service-chapter / out-of-range; `requires_laterality` but narrative lacks the side →
  missing-laterality; narrative contains no `expected_terms` → narrative-mismatch.
- **Service code**: valid iff the code exists in the service-code directory, is `active`, and its
  `service_line` matches the performer/expected service line.
- **Service request**: map API field names to template names (`requester_id`→`requester_provider_id`,
  `performer_id`→`performer_provider_id`); derive `performer_service_line` from the provider
  directory; validate each `reason_codes` entry against ICD-10 and against the patient's active
  conditions (`matches_patient_evidence`); read `sbar` sections for coverage.
- **Identity**: weigh match vs conflict signals; serious conflicts block merge; minor conflicts
  allow merge with a review note. Map raw API signals onto the **template's** allowed vocabulary.
See `rules.md` for disposition, tiering, readiness, and risk-flag rules.

### 6. Classify disposition / tier / readiness
Apply the archetype-specific decision rules in `rules.md`: merge disposition, referral readiness,
packet readiness, audit tiering, and risk flags. Every classification must cite the evidence that
produced it (evidence IDs, keys, codes). Where the template exposes a `*_choice` enum (referral
letter fields), pick the single enum value that matches the evidence.

### 7. Fill the template
- Emit every required key with the correct type. Constrain every enum to `allowed_values`.
- Populate `excluded_distractors` / `excluded_*_ids` / `separate_*_ids` wherever the template
  asks — actively exclude stale, out-of-window, inactive, unrelated, and SOP/narrative material.
- Resolve provider contacts from the provider directory; the patient's `primary_care_provider` is
  embedded on the patient record.
- Reconcile any summary counts with the categorized lists you just emitted (counts must match).

### 8. Emit JSON only
Return a single JSON object conforming to the template. No prose, no comments, no markdown
fences, no narrative SOP text, no explanations outside the JSON. Stable IDs, not narratives.

## Core rules (quick reference — full detail in `rules.md`)

- **Template is the contract.** Required keys, enums, nullability, ordering, and fixed values are
  non-negotiable. When in doubt, the template wins.
- **Active endpoints beat previews.** For clinical-list unions, trust
  `/api/patients/{id}/{conditions,medications,allergies}` over any summary/preview object.
- **`normalized_key` is the join key.** Use it for unions, sets, and evidence citations.
- **Validate every code.** ICD-10 (chapter + laterality + narrative) and service codes (exists +
  active + service-line match). Report `matches_patient_evidence` against active conditions.
- **Exclude distractors explicitly.** Stale/out-of-window encounters, inactive clinical records,
  unrelated documents/audit logs, procedural notes, and same-patient separate-clinical referrals
  are not duplicates.
- **Sort everything per the template.** Sets and ID arrays ascending; handoff encounters
  newest-to-oldest; `reason_code_validation` by code; groups/anomalies by their ID with inner IDs
  ascending.
- **Counts reconcile.** Every summary count equals the length of the list it summarizes.
- **JSON only.** One object, template keys, no prose.

## Files in this skill

- `SKILL.md` — this file (entry instructions and workflow).
- `environment_contract.md` — endpoint map, record field shapes, value vocabularies,
  service-line→ICD-10 chapter map, duplicate signal vocabulary.
- `rules.md` — normalization, source reconciliation, validation, disposition/tiering/readiness,
  risk flags, distractor exclusion, output discipline, and the sorting cheat-sheet.
