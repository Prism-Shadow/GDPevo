# 指标与打分

主指标是 `acc@3`。成本与准确率一并报告，但用 Panofy 的原生单位（points + 三桶 token），直接从 SDK 读取（无需解析 transcript）。

## 单次运行

一次单次运行 = 一个训练好的 agent 在某条件下对一个 test task 做一次 `predict()`。

每次运行应产出：

```text
runs/<condition>/<task_id>/attempt_<nn>/func_input.json
runs/<condition>/<task_id>/attempt_<nn>/answer.json
runs/<condition>/<task_id>/attempt_<nn>/score.yaml
runs/<condition>/<task_id>/attempt_<nn>/run_metadata.yaml
```

`func_input.json` 是发给 `predict()` 的确切内容。`answer.json` 是解析后的 `FUNC_OUTPUT`。`score.yaml` 在运行 task evaluator 后写出。`run_metadata.yaml` 记录唯一 attempt id 和 SDK 报告的成本。

## 打分

用该 task 的 **`eval/eval.sh`**、把 prediction 路径作为 `$1` 传入来打分：

```bash
bash task_group/<id>/test_tasks/00N/eval/eval.sh <answer.json 的绝对路径>
```

`eval.sh` 是每个 task 都有的唯一入口；它会路由到该 task 所用的 evaluator（`evaluate.py` / `eval.py` / `evaluator.py` / rubric），并打印含 `total_score`（已归一）的 JSON 对象。若只有 `earned_score` / `max_score`，分数取 `earned / max`。结果钳到 `[0, 1]`。不要直接调用某个具体 evaluator 文件——命名因 task 而异，而且有的需要 `eval.sh` 已经补上的额外参数。

agent 必须返回严格匹配 `answer_template` 的 JSON——键、类型或枚举拼写错了，会在 evaluator 处丢分。

## 成本计量（Panofy）

`predict_with_metadata()` 每次运行返回：

- `run.points_consumed` —— 平台计费的 **points**。这是主成本单位；按条件聚合和对比它。
- `run.usage` —— 三桶 token：`cache_read`、`cache_write`、`output_token`。记为 `cache_read_tokens`、`cache_write_tokens`、`output_tokens`。

Panofy 没有单独的「未缓存 input」桶，所以 **points** 是头条成本；三桶 token 是次要。数值来自 SDK，绝不手数。建议的 `run_metadata.yaml`：

```yaml
eval_attempt_id: <task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
condition: <condition>
task_id: <task_id>
attempt: <int>
agent_id: <训练好的 agent id>
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

## acc@3

同一 test task、同一条件下跑 3 次独立 attempt，其中 `attempt_<nn>` 由独立训练的 agent `attempt_<nn>` 作答：

```text
task acc@3 = (attempt_01_score + attempt_02_score + attempt_03_score) / 3
```

一个条件的整体 `acc@3` 是 5 个 test-task `acc@3` 的平均。

## 分数范围

所有分数归一到 `[0, 1]`。若 evaluator 输出非归一分数，找 `earned / max` 或等价字段。若无法确定归一分数，把该次运行记为失败；不要手动猜分。

## 失败处理

以下情况记为失败并在报告中说明：

- `predict()` 抛错（`FAIL_AT_PLAN`、`FAIL_AT_ANSWER`、超时等）。
- agent 返回无法解析的 `answer.json`。
- evaluator 失败、超时，或返回不了 `[0, 1]` 分。
- 远程环境不可用，导致 agent 无法作答。

失败后重试，直到拿到一次有效可打分的 attempt；把失败记录保留在 attempt 目录。不要把失败 attempt 记 `0` 分，也不要丢掉它继续算 `acc@3`。如果重试仍拿不到有效分，停下并报告问题。

## 聚合要求

所有 `score.yaml` 就绪后，检查三种条件、5 个 test tasks、每个 task 3 次运行是否齐全。然后计算每个 task 的 `acc@3`、整体 `acc@3`、条件间提升，以及平均 points 和各桶 token。

这些效率指标只统计 **test-task 的 `predict()`** 工作，不含训练（进化步骤）、环境启动或 evaluator 执行。聚合方式同 `acc@3`：先对同一 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。临时聚合代码可放 `scratch/`。
