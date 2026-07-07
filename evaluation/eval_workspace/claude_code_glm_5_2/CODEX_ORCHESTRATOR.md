# Codex Orchestrator Guide for Claude Code GLM 5.2

Codex is the main evaluation orchestrator. The orchestrator may inspect the full
task group to stage allowed files, check the remote environment, call
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

The container must have network access because Claude Code needs model API
access and the staged attempt may need `GDPEVO_ENV_BASE_URL`. Do not run a
network-disabled container unless an equivalent working proxy is configured.

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

## Trace Preservation

Preserve the raw Claude Code session file as the primary trace. Create the
mounted Claude config directory under the attempt trace directory, set
`CLAUDE_CONFIG_DIR=/claude_config` only when launching the agent process, pass a
unique `--session-id`, and preserve the resulting file from:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
```

Do not require stdout/stderr command logs as formal trace artifacts, do not use
`--no-session-persistence`, and do not rely on searching the user's global
`~/.claude` after the run.

A Docker run is not complete until `answer.json` or `SKILL.md` and the primary
session trace or its missing reason have been preserved.
