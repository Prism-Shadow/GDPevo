# Codex Orchestrator Guide

Codex is the main evaluation orchestrator. The orchestrator may inspect the full
task group to stage allowed files, check the remote environment, call
evaluators, preserve traces, and aggregate reports. It must not solve test tasks
directly.

Every skill-generation run and every solver attempt must be executed as a
separate isolated agent process inside Docker. The tested agent for this workspace
is Claude Code.

## Docker Isolation

Mount only the current staged directory and a dedicated per-attempt Claude
config directory into the container. Do not mount the full task group, full
evaluation workspace, repository root, parent work directory, home directory,
`env/`, `notes/`, evaluator files, source answers, or previous runs.

The container must have network access because Claude Code needs model API
access and the staged attempt may need `GDPEVO_ENV_BASE_URL`. Do not run a
network-disabled container unless an equivalent working proxy is configured.

## Claude Code Command

Use the configured Claude Code model for the run. The released Claude Code
workspace uses Claude Opus 4.8 with `xhigh` effort.

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

Set the model and effort through the Claude Code environment or configuration
used for the run, and record the observed values under `scratch/` before
launching scored attempts. Do not add `--no-session-persistence`; formal
attempts must leave trace files.

If `claude` is not on `PATH`, locate it before running the experiment and record
the resolved executable path under `scratch/`. Do not hard-code a host-specific
path in reusable instructions.

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

A Docker run is not complete until `answer.json` or `SKILL.md`, the primary
session trace or its missing reason, and the corresponding run/evolve metadata
have been preserved.
