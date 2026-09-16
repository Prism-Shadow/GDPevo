# API Guide

## Shared authentication

All endpoints live under `<TASK_ENV_BASE_URL>`. For SQL access, include:

```
X-Task-Token: licensing-review-019
```

This is the only credential needed. It is always the same across tasks.

## REST endpoints

Call GET endpoints in parallel -- they are independent and stateless.

### /api/policies

Returns the current policy baseline document. The structure varies by task but
typically includes:

- Effective dates
- Coverage minimums (bond amounts, insurance limits)
- Endorsement requirements
- Experience thresholds
- Inspection criteria
- Correspondence verification windows

Use it to determine whether a deficiency is *policy-driven* (would not exist
under the prior baseline). When an application meets the old standard but
fails the new one, mark `policy_impacted: true`.

### Contractor endpoints

**GET /api/contractor/applications** -- Core application records. Each record
contains at minimum an `application_id`, applicant details, and classification.
Check for status flags, pending items, and completeness.

**GET /api/contractor/bonds** -- Bond records keyed by contractor. Look for:
- Bond amount vs. required minimum
- Active/cancelled/expired status
- Effective and expiration dates

**GET /api/contractor/insurance** -- Insurance policies. Check:
- Coverage amount vs. required limit
- Policy start and end dates against the review date
- Whether the contractor is named as insured

**GET /api/contractor/license-history** -- Prior licenses, suspensions,
revocations. Look for `active_suspension` flags and any historical pattern
of non-compliance.

**GET /api/contractor/violations** -- Citations, complaints, formal actions.
Classify by severity: minor (correctable) vs. serious (disqualifying).

**GET /api/contractor/correspondence** -- Letters, notices, requests for
information. Identify stale or unverified items -- those sent but not
acknowledged -- and list their IDs in `stale_or_unverified_correspondence_ids`.

**GET /api/contractor/inspections** -- Field inspection results. Check for
failed items, recheck requirements, and document gaps.

### Liquor endpoints

**GET /api/liquor/applications** -- Liquor license applications with premise
type, ownership, and transfer details.

**GET /api/liquor/settlements** -- Prior enforcement settlements or board
orders that may restrict the applicant or location.

**GET /api/liquor/privileges** -- Current operating privileges attached to
the applicant or predecessor.

**GET /api/liquor/incidents** -- Police calls, complaints, or reported
incidents at the target location. Use to identify risk codes like
`ASSAULT`, `NOISE`, `AFTER_HOURS`, `MINOR_SALE`.

**GET /api/liquor/site-evidence** -- Floor plans, photos, signage,
neighbor notices, police memos. Identify verification gaps when items
are missing, stale, or contradictory.

### Alcohol renewal endpoints

**GET /api/alcohol/licensees** -- Active license records with facility names,
addresses, and license numbers.

**GET /api/alcohol/violations** -- Violation records. These may or may not be
directly keyed by license number; check for address-based matching as a
fallback. Each record has a date; use it to filter against the boundary date.

**GET /api/renewal/rules** -- Renewal scoring or queue-selection rules. These
define how violations contribute to priority ranking and risk tier assignment.

## SQL endpoint

**POST /api/sql** accepts a JSON body with a `query` field and returns a JSON
result set. Use it when:

- You need a date filter the REST endpoint cannot express (e.g. `WHERE
  violation_date <= '<boundary_date>'`)
- You suspect the REST result is incomplete or paginated
- You need to join violation data with licensee data in a single pass

Example request:

```json
{"query": "SELECT * FROM violations WHERE license_no LIKE '<prefix>%' AND violation_date <= '<boundary_date>' ORDER BY violation_date DESC"}
```

Always check the column names in the result before writing follow-up queries.
Schemas are not documented -- inspect the response to learn them.

## Parallelism

All GET calls for a given domain are independent. Batch them:

- Start all contractor GETs together (policies + applications + bonds +
  insurance + history + violations + correspondence + inspections)
- Start all liquor GETs together (policies + applications + settlements +
  privileges + incidents + site-evidence)
- Start all alcohol GETs together (licensees + violations + rules)

Then, when responses arrive, decide whether SQL is needed and issue it.
