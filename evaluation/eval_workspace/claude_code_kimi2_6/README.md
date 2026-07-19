# Kimi 2.6 Claude Code Evaluation Workspace

This workspace is the evaluation entrypoint. You are the main evaluation agent for this stage. Your goal is to formally evaluate one task group that has already passed quality review, using `acc`, population `std`, solver efficiency metrics, and separately reported evolve token/cost metrics across four conditions: `base`, `fewshot`, `self`, and `reflect-3`.

This workspace evaluates one task group at a time. Do not modify the task group under evaluation. If you find that the task group itself is invalid, record the risk in the report and send the data back to an earlier stage.

This workspace is for Claude Code running Kimi 2.6 through the SiliconFlow
Anthropic-compatible endpoint. Before starting any evaluation, confirm Claude
Code is configured with:

```text
ANTHROPIC_BASE_URL=https://api.siliconflow.cn/
ANTHROPIC_MODEL=Pro/moonshotai/Kimi-K2.6
ANTHROPIC_CUSTOM_MODEL_OPTION=Pro/moonshotai/Kimi-K2.6
CLAUDE_CODE_EFFORT_LEVEL=xhigh
permissions.defaultMode=bypassPermissions
```

Record the two inference-control levels separately: Claude Code's outer effort
level is `xhigh`, while the Kimi model-side thinking mode should be recorded as
`enabled`. Do not describe Kimi itself as using an `xhigh` thinking level.

Do not write API keys into this workspace. Use the user's Claude Code
configuration for credentials and record the observed model, Claude Code effort,
Kimi thinking mode, and permission mode before launching Dockerized Claude Code
runs.

## Directories

| Path | Purpose |
| --- | --- |
| `guides/` | Evaluation workflow, skill modes, metrics, scoring, and report format |
| `task_group/` | The single official task group currently under evaluation |
| `skills/` | Generated `fewshot`, `self`, and `reflect-3` skill packages; each attempt is a directory whose entry file is `SKILL.md` |
| `runs/` | Solver outputs and scoring records for each condition, test task, and attempt |
| `original_traces/` | One copied primary Claude Code session JSONL per skill-generation run and solver attempt |
| `scratch/` | Temporary scripts, environment notes, and intermediate checks created by the main evaluation agent |
| `report/` | The final evaluation report for the current task group |

## Guides

Read these files in order before starting evaluation:

1. `guides/workflow.md` - main-agent evaluation workflow
2. `guides/skill_modes.md` - the four conditions and information boundaries
3. `guides/agent_prompts.md` - fixed skill-generation and solver prompts
4. `guides/metric_and_scoring.md` - `acc`, population `std`, trace efficiency, single-attempt scoring, and aggregation rules
5. `guides/report_format.md` - final report format

## Launch Prompt

```text
Please evaluate task_group/<task_group_id> using README.md and guides/.
Model: Pro/moonshotai/Kimi-K2.6 via SiliconFlow.
Run all four modes with acc/std, collect solver and evolve token/cost metrics, preserve each primary session JSONL, and write report/<task_group_id>.yaml.
```

Use `.env` for the agent-container-visible task environment:

```text
GDPEVO_RUN_OWNER="<user_name>"
GDPEVO_ENV_BASE_URL=http://task-env:9001/
GDPEVO_JUDGE_PATH=/api/judge
```

## Workflow

When a user asks you to run evaluation in this workspace, Codex acts as the
orchestrator. For each skill-generation run or solver attempt, Codex stages only
the allowed files into a clean directory and launches a Dockerized `claude -p`
subprocess from that directory. Do not launch scored runs through a parent
Claude Code conversation for this Kimi workspace unless a future instruction
explicitly switches the execution mode. Do not reduce the attempt count, merge
multiple test tasks into one solver run, or solve test tasks directly as the
orchestrator.

Every Dockerized Claude Code subprocess must use Kimi 2.6 via SiliconFlow,
Claude Code effort `xhigh`, Kimi model-side thinking `enabled`, and bypass
permissions. Record those observed settings in `scratch/`.

1. Confirm that `task_group/` contains exactly one task group:

```text
task_group/<task_group_id>/
```

2. Check that the workspace contains only one task group and that the task group includes 5 train tasks, 5 test tasks, a shared environment, standard answers, and evaluators.

3. Build the environment from `task_group/<task_group_id>/env/Dockerfile`. For every runtime scope, create a Docker bridge network whose unique name contains normalized `<user_name>`, task-group number, capability stage, condition/task/attempt when applicable, and an eight-character random suffix. Start the environment on that network with alias `task-env`, `TASK_ENV_BIND=0.0.0.0`, and internal `TASK_ENV_PORT = 9000 + task-group number`; publish no host port. Agent containers join the same network and use `http://task-env:<TASK_ENV_PORT>/`. Read `env.state_mode`: share a read-only instance only inside one capability stage; give every mutable attempt a fresh network and environment. Enable `/api/judge` only for the isolated reflect skill-generation stage and disable it for formal tests. Verify `/health` from a disposable container on the same network and record all runtime names and results.

Some official task inputs may still mention localhost, `127.0.0.1`, or
`env/setup.sh` from the local-environment harness. Do not edit those official
inputs, but treat those local references as superseded for this Kimi evaluation.
When staging every skill-generation or solver directory, write
`environment_access.md` with the `.env` container-visible URL, required runtime
credentials, and every endpoint name allowed for that run from
`task_group/env/endpoints.txt`. List endpoints only as `METHOD /path`, without
descriptions.

4. Generate 3 independent skills for each non-base condition:

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

For every skill-generation run, create a named Docker container without `--rm`,
keep `CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` inside it, and use a unique
session ID. Mount only staged materials and, if needed, a minimum read-only
authentication bootstrap file. After the run, use `docker cp` to copy only
`projects/<sanitized-cwd>/<claude_session_id>.jsonl` (or a temporary `projects/`
subtree under `scratch/trace_extract/<run_id>/` for discovery) to
`original_traces/skill_generation/<condition>/attempt_<nn>/<claude_session_id>.jsonl`,
then populate and verify the matching `evolve_metadata.yaml` under
`scratch/skill_generation/` with token usage and calculated USD cost. Delete
the extraction directory and stopped container only after those fields are
complete. Never retain the complete container-local config.

Do not copy a whole train task or test task directory into any Claude run staging
area. Stage only the files explicitly allowed by `guides/skill_modes.md` and
`guides/workflow.md`.

5. Run test tasks under all four conditions:

```text
runs/base/
runs/fewshot/
runs/self/
runs/reflect-3/
```

For each condition, run each test task independently 3 times. Every run must be completed by a clean-context Dockerized solver subprocess. For skill conditions, solver `attempt_<nn>` uses the independently generated skill with the same attempt number.

6. After each solver output, call the task evaluator and save the score in the corresponding attempt directory. Each attempt directory should also contain `run_metadata.yaml`, recording the unique `eval_attempt_id`, Claude session ID, copied primary trace path, token usage, solver round count, and tool-call count. Use a named container without `--rm`, keep `CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` inside it, match the exact `projects/<sanitized-cwd>/<claude_session_id>.jsonl`, and use `docker cp` to copy only that file to `original_traces/<condition>/<task_id>/attempt_<nn>/<claude_session_id>.jsonl` (a temporary `projects/` subtree under `scratch/trace_extract/<run_id>/` may be used for discovery). Populate and verify token, cost, round, tool-call and metadata fields from the copy before deleting the extraction directory and stopped container. Do not preserve the complete config tree or stdout.

The run layout is mandatory. Do not invent flattened files such as
`runs/base/test_001_attempt_01_answer.json`.

```text
runs/<condition>/<test_id>/attempt_<nn>/answer.json
runs/<condition>/<test_id>/attempt_<nn>/score.yaml
runs/<condition>/<test_id>/attempt_<nn>/run_metadata.yaml
```

7. After all score records are ready, aggregate `acc` and population `std` for the four conditions, plus average token, round-count, tool-call, and cost fields for each condition. Separately aggregate evolve tokens and USD cost across the 3 skill-generation runs for each non-base mode. Write the final report to `report/<task_group_id>.yaml`. The report must include a `model_config` block with `claude_code_effort: xhigh` and `kimi_thinking: enabled`. The formal report field names are `input_tokens_avg_3`, `cache_creation_tokens_avg_3`, `cache_read_tokens_avg_3`, `output_tokens_avg_3`, `cost_usd_avg_3`, `rounds_avg_3`, and `tool_calls_avg_3`. Raw `run_metadata.yaml` may preserve provider-specific token names such as `cache_creation_input_tokens` and `cache_read_input_tokens`, but the report schema must use the normalized field names above. Solver efficiency only counts answer-writing by test solver Claude subprocesses: first average the 3 attempts for the same test task, then average the 5 test tasks. Do not mix skill generation, environment checks, evaluator execution, or orchestrator summarization into solver efficiency. Temporary checking or aggregation code must be placed under `scratch/`, not in the workspace root.

8. Before reporting completion, verify that every scored solver attempt has a
matched primary Claude Code session JSONL copied under `original_traces/`, that
its per-run token, cost, round-count, tool-call and metadata fields were
populated from that copy before its stopped container was removed, and
that the report is reproducible from those retained artifacts. If a trace cannot
be matched uniquely, preserve the issue in the run record, clean up, and rerun
with a new session ID instead of estimating efficiency fields.

## Execution Boundaries

Codex may read the full task group in order to verify the task environment network contract, stage allowed files, call evaluators, and aggregate results, but it must not solve test tasks directly.

Skill-generation Claude subprocesses only generate skills. They do not solve test tasks.

Solver Claude subprocesses may only see the information allowed for the current condition. A solver must not see test standard answers, test notes, evaluator implementation details, or `env/` source code. Skill-generation and solver runs must not enter, list, or read `env/`; they may use the shared environment only through the container-visible Web/API URL or database connection explicitly exposed by Codex. Only reflect skill-generation runs should receive the train-only judge API instructions, and that API is not valid for test-time solving.

Mode-allowed training exposure is not contamination: for example, fewshot skill generation may read train `output/answer.json`. For test-solving attempts, however, direct access to any source `output/answer.json` is forbidden unless that answer file is the solver's own output inside the current attempt directory.

If a solver Claude run accidentally accesses, lists, or reports seeing forbidden material such as `env/`, source `output/answer.json` during test solving, task notes, evaluator files, train tasks outside the allowed mode/stage, or another attempt's run files, treat that attempt as contaminated. Report the incident to the user, do not score or aggregate that attempt, record the reason in the attempt directory, and rerun the affected test in a fresh clean attempt directory.

For each solver attempt, Codex stages the allowed files into a dedicated fresh attempt directory, such as `runs/base/test_001/attempt_01/`, and launches a Dockerized clean-context `claude -p` subprocess from that directory. The container mounts only the staged attempt directory; `CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` remains inside the named container, and only a minimum authentication bootstrap file may be mounted read-only when needed. The Claude run must only read and write task artifacts under the staged directory and must not access any other host path. Stage the current task `input/`, environment access instructions, and, for skill modes only, the complete matching skill package directory as `skill/`. The staged `environment_access.md` must explicitly override any localhost references in official task inputs with the container-visible `GDPEVO_ENV_BASE_URL`. Do not stage `notes/`, `eval/`, source `output/answer.json`, or whole task directories for test solvers. Do not reuse an attempt directory for a rerun; create a new clean directory and keep the invalidated run for audit. For skill generation, stage only the allowed train materials for that mode into a dedicated directory under `scratch/skill_generation/`, restrict that Dockerized Claude run to its own directory, and copy the generated `skill/` directory to the matching canonical attempt directory under `skills/`.

## Fixed Agent Prompts

Use the exact mode-specific skill-generation and test-solver templates in
`guides/agent_prompts.md`. Replace only the declared placeholders and do not
append hints or hidden context. Codex later uses each run id, the Docker run
manifest, and copied primary Claude Code session JSONL to backfill token usage,
round count, and tool-call count.
