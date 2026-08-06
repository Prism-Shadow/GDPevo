# Runtime Access Discipline

The environment access file (e.g. `environment_access.md` staged alongside the
task) is the **only** source of truth for reaching the clinic runtime. Treat it
as a capability list: if an endpoint or credential is not listed there, you do
not have it.

## What to extract

1. **Base URL** — the host root (substituted for `<TASK_ENV_BASE_URL>` in task
   prompts). All paths below are relative to it.
2. **Allowed endpoints** — the exact `GET /api/*` paths you may call, including
   any `{id}` path parameters. Do not call endpoints not listed.
3. **Auth for writes/queries** — any header required for `POST /api/query`
   (commonly an `X-...-Token` header with a per-run value). GET endpoints are
   typically open.

## How to use it

- Build every URL as `{BASE_URL}` + the listed path. Never invent a host.
- For `POST /api/query`, send the required header on every request; omitting it
  yields `401`. The body is a read-only structured query (e.g.
  `{"sql": "..."}`); use it for SELECT-style lookups only.
- Do not derive URLs, tokens, or endpoint names from memory or from the train
  examples — they are per-run. Re-read the file each run.
- If the file is absent, or does not grant an endpoint the task requires, stop
  rather than guessing an endpoint or credential.

## Read-only rule

All actions are reads. Never send a request intended to create, update, delete,
or "place" an order. The task asks for decision *support*, not order entry —
even when the output describes a recommended medication order, you only emit the
recommendation as JSON; you do not POST it to the runtime.
