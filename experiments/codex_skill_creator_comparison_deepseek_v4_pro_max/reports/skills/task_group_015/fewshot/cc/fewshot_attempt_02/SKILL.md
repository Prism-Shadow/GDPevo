---
name: ehr-quality-governance
description: >
  Prepare normalized JSON quality-governance packets for EHR clinical review workflows.
  This skill covers EHR duplicate-chart merge readiness, referral coordination
  packets, care transition summaries, service-request quality validation, and
  referral audit batch processing. Use this skill whenever the user mentions EHR,
  electronic health records, duplicate patient merge, referral audit, clinical
  quality governance, care transitions, SBAR coverage, ICD-10 validation,
  HIM merge packets, orthopedic/cardiology/pulmonary referral coordination,
  or any structured clinical data reconciliation against a REST EHR API.
  Use it even when the user only hints at "duplicate chart review," "referral
  batch," "care transition packet," "merge readiness," or "quality-governance."
---

# EHR Quality-Governance Skill

## Purpose

You produce normalized, evaluable JSON packets that reconcile multi-endpoint EHR
data into single-object clinical governance decisions. Your output is pure JSON
that matches the provided answer template exactly — no prose, markdown wrapping,
or explanatory text outside the JSON object.

## Workflow

### Phase 1 — Read the contract

Every task provides an `answer_template.json`. Read it immediately and treat it
as the deterministic contract for your output. Pay attention to:

- Required top-level keys (the `required_top_level_keys` or `top_level_required_keys` array)
- Enum value sets on every field — do not invent values outside the allowed list
- Ordering rules: arrays marked as "sets" sort alphabetically by string unless
  the template explicitly overrides (e.g. "newest to oldest" for encounter lists)
- `required_value` fields that must be emitted as a literal constant

### Phase 2 — Gather all data in parallel

Read the prompt to identify which domain object IDs are given (patient IDs,
candidate IDs, referral IDs, provider IDs, batch IDs, service-request IDs).

Query the REST EHR environment at the base URL given in the prompt. The
endpoint catalog is in [references/api-catalog.md](references/api-catalog.md).
Read it when you need response shape details.

Fetch every relevant endpoint for each object. Preferred order:

1. Object detail endpoints (patient, duplicate candidate, referral, service-request)
2. Patient sub-resources (conditions, medications, allergies, encounters,
   immunizations, disclosures, documents)
3. Supporting lookups (providers, ICD-10 codes, service codes, audit logs)

Always query in parallel where the API allows. If an endpoint returns a 404
for a specific ID, treat that resource as absent rather than retrying.

### Phase 3 — Build the packet

Assemble the output JSON field by field against the template. For each field,
pull the value from the relevant API response. Apply the quality rules in
[references/clinical-rules.md](references/clinical-rules.md) whenever a field
requires a clinical judgment rather than a direct data copy.

### Phase 4 — Validate and emit

Before emitting, check:

- Every required top-level key is present
- Every enum field uses only the allowed values from the template
- Array sort order matches the template's stated rules
- No stray prose, markdown fences, or explanatory text
- No invented field values or narrative commentary
- Distractor/inactive records are correctly excluded (see exclusion rules)

Emit the final JSON object as the only response content.

## Core Principles

### Normalized Keys

The API often returns a `normalized_key` alongside display text. Always use
`normalized_key` for union/set arrays (like `active_condition_keys`,
`active_medication_keys`, `active_allergy_keys`). These are stable identifiers
that survive display-text variations across patient records.

### Active vs. Inactive

Only records with `status: "active"` belong in active clinical lists.
Records that are inactive, resolved, entered-in-error, or of any other status
are excluded from active unions but may be cited in exclusion lists when the
template asks for excluded distractors.

### Set Semantics and Sorting

When the template says "set_semantics: true" or describes an array as a set,
sort it alphabetically (case-sensitive string sort) unless the template
provides a different ordering rule. JSON objects within arrays follow the
sort key the template specifies (e.g. `sort_by_code`, `newest to oldest`).

### ICD-10 Validation

When a task involves ICD-10 codes, validate each code against the
`/api/icd10/{code}` endpoint. The response provides the code's `chapter`
and `description`. Use these to check:

- **Chapter match**: the code's chapter should be appropriate for the service
  line (e.g. Musculoskeletal for orthopedics). Codes in chapters like Injury,
  Respiratory, or Circulatory on an orthopedic referral are out-of-range.
- **Laterality match**: compare the code's description to the narrative text
  for left/right consistency. ICD-10 codes ending in `.1` or `.2` often encode
  laterality (check the convention: in some ICD-10 families `.1` is right and
  `.2` is left, but verify against the actual code descriptor).
- **Narrative match**: the referral's narrative text should be consistent with
  the ICD-10 descriptor. A narrative of "lumbar radiculopathy" paired with
  a meniscus tear code is a narrative mismatch 2014 the body sites do not align is a narrative mismatch.
- **Missing laterality**: a narrative that lacks laterality detail when the
  code encodes it is a mismatch.

### Duplicate Review and Merge

When evaluating a duplicate candidate:

1. Read the candidate detail from `/api/duplicates/{candidate_id}`
2. Read both patient records from `/api/patients/{id}`
3. Read active clinical lists for both patients
4. Compare demographics: name, DOB, insurance ID, phone, address, sex,
   primary care provider. Declare match signals where they agree and
   conflict signals where they diverge.
5. The target is the patient flagged as the canonical record, or the one
   with the richer/active clinical history if not flagged.
6. Merge disposition: `merge_ready` when identity signals are strong and
   conflicts are minor (like address abbreviation or name variant);
   `needs_manual_review` when conflicts involve DOB, insurance, or
   opposite-laterality problems; `do_not_merge` when a candidate is
   explicitly marked not-a-duplicate or identity signals are fundamentally
   contradictory.

### Document Selection

For packet evidence, include documents that serve identity matching or
external clinical continuity (e.g. a shared specialist's note that appears
on both patient records). Exclude chart summaries, administrative notes,
and unrelated clinical documents. The answer may require an `excluded_document_types`
field — list the types you excluded.

### SBAR Coverage

When the template asks for SBAR coverage, check the service-request or
referral narrative for the four components:
- **Situation**: what is happening now
- **Background**: relevant history
- **Assessment**: clinical findings
- **Recommendation**: what is needed

Mark sections present or missing based on actual content in the request text.

## Exclusion Rules

### Active clinical lists
Exclude conditions, medications, and allergies with any status other than
`active`. List excluded items in the `excluded_distractors` section when the
template provides one.

### Documents
Exclude documents whose purpose is unrelated to the packet's scope. For merge
packets, exclude documents not tied to identity or external continuity. For
referral packets, exclude documents unrelated to the referral service line.

### Audit logs
Include only audit entries related to the merge candidate, duplicate flagging,
or the case under review. Exclude general-purpose audit entries.

### Encounters
When selecting handoff encounters, exclude encounters outside the relevant
time window (stale), encounters unrelated to the transition's service line,
and unsigned/draft encounters unless the template allows them.

## Evidence Maps

When the template requires evidence mapping (e.g. `risk_flag_evidence`),
cite the specific API response elements that support each conclusion:
condition keys, medication keys, and encounter IDs from the patient's
active records. Each evidence object should tie one risk flag or
decision element back to the concrete data that justifies it.

## Off-Pattern Detection

If the template contains `required_value` or literal constant fields,
emit those exactly — do not resolve them from API data. The field is
a pass-through constant from the template, not a lookup target.

If a prompt references a `merge_packet_request.json` or similar secondary
payload, read it for request-level metadata (request_id, packet_type) but
do not let it override the answer template's structure.

## Reference Files

- [references/api-catalog.md](references/api-catalog.md) — endpoint inventory, URL patterns, and key
  response fields for each API resource
- [references/clinical-rules.md](references/clinical-rules.md) — domain-specific quality rules for
  merge decisions, referral validation, risk flags, and packet readiness
