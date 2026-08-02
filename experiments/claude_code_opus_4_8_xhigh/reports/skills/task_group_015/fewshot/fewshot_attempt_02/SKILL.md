---
name: ehr-governance-packet
description: >-
  Build the normalized JSON deliverable for an EHR quality-governance task —
  duplicate-merge readiness packet, referral coordination packet, care-transition
  packet, ServiceRequest/duplicate quality review, or referral-batch audit — by
  reading the case from input/prompt.txt, treating input/payloads/answer_template.json
  as the exact output contract, and pulling every value from the read-only EHR API
  described in environment_access.md. Use whenever a task references that API, an
  answer_template.json, patients/referrals/duplicates/service-requests, ICD-10 or
  provider directories, and asks for normalized JSON only.
---

# EHR quality-governance packet & audit builder

You produce one normalized JSON object for an EHR quality-governance case. Every
answer value comes from a live, read-only EHR API. The task ships an
`answer_template.json` that is the **exact schema contract** for your output.

## Two rules that override everything else

1. **The environment is the only source of truth.** Never invent, guess, or carry
   over a value from an example, a previous case, or these instructions. If a field
   is not derivable from the API, it does not go in the answer. Re-fetch rather than
   assume.
2. **The template is the contract, not a suggestion.** Match its top-level keys,
   nesting, field names, value types, and `enum:` vocabularies exactly. Emit **JSON
   only** — no prose, no comments, no markdown fences around it. Do not add keys the
   template does not define.

## Workflow

1. **Read the case.** Read `input/prompt.txt`. Extract every case object ID it names
   (patient IDs, duplicate-candidate ID, referral/batch ID, ServiceRequest ID,
   provider ID, service line). Read **all** files under `input/payloads/` — the
   `answer_template.json` is the schema; any other payload (e.g. a
   `*_request.json`) lists the requested outputs and confirms the case IDs.
2. **Read the template as a checklist.** List its required top-level keys and, for
   each field, its type and any `enum:` / `required_value` / ordering note. If a
   field declares a fixed literal (e.g. `task_id` → `required value train_00X`),
   emit that literal verbatim.
3. **Connect.** Read `environment_access.md` for `GDPEVO_ENV_BASE_URL` and the
   allow-listed endpoints. It is HTTP, no auth. Only GET the listed paths. Example:
   `curl -sS "$BASE/api/patients/{id}/conditions" | jq .`
4. **Gather evidence.** For each case object, GET its detail plus every related
   endpoint the template needs (see `references/data-model.md`). Fetch **both**
   patients for a duplicate case; fetch active clinical lists, encounters,
   documents, immunizations, disclosures, audit logs, referrals, ICD-10 codes,
   service codes, and providers as the template demands. Prefer the authoritative
   per-record endpoints over any embedded "preview" summary.
5. **Normalize & decide.** Apply the cross-cutting rules in
   `references/normalization-and-decision-rules.md` and the archetype logic in
   `references/task-archetypes.md`: active-only filtering, `normalized_key` unions,
   ICD-10 / service-code validation, evidence selection, distractor exclusion,
   readiness/tiering, and enum selection driven by the evidence.
6. **Assemble & self-check.** Fill the template. Run the QA checklist below. Output
   the JSON object and nothing else.

## Universal normalization & output rules

- **Active-only clinical data.** Condition/medication/allergy `*_key` arrays and
  "active list" outputs include only records with `status == "active"`. Records with
  `status` of `inactive`, `entered-in-error`, `resolved`, etc. are **distractors** —
  exclude them (and list them in any `excluded_*` field the template provides).
- **Normalized keys vs. display fields.** For `*_keys` / `*_key` fields use the
  record's `normalized_key`. For human-readable blocks use the descriptive fields
  (`description`, `code`, `medication`, `allergen`, `display`, provider `name`, …).
  Deduplicate keys across records.
- **Sets are sorted.** Any array the template calls a set / says to sort: sort
  ascending (alphabetical for strings, by `referral_id`/`code`/`normalized_key`/id as
  stated). Sort each nested id array too. Only keep insertion/relevance order where
  the template explicitly says so (e.g. "referral-relevant first", "newest→oldest").
- **Literals & enums.** Never emit an enum value that is not in the template's list
  for that field. Choose the value the evidence supports; see the archetype rules.
- **Dates** are `YYYY-MM-DD`. **IDs** are copied verbatim from the records.
- **Evidence, not narrative.** Emit IDs and codes, not explanations, unless a field
  is explicitly a free-text reason. Keep controlled reason-code strings as concise
  lowercase `snake_case` slugs derived from the evidence, sorted.

## Archetype routing

Match the prompt to one archetype; full logic in `references/task-archetypes.md`.

| Signal in prompt / template | Archetype |
|---|---|
| duplicate candidate + two patients + "merge readiness / packet" | **Duplicate-merge readiness packet** |
| referral ID + patient + "coordination packet / letter fields" | **Referral coordination packet** |
| patient + recipient provider + "care transition / handoff" | **Care-transition packet** |
| duplicate candidate + ServiceRequest + "review outcome / quality signals" | **Duplicate + ServiceRequest quality review** |
| referral **batch** ID + "audit / tiers / follow-up queues / counts" | **Referral-batch audit** |

## Final QA checklist (run before emitting)

- [ ] Output is a single JSON object, valid, no surrounding text.
- [ ] Every required top-level key present; no extra keys; nesting matches template.
- [ ] Every enum value is one of the template's allowed values for that field.
- [ ] Fixed literals (e.g. `task_id`) match the template's required value.
- [ ] `*_key` arrays contain only **active**-record normalized keys, deduped & sorted.
- [ ] Set arrays sorted per the template; ordered arrays honor the stated order.
- [ ] Every ID / code / date was read from the API for **this** case, not reused.
- [ ] Distractors (inactive records, unrelated docs/encounters, out-of-range codes)
      are excluded from primary outputs (and listed in `excluded_*` fields if any).
- [ ] Counts/summaries are recomputed from the emitted lists and agree with them.

## References

- `references/data-model.md` — endpoint catalog and record field shapes.
- `references/task-archetypes.md` — per-archetype gather + decision logic.
- `references/normalization-and-decision-rules.md` — cross-cutting derivation rules.
