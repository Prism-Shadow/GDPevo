# Evaluation Workflow

This file explains how the Codex main evaluation orchestrator should run one
complete Claude Code evaluation with `GLM-5.2`: Claude Code uses `xhigh` effort,
and the GLM model setting reported for the released run is `max`.

The evaluation now uses a remote task environment and four conditions:

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
CLAUDE_CONFIG_DIR=/claude_config claude -p --permission-mode bypassPermissions --session-id "$CLAUDE_SESSION_ID" "$PROMPT"
```

`CLAUDE_CONFIG_DIR` is a runtime-only temporary environment variable for that
agent process, not a task `.env` setting. Do not use `--no-session-persistence`
for formal attempts.

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

## 2. Configure The Remote Environment

Load `.env`:

```text
GDPEVO_ENV_BASE_URL=<remote task environment>
GDPEVO_JUDGE_PATH=/api/judge
```

Do not start the local `task_group/env` service for Claude Code evaluation.
Confirm the remote environment health/index endpoint answers and record the URL
in `scratch/environment.md`.

Skill-generation and solver runs must not enter, list, or read `env/`. They may
use only the remote environment entrypoint staged by the main agent.

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

- `fewshot`: train inputs, train gold answers, remote environment entrypoint.
- `self`: train inputs and remote environment entrypoint; no train answers and
  no judge feedback.
- `reflect-3`: train inputs, remote environment entrypoint, and judge API
  instructions; no train answers.

For every skill-generation run, create a dedicated mounted Claude config
directory and unique session ID. Preserve the complete session trace under
`original_traces/skill_generation/<condition>/attempt_<nn>/` and write the
matching `scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml`.
Backfill its token buckets using the solver-trace deduplication rules, then
calculate cost with `metric_and_scoring.md`. Report this as evolve usage; do not
include it in solver efficiency metrics.

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
- `environment_access.md` with the remote environment URL.
- The matching skill for non-base modes.

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
Claude Code process from that attempt directory. Mount only the attempt
directory and the per-attempt Claude config directory used for
`CLAUDE_CONFIG_DIR`; do not mount the full workspace or task group.

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

Backfill token usage, solver turn count, and tool-call count from the raw Claude
Code session trace written into the attempt-mounted `CLAUDE_CONFIG_DIR`.
Deduplicate by `message.id`: keep input/cache buckets from any record and the
max `output_tokens` per message id, then sum across responses.

Claude Code session traces should be under:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
```

Record the raw session trace path in `run_metadata.yaml`. If the raw session
trace is missing, set the trace path to `null`, keep the token, turn, and
tool-call fields `null`, and report the trace issue.

After all runs complete, aggregate `acc@3`, population `std@3`, per-bucket tokens, and solver turn count and tool-call counts for all four
conditions. Efficiency metrics count only test solver answer writing: average
the 3 attempts for the same test task, then average the 5 test tasks. Do not
include skill generation, remote environment checks, evaluator execution, or
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
