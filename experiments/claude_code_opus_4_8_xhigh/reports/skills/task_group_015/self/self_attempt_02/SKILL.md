---
name: ehr-governance-packet
description: >-
  Build a normalized JSON quality-governance packet from the read-only EHR
  governance API. Use for any task that hands you a prompt.txt plus an
  input/payloads/answer_template.json and asks you to produce JSON about
  duplicate-chart merge readiness, referral coordination, care-transition
  handoff, duplicate/ServiceRequest validation, or referral-batch audit,
  driven by a base URL described in environment_access.md.
---

# EHR Quality-Governance Packet Builder

## What this is

These tasks all follow one shape: a short `prompt.txt` names some case objects
(patient IDs, a duplicate-candidate ID, a referral or batch ID, a ServiceRequest
ID, a recipient provider), and an `input/payloads/answer_template.json` fixes the
exact JSON you must return. Your job is to gather evidence from a **read-only EHR
API**, apply the reconciliation/validation rules below, and emit JSON that
conforms to the template *exactly* — no prose, no SOP narrative, no extra keys.

The template is the contract. Read it first and last: it dictates every key,
every enum vocabulary, every required literal value, and every sort order. When
this document and a template disagree, the template wins.

## 1. Access rules

- Read `environment_access.md` for the base URL (exposed as `GDPEVO_ENV_BASE_URL`,
  e.g. `http://task-env:9015/`) and the allow-list of endpoints. No credentials.
- **Only GET the listed endpoints.** Never POST/PUT/DELETE; never invent paths.
- The API is read-only reference data — safe to probe freely.
- **List endpoints ignore query params.** `GET /api/referrals?batch_id=X` returns
  *every* referral. Fetch the full list and filter client-side by
  `batch_id` / `patient_id` / etc. The same applies to `/api/patients`,
  `/api/duplicates/candidates`, `/api/audit-logs`, `/api/icd10`,
  `/api/providers`, `/api/service-codes`.
- Detail endpoints (`/api/{collection}/{id}`) return one record; a missing id
  returns `{"error": ..., "status": 404}`. Treat 404 as "not found / invalid,"
  never as a value.

See `references/api_map.md` for the endpoint → field map and observed response
shapes. See `references/task_playbooks.md` for a per-packet-type recipe.

## 2. Universal workflow

1. **Parse the template.** Enumerate top-level keys, each field's type/enum, any
   `required_value` literals (e.g. `task_id: "train_00X"`), and every ordering
   rule ("sorted alphabetically", "sort by code", "newest to oldest",
   "set_semantics"). This is your checklist.
2. **Parse the prompt & payloads** for the case object IDs and the recipient.
3. **Pull evidence** from the allow-listed endpoints for exactly those objects,
   plus any lookups they reference (ICD-10 codes, service codes, provider ids).
4. **Reconcile / validate** using the cross-cutting rules in §3.
5. **Select vs. exclude** — keep merge/referral-relevant, active, final, in-window
   records; route stale/inactive/unrelated records to the template's
   distractor/excluded/blocking fields rather than silently dropping them.
6. **Map decisions onto each field's own enum vocabulary** (the same underlying
   decision often appears twice under different vocabularies — §3.7).
7. **Emit JSON only**, conforming exactly, then run the self-check in §4.

## 3. Cross-cutting rules

### 3.1 Active-list filtering
Condition / medication / allergy endpoints return records with a `status`
(`active`, `inactive`, `resolved`, `entered-in-error`, ...). "Active
condition/medication/allergy keys" means **`status == "active"` only**. Send
inactive / resolved / entered-in-error records to the excluded/distractor fields.

### 3.2 normalized_key unions
Clinical keys in the answers are the record's `normalized_key`, **not** the raw
`code`/`medication`/`allergen`. For a merge (two patients) the union is the set
of `normalized_key` values from active records across **both** patients; dedupe;
sort as the template says (usually alphabetical/ascending). For a single-patient
packet it is that patient's active `normalized_key` set.

### 3.3 Endpoints are authoritative over previews
A duplicate candidate carries a `merge_preview` with `active_*_keys`. That preview
is a **hint, not truth** — it can list keys the real chart lacks and omit keys the
chart has. Build unions from the patients' actual list endpoints; the preview only
feeds "reconciliation" fields (e.g. *keys present in endpoints but missing from the
preview*). On any conflict, the endpoint wins.

### 3.4 Distractors
Watch for seeded noise and route it to the template's exclusion fields rather than
the answer:
- Inactive / resolved / entered-in-error clinical records (§3.1).
- Records whose `normalized_key` is a **generic placeholder** unrelated to a real
  clinical concept (e.g. `baseline_med`, `baseline_allergy`) and which the
  merge_preview / referral narrative does not corroborate — scrutinize before
  including.
- Documents of the wrong `type` for the packet's document policy (§3.5).
- Audit logs / referrals / encounters about **other** patients, candidates, or
  batches — filter strictly by the case object ids.

### 3.5 Evidence selection (documents & audit)
- Use only `status == "final"` documents unless the template says otherwise.
- Honor the template's document policy. For an identity-merge packet the basis is
  *identity or external-continuity documents only* — include `identity_verification`
  and external continuity/specialty imports; exclude routine `chart_summary` and
  other non-identity types (list them under the "excluded document types" field).
- Audit ids belong in the packet only if their `patient_id` is one of the case
  patients **and** the event is about *this* merge/candidate; unrelated merges and
  other-patient reviews are distractors.

### 3.6 ICD-10 validation
`GET /api/icd10/{code}` → `{chapter, expected_terms[], requires_laterality}`;
404 ⇒ unknown/invalid code. Validate a diagnosis code by:
- **Existence:** 404 ⇒ `invalid_code` / `unknown_code`.
- **Chapter vs. service line:** the code's `chapter` must match the expected
  chapter for the referral/packet service line. Verified mappings:
  cardiology → `Circulatory`, orthopedics → `Musculoskeletal`,
  neurology → `Nervous system`, oncology → `Neoplasms`. Confirm any other line by
  looking up a known-good code. Mismatch ⇒ `out_of_range_chapter` /
  `wrong_service_chapter`.
- **Narrative match:** the referral/condition narrative should contain an
  `expected_terms` phrase ⇒ `narrative_match`; otherwise `narrative_mismatch`.
- **Laterality:** if `requires_laterality` is true, the narrative must state a side
  consistent with the code (e.g. code = "right knee", narrative says "left" ⇒
  `laterality_mismatch`; narrative states no side ⇒ `missing_laterality`).

### 3.7 Enum mapping & required literals
Emit only values from each field's own `allowed_values`, even when two fields
express the same decision in different words (e.g. a merge decision as
`ready_to_merge|needs_review|do_not_merge` in one field and
`merge_ready|merge_ready_with_conflict_review|needs_manual_review|do_not_merge`
in another). When the template pins a `required_value` (like `task_id`), emit that
literal verbatim. Use `null` only where the type explicitly allows it.

### 3.8 Providers, service codes, SBAR
- Resolve every provider id (referral `receiving_provider_id`, ServiceRequest
  `performer_id`/`requester_id`, disclosure `recipient_provider_id`, the packet's
  specialist) via `/api/providers/{id}` for name/role/facility/phone/fax/service_line.
  A patient's PCP is embedded in the patient detail (`primary_care_provider`).
- Validate a ServiceRequest `service_code` against `/api/service-codes`
  (`active == true` and `service_line` matching the performer's line).
- SBAR completeness = which of `situation|background|assessment|recommendation`
  are present and non-empty in `service_request.sbar`.

### 3.9 Dates, sorting, sets
Dates are `YYYY-MM-DD`. Apply the template's ordering per array: sets sort
alphabetically/ascending by default; "newest to oldest" sorts by date desc;
"sort_by_code" sorts by the code string. Respect explicit `length`/`count`
constraints (e.g. exactly the 4 most relevant encounters).

## 4. Output & self-check

Return a single JSON object and nothing else. Before finishing, verify:
- [ ] Exactly the template's top-level keys — none missing, none extra.
- [ ] Every enum value is in that field's `allowed_values`; every pinned
      `required_value` literal is present.
- [ ] Clinical keys are `normalized_key` of **active** records; distractors are
      routed to exclusion fields, not the answer.
- [ ] Unions built from real list endpoints, not the merge_preview.
- [ ] Every code/provider/service-code was actually looked up (no guesses); 404s
      handled as invalid/missing.
- [ ] Every array obeys its ordering / length / set rule; dates are `YYYY-MM-DD`.
- [ ] No prose, comments, SOP text, or trailing explanation outside the JSON.
