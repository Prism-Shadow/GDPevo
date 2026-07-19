# Calibration Runtime And Fixed Prompts

Difficulty calibration does not use the orchestration system's subagent
mechanism. Every fewshot skill-generation, base, and fewshot run is a separate
noninteractive Codex process inside Docker.

All formal calibration processes use the Codex harness with model `gpt-5.5`
and reasoning effort `xhigh`. This is a fixed benchmark protocol, independent
of the model running the construction workspace. Never infer the calibration
model from the main agent, current session, client default, or available model
alias. If this exact configuration is unavailable, stop and report calibration
as blocked rather than substituting another model or reasoning effort.

## Isolation Contract

For every run, create a fresh staged work directory and a dedicated temporary
Codex home. Mount only those two directories:

```text
scratch/calibration_runs/<run_kind>/<run_id>/work/       -> /work
scratch/calibration_runs/<run_kind>/<run_id>/codex_home/ -> /codex_home
```

The mounted `codex_home/` is disposable runtime state, not a calibration
artifact. The only Codex-home file retained after the run is the matched primary
session JSONL described below.

Do not mount the repository, full task group, parent workspace, user home,
`env/`, notes, evaluators, standard answers not explicitly allowed for that run,
other attempts, or review artifacts.

Build the environment image from `env/Dockerfile` and attach it and every
calibration agent to an orchestrator-created Docker bridge network. The
environment binds `0.0.0.0` at `TASK_ENV_PORT`, where the port is `9000 + the
numeric task-group id`, and has the network alias `task-env`. Do not publish the
port to the host. Stage `http://task-env:<TASK_ENV_PORT>/` in
`environment_access.md`, together with every business endpoint allowed for the
run, copied from `env/endpoints.txt` as `METHOD /path` lines without
descriptions. Do not include `/health`, reset/reseed endpoints, or `/api/judge`
in base/fewshot calibration inputs, and launch calibration environments with
`TASK_ENV_ENABLE_JUDGE=0`. Do not stage or mount environment source files.
Create the bridge without `--internal` so the agent retains outbound model-API
access through Docker's default NAT and DNS.

The orchestrator owns all runtime names. Include the normalized
`GDPEVO_RUN_OWNER` or invoking username, task-group number, `cal`, run kind,
task/attempt when applicable, and an eight-character random suffix. For
example, `gdp-<user_name>-013-cal-base-t001-a01-7f3a91c2-net`. The environment
container receives the same scope with `-env`; the agent receives `-agent`.
Use `task-env` only as a network alias, never as a fixed global container name.

Read `env.state_mode` from `task_group.yaml`. A `read_only` environment may be
shared by concurrent calibration agents on one calibration-stage network. A
`mutable` environment gets a separate network and fresh environment container
for every calibration attempt. The orchestrator may run as many uniquely named
attempts concurrently as the host can support.

## Codex Command

After the orchestrator has created the network and healthy environment
container, use this fixed calibration launch shape:

```bash
docker run --rm \
  --name "$AGENT_CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  --env PROMPT \
  --mount type=bind,src="$WORK_DIR",dst=/work \
  --mount type=bind,src="$CODEX_HOME_DIR",dst=/codex_home \
  "$AGENT_IMAGE" \
  sh -lc 'CODEX_HOME=/codex_home codex exec -C /work -m gpt-5.5 -c '\''model_reasoning_effort="xhigh"'\'' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"'
```

`CODEX_HOME` is a temporary runtime variable for that process. Do not use
`--ephemeral`. After the process exits, locate the primary session file under:

```text
<CODEX_HOME_DIR>/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

Require exactly one session file for the isolated process and verify that it
contains the expected run id and staged `/work` path. Copy that one file to:

```text
scratch/calibration_runs/<run_kind>/<run_id>/trace/rollout-*.jsonl
```

Use the copied JSONL to populate and verify token, cost, turn, tool-call,
contamination, and calibration-record fields. Only after those fields are
complete may the entire temporary `codex_home/` be deleted. Do not retain or copy the full
`CODEX_HOME`; in particular, do not archive its config, credentials, logs,
skills, plugins, caches, databases, or other runtime state. Stdout/stderr and
`codex exec --json` output are not substitutes for the primary session JSONL
and are not required trace artifacts.

Record and verify `model: gpt-5.5` and `reasoning_effort: xhigh`, together with
the image, owner, network and container names, state mode, run id, staged files,
copied trace path, cleanup result, and exit status in the calibration record. If
the session file is missing or ambiguous, record the reason rather than copying
an arbitrary file, remove the temporary home, and rerun with a new run id.

## Prompt Contract

Pass exactly one template below as the final prompt to `codex exec`. Replace
only angle-bracket placeholders. Do not append task hints, answer summaries,
rubric details, evaluator descriptions, notes, construction truth, or paths
outside `/work`.

### Base Test Attempt

Stage only the target test `input/` and `environment_access.md`.

```text
calibration_run_id: <unique_run_id>
run_type: base_test

Solve exactly one test task using only files staged in the current /work directory. Read input/prompt.txt and every file under input/payloads/. Use only the base URL, credentials, and allowed METHOD /path entries listed in environment_access.md to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
```

### Fewshot Skill Generation

Stage all five train `input/` directories, the five matching standard answers
under `train_answers/<task_id>/answer.json`, and `environment_access.md`. Do not
stage test material, notes, evaluators, judge instructions, or another skill
attempt. Run this prompt in 3 isolated processes to produce 3 independent skill
packages.

```text
calibration_run_id: <unique_run_id>
run_type: skill_generation
condition: fewshot

Generate one reusable skill package using only files staged in the current /work directory. Read all five train inputs from train_tasks/train_001/input/ through train_tasks/train_005/input/, including every payload, and the five matching standard answers from train_answers/train_001/answer.json through train_answers/train_005/answer.json. Use only the base URL, credentials, and allowed METHOD /path entries listed in environment_access.md to reach the running environment over the network. If any unexpected material is present in /work, stop and write contamination_report.txt. Otherwise create skill/ and write the reusable entry instructions to skill/SKILL.md without copying task-specific answer values. Keep any supporting files inside skill/.
```

After each process finishes, preserve the complete contents of `/work/skill/`
as the matching package root:

```text
scratch/train_skill/fewshot_attempt_01/SKILL.md
scratch/train_skill/fewshot_attempt_02/SKILL.md
scratch/train_skill/fewshot_attempt_03/SKILL.md
```

### Fewshot Test Attempt

Stage only the target test `input/`, the complete generated skill directory as
`skill/`, and `environment_access.md`.

```text
calibration_run_id: <unique_run_id>
run_type: fewshot_test

Solve exactly one test task using only files staged in the current /work directory. Read skill/SKILL.md and any files it references inside skill/, then read input/prompt.txt and every file under input/payloads/. Use only the base URL, credentials, and allowed METHOD /path entries listed in environment_access.md to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
```

## Run Validation

A run is valid only when:

- it ran through the Codex harness with `gpt-5.5` and `xhigh` reasoning effort;
- its work directory was fresh and contained only the materials allowed above;
- the environment health check succeeded from a disposable container on the
  same Docker network through `http://task-env:<TASK_ENV_PORT>/`;
- the process produced the expected `answer.json` or complete skill package;
- the matched primary Codex session JSONL is copied into the run's `trace/`
  directory, or a concrete missing reason is recorded;
- all token, cost, turn, tool-call and calibration-record fields derived from
  the trace have been populated and verified;
- the temporary `codex_home/` has been deleted only after that verification;
- the trace shows no access to forbidden material; and
- scoring was performed outside the agent process by the main agent.

Contaminated or incomplete runs do not count toward `avg@3`. Keep them for
audit, create a new run id and directory, and rerun from a clean stage.
