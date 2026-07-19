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

Preserve exactly one complete native Claude Code session JSONL as the primary
trace. Create the mounted Claude config directory under
`scratch/runtime_homes/`, outside `original_traces/`, and pass a unique
`--session-id`. After the process exits, find the exact file named by that
session ID under the temporary config directory:

```text
<temporary_claude_config>/projects/<sanitized-cwd>/<claude_session_id>.jsonl
```

Verify its session ID and working directory, then copy only that JSONL to:

```text
original_traces/skill_generation/<condition>/attempt_<nn>/<claude_session_id>.jsonl
original_traces/<condition>/<task_id>/attempt_<nn>/<claude_session_id>.jsonl
```

For each skill-generation run, also write the matching token and cost record:

```text
scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml
```

Use the copied primary JSONL to populate and verify token, cost, turn, and
tool-call data. Only after the trace and metadata are complete, delete the full
temporary `CLAUDE_CONFIG_DIR`. Do not archive its config, credentials, plugins,
caches, logs, databases, or other runtime state. Do not require stdout/stderr
command logs as formal trace artifacts, do not use `--no-session-persistence`,
and do not rely on searching the user's global `~/.claude` after the run. If the
session file is missing or ambiguous, record the reason, clean up the temporary
directory, and rerun with a new session ID.

A Docker run is not complete until `answer.json` or the complete `skill/` package
with `skill/SKILL.md` as its entry file, the primary
session trace or its missing reason, and the corresponding run/evolve metadata
have been preserved.
