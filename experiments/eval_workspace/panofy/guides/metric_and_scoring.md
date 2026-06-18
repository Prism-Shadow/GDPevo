# Metric And Scoring

The main evaluation metric is `avg@3`. Cost is reported alongside accuracy, in
Panofy's native units (points + a 3-bucket token usage), read straight from the
SDK (no transcript parsing).

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
`run_metadata.yaml` records the unique attempt id and the SDK-reported cost.

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
types, or enum spellings cost points at the evaluator.

## Cost Accounting (Panofy)

`predict_with_metadata()` returns, per run:

- `run.points_consumed` — the platform's billed **points**. This is the primary
  cost unit; aggregate and compare it across conditions.
- `run.usage` — a 3-bucket token usage: `cache_read`, `cache_write`,
  `output_token`. Record as `cache_read_tokens`, `cache_write_tokens`,
  `output_tokens`.

Panofy exposes no separate uncached-input bucket, so **points** is the headline
cost; the three token buckets are secondary. Values come from the SDK, never from
manual counting. Recommended `run_metadata.yaml`:

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
  points_consumed: <int>
token_usage:
  source: panofy_last_usage
  cache_read_tokens: <int>
  cache_write_tokens: <int>
  output_tokens: <int>
  points_consumed: <int>
```

## avg@3

For the same test task under the same condition, run 3 independent attempts,
where `attempt_<nn>` is answered by the independently trained agent
`attempt_<nn>`:

```text
task avg@3 = (attempt_01_score + attempt_02_score + attempt_03_score) / 3
```

The overall `avg@3` for a condition is the average of the 5 test-task `avg@3`
values.

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
and do not drop it while still computing `avg@3`. If retries still cannot produce
a valid score, stop and report the issue.

## Aggregation Requirements

After all `score.yaml` files are ready, check that all three conditions, 5 test
tasks, and 3 runs per task are complete. Then compute per-task `avg@3`, overall
`avg@3`, and condition-to-condition improvements, plus the average points and
per-bucket tokens.

These efficiency metrics only count the **test-task `predict()`** work. They do
not include training (the evolution step), environment startup, or
evaluator execution. They aggregate the same way as `avg@3`: average the 3
attempts for one test task, then average the 5 test tasks. Temporary aggregation
code may live under `scratch/`.
