# Evaluation Workflow

本文说明主评估 agent 应如何运行一次完整评估。

当用户要求你在这个工作区中运行评估时，该请求即视为允许使用 Claude Code subagents（Task / Agent 工具）。主 agent 可以启动干净上下文的 skill-generation subagents 和 solver subagents 来生成 skills 并完成 test attempts。

Solver 和 skill-generation subagents 使用与主 agent 相同的模型和 reasoning/effort 设置——这会自动继承，无需额外设置。

如果所需 subagent 数量超过 subagent 并发上限，应分批运行。分批执行仍必须保证每次 solver attempt 都是干净上下文、拥有唯一 `eval_attempt_id`，并保存完整运行记录。不要减少 attempt 数量，不要让一个 solver 解多个 test tasks，也不要让主 agent 直接解 test tasks。

启动任何 skill-generation 或 solver subagent 之前，主 agent 必须为该 subagent 准备一个只包含其允许文件的专属目录，并要求 subagent 只读写该目录内的文件。不要让 subagent 访问 workspace 根目录、`task_group/` 根目录，或任何包含该 subagent 信息边界之外文件的目录。

## 1. 准备 Task Group

本工作区一次评估一个 task group。待评估 task group 应位于：

```text
task_group/<task_group_id>/
```

该 task group 必须已经通过质量审核。

## 2. 检查工作区

主 agent 首先确认工作区只包含一个 task group，并且它包含：

- 5 个 train tasks。
- 5 个 test tasks。
- task-group 级别共享环境。
- 每个 task 的正式输入、标准答案和 evaluator。

## 3. 启动共享环境

主 agent 准备 task-group 环境，并总结 solver 可见的环境入口。

如果需要 Web/API 服务，应在 `8000-8100` 中随机 roll 一个候选端口；如果该端口被占用，再重新 roll。不要从 `8000` 开始向上扫描。记录：

- 启动命令。
- 端口。
- Solver 可见端口、Web/API URL 或数据库连接说明。
- 环境错误或重启记录。

Skill-generation 和 solver subagents 不能进入、列出或读取 `env/`。它们只能通过主 agent 明确暴露的端口、Web/API URL 或数据库连接使用共享环境。

## 4. 生成 Skills

主 agent 为每种 skill 条件生成 3 个独立 skills。每个 skill 都必须由干净上下文的 skill-generation subagent 使用 `skill-creator` skill 生成。

每个 skill-generation subagent 应分配一个专属工作目录，并限定在该目录内，例如：

```text
scratch/skill_generation/demonstration_skill_attempt_01/
scratch/skill_generation/reflection_skill_attempt_01/
```

主 agent 只把该模式允许的 train inputs、train answers 和暴露的环境入口 staging 到这个目录中。对于 `reflection_skill`，在 blind train attempts 保存之前，不要 staging train answers。Skill-generation subagent 在自己的目录中写 draft skill；主 agent 再将接受的 skill 复制到 `skills/`。

推荐布局：

```text
skills/demonstration_skill/demonstration_skill_attempt_01/SKILL.md
skills/demonstration_skill/demonstration_skill_attempt_02/SKILL.md
skills/demonstration_skill/demonstration_skill_attempt_03/SKILL.md
skills/reflection_skill/reflection_skill_attempt_01/SKILL.md
skills/reflection_skill/reflection_skill_attempt_02/SKILL.md
skills/reflection_skill/reflection_skill_attempt_03/SKILL.md
```

生成规则见 `skill_modes.md`。

每个生成的 skill 应是一个 skill directory，markdown 入口文件为 `SKILL.md`。

Skill-generation token 用量不计入 solver 效率指标。

## 5. 运行 No-Skill 实验

每个 test task 独立运行 3 次。Solver 只接收该 test task 的正式输入和允许的环境入口。

推荐记录布局：

```text
runs/no_skill/test_001/attempt_01/answer.json
runs/no_skill/test_001/attempt_01/score.yaml
runs/no_skill/test_001/attempt_01/run_metadata.yaml
```

启动每个 solver subagent，并将其限定在对应 attempt 目录内：

```text
runs/no_skill/test_001/attempt_01/
```

启动前，只将允许文件 staging 到该 attempt 目录：

- 从当前 test task 正式 `input/` 复制出的 `input/`。
- `environment_access.md` 或等价的简明说明，用于说明暴露的 Web/API/database 入口。

不要 staging `env/`、task outputs、task notes、evaluator files、train tasks、其他 test tasks、generated skills 或 no-skill runs 的 prior run outputs。Solver 在自己的 attempt 目录中写入 `answer.json`。

## 6. 运行 Demonstration Skill 实验

每个 test task 独立运行 3 次。Solver 接收该 test task 的正式输入、允许的环境入口，以及对应的独立生成 demonstration skill：

```text
attempt_01 uses skills/demonstration_skill/demonstration_skill_attempt_01/SKILL.md
attempt_02 uses skills/demonstration_skill/demonstration_skill_attempt_02/SKILL.md
attempt_03 uses skills/demonstration_skill/demonstration_skill_attempt_03/SKILL.md
```

每次运行仍然需要干净上下文。不要让一个 solver 解多个 test tasks。

启动每个 solver，并将其限定在各自 attempt 目录内，例如：

```text
runs/demonstration_skill/test_001/attempt_01/
```

只 staging 当前 test task 的 `input/`、环境入口，以及与 attempt 编号匹配的 generated skill 副本。不要暴露完整 `skills/` 目录，也不要暴露其他 attempt 编号的 skills。

## 7. 运行 Reflection Skill 实验

每个 test task 独立运行 3 次。Solver 接收该 test task 的正式输入、允许的环境入口，以及对应的独立生成 reflection skill：

```text
attempt_01 uses skills/reflection_skill/reflection_skill_attempt_01/SKILL.md
attempt_02 uses skills/reflection_skill/reflection_skill_attempt_02/SKILL.md
attempt_03 uses skills/reflection_skill/reflection_skill_attempt_03/SKILL.md
```

每次运行仍然需要干净上下文。不要让一个 solver 解多个 test tasks。

启动每个 solver，并将其限定在各自 attempt 目录内，例如：

```text
runs/reflection_skill/test_001/attempt_01/
```

只 staging 当前 test task 的 `input/`、环境入口，以及与 attempt 编号匹配的 generated skill 副本。不要暴露完整 `skills/` 目录，也不要暴露其他 attempt 编号的 skills。

## 8. 打分和聚合

每个 solver 写出 `answer.json` 后，主 agent 调用对应 task evaluator，并写入 `score.yaml`。

每个 solver attempt 都必须有唯一 `eval_attempt_id`，并且该 ID 必须出现在 solver prompt、attempt 目录和 `run_metadata.yaml` 中。推荐格式：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

主 agent 从 session transcript 中回填 token 用量。不要只用“最新一条记录”来归属用量；应确认以下全部条件：

- 这些 turns 属于一次 subagent 调用，而不是主 agent。
- 该 subagent 由当前主评估 agent 启动（其 `parent_tool_use_id` 与你为该 attempt 发起的 Agent 工具调用一致）。
- 该 attempt 的 `answer.json` 写在预期的 attempt 目录下，例如 `runs/<condition>/test_<nn>/attempt_<mm>/`。
- subagent prompt 中包含对应 `eval_attempt_id`。

每个 solver subagent 有自己独立的 transcript：

```text
~/.claude/projects/<project>/<session-id>/subagents/agent-<agent_id>.jsonl
```

一条 API 响应会被拆成多条 content-block 记录:`input`/`cache_creation`/`cache_read` 完全相同,但 `output_tokens` 是流式累计的。**按 `message.id` 去重**——input/cache 三桶取任一条,`output_tokens` 取该 id 的**最大值**;逐行求和会把 input/cache 放大约 2-3 倍,只取第一条又会低估 output。对去重后的响应,把四个桶(`input_tokens`、`cache_creation_input_tokens`、`cache_read_input_tokens`、`output_tokens`)分别求和,并用 `metric_and_scoring.md` 里的逐响应公式算出 `cost_usd`。不要拿父会话 `toolUseResult.totalTokens` 当计费总量——它是"上下文规模"口径且不含 cache_read。

所有 runs 完成后，聚合三种条件的 `avg@3`、平均各桶 token 和平均 `cost_usd`。这些效率指标只统计 test solver subagents 写答案的过程：先对同一个 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。不要包含 skill 生成、环境启动、evaluator 执行或主 agent 汇总。

临时检查代码、聚合代码或环境启动 notes 可以放在 `scratch/`。这些材料不是正式评估数据。

## 9. 解释结果

在报告中解释：

- 三种条件的整体 `avg@3`。
- 每种 skill 条件相对 no-skill 的提升。
- Reflection skill 是否优于 demonstration skill。
- 哪些 test tasks 提升明显，哪些没有。
- 任何环境不稳定、输出 schema 摩擦、evaluator 问题或可疑泄漏风险。
