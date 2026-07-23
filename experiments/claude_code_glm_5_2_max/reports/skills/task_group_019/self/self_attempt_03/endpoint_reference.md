# Endpoint Reference

## Authentication
- POST `/api/sql` requires header `X-Task-Token: licensing-review-019`
- All GET endpoints require no authentication header

## Contractor Endpoints
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/contractor/applications` | Application records (id, specialty, experience, status) |
| GET | `/api/contractor/bonds` | Bond records (amount, status, cancellation) |
| GET | `/api/contractor/insurance` | Insurance records (coverage, expiry, amount) |
| GET | `/api/contractor/license-history` | Prior licenses and suspensions |
| GET | `/api/contractor/violations` | Violations with severity classification |
| GET | `/api/contractor/correspondence` | Letters, notices, responses |
| GET | `/api/contractor/inspections` | Inspection outcomes, doc gaps, safety rechecks |

## Liquor Endpoints
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/liquor/applications` | Liquor license applications |
| GET | `/api/liquor/settlements` | Prior settlements and agreements |
| GET | `/api/liquor/privileges` | Existing privileges, same-premises info |
| GET | `/api/liquor/incidents` | Incident reports at/near premises |
| GET | `/api/liquor/site-evidence` | Photos, floor plans, signage, camera evidence |

## Alcohol Endpoints
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/alcohol/licensees` | Licensee details, facility names, addresses |
| GET | `/api/alcohol/violations` | Violation records with dates |
| GET | `/api/renewal/rules` | Renewal review threshold rules |

## Shared Endpoints
| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/policies` | Current policy baseline with effective dates |
| POST | `/api/sql` | Ad-hoc SQL query execution (SELECT only) |

## SQL Endpoint Usage
- URL: `<TASK_ENV_BASE_URL>/api/sql`
- Method: POST
- Header: `X-Task-Token: licensing-review-019`
- Body: SQL query string
- Use only for read queries (SELECT)
- Useful for: joining violations to licensees, filtering by date ranges, cross-referencing across endpoints
