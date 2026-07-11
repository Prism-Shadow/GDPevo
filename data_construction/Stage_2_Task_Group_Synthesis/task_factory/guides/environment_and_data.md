# Environment And Data

## Environment Design

`env/` should be developed for the whole task group scenario, not assembled as one-off tools for individual tasks.

The environment represents shared public data and an office-work setting: business systems, public directories, CRM-like records, databases, files, dashboards, APIs, and web pages that multiple tasks can use. It should feel like one coherent workplace, not ten separate task folders behind an API.

It may include:

- Web applications or pages.
- Local API services.
- PostgreSQL or other databases exposed to the solver.
- Business-system data, generator scripts, initialization scripts, and configuration files.
- Query, filtering, status-check, or operational interfaces that are relevant to the task but do not directly return the answer.

The environment should reflect real production-system complexity: enough objects, states, history, noisy data, similar interfaces, and irrelevant but plausible distractors. Do not create an endpoint that directly returns the answer.

Do not partition the solver-facing environment by task. Avoid per-task data packages, per-task databases, or endpoints such as `/api/tasks/<task_id>/data` that hand the solver a task-specific bundle. The generator may keep hidden construction metadata for builders, but solver-facing services should expose shared business objects and normal workplace interfaces, such as `/events`, `/crm/accounts`, `/campaign-members`, `/exhibitors`, `/finance/invoices`, SQL tables, or shared files.

`env/` itself is not solver-visible input. Solver, direct-test, and post-skill agents should access the environment only through exposed entry points, such as a browser URL, API base URL, or database connection string. If a task uses PostgreSQL or another database, expose it as a running service with connection details; do not let solver agents inspect `env/` files, migration scripts, generated data files, database dumps, seeds, manifests, or setup scripts directly.

In solver-visible task inputs, refer to the running environment base URL only as
`<TASK_ENV_BASE_URL>`. Keep real localhost addresses, private IPs, public host
names, ports, and setup commands out of `prompt.txt` and `input/payloads/`; those
values belong in the evaluation workspace `.env` file for the actual run.

## Train-Only Judge API

Every task-group environment must expose `POST /api/judge` to judge candidate answers for train tasks. The request body uses `{"task_id": "train_001", "answer": {...}}`. The endpoint must run the matching train evaluator and return only a normalized `score` in `[0, 1]`, a boolean `correct`, and a notice that the endpoint is train-only. It must reject every `test_*` task id and must not return the gold answer, rubric details, evaluator output, or other hidden material.

Keep the reusable judge implementation in `env/judge_api.py`, connect it to the task group's existing HTTP service, and declare it under `env.files` in `task_group.yaml`. The judge endpoint is an evaluation control surface, not a business-data endpoint; do not expose task-specific source data through it.

## Env-Builder Ownership

The main agent owns the environment blueprint, task-group coherence, and final integration. The actual environment implementation should be done by a clean-context env-builder coding subagent based on that blueprint.

The blueprint should be written before implementation and stored at:

```text
scratch/env_blueprint.md
```

It should specify business systems, public entry points, data contracts, required tables or APIs, random seeds, generated-data expectations, setup behavior, and manifest requirements.

The env-builder coding subagent should implement:

- `env/setup.sh` can prepare or start the required environment.
- Web, API, database, and data files serve the whole task group.
- Shared data models and public interfaces are organized by business domain, not by task id.
- Train and test tasks use the same business infrastructure, creating transferable environment experience.
- The solver can access necessary capabilities through public entry points but cannot see standard answers, hidden notes, or the `env/` implementation files.
- Programmatic data-generation scripts, fixed seeds, generated data, and manifests are retained under `env/`.
- The existing HTTP service exposes the train-only `POST /api/judge` endpoint through `env/judge_api.py`.

Task-builder subagents may request additional interfaces, tables, or data through the main agent. They should not independently implement separate environments.

## Programmatic Data Generation

Large-scale data must be generated with programs and randomness. Do not handwrite production-scale data.

Requirements:

- Keep data-generation scripts under `env/`, such as `generate_data.py`.
- Use fixed random seeds for reproducibility.
- Provide an output list or manifest describing generated files, tables, or records.
- Place underlying business data, large tables, databases, graphs, system states, and API backend data under `env/`, accessible through environment interfaces.
- Generated data may include task-relevance metadata for construction and review, but solver-facing data should remain a shared office environment rather than per-task slices.
- Include realistic noise such as missing fields, duplicate records, stale exports, definition differences, similar entities, conflicting states, or irrelevant records.

Payloads may contain solver-visible small exports, emails, spreadsheets, logs, templates, or local materials. Do not place the complete underlying database, API source code, or large-scale business-system data directly in `input/payloads/`.

Data-generation scripts must not become full task-group builders. An `env/` script may generate shared business records, manifests, database initialization files, or service fixtures, but it must not also generate all task prompts, hidden notes, standard answers, evaluators, `task_group.yaml`, scratch design docs, or calibration skills. Keep environment generation separate from task construction.
