# API Endpoint Catalog

All endpoints are accessed from the base URL provided in the task prompt as `<TASK_ENV_BASE_URL>` (environment variable or placeholder in the prompt).

## Authentication

All GET endpoints are unauthenticated unless the prompt specifies a header. The POST `/api/sql` endpoint requires:

```
Header: X-Task-Token
Value: licensing-review-019
```

## Endpoints by Domain

### Cross-Domain

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/policies` | Current policy baseline: financial minimums, endorsement requirements, experience thresholds, and other regulatory standards. Compare current against prior baseline to determine `policy_impacted`. |
| POST | `/api/sql` | SQL query access for cross-entity joins and complex lookups. Body: `{"query": "<SQL>"}`. Requires `X-Task-Token` header. |

### Contractor Review (train_001, train_004 patterns)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/contractor/applications` | Application records including applicant identity, license class, experience claimed, endorsements requested, and application status. |
| GET | `/api/contractor/bonds` | Bond/surety records: bond amount, effective date, expiry/cancellation date, status. |
| GET | `/api/contractor/insurance` | Insurance records: coverage type, amount, effective date, expiry date, carrier, status. |
| GET | `/api/contractor/license-history` | Prior license records: suspensions, revocations, disciplinary actions, dates, status. |
| GET | `/api/contractor/violations` | Violation/complaint records: violation type, severity (minor/serious), status (open/resolved), dates. |
| GET | `/api/contractor/correspondence` | Correspondence records: ID, sender, recipient, subject, date sent, verification status, stale/unverified flags. |
| GET | `/api/contractor/inspections` | Inspection records: inspection type, date, outcome, documentation gaps, safety recheck flags. |

### Restricted Liquor License Review (train_002, train_005 patterns)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/liquor/applications` | License application records including applicant, premises, license class, same-premises basis, requested controls. |
| GET | `/api/liquor/settlements` | Settlement/agreement records: prior settlement terms, conditions, status. |
| GET | `/api/liquor/privileges` | License privilege records: current grants, restrictions, operating conditions. |
| GET | `/api/liquor/incidents` | Incident records at or near the premises: type, date, severity, status (open/closed), police memo references. |
| GET | `/api/liquor/site-evidence` | Site evidence records: floor plans, photos, control signage, camera evidence, food-service evidence, neighbor notices, tax clearance status. |

### Alcohol Renewal Review (train_003 pattern)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/alcohol/licensees` | Licensee records: license number, facility name, address, license type, status. |
| GET | `/api/alcohol/violations` | Violation records: violation ID, related license number(s), facility address, violation type, date, severity. May reference current or legacy license numbers. |
| GET | `/api/renewal/rules` | Renewal rule definitions: renewal requirements, boundary dates, screening criteria, escalation thresholds. |

## SQL Query Patterns

Use `POST /api/sql` when the GET endpoints do not provide sufficient join or filtering capability. Common patterns:

- Join licensees to violations where the license number matches directly or through a legacy/alternate identifier.
- Filter violations by date range relative to a boundary.
- Aggregate violation counts per licensee.
- Cross-reference correspondence IDs against applications when the GET response does not include the full linkage.

Always prefer GET endpoints first and use SQL only when the direct endpoint does not provide the needed cross-entity view.
