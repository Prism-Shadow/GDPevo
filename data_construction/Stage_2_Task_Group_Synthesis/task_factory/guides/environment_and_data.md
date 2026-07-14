# Environment And Data

## Environment Design

`env/` should be developed for the whole task group scenario, not assembled as one-off tools for individual tasks.

The environment represents shared public data and an office-work setting: business systems, public directories, CRM-like records, databases, files, dashboards, APIs, and web pages that multiple tasks can use. It should feel like one coherent workplace, not ten separate task folders behind an API.

It may include:

- Web applications or pages.
- HTTP/API services.
- SQLite-backed data stores exposed through an authenticated network query service. Do not use PostgreSQL or another server database.
- Business-system data, generator scripts, initialization scripts, and configuration files.
- Query, filtering, status-check, or operational interfaces that are relevant to the task but do not directly return the answer.

The environment should reflect real production-system complexity: enough objects, states, history, noisy data, similar interfaces, and irrelevant but plausible distractors. Do not create an endpoint that directly returns the answer.

Do not partition the solver-facing environment by task. Avoid per-task data packages, per-task databases, or endpoints such as `/api/tasks/<task_id>/data` that hand the solver a task-specific bundle. The generator may keep hidden construction metadata for builders, but solver-facing services should expose shared business objects and normal workplace interfaces, such as `/events`, `/crm/accounts`, `/campaign-members`, `/exhibitors`, `/finance/invoices`, SQL tables, or shared files.

`env/` itself is not solver-visible input. Solver, base, and fewshot agents should access the environment only through exposed entry points, such as a browser URL, API base URL, or authenticated SQLite query-service URL and credentials. If a task requires relational data access, keep the SQLite database file on the orchestration host and expose the required read or write SQL capability through the running environment service. The service may accept SQL over HTTP or provide an equivalent shared query interface, but it must not become a task-answer endpoint. Do not let solver agents inspect or mount `env/` files, SQLite database files, schema or migration scripts, generated data files, database dumps, seeds, manifests, or setup scripts directly.

In solver-visible task inputs, refer to the running environment base URL only as
`<TASK_ENV_BASE_URL>`. Keep real localhost addresses, private IPs, public host
names, ports, and setup commands out of `prompt.txt` and `input/payloads/`; those
values belong in the evaluation workspace `.env` file for the actual run.

## Execution Architecture

The environment is a host-side network service outside every skill-generation
or solver container. Start it from `env/setup.sh` on the orchestration host with
`TASK_ENV_BIND=0.0.0.0` and a configured `TASK_ENV_PORT`. Filesystem isolation
remains strict: never stage or mount `env/`, its database files, seeds,
manifests, source code, or setup scripts into an agent container.

Use this one network pattern for calibration and evaluation:

```text
host environment: TASK_ENV_BIND=0.0.0.0, TASK_ENV_PORT=<port>
agent URL:        http://host.docker.internal:<port>
docker option:    --add-host=host.docker.internal:host-gateway
```

Pass the `--add-host` option on every agent `docker run`, including Docker
Desktop. This keeps the launch shape identical across development machines and
Linux servers. Do not replace it with a task-specific host IP or an env-container
alias.

`localhost` or `127.0.0.1` inside an agent container refers to that agent
container, not to an API running on the host or in another container. Do not use
it unless an explicitly verified host-network configuration makes that mapping
true.

Before any scored calibration or evaluation run, perform a health check from a
disposable container with
`--add-host=host.docker.internal:host-gateway`, using the exact URL that will be
staged in `environment_access.md`. Record the port, resolved
`TASK_ENV_BASE_URL`, and successful container-side health check under
`scratch/`. If the check fails, fix host binding or forwarding before launching
agents; do not work around it by mounting environment files.

Keep bind address, listen port, and agent-facing base URL configurable. Do not
hard-code a particular host IP, domain, or port into task data. Do not tell the
solver to start the service; the main orchestrator starts and resets it, while
the solver receives only the running entry point and any required test
credentials.

Stateful environments must also provide an operator-controlled, deterministic
reset or reseed procedure so attempts do not inherit writes from earlier runs.
The reset surface must not reveal answers and must not be exposed as a normal
solver-facing business endpoint.

## Train-Only Judge API

Every task-group environment must expose `POST /api/judge` to judge candidate answers for train tasks. The request body uses `{"task_id": "train_001", "answer": {...}}`. The endpoint must run the matching train evaluator and return only a normalized `score` in `[0, 1]`, a boolean `correct`, and a notice that the endpoint is train-only. It must reject every `test_*` task id and must not return the gold answer, rubric details, evaluator output, or other hidden material.

Keep the reusable judge implementation in `env/judge_api.py`, connect it to the task group's existing HTTP service, and declare it under `env.files` in `task_group.yaml`. The endpoint must be reachable through the same container-visible base URL as the business service. The judge endpoint is an evaluation control surface, not a business-data endpoint; do not expose task-specific source data through it.

## Env-Builder Ownership

The main agent owns the environment blueprint, task-group coherence, and final integration. The actual environment implementation should be done by a clean-context env-builder coding subagent based on that blueprint.

The blueprint should be written before implementation and stored at:

```text
scratch/env_blueprint.md
```

It should specify business systems, public entry points, data contracts, required tables or APIs, the SQLite schema and query-service contract when applicable, authentication requirements, random seeds, generated-data expectations, setup behavior, manifest requirements, `TASK_ENV_BIND`/`TASK_ENV_PORT`, the fixed host-gateway route, health checks, and state-reset behavior.

The env-builder coding subagent should implement:

- `env/setup.sh` can prepare or start the required environment.
- Services honor `TASK_ENV_BIND=0.0.0.0` and `TASK_ENV_PORT`, and are reachable
  from an agent container at `http://host.docker.internal:<port>` when the fixed
  `--add-host=host.docker.internal:host-gateway` option is present.
- Bind addresses are not reused blindly as agent-facing URLs;
  `TASK_ENV_BASE_URL` is supplied by the orchestrator after networking is set up.
- Web/API services and SQLite-backed data serve the whole task group. Any SQLite query service supports the read and write operations required by the tasks while keeping the `.db` file host-side.
- Shared data models and public interfaces are organized by business domain, not by task id.
- Train and test tasks use the same business infrastructure, creating transferable environment experience.
- The solver can access necessary capabilities through public entry points but cannot see standard answers, hidden notes, or the `env/` implementation files.
- Programmatic data-generation scripts, fixed seeds, generated data, and manifests are retained under `env/`.
- The existing HTTP service exposes the train-only `POST /api/judge` endpoint through `env/judge_api.py`.
- A health endpoint and deterministic operator reset/reseed path are documented
  for deployment and calibration without exposing hidden task truth.

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
