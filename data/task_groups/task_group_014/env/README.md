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

Dockerized evaluation should build this directory as the image context and run
the container on the per-run Docker network. The evaluation harness supplies
`TASK_ENV_BASE_URL` to agents as the container-to-container URL, for example
`http://task-env:9014`. The solver container should not mount this `env/`
directory or the SQLite database.

Optional environment variables:

- `PORT` or `TASK_ENV_PORT` sets the service port.
- `TASK_ENV_BIND` sets the bind interface and defaults to `0.0.0.0`.
- `TASK_ENV_REGENERATE=1` rebuilds the database before service startup.
- `TASK_ENV_ENABLE_JUDGE=1` enables the train-only `POST /api/judge` endpoint.

`POST /api/judge` is disabled by default and should only be enabled for
train-only judge-feedback runs. Solver-facing SQL access remains limited to the
authenticated read-only `/query` endpoint.
