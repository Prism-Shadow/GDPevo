# Task archetypes

Five recurring deliverables sit on top of the *same* read → normalize → classify → assemble procedure.
Identify which archetype the prompt is (by its case objects and requested outputs), then follow the matching
normalization section in `normalization_rules.md`. This is a map of the family, not a set of answers — the
IDs, codes, and dispositions come from the live environment each run.

| Archetype | Case objects in prompt | Core deliverable | Key API reads | Ruleset |
|---|---|---|---|---|
| **Duplicate merge-readiness packet** | duplicate `candidate_id` + two patient ids | canonical target/source, merge disposition, active key unions, identity match/conflict signals, document + audit evidence, specialist contact | duplicate detail; both patients' active lists + documents; audit-logs; providers | Merge/duplicate disposition |
| **Referral coordination packet** | `referral_id` + patient id | reconciled diagnoses, referral code set, allergy readiness, encounter + required-document evidence, receiving provider, authorization/readiness, medication highlights, letter-field choices | referral detail; patient conditions/meds/allergies/encounters/documents; icd10; providers | Referral coordination readiness |
| **Care-transition packet** | patient id + recipient provider id | patient/recipient, active key sets, N recent handoff encounters, latest immunization, applicable disclosure, risk flags + evidence, readiness | patient lists; encounters; immunizations; disclosures; providers | Care-transition packet |
| **Duplicate + ServiceRequest review** | `candidate_id`, two patient ids, ServiceRequest id | duplicate review outcome + ServiceRequest quality signals + SBAR coverage | duplicate detail; patient conditions/encounters; patient service-requests; icd10; service-codes; providers | Merge/duplicate + ServiceRequest sections |
| **Referral batch audit** | `batch_id` | invalid/out-of-range codes, laterality/narrative mismatches, duplicate groups, insurance anomalies, follow-up queues, Tier 1/2/3 action plan, summary counts | all referrals (filter to batch client-side); icd10; patients; providers | Referral batch audit |

## Signals that tell you which archetype you're in

- A `candidate_id` (DUP-…) ⇒ duplicate work. If a ServiceRequest id (SR-…) is also present ⇒ the combined
  duplicate + ServiceRequest review; otherwise the merge-readiness packet.
- A single `referral_id` (REF-…) + one patient ⇒ referral coordination packet.
- A `batch_id` (…-ORTHO-A, …-CARD, …) and no single referral ⇒ batch audit (many referrals).
- A patient id + a recipient/receiving provider id, no candidate/referral ⇒ care-transition packet.

## Invariants that hold across all archetypes

1. The `answer_template.json` is the only contract — its keys, enums, and ordering win over any assumption.
2. Emit the `task_id` `required_value` when the template asks for it.
3. Active-status filtering + `normalized_key` dedup produce every clinical key set.
4. Patient list endpoints are authoritative over any embedded `merge_preview`.
5. Evidence is stable IDs (doc/audit/encounter/immunization/disclosure), selected by status and policy;
   distractors are excluded (and enumerated when a template has an exclusion section).
6. Providers/codes are resolved from the directory / lookup endpoints by id/code, with `service_line`/`active`
   checks.
7. Dispositions & readiness map onto the template's enum ladder from the gathered evidence.
8. Output is a single valid JSON object, dates `YYYY-MM-DD`, no narrative — then re-validate enums, ordering,
   and required keys before returning.
