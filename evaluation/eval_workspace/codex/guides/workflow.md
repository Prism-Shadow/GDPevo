# Evaluation Workflow

This file explains how the Codex main evaluation orchestrator should run one
complete Codex evaluation.

The evaluation uses one task environment reachable from the agent containers
and four conditions:

```text
base
fewshot
self
reflect-3
```

When a user asks you to run evaluation in this workspace, that request is
permission for Codex to orchestrate the experiment and launch Dockerized Codex
runs. Keep every skill-generation and solver run in a clean, dedicated staged
directory mounted as `/work` inside Docker.

Read `CODEX_ORCHESTRATOR.md` before launching isolated agent runs. The formal
Codex command shape is:

```bash
CODEX_HOME=/codex_home codex exec -C /work -m gpt-5.5 -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"
```

`CODEX_HOME` is a runtime-only temporary environment variable for that agent
process, not a task `.env` setting. Do not use `codex exec --ephemeral` for
formal attempts. Use the exact mode-specific prompt in `agent_prompts.md` for
every process; replace only declared placeholders and do not append task hints
or extra paths.

## 1. Prepare The Task Group

The task group under evaluation should be located at:

```text
task_group/<task_group_id>/
```

Confirm it contains 5 train tasks, 5 test tasks, `env/`, official inputs,
standard answers, and `eval/eval.sh` for each task. Do not modify it.

## 2. Start And Connect The Environment

Load `.env`:

```text
GDPEVO_ENV_BASE_URL=http://host.docker.internal:<TASK_ENV_PORT>/
GDPEVO_JUDGE_PATH=/api/judge
```

Start `task_group/env` on the orchestration host with
`TASK_ENV_BIND=0.0.0.0` and `TASK_ENV_PORT` set to `9000 + the numeric task-group id`. Set
`GDPEVO_ENV_BASE_URL=http://host.docker.internal:<TASK_ENV_PORT>/` and pass
`--add-host=host.docker.internal:host-gateway` to every agent `docker run`.
Never mount `task_group/env/` into an agent container. Confirm the health/index
endpoint from a disposable container through that exact route, using the same
image and network option as scored runs, and record the startup/reset commands,
port, URL, and health result in `scratch/environment.md`.

Skill-generation and solver runs must not enter, list, or read `env/`. They may
use only the container-visible environment entrypoint staged by the main agent.

Read endpoint names from `task_group/env/endpoints.txt`. Each staged
`environment_access.md` must include the base URL, required credentials, and
all endpoints allowed for that run as `METHOD /path` lines without endpoint
descriptions. Include business endpoints for skill generation and test solving;
add `/api/judge` only for reflect skill generation; never include `/health` or
reset/reseed endpoints in execution-agent inputs.

The judge endpoint is train-only and valid only during reflect skill generation
on train tasks. It must not be staged to test solvers or written into generated
skills as a test-time tool. Only reflect skill-generation runs should
receive its usage instructions:

```text
POST {GDPEVO_ENV_BASE_URL}{GDPEVO_JUDGE_PATH}
{"task_id": "train_001", "answer": <candidate answer JSON>}
```

## 3. Generate Skills

Generate 3 independent skills for each non-base condition:

```text
skills/fewshot/fewshot_attempt_01/SKILL.md
skills/fewshot/fewshot_attempt_02/SKILL.md
skills/fewshot/fewshot_attempt_03/SKILL.md
skills/self/self_attempt_01/SKILL.md
skills/self/self_attempt_02/SKILL.md
skills/self/self_attempt_03/SKILL.md
skills/reflect-3/reflect-3_attempt_01/SKILL.md
skills/reflect-3/reflect-3_attempt_02/SKILL.md
skills/reflect-3/reflect-3_attempt_03/SKILL.md
```

Use dedicated workspaces such as:

```text
scratch/skill_generation/fewshot_attempt_01/
scratch/skill_generation/self_attempt_01/
scratch/skill_generation/reflect-3_attempt_03/
```

Stage only the materials allowed by `skill_modes.md`.

- `fewshot`: train inputs, train gold answers, container-visible environment entrypoint.
- `self`: train inputs and container-visible environment entrypoint; no train answers and
  no judge feedback.
- `reflect-3`: train inputs, container-visible environment entrypoint, and judge API
  instructions; no train answers.

Give every skill-generation run a unique evolve attempt ID:

```text
<task_group_id>__skill_generation__<condition>__attempt_<nn>__<timestamp>
```

Create a dedicated mounted `CODEX_HOME` for that run under:

```text
original_traces/skill_generation/<condition>/attempt_<nn>/codex_home/
```

After the run, preserve the complete raw `rollout-*.jsonl` session trace and
write `evolve_metadata.yaml` in the matching staged directory under
`scratch/skill_generation/`. The metadata must contain the evolve attempt ID,
skill output path, trace path, token usage, pricing inputs, and calculated USD
cost. Token and cost values must come from the matched raw Codex trace.

Skill-generation token usage and cost are reported as evolve metrics. They are
not included in test solver efficiency metrics.

## 4. Run Test Solvers

Run every condition, every test task, and every attempt independently in a fresh
directory:

```text
runs/<condition>/test_001/attempt_01/
```

Conditions:

```text
base
fewshot
self
reflect-3
```

For each attempt directory, stage only:

- The current test task `input/`.
- `environment_access.md` with the container-visible URL, credentials when needed, and the allowed endpoint names.
- The complete matching skill package directory as `skill/` for non-base modes.

Do not stage `env/`, train tasks, source answer files, test answers, task notes,
evaluator files, other test tasks, generated skills from other attempts, prior
runs, or judge instructions for test solvers. This does not prohibit fewshot
skill generation from reading staged train gold answers; the restriction here
applies to test solver attempt staging.

If a solver accesses, lists, or reports seeing forbidden material such as
`env/`, a source `output/answer.json` during test solving, notes, evaluator
files, train tasks or train answers outside the allowed mode/stage, or another
attempt's files, stop using that result. Mark the attempt contaminated, record
the reason in that attempt directory, report it to the user, and rerun the
affected test in a new clean attempt directory. Do not score or aggregate a
contaminated attempt.

The solver writes `answer.json` in its own attempt directory.

Each solver attempt is launched by the Codex orchestrator as a Dockerized Codex
process from that attempt directory. Mount only the attempt directory and the
per-attempt Codex home used for `CODEX_HOME`; do not mount the full workspace or
task group.

## 5. Score And Aggregate

After each solver writes `answer.json`, call the current test task's
`eval/eval.sh` with the prediction path and save `score.yaml`.

Every solver attempt must have a unique `eval_attempt_id`:

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

The ID must appear in the solver prompt, attempt directory, and
`run_metadata.yaml`.

Backfill token usage, solver turn count, and tool-call count from the raw Codex
session trace written into the attempt-mounted `CODEX_HOME`. Confirm the trace
uses the expected attempt directory and contains the matching `eval_attempt_id`.

Codex raw session traces should be under:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/codex_home/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

Record the raw session trace path in `run_metadata.yaml`. If the raw session
trace is missing, keep the raw trace path `null`, leave trace-derived efficiency
fields `null`, and report the trace issue.

After all runs complete, aggregate `acc@3`, population `std@3`, average
cached/input/output tokens, and solver turn count and tool-call counts for all
four conditions. Efficiency metrics count only test solver answer writing:
average the 3 attempts for the same test task, then average the 5 test tasks.
Do not include skill generation, environment checks, evaluator execution,
or main-agent summarization in solver efficiency.

Separately aggregate evolve token usage and cost across the 3 skill-generation
runs for `fewshot`, `self`, and `reflect-3`. Preserve each attempt's metadata and
trace path in the workspace audit files. In the formal report, keep only each
attempt's token and cost fields plus the arithmetic mean of each token bucket
and USD cost, without mixing them into solver efficiency.

## 6. Interpret Results

In the report, explain:

- Overall `acc@3` and population `std@3` for all four conditions.
- Improvement from `fewshot`, `self`, and `reflect-3` over `base`.
- Evolve token usage and USD cost for `fewshot`, `self`, and `reflect-3`.
- Which test tasks improved clearly and which did not.
- Any environment instability, output-schema friction, evaluator issue, or
  suspicious leakage risk.
