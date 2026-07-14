# Cascadia Licensing Review Portal (CLRP) — Skill

## Overview
This skill covers all CLRP task variants: contractor eligibility reviews, alcohol license
reviews, renewal manual-review queues, and alcohol monitoring plans. The CLRP is a REST API
plus CSV exports. Every task requires one JSON output conforming to the supplied
`input/payloads/answer_template.json`.

## Environment
- **Base URL**: Always use `http://34.46.77.124:9019`. Replace every `<TASK_ENV_BASE_URL>`
  placeholder with this URL.
- Never start local env, run setup scripts, or inspect hidden/task files.
- All endpoints are read-only GETs. All API endpoints return JSON; exports return CSV.

## Quick-Reference Endpoints

### Contractor domain
| Endpoint | Key param |
|---|---|
| `GET /api/contractors/applications?batch_id=` | `batch_id` (e.g. `HS-2026-Q1A`) |
| `GET /api/contractors/bonds?name=` | contractor legal or principal name |
| `GET /api/contractors/insurance?name=` | contractor legal name or policy name |
| `GET /api/contractors/violations?name=` | contractor legal or principal name |
| `GET /api/contractors/complaints?name=` | contractor legal name |
| `GET /api/contractors/field-notes?name=` | contractor legal name |
| `GET /api/contractors/correspondence?batch_id=` | `batch_id` |
| `GET /api/contractors/bulletins?effective_on=` | date `YYYY-MM-DD` (use the cutoff date) |
| `GET /exports/contractor_batch_<batch_id>.csv` | bulk CSV export |

### Alcohol domain
| Endpoint | Key param |
|---|---|
| `GET /api/alcohol/applications?review_month=` | `YYYY-MM` |
| `GET /api/alcohol/premises?premises_id=` | premises ID |
| `GET /api/alcohol/incidents?premises_id=` | premises ID |
| `GET /api/alcohol/settlements?premises_id=` | premises ID |
| `GET /api/alcohol/restrictions?premises_id=` | premises ID |
| `GET /api/alcohol/standard-obligations?license_type=` | license type string |

### Renewals domain
| Endpoint | Key param |
|---|---|
| `GET /api/renewals/licensees?release_batch=` | release batch (e.g. `RV-2026-SPRING`) |
| `GET /api/renewals/violations?city=` | city name for address-matched violations |
| `GET /exports/renewal_roster_<release_batch>.csv` | bulk CSV export |

### Address search
| Endpoint | Key param |
|---|---|
| `GET /api/search/address?address=` | address string for cross-referencing |

## Workflow

### 1. Orient
Read `input/payloads/answer_template.json` first — it defines the exact output schema,
required keys, allowed enum values, sort orders, and field types. Then read the prompt
for task type, identifiers, and cutoff/boundary dates.

### 2. Gather data
Use the endpoints matching the task domain:
- **Contractor eligibility**: applications → CSV export (optional bulk cross-check) →
  bonds/insurance/violations/complaints/field-notes per applicant → correspondence →
  bulletins effective on cutoff date.
- **Alcohol review**: applications for review month → target premises → incidents →
  settlements → restrictions → standard-obligations for license type.
- **Renewal queue**: licensees for release batch → roster CSV → violations by city
  for each licensee (use address search to match facility addresses to cities).
- **Alcohol monitoring plan**: target application → premises → incidents → settlements →
  restrictions → standard-obligations.

### 3. Apply decision logic
See the decision-rules section below for each task type.

### 4. Format output
Produce **exactly one JSON object**. No markdown fences, no narrative outside the JSON.
Use only the controlled enum values from the template. Sort lists as specified
(ascending by ID is the default). All counts are integers. Dates are `YYYY-MM-DD`.

## Decision Rules

### Contractor Eligibility (HOLD/APPROVE/DENY)
For each application in the batch, check every deficiency dimension:

| Deficiency check | Data source | HOLD reason_code | next_action |
|---|---|---|---|
| Bond amount < required minimum | bonds API + bulletins | `BOND_SHORTFALL` | `REQUEST_BOND_RIDER` |
| Bond status cancelled/revoked | bonds API | `BOND_CANCELLED` | `REQUEST_REPLACEMENT_BOND` |
| Insurance insufficient/missing/expired | insurance API | `INSURANCE_VERIFY` | `REQUEST_INSURANCE_VERIFICATION` |
| Open violation with unresolved penalty | violations API | `UNRESOLVED_PENALTY` | `REFER_UNRESOLVED_PENALTY` |
| Adverse field inspection note | field-notes API | `FIELD_NOTE_HOLD` | `REQUEST_FIELD_CLEARANCE` |
| Serious disqualifying complaint/violation | complaints + violations | `DISQUALIFYING_CONDUCT` | `DENY_APPLICATION` |
| Experience documentation gap | applications data | `EXPERIENCE_VERIFY` | `REQUEST_EXPERIENCE_DOCUMENTATION` |
| Material correspondence flagged | correspondence API | `CORRESPONDENCE_HOLD` | *(see template)* |
| Prior registration adverse history | applications/prior records | `ADVERSE_PRIOR_REGISTRATION` | *(see template)* |
| Exam score below bulletin minimum | applications + bulletins | `EXAM_SCORE_SHORTFALL` | *(see template)* |
| Financial statement missing | applications/CSV | `FINANCIAL_STATEMENT_MISSING` | *(see template)* |
| No issues found | all clear | `NO_DEFICIENCY` | `NO_ACTION` |

- **APPROVE** when `NO_DEFICIENCY` is the only code.
- **DENY** when `DISQUALIFYING_CONDUCT` is present.
- **HOLD** for all other deficiencies.
- When multiple HOLD-level deficiencies exist, use `COMBINED_HOLD_REVIEW` as `next_action`.
- `primary_bulletin_ids`: list bulletin IDs whose rule changes caused or contributed to
  the deficiency. Empty list when no bulletin is the driver.

#### Manual followup mapping (for tasks that require it)
Map each HOLD reason_code to a followup_reason_code:
- `ADVERSE_PRIOR_REGISTRATION` → `PRIOR_REGISTRATION_FILE_REVIEW`
- `BOND_CANCELLED` → `BOND_REPLACEMENT_REQUIRED`
- `BOND_SHORTFALL` → `BOND_INCREASE_REQUIRED`
- `INSURANCE_VERIFY` → `CARRIER_VERIFICATION_REQUIRED` (or `INSURANCE_REPLACEMENT_REQUIRED` if policy is cancelled/expired)
- `FIELD_NOTE_HOLD` → `INSPECTOR_CLEARANCE_REQUIRED`
- `UNRESOLVED_PENALTY` → `PENALTY_LEDGER_REVIEW`
- `EXPERIENCE_VERIFY` → `EXPERIENCE_DOCUMENTATION_REQUIRED`
- `CORRESPONDENCE_HOLD` → `MATERIAL_CORRESPONDENCE_REVIEW`
- `FINANCIAL_STATEMENT_MISSING` → `FINANCIAL_STATEMENT_REQUIRED`

#### Bulletin impact analysis
- Query bulletins with `effective_on=<review_cutoff_date>`.
- Bulletins effective on or before the cutoff date may change minimums for bonds,
  insurance, exams, or experience.
- An application is "changed by bulletins" if a bulletin-altered threshold is the
  reason it now fails when it would have passed under pre-bulletin rules.
- `deficiency_count_by_rule_type` counts applications whose deficiency is driven by
  each rule type: `EXAM_MINIMUM`, `BOND_MINIMUM`, `INSURANCE_MINIMUM`, `EXPERIENCE_MINIMUM`.
- `unchanged_by_bulletins_count`: applications whose determination would be the same
  with or without the Q1 2026 bulletins.

### Alcohol License Review
For the target application at the target premises:
- **same_premises_basis**: `SAME_ADDRESS_OVERLAP` if the premises address matches prior
  incidents/settlements; `PRIOR_SETTLEMENT_AT_ADDRESS` if a settlement exists at this
  address; `NONE` otherwise.
- **prior_incident_level**: based on count and severity — 0 → `NONE`, 1-2 low → `LOW`,
  3-4 mixed → `MODERATE`, 5+ or any high-severity → `HIGH`.
- **incident_count**: total incidents at premises.
- **unresolved_incident_count**: incidents with pending or blank disposition.
- **high_severity_incident_count**: incidents marked high severity.
- **settlement_posture**: `CURRENT_SETTLEMENT` if active settlement exists;
  `PRIOR_RESTRICTED_OR_DENIAL` if prior restrictive action; `PRIOR_WARNING_WITH_CONTROLS`
  if prior warning; `NONE` if no settlement history.
- **control_coverage**: `ADEQUATE_LOCATION_SPECIFIC` if premises-specific controls exist
  and address key risks; `STANDARD_ONLY` if only license-type/all-license obligations
  apply; `NO_CONTROLS` if no controls at all.
- **overall_risk**: synthesize from incidents + settlements + control coverage.
  Default to `ELEVATED` when high unresolved incidents and STANDARD_ONLY controls.
- **recommendation**: `ISSUE_RESTRICTED` if risk is low with controls; `REQUEST_FOLLOWUP`
  if gaps exist; `DENY` if severe risk with no mitigations.
- **verification_gaps**: list specific gap enum values from template based on what
  controls/checks are missing vs. what incidents/settlements imply is needed.
- **inspection_controls**: partition into `standard_obligations` (from license type and
  all-license standards) and `location_specific_restrictions` (from premises restrictions
  API). Map each control_code to its source and evidence.
- **review_month_comparison**: fetch all applications for the review month, count total,
  count those with location-specific controls, list their application IDs.

### Renewal Manual-Review Queue
- Fetch all licensees for the release batch.
- Fetch the renewal roster CSV for bulk cross-reference.
- For each licensee, query violations by city (derived from facility address via address
  search or roster).
- **Exclude** violations with date after the release boundary.
- **Rank** licensees by violation count descending; use most recent violation date as
  tiebreaker (more recent ranks higher).
- **match_confidence**: `exact` when facility name and address both match violation
  records cleanly; `close` when partial match (e.g. name matches but address differs
  slightly); `shared_address_manual` when multiple licensees share an address.
- **next_step_label**: based on violation recency and count:
  - Recent (within ~2 months of boundary) + high count → `board review`
  - Moderate count + medium recency → `manual fine check`
  - Older violations → `manual ALERT check`
  - Edge cases → `additional record check`
- Exactly 10 entries in the queue, ranked 1–10.
- `post_boundary_exclusion_applied`: true when any violation was excluded for being
  after the boundary.
- `excluded_post_boundary_count`: count of violations excluded for post-boundary dates.
- `shared_address_records_not_spread`: true when shared-address licensees are kept
  grouped rather than spread across the queue.

### Alcohol Monitoring Plan
- Determine **successor_risk_classification**: `HIGH` if prior licensee at same premises
  with incidents/settlements; `MODERATE` if same premises but clean history; `LOW`
  if no prior licensee.
- **verification_gaps**: check for pending incident dispositions, post-review settlement
  timing, standard control overlap (when a standard obligation duplicates a premises
  restriction), and successor control separation needs.
- **standard_obligations**: list from `/api/alcohol/standard-obligations?license_type=`
  for the application's license type, plus all-license obligations.
- **premises_specific_controls**: derive from incidents (disorder → LATE_NIGHT_DISORDER_MONITORING),
  settlements (conditions → QUARTERLY_INSPECTION_CONDITION), restrictions (AGE_CHECK, etc.),
  and incident history suggesting security plan lapses.
- **records_requests**: one entry per group of related source IDs, requesting the specific
  evidence packet needed.
- **escalation_triggers**: for each key control or gap, define what monitored event should
  trigger escalation. Common triggers: missed audit, missed 90-day check, new high-severity
  incident, confirmed violation from pending incident, confirmed successor link.

## Source Precedence
1. API JSON responses (authoritative, structured, real-time).
2. CSV exports (bulk, good for cross-referencing and counting).
3. `answer_template.json` (defines schema — never deviate from its allowed enum values).

## Output Conventions
- Exactly one JSON object. No markdown, no narrative outside the JSON.
- All enum values are **case-sensitive** — copy exactly from the template.
- Dates: `YYYY-MM-DD` (months: `YYYY-MM` for alcohol review_month fields).
- Counts: always integers, never floats.
- Lists: sort ascending by ID unless the template explicitly says order doesn't matter.
- Empty lists: use `[]`, never `null` or omitted.
- `primary_bulletin_ids` / `source_ids`: empty list when no source drives the item.
- Boolean fields: use JSON `true`/`false`, never strings.

## Common Pitfalls
- **Wrong base URL**: Always use the URL from environment_access.md, never localhost or a
  URL from prompt text when it differs.
- **Post-boundary violations**: In renewal queues, always filter out violations dated
  after the release boundary before ranking.
- **Bulletin effective_on**: Use the review cutoff date, not today's date.
- **Double-counting**: When a deficiency is caused by a bulletin change, count it in both
  the deficiency count AND the bulletin impact section — these are separate tallies.
- **Missing zero counts**: Include every enum value from the template in reason_code
  counts, even those with 0 occurrences.
- **Sort order**: Application IDs and bulletin IDs sort lexicographically (string sort).
- **License type mapping**: For standard obligations, derive the license type from the
  application data (e.g. "RTL", "BREWPUB", "TAVERN", "F_COM") and query accordingly.
- **Address-based matching**: When matching renewal licensees to city violations, use the
  address search API to resolve facility addresses to cities, then query violations by city.
