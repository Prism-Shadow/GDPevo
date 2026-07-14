# Cascadia Licensing Review Portal (CLRP) — Operational Skill

## Workflow Rules

1. **Read the prompt** for the target batch ID, application ID, premises ID, review month, or release batch. Every task identifies the target explicitly.
2. **Substitute `<TASK_ENV_BASE_URL>`** with the remote environment base URL provided in `environment_access.md`. Never use localhost.
3. **Query all relevant CLRP endpoints** for the target before constructing the answer.
4. **Assemble the answer** strictly matching the provided `answer_template.json` schema. Return JSON only — no markdown or prose.
5. **Use controlled enum values only** — never invent values. Enum lists in templates are authoritative.

## Source Precedence

- Remote API responses are the single source of truth.
- CSV exports are redundant copies of the same data; prefer the JSON API for structured fields and use CSV only for batch overview.
- If an API response and a CSV export conflict, trust the API.
- The `answer_template.json` defines the output contract — its field names, ordering requirements, and enum lists are normative.

## Environment API Usage

All endpoints are relative to the base URL. Common patterns:

### Contractor Reviews
| Data | Endpoint |
|------|----------|
| Applications in batch | `GET /api/contractors/applications?batch_id=<id>` |
| Batch CSV export | `GET /exports/contractor_batch_<id>.csv` |
| Bonds for a contractor | `GET /api/contractors/bonds?name=<legal_or_principal>` |
| Insurance | `GET /api/contractors/insurance?name=<legal_name>` |
| Violations | `GET /api/contractors/violations?name=<legal_or_principal>` |
| Complaints | `GET /api/contractors/complaints?name=<legal_name>` |
| Field notes | `GET /api/contractors/field-notes?name=<legal_name>` |
| Batch correspondence | `GET /api/contractors/correspondence?batch_id=<id>` |
| Active bulletins | `GET /api/contractors/bulletins?effective_on=<YYYY-MM-DD>` |

### Alcohol License Reviews
| Data | Endpoint |
|------|----------|
| Applications in month | `GET /api/alcohol/applications?review_month=<YYYY-MM>` |
| Premises detail | `GET /api/alcohol/premises?premises_id=<id>` |
| Incidents | `GET /api/alcohol/incidents?premises_id=<id>` |
| Settlements | `GET /api/alcohol/settlements?premises_id=<id>` |
| Restrictions | `GET /api/alcohol/restrictions?premises_id=<id>` |
| Standard obligations | `GET /api/alcohol/standard-obligations?license_type=<type>` |

### Renewal Reviews
| Data | Endpoint |
|------|----------|
| Licensees in batch | `GET /api/renewals/licensees?release_batch=<id>` |
| Roster CSV export | `GET /exports/renewal_roster_<batch>.csv` |
| **Per-licensee violations** | `GET /api/search/address?address=<full_address>` |
| City-wide violations | `GET /api/renewals/violations?city=<name>` |

**Critical:** For renewal manual-review queues, use `GET /api/search/address?address=...` per licensee — it returns violations WITH `alert_related`, `severity`, `disposition`, `fine_cents`, and `violation_code` fields that the city-wide endpoint omits. These fields drive ranking and next-step labeling.

## Cutoff Date / Boundary Date Filtering

- A **review cutoff date** (contractor reviews) or **release boundary date** (renewal reviews) is always specified. Filter out records with dates **strictly after** the boundary.
- For contractor reviews: violations, correspondence, and field notes dated after the cutoff are excluded from deficiency counts.
- Bond cancellation dates before the cutoff count; cancellations after the cutoff may still count for a "final" screen — check the task framing.
- For renewal reviews: violations with `violation_date > release_boundary` are excluded from per-licensee counts and tallied separately in `excluded_post_boundary_count`.

## Decision Logic

### Contractor Eligibility (APPROVE / HOLD / DENY)

**APPROVE** when `NO_DEFICIENCY` is the sole reason code. All checks pass.

**HOLD** for correctable issues:
- `BOND_SHORTFALL` — actual bond amount (from bonds endpoint) is below the bulletin minimum for the trade. Compare the **actual** bond amount on record, not the declared amount.
- `BOND_CANCELLED` — bond status is `cancelled` with a cancellation date on or before the cutoff.
- `INSURANCE_VERIFY` — insurance `verification_status` is `pending` or `stale`; or correspondence indicates carrier mismatch.
- `UNRESOLVED_PENALTY` — any violation with `status: "unresolved"` and `penalty_due_cents > 0`.
- `FIELD_NOTE_HOLD` — field note with `finding_type: "open hold"` and `recommended_action` containing "hold".
- `CORRESPONDENCE_HOLD` — correspondence with `document_status: "needs_review"` or `"new"` and `item_type: "material notice"`, dated on or before the cutoff.
- `EXPERIENCE_VERIFY` — experience_years below a bulletin threshold for the trade, or conspicuously low (≤2 years) even without a specific bulletin.
- `FINANCIAL_STATEMENT_MISSING` — `financial_statement_filed: 0`.
- `ADVERSE_PRIOR_REGISTRATION` — `background_status: "adverse"` or `"needs_review"` with a non-empty `prior_registration_id`.

**DENY** for disqualifying issues (when the enum includes `DISQUALIFYING_CONDUCT`):
- Violation type `"fraudulent registration"` with `severity: "high"` or `ag_referral: 1`.
- `background_status: "adverse"` combined with unresolved high-severity violations.
- **Note:** Some task schemas omit `DISQUALIFYING_CONDUCT` — check the enum list in the answer template before using it.

### Renewal Manual-Review Queue Ranking

Rank licensees by (in priority order):
1. `alert_related` count (descending) — violations with `alert_related: 1`
2. High-severity count (descending) — `severity: "high"`
3. Total pre-boundary violation count (descending)
4. Most recent violation date (descending)

**Match confidence:** Use `"exact"` when the violation address matches the licensee address after normalizing suite/unit prefixes. Use `"close"` when the address matches only after suite normalization.

**Next-step labels:**
- `"board review"` — 3+ alert-related violations OR 3+ high-severity violations
- `"manual ALERT check"` — any alert-related violations
- `"manual fine check"` — violations with `violation_code: "UNPAID_FINE"`
- `"additional record check"` — other patterns needing documentation

### Alcohol License Review Risk Assessment

**same_premises_basis:** Use `"SAME_ADDRESS_OVERLAP"` when the premises record shows a prior licensee at the same address. Use `"PRIOR_SETTLEMENT_AT_ADDRESS"` when there is a prior settlement but no same-address prior licensee. Use `"NONE"` otherwise.

**prior_incident_level:** The maximum severity among all incidents at the premises (`"NONE"` < `"LOW"` < `"MODERATE"` < `"HIGH"`).

**incident_count:** Total incidents returned for the premises.

**unresolved_incident_count:** Incidents with disposition `"pending"` or blank/empty disposition.

**high_severity_incident_count:** Incidents with `severity: "high"`.

**settlement_posture:** Map from most recent settlement:
- No settlement → `"NONE"`
- `original_posture: "warning"` → `"PRIOR_WARNING_WITH_CONTROLS"`
- `original_posture` containing "restrict" or "deny" → `"PRIOR_RESTRICTED_OR_DENIAL"`
- Settlement with `prior_or_current: "current"` → `"CURRENT_SETTLEMENT"`

**control_coverage:** `"ADEQUATE_LOCATION_SPECIFIC"` when the premises has restriction records with `category: "premises-specific"` that cover the risk areas identified by incidents. `"STANDARD_ONLY"` when only standard obligations or settlement-imposed standard obligations exist. `"NO_CONTROLS"` when the restrictions list is empty.

**overall_risk:** Derived from the combination — HIGH incident level + STANDARD_ONLY controls → `"ELEVATED"` or `"SEVERE"`. HIGH + ADEQUATE controls → `"MODERATE"`. LOW incidents + STANDARD controls → `"LOW"`.

### Monitoring Plan (Alcohol)

**Recommendation:** `"ISSUE_RESTRICTED_WITH_MONITORING"` is the default when the premises has prior incidents but current restrictions exist. Use `"REQUEST_RECORDS_BEFORE_ISSUE"` when pending incident dispositions or unverified settlement terms need resolution first. Use `"DENY"` only for severe unresolved patterns.

**Successor risk:** `"HIGH"` when same-premises basis is confirmed with overlapping service area and prior incidents. `"MODERATE"` with same address but resolved incidents. `"LOW"` otherwise.

## Bulletin Impact Rules

- Bulletins with `effective_date` on or before the review cutoff date apply to all applications in the batch.
- An application is **changed by a bulletin** when its determination would differ under the prior rule vs. the new rule. Examples:
  - Bond amount met the old minimum but fails the new minimum → changed.
  - Bond amount fails both old and new minimums → NOT changed (the bulletin didn't cause the shortfall).
  - Exam score passes both thresholds → NOT changed.
- `deficiency_count_by_rule_type` counts the number of applications where a deficiency is specifically caused by a bulletin rule-type change, not just the number of applications with that type of deficiency.
- `unchanged_by_bulletins_count` = total applications minus changed applications.

## Output Conventions

1. **JSON only.** Never include markdown fences, prose, or commentary outside the JSON object.
2. **Application IDs in ascending order** where the schema requires ordered lists.
3. **Reason codes in enum definition order** (the order they appear in the template/schema).
4. **Dates as YYYY-MM-DD strings.** Months as YYYY-MM strings.
5. **All counts are integers.**
6. **Empty lists use `[]`**, not null. Use `""` for empty string fields.
7. **Enum values are case-sensitive.** Match the template exactly.

## Calculation Habits

- For bonds: use the **actual** bond amount from the bonds API (`amount` field), not the `declared_bond_amount` from the application.
- For insurance: check both `verification_status` and `coverage_amount` against bulletin minimums. `status: "stale"` or `verification_status: "pending"` triggers `INSURANCE_VERIFY` even if coverage meets the minimum.
- For field notes: only `finding_type: "open hold"` triggers `FIELD_NOTE_HOLD`. `"resolved note"`, `"document check"`, and `"site visit"` do not — even if `recommended_action` says "hold."
- For violations: `penalty_due_cents > 0` with `status: "unresolved"` triggers `UNRESOLVED_PENALTY`. Resolved violations ($0 penalty or `status: "resolved"`) do not count.
- Distractor bond records (identified by notes like "Distractor surety record for similar legal name") should be ignored — use only the bond matching the current application's legal name.
- Violations matched to a different legal name variant (e.g., a truncated name like "Harbor Summitntracting" when the applicant is "Harbor Summit Contracting Inc") should be excluded — query with the exact legal name to verify.

## Pitfalls

- **Don't use city-wide violation queries for ranking.** The `/api/renewals/violations?city=...` endpoint returns violations for ALL addresses in that city, past and present. Most won't match current licensees. Use `GET /api/search/address?address=...` per licensee instead.
- **Don't count post-boundary violations in ranking.** Filter strictly by `violation_date <= release_boundary`.
- **Don't assume all trades have bulletins.** Only the trades listed in bulletin `trade_scope` fields are affected. Solar, Fire Protection, and other unlisted trades use no bulletin minimums (unless General Builder applies).
- **Don't confuse declared vs. actual amounts.** Applications declare expected bond/insurance; the bonds/insurance endpoints show what's actually on file.
- **Match addresses exactly after normalization.** Remove "Suite B, " prefixes before comparing. Don't fuzzy-match on street name alone — different streets with the same number are different addresses.
- **Check correspondence `received_date` against the cutoff.** Correspondence received after the cutoff may still be listed in the API but should be excluded from deficiency counts.
- **Follow the answer template enums exactly.** Different task variants for the same domain (e.g., HS-2026-Q1A vs HS-2026-Q1B) may use different reason code sets. Always read the template before assigning codes.
