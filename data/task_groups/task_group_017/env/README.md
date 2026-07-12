# task_group_017 Environment

Shared legal investigation JSON API for white-collar defense production-review tasks.

Start:

```bash
PORT=8057 ./setup.sh
```

The service binds to `${TASK_ENV_HOST:-0.0.0.0}` on `${PORT}`. Configure the
externally reachable URL separately as `TASK_ENV_BASE_URL` in the evaluation
workspace. It exposes:

- `/health`
- `/api/matters`
- `/api/matters/{matter_id}`
- `/api/subpoena_categories?matter_id=...`
- `/api/production_logs?matter_id=...`
- `/api/collection_events?matter_id=...`
- `/api/retention_rules?matter_id=...`
- `/api/destruction_events?matter_id=...`
- `/api/privilege_logs?matter_id=...`
- `/api/qc_events?matter_id=...`
- `/api/custodians?matter_id=...`
- `/api/documents?matter_id=...`
- `/api/search?matter_id=...&q=...`

Data is generated deterministically with seed `17017`.
