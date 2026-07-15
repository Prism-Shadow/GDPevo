# Codex Orchestrator Guide

Codex is the main evaluation orchestrator. The orchestrator may inspect the full
task group to stage allowed files, start and check the task environment, call
evaluators, preserve traces, and aggregate reports. It must not solve test tasks
directly.

Every skill-generation run and every solver attempt must be executed as a
separate isolated agent process inside Docker. The tested agent for this workspace
is Codex.

## Docker Isolation

Mount only the current staged directory and a dedicated per-attempt Codex home
into the container. Do not mount the full task group, full evaluation workspace,
repository root, parent work directory, home directory, `env/`, `notes/`,
evaluator files, source answers, or previous runs.

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

The command shape inside Docker is:

```bash
CODEX_HOME=/codex_home \
codex exec \
  -C /work \
  -m gpt-5.5 \
  -c 'model_reasoning_effort="xhigh"' \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$PROMPT"
```

`CODEX_HOME=/codex_home` is a runtime-only environment variable for this single
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

Preserve the complete raw Codex session file as the primary trace. Create a
dedicated mounted Codex home for every skill-generation run and solver attempt,
set `CODEX_HOME=/codex_home` only when launching that agent process, and keep
the resulting `rollout-*.jsonl` file in place.

For skill-generation runs, use:

```text
original_traces/skill_generation/<condition>/attempt_<nn>/codex_home/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

For test solver attempts, use:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/codex_home/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

Do not require stdout/stderr command logs as formal trace artifacts, do not treat
stdout JSONL as a replacement for the raw `rollout-*.jsonl` session trace, and
do not rely on searching the user's global `~/.codex` after the run.

A Docker run is not complete until `answer.json` or the complete `skill/` package
with `skill/SKILL.md` as its entry file, the complete
primary session trace or its missing reason, and the corresponding metadata
record have been preserved.
