# Payer Operations SQL Environment

This shared environment exposes a SQLite database through an authenticated HTTP query service. Solver-facing access is limited to:

- `GET /health`
- `GET /`
- `POST /query`

Fixed synthetic Basic authentication credentials are:

- Username: `payer_ops_solver`
- Password: `revcycle_sql_014`

The service accepts read-only SQLite statements through `/query` as JSON:

```json
{"sql": "SELECT COUNT(*) AS cases FROM authorization_requests", "params": []}
```

`generate_data.py` creates `payer_ops.db` and `data_manifest.json` with fixed seed `140014`. The manifest is for environment builders and reviewers only. It lists construction identifiers and table counts, but does not contain answer objects.

Start the environment:

```bash
./setup.sh
```

Optional environment variables:

- `PORT` or `TASK_ENV_PORT` sets the service port.
- `TASK_ENV_HOST` sets the bind interface and defaults to `0.0.0.0`.
- `TASK_ENV_REGENERATE=1` rebuilds the database before service startup.

Configure the externally reachable URL separately as `TASK_ENV_BASE_URL` in the
evaluation workspace.
