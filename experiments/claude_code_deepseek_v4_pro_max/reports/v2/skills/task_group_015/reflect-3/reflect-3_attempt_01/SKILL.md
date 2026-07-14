# EHR Quality Governance & Clinical Record Quality Control

## API Usage Workflow

1.  Start from `GET /api` to confirm the available endpoint index.
2.  Identify the target entity (duplicate candidate, referral batch, handoff packet,
    service request, or referral+patient) from the task scope.
3.  Pull the top-level entity first (e.g. `GET /api/duplicate-candidates/<id>`,
    `GET /api/referral-batches/<id>`, `GET /api/handoff-packets/<id>`,
    `GET /api/service-requests/<id>`, `GET /api/referrals` filtered for the target).
4.  Expand: pull linked patient records (`GET /api/patients/<id>`), then drill into
    sub-resources as needed (`/problems`, `/medications`, `/allergies`, `/encounters`,
    `/immunizations`, `/disclosures`, `/documents`).
5.  Load reference data: `GET /api/providers` and `GET /api/codebook/icd10` before
    making classification decisions (laterality, code-range, specialty matching).
6.  For duplicate candidates, also fetch `GET /api/audit-log` and match the audit
    event whose `patient_ids` list contains the candidate's patient IDs.

## Identifier & List Ordering Rules

- **All lists of stable identifiers must be sorted ascending** (lexicographic for
  string IDs, e.g. `"ENC-TR003-01"` before `"ENC-TR003-02"`; ICD codes sort by
  their string value).
- The only exception: fields that explicitly represent a priority queue or ranking
  (the field name or description will say so — e.g. `priority_queues` tier lists).
  Items within each tier-level list are still sorted ascending.
- Object-key maps (like `corrected_code_suggestions`) should emit keys in ascending
  order.

## Clinical List Filtering Rules

- **Status filtering**: When collecting `active_allergy_labels`, `active_medication_ids`,
  or `active_problem_codes`, include **only** items whose `status` is `"active"`.
  Exclude items with `"inactive"` or any other status.
- **Preserved lists for merges**: When merging duplicate patient records, the
  preserved lists combine all unique active items from both patients. Deduplicate
  by ID (for medications and problems) or by label (for allergies).
- **Encounter recency**: For `recent_encounter_ids`, include all encounters from the
  patient record. Do not second-guess relevance — include every encounter listed in
  the patient's encounters array, sorted ascending.
- **Allergy labels vs codes**: Fields named `*_allergy_labels` expect human-readable
  display labels (e.g. `"Penicillin"`), not internal codes (`"ALG-PEN"`).

## ICD-10 Codebook & Classification Rules

### Laterality Matching

Compare the diagnosis description text against the ICD-10 code's `laterality` field
in the codebook:

- If the diagnosis text says "left" but the codebook entry's `laterality` is
  `"right"` (or vice versa), flag as a **laterality mismatch**.
- Codes with empty `laterality` (e.g. spine codes, unspecified codes) cannot produce
  a laterality mismatch — only a narrative mismatch is possible.
- **Correct the code** by finding the same-condition code with the opposite laterality
  from the codebook (e.g. `M76.61` right → `M76.62` left).

### Narrative Mismatch

A narrative mismatch exists when the diagnosis description describes a fundamentally
different condition than what the ICD-10 code represents. The canonical example:
`"Olecranon bursitis right elbow"` with code `M79.3` (Panniculitis, unspecified).
The correct code is `M70.21` (Olecranon bursitis, right elbow).

### Out-of-Range Codes

Check `in_musculoskeletal_tracking_range` in the codebook. Codes where this is
`false` may be flagged as out-of-range for orthopedic service lines. However, only
include a referral in `out_of_range_code_referral_ids` — do **not** automatically
add a corrected code suggestion unless a better specific code exists in the codebook.

### Corrected Code Suggestions

- Map `referral_id` → corrected ICD-10 code string.
- Include only referrals that need an actual code change (laterality fixes, narrative
  mismatches with clear alternatives).
- Do **not** include referrals where the code is accurate but merely out-of-range
  for tracking purposes.
- Preserve the code formatting style used in the codebook (e.g. `"M70.21"`).

## Service-Line Specialty Matching

- When choosing a `referral_target` provider, match the referral's clinical
  context to the most specific provider specialty available. For a cardiology/heart
  failure referral, prefer `"Advanced Heart Failure"` over general `"Internal Medicine"`.
- The `specialty` field in the target object should use the exact specialty string
  from the providers endpoint.

## SBAR Note Parsing

Service request notes follow the SBAR format with labeled sections:

```
Situation: <text> Background: <text> Assessment: <text> Recommendation: <text>
```

- Parse by splitting on the section labels (`Situation:`, `Background:`,
  `Assessment:`, `Recommendation:`).
- A section is **present** (boolean `true`) if any non-whitespace content follows
  its label before the next section label or end-of-string.
- A section is **missing** if its label is followed only by whitespace, the next
  label, or end-of-string.
- List missing sections in `missing_sbar_sections` in **UPPERCASE** matching the
  SBAR section keys.

## Blocker Codes

- Use **specific, element-level blocker codes** that name exactly what is missing
  or wrong (e.g. `"MISSING_RECOMMENDATION"`), not generic categories
  (e.g. avoid `"SBAR_INCOMPLETE"`).

## Duplicate Candidate Reconciliation

### Merge Decision

- **canonical_target_patient_id**: The surviving record. Prefer the patient with the
  more complete clinical record (more medications, problems, encounters). When the
  duplicate candidate's `patient_ids` list is ordered `["A", "B"]`, typically the
  first ID (`"A"`) is the canonical target.
- **source_patient_id**: The record being absorbed/archived.
- **disposition**: Use `"MERGE_READY"` when both patients share the same address and
  the audit event confirms readiness. Use `"DO_NOT_MERGE"` for address conflicts.
- **reason_code**: A descriptive string explaining the merge basis (e.g. matching
  demographics plus audit confirmation).

### Audit

- `audit_status`: Map the audit-log event `status` field to the UPPER_SNAKE_CASE
  enum: `"ready_for_merge"` → `"READY_FOR_MERGE"`, `"blocked_address_conflict"` →
  `"BLOCKED_ADDRESS_CONFLICT"`. Use `"NO_EVENT_FOUND"` if no matching audit event
  exists.
- `merge_audit_event_id`: The `event_id` from the matching audit-log entry.

### Contact Action

- `target_provider_id`: The shared primary provider if both patients have the same
  one. If providers differ, use the canonical target's provider.
- `action_required`: `true` when there are clinical discrepancies between the
  records that require provider review. `false` when the merge is straightforward.

### Excluded Patient IDs

- List the source patient ID(s) that will be absorbed and no longer active after
  the merge. Sort ascending.

## Referral Batch Quality Audit

### Duplicate Groups

- Group referrals that share the **same patient** (match on full name + DOB) and
  the **same ICD-10 code**.
- Each group is a list of referral IDs sorted ascending.
- The outer list of groups should also have the first ID of each group sorted
  ascending for stable ordering.

### Insurance Anomalies

- An anomaly exists when the same `insurance_id` appears on referrals for
  **different** patients.
- `related_duplicate_referral_ids`: referrals for the same patient sharing this
  insurance (the legitimate duplicates).
- `unrelated_referral_ids`: referrals for a **different** patient using the same
  insurance ID.

### Missing Counts

- `auth_not_submitted`: Count referrals where `auth_status` equals `"Not Submitted"`
  (NOT `"N/A"` — those are "not required").
- `imaging_missing`: Count referrals where `imaging_received` equals `"No"`.
- `records_missing`: Count referrals where `records_received` equals `"No"`.

### Priority Queues

Assign each referral in the batch to exactly one tier:

- **tier1_immediate**: Patient-safety-critical issues (pathological fractures with
  oncology flags, urgent referrals with code mismatches that could cause wrong-site
  procedures).
- **tier2_short_term**: Clinical quality concerns that affect decision-making but
  are not immediately dangerous (duplicate referrals, laterality mismatches on
  non-urgent cases, narrative mismatches).
- **tier3_administrative**: Process issues (missing auth submissions, incomplete
  records/imaging, routine referrals with no clinical flags).

## Handoff Packet Completeness

### Readiness Determination

- `"READY"`: All required sections are present; any missing sections are
  non-blocking (informational only).
- `"READY_WITH_WARNINGS"`: The packet is substantially complete but a clinically
  important section (e.g. cognitive status for a skilled-nursing transfer) is
  missing.
- `"BLOCKED_INCOMPLETE_PACKET"`: Multiple required sections are missing.
- `"NEEDS_CLARIFICATION"`: Conflicting or ambiguous information exists.
- `"BLOCKED_ORDER_SAFETY"`: A medication or order safety issue blocks the transfer.

### Missing Sections

- Base this on the packet's `notes` field plus standard section expectations for
  the transfer type. For skilled-nursing handoffs, expect `cognitive_status`.
- List section names in snake_case as they appear in the `included_sections` list.

### Disclosure Status

- Use the `status` value from the patient's disclosure record that matches the
  handoff's receiving facility. If the disclosure recipient matches the
  `receiving_facility`, that disclosure governs.

### Most Recent Immunization

- Sort immunizations by date descending; pick the most recent `id`.

## Service Request Validation

### Order Validation

- Copy `priority`, `service_code`, `specialty`, and `status` directly from the
  service request object.
- Use the values exactly as they appear — do not transform or map them.

### Laterality Consistency

- Extract the body side (left/right) from the request's `note_text`.
- Look up the ICD code for the linked encounter's primary diagnosis in the codebook.
- Compare: `true` if sides match or the code has no laterality; `false` if they
  explicitly differ.

### Ready to Sign

- `false` if any SBAR section is missing or a clinical safety issue is flagged.
- `true` only when all SBAR sections are present, laterality is consistent, and
  no blocker codes apply.

## Referral Chart-Update Decision

### Referral Target

- Match the referral's clinical domain to the most specialized relevant provider.

### Allergy Update from Referral Notes

- When referral notes say to add an allergy, construct the allergy_update object
  with the allergen name from the notes.
- Use `"Anaphylaxis"` as the default reaction when "severe" is specified without
  further detail.
- Set `severity` based on the note's language (`"Severe"` when stated).
- Set `status` to `"active"`.

### Send Readiness

- `"BLOCKED"`: A safety-critical item (like a missing allergy that affects
  procedure safety) must be resolved before the referral can be sent.
- `"NEEDS_CLARIFICATION"`: Information is ambiguous or incomplete but not
  immediately dangerous.
- `"READY"`: All checks pass; the referral can be sent.

### Safety Flags

- Derive from referral notes and patient chart gaps that pose clinical risk
  (e.g. missing contrast allergy when cardiac imaging is planned, unreported
  allergies, anticoagulant use without documented monitoring).

### Unresolved Quality Issues

- List specific chart gaps that the referral surface identified but are not
  yet resolved (e.g. `"missing_iodinated_contrast_allergy"`).

### Letter Merge Fields

- These are the clinical-domain field names from the patient chart that the
  referral letter template expects to pull in. Include the categories most
  relevant to the referral's clinical context (e.g. `"allergies"`,
  `"diagnosis"`, `"medications"`).

### Diagnosis Update

- When the referral confirms an existing diagnosis, the code and description
  should match the patient's active problem. If the referral adds specificity
  (e.g. "with reduced ejection fraction"), incorporate that into the description
  while keeping the correct ICD-10 code.

## Common Pitfalls

1.  **Using allergy codes instead of labels**: Fields named `*_allergy_labels` or
    `*_label*` expect display names, not internal codes.
2.  **Including inactive items in preserved lists**: Always filter by
    `"status": "active"`.
3.  **Over-filtering encounters**: Include all encounters from the patient record
    for `recent_encounter_ids` unless there is a documented recency window.
4.  **Generic blocker codes**: Use specific codes naming the missing element
    (e.g. `"MISSING_RECOMMENDATION"`), not category-level codes.
5.  **Confusing narrative mismatch with laterality mismatch**: If the code
    describes an entirely wrong condition (not just wrong side), it is a narrative
    mismatch, not a laterality mismatch.
6.  **Adding corrected codes for out-of-range entries**: An accurate code that
    happens to be outside the musculoskeletal tracking range should be flagged
    as out-of-range but does NOT need a corrected code suggestion.
7.  **Sorting errors**: Every list of stable IDs must be sorted ascending.
    Object-key maps should emit keys in ascending order.
8.  **Wrong audit event selection**: Match audit events by checking that the
    event's `patient_ids` array contains both patient IDs from the duplicate
    candidate, not just any event mentioning one of them.
9.  **SBAR section presence**: Check for non-whitespace content after the label
    colon, not just the presence of the label itself. `"Recommendation:"` with
    nothing after it means `false`.
10. **Auth status counting**: Only count `"Not Submitted"` — do not include
    `"N/A"` referrals which are "not required" rather than "not submitted".
