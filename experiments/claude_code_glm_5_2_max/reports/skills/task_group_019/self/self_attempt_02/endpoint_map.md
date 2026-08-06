# Endpoint Map by Archetype

Quick reference for which endpoints to call for each task archetype.
Derived from the five training tasks.

## Contractor Batch Eligibility

| Endpoint | Key data |
|---|---|
| `GET /api/policies` | Current policy baseline, thresholds, new requirements |
| `GET /api/contractor/applications` | Application details, experience info, endorsement status |
| `GET /api/contractor/bonds` | Bond amounts, status, cancellation |
| `GET /api/contractor/insurance` | Insurance coverage, expiry dates, amounts |
| `GET /api/contractor/license-history` | Past licenses, suspensions, reinstatements |
| `GET /api/contractor/violations` | Open/closed violations, severity |
| `GET /api/contractor/correspondence` | Stale/unverified correspondence records |
| `GET /api/contractor/inspections` | Inspection results, doc gaps, safety rechecks |
| `POST /api/sql` | Cross-entity queries (requires X-Task-Token header) |

## Liquor Restricted-License Staff Package

| Endpoint | Key data |
|---|---|
| `GET /api/policies` | Current policy baseline for liquor licensing |
| `GET /api/liquor/applications` | Application details, location, license class |
| `GET /api/liquor/settlements` | Prior settlement history, same-premises basis |
| `GET /api/liquor/privileges` | Existing privileges, covered risks |
| `GET /api/liquor/incidents` | Incidents at or near the location |
| `GET /api/liquor/site-evidence` | Floor plans, signage, photos, camera evidence |
| `POST /api/sql` | Cross-entity queries (requires X-Task-Token header) |

## Alcohol Renewal Manual-Review Queue

| Endpoint | Key data |
|---|---|
| `GET /api/alcohol/licensees` | Licensee identities, addresses, facility names |
| `GET /api/alcohol/violations` | Violations with dates and severity |
| `GET /api/renewal/rules` | Renewal disqualification rules, flagging criteria |
| `POST /api/sql` | Join queries for violation-to-licensee matching (requires X-Task-Token header) |

## Cross-Archetype Notes

- `GET /api/policies` is shared by contractor and liquor archetypes but NOT used in alcohol renewal.
- `POST /api/sql` is available in all three archetypes; always requires the `X-Task-Token` header from `environment_access.md`.
- Never call endpoints not listed in the task prompt or `environment_access.md`.
