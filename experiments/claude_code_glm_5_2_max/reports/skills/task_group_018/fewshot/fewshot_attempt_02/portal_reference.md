# Court Operations Portal Reference

## Connection

- **Base URL**: Read from `environment_access.md` in the repository root. The base URL, credentials, and allowed endpoints are listed there.
- **Authentication**: None required (portal API is open within the network).
- **Protocol**: HTTP GET only. Do not attempt POST, PUT, DELETE, or any write operations.

## Endpoints

| Endpoint | Purpose | Typical query parameters |
|---|---|---|
| `GET /api/jurisdictions` | List or look up jurisdiction codes and names | `?code=...` |
| `GET /api/cases` | Case records: defendant, status, court, disposition | `?case_number=...`, `?jurisdiction_code=...` |
| `GET /api/charges` | Charge details: offense code, statute, plea, disposition | `?case_number=...` |
| `GET /api/docket-entries` | Docket/chronological entries for a case | `?case_number=...` |
| `GET /api/citations` | Traffic citation records | `?citation_number=...` |
| `GET /api/fee-schedules` | Current fee amounts by jurisdiction, year, and fee code | `?jurisdiction_code=...`, `?year=...`, `?fee_code=...` |
| `GET /api/payment-policies` | Payment plan rules, policy IDs, bands, return-to-court offsets | `?policy_id=...`, `?jurisdiction_code=...` |
| `GET /api/forms` | Form IDs, labels, revision dates, field definitions | `?form_id=...`, `?jurisdiction_code=...` |
| `GET /api/financial-petitions` | Petition records: balances, classification, budget data | `?petition_id=...`, `?case_number=...` |
| `GET /api/search` | General search across multiple record types | `?q=...`, `?type=...` |

## Usage Guidelines

1. **Always query the portal** for each target case/citation — do not rely solely on local payloads.
2. **Use fee-schedules endpoint** to resolve any amount flagged as stale, archived, or from a prior year.
3. **Use payment-policies endpoint** to get policy bands (minimum/maximum monthly), return-to-court offsets, and agreement-type rules.
4. **Use forms endpoint** to confirm form IDs, labels, and required fields before filling form-entry sections.
5. **Use financial-petitions endpoint** to cross-check petition balances and classifications reported locally.
6. **Use search endpoint** as a fallback when a specific endpoint doesn't return the needed record.
7. **Do not attempt** to read server-side files, access undocumented endpoints, or modify any data.

## Rate and Error Handling

- The portal is internal and generally responsive; no special rate limiting is needed.
- If a query returns no results, verify the case_number, citation_number, or jurisdiction_code and retry.
- If the portal is unreachable, note the failure in the answer and use `"verify_before_entry"` for any fields that required portal confirmation.
