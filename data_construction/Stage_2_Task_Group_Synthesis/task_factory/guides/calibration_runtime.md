# Calibration Runtime And Fixed Prompts

Difficulty calibration does not use the orchestration system's subagent
mechanism. Every fewshot skill-generation, base, and fewshot run is a separate
noninteractive Codex process inside Docker.

## Isolation Contract

For every run, create a fresh staged work directory and a dedicated Codex home.
Mount only those two directories:

```text
scratch/calibration_runs/<run_kind>/<run_id>/work/       -> /work
scratch/calibration_runs/<run_kind>/<run_id>/codex_home/ -> /codex_home
```

Do not mount the repository, full task group, parent workspace, user home,
`env/`, notes, evaluators, standard answers not explicitly allowed for that run,
other attempts, or review artifacts.

The environment API runs on the orchestration host with
`TASK_ENV_BIND=0.0.0.0`. Every agent container uses the fixed
`--add-host=host.docker.internal:host-gateway` option and reaches it through
`http://host.docker.internal:<TASK_ENV_PORT>`. Stage that URL in
`environment_access.md`, together with every business endpoint allowed for the
run, copied from `env/endpoints.txt` as `METHOD /path` lines without
descriptions. Do not include `/health`, reset/reseed endpoints, or `/api/judge`
in base/fewshot calibration inputs. Do not stage or mount environment source
files.

## Codex Command

Use the configured calibration model and reasoning effort. The fixed host-side
launch shape is:

```bash
docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  --env PROMPT \
  --mount type=bind,src="$WORK_DIR",dst=/work \
  --mount type=bind,src="$CODEX_HOME_DIR",dst=/codex_home \
  "$AGENT_IMAGE" \
  sh -lc 'CODEX_HOME=/codex_home codex exec -C /work -m <calibration_model> -c '\''model_reasoning_effort="<reasoning_effort>"'\'' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"'
```

`CODEX_HOME` is a temporary runtime variable for that process. Do not use
`--ephemeral`: preserve the complete `rollout-*.jsonl` under the dedicated
`codex_home/` as the primary trace. Record the model, reasoning effort, image,
network configuration, run id, staged files, trace path, and exit status in the
calibration record.

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

Solve exactly one test task using only files staged in the current /work directory. Read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
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

Generate one reusable skill package using only files staged in the current /work directory. Read all five train inputs from train_tasks/train_001/input/ through train_tasks/train_005/input/, including every payload, and the five matching standard answers from train_answers/train_001/answer.json through train_answers/train_005/answer.json. Use environment_access.md only to reach the running environment over the network. If any unexpected material is present in /work, stop and write contamination_report.txt. Otherwise create skill/ and write the reusable entry instructions to skill/SKILL.md without copying task-specific answer values. Keep any supporting files inside skill/.
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

Solve exactly one test task using only files staged in the current /work directory. Read skill/SKILL.md and any files it references inside skill/, then read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
```

## Run Validation

A run is valid only when:

- its work directory was fresh and contained only the materials allowed above;
- the environment health check succeeded from the same container network;
- the process produced the expected `answer.json` or complete skill package;
- the complete Codex session trace is preserved, or a concrete missing reason is
  recorded;
- the trace shows no access to forbidden material; and
- scoring was performed outside the agent process by the main agent.

Contaminated or incomplete runs do not count toward `avg@3`. Keep them for
audit, create a new run id and directory, and rerun from a clean stage.
