# task_group_005 Environment

Shared ERP finance JSON API for claims, AP, payments, vendors, compliance review, prepaid accounting, GL balances, and close logs.

## Start

```sh
sh setup.sh 8005
```

The port argument is optional and defaults to `8005`. `setup.sh` generates deterministic data if `manifest.json` or `data/claims.json` is missing, then starts the API server.

You can also run the scripts directly on Windows:

```sh
python generate_data.py
python server.py 8005
```

## Data

The generator uses fixed seed `5005` and writes JSON files under `data/` plus `manifest.json`.

## Endpoints

- `GET /health`
- `GET /api/health`
- `GET /endpoints`
- `GET /claims` and `GET /api/claims`
- `GET /api/claims/{claim_id}`
- `GET /bills` and `GET /api/ap/bills`
- `GET /payments` and `GET /api/ap/payments`
- `GET /api/ap/aging?as_of=YYYY-MM-DD`
- `GET /vendors` and `GET /api/vendors`
- `GET /compliance/objects` and `GET /api/compliance/objects`
- `GET /api/compliance/profile/{business_id}`
- `GET /api/compliance/ownership/{business_id}`
- `GET /api/compliance/registry/{business_id}`
- `GET /api/compliance/screening/{business_id}`
- `GET /api/compliance/bank/{business_id}`
- `GET /api/compliance/risk/{business_id}`
- `GET /prepaids/invoices` and `GET /api/prepaids/invoices`
- `GET /gl/balances` and `GET /api/prepaids/gl-balances`
- `GET /close/logs` and `GET /api/close/logs`

Object endpoints support exact-match query parameters for fields, plus `limit` and `offset`.

Examples:

```text
http://<TASK_ENV_BASE_URL>/bills?status=paid&limit=20
http://<TASK_ENV_BASE_URL>/gl/balances?account=1250&period=2025-04
http://<TASK_ENV_BASE_URL>/compliance/objects?review_status=escalated
```
