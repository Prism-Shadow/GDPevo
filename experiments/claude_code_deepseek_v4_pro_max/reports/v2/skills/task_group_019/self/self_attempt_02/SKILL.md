# Cascadia Licensing Review Portal (CLRP) — Review Skill

## Overview

CLRP is a government regulatory licensing portal with three review workflows:
1. **Contractor Eligibility Review** — batch-based contractor registration screening
2. **Alcohol License Review** — per-application restricted-license assessments
3. **Renewal Manual-Review Queue** — ranked licensee queues from release batches

All data comes from a single remote CLRP API. The base URL is provided per task
and overrides any localhost references. Use only the public API and export
endpoints; never inspect local files, databases, or setup scripts.

---

## Workflow 1: Contractor Eligibility Review

### Data Sources (in order of precedence)

| Priority | Source | Purpose |
|----------|--------|---------|
| 1 | `GET /api/contractors/applications?batch_id=<B>` | Master application list; source of truth for IDs |
| 2 | `GET /exports/contractor_batch_<B>.csv` | Secondary confirmation; DBA field may have truncation artifacts |
| 3 | `GET /api/contractors/bulletins?effective_on=<YYYY-MM-DD>` | Active regulatory thresholds as of review cutoff |
| 4 | `GET /api/contractors/bonds?name=<search_term>` | Bond status per contractor |
| 5 | `GET /api/contractors/insurance?name=<search_term>` | Insurance verification per contractor |
| 6 | `GET /api/contractors/violations?name=<search_term>` | Violation history |
| 7 | `GET /api/contractors/complaints?name=<search_term>` | Open complaints |
| 8 | `GET /api/contractors/field-notes?name=<search_term>` | Inspector field findings |
| 9 | `GET /api/contractors/correspondence?batch_id=<B>` | Batch-level correspondence keyed by `affects_application_id` |

### Name-Matching Rule (CRITICAL)

All `?name=` endpoints perform **substring search** across legal_name and
principal_name. A query for "Beacon" returns records for "Beacon Summit",
"Beacon Ridge", "Beacon Cedar", "Beacon Marina", etc. — entities that share the
search term but are different contractors.

**After every name-based API call, filter the response to records matching BOTH:**
- `legal_name` exactly equals the application's `legal_name`
- `principal_name` exactly equals the application's `principal_name`

Records matching only one field or a partial name are **distractors** and must
be excluded from the decision. The DBA field (when present) is NOT used for
matching because it may be truncated in the data.

### Bulletin Application

Bulletins retrieved with `effective_on=<cutoff_date>` include all bulletins
effective on or before that date. Each bulletin has:

| Field | Meaning |
|-------|---------|
| `rule_type` | EXAM_MINIMUM, BOND_MINIMUM, INSURANCE_MINIMUM, EXPERIENCE_MINIMUM |
| `trade_scope` | "ALL" or a specific trade name |
| `threshold_value` | The numeric minimum |
| `effective_date` | When the rule took effect |

**Application rule:** A bulletin applies to an application when:
- `trade_scope` is "ALL", OR
- `trade_scope` matches the applicant's `trade` field (case-sensitive exact match)

### Decision Dimensions

For each application in the batch, check:

1. **Exam score** (`exam_score`) vs bulletin `EXAM_MINIMUM` threshold → `EXAM_SCORE_SHORTFALL`
2. **Bond amount** (`declared_bond_amount`) vs bulletin `BOND_MINIMUM` → `BOND_SHORTFALL`
3. **Bond status** from bond API (must match name+principal): `cancelled` → `BOND_CANCELLED`; `reduced` with a reduction notice → `BOND_SHORTFALL`
4. **Insurance coverage** from insurance API (match by `legal_name`): coverage amount vs bulletin `INSURANCE_MINIMUM`, and carrier/policy match vs declared → `INSURANCE_VERIFY`
5. **Experience years** (`experience_years`) vs bulletin `EXPERIENCE_MINIMUM` → `EXPERIENCE_VERIFY`
6. **Financial statement** (`financial_statement_filed`): 0 → `FINANCIAL_STATEMENT_MISSING`
7. **Background status** (`background_status`): `adverse` + prior registration → check violations/complaints → `ADVERSE_PRIOR_REGISTRATION`
8. **Violations**: unresolved violations (especially high-severity, AG referral, or with penalty_due_cents > 0) → `UNRESOLVED_PENALTY` or `DISQUALIFYING_CONDUCT` for fraudulent registration
9. **Field notes**: inspector holds or "verify documents" recommendations → `FIELD_NOTE_HOLD`
10. **Correspondence**: `material notice` with `needs_review` or `new` status for the application → `CORRESPONDENCE_HOLD`

### Determination Logic

- **APPROVE**: No deficiency codes at all → `reason_codes: ["NO_DEFICIENCY"]`
- **HOLD**: One or more non-fatal deficiencies (bond shortfall, insurance verify, experience verify, field note hold, correspondence hold, financial statement missing, unresolved penalty that is not disqualifying)
- **DENY**: Disqualifying conduct (fraudulent registration), bond cancelled without replacement, adverse prior registration with ongoing serious violations

### `next_action` Mapping

| Condition | next_action |
|-----------|-------------|
| No deficiencies | `NO_ACTION` |
| Bond shortfall (amount too low) | `REQUEST_BOND_RIDER` |
| Bond cancelled | `REQUEST_REPLACEMENT_BOND` |
| Insurance mismatch/verify | `REQUEST_INSURANCE_VERIFICATION` |
| Unresolved penalty (non-disqualifying) | `REFER_UNRESOLVED_PENALTY` |
| Field note hold | `REQUEST_FIELD_CLEARANCE` |
| Experience shortfall | `REQUEST_EXPERIENCE_DOCUMENTATION` |
| Disqualifying conduct | `DENY_APPLICATION` |
| Multiple hold reasons | `COMBINED_HOLD_REVIEW` |

### `primary_bulletin_ids`

List the bulletin IDs whose thresholds drive a deficiency. When multiple
bulletins apply, include all. Use `[]` when no bulletin drives the decision.

### Deficiency Counts

Count every application that has each reason_code. An application with
`NO_DEFICIENCY` contributes 1 to that count (and is the only code for that app).
Applications with multiple deficiencies contribute 1 to each applicable code.

### Bulletin Impact Summary

- `applicable_bulletin_ids`: All bulletins effective on or before the cutoff, sorted ascending
- `applications_changed_by_2026_bulletins`: Applications whose determination would differ without 2026 bulletins (i.e., where a bulletin threshold causes a deficiency)
- `deficiency_count_by_rule_type`: Count of deficiencies caused by each rule type across all applications
- `unchanged_by_bulletins_count`: Applications whose determination is not affected by any bulletin

---

## Workflow 2: Alcohol License Review (Restricted Issuance)

### Data Sources

| Priority | Source | Purpose |
|----------|--------|---------|
| 1 | `GET /api/alcohol/applications?review_month=YYYY-MM` | All applications in review month |
| 2 | `GET /api/alcohol/premises?premises_id=<P>` | Premises details, prior licensee, risk |
| 3 | `GET /api/alcohol/incidents?premises_id=<P>` | Incident history at the premises |
| 4 | `GET /api/alcohol/settlements?premises_id=<P>` | Prior/current settlement posture |
| 5 | `GET /api/alcohol/restrictions?premises_id=<P>` | Current restrictions (standard + premises-specific) |
| 6 | `GET /api/alcohol/standard-obligations?license_type=<L>` | Standard obligations for the license type |

### License Types and Their Standard Obligations

Standard obligations are returned from the API by querying the application's
`license_type`. Every license type also gets the ALL-type obligations
(`INCIDENT_REPORT`, `PUBLIC_RECORDS`).

| License Type | Type-Specific Obligation Codes |
|-------------|-------------------------------|
| F-RTL | `RTL_DISPLAY`, `RTL_SALES`, `RTL_STAFF` |
| F-COM | `F_COM_FOOD`, `F_COM_SERVER`, `F_COM_MINORS` |
| TAVERN | `TAVERN_AGE`, `TAVERN_HOURS`, `TAVERN_SECURITY` |
| BREWPUB | `BREW_PRODUCTION`, `BREW_SAMPLES`, `BREW_TRAINING` |

### Risk Assessment

Count incidents from the premises incidents endpoint:
- `incident_count`: Total incidents
- `unresolved_incident_count`: Incidents with `disposition` of "pending" or empty string
- `high_severity_incident_count`: Incidents with `severity` of "high"

Determine `prior_incident_level`:
- 0 incidents → `NONE`
- Only low severity → `LOW`
- Any medium, no high → `MODERATE`
- Any high → `HIGH`

Determine `same_premises_basis` from premises data:
- No prior licensee → `NONE`
- Prior settlement at same address → `PRIOR_SETTLEMENT_AT_ADDRESS`
- Same address overlap → `SAME_ADDRESS_OVERLAP`

Determine `settlement_posture` from settlements endpoint:
- No settlements → `NONE`
- Prior warning with controls → `PRIOR_WARNING_WITH_CONTROLS`
- Prior restricted or denial → `PRIOR_RESTRICTED_OR_DENIAL`
- Current settlement exists → `CURRENT_SETTLEMENT`

Determine `control_coverage` from restrictions:
- Premises-specific restrictions exist → `ADEQUATE_LOCATION_SPECIFIC`
- Only standard obligations → `STANDARD_ONLY`
- Empty restrictions → `NO_CONTROLS`

Determine `overall_risk`:
- No incidents, no prior licensee, adequate controls → `LOW`
- Low incidents, standard controls → `MODERATE`
- Moderate/high incidents, some gaps → `ELEVATED`
- High incidents, unsettled, no controls or prior restricted → `SEVERE`

### Verification Gaps

Check for gaps between what controls exist and what incidents/settlements
suggest should exist:
- Missing age-verification amid minor-on-premises incidents → `AGE_VERIFICATION_CONTROL_NOT_IN_CURRENT_RESTRICTIONS`
- Late-night disorder with no late-night security control → `LATE_NIGHT_SECURITY_CONTROL_NOT_IN_CURRENT_RESTRICTIONS`
- Pending police dispositions → `PENDING_POLICE_CALL_DISPOSITIONS`
- Security plan lapse with missing disposition → `SECURITY_PLAN_LAPSE_DISPOSITION_MISSING`
- Settlement exists but terms unclear → `SETTLEMENT_TERMS_NOT_FOUND`
- All gaps covered → `NO_VERIFICATION_GAPS`

### Review-Month Comparison

Query all applications in the review month. Count:
- Total applications in the review month
- Applications whose premises have location-specific (premises-specific category) restrictions
- The target's own location-specific control count and whether it has any

---

## Workflow 3: Renewal Manual-Review Queue

### Data Sources

| Priority | Source | Purpose |
|----------|--------|---------|
| 1 | `GET /api/renewals/licensees?release_batch=<B>` | Licensee roster |
| 2 | `GET /exports/renewal_roster_<B>.csv` | Complete roster CSV |
| 3 | `GET /api/renewals/violations?city=<C>` | Violations per city (query EACH city) |
| 4 | `GET /api/search/address?address=<A>` | Cross-domain address lookups |

### Queue Construction

1. Fetch all licensees from the renewal API for the release batch.
2. Query violations for **every city** that appears in the licensee roster.
3. Match violations to licensees by facility name. **Matching is fuzzy:**
   - "Grill" may appear as "Grille" (successor_hint)
   - "Market" may be abbreviated "Mkt" (successor_hint)
   - The `successor_hint` field on licensees gives known name variants
   - Match on `historical_name` in violation records against `facility_name`
     (and `successor_hint` variants) of licensees
4. **Release boundary filter (CRITICAL):** Exclude all violation records whose
   `violation_date` is after the `release_boundary` date. Count these excluded
   records as `excluded_post_boundary_count`.
5. **Shared address rule:** When a violation's address matches multiple
   licensees at the same address, do NOT spread (duplicate) the violation across
   all of them. Match to the specific facility name.
6. Rank licensees by:
   - Primary: `violation_count_used` descending
   - Secondary: `most_recent_date_used` descending (more recent = higher rank)
7. Select exactly the top N (typically 10) ranked licensees for the queue.

### Match Confidence

| Confidence | When to Use |
|-----------|-------------|
| `exact` | Facility name matches violation historical_name exactly |
| `close` | Match via successor_hint variant or minor spelling difference |
| `shared_address_manual` | Same address but different facility name; requires manual check |

### Next Step Labels

| Condition | Label |
|-----------|-------|
| Unresolved fines present | `manual fine check` |
| ALERT-related violation found | `manual ALERT check` |
| High-severity or multiple unresolved violations | `board review` |
| Other concerns (successor risk, address mismatch) | `additional record check` |

### Method Flags

- `post_boundary_exclusion_applied`: `true` if any violations were excluded for being post-boundary
- `shared_address_records_not_spread`: `true` (always — violations are NOT duplicated across same-address licensees)

---

## Workflow 4: Alcohol Monitoring Plan (train_005 pattern)

### Data Sources

Same as Workflow 2, plus:
- `GET /api/search/address?address=<A>` for cross-domain context

### Key Assessments

**Successor Risk Classification:**
- No prior licensee → `LOW`
- Prior licensee with no incidents → `MODERATE`
- Prior licensee with incidents or settlements → `HIGH`

**Standard Obligations:** List all obligations from the standard-obligations
endpoint for the license type. Each gets:
- `obligation_code` from the API
- `source_obligation_id` from the API's `obligation_id`
- `evidence_required` from the API

**Premises-Specific Controls:** From the restrictions endpoint, filter to
`category: "premises-specific"`. Each gets:
- `control_code` from `restriction_code`
- `source_ids`: list of `restriction_id` values
- `check_code`: determined by control type (AGE_CHECK → DEVICE_AUDIT, SECURITY_LOG → SECURITY_LOG_REVIEW, NO_AFTER_MIDNIGHT_SERVICE → SERVICE_LOG_REVIEW, PATIO_LIMIT → PATROL_OBSERVATION, etc.)
- `first_90_day_check`: `true` for controls that need verification within 90 days of issuance

**Verification Gaps** (see Workflow 2 gap codes plus these additions):
- `CONTROL_EVIDENCE_NOT_VERIFIED` — restrictions exist but evidence unverified
- `STANDARD_CONTROL_OVERLAP` — standard obligation overlaps premises control
- `SUCCESSOR_CONTROL_SEPARATION` — need to distinguish successor from prior controls
- `POST_REVIEW_SETTLEMENT_TIMING` — settlement after review creates timing gap

**Records Requests:** Documents to request before final determination:
- Based on gaps found, request: device audits, police call logs, settlement packets, inspection calendars, ownership statements

**Escalation Triggers:** Conditions that would escalate the license:
- Missing/failed age-check audit
- First-90-day check missed
- New high-severity incident
- Pending incident confirmed as violation
- Successor link confirmed to prior licensee

---

## Cross-Cutting Rules

### Output Format
- **Always return pure JSON** — no markdown fences, no prose outside the JSON
- Match the `answer_template.json` schema exactly
- Use only controlled enum values from the template
- Sort lists as specified (typically ascending by ID/code)
- All counts must be integers

### Date Formats
- Full dates: `YYYY-MM-DD`
- Year-month: `YYYY-MM`
- Always use the format specified in the template

### API Pattern
- All endpoints return JSON with structure: `{ "count": N, "data": [...], "meta": {...} }`
- The `/exports/` CSV endpoints return raw CSV
- The `/api/search/address` endpoint returns a structured cross-domain result
- All `?name=` queries use substring matching — always filter results by exact name match

### Common Pitfalls
1. **Fuzzy name matching**: Never trust a `?name=` result without filtering by exact legal_name AND principal_name
2. **DBA truncation**: The DBA field in CSVs and sometimes in API responses has character-level truncation (e.g., "Summitntracting" for "Summit Contracting") — use `legal_name`, not `dba`, for matching
3. **Trade-scoped bulletins**: A bulletin for "Roofing" does not apply to "Plumbing" — check `trade_scope` against the application's `trade`
4. **Bond records**: A contractor may have multiple bond records; match by legal_name + principal_name, then check status (active/cancelled/reduced)
5. **Violation matching**: Violation records also use fuzzy name matching — filter to the exact legal_name + principal_name
6. **Release boundary**: In renewal reviews, violations with dates after the release boundary must be excluded from counts (but counted separately)
7. **Shared addresses**: Multiple licensees can share an address — do not duplicate violation counts across them
8. **Empty vs missing**: An empty string `""` for `disposition` in incidents counts as unresolved; a missing/empty `cancellation_date` in bonds means not cancelled
9. **Correspondence filtering**: Batch correspondence uses `affects_application_id` — only consider items for the specific application being reviewed
10. **Bulletin effective date ordering**: When multiple bulletins of the same rule_type exist, the one with the latest `effective_date` ≤ cutoff applies
