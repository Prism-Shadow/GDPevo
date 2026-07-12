# Northstar Care Intake Portal

Compact standard-library Python environment for the healthcare intake transfer task group.

## Run

```sh
./setup.sh
```

The app binds to `${TASK_ENV_HOST:-0.0.0.0}` and uses `${TASK_ENV_PORT:-8073}`.
Configure the externally reachable URL separately as `TASK_ENV_BASE_URL` in the
evaluation workspace.

Login:

- Email: `intake.admin@northstar.example`
- Password: `Northstar-Intake-2026!`

## Files

- `generate_data.py` creates deterministic data with seed `130726`.
- `data/generated_data.json` stores shared patients, benefits, pharmacies, transfers, referrals, charts, programs, queue items, documents, and policies.
- `manifest.json` records counts, app entry points, credentials, target IDs, and generation timestamp.
- `app.py` serves the browser portal using `http.server` with cookie-backed sessions.

Public pages are `/`, `/login`, and `/healthz`. All operational pages require login.
