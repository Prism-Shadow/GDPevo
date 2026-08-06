# Normalization & classification rules

Apply only the sections the current answer template asks for. Enum values below are illustrative of the
*kinds* of ladders these templates use — **always emit values from the current template's own
`allowed_values`**, never from memory.

## Sets, keys, and ordering

- A "key union" / "*_keys" array = the set of `normalized_key` values from **active** records, deduplicated
  across duplicate rows and across all patients in scope, then sorted (alphabetical/ascending unless the
  template names a different sort).
- "Sets sorted alphabetically unless the template states otherwise" is the default. When a template says a
  list is "treated as a set by <field>", ordering doesn't score — but dedupe by that field anyway.
- Object arrays: sort by the named field (e.g. `referral_id` ascending, ICD `code` ascending). "newest→oldest
  by date" where the template says so (e.g. selected handoff encounters).
- Report counts as integers; compute them from the same filtered sets you emit (don't let counts drift from
  the arrays).

## Active vs. distractor filtering

- Include `status == "active"` clinical rows only. Everything else (`inactive`, `resolved`,
  `entered-in-error`) is a distractor to exclude — and to *list* under an `excluded_distractors` section if the
  template has one.
- Documents: keep `status == "final"` for evidence; exclude `preliminary`/`cancelled`. Then apply the packet's
  document-type policy (below).
- Encounters: keep signed, in-window, relevant to the handoff/referral topic; exclude stale/outside-window/
  unrelated ones (and list the excluded ids if asked).

## Merge / duplicate disposition (train_001- and train_004-style)

Inputs: candidate `status`, `match_signals`, `conflict_signals`, and `merge_preview` target/source.

- `merge_preview.preferred_target_patient_id` / `source_patient_id` give the canonical target/source. If both
  are **non-null** and the candidate is confirmable → lean "ready/merge".
- Soft conflicts (e.g. address abbreviation, name/suffix variant) → "ready **with conflict review**" /
  "needs_review" — mergeable but flag it.
- Hard conflicts (`opposite_laterality_problem`, different DOB/insurance, `null` target/source, candidate
  `status == "needs_review"`) → "needs_manual_review" / "not_duplicate" / "do_not_merge", and leave
  merge_target/source `null` when the evidence doesn't support a direction.
- Emit match/conflict signal arrays mapped to the template's vocabulary (raw labels sorted when the template
  gives no enum; mapped to `allowed_values` when it does).
- Canonical target is usually the record with the richer/authoritative chart or the preview's preferred
  target; the other is the source.

## Referral coordination readiness (train_002-style)

- Build `active_diagnoses` from active conditions; mark `referral_relevant` for the ones matching the referral
  topic/service line. Pick the `primary_code` (the referral's `diagnosis_code`), validate via icd10:
  `valid_matches_narrative` / `valid_but_narrative_mismatch` / `invalid_code` / `wrong_service_chapter`.
- Allergy readiness: `complete_documented` when active allergies are fully specified;
  `incomplete_needs_clarification` when a `coordination_note` (or missing detail) asks to confirm;
  `no_known_allergies` when none; `conflicting_allergy_records` when sources disagree.
- Required documents: check `documents_received[]` and patient documents for the echo + office note; list
  anything missing.
- Authorization: from the referral's `authorization_status`. Overall readiness ladder — send only when auth is
  present, required docs are in, allergies are clear, code is valid, provider resolved; otherwise
  `hold_for_authorization` / `hold_for_missing_documents` / `hold_for_clinical_clarification`. The
  `coordination_note` frequently names the actual blocker.
- Fill the `*_choice` letter fields by selecting the enum option consistent with the evidence you derived.

## Care-transition packet (train_003-style)

- Recipient = the named provider id from the directory; confirm `service_line`.
- Active condition/medication/allergy key sets as above.
- `handoff_encounters`: the N most relevant recent encounters (template states the count, e.g. 4), newest→
  oldest, signed; record the selection rule in `source_selection.selection_basis` and the excluded ids.
- `latest_immunization` = most recent by date. `disclosure` = the one whose `recipient_provider_id` matches the
  recipient; it must be `status == "permitted"` for the packet to be sendable.
- Risk flags: derive from active clinical evidence (e.g. insulin-dependent diabetes, hypertension, cognitive/
  memory loss, latex allergy, and derived perioperative/fall-risk needs), each backed by `risk_flag_evidence`
  citing the condition/medication/encounter ids. Emit only the template's `allowed_values`.
- Readiness: `ready` / `ready_with_risk_flags` / `not_ready`; `ready_to_send` false and add a
  `blocking_issue_code` when a required element (patient, recipient, lists, handoff encounters, immunization,
  disclosure) is missing or the disclosure is not permitted.

## ServiceRequest quality signals + SBAR (train_004-style)

- Copy the ServiceRequest fields straight through (`status`, `intent`, `priority`, `service_code`,
  requester/performer ids, dates). Derive `performer_service_line` from the performer provider's directory
  record. Validate `service_code` via service-codes (exists + active + service_line matches).
- `reason_code_validation`: for each reason ICD-10 code, look it up → `valid` (found), `chapter`, and
  `matches_patient_evidence` (does an active condition / the case narrative support it). Sort by code.
- `sbar_coverage`: `sections_present` = which of situation/background/assessment/recommendation are present and
  non-empty; `missing_sections` = the rest; `complete` = all four present.

## Referral batch audit (train_005-style)

- Fetch all referrals, filter to the batch client-side. `record_count` = rows in batch;
  `unique_patient_count` = distinct patient_ids.
- `invalid_or_out_of_range_code_referrals`: icd10 chapter ≠ expected service chapter → `out_of_range_chapter`;
  404 → `unknown_code`.
- `laterality_or_narrative_mismatch_referrals`: when `requires_laterality` and the narrative's side/terms don't
  match `expected_terms` → `laterality_mismatch` / `narrative_mismatch` / `missing_laterality`; include the
  directory `expected_terms`.
- `duplicate_groups`: same patient with multiple referrals of the same clinical intent → one group,
  `duplicate_type: same_patient_resubmission`, `recommended_disposition: consolidate_under_original`; keep
  genuinely separate clinical referrals out of the duplicate group (they're separate reviews).
- `insurance_patient_anomalies`: shared insurance across *different* patients → verify, do-not-merge; same
  patient with separate clinical referrals → separate clinical review, not duplicate.
- `follow_up_queues`: `authorization_missing` / `authorization_pending` from `authorization_status`;
  `records_request` when the office note is missing; `imaging_follow_up` when imaging is missing/pending.
- `action_plan` tiering: Tier 1 = urgent coding error or duplicate blocker; Tier 2 = routine coding/auth/
  document blocker; Tier 3 = administrative document completion. `owner_provider_id` = the referral's
  receiving provider. `summary_counts` must be internally consistent with every array above.
