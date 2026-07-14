# Codex Orchestrator Guide for Claude Code GLM 5.2

Codex is the main evaluation orchestrator. The orchestrator may inspect the full
task group to stage allowed files, start and check the environment, call
evaluators, preserve traces, and aggregate reports. It must not solve test tasks
directly.

Every skill-generation run and every solver attempt must be executed as a
separate isolated agent process inside Docker. The tested agent for this workspace
is Claude Code configured to use GLM-5.2. Claude Code runs with `xhigh` effort,
while the GLM model setting reported for this workspace is `max`.

## Docker Isolation

Mount only the current staged directory and a dedicated per-attempt Claude
config directory into the container. Do not mount the full task group, full
evaluation workspace, repository root, parent work directory, home directory,
`env/`, `notes/`, evaluator files, source answers, or previous runs.

Run the environment on the orchestration host with `TASK_ENV_BIND=0.0.0.0`.
Every agent `docker run` must include
`--add-host=host.docker.internal:host-gateway` and use
`http://host.docker.internal:<TASK_ENV_PORT>/`. The agent container must also
have model API access. Before scored runs, verify the environment health
endpoint from a disposable container through this exact route. Never stage or
mount `env/` into the agent container.

## Claude Code Command

Use the GLM-5.2 Claude Code configuration for the run. Record the observed model
and effort under `scratch/` before launching scored attempts.

The command shape inside Docker is:

```bash
CLAUDE_CONFIG_DIR=/claude_config \
claude -p \
  --permission-mode bypassPermissions \
  --session-id "$CLAUDE_SESSION_ID" \
  "$PROMPT"
```

`CLAUDE_CONFIG_DIR=/claude_config` is a runtime-only environment variable for
this single agent process. Do not write it into `.env`, task materials,
generated skills, or reports as a task environment setting.

Do not add `--no-session-persistence`; formal attempts must leave trace files.
If `claude` is not on `PATH`, locate it before running the experiment and record
the resolved executable path under `scratch/`. Do not hard-code a host-specific
path in reusable instructions.

## Fixed Prompt Contract

Use exactly one mode-specific template from `guides/agent_prompts.md` as
`$PROMPT`. Replace only its declared placeholders. Do not append hints, answer
summaries, notes, rubric/evaluator details, or additional paths. The staged
`/work` contents and Docker mounts enforce the information boundary; the prompt
must describe the run, not smuggle extra context into it.

## Trace Preservation

Preserve the complete raw Claude Code session file as the primary trace. Create
the mounted Claude config directory under the matching trace directory, set
`CLAUDE_CONFIG_DIR=/claude_config` only when launching the agent process, pass a
unique `--session-id`, and preserve the resulting file from:

```text
original_traces/skill_generation/<condition>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
original_traces/<condition>/<task_id>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
```

For each skill-generation run, also write the matching token and cost record:

```text
scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml
```

Do not require stdout/stderr command logs as formal trace artifacts, do not use
`--no-session-persistence`, and do not rely on searching the user's global
`~/.claude` after the run.

A Docker run is not complete until `answer.json` or the complete `skill/` package
with `skill/SKILL.md` as its entry file, the primary
session trace or its missing reason, and the corresponding run/evolve metadata
have been preserved.
