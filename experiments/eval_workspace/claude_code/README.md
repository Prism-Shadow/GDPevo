# Evaluation Workspace

This workspace is the evaluation entrypoint. You are the main evaluation agent for this stage. Your goal is to formally evaluate one task group that has already passed quality review, using `avg@3` across three skill conditions.

This workspace evaluates one task group at a time. Do not modify the task group under evaluation. If you find that the task group itself is invalid, record the risk in the report and send the data back to an earlier stage.

## Directories

| Path | Purpose |
| --- | --- |
| `guides/` | Evaluation workflow, skill modes, metrics, scoring, and report format |
| `task_group/` | The single official task group currently under evaluation |
| `skills/` | Generated `demo` and `reflect` files |
| `runs/` | Solver outputs and scoring records for each condition, test task, and attempt |
| `scratch/` | Temporary scripts, environment notes, and intermediate checks created by the main evaluation agent |
| `report/` | The final evaluation report for the current task group |

## Guides

Read these files in order before starting evaluation:

1. `guides/workflow.md` - main-agent evaluation workflow
2. `guides/skill_modes.md` - the three skill conditions and information boundaries
3. `guides/metric_and_scoring.md` - `avg@3`, single-attempt scoring, and aggregation rules
4. `guides/report_format.md` - final report format

## Launch Prompt

```text
Please evaluate task_group/<task_group_id> using README.md and guides/.
Model: <model>.
Run all three modes with avg@3 and write report/<task_group_id>.yaml.
```

## Workflow

When a user asks you to run evaluation in this workspace, that request is considered permission to use Claude Code subagents (the Task / Agent tool), including skill-generation subagents and solver subagents. If the required number of subagents exceeds the subagent concurrency limit, run them in batches until all required attempts are complete. Do not reduce the attempt count, merge multiple test tasks into one solver run, or solve test tasks directly as the main agent.

Solver and skill-generation subagents run with the same model and reasoning/effort setting as the main agent — this is inherited automatically and does not need to be set.

1. Confirm that `task_group/` contains exactly one task group:

```text
task_group/<task_group_id>/
```

2. Check that the workspace contains only one task group and that the task group includes 5 train tasks, 5 test tasks, a shared environment, standard answers, and evaluators.

3. Start or prepare the task-group environment. If a port is needed, roll a random candidate in `8000-8100`; if it is occupied, roll another one. Do not scan upward from `8000`. Record the start command, port, and environment notes.

4. Generate 3 independent skills for each skill condition:

```text
skills/demo/demo_attempt_01/SKILL.md
skills/demo/demo_attempt_02/SKILL.md
skills/demo/demo_attempt_03/SKILL.md
skills/reflect/reflect_attempt_01/SKILL.md
skills/reflect/reflect_attempt_02/SKILL.md
skills/reflect/reflect_attempt_03/SKILL.md
```

5. Run test tasks under all three conditions:

```text
runs/base/
runs/demo/
runs/reflect/
```

For each condition, run each test task independently 3 times. Every run must be completed by a clean-context solver subagent. For skill conditions, solver `attempt_<nn>` uses the independently generated skill with the same attempt number.

6. After each solver output, call the task evaluator and save the score in the corresponding attempt directory. Each attempt directory should also contain `run_metadata.yaml`, recording the unique `eval_attempt_id`, the matched session-transcript reference, and token usage.

7. After all score records are ready, aggregate `avg@3` for the three conditions, plus average cached/input/output tokens for each condition. Write the final report to `report/<task_group_id>.yaml`. These efficiency metrics only count answer-writing by test solver subagents: first average the 3 attempts for the same test task, then average the 5 test tasks. Do not include skill generation, environment startup, evaluator execution, or main-agent summarization. Temporary checking or aggregation code may be placed under `scratch/`.

## Agent Boundaries

The main agent may read the full task group in order to start the environment, call evaluators, and aggregate results, but it must not solve test tasks directly.

Skill-generation subagents only generate skills. They do not solve test tasks.

Solver subagents may only see the information allowed for the current condition. A solver must not see test standard answers, test notes, evaluator implementation details, or `env/` source code. Skill-generation and solver subagents must not enter, list, or read `env/`; they may use the shared environment only through the port, Web/API URL, or database connection explicitly exposed by the main agent.

For each solver attempt, the main agent stages the allowed files into a dedicated attempt directory, such as `runs/base/test_001/attempt_01/`, and launches a clean-context subagent that is restricted to that directory: the subagent must only read and write files under it and must not access any path outside it. Stage the current task `input/`, environment access instructions, and, for skill modes only, the matching skill copy for the same attempt number. For skill generation, stage only the allowed train materials for that mode into a dedicated directory under `scratch/skill_generation/`, and restrict that subagent to its own directory in the same way.

## Solver Prompt

Keep the solver subagent prompt short and explicit:

```text
eval_attempt_id: <unique_eval_attempt_id>

Please solve this single test task. You may only read and write files inside this attempt directory; do not access any path outside it. Use only the staged task input, allowed environment access, and the skill file if one is provided. Write the final answer as answer.json following input/payloads/answer_template.json.
```

The main agent later uses `eval_attempt_id` to locate the subagent's turns in the session transcript and backfill `token_count`.
