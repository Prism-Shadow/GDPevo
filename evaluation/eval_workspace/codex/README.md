# Evaluation Workspace

This workspace is the evaluation entrypoint. You are the main evaluation agent for this stage. Your goal is to formally evaluate one task group that has already passed quality review, using `acc@3` across four conditions: `base`, `fewshot`, `self`, and `reflect-3`.

This workspace evaluates one task group at a time. Do not modify the task group under evaluation. If you find that the task group itself is invalid, record the risk in the report and send the data back to an earlier stage.

## Directories

| Path | Purpose |
| --- | --- |
| `guides/` | Evaluation workflow, skill modes, metrics, scoring, and report format |
| `task_group/` | The single official task group currently under evaluation |
| `skills/` | Generated `fewshot`, `self`, and `reflect-3` files |
| `runs/` | Solver outputs and scoring records for each condition, test task, and attempt |
| `scratch/` | Temporary scripts, environment notes, and intermediate checks created by the main evaluation agent |
| `report/` | The final evaluation report for the current task group |

## Guides

Read these files in order before starting evaluation:

1. `guides/workflow.md` - main-agent evaluation workflow
2. `guides/skill_modes.md` - the four conditions and information boundaries
3. `guides/metric_and_scoring.md` - `acc@3`, single-attempt scoring, and aggregation rules
4. `guides/report_format.md` - final report format

## Launch Prompt

```text
Please evaluate task_group/<task_group_id> using README.md and guides/.
Model: <model>, <reasoning_effort>.
Run all four modes with acc@3 and write report/<task_group_id>.yaml.
```

Use `.env` for the remote task environment:

```text
GDPEVO_ENV_BASE_URL=https://your-env-host.example/
GDPEVO_JUDGE_PATH=/api/judge
```

## Workflow

When a user asks you to run evaluation in this workspace, that request is considered permission to use Codex subagents, including skill-generation subagents and solver subagents. If the required number of subagents exceeds the current Codex concurrency limit, run them in batches until all required attempts are complete. Do not reduce the attempt count, merge multiple test tasks into one solver run, or solve test tasks directly as the main agent.

1. Confirm that `task_group/` contains exactly one task group:

```text
task_group/<task_group_id>/
```

2. Check that the workspace contains only one task group and that the task group includes 5 train tasks, 5 test tasks, a shared environment, standard answers, and evaluators.

3. Confirm the remote task-group environment from `.env`. Do not start a local env service for Codex evaluation. Record the base URL, health-check result, and any remote environment notes.

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

5. Run test tasks under all four conditions:

```text
runs/base/
runs/fewshot/
runs/self/
runs/reflect-3/
```

For each condition, run each test task independently 3 times. Every run must be completed by a clean-context solver subagent. For skill conditions, solver `attempt_<nn>` uses the independently generated skill with the same attempt number.

6. After each solver output, call the task evaluator and save the score in the corresponding attempt directory. Each attempt directory should also contain `run_metadata.yaml`, recording the unique `eval_attempt_id`, Codex session trace, and token usage.

7. After all score records are ready, aggregate `acc@3` for the four conditions, plus average cached/input/output tokens for each condition. Write the final report to `report/<task_group_id>.yaml`. These efficiency metrics only count answer-writing by test solver subagents: first average the 3 attempts for the same test task, then average the 5 test tasks. Do not include skill generation, remote environment checks, evaluator execution, or main-agent summarization. Temporary checking or aggregation code may be placed under `scratch/`.

## Agent Boundaries

The main agent may read the full task group in order to verify the remote environment contract, call evaluators, and aggregate results, but it must not solve test tasks directly.

Skill-generation subagents only generate skills. They do not solve test tasks.

Solver subagents may only see the information allowed for the current condition. A solver must not see test standard answers, test notes, evaluator implementation details, or `env/` source code. Skill-generation and solver subagents must not enter, list, or read `env/`; they may use the shared environment only through the remote Web/API URL or database connection explicitly exposed by the main agent. Only reflect skill-generation subagents should receive the train-only judge API instructions, and that API is not valid for test-time solving.

If a solver/test subagent accidentally accesses, lists, or reports seeing forbidden material such as `env/`, `output/answer.json`, task notes, evaluator files, train tasks outside the allowed mode, or another attempt's run files, treat that attempt as contaminated. Report the incident to the user, do not score or aggregate that attempt, record the reason in the attempt directory, and rerun the affected test in a fresh clean attempt directory.

For solver attempts, use the corresponding fresh attempt directory as the subagent workspace/cwd, such as `runs/base/test_001/attempt_01/`. Stage the current task `input/`, environment access instructions, and, for skill modes only, the matching skill copy for the same attempt number. Do not reuse an attempt directory for a rerun; create a new clean directory and keep the invalidated run for audit. For skill generation, use a dedicated directory under `scratch/skill_generation/` and stage only the allowed train materials for that mode.

## Solver Prompt

Keep the solver subagent prompt short and explicit:

```text
eval_attempt_id: <unique_eval_attempt_id>

Please solve this single test task from the current attempt directory only. Do not access any path outside it. Use only the staged task input, allowed environment access, and the skill file if one is provided. If you accidentally see env source, answer files, notes, evaluator files, train tasks not staged for this attempt, or another run's files, stop and report the contamination instead of solving. Write the final answer as answer.json following input/payloads/answer_template.json.
```

The main agent later uses `eval_attempt_id` to match the corresponding Codex session trace and backfill `token_count`.
