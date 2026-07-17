# HarborCRM Shared Environment

This directory contains the shared HarborCRM environment for `task_group_001`.
It provides deterministic CRM, event, finance, trade-show, and contact-import
data through a local JSON API.

## Start The API

```bash
cd /Users/aaad1eu/ljzhou/work_space/data_gen_001/task_factory/task_group/task_group_001/env
./setup.sh
```

The default port is `8067`. To choose another port:

```bash
TASK_ENV_PORT=9001 ./setup.sh
```

`setup.sh` generates `data/harborcrm_data.json` and `data/manifest.json` if
they are missing, then starts the local API.

## Regenerate Data

```bash
python3 generate_data.py
```

The generator uses fixed seed `41001`, so the generated data is deterministic.

## Public Entry Points

- `GET /health`
- `GET /api/events`
- `GET /api/events/{event_id}`
- `GET /api/events/{event_id}/orders`
- `GET /api/events/{event_id}/badges`
- `GET /api/events/{event_id}/sponsor_packages`
- `GET /api/finance/invoices?event_id=<event_id>`
- `GET /api/crm/accounts`
- `GET /api/crm/contacts`
- `GET /api/crm/opportunities`
- `GET /api/crm/campaign_members?event_id=<event_id>`
- `GET /api/tradeshows`
- `GET /api/tradeshows/{show_id}/exhibitors`
- `GET /api/tradeshows/{show_id}/meeting_interest`
- `GET /api/import_batches`
- `GET /api/import_batches/{batch_id}/raw_contacts`
- `GET /api/import_batches/{batch_id}/suppression`
- `GET /api/policies`

The API exposes shared domain records only. It does not provide task-specific
answer endpoints.
