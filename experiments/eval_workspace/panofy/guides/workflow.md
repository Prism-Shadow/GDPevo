# Evaluation Workflow

This file explains how the main evaluation agent should run one complete
evaluation, on the Panofy platform.

The solver here is a **trained Panofy agent reached over the SDK**. You drive
the evaluation by calling the SDK directly
(`train`, `predict`) and running each task's official `eval/eval.sh`. Each
`predict()` is already an isolated function-mode run that sees only its own
`FUNC_INPUT`, so there are no subagents to stage or restrict. Write small,
throwaway SDK / aggregation scripts under `scratch/` as needed, and run them in a
`uv`-managed environment (see Setup in `README.md`). The `panofy` package's own
README documents the exact call signatures.

The agent **evolves during training**: the training instruction tells it to
**evolve from the train tasks** — learn from them and get better at this family
of tasks. Nothing is extracted; the evolution is baked into the trained agent.
So a condition is just a particular set of training materials + instruction.

## 1. Prepare The Task Group

This workspace evaluates one task group at a time, located at:

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

Also confirm Panofy connectivity with the run-time base URL + API key by listing
agents (`panofy.agents.list()`; this spends no points).

## 3. Point At The Remote Environment

The trained agent runs remotely and **can make outbound HTTP requests**, but it
cannot reach a local server. The task environment is therefore served at a
**remote URL supplied in the launch prompt**. You inject that URL into every
`FUNC_INPUT` as `api_base_url`; the agent issues the GET calls named in each
task prompt against it.

Before running, confirm:

- The env's health / index endpoint answers with HTTP 200. The path is not
  uniform across task groups — it may be `/health`, `/api/health`, or just `/`
  (the HTML index); check `task_group/env` to see which one this group uses.
- The exposed endpoints return the same **public projection** as the local
  `task_group/env` server — hidden / construction fields must not be exposed.

Record the env URL and any restart notes in `scratch/`. Do not enter or expose
hidden `env/` fields to the agent; it only ever sees the remote URL.

## 4. Train The Agents

Train **3 independent agents for each condition** — `attempt_<nn>` → one agent —
so acc@3 captures training variance. What differs per condition is only the
training materials and the training instruction (see `evolve_modes.md`).

Stage each condition's materials into a dedicated directory, for example:

```text
scratch/materials/base/attempt_01/
scratch/materials/demo/attempt_01/
scratch/materials/reflect/attempt_01/
```

For `reflect`, the materials still include the train gold answers (the
agent needs them to reflect); the difference is the instruction, which requests
the blind-attempt / compare / reflect loop. Then train each (condition, attempt)
with the SDK's **async** one-shot `train()` (wrap it in `asyncio.run`); it creates
the agent, uploads the materials, trains to completion, and returns the new
`agent_id`. Record each `agent_id` in `agents/registry.json`. Training cost is
**not** counted in solver efficiency metrics.

Do not put any test task, test answer, test note, or evaluator into training
materials. Only train inputs and train gold answers are allowed.

## 5. Run The Base Experiment

Run each test task independently 3 times. The solver for `attempt_<nn>` is the
`base` agent trained as `attempt_<nn>`. Each `predict()` receives only the
official test `FUNC_INPUT` — `task_id`, `prompt`, `api_base_url`,
`answer_template` — and the allowed remote env URL.

**One question per call, run sequentially (applies to all three conditions):**
answer exactly one test task per `predict()` call, and run the 5 test tasks one
at a time — do not put multiple tasks in a single input, and do not fire
predicts concurrently. The platform caps concurrent tasks, so overlapping runs
fail.

Recommended record layout:

```text
runs/base/test_001/attempt_01/func_input.json
runs/base/test_001/attempt_01/answer.json
runs/base/test_001/attempt_01/score.yaml
runs/base/test_001/attempt_01/run_metadata.yaml
```

Do not place gold answers, notes, or evaluator details into any test
`FUNC_INPUT`. Answer with a `Panofy(base_url, api_key, agent_id)` client: call
`predict(func_input)` (the FUNC_INPUT as a single positional dict) with
`resolve_files=False` and `output_dir=None`, since the inputs are plain JSON, not
files; use `predict_with_metadata()` to also capture `run.usage` and
`run.points_consumed`. `answer.json` is the parsed `FUNC_OUTPUT` it returns.

## 6. Run The Demo Experiment

Run each test task independently 3 times. `attempt_<nn>` is answered by the
`demo` agent trained as `attempt_<nn>`:

```text
attempt_01 -> demo agent attempt_01
attempt_02 -> demo agent attempt_02
attempt_03 -> demo agent attempt_03
```

The test `FUNC_INPUT` is identical to the base condition; only the agent
differs (it was trained on the 5 solved train tasks). Record under
`runs/demo/test_00N/attempt_0M/`.

## 7. Run The Reflect Experiment

Same as §6, with the `reflect` agents (trained with the reflection
instruction). Record under `runs/reflect/test_00N/attempt_0M/`.

## 8. Score And Aggregate

After each `predict()` writes `answer.json`, score it by running the task's
**`eval/eval.sh`** with the prediction path as `$1` — that one entrypoint is
present on every task and routes to whatever evaluator it uses
(`evaluate.py` / `eval.py` / `evaluator.py` / a rubric). Read `total_score`
(already in `[0,1]`) and write `score.yaml`.

Token usage and points come straight from the SDK — no transcript parsing.
`predict_with_metadata()` returns `run.points_consumed` and `run.usage`
(`cache_read`, `cache_write`, `output_token`). Record them in
`run_metadata.yaml` with a unique `eval_attempt_id`:

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

After all `score.yaml` files exist, aggregate per-task `acc@3`, overall `acc@3`,
and the average points / per-bucket tokens for each condition. These efficiency
metrics only count **test-task `predict()`** work — never training (the
evolution step), environment startup, or evaluator execution. Aggregate
the same way as `acc@3`: average the 3 attempts for one test task, then average
the 5 test tasks. Put any temporary aggregation code under `scratch/`. Write the
final report to `report/<task_group_id>.yaml` per `report_format.md`.

## 9. Interpret Results

In the report (or accompanying notes), explain:

- Overall `acc@3` for all three conditions.
- Improvement from each evolve condition over base.
- Whether reflect outperforms demo.
- Which test tasks improved clearly and which did not.
- The point / token cost per condition — does training buy accuracy while
  spending fewer points, or more?
- Any environment instability, output-schema friction (the agent must return
  JSON matching `answer_template` exactly), evaluator issue, or suspicious
  leakage risk.

## Failure Handling

Record as failures and explain in the report: `predict()` raises, the agent
returns no parseable `answer.json`, or the evaluator fails / returns no `[0,1]`
score. After a failure, retry until one valid scoreable attempt is obtained, and
preserve the failed record in the attempt directory. Do not score a failed
attempt as `0`, and do not drop it while still computing `acc@3`. If retries
still cannot produce a valid score, stop and report the issue.
