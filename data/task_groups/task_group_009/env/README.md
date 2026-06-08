# Crescent Finance Ops Environment

This shared environment supports the Finance Operational Modeling and Management Reporting task group. It exposes branch finance records, compensation rate books and rosters, and theatre payroll data through a domain-oriented HTTP API.

Start it with:

```bash
PORT=8047 bash env/setup.sh
```

or:

```bash
bash env/setup.sh 8047
```

Public API endpoints:

- `GET /health`
- `GET /api/manifest`
- `GET /api/finance/branches`
- `GET /api/finance/period-map`
- `GET /api/finance/accounts`
- `GET /api/finance/records`
- `GET /api/compensation/rate-book`
- `GET /api/compensation/rosters`
- `GET /api/compensation/scenarios`
- `GET /api/payroll/rate-book`
- `GET /api/payroll/productions`

Optional filters:

- `/api/finance/records?branch_id=BR-004`
- `/api/finance/records?region=REG-WEST`
- `/api/finance/records?account=product_revenue`
- `/api/compensation/rosters?ensemble_id=ENS-REDWOOD`
- `/api/payroll/productions?production_id=PROD-HAMILTON-26`

The API does not expose task answers, rubrics, or task-specific bundles.
