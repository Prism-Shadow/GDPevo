# Codex Orchestrator Guide

Codex is the main evaluator and the tested harness for both skill generation
and test solving. The orchestrator may stage allowed files, run Docker
environments, launch isolated Codex processes, call evaluators, preserve traces,
and aggregate reports. It must not solve train or test tasks itself.

Every generation and solver attempt runs as a separate Codex process in Docker
with a clean container-local `CODEX_HOME`.

## Orchestrator Source Boundary

Resolve the current workspace root once and keep all orchestration source,
staging, metadata, and reports beneath it. The main orchestrator may use only:

- Files inside the current workspace.
- The exact auth file named by `GDPEVO_CODEX_AUTH_JSON`, read-only.
- The explicitly configured machine runtime values, without printing secrets.
- Docker metadata and operations for the configured agent image, the task image
  built from this workspace, and containers/networks created for this run.
- Installed command-line tools only for their executable behavior, version, and
  help output.

The orchestrator must not search, list, read, copy, import, or summarize:

- Parent, sibling, or historical evaluation workspaces.
- Previous runner, orchestrator, helper, report, trace, skill, or attempt files.
- Host `$HOME/.codex` content other than the exact configured auth file,
  including sessions, history, logs, databases, config, plugins, skills, and
  caches.
- Docker images, containers, networks, or logs belonging to another task or
  experiment.

Unrestricted host filesystem access is not permission to use historical
material. Do not run broad searches under `/home`, a parent `test/` directory,
or the Docker image catalog to find implementation examples.

Any temporary helper must be authored under `scratch/` from the current
workspace guides and standard tool documentation only. Do not copy or adapt an
external runner. A source-boundary violation is an orchestration infrastructure
failure, not a creator result: preserve a concise incident record, stop the
profile, clean run-owned resources, and restart with a new main-orchestrator
session.

## Resolve One Profile

Accept only `model_profile`. Require exactly one task-group directory and load
all four creators from `configs/experiment.yaml`.

Before formal attempts, verify:

- An uncommitted `.env` exists in the current workspace and every required
  machine input is resolved without placeholders.
- Generator and solver resolve to the same model profile.
- Required provider, authentication, and reasoning values are present.
- Each creator manifest is pinned and matches its complete upstream bundle.
- The task group has the expected 5-train/5-test structure.
- `GDPEVO_AGENT_IMAGE` resolves locally to the approved immutable agent image,
  contains the required Codex executable, and uses the same resolved image ID
  throughout the profile.
- A disposable inspection of that image confirms `/work` is empty and no
  authentication file, Codex runtime home or session, task material, generated
  skill, or previous run output is baked into it.
- The exact `GDPEVO_CODEX_AUTH_JSON` bootstrap passes container-local
  `codex login status`.
- The task image is reachable and healthy from the agent network.

These are runtime setup checks, not a separate model run. The first model
invocation is the formal `codex/attempt_01` generation slot.

Write one sanitized record:

```text
scratch/run_manifest/<model_profile>.yaml
```

Record the resolved model/provider/reasoning values, task-group ID, Codex
version, configured agent-image reference and resolved image ID, task image ID,
resolved agent UID:GID, creator revisions and bundle hashes, prompt template IDs
and hashes, common-contract hash, attempt counts, fixed execution order,
runtime-setup results, and sanitized proxy/endpoint information. Do not record
secrets or the host auth path.

Use only this run manifest for the resolved profile.

Temporary helper scripts may be written under `scratch/` from these guides. They
do not need to be committed before execution, but their hash must be recorded in
the run manifest and they must not be copied from another workspace. Freeze
their bytes before the first formal slot. A later helper change is an
infrastructure change and requires preserving the incident evidence and
restarting the profile from a clean main-orchestrator session.

## Docker Isolation

Mount only the current staged attempt directory as `/work`. Never mount the
full task group, evaluation workspace, repository, host home, host
`CODEX_HOME`, notes, evaluators, source test answers, previous runs, or another
creator bundle.

Read `GDPEVO_AGENT_IMAGE` directly from the current workspace's `.env`. Inspect
only that reference and resolve it to one immutable local image ID. If it is
missing locally, contains a placeholder, or is not approved as task-agnostic,
block the run. Do not list images to find an alternative, pull a replacement,
reuse an image because its name resembles another experiment, or change the
image during the profile.

Resolve the execution user once:

```bash
AGENT_UID_GID="$(id -u):$(id -g)"
```

Use that same value with `docker create --user` for every creator and solver
attempt under the selected profile. Record it in the run manifest. This keeps
host-mounted outputs user-owned and equal across creators.

Create writable internal runtime homes as the resolved agent user:

```text
HOME=/tmp/gdpevo-agent-home
CODEX_HOME=/tmp/gdpevo-codex-home
```

If authentication is required, mount only the exact
`GDPEVO_CODEX_AUTH_JSON` file read-only at a dedicated bootstrap path, copy it
with mode `0600` into the container-local home, and run `codex login status`.
Do not derive a host `CODEX_HOME`, scan for credentials, or copy the host config,
sessions, database, logs, plugins, skills, caches, or history.

For custom providers, create only the minimum container-local configuration
from the selected profile. Pass keys through the declared environment variable.
Provider and proxy settings are runtime setup; apply them identically to every
agent in the profile and record only sanitized values.

If `GDPEVO_DOCKER_PROXY_URL` is non-empty, pass that exact value as uppercase
and lowercase `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` to every agent
container. Set uppercase and lowercase `NO_PROXY` uniformly for `task-env`,
`localhost`, `127.0.0.1`, and `::1`. Do not silently inherit, translate, or
substitute a different proxy protocol or address.

Use the selected profile for both generator and solver:

```bash
install -d -m 700 /tmp/gdpevo-agent-home /tmp/gdpevo-codex-home
HOME=/tmp/gdpevo-agent-home \
CODEX_HOME=/tmp/gdpevo-codex-home \
codex exec \
  -C /work \
  -m "<resolved_model_id>" \
  -c 'model_provider="<resolved_provider_id>"' \
  -c 'model_reasoning_effort="<resolved_effort>"' \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$PROMPT"
```

Apply the configured wall timeout outside `codex exec`. Do not use
`--ephemeral`; the primary session trace must remain available in the stopped
container.

## Task Environment

Build from:

```text
task_group/<task_group_id>/env/Dockerfile
```

Use a normal Docker bridge network with a unique owner/task/stage suffix. Start
the environment with alias `task-env`, no published host port, and:

```text
TASK_ENV_BIND=0.0.0.0
TASK_ENV_PORT=9000 + numeric task-group id
TASK_ENV_ENABLE_JUDGE=0
```

Agent containers use `http://task-env:<TASK_ENV_PORT>/`. Keep normal provider
egress and DNS. Verify `/health` from a disposable container on the same network
before the stage starts. Do not expose health, reset, reseed, or judge endpoints
inside agent-visible `environment_access.md`.

Follow `env.state_mode`: a read-only environment may be shared within one stage;
a mutable environment needs a fresh instance per attempt.

## Generation Staging

For each creator and attempt, stage:

```text
scratch/skill_generation/<model_profile>/<creator>/attempt_<nn>/
```

Its `/work` view contains only:

```text
creator/                 # the selected pinned upstream bundle
creator_contract.md      # unchanged common contract
train_tasks/             # train_001 through train_005 inputs
train_answers/           # matching standard answer.json files
environment_access.md
```

Do not stage test material, notes, evaluators, environment source, previous
runs, or another creator.

Use the fixed generation prompt. The process writes `skill/SKILL.md` and any
supporting files under `skill/`. After it exits:

1. Preserve the matching primary trace and usage metadata.
2. Check for contamination and symbolic links.
3. Validate `SKILL.md` and referenced local files without editing them.
4. Calculate package content and executable-bit digests.
5. For a valid package, copy the complete package without modification to:

   ```text
   skills/<model_profile>/fewshot/<creator>/fewshot_attempt_<nn>/
   ```

An invalid or missing package is a logical creator result. Preserve its metadata
and do not repair or retry it for quality.

## Solver Staging

Base:

```text
runs/<model_profile>/base/<test_id>/attempt_<nn>/
```

Stage only the current test `input/` and `environment_access.md`.

Few-shot:

```text
runs/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/
```

Stage only the current test `input/`, `environment_access.md`, and the complete
matching generated package as read-only `skill/`.

Solver `attempt_<nn>` must use that creator's `fewshot_attempt_<nn>`. Verify the
package digest before staging. Do not expose train material, creator bundles,
other skills, answers, notes, evaluators, environment source, reports, traces,
or judge instructions.

After the solver exits, preserve its primary trace and metadata, check
contamination, call the official evaluator from orchestrator context, and write:

```text
answer.json
score.yaml
run_metadata.yaml
```

## Fixed Prompts

Use exactly one template from `guides/agent_prompts.md` and replace only declared
placeholders. Do not append creator-specific hints, answers, notes, rubric
details, or external paths.

Each process receives a fresh opaque UUID. Keep descriptive creator, task, and
attempt labels only in orchestrator metadata. Within one model profile, the
rendered generation prompt must be identical across creators apart from the
fresh UUID; the model-profile value is the same, and the staged creator bundle
is the only creator-specific input.

Follow the rendering and canonical hashing contract in
`guides/agent_prompts.md`. Record `prompt_template_id`,
`prompt_template_sha256`, and `rendered_prompt_sha256` in every generation and
solver attempt's metadata. Use the template hash, not the rendered hash, when
checking prompt equality across creators.

## Trace Preservation

Preserve exactly one matching `rollout-*.jsonl` for every selected generation
and solver attempt. Match it by opaque run ID and `/work` path.

Canonical destinations:

```text
original_traces/<model_profile>/skill_generation/<creator>/attempt_<nn>/
original_traces/<model_profile>/base/<test_id>/attempt_<nn>/
original_traces/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/
```

When trace discovery requires copying the container `sessions/` tree, avoid
root-owned host files by streaming the archive through an unprivileged host
`tar`:

```bash
mkdir -p "$TRACE_EXTRACT_DIR"
sudo -n docker cp \
  "$AGENT_CONTAINER:/tmp/gdpevo-codex-home/sessions/." - \
  | tar -x -C "$TRACE_EXTRACT_DIR"
```

Here `sudo` applies only to `docker cp`; `tar` runs as the workspace owner.
Delete the temporary extraction directory after selecting the trace. Do not use
`sudo find`, retain a full runtime home, or preserve credentials, caches,
databases, or stdout as the formal trace.

Populate token, cost, turn, tool-call, and observed-model fields from the copied
primary trace. Remove the stopped agent container only after output, trace, and
metadata are complete.

Never inspect host `$HOME/.codex/sessions` or any previous experiment trace to
learn or infer the trace schema. Trace discovery and parsing must use only the
current named attempt container and the current workspace guides.

## Failures And Cleanup

For a verified infrastructure failure, preserve the failed attempt under:

```text
scratch/infrastructure_failures/<model_profile>/<logical_slot>/<agent_run_id>/
```

Then recreate the formal slot from clean inputs and retry it with a new UUID.
Keep the same creator, prompt, model, evidence, limits, and logical attempt
number.

Agent timeout, invalid skill, invalid answer, refusal, or agent-originated
boundary violation is a logical result and is not retried merely to get success.
A staging leak caused by the orchestrator is infrastructure and may be retried
after fixing only that leak.

After every attempt, remove its agent container and attempt-scoped network and
environment when applicable. Leave no credentials or temporary runtime home on
the host.
