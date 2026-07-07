# Evaluation Workflow

This file explains how the main evaluation agent should run one complete Claude
Code evaluation for Kimi 2.6 through SiliconFlow.

The evaluation now uses a remote task environment and four conditions:

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

Run `/status` in Claude Code and record the observed model/effort in
`scratch/environment.md`. Skill-generation and solver subagents inherit the
main session configuration; do not pass a different model to subagents.

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

Some official task inputs were authored for the local-environment harness and
may mention localhost, `127.0.0.1`, or `env/setup.sh`. Do not modify official
task input files, but treat those local references as obsolete for this Kimi
evaluation. Every staged skill-generation and solver directory must include an
`environment_access.md` file that states:

```text
Use only GDPEVO_ENV_BASE_URL=<remote URL from .env>.
Do not start task_group/env, run env/setup.sh, or use localhost/127.0.0.1
unless the remote URL itself explicitly points there.
If any task text mentions a local env URL, this environment_access.md overrides
that local reference.
```

Skill-generation and solver subagents must not enter, list, or read `env/`.
They may use only the remote environment entrypoint staged by the main agent.

The judge endpoint is train-only and valid only during reflect skill generation
on train tasks. It must not be staged to test solvers or written into generated
skills as a test-time tool. Only reflect skill-generation subagents should
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

Do not copy whole train task directories for skill generation. For each staged
train task, copy only:

- `input/`
- `output/answer.json` only when the current mode explicitly allows train gold
  answers.

Never stage `notes/`, `eval/`, `env/`, `test_tasks/`, task-group manifests
outside the staged inputs, or source files not explicitly allowed above.

Skill-generation token usage is not included in solver efficiency metrics.

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
- `environment_access.md` with the remote environment URL and the override
  notice for any stale local-env references in official task inputs.
- The matching skill for non-base modes.

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

Backfill token usage from the matched Claude Code subagent transcript. Deduplicate
by `message.id`: keep input/cache buckets from any record and the max
`output_tokens` per message id, then sum across responses. Count solver
assistant/model-response turns and assistant `tool_use` content blocks from the
same matched formal solver trace.

Claude Code subagent transcripts are usually under:

```text
~/.claude/projects/<project>/<session-id>/subagents/agent-<agent_id>.jsonl
```

After matching the transcript, copy or hard-link the raw `agent-*.jsonl` file
into:

```text
original_traces/<condition>/<task_id>/attempt_<nn>/
```

Record both the source transcript path and the copied workspace trace path in
`run_metadata.yaml`. If no unique transcript can be matched, set the copied
trace path to `null`, keep the token, turn, and tool-call fields `null`, and
report the trace issue.

After all runs complete, aggregate `acc@3`, population `std@3`, per-bucket
tokens, solver turn counts, and solver tool-call counts for all four
conditions. Efficiency metrics count only test solver answer writing: average
the 3 attempts for the same test task, then average the 5 test tasks. Do not
include skill generation, remote environment checks, evaluator execution, or
main-agent summarization. Temporary checking code, aggregation code, and
environment notes must be placed under `scratch/`, not in the workspace root.

Before marking the evaluation complete, check that each scored solver attempt
has a matched raw subagent transcript copied under `original_traces/` and that
the report token, turn-count, and tool-call fields were aggregated from those
copied traces. If any trace or efficiency field is missing, preserve the reason
in `run_metadata.yaml` and call it out in the final report.

## 6. Interpret Results

In the report, explain:

- Overall `acc@3` and population `std@3` for all four conditions.
- Improvement from `fewshot`, `self`, and `reflect-3` over `base`.
- Which test tasks improved clearly and which did not.
- Any environment instability, output-schema friction, evaluator issue, or
  suspicious leakage risk.
