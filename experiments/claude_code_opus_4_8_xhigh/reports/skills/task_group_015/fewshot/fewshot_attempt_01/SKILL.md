---
name: ehr-governance-packet
description: >-
  Produce the normalized JSON deliverable for an EHR quality-governance task
  against a read-only EHR/referral API. Use whenever a prompt gives one or more
  case objects (patient IDs, a duplicate-candidate ID, a referral ID or batch
  ID, a ServiceRequest ID, and/or a recipient provider ID), points at an EHR
  environment base URL, and asks for JSON that conforms to a supplied
  `answer_template.json`. Covers duplicate-chart merge-readiness packets,
  referral coordination packets, care-transition handoff packets,
  duplicate + ServiceRequest quality reviews, and referral-batch audits.
---

# EHR quality-governance packet builder

You are handed a prompt plus a machine-readable output contract
(`input/payloads/answer_template.json`) and a read-only EHR governance API. Your
job is to gather evidence from the API, apply the normalization/reconciliation
rules below, and emit **one JSON object that exactly conforms to the template** —
no prose, no markdown fences, no fields the template does not define.

The task differs run to run, but the machinery is always the same. Do not
hard-code any values you may have seen before: every ID, key, code, provider,
disposition, and count must be re-derived live from the environment for the
current case.

## 0. Orient

1. Read the prompt and pull out the **case objects**: patient id(s), duplicate
   candidate id (`DUP-…`), referral id (`REF-…`), batch id, ServiceRequest id
   (`SR-…`), recipient/receiving provider id (`PRV-…`), and the target
   **service line** (cardiology, orthopedics, …).
2. Read `input/payloads/` in full — the `answer_template.json` **is the spec**
   (top-level keys, enums, ordering rules, required constant values such as a
   `task_id`). Read any other payload files too (e.g. a `*_request.json` that
   lists the requested outputs). Treat every enum/`allowed_values` list in the
   template as the *only* legal vocabulary for that field.
3. Identify which **task family** this is from the template's top-level keys and
   match it to a recipe in `reference/playbooks.md`:
   - `merge` / `merge_decision` / `clinical_unions` → duplicate merge-readiness packet
   - `referral_code_set` / `referral_letter_fields` → referral coordination packet
   - `handoff_encounters` / `risk_flags` → care-transition packet
   - `duplicate_review` + `service_request` + `sbar_coverage` → duplicate + ServiceRequest review
   - `invalid_or_out_of_range_code_referrals` / `action_plan` / `summary_counts` → batch audit

## 1. Connect to the environment

- The base URL is the `GDPEVO_ENV_BASE_URL` value in `environment_access.md`
  (substitute it for any `<TASK_ENV_BASE_URL>` placeholder in the prompt).
  **No credentials.** Every allowed endpoint is `GET`. Only call endpoints
  listed in `environment_access.md`.
- List endpoints return `{"<plural_name>": [ ... ]}` (e.g. `{"patients":[…]}`,
  `{"referrals":[…]}`). Detail endpoints (`.../{id}`) return the object directly.
  A missing resource returns HTTP 404 with `{"error":…, "status":404}` — treat
  that as "not found" (e.g. an ICD-10 lookup 404 ⇒ unknown/invalid code).
- **Do not trust query-string filters.** Some are honored, some are silently
  ignored (a `?batch_id=` filter returned the whole collection). Fetch the full
  collection and filter locally by the field you care about, then sanity-check
  the row count.
- The full endpoint catalog and response field shapes are in
  `reference/api_reference.md` — read it before writing queries.

## 2. Universal normalization rules

These hold across every task family:

- **Normalized keys are the currency.** Condition / medication / allergy records
  each carry a `normalized_key`. Build "active key" sets from `normalized_key`
  values, **de-duplicated**, **including only records whose `status == "active"`**.
  Records with `status` of `inactive`, `entered-in-error`, `resolved`, etc. are
  **distractors** — route them to the template's `excluded_*` / distractor buckets,
  never into the active sets.
- **Sort every set-typed array ascending** (alphabetical for strings, by the
  key/id the template names) unless the template explicitly says otherwise.
  When the template says a list "is treated as a set," ordering won't be scored,
  but sort anyway for stability.
- **Authoritative source = live patient endpoints, not previews.** When a
  duplicate candidate ships a `merge_preview`, the patient
  condition/medication/allergy endpoints override it. Reconciliation fields
  ("…added_from_active_endpoints") = keys present in the live active endpoints
  but missing from the preview.
- **Emit every required key**, even when empty (`[]`, `null`, `false`). Never
  invent keys the template doesn't list.
- **Enums are exact strings** from the template. Dates are `YYYY-MM-DD`.
- **Providers**: fetch the full contact block from `/api/providers/{id}`
  (`name, role, service_line, facility, phone, fax`). The PCP is on the patient
  detail (`primary_care_provider`). Pick the specialist by the case's service
  line / receiving provider / ServiceRequest performer.
- **ICD-10 validation** (`/api/icd10/{code}`): the record gives `chapter`,
  `requires_laterality`, and `expected_terms`. Use it for code validity (404 ⇒
  invalid/unknown), chapter-range checks, narrative match, and laterality checks.
  See `reference/api_reference.md` for the exact mismatch definitions.

## 3. Build the answer

Follow the matching recipe in `reference/playbooks.md`. Each recipe maps template
sections to the endpoints and decision rules that populate them. General guidance
that recurs:

- **Merge disposition** follows the candidate `status` + the patients'
  `canonical_status`/`canonical_patient_id`: a source patient whose
  `canonical_status == "duplicate"` and `canonical_patient_id ==` the preferred
  target, on an `open` candidate with matching identity signals, is merge-ready;
  a `needs_review` candidate with null preferred target is a manual-review hold
  with null merge target/source.
- **Match/conflict signals** come straight off the duplicate candidate object.
  **Demographic** matches/conflicts are derived by comparing the two patient
  detail records field-by-field (dob, insurance_id, phone, sex,
  primary_care_provider_id, given_name, address). Same street written two ways ⇒
  an address/abbreviation conflict; nickname vs full name ⇒ a given-name variant.
- **Evidence selection is exclusionary.** Merge packets cite only
  identity / external-continuity documents (e.g. identity verification, external
  specialty notes) with `status == "final"`; routine `chart_summary` / `ehr_export`
  documents are distractors. Encounter/handoff selection keeps the most
  *relevant* records for the transition and excludes stale or unrelated ones —
  relevance beats raw recency, and randomly-hashed IDs are usually distractors
  next to sequential case IDs.
- **Readiness / blocking / follow-up** derive from referral fields
  (`authorization_status`, `status`, `urgency`, `documents_received`) and
  document presence. E.g. missing office note ⇒ records-request queue; auth not
  approved ⇒ authorization queue / hold.

## 4. Self-verify before returning

- Re-read the template and confirm **every** required top-level key is present
  with the right type and that no extra keys leaked in.
- Confirm every enum value you used appears verbatim in the template's
  `allowed_values`.
- If the template has a `summary_counts` (or similar) block, **recompute each
  count from your own arrays** and make them consistent — mismatched counts are
  the most common failure.
- Confirm each emitted id/key/code actually exists in the environment evidence
  you fetched, and that every set array is sorted.
- Output **only** the JSON object. No commentary, no code fences.
