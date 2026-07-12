# Codex Orchestrator Guide

Codex is the main evaluation orchestrator. The orchestrator may inspect the full
task group to stage allowed files, check the remote environment, call
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

The container must have network access because Codex needs model API access and
the staged attempt may need `GDPEVO_ENV_BASE_URL`. Do not run a network-disabled
container unless an equivalent working proxy is configured.

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

A Docker run is not complete until `answer.json` or `SKILL.md`, the complete
primary session trace or its missing reason, and the corresponding metadata
record have been preserved.
