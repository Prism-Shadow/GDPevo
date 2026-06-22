# Evaluation Workflow

This file explains how the main evaluation agent should run one complete
evaluation on the Panofy platform.

The solver is a **trained Panofy agent reached over the SDK**. Drive the
evaluation by calling the SDK (`train`, `predict`) and each task's official
`eval/eval.sh`. Each `predict()` is already an isolated function-mode run that
sees only its own `FUNC_INPUT`, so there are no subagents to stage or restrict.
Write small SDK / aggregation scripts under `scratch/` as needed, and run them
in the `uv`-managed environment described in `README.md`.

The agent **evolves during training**: the training instruction tells it to
learn from the train tasks and improve on this task family. A condition is a
particular set of training materials plus a training instruction.

## 1. Prepare The Task Group

This workspace evaluates one task group at a time:

```text
task_group/<task_group_id>/
```

The task group must have passed quality review.

## 2. Check The Workspace

Confirm the workspace contains exactly one task group and that it includes:

- 5 train tasks.
- 5 test tasks.
- A task-group-level shared environment (`env/`).
- Official input, standard answer, and evaluator (`eval/eval.sh`) for each task.

Also confirm Panofy connectivity with the run-time base URL and API key by
listing agents (`panofy.agents.list()`; this is not a test-task `predict()` run).

## 3. Point At The Remote Environment

Panofy agents run remotely and **can make outbound HTTP requests**, but they
cannot reach a local server. The task environment must therefore be served at a
remote URL supplied through `.env`:

```text
PANOFY_ENV_BASE_URL=<remote task-group environment URL>
PANOFY_JUDGE_PATH=/api/judge
```

Inject the env base URL into every `FUNC_INPUT` as `api_base_url`; the agent
issues the public GET calls named in each task prompt against it. Before
running, confirm that the env health / index endpoint answers with HTTP 200 and
that exposed endpoints return the same public projection as the local
`task_group/env` server. Hidden construction fields must not be exposed.

Only reflect training receives the judge endpoint. The judge endpoint must never
be placed in test `FUNC_INPUT`, and test solvers must not use it.

## 4. Train The Agents

Train **3 independent agents for each condition**:

```text
base
fewshot
self
reflect-3
```

`attempt_<nn>` maps to one trained agent, so acc@3 captures training variance.
What differs per condition is only the training materials and training
instruction; see `evolve_modes.md`.

Stage each condition's materials into a dedicated directory, for example:

```text
scratch/materials/base/attempt_01/
scratch/materials/fewshot/attempt_01/
scratch/materials/self/attempt_01/
scratch/materials/reflect-3/attempt_03/
```

Training material boundaries:

- `base`: no task-specific train material beyond the generic instruction and
  remote environment URL.
- `fewshot`: train inputs plus train gold answers.
- `self`: train inputs plus remote environment URL; no train answers and no
  judge feedback.
- `reflect-3`: train inputs plus remote environment URL and judge API
  instructions; no train answers. Run exactly 3 epochs over the five train tasks.

For reflect training, the agent first answers a train task from the visible
input, then calls:

```text
POST {PANOFY_ENV_BASE_URL}{PANOFY_JUDGE_PATH}
```

with:

```json
{"task_id": "train_001", "answer": <candidate answer JSON>}
```

The response contains only score / correctness feedback. It does not expose
gold answers or evaluator details.

Do not put any test task, test answer, test note, or evaluator into training
materials. Use the SDK's async one-shot `train()` for each `(condition,
attempt)`, record each returned `agent_id` in `agents/registry.json`, and do not
count training cost in solver efficiency metrics.

## 5. Run Test Experiments

For every condition, run each test task independently 3 times. The solver for
`attempt_<nn>` is the agent trained for the same condition and attempt number.
Each `predict()` receives only the official test `FUNC_INPUT`:

```text
task_id
prompt
api_base_url
answer_template
```

The test `FUNC_INPUT` is identical across conditions; only the trained agent
differs. Never include test gold answers, notes, evaluator details, train
materials, or judge endpoint instructions in test `FUNC_INPUT`.

Run one question per call and run sequentially: answer exactly one test task per
`predict()` call, and run the 5 test tasks one at a time. Do not put multiple
tasks in a single input and do not fire predicts concurrently.

Recommended record layout:

```text
runs/<condition>/test_001/attempt_01/func_input.json
runs/<condition>/test_001/attempt_01/answer.json
runs/<condition>/test_001/attempt_01/score.yaml
runs/<condition>/test_001/attempt_01/run_metadata.yaml
```

Call `predict(func_input)` with `resolve_files=False` and `output_dir=None`.
Use `predict_with_metadata()` to capture `run.usage`; derive `cost_usd` from the
token buckets and configured model price table. `answer.json` is the parsed
`FUNC_OUTPUT`.

## 6. Score And Aggregate

After each `predict()` writes `answer.json`, score it by running the task's
**`eval/eval.sh`** with the prediction path as `$1`. Read `total_score`
already in `[0,1]`; if needed, derive a normalized score from earned / max
fields. Write `score.yaml`.

Record token usage and derived `cost_usd` in `run_metadata.yaml` with a unique
`eval_attempt_id`:

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

After all `score.yaml` files exist, aggregate per-task `acc@3`, overall
`acc@3`, and average `cost_usd` / token buckets for each condition. Efficiency
metrics only count **test-task `predict()`** work; never include training,
remote environment checks, or evaluator execution. Aggregate the same way as
`acc@3`: average the 3 attempts for one test task, then average the 5 test
tasks. Write the final report to `report/<task_group_id>.yaml` per
`report_format.md`.

## 7. Interpret Results

In the report or accompanying notes, explain:

- Overall `acc@3` for all four conditions.
- Improvement from `fewshot`, `self`, and `reflect-3` over `base`.
- Which test tasks improved clearly and which did not.
- The USD price and token cost per condition.
- Any environment instability, output-schema friction, evaluator issue, or
  suspicious leakage risk.

## Failure Handling

Record as failures and explain in the report: `predict()` raises, the agent
returns no parseable `answer.json`, the evaluator fails, or no `[0,1]` score can
be determined. After a failure, retry until one valid scoreable attempt is
obtained, and preserve the failed record in the attempt directory. Do not score
a failed attempt as `0`, and do not drop it while still computing `acc@3`. If
retries still cannot produce a valid score, stop and report the issue.
