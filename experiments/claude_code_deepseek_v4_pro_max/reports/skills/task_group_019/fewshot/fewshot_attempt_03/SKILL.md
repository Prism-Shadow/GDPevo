# Licensing Review Skill

Reusable instructions for processing structured licensing-review tasks in contractor, liquor, and alcohol-renewal domains. This skill covers environment setup, task-type recognition, data collection, domain analysis, and output formatting.

---

## 1. Environment Setup

Every task references `<TASK_ENV_BASE_URL>` in the prompt. Resolve this by reading the file `environment_access.md` at the workspace root, which contains:

- **`base_url`** — the actual HTTP origin to use in place of `<TASK_ENV_BASE_URL>`.
- **`credentials`** — a mapping of HTTP method + path pattern to required headers. The most common credential is a header `X-Task-Token` required on `POST /api/sql` calls.
- **`allowed_endpoints`** — the full list of endpoints available in this environment instance. Only endpoints listed here (and in the prompt) should be called.

### Making API calls

- Use the `base_url` from `environment_access.md` to construct full URLs.
- For `GET` endpoints, no special headers are typically required unless `environment_access.md` specifies one.
- For `POST /api/sql`, include the required token header from `environment_access.md` credentials. The body should be a JSON object with a `"query"` key containing the SQL string.

### SQL access

When `POST /api/sql` appears in the prompt or `environment_access.md`, you may run arbitrary `SELECT` queries against the environment's database. Use SQL to:
- Join records across related tables when the REST endpoints return only flat lists.
- Filter or aggregate data that would require multiple client-side passes over REST results.
- Look up records by criteria not directly exposed as REST query parameters.

Always inspect the REST endpoint responses first to understand the available table schemas and column names before writing SQL.

---

## 2. Task-Type Recognition

Read the prompt to determine which of three task families the request belongs to. The family determines the endpoints to call, the analysis framework to apply, and the shape of the output.

### Type A — Contractor Batch Eligibility Review

**Recognition signals:**
- Mention of "State Contractors Licensing Board" or "Contractors Licensing Board".
- A list of application IDs in the format `C-TRX-NNN`.
- Phrases like "eligibility batch", "escalated for a structured application decision", or "specialty endorsement questions".
- The prompt may specify a review date for financial-coverage checks.

**Relevant endpoints:**
- `GET /api/policies`
- `GET /api/contractor/applications`
- `GET /api/contractor/bonds`
- `GET /api/contractor/insurance`
- `GET /api/contractor/license-history`
- `GET /api/contractor/violations`
- `GET /api/contractor/correspondence`
- `GET /api/contractor/inspections`
- `POST /api/sql`

### Type B — Liquor License Staff Package

**Recognition signals:**
- Mention of "restricted liquor license", "liquor license transfer", "hotel-lounge", or "internal staff package".
- A single target application ID in the format `L-TR*-*` plus a location ID in the format `LOC-TR*`.
- Phrases like "issuance posture", "same-premises basis", "first-90-day monitoring plan", "escalation triggers".

**Relevant endpoints:**
- `GET /api/policies`
- `GET /api/liquor/applications`
- `GET /api/liquor/settlements`
- `GET /api/liquor/privileges`
- `GET /api/liquor/incidents`
- `GET /api/liquor/site-evidence`
- `POST /api/sql` (when listed in the prompt or `environment_access.md`)

### Type C — Alcohol Renewal Review Queue

**Recognition signals:**
- Mention of "Alcohol Renewal Unit", "pre-release renewal screen", or "renewal queue".
- A range of license numbers in the format `AL-TR*-*`.
- A "release boundary" or "boundary date" plus a "target queue size".
- Phrases like "ranked manual-review queue", "violation matching", or "match confidence".

**Relevant endpoints:**
- `GET /api/alcohol/licensees`
- `GET /api/alcohol/violations`
- `GET /api/renewal/rules`
- `POST /api/sql` (when listed in the prompt or `environment_access.md`)

---

## 3. Data Collection Strategy

### General pattern

1. Read `environment_access.md` to get `base_url` and any required token.
2. Read `input/payloads/answer_template.json` to understand the exact output schema — every field name, every allowed value, every ordering rule.
3. Call all relevant `GET` endpoints for the task type. Inspect the shape of each response to understand the available fields.
4. If the REST data is insufficient to resolve a decision (e.g., you need to join two datasets, or filter on a field not exposed as a query parameter), use `POST /api/sql` with a targeted `SELECT` query.
5. Cross-reference `GET /api/policies` against each application — policies describe current regulatory baselines that may create or remove deficiency flags compared to prior standards.

### Endpoint data shapes (general patterns)

**`/api/policies`** — Returns policy records with fields for policy identifiers, effective dates, and policy text describing current regulatory requirements. Use these to determine whether a deficiency is created by a policy change (for the `policy_impacted` flag in Type A tasks).

**Contractor endpoints** (Type A):
- **`/api/contractor/applications`** — Each record has an `application_id`, applicant details, endorsement fields, and status flags.
- **`/api/contractor/bonds`** — Each record links to an application or license and has bond amount, status (active/cancelled), and effective dates.
- **`/api/contractor/insurance`** — Each record has coverage amounts, status (current/expired/pending), and effective dates.
- **`/api/contractor/license-history`** — Each record has license status events including suspension start/end dates.
- **`/api/contractor/violations`** — Each record has a violation ID, severity (minor/serious), and resolution status.
- **`/api/contractor/correspondence`** — Each record has a correspondence ID, date, verification status, and linked application.
- **`/api/contractor/inspections`** — Each record has inspection results, document gaps, and safety flags.

**Liquor endpoints** (Type B):
- **`/api/liquor/applications`** — The target application record with premise details, license class, and status.
- **`/api/liquor/settlements`** — Past settlement agreements that may cover or exclude specific risks.
- **`/api/liquor/privileges`** — Operating privilege grants and conditions attached to the license or location.
- **`/api/liquor/incidents`** — Reported incidents at the location (assaults, noise complaints, minor sales, etc.).
- **`/api/liquor/site-evidence`** — Site documentation: floor plans, photos, camera evidence, signage records, police memos.

**Alcohol endpoints** (Type C):
- **`/api/alcohol/licensees`** — Each record has a `license_no`, facility name, address, and status.
- **`/api/alcohol/violations`** — Each record has a `violation_id`, `license_no` (or related identifier), violation date, and description.
- **`/api/renewal/rules`** — Rule records describing renewal criteria, boundary-date handling, and risk-tier thresholds.

---

## 4. Domain Analysis Frameworks

### 4A. Contractor Batch Eligibility (Type A)

For each application in the batch, evaluate across these dimensions and map findings to the deficiency codes and required actions defined in the answer template:

**Bond evaluation:**
- If no active bond exists → deficiency: `no_active_bond` / `bond_cancelled` → action: `file_active_bond` / `obtain_current_bond`.
- If the bond amount is below the required minimum (check policies and application class) → deficiency: `bond_shortfall` → action: `increase_bond_amount` / `increase_bond`.

**Insurance evaluation:**
- If the insurance policy has expired based on the review date → deficiency: `insurance_expired` / `insurance_not_current` → action: `provide_current_insurance` / `renew_insurance`.
- If coverage is below the required amount → deficiency: `insurance_shortfall` → action: `increase_insurance_amount` / `increase_insurance`.
- If insurance status is pending and not yet bound → deficiency: `insurance_pending` → action: `verify_insurance_binding`.

**Endorsement evaluation:**
- If a required endorsement is completely absent → deficiency: `endorsement_missing` / `endorsement_not_verified` → action: `obtain_required_endorsement` / `verify_endorsement`.
- If an endorsement application is in progress but not yet confirmed → deficiency: `endorsement_pending` → action: `verify_pending_endorsement`.

**Experience evaluation:**
- If documented experience falls below the required threshold for the license class → deficiency: `experience_shortfall` → action: `submit_experience_evidence` / `document_experience`.

**License history evaluation:**
- If the applicant has an active (unresolved) suspension → deficiency: `active_suspension` → action: `board_review_suspension` / `clear_suspension`.

**Violation evaluation:**
- If there are open/unresolved minor violations → deficiency: `open_minor_violation` → action: `resolve_minor_violation_review`.
- If there are open/unresolved serious violations → deficiency: `open_serious_violation` / `unresolved_serious_complaint` → action: `resolve_serious_violation` / `resolve_complaint`.

**Inspection evaluation:**
- If an inspection found document gaps not yet cleared → deficiency: `inspection_doc_gap` → action: `clear_document_gap`.
- If an inspection flagged safety issues requiring re-inspection → deficiency: `inspection_safety_recheck` → action: `complete_safety_recheck`.

**Decision logic:**
- **APPROVE**: No deficiencies found. All bonds, insurance, endorsements, experience, and background checks are satisfactory.
- **HOLD**: One or more deficiencies exist that can be resolved by the applicant (missing documents, shortfalls, pending verifications). No active suspension or unresolved serious violation.
- **DENY**: Active suspension, unresolved serious violations, or a combination of deficiencies that cannot be cured within the review period.

**Risk tier assignment:**
- **low**: No deficiencies (APPROVE cases).
- **medium**: Holdable deficiencies that are administrative or financial in nature.
- **high**: Active suspension, serious violations, safety recheck required, or a combination of 3+ deficiency categories.

**Policy impact determination:**
- Compare the application against the current policies from `GET /api/policies`. A `policy_impacted` flag is `true` when one or more deficiencies would not have existed under the prior policy baseline — i.e., the current policy *creates* the deficiency or material review flag.

**Correspondence review:**
- Identify correspondence records that are stale (beyond a reasonable response window) or unverified. Include their IDs in `stale_or_unverified_correspondence_ids` in the summary.

**Summary construction:**
- Count applications by determination (approve, hold, deny).
- Collect application IDs for high-risk and policy-impacted cases.
- Sort all ID lists in ascending lexical order.

### 4B. Liquor License Staff Package (Type B)

For the single target application and location, build a structured staff review package:

**Same-premises basis:**
- Check the application and privilege records to determine whether the license is being reviewed on the same premises as a prior license. If the premises address matches a prior license record and the license class is transferable, `same_premises_basis_applies` is `true`.

**Risk coverage assessment (`covered_risk_codes`):**
- Review incidents, settlements, and site evidence to identify which risks are present and covered by current controls:
  - `AFTER_HOURS` — incidents or complaints about after-hours operation.
  - `ASSAULT` — reported assaults or violent incidents on premises.
  - `FOOD_SERVICE_GAP` — insufficient food service documentation or capacity.
  - `MINOR_SALE` / `SALE_TO_MINOR` — recorded or alleged sales to minors.
  - `NOISE` — noise complaints tied to the location.
  - `PUBLIC_SAFETY` — general public-safety incidents.
  - `SAME_PREMISES` — risks specifically tied to same-premises transfer rules.
  - `TAX_HOLD` — outstanding tax obligations blocking the license.
  - `PATIO_BOUNDARY` — risks related to patio or outdoor service boundaries.
  - `CAMERA_COVERAGE` — gaps in camera surveillance coverage.
  - `ID_CHECK` — risks from inadequate ID verification.

**Verification gaps (`verification_gap_codes`):**
- Identify what evidence or documentation is missing, conflicting, or stale:
  - Signage issues: `CONTROL_SIGNAGE_CONFLICTING`, `CONTROL_SIGNAGE_CURRENT_MISSING`, `control_signage_missing`.
  - Floor plan issues: `FLOOR_PLAN_CONFLICTING`, `FLOOR_PLAN_STALE`, `floor_plan_conflicting`.
  - Evidence gaps: `SITE_PHOTO_MISSING`, `site_photo_missing`, `camera_evidence_missing`, `food_service_evidence_missing`.
  - Notice gaps: `NEIGHBOR_NOTICE_MISSING`, `neighbor_notice_missing`.
  - Memo/legal conflicts: `POLICE_MEMO_CONFLICTING`, `police_memo_identity_note`.
  - Open issues: `OPEN_INCIDENT_FOLLOW_UP`, `TAX_CLEARANCE_MISSING`, `tax_hold_unresolved`, `late_night_monitoring_needed`.

**Standard obligations vs. location-specific controls:**
- **Standard obligations** are the ordinary license-class requirements — the obligations that apply to *any* license of this class regardless of location. Common codes: `CCTV`, `DELIVERY`, `FOOD_SERVICE`, `HOURS`, `ID_CHECK`, `NOISE`, `PATIO`, `SECURITY`.
- **Location-specific controls** are additional controls imposed on *this specific location* due to its history, incidents, or conditions. Use the same code set but only include controls that are actively required at this location based on privilege conditions, settlement terms, or site-evidence documentation.

**First-90-day monitoring plan:**
- Build an ordered list of monitoring checkpoints, each with a `check_code` and `timing`:
  - `first_30_days` — checks that must happen immediately after issuance (signage review, ID check observation, initial walkthrough).
  - `days_31_60` — follow-ups that need a month of operational data (after-hours visits, police memo follow-up).
  - `days_61_90` — later-stage checks that verify sustained compliance (noise log review, patio boundary checks, tax clearance).
- Each `check_code` addresses a specific verification gap or risk. The plan should be operationally sequenced — earlier checks verify setup, later checks verify sustained operation.

**Escalation triggers:**
- Define conditions that would cause field staff to escalate the license back for review:
  - Violation-based: `AFTER_HOURS_VIOLATION`, `REFERRED_MINOR_SALE_UNRESOLVED`, `minor_sale`, `after_hours_service`, `noise_or_patio_breach`, `patio_boundary_failure`, `id_check_failure`.
  - Control failures: `CONTROL_SIGNAGE_NOT_VERIFIED`, `SECURITY_CCTV_CONTROL_FAILURE`, `missing_camera_coverage`, `footage_not_produced`, `food_service_not_available`.
  - External events: `MAJOR_INCIDENT_REPORTED`, `BOARD_ORDER_CONFLICT`, `unreported_violent_incident`.
  - Administrative: `TAX_HOLD_REOPENED`, `open_tax_hold_uncleared`.

**Recommended posture:**
- `issue_restricted` — All major risks are covered, verification gaps are minor, and a monitoring plan is feasible.
- `request_follow_up` — Significant verification gaps exist that need resolution before a final decision, but denial is premature.
- `deny` — Unresolvable risks, missing same-premises basis when required, or active serious violations.

### 4C. Alcohol Renewal Review Queue (Type C)

Build a ranked manual-review queue from a set of target licenses:

**Violation matching:**
- For each target license, find all violations that match. Matching should consider:
  - **Exact match**: The violation's `license_no` field equals the target license number exactly.
  - **Close address match**: The violation references the same facility/location through a related identifier (e.g., an old license number for the same premises, or an address-based match when the license number differs slightly).
  - **Uncertain match**: The violation may relate to the license but the connection is ambiguous (e.g., same address but different entity name).
- Set `match_confidence` accordingly: `"exact"`, `"close_address"`, or `"uncertain"`.

**Boundary date filtering:**
- The prompt specifies a release boundary date. Violations with dates **on or after** the boundary date are *post-boundary* and must be **excluded** from the violation counts, `most_recent_violation_date`, and `matched_violation_ids` used for ranking.
- Post-boundary violations should still be listed in `summary.post_boundary_violation_ids_excluded`.

**Ranking logic:**
- Rank licenses from highest review priority (rank 1) to lowest (rank 10) using these factors in descending priority:
  1. **Number of pre-boundary matched violations** (more violations = higher priority).
  2. **Recency** of the most recent pre-boundary violation (more recent = higher priority).
  3. **Match confidence** (exact matches rank higher than close_address, which ranks higher than uncertain, all else equal).
  4. **Violation severity** implied by the renewal rules or violation descriptions.
- The queue must contain exactly the target size (e.g., 10 entries), with ranks 1 through N and no gaps.

**Risk tier assignment:**
- **high**: Multiple recent violations, serious violation types, or board-review triggers.
- **medium**: Some violations but older or less severe.
- **low**: Few or no violations, all minor and old.

**Next-step label assignment:**
- `board_review` — Licensees with the most severe or numerous violations requiring elevated review.
- `manual_fine_check` — Licensees where fines may need manual verification.
- `manual_ALERT_check` — Licensees flagged in an ALERT system or similar watchlist.
- `additional_record_check` — Licensees needing further record pulls before a decision.

**Summary construction:**
- `queue_size`: The number of entries in the queue (should match the target).
- `boundary_date`: The release boundary date from the prompt, in YYYY-MM-DD format.
- `post_boundary_violation_ids_excluded`: All violation IDs with dates on or after the boundary date, sorted ascending.
- `close_or_uncertain_match_license_numbers`: License numbers with non-exact match confidence, sorted ascending.
- `board_review_license_numbers`: License numbers assigned `board_review` as their next step, sorted ascending.

---

## 5. Output Formatting Rules

### General rules for all task types

1. **Return only JSON** — no markdown fences, no prose, no narrative memo, no citations outside the JSON structure.
2. **Follow the answer template exactly** — use only the keys, value types, and allowed enum values defined in `input/payloads/answer_template.json`.
3. **Ordering** — respect all ordering rules stated in the template:
   - Application/queue entries ordered by their identifier (ascending lexical for IDs, ascending integer for ranks).
   - Deficiency codes, required actions, and other code arrays sorted in the order specified by the template (usually alphabetical/lexical ascending).
   - Violation IDs sorted by date ascending, then by ID ascending.
4. **Empty values** — use `[]` (empty array) when no codes, actions, or IDs apply. Never use `null` or omit a required key.
5. **Date format** — all dates must use `YYYY-MM-DD` format.
6. **No extra keys** — do not add keys not shown in the template, even if they would be informative.

### Type-specific formatting notes

**Type A (Contractor Batch):**
- `application_decisions` must contain exactly the number of target applications listed in the prompt, ordered by `application_id` ascending.
- `summary.approve_count + summary.hold_count + summary.deny_count` must equal the total number of applications.
- `policy_impacted` is a boolean per application.
- `stale_or_unverified_correspondence_ids` collects correspondence IDs that are stale or unverified across the entire batch.

**Type B (Liquor Staff Package):**
- All code arrays (`covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`, `location_specific_control_codes`, `escalation_trigger_codes`) must use only the allowed values from the template — the vocabulary varies between task instances.
- `first_90_day_plan` is an array of objects, each with `check_code` and `timing`. The allowed check codes and timing values are specific to each template.
- `same_premises_basis_applies` is a boolean.
- `recommended_posture` is one of the three allowed enum values.

**Type C (Alcohol Renewal Queue):**
- `queue` must have exactly the target queue size with ranks 1 through N and no gaps.
- `matched_violation_ids` within each queue entry must be sorted by violation date ascending, then violation_id ascending.
- `summary.post_boundary_violation_ids_excluded` lists violation IDs that were filtered out by the boundary date.
- `summary.close_or_uncertain_match_license_numbers` and `summary.board_review_license_numbers` must be sorted ascending.

---

## 6. Step-by-Step Execution Protocol

When a licensing-review task is encountered, follow this protocol:

1. **Read environment**: Open `environment_access.md`, note `base_url` and any credentials.
2. **Read template**: Open `input/payloads/answer_template.json`, memorize the required output shape and all allowed enum values.
3. **Identify task type**: Match the prompt against the three families in Section 2.
4. **Fetch data**: Call all relevant `GET` endpoints. Inspect response shapes to learn field names.
5. **Apply analysis framework**: Use the appropriate framework from Section 4 to evaluate each application/license.
6. **Cross-reference policies**: Always check `GET /api/policies` against each application to determine policy impact.
7. **Fill gaps with SQL**: If REST data is insufficient to resolve a specific decision (e.g., joining across datasets, filtering by criteria not exposed as query parameters), use `POST /api/sql`.
8. **Construct output**: Build the JSON strictly according to the template, following all ordering and formatting rules from Section 5.
9. **Validate**: Verify counts are consistent, all required keys are present, all enum values are from the allowed set, and ordering rules are satisfied.
10. **Return only the JSON object** — no surrounding text.
