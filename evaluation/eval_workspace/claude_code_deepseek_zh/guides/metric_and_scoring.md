# Metric And Scoring

主评估指标是 `acc@3`。

## 单次运行

一次运行指一个干净上下文的 solver subagent 在一种评估条件下完成一个 test task。

每次运行应产出：

```text
runs/<condition>/<task_id>/attempt_<nn>/answer.json
runs/<condition>/<task_id>/attempt_<nn>/score.yaml
runs/<condition>/<task_id>/attempt_<nn>/run_metadata.yaml
```

`answer.json` 是 solver 的最终答案。`score.yaml` 由主 agent 调用 task evaluator 后生成。

`run_metadata.yaml` 记录唯一 attempt ID、匹配到的 transcript 引用和 token 用量。token 值来自该 subagent 的 session transcript，而不是让 agent 在 prompt 内手动统计。

### Token 口径(务必看清，极易算错)

每个 solver subagent 有自己独立的 transcript：

```text
~/.claude/projects/<project>/<session-id>/subagents/agent-<agent_id>.jsonl
```

本 workspace 只用于 Claude Code + DeepSeek V4 Pro。效率指标的权威来源是 Claude Code subagent transcript，而不是 DeepSeek 原始 API response schema。当前观察到的 `deepseek-v4-pro` Claude Code transcript 会用 Claude Code 风格字段保存 usage：

- `input_tokens`：非缓存 input tokens
- `cache_creation_input_tokens`：写入 prompt cache 的 input tokens
- `cache_read_input_tokens`：从 prompt cache 读取的 input tokens
- `output_tokens`：生成 token

DeepSeek API 文档中的字段是 `prompt_cache_hit_tokens` 和 `prompt_cache_miss_tokens`，但 Claude Code 目前不会在 session logs 中保存这两个字段名。不要在 `run_metadata.yaml` 中把 Claude Code transcript 字段重命名成 DeepSeek API 字段。正式批量聚合前仍应检查一次 pilot run，以防未来 Claude Code 版本调整落盘 schema。

如果 Claude Code transcript 将同一响应拆成多条流式记录，应先按稳定的 response/message id 去重再求和。input token 字段从单条最终/去重后的响应记录中取值，output tokens 取该响应的最大累计值。如果没有稳定 id，应把 transcript match 标记为 `ambiguous`，不要手动估算计费。

对于 `deepseek-v4-pro`，使用 DeepSeek V4 Pro 价格计算成本：

```text
cost_usd =
  ((input_tokens + cache_creation_input_tokens) * 0.435
   + cache_read_input_tokens * 0.003625
   + output_tokens * 0.87) / 1_000_000
```

发布可计费报告前应重新核对 DeepSeek pricing 页面；如果 DeepSeek 调整价格，需要同步更新公式和 `run_metadata.yaml` 中的 `pricing` block。

**不要**用父会话 `toolUseResult.totalTokens` 当成本或计费总量。它只能作为上下文规模的快速交叉检查，而且可能不包含 Claude Code transcript usage 字段。

推荐格式：

```yaml
eval_attempt_id: <task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
condition: <condition>
task_id: <task_id>
attempt: <int>
model: <model_name_or_config>

transcript:
  subagent_file: <path to .../subagents/agent-<agent_id>.jsonl or null>
  parent_tool_use_id: <tool_use_id of the Agent call for this attempt>
  match_status: matched

token_usage:                          # Claude Code usage，去重后跨响应求和
  source: subagent_transcript
  input_tokens: <int or null>
  cache_creation_input_tokens: <int or null>
  cache_read_input_tokens: <int or null>
  output_tokens: <int or null>
  cost_usd: <float or null>
  billing_mapping:
    full_price_input_tokens: input_tokens + cache_creation_input_tokens
    cache_hit_input_tokens: cache_read_input_tokens
  pricing:
    full_price_input_usd_per_million: 0.435
    cache_read_input_usd_per_million: 0.003625
    output_usd_per_million: 0.87
```

如果 transcript 不能被唯一匹配，应在 `match_status` 中写入 `missing` 或 `ambiguous`，将对应 token 字段设为 `null`，不要手动估算。

## acc@3

同一个 test task 在同一种条件下运行 3 次独立 attempts。

```text
task acc@3 = (attempt_01_score + attempt_02_score + attempt_03_score) / 3
```

某一条件的整体 `acc@3` 是 5 个 test-task `acc@3` 的平均值。

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

所有 `score.yaml` 准备完成后，主 agent 应检查三种条件、5 个 test tasks、每个 task 3 次运行是否完整。然后计算每个 task 的 `acc@3`、整体 `acc@3`，以及条件之间的提升。

主 agent 还应从每个 `run_metadata.yaml` 中聚合平均 Claude Code transcript token 字段，先按每个 test task 的 3 次 attempts 求平均，再按条件下的 5 个 test tasks 求平均。聚合 `input_tokens`、`cache_creation_input_tokens`、`cache_read_input_tokens`、`output_tokens` 和 `cost_usd`。

这些效率指标只统计 test solver subagents 写答案的过程。不包括 skill 生成、环境启动、evaluator 执行或主 agent 汇总。它们不能替代 `acc@3`，但应出现在最终报告中，用于比较不同 skill 条件下的效率。

评估 agent 可以根据当前 task group 的 evaluator 形态，在 `scratch/` 中编写临时聚合或检查代码。
