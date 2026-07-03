# Metric And Scoring

The main evaluation metrics are `acc@3` and population `std@3`. Efficiency
information is the SDK-reported 3-bucket token usage.

## Single Run

A single run means one `predict()` of one test task by one trained agent under
one condition.

Each run should produce:

```text
runs/<condition>/<task_id>/attempt_<nn>/func_input.json
runs/<condition>/<task_id>/attempt_<nn>/answer.json
runs/<condition>/<task_id>/attempt_<nn>/score.yaml
runs/<condition>/<task_id>/attempt_<nn>/run_metadata.yaml
```

`func_input.json` is exactly what was sent to `predict()`. `answer.json` is the
parsed `FUNC_OUTPUT`. `score.yaml` is written after running the task evaluator.
`run_metadata.yaml` records the unique attempt id, SDK-reported token usage,
and Panofy agent / run identifiers.

## Scoring

Score by running the task's **`eval/eval.sh`** with the prediction path as `$1`:

```bash
bash task_group/<id>/test_tasks/00N/eval/eval.sh <abs-path-to-answer.json>
```

`eval.sh` is the one entrypoint present on every task; it routes to whatever
evaluator that task uses (`evaluate.py` / `eval.py` / `evaluator.py` / a rubric)
and prints a JSON object with `total_score` (already normalised). If only
`earned_score` / `max_score` are present, the score is `earned / max`. Clamp to
`[0, 1]`. Do not invoke a specific evaluator file directly — names vary by task,
and some take extra arguments that `eval.sh` already supplies.

The agent must return JSON matching `answer_template` exactly — wrong keys,
types, or enum spellings lose evaluator score.

## Token Accounting (Panofy)

`predict_with_metadata()` returns, per run:

- `run.usage` — a 3-bucket token usage: `cache_read`, `cache_write`,
  `output_token`. Record as `cache_read_tokens`, `cache_write_tokens`,
  `output_tokens`.

Panofy exposes no separate uncached-input bucket. Record the three token buckets
from the SDK; if any bucket is unavailable, write `null` and preserve the reason
in the run record. Token values come from the SDK, never from manual counting.
Recommended `run_metadata.yaml`:

```yaml
eval_attempt_id: <task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
condition: <condition>
task_id: <task_id>
attempt: <int>
agent_id: <trained agent id>
model_id: <PANOFY_PRO | PANOFY_AIR>
run:
  run_id: <sdk run id>
  panofy_task_id: <sdk task id>
  status: COMPLETED
token_usage:
  source: panofy_last_usage
  cache_read_tokens: <int>
  cache_write_tokens: <int>
  output_tokens: <int>
```

## acc@3

For the same test task under the same condition, run 3 independent attempts,
where `attempt_<nn>` is answered by the independently trained agent
`attempt_<nn>`:

```text
task acc@3 = (attempt_01_score + attempt_02_score + attempt_03_score) / 3
```

The overall `acc@3` for a condition is the average of the 5 test-task `acc@3`
values.

## std@3

`std@3` records score stability across the same 3 attempts and uses
population standard deviation. For one test task:

```text
task std@3 = sqrt(((s1 - task_acc@3)^2 + (s2 - task_acc@3)^2 + (s3 - task_acc@3)^2) / 3)
```

The overall `std@3` for a condition uses the same aggregation shape as
`acc@3`: first compute each test task's `std@3`, then average the 5 test-task
`std@3` values.

```text
overall std@3 = (test_001_std@3 + test_002_std@3 + test_003_std@3 + test_004_std@3 + test_005_std@3) / 5
```


## rounds@3 / turn count

`rounds_avg_3` counts solver assistant/model-response turns. During evaluation,
record the Panofy `agent_id`, SDK run id, task id, and SDK usage metadata; leave
turn counts as `null` unless a packaged service log has already been supplied
to the workspace. Panofy service logs are archived after the experiment and can
be used to backfill `rounds_avg_3`.

```text
task rounds@3 = (attempt_01_turns + attempt_02_turns + attempt_03_turns) / 3
overall rounds@3 = (test_001_rounds@3 + test_002_rounds@3 + test_003_rounds@3 + test_004_rounds@3 + test_005_rounds@3) / 5
```

If the packaged service log for a formal attempt is unavailable, write the turn
count as `null`; do not estimate it manually.

## Score Range

All scores are normalised to `[0, 1]`. If an evaluator outputs a non-normalised
score, find `earned / max` or an equivalent field. If no normalised score can be
determined, mark that run as failed; do not guess a score manually.

## Failure Handling

Record as a failure and explain in the report:

- `predict()` raises (`FAIL_AT_PLAN`, `FAIL_AT_ANSWER`, timeout, etc.).
- The agent returns no parseable `answer.json`.
- The evaluator fails, times out, or returns no `[0, 1]` score.
- The remote environment is unavailable and prevents the agent from answering.

After a failure, retry until one valid scoreable attempt is obtained; preserve
the failed record in the attempt directory. Do not score a failed attempt as `0`,
and do not drop it while still computing `acc@3`. If retries still cannot produce
a valid score, stop and report the issue.

## Aggregation Requirements

After all `score.yaml` files are ready, check that all four conditions, 5 test
tasks, and 3 runs per task are complete. Then compute per-task `acc@3` and
`std@3`, overall `acc@3` and `std@3`, improvements from `fewshot`, `self`, and
`reflect-3` over `base`, plus average per-bucket tokens. Include solver turns
only when packaged service logs are available.

These efficiency metrics only count the **test-task `predict()`** work. They do
not include training (the evolution step), remote environment checks, or
evaluator execution. Token metrics come from the SDK during evaluation. Turn
metrics, when available after log archival, aggregate the same way as `acc@3`:
average the 3 attempts for one test task, then average the 5 test tasks.
Temporary aggregation code may live under `scratch/`.
