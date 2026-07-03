# Metric And Scoring

主评估指标是 `acc@3` 和 population `std@3`。

## 单次运行

一次运行指一个干净上下文的 solver subagent 在一种评估条件下完成一个 test task。

每次运行应产出：

```text
runs/<condition>/<task_id>/attempt_<nn>/answer.json
runs/<condition>/<task_id>/attempt_<nn>/score.yaml
runs/<condition>/<task_id>/attempt_<nn>/run_metadata.yaml
```

`answer.json` 是 solver 的最终答案。`score.yaml` 由主 agent 调用 task evaluator 后生成。

`run_metadata.yaml` 记录唯一 attempt ID、trace 来源、token 用量和 solver turn count。token 值应尽量来自 Codex session trace，而不是让 agent 在 prompt 内手动统计。

推荐格式：

```yaml
eval_attempt_id: <task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
condition: <condition>
task_id: <task_id>
attempt: <int>
model: <model_name_or_config>

trace:
  session_file: <path to rollout-*.jsonl or null>
  copied_trace_file: <path under original_traces/ or null>
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
turn_count:
  source: codex_session_trace
  assistant_turns: <int>
```

如果 trace 不能被唯一匹配，应在 `match_status` 中写入 `missing` 或 `ambiguous`，将 `copied_trace_file` 和对应 token/turn 字段设为 `null`，不要手动估算。

## acc@3

同一个 test task 在同一种条件下运行 3 次独立 attempts。

```text
task acc@3 = (attempt_01_score + attempt_02_score + attempt_03_score) / 3
```

某一条件的整体 `acc@3` 是 5 个 test-task `acc@3` 的平均值。

## std@3

`std@3` 用来记录同一组 3 次 attempts 的分数稳定性，使用 population standard
deviation。对单个 test task：

```text
task std@3 = sqrt(((s1 - task_acc@3)^2 + (s2 - task_acc@3)^2 + (s3 - task_acc@3)^2) / 3)
```

一个条件的整体 `std@3` 使用和 `acc@3` 一致的聚合形状：先计算每个 test
task 的 `std@3`，再对 5 个 test-task `std@3` 取平均。

```text
overall std@3 = (test_001_std@3 + test_002_std@3 + test_003_std@3 + test_004_std@3 + test_005_std@3) / 5
```


## rounds@3 / turn count

`rounds_avg_3` 统计 solver 的 assistant/model-response turns。Codex 和 Claude Code 从匹配到的 solver trace 中统计 assistant 响应；如果一轮响应被拆成多条 content-block 记录，应按响应或 message id 去重。Panofy 从正式 scored `predict()` trace 的 history 中统计 assistant 消息。不要统计 main agent、skill generation、evaluator、环境检查或被替换的失败 attempt。

```text
task rounds@3 = (attempt_01_turns + attempt_02_turns + attempt_03_turns) / 3
overall rounds@3 = (test_001_rounds@3 + test_002_rounds@3 + test_003_rounds@3 + test_004_rounds@3 + test_005_rounds@3) / 5
```

如果某个正式 attempt 的 trace 无法匹配，turn count 写 `null`，并在 run record 中保留原因；不要手动估算。

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

如果重试后仍无法获得有效分数，应停止评估并报告问题。不要把失败 attempt 记为 `0`，也不要丢弃失败 attempt 后继续计算 `acc@3`。

## 聚合要求

所有 `score.yaml` 准备完成后，主 agent 应检查四种条件、5 个 test tasks、每个 task 3 次运行是否完整。然后计算每个 task 的 `acc@3` 和 `std@3`、整体 `acc@3` 和 `std@3`，以及 `fewshot`、`self` 和 `reflect-3` 相对 `base` 的提升。

主 agent 还应从每个 `run_metadata.yaml` 中聚合平均 cached/input/output tokens 和 solver turns，先按每个 test task 的 3 次 attempts 求平均，再按条件下的 5 个 test tasks 求平均。

这些效率指标只统计 test solver subagents 写答案的过程。不包括 skill 生成、远程环境检查、evaluator 执行或主 agent 汇总。它们不能替代 `acc@3`，但应出现在最终报告中，用于比较不同 skill 条件下的效率。

评估 agent 可以根据当前 task group 的 evaluator 形态，在 `scratch/` 中编写临时聚合或检查代码。
