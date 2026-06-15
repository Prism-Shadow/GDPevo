# Metric And Scoring

主评估指标是 `avg@3`。

## 单次运行

一次运行指一个干净上下文的 solver subagent 在一种评估条件下完成一个 test task。

每次运行应产出：

```text
runs/<condition>/<task_id>/attempt_<nn>/answer.json
runs/<condition>/<task_id>/attempt_<nn>/score.yaml
runs/<condition>/<task_id>/attempt_<nn>/run_metadata.yaml
```

`answer.json` 是 solver 的最终答案。`score.yaml` 由主 agent 调用 task evaluator 后生成。

`run_metadata.yaml` 记录唯一 attempt ID、trace 来源和 token 用量。token 值应尽量来自 Codex session trace，而不是让 agent 在 prompt 内手动统计。

推荐格式：

```yaml
eval_attempt_id: <task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
condition: <condition>
task_id: <task_id>
attempt: <int>
model: <model_name_or_config>

trace:
  session_file: <path to rollout-*.jsonl or null>
  session_id: <session_id>
  parent_thread_id: <parent_thread_id>
  agent_nickname: <agent_nickname>
  match_status: matched

token_usage:
  source: codex_session_trace
  input_tokens: <int>
  cached_input_tokens: <int>
  output_tokens: <int>
  reasoning_output_tokens: <int>
  total_tokens: <int>
```

如果 trace 不能被唯一匹配，应在 `match_status` 中写入 `missing` 或 `ambiguous`，将对应 token 字段设为 `null`，不要手动估算。

## avg@3

同一个 test task 在同一种条件下运行 3 次独立 attempts。

```text
task avg@3 = (attempt_01_score + attempt_02_score + attempt_03_score) / 3
```

某一条件的整体 `avg@3` 是 5 个 test-task `avg@3` 的平均值。

## 分数范围

所有分数都应归一化到 `[0, 1]`。

如果 evaluator 输出的是非归一化分数，主 agent 应找到 `earned / max` 或等价字段，并转换为归一化分数。如果无法确定归一化分数，应将该运行标记为失败，而不是手动猜测分数。

## 失败处理

以下情况应记录为失败，并在报告中解释：

- Solver 没有产出可解析的 `answer.json`。
- Evaluator 失败或超时。
- Evaluator 输出无法解析为 `[0, 1]` 分数。
- 环境不可用，导致 solver 无法完成任务。

失败后，主 agent 应重试，直到获得一次有效、可打分的 attempt。重试原因和失败记录应保留在对应 attempt 目录中。

如果重试后仍无法获得有效分数，应停止评估并报告问题。不要把失败 attempt 记为 `0`，也不要丢弃失败 attempt 后继续计算 `avg@3`。

## 聚合要求

所有 `score.yaml` 准备完成后，主 agent 应检查三种条件、5 个 test tasks、每个 task 3 次运行是否完整。然后计算每个 task 的 `avg@3`、整体 `avg@3`，以及条件之间的提升。

主 agent 还应从每个 `run_metadata.yaml` 中聚合平均 cached/input/output tokens，先按每个 test task 的 3 次 attempts 求平均，再按条件下的 5 个 test tasks 求平均。

这些效率指标只统计 test solver subagents 写答案的过程。不包括 skill 生成、环境启动、evaluator 执行或主 agent 汇总。它们不能替代 `avg@3`，但应出现在最终报告中，用于比较不同 skill 条件下的效率。

评估 agent 可以根据当前 task group 的 evaluator 形态，在 `scratch/` 中编写临时聚合或检查代码。
