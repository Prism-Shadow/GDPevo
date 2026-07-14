# Cascadia Licensing Review Portal (CLRP) — Skill

## Overview

Conduct formal regulatory reviews through the Cascadia Licensing Review Portal (CLRP), a REST API for Harbor State contractor eligibility, alcohol licensing, and license renewal screening. Every task produces **exactly one JSON object** conforming to `input/payloads/answer_template.json`. No markdown, no narrative outside the JSON.

## Environment

- **Base URL**: `http://34.46.77.124:9019` (replaces every `<TASK_ENV_BASE_URL>` placeholder).
- **Response format**: All API endpoints return JSON except CSV exports.
- **No local files**: Do not inspect env, setup scripts, databases, or hidden task files. Use only the public API and exports.

## Workflow (every task)

1. **Read the template** — `input/payloads/answer_template.json` is the contract: required keys, allowed enum values, types, formats, ordering rules, and numeric precision.
2. **Gather the roster** — fetch the main listing endpoint or CSV export to get every application/licensee that must be reviewed.
3. **Fetch cross-cutting data** — bulletins (if applicable), batch correspondence, address searches.
4. **Per-entity detail** — for each application/licensee, query bonds, insurance, violations, complaints, field notes, incidents, settlements, restrictions, standard obligations as relevant.
5. **Apply rules** — compare entity data against regulatory thresholds (bond minimums, insurance requirements, exam scores, experience, incident history, settlement posture, control coverage).
6. **Count and sort** — populate deficiency/determination counts; sort lists per template ordering rules.
7. **Validate** — every key matches the template; every value is from the allowed enum set; every count is an integer.

## Source Precedence

1. **`answer_template.json`** — defines the output schema. Required keys, enums, ordering, and types are non-negotiable.
2. **API responses** — ground truth for entity state.
3. **CSV exports** — equivalent to API listings; use whichever is more complete.
4. **Bulletins API** — defines regulatory minimums/thresholds effective on the review date. When a bulletin raises a threshold, entities that met the old threshold but not the new one are impacted.

## Public API Reference

### Contractor Domain
| Endpoint | Purpose |
|---|---|
| `GET /api/contractors/applications?batch_id=<id>` | List applications in a batch |
| `GET /exports/contractor_batch_<id>.csv` | CSV export of batch |
| `GET /api/contractors/bonds?name=<name>` | Bond records (try legal name and principal name) |
| `GET /api/contractors/insurance?name=<name>` | Insurance records |
| `GET /api/contractors/violations?name=<name>` | Violations/penalties |
| `GET /api/contractors/complaints?name=<name>` | Complaints |
| `GET /api/contractors/field-notes?name=<name>` | Field inspection notes |
| `GET /api/contractors/correspondence?batch_id=<id>` | Batch-level correspondence |
| `GET /api/contractors/bulletins?effective_on=<date>` | Bulletins effective on YYYY-MM-DD |

### Alcohol License Domain
| Endpoint | Purpose |
|---|---|
| `GET /api/alcohol/applications?review_month=YYYY-MM` | Applications for review month |
| `GET /api/alcohol/premises?premises_id=<id>` | Premises details |
| `GET /api/alcohol/incidents?premises_id=<id>` | Incidents at premises |
| `GET /api/alcohol/settlements?premises_id=<id>` | Settlements at premises |
| `GET /api/alcohol/restrictions?premises_id=<id>` | Premises-specific restrictions |
| `GET /api/alcohol/standard-obligations?license_type=<type>` | Standard obligations by license type |

### Renewal Domain
| Endpoint | Purpose |
|---|---|
| `GET /api/renewals/licensees?release_batch=<batch>` | Licensees in release batch |
| `GET /api/renewals/violations?city=<city>` | Violations by city |
| `GET /api/search/address?address=<addr>` | Address search for fuzzy matching |
| `GET /exports/renewal_roster_<batch>.csv` | CSV roster export |

## Determination Rules

### Contractor Eligibility

Map each deficiency to its determination and next action:

| Reason Code | Determination | Next Action |
|---|---|---|
| `NO_DEFICIENCY` | `APPROVE` | `NO_ACTION` |
| `BOND_SHORTFALL` | `HOLD` | `REQUEST_BOND_RIDER` |
| `BOND_CANCELLED` | `HOLD` | `REQUEST_REPLACEMENT_BOND` |
| `INSURANCE_VERIFY` | `HOLD` | `REQUEST_INSURANCE_VERIFICATION` |
| `UNRESOLVED_PENALTY` | `HOLD` | `REFER_UNRESOLVED_PENALTY` |
| `FIELD_NOTE_HOLD` | `HOLD` | `REQUEST_FIELD_CLEARANCE` |
| `EXPERIENCE_VERIFY` | `HOLD` | `REQUEST_EXPERIENCE_DOCUMENTATION` |
| `CORRESPONDENCE_HOLD` | `HOLD` | `COMBINED_HOLD_REVIEW` |
| `ADVERSE_PRIOR_REGISTRATION` | `HOLD` | `COMBINED_HOLD_REVIEW` |
| `EXAM_SCORE_SHORTFALL` | `HOLD` | `COMBINED_HOLD_REVIEW` |
| `FINANCIAL_STATEMENT_MISSING` | `HOLD` | `COMBINED_HOLD_REVIEW` |
| `DISQUALIFYING_CONDUCT` | `DENY` | `DENY_APPLICATION` |

**Multiple HOLD reasons** → `next_action` = `COMBINED_HOLD_REVIEW`.
**HOLD + DENY reasons** → `DENY` wins (most severe).

### Contractor Manual Followup Mapping

When `manual_followup_required` is true, map reason codes to followup codes:

| Reason Code | Followup Reason Code |
|---|---|
| `ADVERSE_PRIOR_REGISTRATION` | `PRIOR_REGISTRATION_FILE_REVIEW` |
| `BOND_CANCELLED` | `BOND_REPLACEMENT_REQUIRED` |
| `BOND_SHORTFALL` | `BOND_INCREASE_REQUIRED` |
| `INSURANCE_VERIFY` | `CARRIER_VERIFICATION_REQUIRED` |
| `FIELD_NOTE_HOLD` | `INSPECTOR_CLEARANCE_REQUIRED` |
| `UNRESOLVED_PENALTY` | `PENALTY_LEDGER_REVIEW` |
| `EXPERIENCE_VERIFY` | `EXPERIENCE_DOCUMENTATION_REQUIRED` |
| `FINANCIAL_STATEMENT_MISSING` | `FINANCIAL_STATEMENT_REQUIRED` |
| `CORRESPONDENCE_HOLD` | `MATERIAL_CORRESPONDENCE_REVIEW` |

### Alcohol License Risk Assessment

1. **Same-premises basis**: check settlements and incidents at the target premises address.
   - No prior activity → `NONE`
   - Prior settlement at same address → `PRIOR_SETTLEMENT_AT_ADDRESS` or `SAME_ADDRESS_OVERLAP`
2. **Prior incident level**: derived from incident_count and severity.
   - 0 incidents → `NONE`
   - 1–2 incidents, none high-severity → `LOW`
   - 3–4 incidents or 1 high-severity → `MODERATE`
   - 5+ incidents or multiple high-severity → `HIGH`
3. **Settlement posture**: review settlement history.
   - No settlements → `NONE`
   - Prior warning with controls → `PRIOR_WARNING_WITH_CONTROLS`
   - Prior restriction or denial → `PRIOR_RESTRICTED_OR_DENIAL`
   - Active settlement → `CURRENT_SETTLEMENT`
4. **Control coverage**:
   - Has current location-specific restrictions → `ADEQUATE_LOCATION_SPECIFIC`
   - Only standard obligations, no premises-specific → `STANDARD_ONLY`
   - No restrictions at all → `NO_CONTROLS`
5. **Overall risk**: synthesize. `HIGH` incident level + `STANDARD_ONLY` controls → `ELEVATED` or `SEVERE`.

### Alcohol License Recommendation

- No incidents, no prior settlements, standard obligations adequate → `ISSUE_RESTRICTED` / `ISSUE_STANDARD`
- Unresolved incidents, missing location-specific controls, prior warnings → `REQUEST_FOLLOWUP`
- Current settlement with violation, severe incident history → `DENY`

## Renewal Manual-Review Queue Ranking

1. Fetch the **roster** (API or CSV) and **violations by city** for each licensee.
2. **Match** violations to licensees: exact name match → `exact`; close fuzzy match → `close`; same address different name → `shared_address_manual`.
3. **Exclude** violations with `violation_date` after the release boundary date.
4. **Rank** by: violation_count_used descending (primary), most_recent_date_used descending (secondary).
5. **Assign next_step_label**:
   - 4+ violations → `board review`
   - Fines-dominant pattern (violations mentioning fines/penalties) → `manual fine check`
   - ALERT-flagged violations → `manual ALERT check`
   - Edge cases or shared-address matches → `additional record check`
6. **Shared address records** apply to the matched licensee only; do not spread across licensees.

## Bulletin Impact Rules

- Fetch bulletins with `effective_on=<review_cutoff_date>`.
- Bulletins may change minimums for bonds, insurance, exams, or experience.
- An application is **changed by bulletins** if its determination would differ under pre-bulletin rules (i.e., it met old thresholds but fails new ones).
- Count impacted applications in `applications_changed_by_2026_bulletins`.
- Count per-rule-type deficiencies: `BOND_MINIMUM`, `INSURANCE_MINIMUM`, `EXAM_MINIMUM`, `EXPERIENCE_MINIMUM`.
- `unchanged_by_bulletins_count` = total applications − changed_by_bulletins count.

## Output Conventions

- **JSON only** — no markdown fences, no prose.
- **Dates** — `YYYY-MM-DD` format.
- **Months** — `YYYY-MM` format.
- **Counts** — integers only; never floats.
- **Empty lists** — use `[]`, not `null` or absent key.
- **Enums** — case-sensitive; exactly as defined in the template; never invent abbreviations.
- **Sorting** — "ascending by application_id" means lexicographic ascending (`CA-2026-0001` before `CA-2026-0002`). "Use the enum order listed here" means follow the template's array order. "Not significant" means any consistent order is acceptable.
- **Coverage** — every application/licensee in the batch/review-month must appear; no extras.

## Verification Gaps (Alcohol Domain)

Common patterns that produce verification gaps:
- **PENDING_INCIDENT_DISPOSITIONS**: incidents with blank/null disposition → request disposition packet.
- **AGE_VERIFICATION_CONTROL_NOT_IN_CURRENT_RESTRICTIONS**: premises has age-related incidents but no AGE_CHECK restriction.
- **LATE_NIGHT_SECURITY_CONTROL_NOT_IN_CURRENT_RESTRICTIONS**: late-night incidents but no NO_AFTER_MIDNIGHT_SERVICE or SECURITY_LOG restriction.
- **SETTLEMENT_TERMS_NOT_FOUND**: settlement referenced but terms unavailable.
- **SECURITY_PLAN_LAPSE_DISPOSITION_MISSING**: security-plan-related incident with no disposition.
- **CONTROL_EVIDENCE_NOT_VERIFIED**: restriction exists but evidence not confirmed.
- **STANDARD_CONTROL_OVERLAP**: standard obligation duplicates a premises-specific control.
- **SUCCESSOR_CONTROL_SEPARATION**: prior licensee at same premises had issues; controls must be explicitly separated.

## Pitfalls

1. **Using the wrong name for contractor lookups** — bonds/violations may be filed under legal name or principal name. Try both if the first returns empty.
2. **Forgetting to exclude post-boundary violations** — in renewal queues, violations dated after the release boundary must be excluded and counted in `excluded_post_boundary_count`.
3. **Missing bulletin impacts** — always fetch bulletins and compare pre/post thresholds, even if the raw data looks clean.
4. **Sorting by wrong field** — application_id is a string, not a number; sort lexicographically.
5. **Mixing up reason_codes and followup_reason_codes** — they are separate enum spaces with separate mappings.
6. **Incomplete counts** — deficiency_counts and determination_counts must sum correctly: `APPROVE + HOLD + DENY = applications_reviewed`. Reason code counts must match what appears in application_decisions.
7. **Overlooking correspondence** — batch-level correspondence can add `CORRESPONDENCE_HOLD` to applications that otherwise appear clean.
8. **Assuming all licensees have violations** — some may have zero matched violations; they rank last or not at all.
9. **Spreading shared-address violations** — each violation record belongs to exactly one licensee, even if the address matches multiple.
10. **Boolean vs integer confusion** — `target_has_location_specific_controls` is boolean; `target_current_location_specific_control_count` is integer. Don't confuse them.
