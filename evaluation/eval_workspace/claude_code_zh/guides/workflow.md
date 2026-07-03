# Evaluation Workflow

本文说明主评估 agent 如何运行一次完整 Claude Code 评估。

评估现在使用远程 task 环境和四种条件：

```text
base
fewshot
self
reflect-3
```

当用户要求你在这个工作区中运行评估时，该请求即视为允许使用 Claude Code
subagents（Task / Agent 工具）。每个 skill-generation 和 solver run 都必须
放在干净、专属的目录中，并将对应 subagent 限定在该目录内。

## 1. 准备 Task Group

待评估 task group 应位于：

```text
task_group/<task_group_id>/
```

确认它包含 5 个 train tasks、5 个 test tasks、`env/`、每个 task 的正式
input、标准答案和 `eval/eval.sh`。不要修改 task group。

## 2. 配置远程环境

读取 `.env`：

```text
GDPEVO_ENV_BASE_URL=<remote task environment>
GDPEVO_JUDGE_PATH=/api/judge
```

Claude Code 评估不再本地启动 `task_group/env` 服务。确认远程环境的 health /
index 端点可访问，并把 URL 记录到 `scratch/environment.md`。

Skill-generation 和 solver subagents 不得进入、列出或读取 `env/`。它们只能
使用主 agent staging 的远程环境入口。

Judge endpoint 只用于 reflect skill generation 中的 train tasks。它不能
staging 给 test solver，也不能作为 test-time 工具写入生成的 skill。只有
reflect skill-generation subagents 能收到它的调用说明：

```text
POST {GDPEVO_ENV_BASE_URL}{GDPEVO_JUDGE_PATH}
{"task_id": "train_001", "answer": <candidate answer JSON>}
```

## 3. 生成 Skills

为每个非 base 条件生成 3 个独立 skills：

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

使用专属 workspace，例如：

```text
scratch/skill_generation/fewshot_attempt_01/
scratch/skill_generation/self_attempt_01/
scratch/skill_generation/reflect-3_attempt_03/
```

只 staging `skill_modes.md` 允许的材料。

- `fewshot`：train inputs、train 标准答案、远程环境入口。
- `self`：train inputs 和远程环境入口；无 train answers、无 judge feedback。
- `reflect-3`：train inputs、远程环境入口、judge API 调用说明；无 train
  answers。

Skill-generation token 用量不计入 solver 效率指标。

## 4. 运行 Test Solvers

每种条件、每个 test task、每次 attempt 都在全新的目录中独立运行：

```text
runs/<condition>/test_001/attempt_01/
```

条件：

```text
base
fewshot
self
reflect-3
```

每个 attempt 目录只 staging：

- 当前 test task 的 `input/`。
- 包含远程环境 URL 的 `environment_access.md`。
- 非 base 模式下与 attempt 编号匹配的 skill。

不要给 test solver staging `env/`、train tasks、源 answer files、test answers、
task notes、evaluator files、其他 test tasks、其他 attempt 的 generated skills、
prior runs，或 judge 调用说明。这个限制不禁止 fewshot skill 生成阶段读取
已 staging 的 train 标准答案；这里约束的是 test solver attempt 的 staging。

如果 solver 访问、列出或报告看到了禁止材料，例如 `env/`、test solving 阶段
的源 `output/answer.json`、notes、evaluator files、当前模式/阶段不允许的
train tasks 或 train answers，或其它 attempt 的文件，停止使用该结果。将该
attempt 标记为污染，在 attempt 目录记录原因，及时报告给用户，并在新的干净
attempt 目录中重新测试受影响任务。污染 attempt 不打分、不纳入聚合。

Solver 在自己的 attempt 目录中写 `answer.json`。

## 5. 打分与聚合

每个 solver 写出 `answer.json` 后，主 agent 调用当前 test task 的
`eval/eval.sh`，把 prediction 路径传入，并保存 `score.yaml`。

每个 solver attempt 都必须有唯一 `eval_attempt_id`：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

该 ID 必须出现在 solver prompt、attempt 目录和 `run_metadata.yaml` 中。

主 agent 从匹配到的 Claude Code subagent transcript 中回填 token 用量。
按 `message.id` 去重：input/cache 桶取任一条记录，`output_tokens` 取同一
message id 的最大值，然后跨响应求和。

Claude Code subagent transcripts 通常位于：

```text
~/.claude/projects/<project>/<session-id>/subagents/agent-<agent_id>.jsonl
```

匹配到 transcript 后，将原始 `agent-*.jsonl` 复制或硬链接到：

```text
original_traces/<condition>/<task_id>/attempt_<nn>/
```

在 `run_metadata.yaml` 中同时记录原始 transcript 路径和复制进工作区后的
trace 路径。如果不能唯一匹配 transcript，将复制后的 trace 路径写为
`null`，token 和 turn 字段也保持 `null`，并报告 trace 问题。

所有 runs 完成后，聚合四种条件的 `acc@3`、population `std@3`、各桶 token 和 solver turn counts。效率指标只统计
test solver 写答案的过程：先对同一个 test task 的 3 次 attempts 取平均，再对
5 个 test tasks 取平均。不要包含 skill generation、远程环境检查、evaluator
执行或主 agent 汇总。

## 6. 解释结果

在报告中解释：

- 四种条件的整体 `acc@3` 和 population `std@3`。
- `fewshot`、`self` 和 `reflect-3` 相对 `base` 的提升。
- 哪些 test tasks 提升明显，哪些没有。
- 任何环境不稳定、输出 schema 摩擦、evaluator 问题或可疑泄漏风险。
