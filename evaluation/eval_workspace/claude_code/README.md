# Evaluation Workspace

This workspace is the evaluation entrypoint. You are the main evaluation agent for this stage. Your goal is to formally evaluate one task group that has already passed quality review, using `acc`, population `std`, solver efficiency metrics, and separately reported evolve token/cost metrics across four conditions: `base`, `fewshot`, `self`, and `reflect-3`.

This workspace evaluates one task group at a time. Do not modify the task group under evaluation. If you find that the task group itself is invalid, record the risk in the report and send the data back to an earlier stage.

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

1. `CODEX_ORCHESTRATOR.md` - Codex main-agent orchestration, Docker isolation, Claude Code command, and trace preservation
2. `guides/workflow.md` - main-agent evaluation workflow
3. `guides/skill_modes.md` - the four conditions and information boundaries
4. `guides/agent_prompts.md` - fixed skill-generation and solver prompts
5. `guides/metric_and_scoring.md` - `acc`, population `std`, turn/tool-call tracking, single-attempt scoring, and aggregation rules
6. `guides/report_format.md` - final report format

## Launch Prompt

```text
Please evaluate task_group/<task_group_id> using README.md and guides/.
Model: <model>.
Run all four modes with acc/std, collect solver and evolve token/cost metrics, preserve each primary session JSONL, and write report/<task_group_id>.yaml.
```

Use `.env` for the agent-container-visible task environment:

```text
GDPEVO_RUN_OWNER="<user_name>"
GDPEVO_ENV_BASE_URL=http://task-env:9001/
GDPEVO_JUDGE_PATH=/api/judge
```

## Workflow

Codex is the main evaluation orchestrator. When a user asks you to run evaluation in this workspace, that request is permission for Codex to stage clean directories, launch Dockerized Claude Code isolated agent runs with `claude -p`, call evaluators, preserve traces, and aggregate reports. Do not reduce the attempt count, merge multiple test tasks into one solver run, or solve test tasks directly as the main agent.

Each skill-generation run and solver attempt must run inside Docker from only its staged directory. Use the command shape in `CODEX_ORCHESTRATOR.md`: `CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config claude -p --permission-mode bypassPermissions --session-id "$CLAUDE_SESSION_ID" "$PROMPT"`. `CLAUDE_CONFIG_DIR` is a runtime-only temporary environment variable for that agent process, not a task `.env` setting. Do not use `--no-session-persistence` for formal attempts.

1. Confirm that `task_group/` contains exactly one task group:

```text
task_group/<task_group_id>/
```

2. Check that the workspace contains only one task group and that the task group includes 5 train tasks, 5 test tasks, a shared environment, standard answers, and evaluators.

3. Build the environment from `task_group/<task_group_id>/env/Dockerfile`. For every runtime scope, create a Docker bridge network whose unique name contains normalized `<user_name>`, task-group number, capability stage, condition/task/attempt when applicable, and an eight-character random suffix. Start the environment on that network with alias `task-env`, `TASK_ENV_BIND=0.0.0.0`, and internal `TASK_ENV_PORT = 9000 + task-group number`; publish no host port. Agent containers join the same network and use `http://task-env:<TASK_ENV_PORT>/`. Read `env.state_mode`: share a read-only instance only inside one capability stage; give every mutable attempt a fresh network and environment. Enable `/api/judge` only for the isolated reflect skill-generation stage and disable it for formal tests. Verify `/health` from a disposable container on the same network and record all runtime names and results.

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

For every skill-generation run, create a named Docker container without `--rm`
and keep `CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` inside it. Mount only the
staged materials and, when needed, a minimum read-only authentication bootstrap
file. After the run, use `docker cp` to extract only the matching native session
JSONL (or a temporary `projects/` subtree under
`scratch/trace_extract/<run_id>/` for discovery) to
`original_traces/skill_generation/<condition>/attempt_<nn>/`. Write and verify
the matching `evolve_metadata.yaml` under `scratch/skill_generation/` with token
usage and calculated USD cost before removing the extraction directory and
stopped container. Never retain the complete container-local Claude config.

5. Run test tasks under all four conditions:

```text
runs/base/
runs/fewshot/
runs/self/
runs/reflect-3/
```

For each condition, run each test task independently 3 times. Every run must be completed by a clean-context Dockerized Claude Code isolated agent run. For skill conditions, solver `attempt_<nn>` uses the independently generated skill with the same attempt number.

6. After each solver output, call the task evaluator and save the score in the corresponding attempt directory. Each attempt directory should also contain `run_metadata.yaml`, recording the unique `eval_attempt_id`, the Claude session ID, copied primary session trace path, token usage, solver turn count, and tool-call count. Run the solver in a named container without `--rm`, with `CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` kept inside the container. After the run, use `docker cp` to copy only `projects/<sanitized-cwd>/<claude_session_id>.jsonl` to `original_traces/<condition>/<task_id>/attempt_<nn>/<claude_session_id>.jsonl` (a temporary `projects/` subtree under `scratch/trace_extract/<run_id>/` may be used for discovery). Populate and verify token, cost, turn, tool-call and metadata fields from that copy before deleting the extraction directory and stopped container. Do not preserve the complete config tree, credentials, plugins, caches, logs, databases, or stdout as trace artifacts.

7. After all score records are ready, aggregate `acc` and population `std` for the four conditions, plus average token, turn, tool-call, and cost fields for each condition. Separately aggregate evolve tokens and USD cost across the 3 skill-generation runs for each non-base mode. Write the final report to `report/<task_group_id>.yaml`. Solver efficiency only counts answer-writing by test solver runs: first average the 3 attempts for the same test task, then average the 5 test tasks. Do not mix skill generation, environment checks, evaluator execution, or main-agent summarization into solver efficiency. Temporary checking or aggregation code may be placed under `scratch/`.

## Agent Boundaries

The main agent may read the full task group in order to start/reset the environment, verify its network contract, call evaluators, and aggregate results, but it must not solve test tasks directly.

Skill-generation isolated agent runs only generate skills. They do not solve test tasks.

Solver isolated agent runs may only see the information allowed for the current condition. A solver must not see test standard answers, test notes, evaluator implementation details, or `env/` source code. Skill-generation and solver runs must not enter, list, read, or mount `env/`; they may use the shared environment only through the container-visible Web/API URL or database connection explicitly exposed by the main agent. Only reflect skill-generation runs should receive the train-only judge API instructions, and that API is not valid for test-time solving.

Mode-allowed training exposure is not contamination: for example, fewshot skill generation may read train `output/answer.json`. For test-solving attempts, however, direct access to any source `output/answer.json` is forbidden unless that answer file is the solver's own output inside the current attempt directory.

If a solver/test run accidentally accesses, lists, or reports seeing forbidden material such as `env/`, source `output/answer.json` during test solving, task notes, evaluator files, train tasks outside the allowed mode/stage, or another attempt's run files, treat that attempt as contaminated. Report the incident to the user, do not score or aggregate that attempt, record the reason in the attempt directory, and rerun the affected test in a fresh clean attempt directory.

For each solver attempt, the main agent stages the allowed files into a dedicated fresh attempt directory, such as `runs/base/test_001/attempt_01/`, and mounts only that directory as `/work` for the Dockerized Claude Code run. Stage the current task `input/`, environment access instructions, and, for skill modes only, the complete matching skill package directory as `skill/`. Do not reuse an attempt directory for a rerun; create a new clean directory and keep the invalidated run for audit. For skill generation, stage only the allowed train materials for that mode into a dedicated directory under `scratch/skill_generation/`, mount only that directory, and copy the generated `skill/` directory to the matching canonical attempt directory under `skills/`.

## Fixed Agent Prompts

Use the exact mode-specific skill-generation and test-solver templates in
`guides/agent_prompts.md`. Replace only the declared placeholders and do not
append hints or hidden context. The main agent later uses each run id and Claude
session id to locate the mounted session trace and backfill token, turn, and
tool-call fields.
