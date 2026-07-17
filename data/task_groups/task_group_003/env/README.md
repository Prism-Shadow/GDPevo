# task_group_003 Shared Support Console Environment

Start the environment:

```bash
TASK_ENV_PORT=9003 ./setup.sh
```

The API listens on `http://${TASK_ENV_BIND:-0.0.0.0}:${TASK_ENV_PORT:-9003}` and exposes shared CRM support records: accounts, service tickets, outages, diagnostics, troubleshooting, mobile lines, devices, bills, contact-center cases, enterprise accounts, export incidents, export runs, messages, and SLA contracts.

Useful endpoints include:

- `/health`
- `/api/catalog`
- `/api/tickets` and `/api/tickets/<ticket_id>`
- `/api/outages?service_area=<area>`
- `/api/diagnostics/<ticket_id>`
- `/api/troubleshooting/<ticket_id>`
- `/api/cases` and `/api/cases/<case_id>`
- `/api/lines/<line_id>`
- `/api/devices/<device_id>`
- `/api/plans/<plan_id>`
- `/api/enterprise/incidents/<incident_id>`
- `/api/enterprise/export-runs?incident_id=<incident_id>`
- `/api/enterprise/messages?query=<text>`
- `/api/enterprise/sla/<enterprise_account_id>`

The environment is shared across all train and test tasks. It does not expose task-specific bundles or standard answers.
