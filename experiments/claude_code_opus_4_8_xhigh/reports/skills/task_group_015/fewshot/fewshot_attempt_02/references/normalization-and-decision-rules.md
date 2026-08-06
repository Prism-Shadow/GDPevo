# Cross-cutting normalization & decision rules

These apply across archetypes. Always map a derived value onto the exact enum /
field the current template defines — the label names below describe the *logic*, not
the literal strings to emit; use the template's vocabulary.

## 1. Active-only filtering & distractors

Include a clinical record in `*_key` / active-list outputs **iff** `status ==
"active"`. Everything else (`inactive`, `entered-in-error`, `resolved`) is a planted
distractor. The datasets deliberately seed:

- inactive conditions/meds/allergies alongside active ones,
- documents that are generic exports (`chart_summary`, `ehr_export`) next to the
  identity / external-continuity docs that actually belong in a packet,
- unrelated or out-of-window encounters (sometimes with a *newer* date than the
  relevant ones),
- out-of-service-line or unknown ICD-10 codes.

Exclude distractors from primary outputs; when the template has an `excluded_*`
array, put them there (sorted).

## 2. Normalized keys, dedup, sorting

- `*_key(s)` fields → the record's `normalized_key`. Human-readable blocks → the
  descriptive fields. Dedupe keys.
- Sets sort ascending. Ordered lists follow the template's stated order
  ("referral-relevant first", "newest→oldest"); when it says "treated as a set by
  X", any order is accepted but sort anyway for stability.

## 3. Duplicate-candidate reconciliation (authoritative union)

For a two-patient duplicate case, the **patient active-list endpoints are
authoritative over `merge_preview`**:

1. Fetch `/conditions`, `/medications`, `/allergies` for **both** patients.
2. `active_key_union = sort(dedupe(active normalized_keys from both patients))`.
3. If the template has a reconciliation block: `*_added_from_active_endpoints =
   active_key_union − merge_preview.active_*_keys` (keys present in the real
   endpoints but missing from the preview), and the authoritative-source field takes
   the "patient active-list endpoints over duplicate preview" value.

## 4. Identity match / conflict signals

- `match_signals` / `conflict_signals` come **directly** from the duplicate
  candidate — copy them (sorted).
- For separate `demographic_matches` / `demographic_conflicts` fields, compare the
  two patient detail records field-by-field: `dob`, `sex`, `phone`, `insurance_id`,
  `primary_care_provider_id`, `given_name`, `family_name`, `address`. Equal →
  match; differing → conflict. Distinguish a soft/normalization conflict (a name
  *variant*, an address *abbreviation*) from a hard conflict (different DOB, insurer,
  or an opposite-laterality problem).

## 5. Merge disposition

Drive the disposition enum from candidate status + signal strength:

- Candidate `status == "open"`, `preferred_target_patient_id` set, strong identity
  match, and only soft/normalization conflicts → **merge-ready** (no manual review);
  `target = preferred_target_patient_id`, `source = source_patient_id`.
- Candidate `status == "needs_review"`, or any **hard** conflict (opposite
  laterality, different DOB/insurer, non-variant name mismatch), or missing
  preferred target → **needs-review / review-hold**; leave merge target & source
  **null**.
- Signals actively refute identity → **do-not-merge**.

`manual_review_required` is true whenever the disposition is anything other than the
clean merge-ready case. Reason-code arrays: concise sorted `snake_case` slugs
describing the drivers actually observed (identity-match strength, whether the source
record already points to the target, canonical/active status, blocking conflicts).

## 6. Evidence selection

- **Merge-packet documents:** keep only identity-verification and external-continuity
  documents (external specialist notes / imports); exclude generic chart-summary /
  EHR-export documents (list them as excluded document types / distractors). Use only
  `status == "final"` documents. Sort IDs.
- **Audit IDs:** include audit-log entries about the merge / identity review for the
  involved patients; exclude unrelated events.
- **Encounters (handoff / referral evidence):** select those relevant to the target
  service line and within the prompt's handoff/recency window; order newest→oldest;
  keep exactly the count the template asks for. Exclude stale, out-of-window, or
  off-topic encounters **even if one has a more recent date**. Note: an encounter
  excluded from the main handoff list can still be cited as evidence in a
  `risk_flag_evidence`-style field if it documents that specific risk.

## 7. ICD-10 validation (codes, chapters, laterality, narrative)

For each code, `GET /api/icd10/{code}`:

- **404 → unknown/invalid code.**
- **Chapter check:** compare `chapter` to the chapter expected for the service line
  (orthopedics → `Musculoskeletal`). Mismatch → out-of-range-chapter.
- **Narrative match:** does `diagnosis_narrative` (or condition description) align
  with `expected_terms`? If not → narrative-mismatch.
- **Laterality:** if `requires_laterality` and the narrative names the opposite side
  from the code → laterality-mismatch; if it names no side → missing-laterality.
- A row can carry multiple mismatch types at once (collect them as a set).

## 8. Service-code & reason-code validation

- `service_code_valid` = service code exists, `active == true`, and its
  `service_line` matches the requested line; `performer_service_line` from the code /
  performer provider.
- For each ServiceRequest `reason_code`: `valid`+`chapter` from the ICD-10 lookup;
  `matches_patient_evidence` = the code corresponds to an active condition (or
  documented encounter diagnosis) for that patient. Sort validation objects by code.
- Map `status`/`intent`/`priority` from the ServiceRequest record onto the template
  enums (read them from the record; do not assume).

## 9. SBAR coverage

From `sbar`, `sections_present` = the subset of {situation, background, assessment,
recommendation} that are non-empty; `missing_sections` = the rest; `complete` = all
four present.

## 10. Readiness, blockers & tiering

- **Readiness / blocking issues:** derive from presence of blockers — missing
  required document, missing/pending authorization, incomplete allergy record,
  unresolved provider, invalid diagnosis code, clinical mismatch, disclosure not
  permitted. No blockers → ready-to-send; risk flags present but non-blocking →
  ready-with-flags; a hard blocker → the matching hold/blocked enum. Populate the
  `blocking_issue`/`missing_*` arrays from the actual gaps only.
- **Follow-up queues (batch audit):** `authorization_status == missing/pending` →
  the respective auth queue; `office_note` absent from `documents_received` →
  records-request; imaging (mri/echo/x-ray) missing or pending → imaging-follow-up.
- **Tiering (batch audit):** Tier 1 = urgent-priority rows and duplicate-blocker
  rows; Tier 2 = routine rows with a coding / authorization / document blocker; Tier
  3 = rows needing only administrative document completion; a clean row with no
  follow-up counts toward `validated_ready`. `owner_provider_id` = the referral's
  `receiving_provider_id`.
- **Duplicate groups & insurance anomalies (batch audit):** group repeated referrals
  for the *same* patient (same-patient resubmission → consolidate under original);
  flag the same `insurance_id` shared across *different* patients as a
  shared-insurance anomaly (verify membership, do **not** merge on insurance alone).

## 11. Counts

Recompute every summary count from the lists you actually emit (record rows, unique
`patient_id`s, per-priority counts, per-category counts, per-tier counts). They must
agree with the arrays in the same answer.
