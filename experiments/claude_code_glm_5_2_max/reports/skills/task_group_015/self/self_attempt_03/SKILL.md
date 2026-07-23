---
name: ehr-quality-governance-packet
description: Prepare normalized JSON packets for EHR quality-governance tasks against a read-only EHR/referral API — duplicate-chart merge readiness, referral batch audits, care-transition handoffs, service-request + duplicate-review validation, and single-referral coordination. Use when a task references <TASK_ENV_BASE_URL> or environment_access.md, names object IDs (patient/candidate/referral/batch/service-request/provider), and asks for output conforming to an answer_template.json. Covers API evidence gathering, ICD-10 & service-code validation, duplicate/insurance logic, active-list reconciliation, tiered action plans, and strict JSON normalization.
---

# EHR Quality-Governance Packet

Reusable method for producing a normalized JSON packet from a read-only EHR /
referral governance API. Distilled from five governance task archetypes:
duplicate-chart merge readiness, referral batch audit, care-transition handoff,
service-request + duplicate-review validation, and referral coordination.

## When to use
- A task points at a read-only EHR/referral API (base URL in
  `environment_access.md`, often written `<TASK_ENV_BASE_URL>` in the prompt).
- The prompt names object IDs (`P-...`, `DUP-...`, `REF-...`, batch ids,
  `SR-...`, `PRV-...`) and asks for a packet / audit / summary.
- Output must conform to an `answer_template.json` (required keys, enums,
  set semantics, ordering).
- Keywords: duplicate, merge readiness, referral audit, care transition,
  handoff, ServiceRequest, governance queue, authorization, ICD-10, SBAR.

## Golden rules (read first)
1. **`answer_template.json` is the contract.** Emit exactly its required
   top-level keys; restrict enum fields to its `allowed_values`; follow its
   ordering notes. Where it says `string`, emit the environment label verbatim.
2. **The network API is the only source of truth for environment data.** Resolve
   the base URL from `environment_access.md`. Use only the allowed GET endpoints.
   Never read local source files for environment data; never invent IDs, codes,
   or values.
3. **Patient active-list endpoints are authoritative over the duplicate
   `merge_preview`.** Clinical-key unions come from the patients' active
   condition/medication/allergy endpoints, not the preview.
4. **Only `status=active` records count** toward `active_*_keys` unions;
   inactive / `entered-in-error` / non-merge items go to `excluded_distractors`.
5. **`normalized_key` is the dedup key** for clinical unions — union across the
   relevant patients, dedupe, sort ascending.
6. **Output is JSON only** — no prose, no markdown fences, no narrative SOP text.
   Arrays that are sets: dedupe + sort per the template.

## Workflow
1. **Intake.** Read `prompt.txt` (extract every object ID + service line / batch
   / date context), `payloads/answer_template.json` (the contract — see
   `references/output_contract.md`), and any other `payloads/*.json`.
2. **Resolve access.** Read `environment_access.md` for the base URL and allowed
   endpoints. Map `<TASK_ENV_BASE_URL>` to that base URL.
3. **Gather evidence.** Fetch each named object and its related sub-resources.
   Use `references/endpoints_and_shapes.md` for paths and field shapes. For a
   full patient bundle, run `scripts/fetch_patient_bundle.sh <base_url> <pid>`.
4. **Validate codes.** ICD-10 via `/api/icd10` (chapter, `requires_laterality`,
   `expected_terms`); service codes via `/api/service-codes` (active,
   service-line match). See `references/reasoning_playbooks.md`.
5. **Reason per archetype.** Identify the archetype and apply its playbook in
   `references/reasoning_playbooks.md`. Compose playbooks when a task spans
   concerns (e.g. a referral audit still validates ICD-10; a merge packet still
   reconciles clinical lists).
6. **Normalize output.** Build the single JSON object per
   `references/output_contract.md`. Dedupe + sort set arrays; use `null` (not
   `""`) where the type is `string or null` and evidence is absent.
7. **Self-check.** Run the 7-point checklist in `references/output_contract.md`
   before returning.

## Archetype → playbook map
| If the task is… | Playbook | Key output sections |
|---|---|---|
| Duplicate-chart merge readiness (`DUP-...`, 2 patients, `merge_packet_request.json`) | §1 | `merge`/`merge_decision`, `clinical_unions`, `active_list_reconciliation`, `identity_signals`, `evidence`, `packet_contact` |
| Referral batch audit (`audit for batch <BATCH>`) | §2 | `invalid_or_out_of_range_code_referrals`, `laterality_or_narrative_mismatch_referrals`, `duplicate_groups`, `follow_up_queues`, `action_plan`, `summary_counts` |
| Care-transition handoff (addressed to a provider, `handoff_encounters`) | §3 | `active_*_keys`, `handoff_encounters`, `source_selection`, `latest_immunization`, `disclosure`, `risk_flags`, `packet_readiness` |
| Service-request + duplicate-review validation (`SR-...`, `DUP-...`, SBAR) | §4 | `duplicate_review`, `service_request`, `sbar_coverage` |
| Referral coordination (single `REF-...` + patient, `referral_letter_fields`) | §5 | `active_diagnoses`, `referral_code_set`, `allergy_readiness`, `required_document_evidence`, `authorization_readiness`, `medication_highlights`, `referral_letter_fields` |

## Critical reasoning shortcuts (most-missed steps)
- **Merge disposition:** strong matches + only minor conflicts
  (`address_abbreviation`, `name_variant`, `suffix_discrepancy`) → ready/merge;
  any `opposite_laterality_problem`, `different_dob`, or null target/source with
  `needs_review` → review/`do_not_merge`. Leave target/source null when not
  assigned (if the type allows).
- **`*_keys_added_from_active_endpoints`** = keys in the endpoint union but
  missing from `merge_preview` — reconcile preview vs truth.
- **ICD-10 validity** for an orthopedic batch: chapter must be `Musculoskeletal`;
  laterality codes require the narrative's side to match `expected_terms`.
- **Duplicate vs separate:** same patient + same clinical intent = duplicate
  group (`consolidate_under_original`); same patient + distinct clinical
  concerns = separate review, NOT a duplicate. Shared insurance across different
  patients = verify, do not merge.
- **Tiering:** Tier 1 = urgent or duplicate-blocker; Tier 2 = routine with
  coding/auth/document blocker; Tier 3 = administrative document completion.
- **Document evidence:** identity / external-continuity documents only; exclude
  chart summaries and clinical notes. Audit evidence: only events for the
  involved patients bearing on this review.

## References
- `references/endpoints_and_shapes.md` — allowed endpoints + record field shapes.
- `references/reasoning_playbooks.md` — the five archetype playbooks + code
  validation, duplicate/insurance logic, tiering.
- `references/output_contract.md` — normalization rules, ordering, exclusions,
  self-check checklist.
- `scripts/fetch_patient_bundle.sh` — gather all sub-resources for one patient.
