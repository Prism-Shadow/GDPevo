# Reconciliation rules

Transferable decision rules for EHR governance/coordination packets. Apply the
subset relevant to the current template. Nothing here is a task-specific answer;
these are the *methods* that produce the answer from whatever data you fetch.

## 1. Active clinical lists & key unions

- A record counts toward an "active" list **iff** `status == "active"`. Key it
  by its `normalized_key`. Union across every patient in scope (e.g. both sides
  of a merge). Deduplicate, then sort as the template says (usually
  alphabetical).
- Include **every** active key, even ones that look like generic placeholders.
  Do **not** drop a key because its name seems non-clinical or because a
  `merge_preview` omitted it.
- Non-active records (`inactive`, `entered-in-error`, legacy imports marked
  inactive) go into the `excluded_distractors` / excluded-keys lists, never the
  active union.
- When a template distinguishes "keys added from the active endpoints vs a
  preview", the added set = (active endpoint keys) − (preview keys). The
  patient's active-list endpoints are authoritative **over** any preview.

## 2. Canonical / duplicate-merge resolution

- Canonical **target** = the patient with `canonical_status == "active"` and
  `canonical_patient_id == null`. **Source** = the patient with
  `canonical_status == "duplicate"` whose `canonical_patient_id` points at the
  target. This usually matches the candidate's `preferred_target/source`.
- Match/conflict signals come from the duplicate candidate record; confirm each
  against the actual demographics (same/different dob, phone, insurance,
  address, given name). "similar_address" (e.g. "St" vs "Street", "Way" vs
  "Wy") is a **match**, not a conflict.
- Disposition:
  - Strong identity match with only a **trivial** conflict (address
    abbreviation, nickname variant like Sam/Samuel) → treat as a confirmed,
    clean merge (`ready_to_merge` / `merge_ready`, `manual_review_required =
    false`, readiness `ready`). Do **not** escalate to a conflict-review path
    for a cosmetic difference.
  - Genuinely conflicting identity — different *given names* (not a nickname,
    e.g. Nadia vs Nadine), different phone, and/or `opposite_laterality_problem`
    — over shared dob/insurance/address is the twin/sibling false-duplicate
    pattern. Here the candidate's stored `status` (e.g. `needs_review`) is the
    answer: report that status, set the decision to the hold/review value, and
    leave merge target/source `null`. Report the **stored** status faithfully;
    don't substitute your own not-duplicate/confirmed verdict.

## 3. Evidence, documents, and audit IDs

- Follow the template's stated document basis (e.g. "identity or external
  continuity documents only"). Typically **include** `identity_verification`
  and external specialty/continuity notes with `status == "final"`; **exclude**
  generic `chart_summary` / `ehr_export` documents and anything for an unrelated
  patient.
- Case-relevant audit rows are the ones about *these* patients/this candidate;
  other patients' rows and unrelated merges are distractors.
- Sort id arrays ascending (string sort) unless told otherwise.

## 4. Provider / recipient selection

- Choose the specialist/recipient by the **service line implied by the case**
  (a cardiology referral → the cardiologist; an orthopedic transition → the
  named ortho surgeon; a cardiology-continuity merge → the cardiologist behind
  the external note). Pull the full contact block (name, role, service_line,
  facility, phone, fax) from the provider directory by `provider_id`.
- The primary-care provider comes from the patient record's
  `primary_care_provider`.

## 5. ICD-10 validation & narrative/laterality checks

Look every diagnosis code up in the ICD-10 directory (`chapter`,
`expected_terms`, `requires_laterality`).

- **Chapter / out-of-range:** for a service-line batch, the code's `chapter`
  must equal the expected chapter (orthopedics → `Musculoskeletal`). A code in
  any other chapter — including Injury (`S…`) and Respiratory (`J…`) — is
  `out_of_range_chapter`. A code absent from the directory is `unknown_code`.
  This is a **mechanical chapter test**: do not exempt codes just because the
  condition is clinically plausible for the specialty.
- **Narrative match:** compare the narrative's core anatomy/condition to the
  code. Different region/condition (knee code vs "lumbar radiculopathy", knee
  code vs "hip arthritis") → `narrative_mismatch`.
- **Laterality:** if the code carries a side and the narrative names the
  opposite side → `laterality_mismatch`. If the code `requires_laterality` but
  the narrative gives no side → `missing_laterality`. A same-joint difference of
  wording only (e.g. "knee pain" vs a "knee OA" code, same side) is *not* a
  narrative mismatch on its own.
- **matches_patient_evidence:** a reason code "matches" when the patient's own
  active conditions include that code/finding (right side, right condition).

## 6. Service-code validation

- Validate a `service_code` against the service-code directory: it is valid when
  it exists, is `active`, and its `service_line` fits the order/performer.
  Derive `performer_service_line` from the performer provider's directory entry.

## 7. Encounter / handoff selection

- Select encounters by **topic relevance + recency window**, not by "latest
  overall". For a referral/transition about a specific problem (a joint, a
  condition), keep the encounters on that thread (matching diagnoses / a
  `care_transition` note) and drop unrelated recent visits and stale/oldest
  ones. If the template asks for N encounters, take the N most recent *relevant*
  ones and list the rest as excluded (stale / outside-window / not-relevant).
- Copy encounter fields verbatim (`encounter_id`, date, type, `signed_status`,
  diagnoses, meds mentioned). Order newest→oldest when required.

## 8. Referral-batch audit

- **record_count** = number of referral rows; **unique_patient_count** =
  distinct `patient_id` values (a resubmission repeats a patient).
- **Duplicate groups:** the same `patient_id` appearing on more than one row
  (especially with a "duplicate resubmission" note or a `-DUP` id) is a
  `same_patient_resubmission` group → `consolidate_under_original`; those rows
  are the tier-1 duplicate blockers.
- **Insurance/patient anomalies:** the same `insurance_id` on **different**
  patients → `shared_insurance_different_patients` → verify membership,
  do-not-merge. Same name with different dob/insurance = mere namesakes, **not**
  an anomaly.
- **Follow-up queues** partition by field: `authorization_status` (`missing`
  vs `pending`); missing office-note document → records request; imaging pending
  / missing imaging → imaging follow-up.
- **Action tiers:** Tier 1 = urgent rows with a coding problem *or* duplicate
  blockers; Tier 2 = routine rows with a coding / authorization / document
  blocker; Tier 3 = rows needing only administrative document completion. Owner
  = the receiving provider. Rows with no issue at all are the "validated ready /
  no follow-up" count.
- **summary_counts** must be internally consistent with the arrays above — count
  from the same computed sets, don't re-derive by hand.

## 9. Risk flags & readiness

- Emit a risk flag only when the chart has evidence for it (an active condition,
  an active med such as insulin, an allergy, or an explicit care-plan note like
  "needs glucose plan / fall-risk note"). Provide the supporting
  condition/med/encounter evidence the template asks for.
- Readiness: the packet is ready (or "ready with flags") when all **required
  components exist** and no hard blocker applies; informational risk flags do
  not block sending. Map `blocking_issue_codes` only to the template's allowed
  *missing-component* values (missing patient/recipient/lists/encounters/
  immunization/disclosure, disclosure-not-permitted) — a present-but-flagged
  packet has an empty blocking list.
