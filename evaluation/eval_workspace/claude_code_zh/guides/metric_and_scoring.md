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

`run_metadata.yaml` 记录唯一 attempt ID、匹配到的 transcript 引用、token 用量、solver turn count 和 tool-call count。token 值来自该 subagent 的 session transcript，而不是让 agent 在 prompt 内手动统计。

### Token 口径(务必看清，极易算错)

每个 solver subagent 有自己独立的 transcript：

```text
~/.claude/projects/<project>/<session-id>/subagents/agent-<agent_id>.jsonl
```

**一条 API 响应会被拆成多条 content-block 记录。** 这些记录里 `input_tokens` / `cache_creation_input_tokens` / `cache_read_input_tokens` **完全相同**,但 `output_tokens` 是**流式累计**的——后面的记录值更大。所以按 `message.id` 去重时:input/cache 三桶取任一条,`output_tokens` 取该 `message.id` 的**最大值(最后一条)**。逐行求和会把 input/cache 放大约 2-3 倍;只取第一条又会低估 output。去重后,四个桶分别在响应间求和:

- `input_tokens` —— 未缓存 input
- `cache_creation_input_tokens` —— 写缓存
- `cache_read_input_tokens` —— 读缓存
- `output_tokens` —— 生成 token

**不要**用父会话 `toolUseResult.totalTokens` 当 token 总量——它是 `最后一条响应(input+cache) + 累计 output`（一个"最终上下文规模"口径），且**不含 cache_read**，不是完整 token 总量。只能当快速校验或"上下文规模"KPI 用。

推荐格式：

```yaml
eval_attempt_id: <task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
condition: <condition>
task_id: <task_id>
attempt: <int>
model: <model_name_or_config>

transcript:
  subagent_file: <path to .../subagents/agent-<agent_id>.jsonl or null>
  copied_trace_file: <path under original_traces/ or null>
  parent_tool_use_id: <tool_use_id of the Agent call for this attempt>
  match_status: matched

token_usage:                          # 按 message.id 去重、跨响应求和
  source: subagent_transcript
  input_tokens: <int>                 # 未缓存
  cache_creation_input_tokens: <int>
  cache_read_input_tokens: <int>
  output_tokens: <int>
turn_count:
  source: subagent_transcript
  assistant_turns: <int>
```

如果 transcript 不能被唯一匹配，应在 `match_status` 中写入 `missing` 或 `ambiguous`，将 `copied_trace_file` 和对应 token/turn/tool-call 字段设为 `null`，不要手动估算。

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


## rounds@3 and tool calls@3 / trace efficiency

`rounds_avg_3` 统计 solver 的 assistant/model-response turns。Codex 和 Claude Code 从匹配到的 solver trace 中统计 assistant 响应；如果一轮响应被拆成多条 content-block 记录，应按响应或 message id 去重。Panofy 从正式 scored `predict()` trace 的 history 中统计 assistant 消息。

`tool_calls_avg_3` 统计同一条正式 solver trace 中 solver 发起的工具调用次数。Codex trace 统计 `function_call` 和 `custom_tool_call` response item；Claude Code / GLM trace 统计 assistant `tool_use` content block；Panofy trace 统计正式 scored `predict()` history 中 assistant 的 `tool_call` content item。不要统计 tool result、main agent、skill generation、evaluator、环境检查或被替换的失败 attempt。

```text
task rounds@3 = (attempt_01_turns + attempt_02_turns + attempt_03_turns) / 3
overall rounds@3 = (test_001_rounds@3 + test_002_rounds@3 + test_003_rounds@3 + test_004_rounds@3 + test_005_rounds@3) / 5

task tool calls@3 = (attempt_01_tool_calls + attempt_02_tool_calls + attempt_03_tool_calls) / 3
overall tool calls@3 = (test_001_tool_calls@3 + test_002_tool_calls@3 + test_003_tool_calls@3 + test_004_tool_calls@3 + test_005_tool_calls@3) / 5
```

如果某个正式 attempt 的 trace 无法匹配，turn count 和 tool-call count 写 `null`，并在 run record 中保留原因；不要手动估算。

## 聚合要求

所有 `score.yaml` 准备完成后，主 agent 应检查四种条件、5 个 test tasks、每个 task 3 次运行是否完整。然后计算每个 task 的 `acc@3` 和 `std@3`、整体 `acc@3` 和 `std@3`，以及 `fewshot`、`self` 和 `reflect-3` 相对 `base` 的提升。

主 agent 还应从每个 `run_metadata.yaml` 中聚合平均 token 字段和 solver turns，先按每个 test task 的 3 次 attempts 求平均，再按条件下的 5 个 test tasks 求平均。

这些效率指标只统计 test solver subagents 写答案的过程。不包括 skill 生成、远程环境检查、evaluator 执行或主 agent 汇总。它们不能替代 `acc@3`，但应出现在最终报告中，用于比较不同 skill 条件下的效率。

评估 agent 可以根据当前 task group 的 evaluator 形态，在 `scratch/` 中编写临时聚合或检查代码。
