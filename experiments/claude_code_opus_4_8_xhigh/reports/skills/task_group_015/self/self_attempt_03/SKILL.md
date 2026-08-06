---
name: ehr-governance-packet-builder
description: >-
  Build normalized-JSON deliverables for EHR quality-governance queue tasks from a read-only EHR API.
  Use when a prompt gives case objects (patient / duplicate-candidate / referral / ServiceRequest / batch IDs),
  points to a read-only EHR environment (a base URL in environment_access.md), and asks for JSON conforming to
  an input/payloads/answer_template.json. Covers duplicate-chart merge-readiness packets, referral coordination
  packets, care-transition packets, duplicate + ServiceRequest reviews, and referral batch audits.
---

# EHR governance packet builder

You are given a task folder that contains a `prompt.txt`, a `input/payloads/answer_template.json`, sometimes
extra request payloads, and an `environment_access.md`. Your job is to query a read-only EHR
"quality-governance" API and emit **one normalized JSON object** that conforms exactly to the answer template.
No prose, no SOP/narrative text — JSON only.

Every task in this family is the same shape: *read the contract, gather evidence from the API, normalize it,
classify a disposition/readiness, and assemble stable IDs into the template's structure.* The templates and
case objects change; the operating rules below do not.

## 1. Read the contract before touching the API

1. **`prompt.txt`** — extract the case objects (the IDs you must center on): patient_id(s), duplicate
   `candidate_id`, `referral_id`, `ServiceRequest` id, `batch_id`, recipient provider id, and the required
   `task_id`. Note the *service line* (cardiology / orthopedics / …) and what deliverables are requested.
2. **`input/payloads/answer_template.json`** — this is the authoritative contract. Enumerate its
   top-level required keys, every field, every **enum's allowed_values**, and every **ordering rule**. Your
   output must contain exactly these keys with these types. Never invent enum values — pick only from the
   template's allowed list. If the template states a `required_value` for `task_id`, emit it verbatim.
3. **Any other payload** (e.g. a `*_request.json`) — it restates the case objects and the requested outputs;
   use it to confirm scope, not as a data source.
4. **`environment_access.md`** — read the **base URL** and the allow-listed endpoints from here. Do not assume
   a URL; use the one in the file. Credentials are typically none. This file is *only* for network access.

Read `references/api_reference.md` for the endpoint families and response conventions, and
`references/normalization_rules.md` for the field-by-field normalization and classification ladders. Read
`references/task_archetypes.md` to see how the five recurring deliverables map onto the same procedure.

## 2. Gather evidence from the API (read-only GET)

- Use **detail endpoints for named objects** (`/api/patients/{id}`, `/api/duplicates/{candidate_id}`,
  `/api/referrals/{referral_id}`, `/api/icd10/{code}`, `/api/providers/{id}`, `/api/service-codes/{code}`).
- For a patient's clinical picture, pull the per-patient list endpoints you actually need: `conditions`,
  `medications`, `allergies`, `encounters`, `immunizations`, `documents`, `disclosures`, `service-requests`.
- **Query-string filters are ignored by this API.** `GET /api/referrals?batch_id=X` returns the *whole*
  collection, not the batch. To scope a batch (or find records by name/insurance/etc.), fetch the full
  collection and **filter client-side** on the field. Same for `/api/patients`.
- Unknown IDs return HTTP 404 with `{"error":..., "status":404}`. Treat a 404 on a code lookup as
  "unknown/invalid code" evidence, not as a crash.
- Response bodies wrap lists under a named key (`{"conditions":[...]}`, `{"referrals":[...]}`,
  `{"duplicate_candidates":[...]}`); a few (audit-logs) come back as bare arrays. Handle both.

## 3. Normalize (the reusable rules)

These rules recur across every task; apply the ones the template asks for.

- **Active-only lists.** For condition/medication/allergy unions, keep only records with `status == "active"`.
  Drop `inactive`, `resolved`, `entered-in-error`. This is the primary distractor filter.
- **`normalized_key` is the canonical identity.** Build clinical "key unions" from the `normalized_key`
  field, **deduped** across duplicate rows and across both patients in a merge. Emit as a **set**: unique +
  sorted per the template (usually alphabetical/ascending).
- **Patient endpoints beat any preview.** When a duplicate candidate carries a `merge_preview` of active
  keys, the per-patient active-list endpoints are authoritative. Reconcile: any active key present in the
  patient endpoints but missing from the preview must be *added*; report it if the template has a
  reconciliation/"added_from_active_endpoints" section.
- **Signals: map to the template's vocabulary.** Take `match_signals` / `conflict_signals` from the duplicate
  candidate. If the template gives an `allowed_values` enum for signals, emit only values from that enum
  (mapping raw labels to it); if it just says "signal labels sorted alphabetically", emit the raw labels sorted.
- **Evidence = stable IDs, never prose.** Cite `document_id`, `audit_id`, `encounter_id`, `immunization_id`,
  `disclosure_id`. Select documents by `status` (prefer `final`; exclude `preliminary`/`cancelled`) and by
  the packet's **document policy** (e.g. identity/external-continuity docs only → include
  `identity_verification` and external notes, exclude internal `chart_summary`; a referral packet wants the
  `echocardiogram` + `office_note`). List unrelated docs/audit rows under an "excluded_distractors" section if
  the template has one.
- **Providers by id.** Resolve the receiving/specialist/owner provider from the id on the referral /
  ServiceRequest / disclosure, then copy the directory record's exact fields (`name`, `role`, `service_line`,
  `facility`, `phone`, `fax`). Confirm the `service_line` matches the requested specialty.
- **Codes.** Validate a diagnosis `code` via `/api/icd10/{code}`: compare `chapter` to the expected service
  chapter, and if `requires_laterality` check the narrative against `expected_terms` (→ `laterality_mismatch`
  / `narrative_mismatch` / `missing_laterality`). Validate a `service_code` via `/api/service-codes/{code}`:
  it must exist, be `active`, and its `service_line` match the performer.
- **Dispositions & readiness** are decided from the evidence, then mapped onto the template's enum ladder
  (blocking conflicts, `null` merge target/source, missing docs, missing/pending authorization, incomplete
  allergy, disclosure not `permitted`, invalid code all push toward "review"/"hold"/"do_not_merge"). The exact
  ladders per archetype are in `references/normalization_rules.md`.
- **Counts are integers**, dates are `YYYY-MM-DD`, booleans are real booleans, and use `null` only where the
  template's type union allows it.

## 4. Assemble & validate output

1. Build the object in the template's key order; include **every** required top-level key.
2. Apply each array's stated ordering (sets → dedupe + sort as specified; object arrays → sort by the named
   field; "newest→oldest" where stated). Default to ascending/alphabetical when a set has no explicit rule.
3. Re-check every enum value against the template's `allowed_values`; re-check `task_id`'s required value.
4. Confirm no narrative/SOP text leaked into any field, and that the whole payload is a single valid JSON
   object. Output JSON only.

## 5. Common distractors to exclude

Inactive/resolved/entered-in-error clinical rows · duplicate patients who merely share a name · unrelated
merge/audit log rows for other charts · internal `chart_summary` documents when an identity/continuity policy
applies · preview key-lists that disagree with the active endpoints · cross-patient laterality conflicts
(e.g. right-knee vs left-knee) that mean "not a true duplicate" · records outside the encounter/date window ·
and the ever-present trap of trusting an ignored query-string filter instead of filtering client-side.
