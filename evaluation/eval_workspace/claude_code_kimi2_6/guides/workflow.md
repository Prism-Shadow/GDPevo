# Evaluation Workflow

This file explains how the main evaluation agent should run one complete Claude
Code evaluation for Kimi 2.6 through SiliconFlow.

The evaluation uses one host-side task environment reachable from the agent
containers and four conditions:

```text
base
fewshot
self
reflect-3
```

Before starting, confirm the active Claude Code session is configured for the
Kimi 2.6 run:

```text
ANTHROPIC_BASE_URL=https://api.siliconflow.cn/
ANTHROPIC_MODEL=Pro/moonshotai/Kimi-K2.6
ANTHROPIC_CUSTOM_MODEL_OPTION=Pro/moonshotai/Kimi-K2.6
CLAUDE_CODE_EFFORT_LEVEL=xhigh
permissions.defaultMode=bypassPermissions
```

Record the observed model, Claude Code effort, Kimi model-side thinking mode,
and permission mode in `scratch/environment.md`. Treat these as two separate
inference-control levels: Claude Code effort is `xhigh`, while Kimi thinking
should be recorded as `enabled`; do not describe Kimi itself as using an
`xhigh` thinking level.

When a user asks you to run evaluation in this workspace, that request is
permission for Codex to orchestrate Dockerized `claude -p` subprocesses. Keep
every skill-generation and solver run in a clean, dedicated directory, and mount
only that staged directory plus the matching trace/output directory into the
container. Use the exact mode-specific prompt in `agent_prompts.md` for every
process; replace only declared placeholders and do not append task hints or
extra paths.

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
`TASK_ENV_BIND=0.0.0.0` and `TASK_ENV_PORT` set to `9000 + the numeric task-group id`.
Every agent container must use
`--add-host=host.docker.internal:host-gateway`. Confirm the health/index
endpoint from a disposable container through this exact route and record the
startup/reset commands, port, and URL in `scratch/environment.md`.

Some official task inputs were authored for the local-environment harness and
may mention localhost, `127.0.0.1`, or `env/setup.sh`. Do not modify official
task input files, but treat those local references as obsolete for this Kimi
evaluation. The main agent must override those references when preparing each
staged `environment_access.md`:

```text
base_url: http://host.docker.internal:<TASK_ENV_PORT>/
allowed_endpoints:
- <METHOD /path>
credentials: <runtime credentials, only when required>
```

Skill-generation and solver Claude runs must not enter, list, or read `env/`.
They may use only the container-visible environment entrypoint staged by the main agent.

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

Do not copy whole train task directories for skill generation. For each staged
train task, copy only:

- `input/`
- `output/answer.json` only when the current mode explicitly allows train gold
  answers.

Never stage `notes/`, `eval/`, `env/`, `test_tasks/`, task-group manifests
outside the staged inputs, or source files not explicitly allowed above.

For every skill-generation run, mount a dedicated per-run Claude config
directory as `CLAUDE_CONFIG_DIR=/claude_config`, pass a unique session ID, and
preserve the exact session file under
`original_traces/skill_generation/<condition>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl`.
Write `scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml`.
Backfill token buckets from the matched session using the same deduplication
rules as solver traces, then calculate cost with `metric_and_scoring.md`. Report
this as evolve usage; do not include it in solver efficiency metrics.

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
- `environment_access.md` with the container-visible URL, credentials when needed, and the allowed endpoint names; it overrides stale local-env references in official task inputs.
- The complete matching skill package directory as `skill/` for non-base modes.

Do not copy whole test task directories for solver attempts. Do not stage
`env/`, train tasks, source answer files, test answers, task notes, evaluator
files, other test tasks, generated skills from other attempts, prior runs, or
judge instructions for test solvers. This does not prohibit fewshot skill
generation from reading staged train gold answers; the restriction here applies
to test solver attempt staging.

If a solver accesses, lists, or reports seeing forbidden material such as
`env/`, a source `output/answer.json` during test solving, notes, evaluator
files, train tasks or train answers outside the allowed mode/stage, or another
attempt's files, stop using that result. Mark the attempt contaminated, record
the reason in that attempt directory, report it to the user, and rerun the
affected test in a new clean attempt directory. Do not score or aggregate a
contaminated attempt.

The solver writes `answer.json` in its own attempt directory.

The attempt directory layout is mandatory:

```text
runs/<condition>/<test_id>/attempt_<nn>/answer.json
runs/<condition>/<test_id>/attempt_<nn>/score.yaml
runs/<condition>/<test_id>/attempt_<nn>/run_metadata.yaml
```

Do not use flattened files such as
`runs/base/test_001_attempt_01_answer.json`; they cannot be aggregated or
matched to traces reliably.

## 5. Score And Aggregate

After each solver writes `answer.json`, call the current test task's
`eval/eval.sh` with the prediction path and save `score.yaml`.

Every solver attempt must have a unique `eval_attempt_id`:

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

The ID must appear in the solver prompt, attempt directory, and
`run_metadata.yaml`.

Backfill token usage from the matched Dockerized Claude Code solver session
trace captured from the container's Claude home under
`.claude/projects/.../*.jsonl`. Deduplicate by `message.id`: keep input/cache
buckets from any record and the max `output_tokens` per message id, then sum
across responses.
From the same matched solver trace, also count solver assistant/model-response
turns and assistant `tool_use` content blocks. Store these raw counts in
`run_metadata.yaml` as `rounds` and `tool_calls`.

Each Dockerized Claude run should also write a `docker_run_manifest.yaml` under
the matching trace directory, recording the staged working directory, trace
directory, session id when available, model, Claude Code effort, Kimi thinking mode,
permission mode, timeout, exit code, and copied session trace files.

After matching the trace, copy or preserve the raw trace files under:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/
```

Record the copied workspace trace paths in `run_metadata.yaml`. If no unique
trace can be matched, set the copied trace path to `null`, keep the token,
round-count, and tool-call fields `null`, and report the trace issue.

After all runs complete, aggregate `acc@3`, population `std@3`, per-bucket
tokens, `rounds_avg_3`, and `tool_calls_avg_3` for all four conditions. Raw
metadata may keep provider-specific names such as `cache_creation_input_tokens`
and `cache_read_input_tokens`, but the formal report must use
`cache_creation_tokens_avg_3` and `cache_read_tokens_avg_3`. Efficiency metrics
count only test solver answer writing: average the 3 attempts for the same test
task, then average the 5 test tasks. Do not include skill generation, remote
environment checks, evaluator execution, or main-agent summarization. Temporary
checking code, aggregation code, and environment notes must be placed under
`scratch/`, not in the workspace root.

Separately aggregate each non-base mode's 3 skill-generation traces and
`evolve_metadata.yaml` files into the report's top-level `evolve` block. Keep
metadata and trace paths in workspace audit files. In the formal report, keep
only each attempt's token and cost fields plus the arithmetic mean of every
token bucket and USD cost across the three attempts.

The final report must also include `model_config.claude_code_effort: xhigh` and
`model_config.kimi_thinking: enabled`. Do not encode Kimi's thinking mode as
`xhigh`; `xhigh` refers only to Claude Code's outer effort setting.

Before marking the evaluation complete, check that each scored solver attempt
has a matched raw Claude Code trace copied under `original_traces/` and that
the report token, round-count, and tool-call fields were aggregated from those
copied traces. If any trace or efficiency field is missing, preserve the reason
in `run_metadata.yaml` and call it out in the final report.

## 6. Interpret Results

In the report, explain:

- Overall `acc@3` and population `std@3` for all four conditions.
- Improvement from `fewshot`, `self`, and `reflect-3` over `base`.
- Which test tasks improved clearly and which did not.
- Any environment instability, output-schema friction, evaluator issue, or
  suspicious leakage risk.
