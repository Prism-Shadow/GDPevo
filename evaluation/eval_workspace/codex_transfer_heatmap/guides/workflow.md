# Workflow

This workspace runs only the Codex cross-task skill-transfer experiment. It
does not generate new skills.

When a user asks you to run this workspace, that request is permission for Codex
to orchestrate the experiment and launch Dockerized Codex solver runs. Keep
every solver run in a clean, dedicated attempt directory mounted as `/work`
inside Docker. If the required number of runs exceeds practical concurrency,
run them in batches until all required attempts are complete. Do not reduce the
attempt count, merge multiple test tasks into one solver run, or solve test
tasks directly as the main agent.

Read `CODEX_ORCHESTRATOR.md` before launching solver runs. The formal command
shape is:

```bash
CODEX_HOME=/tmp/gdpevo-codex-home codex exec -C /work -m gpt-5.5 -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"
```

`CODEX_HOME` is a runtime-only temporary environment variable for that solver
process, not a task `.env` setting. Do not use `codex exec --ephemeral` for
formal attempts. Use exactly the prompt in `guides/agent_prompts.md`; replace
only its declared placeholders.

Resolve the active Codex home before overriding `CODEX_HOME`. If authentication
is needed, mount only its `auth.json` read-only at
`/run/gdpevo-bootstrap/auth.json`, copy it with mode `0600` into the
container-local home, and verify the login inside the same named container with
`codex login status`. Missing authentication blocks the run; never mount or copy
the complete active Codex home.

Use the model configuration in `heatmap_scope.json` unless the user explicitly
overrides it:

```text
model: GPT-5.5
reasoning_effort: xhigh
```

Read these files before running:

1. `README.md`
2. `RUN_SCOPE.md`
3. `guides/skill_modes.md`
4. `guides/metric_and_scoring.md`
5. `guides/report_format.md`

## 1. Check Scope

Confirm that `task_groups/` contains only the 3 representative task groups:

```text
task_group_002
task_group_006
task_group_010
```

Confirm that `heatmap_scope.json` matches `RUN_SCOPE.md`.

## 2. Start And Check Environments

Start all three environments on the orchestration host with
`TASK_ENV_BIND=0.0.0.0` and distinct ports. Set these values in `.env`:

```text
GDPEVO_TASK_GROUP_002_ENV_BASE_URL=http://host.docker.internal:<TG002_PORT>/
GDPEVO_TASK_GROUP_006_ENV_BASE_URL=http://host.docker.internal:<TG006_PORT>/
GDPEVO_TASK_GROUP_010_ENV_BASE_URL=http://host.docker.internal:<TG010_PORT>/
```

Every solver `docker run` must include
`--add-host=host.docker.internal:host-gateway`. Verify each health/index
endpoint from a disposable container through the exact configured route before
starting scored runs.

The main agent may inspect `task_groups/*/env/` and evaluators to verify the
environment contract, stage allowed materials, and score results. Solver
processes must not enter, list, read, or mount any `env/` source files.

For each target task group, build `environment_access.md` from the verified
runtime contract. Include the container-visible base URL, required credentials,
and every allowed endpoint. List GET endpoints as `METHOD /path` lines without
business descriptions. For every POST endpoint, also include its content type,
required authentication headers, required and optional JSON fields with value
types, and one minimal request example using placeholders. The POST contract
must use the actual field names and credential location; it must not expose
business rules, hidden values, expected answers, evaluator behavior, or
task-specific query results.

Use this shape for POST entries:

```text
POST /path
Content-Type: application/json
Required headers: <header name and runtime value, or none>
JSON body: {"field": "<string>", "optional_field": ["<value>"]}
Example: curl ...
```

## 3. Check Source Skills

Confirm the required existing skills are present:

```text
skills/fewshot/<source_task_group_id>/fewshot_attempt_01/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_02/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_03/SKILL.md

skills/reflect-3/<source_task_group_id>/reflect-3_attempt_01/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_02/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_03/SKILL.md
```

The three attempt skills for the same source/mode must be independent. If any
required skill is missing, stop and report the missing artifact instead of
regenerating it.

## 4. Run Cross-Task Solvers

For every mode, off-diagonal source/target pair, test task, and attempt, create
a fresh solver directory:

```text
runs/<mode>/<source_task_group_id>__to__<target_task_group_id>/test_001/attempt_01/
```

Each attempt directory should contain only:

- The current target test task `input/`.
- `environment_access.md`, containing the target task group's container-visible
  environment entrypoint, credentials, allowed endpoints, and POST request
  contracts defined above.
- The complete skill package directory matching the current source task group,
  mode, and attempt number, staged as `skill/` with `skill/SKILL.md` as its
  entry file.

Do not stage:

- `env/`
- train tasks
- source `output/answer.json`
- test standard answers
- test notes
- evaluator files
- run files from other attempts

Solver output:

```text
answer.json
run_metadata.yaml
```

Every solver attempt must be completed by a clean-context Dockerized Codex run
using the configured model and reasoning effort. The main agent stages the
attempt directory, launches the isolated solver run, then scores and aggregates
the result after the solver writes `answer.json`.

Use the fixed solver prompt in `guides/agent_prompts.md` without additions.

## 5. Score

After each solver finishes, the main agent calls the target test task evaluator
and saves:

```text
runs/<mode>/<source>__to__<target>/test_001/attempt_01/score.yaml
```

Each attempt must have a unique `eval_attempt_id`:

```text
transfer__<mode>__<source>__to__<target>__<test_id>__attempt_<nn>__<timestamp>
```

After scoring, keep the named solver container stopped and read the solver's raw
Codex session trace from its container-local `CODEX_HOME`. Use `docker cp` to
extract only the exact file, or a temporary `sessions/` subtree under
`scratch/trace_extract/<run_id>/` when discovery is necessary. Verify it matches
the run, and copy only that file to:

```text
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/rollout-*.jsonl
```

Confirm the trace uses the expected attempt directory and contains the matching
`eval_attempt_id`. This raw session file is the primary trace. Record the raw
session trace path and any trace-derived token fields in `run_metadata.yaml`,
verify them, then delete the temporary extraction directory and stopped
container. Do not preserve the full home or stdout. If the raw session trace is
missing or ambiguous, set the trace path to `null`, record the reason, clean up,
and rerun with a new run ID.

Token usage may be recorded in `run_metadata.yaml`, but the heatmap uses scores
by default.

## 6. Aggregate And Render

Write one cell report for each off-diagonal `<mode>/<source>__to__<target>`:

```text
report/cells/<mode>/<source>__to__<target>.yaml
```

After all 12 cell reports are complete, run:

```bash
python3 scripts/build_heatmaps.py
```

The script creates:

```text
report/matrix.yaml
report/matrix.json
heatmaps/data/matrices.json
heatmaps/data/fewshot_matrix.csv
heatmaps/data/reflect-3_matrix.csv
heatmaps/index.html
```

Open `heatmaps/index.html` to view the two 3x3 heatmaps.

## 7. Contamination Handling

If a solver/test attempt accesses forbidden material, stop using that result:

1. Write the contamination reason in that attempt directory.
2. Do not score or aggregate that attempt.
3. Rerun the affected test in a new clean attempt directory.
4. Record the issue in the cell report's `notes` or `excluded_attempts`.

Existing skill package directories are allowed artifacts for the matching source/mode/attempt.
Test solvers must not directly read source or target train tasks, standard
answers, notes, evaluators, env source files, or other run directories.
