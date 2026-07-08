# Codex Orchestrator Guide for Kimi 2.6 Claude Code Evaluation

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
<work_root>/task_group_XXX/evaluation/eval_workspace/claude_code_kimi2_6
```

Read `README.md` and `guides/` first. Use `.env` for the remote task
environment. Do not start the local `task_group/env` service.

Before running any Claude Code command, confirm the active Claude Code
configuration is Kimi 2.6 with Claude Code `xhigh` effort, Kimi model-side
thinking `enabled`, and bypass permissions:

```text
ANTHROPIC_BASE_URL=https://api.siliconflow.cn/
ANTHROPIC_MODEL=Pro/moonshotai/Kimi-K2.6
ANTHROPIC_CUSTOM_MODEL_OPTION=Pro/moonshotai/Kimi-K2.6
CLAUDE_CODE_EFFORT_LEVEL=xhigh
permissions.defaultMode=bypassPermissions
```

Record this check in the evaluation workspace under `scratch/`. Keep the two
levels separate in notes and reports: `xhigh` describes Claude Code's outer
effort setting, while Kimi thinking is recorded as `enabled`.

## Core Rule

Codex may inspect the full task group to stage files, score attempts, audit
outputs, and aggregate the report. Claude Code may only see a dedicated staged
directory created for the current skill-generation run or solver attempt.

Never launch Claude Code from:

```text
evaluation/eval_workspace/claude_code_kimi2_6
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
- the matching skill for non-base modes

The solver prompt must tell Claude Code to read/write only inside that attempt
directory and write the final answer as `answer.json`.

## Running Claude Code

For this Kimi 2.6 rerun, Claude Code must run with Docker isolation unless the
user explicitly approves a fallback later. Do not start any scored or
skill-generation Claude run with direct host `claude -p` fallback.

On this server, direct `docker` access may fail because the user is not in the
`docker` group. Use `sudo docker` for Docker commands. `sudo docker ps` is
expected to work without an interactive password prompt. If `sudo docker` is not
usable, stop before launching Claude Code, record the blocker in `scratch/`, and
report it to the user.

The container must have network access because Claude Code needs the
SiliconFlow API and tasks may need `GDPEVO_ENV_BASE_URL`. Do not use a
network-disabled container unless an equivalent working proxy is explicitly
configured.

Mount only the current staged working directory and the trace/output
directories into the container. Do not mount the full task group, full
evaluation workspace, parent `work/` directory, repository root, or home
directory. This file isolation is the main protection against `notes/`, `eval/`,
`env/`, source answers, and previous runs leaking into Claude Code.

Launch Claude Code with bypass permissions, for example:

```text
claude -p --permission-mode bypassPermissions ...
```

or an equivalent configuration. Do not use `--no-session-persistence`; it can
prevent Claude Code session traces from being written.

If the `claude` executable is not on `PATH`, locate it before running the
experiment. Do not hard-code a host-specific path in reusable scripts; record
the resolved executable path in `scratch/`.

Do not use direct host execution as an automatic fallback. If a Dockerized
Claude command cannot be constructed, stop and report the blocker instead of
running `claude -p` on the host.

## Scoring, Traces, Tokens, Report

Codex, not Claude, calls the evaluator and writes:

```text
runs/<condition>/<test_id>/attempt_<nn>/score.yaml
runs/<condition>/<test_id>/attempt_<nn>/run_metadata.yaml
```

Every scored solver attempt must have the raw Claude Code work trace for that
specific Claude skill-generation or solver run copied under:

```text
original_traces/<condition>/<test_id>/attempt_<nn>/
```

Populate token usage, round count, and tool-call count in `run_metadata.yaml`
and the final report from the matched trace. Deduplicate token usage by
`message.id` before summing. If a trace cannot be matched, record the issue
explicitly and do not invent efficiency numbers.

For `claude -p`, save stdout as a machine-readable trace when possible, such as
`--output-format stream-json --verbose`, under the matching `original_traces/`
directory. This stdout stream is auxiliary. The primary trace for token usage,
rounds, and tool-call counting is the Claude Code session JSONL from the active
`.claude` directory. This means the Claude run itself, or the Codex orchestrator
immediately after that run, must find the matching
`.claude/projects/.../*.jsonl` or equivalent session file for the current staged
directory/session and copy it into `original_traces/`.

If running inside Docker, the relevant `.claude` directory may be inside the
container rather than the host. Mount a host trace directory as the container's
Claude home/session-trace location when possible. Otherwise, before the
container is stopped or removed, explicitly copy the matching container
`.claude` session trace files to the host workspace. A Docker run is not
complete until this Claude work trace has been preserved.

Before deleting or replacing any Docker container, verify that all required
artifacts have been written to the host workspace:

- `answer.json` or `SKILL.md`
- Claude Code session trace, when available
- optional stdout stream/json trace, when captured
- debug logs, when used
- score and metadata files after Codex scoring

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
