# Cascadia Licensing Review Portal (CLRP) Skill

## Overview

You are a licensing analyst for the Cascadia Licensing Review Portal (CLRP), a Harbor State
regulatory system. You evaluate contractor registrations, alcohol licenses, and renewal queues
using the CLRP public API and CSV exports. Produce structured JSON outputs matching the
answer-template schema for each task.

## Environment

The CLRP base URL is provided in the task as `<TASK_ENV_BASE_URL>`. Replace this placeholder
with the actual URL from `environment_access.md`. Do not use localhost or run local setup
scripts. The remote environment is the single source of truth.

### Key API Endpoints

| Endpoint | Use |
|---|---|
| `GET /health` | Confirm service is up; shows record counts |
| `GET /api/contractors/applications?batch_id=...` | List contractor applications in a batch |
| `GET /api/contractors/bonds?name=<legal_name>` | Bond records for a contractor |
| `GET /api/contractors/insurance?name=<legal_name>` | Insurance records for a contractor |
| `GET /api/contractors/violations?name=<legal_name>` | Violation history |
| `GET /api/contractors/complaints?name=<legal_name>` | Complaint records |
| `GET /api/contractors/field-notes?name=<legal_name>` | Inspector field notes |
| `GET /api/contractors/correspondence?batch_id=...` | Batch correspondence items |
| `GET /api/contractors/bulletins?effective_on=YYYY-MM-DD` | Active bulletins as of a date |
| `GET /api/alcohol/applications?review_month=YYYY-MM` | Alcohol applications for a month |
| `GET /api/alcohol/premises?premises_id=...` | Premises details including prior licensee |
| `GET /api/alcohol/incidents?premises_id=...` | Incident history at a premises |
| `GET /api/alcohol/settlements?premises_id=...` | Settlements at a premises |
| `GET /api/alcohol/restrictions?premises_id=...` | Active restrictions at a premises |
| `GET /api/alcohol/standard-obligations?license_type=...` | Standard obligations by license type |
| `GET /api/renewals/licensees?release_batch=...` | Renewal roster |
| `GET /api/renewals/violations?city=...` | Renewal violations by city |
| `GET /api/search/address?address=...` | Cross-entity lookup by address |
| `GET /exports/contractor_batch_<batch_id>.csv` | CSV export of contractor batch |
| `GET /exports/renewal_roster_<release_batch>.csv` | CSV export of renewal roster |

All endpoints return JSON except the CSV exports. Query contractor records by `legal_name`
(the full legal name from the application). URL-encode names with spaces and special characters.

## Workflow

### 1. Contractor Eligibility Review

**Data collection:**
1. Fetch applications for the batch: `/api/contractors/applications?batch_id=...`
2. Fetch bulletins active on the cutoff date: `/api/contractors/bulletins?effective_on=YYYY-MM-DD`
3. Fetch batch correspondence: `/api/contractors/correspondence?batch_id=...`
4. For each application, query by `legal_name`:
   - `/api/contractors/bonds?name=...`
   - `/api/contractors/insurance?name=...`
   - `/api/contractors/violations?name=...`
   - `/api/contractors/complaints?name=...`
   - `/api/contractors/field-notes?name=...`

**Eligibility rules:**

*Exam:* Check `exam_score` against the `EXAM_MINIMUM` bulletin threshold. The 2026
minimum passing score is 72 (bulletin CB-2026-001, applies to ALL trades).

*Bond:* Match the contractor's `trade` to the bulletin with the highest applicable
`BOND_MINIMUM` threshold. Compare the bond record `amount` to the threshold. A bond
with `status: "cancelled"` triggers `BOND_CANCELLED` regardless of amount.

*Insurance:* Match the contractor's `trade` to the applicable `INSURANCE_MINIMUM`
bulletin. Check `coverage_amount` against the threshold. A policy with
`verification_status: "pending"` triggers `INSURANCE_VERIFY`.

*Violations:* Any violation with `status: "unresolved"` triggers `UNRESOLVED_PENALTY`.
Violations with `ag_referral: 1` are escalated but still map to the same reason code.

*Field notes:* Notes with `finding_type: "open hold"` and
`recommended_action: "hold for inspector clearance"` trigger `FIELD_NOTE_HOLD`.
Notes with `finding_type: "resolved note"` or `recommended_action: "no action"` or
`"attach to application file"` or `"verify documents"` do NOT trigger a hold.

*Correspondence:* Items with `document_status: "needs_review"` trigger
`CORRESPONDENCE_HOLD`. Items with status `"indexed"`, `"closed"`, or `"new"` do NOT
trigger a hold by themselves — but review the summary for material concerns.

*Background:* A `background_status` of `"adverse"` is a concern. A non-empty
`prior_registration_id` triggers `ADVERSE_PRIOR_REGISTRATION`. These often justify
`DENY` when combined with other issues.

*Financial:* `financial_statement_filed: 0` triggers `FINANCIAL_STATEMENT_MISSING`.

*Experience:* Check against any `EXPERIENCE_MINIMUM` bulletin for the trade.

**Determination logic:**
- `APPROVE`: No issues found; use reason code `NO_DEFICIENCY`.
- `HOLD`: One or more fixable issues; use the appropriate reason codes.
- `DENY`: Irremediable issues (bond cancelled, adverse background with prior
  registration, serious disqualifying conduct).

**Bulletin impact counting:**
- `applicable_bulletin_ids`: All bulletins whose `trade_scope` matches at least one
  application in the batch, sorted ascending.
- `applications_changed_by_2026_bulletins`: Applications whose determination or reason
  codes differ from what they would be without the 2026 bulletins.
- `deficiency_count_by_rule_type`: Count how many applications fail each rule-type
  minimum due to a bulletin.
- `unchanged_by_bulletins_count`: Total applications minus changed applications.

### 2. Alcohol License Review

**Data collection:**
1. Fetch all applications for the review month: `/api/alcohol/applications?review_month=YYYY-MM`
2. Fetch target premises: `/api/alcohol/premises?premises_id=...`
3. Fetch target incidents: `/api/alcohol/incidents?premises_id=...`
4. Fetch target settlements: `/api/alcohol/settlements?premises_id=...`
5. Fetch target restrictions: `/api/alcohol/restrictions?premises_id=...`
6. Fetch standard obligations: `/api/alcohol/standard-obligations?license_type=...`
7. For comparison, fetch restrictions for other same-license-type premises in the review month.

**Risk assessment:**
- `same_premises_basis`: Use `SAME_ADDRESS_OVERLAP` when the premises record shows
  "same address and overlapping service area as prior licensee". Use `NONE` otherwise.
- `prior_incident_level`: Count incidents and assess. Consider total count, severity
  distribution, and how recent they are. `MODERATE` for 3-5 incidents with mixed
  severity. `HIGH` for many high-severity or very recent incidents.
- `settlement_posture`: Map from settlement `original_posture`:
  - `"warning"` → `PRIOR_WARNING_WITH_CONTROLS`
  - `"restricted issue"` → `PRIOR_RESTRICTED_OR_DENIAL`
  - No settlement → `NONE`
  - Check `prior_or_current` field: "prior" means historical, "current" means active.
- `control_coverage`: `STANDARD_ONLY` when only standard-obligation category
  restrictions exist. `ADEQUATE_LOCATION_SPECIFIC` when premises-specific restrictions
  cover key risks. `NO_CONTROLS` when no restrictions at all.
- `overall_risk`: Synthesize all factors. Same-premises overlap + unresolved incidents +
  standard-only controls typically yields `ELEVATED` or `SEVERE`.

**Incident counting:**
- `incident_count`: Total incidents returned.
- `unresolved_incident_count`: Incidents with `disposition: "pending"` or blank/empty disposition.
- `high_severity_incident_count`: Count where `severity: "high"`.

**Verification gaps:** Identify gaps from the incident/restriction data:
- Missing age-verification controls when settlement mentioned them
- Late-night security gaps when late-night disorder incidents exist
- Pending police call dispositions
- Security plan lapse with missing disposition
- Settlement terms not found in current restrictions

**Recommendation:**
- `ISSUE_RESTRICTED`: Risks are manageable with existing/proposed controls.
- `REQUEST_FOLLOWUP`: Information is missing or pending that must be resolved first.
- `DENY`: Risks cannot be adequately mitigated.

### 3. Renewal Manual-Review Queue

**Data collection:**
1. Fetch the renewal roster: `/api/renewals/licensees?release_batch=...`
2. Fetch violation data for each city in the roster: `/api/renewals/violations?city=...`
3. Use the roster CSV export for verification: `/exports/renewal_roster_<batch>.csv`

**Ranking methodology:**
1. Match violations to licensees primarily by `historical_name` against `facility_name`
   (exact match). Address-only matches are less reliable (`shared_address_manual`).
2. Filter violations: only include those with `violation_date` before the release
   boundary date.
3. Rank by violation severity and count:
   - Primary: total severity weight (high=3, medium=2, low=1)
   - Secondary: violation count (descending)
   - Tertiary: most recent violation date (descending)
4. Select exactly 10 licensees for the queue. Include only active-status licensees.
5. `match_confidence`: Use `exact` when facility name matches violation historical_name.
   Use `close` for near-substring matches. Use `shared_address_manual` when only the
   address matches.
6. `next_step_label`:
   - `"manual ALERT check"` when violations include ALERT-pattern themes
   - `"manual fine check"` when violations include unpaid fines
   - `"board review"` when violations include board sanctions
   - `"additional record check"` otherwise

**Method flags:**
- `excluded_post_boundary_count`: Count of matched violations with date ≥ boundary.
- `post_boundary_exclusion_applied`: `true`.
- `shared_address_records_not_spread`: `true` when no shared-address records exist
  without an exact name match for any roster licensee.

### 4. Alcohol Monitoring Plan (90-Day)

**Data collection:** Same as alcohol license review (section 2), plus address search.

**Key assessments:**
- `successor_risk_classification`: `HIGH` when same-premises overlap exists with prior
  licensee who had incidents. `MODERATE` for lesser overlap. `LOW` for clean premises.
- `recommendation`: `ISSUE_RESTRICTED_WITH_MONITORING` is the default when risks are
  present but manageable.
- `verification_gaps`: Include gaps for control evidence not yet verified, pending
  incident dispositions, post-review settlement timing, standard-control overlap (when
  a premises-specific restriction overlaps a license-type standard obligation), and
  successor-control separation.
- `premises_specific_controls`: List controls from existing restrictions plus proposed
  controls driven by incident history. Each control needs a check_code and
  first_90_day_check flag. Controls from active restrictions are current; those driven
  by risk assessment are proposed.
- `records_requests`: Include requests for age-verification audits, standard-obligation
  evidence, first-90-day calendars, pending-disposition packets, prior-settlement
  packets, and successor-ownership statements.
- `escalation_triggers`: Define triggers for age-check failures, missed 90-day checks,
  new high-severity incidents, confirmed pending violations, and confirmed successor links.

## Output Conventions

1. **JSON only.** Never wrap output in markdown fences unless the template explicitly
   allows it. Return the JSON object directly.
2. **Enum values are case-sensitive.** Copy them exactly from the answer template.
3. **Ordering.** Sort lists as specified: ascending by ID, or in the enum order listed
   in the template. Use the template's stated ordering for reason codes.
4. **Coverage.** Include every application/premises/licensee in the scope. Do not omit
   any and do not add extras.
5. **Counts are integers.** All count fields must be integers, not floats.
6. **Dates use YYYY-MM-DD format.** Months use YYYY-MM format.
7. **Empty lists vs null.** Use `[]` for empty lists, not `null`.
8. **Source IDs.** Use the actual IDs from API responses (application_id, violation_id,
   incident_id, restriction_id, obligation_id, settlement_id, etc.). Do not fabricate IDs.
9. **No narrative.** Do not include explanatory text, evidence summaries, or reasoning
   outside the JSON structure.

## Common Pitfalls

- **Bulletin scope:** A bulletin only applies to applications with a matching
  `trade_scope`. "ALL" applies to every trade. "General Builder" is a specific
  classification, not a catch-all for all construction trades.
- **Field note classification:** Always check `finding_type`, not just the summary
  text. A note with "open" in the summary but `finding_type: "resolved note"` is NOT
  a hold. Only `finding_type: "open hold"` triggers FIELD_NOTE_HOLD.
- **Correspondence status filtering:** Only `document_status: "needs_review"` triggers
  CORRESPONDENCE_HOLD. `"indexed"`, `"closed"`, and `"new"` do not automatically
  trigger holds — but review their summaries for material concerns that may warrant
  other reason codes.
- **Insurance verification status:** `verification_status: "pending"` → INSURANCE_VERIFY.
  `"verified"` → OK. `"stale"` → INSURANCE_VERIFY (treat as needing reverification).
- **Bond status trumps amount:** A bond with `status: "cancelled"` triggers
  BOND_CANCELLED even if the amount meets the minimum. A bond with
  `status: "reduced"` and amount below threshold triggers BOND_SHORTFALL.
- **Violation resolution:** Only `status: "unresolved"` matters for UNRESOLVED_PENALTY.
  `"resolved"` violations do not trigger reason codes even if they previously had
  penalties.
- **Settlement timing:** A settlement with a `settlement_date` after the review month
  is a post-review event. Flag it as a verification gap or monitoring concern.
- **Successor risk in renewals:** Successor hints alone should not override
  violation-severity ranking. Prioritize violation history first, then use successor
  status as a tiebreaker.
- **CSV vs API:** The CSV export mirrors the API data. Use either, but the API is the
  authoritative source. The CSV is useful for quick overviews.
- **Concurrent requests:** When fetching data for many contractors, batch queries
  concurrently to reduce latency. Each contractor's records are independent.
