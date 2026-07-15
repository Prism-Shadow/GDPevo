# GDPevo Cross-Task Skill Transfer Workspace

This workspace runs a Codex-only 3x3 skill-transfer heatmap experiment.

The goal is not to rerun the full benchmark. Instead, it fixes three
representative task groups and compares how `fewshot` and `reflect-3` skills
previously generated from one task group transfer to the other two domains.

## Core Matrix

Both heatmaps use the same row and column labels:

```text
CRM      task_group_002
ERP      task_group_006
Finance  task_group_010
```

- Row: the task group used to generate the skill.
- Column: the target task group used for testing.
- Cell: `acc@3` from solving the target task group's 5 test tasks with the 3
  independently generated skills from the row task group.
- Diagonal cells where source and target are the same task group are not run.

This workspace produces exactly two heatmaps:

```text
fewshot
reflect-3
```

Do not run `base`, `self`, or any non-Codex harness in this workspace.

## Directories

| Path | Purpose |
| --- | --- |
| `CODEX_ORCHESTRATOR.md` | Codex orchestration, Docker isolation, `codex exec` command shape, and trace preservation |
| `RUN_SCOPE.md` | Fixed scope for this 3x3 transfer experiment |
| `heatmap_scope.json` | Machine-readable task group, mode, and label definition |
| `guides/` | Workflow, fixed solver prompt, skill modes, scoring, and report format |
| `task_groups/` | The 3 representative task groups for this transfer run |
| `skills/` | Existing `fewshot` and `reflect-3` skills by source task group |
| `runs/` | Isolated solver records for each mode/source/target/test/attempt |
| `original_traces/` | Raw Codex session trace files copied after each solver attempt |
| `report/cells/` | Per-cell structured scoring reports |
| `heatmaps/` | Aggregated matrix data and HTML render page |
| `scripts/` | Aggregation and heatmap HTML builder |

## Launch Prompt

```text
Read README.md, CODEX_ORCHESTRATOR.md, RUN_SCOPE.md, and guides/. Run the Codex-only 3x3 cross-task
skill transfer experiment for fewshot and reflect-3. Use three independent
pre-generated skills per source task group for @3. Keep every solver attempt isolated under
runs/. Write per-cell reports under report/cells/, then build the two heatmaps
under heatmaps/. Copy each matched raw Codex trace into original_traces/.
Model: GPT-5.5, reasoning_effort: xhigh.
```

## Environment

Start each task-group environment on the orchestration host with
`TASK_ENV_BIND=0.0.0.0` and `TASK_ENV_PORT` set to `9000 + the numeric task-group id`. Set each task group's
`.env` URL to `http://host.docker.internal:<TASK_ENV_PORT>/`, and pass
`--add-host=host.docker.internal:host-gateway` to every solver container. Do not
regenerate skills in this workspace. Solver runs must not enter, list, read, or
mount `task_groups/*/env/`; they may only use the container-visible environment
entrypoint staged by the main agent.

## Isolated Solver Runs

When a user asks you to run this workspace, that request is permission for Codex
to orchestrate the experiment and launch Dockerized Codex solver runs with
`codex exec`. Use clean, isolated Docker runs for all test attempts. If the
required number of runs exceeds practical concurrency, run them in batches until
all required attempts are complete.

Use the model configuration in `heatmap_scope.json` unless the user explicitly
overrides it:

```text
model: GPT-5.5
reasoning_effort: xhigh
```

Do not reduce the attempt count, merge multiple test tasks into one solver run,
or solve test tasks directly as the main agent.

Use the command shape in `CODEX_ORCHESTRATOR.md`, including the per-attempt
runtime-only `CODEX_HOME=/codex_home`. `CODEX_HOME` is set only when launching
the solver process and is not a task `.env` setting. Do not use `codex exec
--ephemeral` for formal attempts. Use the exact prompt in
`guides/agent_prompts.md`; replace only its declared placeholders.

## Outputs

The completed workspace should contain at least:

```text
report/cells/fewshot/<source>__to__<target>.yaml
report/cells/reflect-3/<source>__to__<target>.yaml
report/matrix.yaml
report/matrix.json
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/
heatmaps/data/fewshot_matrix.csv
heatmaps/data/reflect-3_matrix.csv
heatmaps/data/matrices.json
heatmaps/index.html
```

Build the aggregate reports and HTML page with:

```bash
python3 scripts/build_heatmaps.py
```

Open `heatmaps/index.html` to view the two 3x3 heatmaps.
