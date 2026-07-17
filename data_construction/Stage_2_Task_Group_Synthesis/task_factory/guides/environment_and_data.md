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

`env/` itself is not solver-visible input. Solver, base, and fewshot agents should access the environment only through exposed entry points, such as a browser URL, API base URL, or authenticated SQLite query-service URL and credentials. If a task requires relational data access, keep the SQLite database file inside the environment container and expose the required read or write SQL capability through the running environment service. The service may accept SQL over HTTP or provide an equivalent shared query interface, but it must not become a task-answer endpoint. Do not let solver agents inspect or mount `env/` files, SQLite database files, schema or migration scripts, generated data files, database dumps, seeds, manifests, or setup scripts directly.

Keep a complete plain-text endpoint list at `env/endpoints.txt`, with one
`METHOD /path` per line and no descriptions. During calibration or evaluation,
the main agent writes all endpoint names allowed for the current run into
`environment_access.md`, together with the runtime base URL and credentials if
needed. Business endpoints may be shown to skill-generation and test agents;
`/api/judge` is shown only during reflect skill generation; `/health` and
reset/reseed endpoints remain orchestration-only.

In solver-visible task inputs, refer to the running environment base URL only as
`<TASK_ENV_BASE_URL>`. Keep real localhost addresses, private IPs, public host
names, ports, and setup commands out of `prompt.txt` and `input/payloads/`; those
values are resolved by the runtime orchestrator from the Docker network and
written to `environment_access.md`.

## Execution Architecture

Build the environment from `env/Dockerfile` with `env/` as the complete build
context. Run it as a container on a user- and run-scoped Docker bridge network;
run every skill-generation, calibration, and solver agent in a separate
container attached to that network. Do not publish the environment port to the
host. The environment source, database, seeds, manifests, `.env` files, and
setup scripts exist only in the environment image or environment-only mounts.
Never stage, copy, or mount them into an agent container.

Create a normal user-defined bridge network, not an `--internal` network.
Docker's default outbound NAT and DNS must remain available so agent containers
can reach their model APIs. This outbound connectivity does not require, and
must not be implemented by, publishing the task-environment port to the host.

Use this fixed internal route:

```text
port rule:         9000 + numeric task-group id
environment bind: TASK_ENV_BIND=0.0.0.0, TASK_ENV_PORT=<computed integer>
network alias:     task-env
agent URL:         http://task-env:<computed integer>/
host publishing:   none
```

Docker's network DNS resolves `task-env` only inside the current network. The
same alias and internal port may therefore be reused safely by other users,
task groups, stages, and attempts on the same Docker daemon. `localhost` inside
an agent container still refers only to that agent container. Do not use
`host.docker.internal`, host networking, a public host address, or `-p`/`ports`
for formal runs.

The trusted orchestrator creates all names. Agents must not choose them. Define
an owner slug from `GDPEVO_RUN_OWNER` or the invoking username, normalized to
lowercase `[a-z0-9_-]`, and include it in every project, network, and container
name. Also include the task-group number, capability stage, condition/task and
attempt when applicable, plus an eight-character random run suffix. For
example:

```text
gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-net
gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-env
gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-agent
```

The real environment container name must be unique; `task-env` is only its
network-scoped alias. Do not set a global fixed `container_name: task-env`.

Before an agent starts, run the health check from a disposable container on the
same network and through the exact `http://task-env:<port>/` route that will be
written to `environment_access.md`. Record the owner, run suffix, state mode,
stage, network name, environment container name, internal port, base URL, image
identifier, and health result under `scratch/`. The environment container may
receive private configuration through environment-only variables, secrets, or
mounts; the agent receives only the base URL, allowed endpoint names, and any
task-visible credentials.

### Environment Lifetime

`task_group.yaml` must declare `env.state_mode` as `read_only` or `mutable`; the
runtime never guesses this value.

- `read_only`: one environment container may serve all concurrent attempts in
  the same capability stage. It must not expose any attempt-visible mutation
  through business endpoints, sessions, caches, auth state, logs, limits, or
  judge bookkeeping.
- `mutable`: every attempt gets a fresh network, environment container, and
  writable layer. Multiple attempts may run concurrently because their names
  and networks are unique. Do not share a database volume between attempts.

Capability stages remain separate even for `read_only` environments. Base,
fewshot, self, and test agents use an environment instance with the judge route
disabled. Reflect skill generation uses a separate instance with
`TASK_ENV_ENABLE_JUDGE=1`. A formal test environment uses
`TASK_ENV_ENABLE_JUDGE=0`, where `POST /api/judge` must be unregistered or
return not found. Calibration also uses a judge-disabled instance. Tear down a
network only after every agent intentionally sharing that stage has finished.

## Train-Only Judge API

Every task-group environment must expose `POST /api/judge` to judge candidate answers for train tasks. The request body uses `{"task_id": "train_001", "answer": {...}}`. The endpoint must run the matching train evaluator and return only a normalized `score` in `[0, 1]`, a boolean `correct`, and a notice that the endpoint is train-only. It must reject every `test_*` task id and must not return the gold answer, rubric details, evaluator output, or other hidden material.

Keep the reusable judge implementation in `env/judge_api.py`, connect it to the task group's existing HTTP service, and declare it under `env.files` in `task_group.yaml`. The endpoint must be reachable through the same container-visible base URL as the business service. The judge endpoint is an evaluation control surface, not a business-data endpoint; do not expose task-specific source data through it.

## Env-Builder Ownership

The main agent owns the environment blueprint, task-group coherence, and final integration. The actual environment implementation should be done by a clean-context env-builder coding subagent based on that blueprint.

The blueprint should be written before implementation and stored at:

```text
scratch/env_blueprint.md
```

It should specify business systems, public entry points, data contracts, required tables or APIs, the complete endpoint list, the SQLite schema and query-service contract when applicable, authentication requirements, random seeds, generated-data expectations, setup behavior, manifest requirements, `TASK_ENV_BIND`/`TASK_ENV_PORT`, `env.state_mode`, the environment image, network-only route, health checks, and state-reset behavior.

The env-builder coding subagent should implement:

- `env/Dockerfile` builds a self-contained environment image from `env/` only,
  and `env/setup.sh` prepares or starts the required environment inside it.
- Services honor `TASK_ENV_BIND=0.0.0.0` and `TASK_ENV_PORT`, and are reachable
  from an agent container at `http://task-env:<port>/` when both containers are
  attached to the orchestrator-created network.
- Bind addresses are not reused blindly as agent-facing URLs;
  `TASK_ENV_BASE_URL` is supplied by the orchestrator after networking is set up.
- Web/API services and SQLite-backed data serve the whole task group. Any SQLite
  query service supports the required operations while keeping the `.db` file
  inside the environment container and outside every agent mount.
- Shared data models and public interfaces are organized by business domain, not by task id.
- Train and test tasks use the same business infrastructure, creating transferable environment experience.
- The solver can access necessary capabilities through public entry points but cannot see standard answers, hidden notes, or the `env/` implementation files.
- Programmatic data-generation scripts, fixed seeds, generated data, and manifests are retained under `env/`.
- `env/endpoints.txt` lists every reachable endpoint as `METHOD /path` without descriptions.
- The existing HTTP service exposes the train-only `POST /api/judge` endpoint through `env/judge_api.py`.
- The service honors `TASK_ENV_ENABLE_JUDGE`: register `/api/judge` only when it
  equals `1`; judge-disabled calibration and test instances must not expose the
  route.
- `task_group.yaml` declares `env.state_mode` correctly; mutable environments
  initialize a clean deterministic state in each new container, while read-only
  environments remain invariant under concurrent requests.
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
