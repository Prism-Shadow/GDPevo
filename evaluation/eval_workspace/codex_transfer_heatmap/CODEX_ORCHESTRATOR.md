# Codex Orchestrator Guide

Codex is the main transfer-evaluation orchestrator. It may inspect the staged
task groups to stage allowed files, call evaluators, preserve traces, aggregate
cell reports, and render heatmaps. It must not solve target test tasks directly.

Every solver attempt must run as a separate isolated Codex process inside
Docker. This workspace does not generate new skills.

## Docker Isolation

Mount only the current solver attempt directory into the container. If the agent
needs authentication, bind only the minimum credential/bootstrap file read-only,
for example at `/run/gdpevo-bootstrap/auth.json`; never mount the host `CODEX_HOME`,
the host home directory, or a complete runtime directory. Create the runtime home
inside the container at `/tmp/gdpevo-codex-home`. Do not mount the full
`task_groups/` tree, full evaluation workspace, repository root, parent work
directory, home directory, `env/`, notes, evaluator files, source answers, or
previous runs.

The container must have network access because Codex needs model API access and
the staged attempt needs the target environment. Start that environment on the
orchestration host with `TASK_ENV_BIND=0.0.0.0`; pass
`--add-host=host.docker.internal:host-gateway` to every solver container and use
`http://host.docker.internal:<TASK_ENV_PORT>/`. Never mount environment files.

## Codex Command

Use the model configuration in `heatmap_scope.json` unless the user explicitly
overrides it. The default is `GPT-5.5` with `xhigh` reasoning effort.

Resolve the active host credential source once, without using it as the runtime
home:

```bash
HOST_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
```

Create a named agent container without `--rm`. If authentication is needed, bind
only `$HOST_CODEX_HOME/auth.json` read-only at `/run/gdpevo-bootstrap/auth.json`
and initialize the container-local home before launching Codex:

```bash
export CODEX_HOME=/tmp/gdpevo-codex-home
install -d -m 700 "$CODEX_HOME"
install -m 600 /run/gdpevo-bootstrap/auth.json "$CODEX_HOME/auth.json"
CODEX_HOME="$CODEX_HOME" codex login status
```

Do not copy `config.toml` or any other Codex state. Never stage the credential in
`/work` or retain it as an experiment artifact. If the internal home cannot be
initialized or login is invalid, mark the run blocked before starting the solver.

Before launching the formal solver, use the same named container and
container-local home to run `codex login status`. Continue only when it confirms
an active login. A missing or invalid login blocks the run; do not replace the
tested solver with the orchestrator.

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
solver process. Do not write it into `.env`, task materials, generated skills,
or reports as a task environment setting.

Do not add `--ephemeral`; formal attempts must leave trace files.

Pass exactly the fixed test-solver prompt from `guides/agent_prompts.md` and
replace only its declared placeholders. Do not append task hints, answer
summaries, evaluator details, or extra filesystem paths.

## Trace Preservation

Preserve only the raw Codex primary session JSONL. The runtime home remains inside
the named container and is never a host bind mount. Start the container without
`--rm`; after the solver exits, keep the stopped container until trace and metadata
verification is complete. Use `docker cp` to copy only the container's
`/tmp/gdpevo-codex-home/sessions/` subtree into a temporary
`scratch/trace_extract/<run_id>/` directory, or copy the exact known rollout file
directly. Select exactly one matching `sessions/.../rollout-*.jsonl` and copy only
that file to:

```text
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/rollout-*.jsonl
```

Verify the copied file contains the expected run id and `/work` path, then
populate and verify `run_metadata.yaml` and any trace-derived token fields. Delete
the temporary extraction directory, then remove the stopped container only after
the answer, score, copied trace (or its missing reason), and metadata are written.
Do not preserve the complete container-local home, its config, credentials,
plugins, skills, caches, logs, databases or other runtime state. Do not require
stdout/stderr command logs as formal trace artifacts, do not treat stdout JSONL
as a replacement for the raw `rollout-*.jsonl` session trace, and do not search
the user's global `~/.codex` after the run. If the session file is missing or
ambiguous, record the reason and rerun with a new run id.
