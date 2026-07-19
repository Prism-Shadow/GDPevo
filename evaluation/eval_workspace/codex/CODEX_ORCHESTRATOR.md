# Codex Orchestrator Guide

Codex is the main evaluation orchestrator. The orchestrator may inspect the full
task group to stage allowed files, start and check the task environment, call
evaluators, preserve traces, and aggregate reports. It must not solve test tasks
directly.

Every skill-generation run and every solver attempt must be executed as a
separate isolated agent process inside Docker. The tested agent for this workspace
is Codex.

## Docker Isolation

Mount only the current staged directory into the agent container. If authentication
is needed, mount only the minimum bootstrap credential read-only at a dedicated path
such as `/run/gdpevo-bootstrap/auth.json`; do not mount a host `CODEX_HOME`, the host
home directory, or any complete runtime directory. The agent's `CODEX_HOME` is created
inside the container, for example `/tmp/gdpevo-codex-home`. Do not mount the full task
group, full evaluation workspace, repository root, parent work directory, `env/`,
`notes/`, evaluator files, source answers, or previous runs.

Build the task environment from `env/Dockerfile` and run it with each agent on
an orchestrator-created Docker bridge network. The environment binds
`0.0.0.0:<TASK_ENV_PORT>`, uses the network alias `task-env`, and publishes no
host port. Agents use `http://task-env:<TASK_ENV_PORT>/` and retain normal model
API egress. Create a normal user-defined bridge, not an `--internal` network, so
Docker's default outbound NAT and DNS remain available. Never stage or mount
`env/` into an agent container.
If `env/Dockerfile` or `env.state_mode` is missing, stop and report an
incompatible legacy task group; do not fall back to a host-side environment.

The orchestrator, not the tested agent, creates all names. Each name contains a
normalized `<user_name>`, task-group number, capability stage,
condition/task/attempt when applicable, and an eight-character random suffix;
for example `gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-net`. Use the same
scope with `-env` and `-agent` for containers. `task-env` is only a network
alias, never a fixed global container name.

Read `env.state_mode` from `task_group.yaml`. A `read_only` instance may serve
concurrent attempts in the same capability stage; a `mutable` environment gets
a fresh network, container, and writable layer per attempt. Run as much
parallelism as the host supports. Keep judge-enabled reflect skill generation
separate from judge-disabled calibration, other skill generation, and formal
test stages. Test instances use `TASK_ENV_ENABLE_JUDGE=0`. Before scored runs,
verify `/health` from a disposable container on the same network through the
exact agent URL.

## Codex Command

Use the configured model for the run. The released Codex workspace uses
`gpt-5.5` with `xhigh` reasoning effort.

Resolve the active host credential source once, without using it as the runtime home:

```bash
HOST_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
```

For every skill-generation run and solver attempt, create a named agent container
without `--rm`. If authentication is needed, bind only the host credential file
read-only and copy it into the container-local runtime home before launching Codex:

```bash
test -f "$HOST_CODEX_HOME/auth.json" || {
  echo "Evaluation blocked: active Codex auth.json was not found" >&2
  exit 1
}
docker create --name "$CONTAINER_NAME" \
  ... \
  -v "$HOST_CODEX_HOME/auth.json:/run/gdpevo-bootstrap/auth.json:ro" \
  ...
```

The container-side wrapper must initialize and use an internal home, for example:

```bash
export CODEX_HOME=/tmp/gdpevo-codex-home
install -d -m 700 "$CODEX_HOME"
install -m 600 /run/gdpevo-bootstrap/auth.json "$CODEX_HOME/auth.json"
CODEX_HOME="$CODEX_HOME" codex login status
```

Do not copy or mount the full active Codex home, `config.toml`, sessions, databases,
logs, skills, plugins, caches, or other state. Model and reasoning settings come from
the explicit launch arguments. Never stage `auth.json` in `/work` or retain it as an
experiment artifact. If the container-local home cannot be initialized or login is
invalid, mark the run blocked before starting the formal attempt.

Run the login check inside the same container-local setup before the formal command.
Do not launch an unauthenticated attempt or replace it with the orchestrator.

The command shape inside Docker is:

```bash
CODEX_HOME=/tmp/gdpevo-codex-home \
codex exec \
  -C /work \
  -m gpt-5.5 \
  -c 'model_reasoning_effort="xhigh"' \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$PROMPT"
```

`CODEX_HOME=/tmp/gdpevo-codex-home` is a runtime-only environment variable for this single
agent process. Do not write it into `.env`, task materials, generated skills, or
reports as a task environment setting.

If the outer Docker mount already provides hard isolation, `--dangerously-bypass-approvals-and-sandbox` is the intended noninteractive equivalent of an open agent permission mode. Do not add `--ephemeral`; formal attempts must leave
trace files.

If `codex` is not on `PATH`, locate it before running the experiment and record
the resolved executable path under `scratch/`. Do not hard-code a host-specific
path in reusable instructions.

## Fixed Prompt Contract

Use exactly one mode-specific template from `guides/agent_prompts.md` as
`$PROMPT`. Replace only its declared placeholders. Do not append hints, answer
summaries, notes, rubric/evaluator details, or additional paths. The staged
`/work` contents and Docker mounts enforce the information boundary; the prompt
must describe the run, not smuggle extra context into it.

## Trace Preservation

Preserve only the raw Codex primary session JSONL. The runtime home remains inside
the named container and is never a host bind mount. Start the container without
`--rm`; after the agent exits, keep the stopped container until trace and metadata
verification is complete. Use `docker cp` to extract only the container's
`/tmp/gdpevo-codex-home/sessions/` subtree into a temporary
`scratch/trace_extract/<run_id>/` directory, or copy the exact known rollout file
directly. Select exactly one `rollout-*.jsonl` matching the run id and `/work` path,
then copy only that file into the canonical trace directory. Delete the temporary
extraction directory after selection.

For skill-generation runs, use:

```text
original_traces/skill_generation/<condition>/attempt_<nn>/rollout-*.jsonl
```

For test solver attempts, use:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/rollout-*.jsonl
```

Use the copied JSONL to populate and verify token, cost, turn, tool-call,
contamination, and metadata fields. Only after those fields are complete may the
container be removed. Never copy or retain the complete container-local
`CODEX_HOME`; this excludes config, credentials, logs, skills, plugins, caches,
databases and other runtime state. Do not require stdout/stderr command logs as
formal trace artifacts, do not treat stdout JSONL as a replacement for the raw
`rollout-*.jsonl` session trace, and do not search the user's global `~/.codex`
after the run. If the session file is missing or ambiguous, record the reason
instead of choosing an arbitrary file, clean up the temporary extraction, remove
the stopped container, and rerun with a new run id.

Remove the named agent container only after the answer or skill package, the copied
primary trace (or its missing reason), all trace-derived metadata, and the report
inputs have been written to the host workspace.

A Docker run is not complete until `answer.json` or the complete `skill/` package
with `skill/SKILL.md` as its entry file, the primary session trace or its missing
reason, all trace-derived data and metadata, and confirmation that the temporary
Codex home was removed only after verification have been preserved.
