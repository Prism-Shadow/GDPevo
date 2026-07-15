# Codex Orchestrator Guide for DeepSeek V4 Pro Claude Code Evaluation

You are the evaluation orchestrator for one task group. Claude Code is only a
Dockerized `claude -p` subprocess used to generate skills or solve a single
staged attempt.
Do not let Claude Code work from the full evaluation workspace or the full
task_group directory.

## Required Workspace

The per-task Codex orchestrator should start from the prepared per-task work
directory:

```text
<work_root>/task_group_XXX
```

The evaluation workspace inside that directory is:

```text
<work_root>/task_group_XXX/evaluation/eval_workspace/claude_code_deepseek_v4_pro
```

Read `README.md` and `guides/` first. Start the task environment outside the
agent container and use `.env` for its container-visible URL.

Before running any Claude Code command, confirm the active Claude Code
configuration is DeepSeek V4 Pro via the DeepSeek Anthropic API with Claude
Code `max` effort, DeepSeek V4 Pro for Haiku/subagent defaults, and bypass
permissions:

```text
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_MODEL=deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-v4-pro[1m]
ANTHROPIC_DEFAULT_HAIKU_MODEL=deepseek-v4-pro[1m]
CLAUDE_CODE_SUBAGENT_MODEL=deepseek-v4-pro[1m]
CLAUDE_CODE_EFFORT_LEVEL=max
permissions.defaultMode=bypassPermissions
```

Record this check in the evaluation workspace under `scratch/`. Record the observed DeepSeek model mapping, Claude Code `max` effort, and
permission mode in notes and reports.

## Core Rule

Codex may inspect the full task group to stage files, score attempts, audit
outputs, and aggregate the report. Claude Code may only see a dedicated staged
directory created for the current skill-generation run or solver attempt.

Never launch Claude Code from:

```text
evaluation/eval_workspace/claude_code_deepseek_v4_pro
task_group/task_group_XXX
```

Launch Claude Code only from a clean staged directory under `scratch/` or the
current attempt directory under `runs/`.

## Forbidden For Claude Code

Do not stage these files or directories for Claude Code:

- `notes/`
- `eval/`
- `env/`
- source `output/answer.json` during test solving
- test answers
- unrelated train or test tasks
- previous attempts, previous runs, report files, or trace files
- judge API instructions during test solving

If a Claude run accesses or reports seeing forbidden material, mark that attempt
invalid, keep the evidence in that attempt directory or `scratch/invalid_attempts/`,
and rerun the affected item in a new clean directory.

## Skill Generation Staging

Create dedicated directories such as:

```text
scratch/staged/skill_generation/fewshot/attempt_01/
scratch/staged/skill_generation/self/attempt_01/
scratch/staged/skill_generation/reflect-3/attempt_01/
```

Stage only:

- `fewshot`: train task `input/`, train `output/answer.json`, and
  `environment_access.md`.
- `self`: train task `input/` and `environment_access.md`.
- `reflect-3`: train task `input/`, `environment_access.md`, and train-only
  judge instructions.

Generated skills must be copied to:

```text
skills/<condition>/<condition>_attempt_<nn>/SKILL.md
```

Reflect skills must not tell test solvers to call the judge API.

## Solver Attempt Staging

For every condition, test task, and attempt, create:

```text
runs/<condition>/<test_id>/attempt_<nn>/
```

Stage only:

- the current test task `input/`
- `environment_access.md`
- the complete matching skill package directory as `skill/` for non-base modes

Use the test-solver template in `guides/agent_prompts.md`; the mounted staging
directory, rather than a path blacklist in the prompt, enforces file isolation.

## Running Claude Code

For this DeepSeek V4 Pro rerun, Claude Code must run with Docker isolation unless the
user explicitly approves a fallback later. Do not start any scored or
skill-generation Claude run with direct host `claude -p` fallback.

On this server, direct `docker` access may fail because the user is not in the
`docker` group. Use `sudo docker` for Docker commands. `sudo docker ps` is
expected to work without an interactive password prompt. If `sudo docker` is not
usable, stop before launching Claude Code, record the blocker in `scratch/`, and
report it to the user.

Build the task environment from `env/Dockerfile` and run it with each agent on
an orchestrator-created Docker bridge network. The environment binds
`0.0.0.0:<TASK_ENV_PORT>`, uses the network alias `task-env`, and publishes no
host port. Agents use `http://task-env:<TASK_ENV_PORT>/` and retain DeepSeek
Anthropic API egress. Create a normal user-defined bridge, not an `--internal`
network, so Docker's default outbound NAT and DNS remain available. Never stage
or mount `env/` into an agent container.
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

Mount only the current staged working directory and a dedicated per-run Claude
config directory into the container. Mount the latter at `/claude_config`; do
not mount the full task group, full
evaluation workspace, parent `work/` directory, repository root, or home
directory. This file isolation is the main protection against `notes/`, `eval/`,
`env/`, source answers, and previous runs leaking into Claude Code.

Generate a unique UUID for every skill-generation run and solver attempt, then
launch Claude Code with the exact session-persistence shape:

```bash
CLAUDE_CONFIG_DIR=/claude_config \
claude -p \
  --permission-mode bypassPermissions \
  --session-id "$CLAUDE_SESSION_ID" \
  "$PROMPT"
```

Do not use `--no-session-persistence`; it can prevent Claude Code session traces
from being written.

If the `claude` executable is not on `PATH`, locate it before running the
experiment. Do not hard-code a host-specific path in reusable scripts; record
the resolved executable path in `scratch/`.

## Fixed Prompt Contract

Use exactly one mode-specific template from `guides/agent_prompts.md` as
`$PROMPT`. Replace only its declared placeholders. Do not append hints, answer
summaries, notes, rubric/evaluator details, or additional paths. The staged
working directory and Docker mounts enforce the information boundary.

Do not use direct host execution as an automatic fallback. If a Dockerized
Claude command cannot be constructed, stop and report the blocker instead of
running `claude -p` on the host.

## Scoring, Traces, Tokens, Report

Codex, not Claude, calls the evaluator and writes:

```text
runs/<condition>/<test_id>/attempt_<nn>/score.yaml
runs/<condition>/<test_id>/attempt_<nn>/run_metadata.yaml
```

Every skill-generation run and scored solver attempt must have its own raw
Claude Code work trace copied under the matching path:

```text
original_traces/skill_generation/<condition>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
original_traces/<condition>/<test_id>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
```

Each skill-generation run must also write:

```text
scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml
```

Populate token usage, round count, and tool-call count in `run_metadata.yaml`
and the final report from the matched trace. Deduplicate token usage by
`message.id` before summing. If a trace cannot be matched, record the issue
explicitly and do not invent efficiency numbers.

For `claude -p`, the primary trace for token usage, rounds, and tool-call
counting is the JSONL written to the dedicated mounted
`CLAUDE_CONFIG_DIR`. Match the exact file by the run's unique session ID. A
Docker run is not complete until this session trace has been preserved.

Before deleting or replacing any Docker container, verify that all required
artifacts have been written to the host workspace:

- `answer.json` or the complete `skill/` package with `skill/SKILL.md` as its entry file
- Claude Code session trace, when available
- debug logs, when used
- score and run metadata files after Codex scoring, or evolve metadata for skill generation

Final report:

```text
report/task_group_XXX.yaml
```

It must include `acc@3`, population `std@3`, failures/invalid attempts, trace
coverage, token coverage, and main artifact paths for all four conditions:

```text
base
fewshot
self
reflect-3
```
