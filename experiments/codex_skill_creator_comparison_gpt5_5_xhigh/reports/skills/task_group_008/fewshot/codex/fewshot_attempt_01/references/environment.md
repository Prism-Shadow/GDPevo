# Advisory API Environment

Use the harness-provided `API_BASE` when present. The staged fallback base URL is `http://task-env:9008/`.

Allowed endpoints:

- `GET /api/clients`
- `GET /api/clients/{client_id}`
- `GET /api/source-documents`
- `GET /api/retirement-accounts`
- `GET /api/life-insurance`
- `GET /api/trust-candidates`
- `GET /api/policies/tax`
- `GET /api/rmd-factors`
- `GET /portal/client/{client_id}` for a human-readable summary only

Fetch fresh records from the API. Do not invent values from the prompt alone.
