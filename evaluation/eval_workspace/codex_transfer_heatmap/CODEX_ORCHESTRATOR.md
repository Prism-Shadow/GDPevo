# Codex Orchestrator Guide

Codex is the main transfer-evaluation orchestrator. It may inspect the staged
task groups to stage allowed files, call evaluators, preserve traces, aggregate
cell reports, and render heatmaps. It must not solve target test tasks directly.

Every solver attempt must run as a separate isolated Codex process inside
Docker. This workspace does not generate new skills.

## Docker Isolation

Mount only the current solver attempt directory and a dedicated temporary
per-attempt Codex home into the container. Do not mount the full `task_groups/` tree, full
evaluation workspace, repository root, parent work directory, home directory,
`env/`, notes, evaluator files, source answers, or previous runs.

The container must have network access because Codex needs model API access and
the staged attempt needs the target environment. Start that environment on the
orchestration host with `TASK_ENV_BIND=0.0.0.0`; pass
`--add-host=host.docker.internal:host-gateway` to every solver container and use
`http://host.docker.internal:<TASK_ENV_PORT>/`. Never mount environment files.

## Codex Command

Use the model configuration in `heatmap_scope.json` unless the user explicitly
overrides it. The default is `GPT-5.5` with `xhigh` reasoning effort.

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
solver process. Do not write it into `.env`, task materials, generated skills,
or reports as a task environment setting.

Do not add `--ephemeral`; formal attempts must leave trace files.

Pass exactly the fixed test-solver prompt from `guides/agent_prompts.md` and
replace only its declared placeholders. Do not append task hints, answer
summaries, evaluator details, or extra filesystem paths.

## Trace Preservation

Preserve only the raw Codex primary session JSONL. Create the temporary mounted
Codex home under `scratch/runtime_homes/`, set `CODEX_HOME=/codex_home` only
when launching the solver process, and after it exits copy the unique matching
`sessions/.../rollout-*.jsonl` to:

```text
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/rollout-*.jsonl
```

Verify the copied file contains the expected run id and `/work` path, then
populate and verify `run_metadata.yaml` and any trace-derived token fields. Only
after that verification may the complete temporary Codex home be deleted. Do not archive its config, credentials,
plugins, skills, caches, logs, databases or other runtime state. Do not require
stdout/stderr command logs as formal trace artifacts, do not treat stdout JSONL
as a replacement for the raw `rollout-*.jsonl` session trace, and do not rely on
searching the user's global `~/.codex` after the run.
