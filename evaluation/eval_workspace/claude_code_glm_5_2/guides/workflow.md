# Evaluation Workflow

This file explains how the Codex main evaluation orchestrator should run one
complete Claude Code evaluation with `GLM-5.2`: Claude Code uses `xhigh` effort,
and the GLM model setting reported for the released run is `max`.

The evaluation uses one task environment reachable from the agent containers
and four conditions:

```text
base
fewshot
self
reflect-3
```

When a user asks you to run evaluation in this workspace, that request is
permission for Codex to orchestrate the experiment and launch Dockerized Claude
Code runs configured for GLM-5.2. Keep every skill-generation and solver run in
a clean, dedicated staged directory mounted as `/work` inside Docker.

Read `CODEX_ORCHESTRATOR.md` before launching isolated agent runs. The formal
Claude Code command shape is:

```bash
CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config claude -p --permission-mode bypassPermissions --session-id "$CLAUDE_SESSION_ID" "$PROMPT"
```

`CLAUDE_CONFIG_DIR` is a runtime-only temporary environment variable for that
agent process, not a task `.env` setting. Do not use `--no-session-persistence`
for formal attempts. Use the exact mode-specific prompt in `agent_prompts.md`
for every process; replace only declared placeholders and do not append task
hints or extra paths.

Before launching any runs, confirm that the Dockerized Claude Code configuration
uses `GLM-5.2` with Claude Code `xhigh` effort and the GLM `max` model setting.
Record the observed model and effort under `scratch/`.

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
GDPEVO_RUN_OWNER="<user_name>"
GDPEVO_ENV_BASE_URL=http://task-env:<TASK_ENV_PORT>/
GDPEVO_JUDGE_PATH=/api/judge
```

Build `task_group/env/Dockerfile`. Create the mandatory owner/run-scoped network
and environment container described in `CODEX_ORCHESTRATOR.md`, with alias
`task-env`, `TASK_ENV_BIND=0.0.0.0`, internal `TASK_ENV_PORT = 9000 + task-group
number`, and no published host port. Attach every agent container to its
assigned network. Read `env.state_mode` to choose shared-within-stage or
fresh-per-attempt lifetime, and keep judge-enabled reflect generation separate
from judge-disabled test runs. Confirm the health/index endpoint from a
disposable container on the same network through the exact agent URL and
record all runtime names, image, state mode, port, URL, and result in
`scratch/environment.md`.

Skill-generation and solver runs must not enter, list, or read `env/`. They may
use only the container-visible environment entrypoint staged by the main agent.

Read endpoint names from `task_group/env/endpoints.txt`. Each staged
`environment_access.md` must include the base URL, required credentials, and
all endpoints allowed for that run. List GET endpoints as `METHOD /path` lines
without business descriptions. For every allowed POST endpoint, inspect the
verified runtime contract and also include its content type, required
authentication headers, required and optional JSON fields with their value
types, and one minimal request example using placeholders. Include only the
mechanical request contract: do not expose business rules, hidden values,
expected answers, evaluator behavior, or task-specific query results. Include
business endpoints for skill generation and test solving; add `/api/judge` only
for reflect skill generation; never include `/health` or reset/reseed endpoints
in execution-agent inputs.

Use this shape for non-judge POST entries in `environment_access.md`:

```text
POST /path
Content-Type: application/json
Required headers: <header name and runtime value, or none>
JSON body: {"field": "<string>", "optional_field": ["<value>"]}
Example: curl ...
```

The example must be directly runnable after replacing placeholders and must
match the actual endpoint fields and authentication placement.

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

For every skill-generation run, create a named agent container without `--rm`
and keep `CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` inside it, together with
a unique session ID. Mount only the staged materials and, if needed, the minimum
read-only authentication bootstrap file. Use `docker cp` to copy only
`projects/<sanitized-cwd>/<claude_session_id>.jsonl` (or a temporary `projects/`
subtree under `scratch/trace_extract/<run_id>/` for discovery) to
`original_traces/skill_generation/<condition>/attempt_<nn>/<claude_session_id>.jsonl`
and write the matching
`scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml`.
Backfill and verify its token buckets and cost from the copied file, then remove
the extraction directory and stopped container. Do not retain the complete
container-local config, credentials, plugins, caches, logs, databases, or
stdout/stderr as trace artifacts. Report this as evolve usage; do not include it
in solver efficiency metrics.

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
- `environment_access.md` with the container-visible URL, credentials when
  needed, allowed endpoint names, and the POST request contracts defined above.
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

Each solver attempt is launched by the Codex orchestrator as a Dockerized
Claude Code process from that attempt directory. Create a named container
without `--rm`, mount only the attempt directory, and keep
`CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` inside it. Do not mount the full
workspace, task group, host `.claude` directory, or host config tree.

## 5. Score And Aggregate

After each solver writes `answer.json`, call the current test task's
`eval/eval.sh` with the prediction path and save `score.yaml`.

Every solver attempt must have a unique `eval_attempt_id`:

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

The ID must appear in the solver prompt, attempt directory, and
`run_metadata.yaml`.

Set `model: glm-5.2, max` in each run metadata file.

Keep the named container stopped after the run. Identify the exact native session
JSONL named by the unique session ID in the container-local `CLAUDE_CONFIG_DIR`,
using `docker cp` (or a temporary `projects/` subtree under
`scratch/trace_extract/<run_id>/` for discovery), verify its working directory,
and copy only that file into `original_traces/`. Backfill token usage, cost,
solver turn count, and tool-call count from the copied file.
Deduplicate by `message.id`: keep input/cache buckets from any record and the
max `output_tokens` per message id, then sum across responses.

Claude Code session traces should be under:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/<claude_session_id>.jsonl
```

Record and verify the copied primary session path and all trace-derived fields in
`run_metadata.yaml`, then delete the temporary extraction directory and stopped
container. Do not preserve the full container-local `CLAUDE_CONFIG_DIR` or
stdout. If the session trace is missing or ambiguous, record the reason, clean up,
and rerun with a new session ID.

After all runs complete, aggregate `acc@3`, population `std@3`, per-bucket tokens, and solver turn count and tool-call counts for all four
conditions. Efficiency metrics count only test solver answer writing: average
the 3 attempts for the same test task, then average the 5 test tasks. Do not
include skill generation, environment checks, evaluator execution, or
main-agent summarization.

Separately aggregate each non-base mode's 3 skill-generation traces and
`evolve_metadata.yaml` files into the report's top-level `evolve` block. Keep
metadata and trace paths in workspace audit files. In the formal report, keep
only each attempt's token and cost fields plus the arithmetic mean of every
token bucket and USD cost across the three attempts.

## 6. Interpret Results

In the report, explain:

- Overall `acc@3` and population `std@3` for all four conditions.
- Improvement from `fewshot`, `self`, and `reflect-3` over `base`.
- Which test tasks improved clearly and which did not.
- Any environment instability, output-schema friction, evaluator issue, or
  suspicious leakage risk.
