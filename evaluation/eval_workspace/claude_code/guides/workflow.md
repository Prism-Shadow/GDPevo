# Evaluation Workflow

This file explains how the main evaluation agent should run one complete Claude
Code evaluation.

The evaluation now uses a remote task environment and four conditions:

```text
base
fewshot
self
reflect-3
```

When a user asks you to run evaluation in this workspace, that request is
permission to use Claude Code subagents. Keep every skill-generation and solver
run in a clean, dedicated directory, and restrict each subagent to that
directory.

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

Skill-generation and solver subagents must not enter, list, or read `env/`.
They may use only the remote environment entrypoint staged by the main agent.

The judge endpoint is train-only. Only reflect skill-generation subagents should
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
  instructions; no train answers. Run exactly 3 epochs over the five train tasks,
  submit each candidate to the judge, and distill the final skill from the
  accumulated feedback.

Skill-generation token usage is not included in solver efficiency metrics.

## 4. Run Test Solvers

Run every condition, every test task, and every attempt independently:

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

Do not stage `env/`, train tasks, test answers, task notes, evaluator files,
other test tasks, generated skills from other attempts, prior runs, or judge
instructions for test solvers.

The solver writes `answer.json` in its own attempt directory.

## 5. Score And Aggregate

After each solver writes `answer.json`, call the current test task's
`eval/eval.sh` with the prediction path and save `score.yaml`.

Every solver attempt must have a unique `eval_attempt_id`:

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

The ID must appear in the solver prompt, attempt directory, and
`run_metadata.yaml`.

Backfill token usage from the matched Claude Code subagent transcript. Deduplicate
by `message.id`: keep input/cache buckets from any record and the max
`output_tokens` per message id, then sum across responses.

After all runs complete, aggregate `acc@3`, per-bucket tokens, and `cost_usd` for
all four conditions. Efficiency metrics count only test solver answer writing:
average the 3 attempts for the same test task, then average the 5 test tasks. Do
not include skill generation, remote environment checks, evaluator execution, or
main-agent summarization.

## 6. Interpret Results

In the report, explain:

- Overall `acc@3` for all four conditions.
- Improvement from `fewshot`, `self`, and `reflect-3` over `base`.
- Which test tasks improved clearly and which did not.
- Any environment instability, output-schema friction, evaluator issue, or
  suspicious leakage risk.
