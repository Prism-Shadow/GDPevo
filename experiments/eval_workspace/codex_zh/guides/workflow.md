# Evaluation Workflow

本文说明主评估 agent 应如何运行一次完整评估。

当用户要求你在这个工作区中运行评估时，该请求即视为允许使用 Codex subagents。主 agent 可以启动干净上下文的 skill-generation subagents 和 solver subagents 来生成 skills 并完成 test attempts。

如果所需 subagent 数量超过当前 Codex 并发上限，应分批运行。分批执行仍必须保证每次 solver attempt 都是干净上下文、拥有唯一 `eval_attempt_id`，并保存完整运行记录。不要减少 attempt 数量，不要让一个 solver 解多个 test tasks，也不要让主 agent 直接解 test tasks。

启动任何 skill-generation 或 solver subagent 之前，主 agent 必须为该 subagent 准备一个最小工作目录，并用该目录作为 workspace/cwd 启动 subagent。不要从 workspace 根目录、`task_group/` 根目录，或任何包含该 subagent 信息边界之外文件的目录启动 subagents。

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

主 agent 为每种 skill 条件生成 3 个独立 skills。每个 skill 都必须由干净上下文的 skill-generation subagent 使用 Codex `skill-creator` skill 生成。

每个 skill-generation subagent 应从专用 workspace 启动，例如：

```text
scratch/skill_generation/demo_attempt_01/
scratch/skill_generation/reflect_attempt_01/
```

主 agent 只把该模式允许的 train inputs、train answers 和暴露的环境入口 staging 到这个 workspace 中。对于 `reflect`，在 blind train attempts 保存之前，不要 staging train answers。Skill-generation subagent 在自己的 workspace 中写 draft skill；主 agent 再将接受的 skill 复制到 `skills/`。

推荐布局：

```text
skills/demo/demo_attempt_01/SKILL.md
skills/demo/demo_attempt_02/SKILL.md
skills/demo/demo_attempt_03/SKILL.md
skills/reflect/reflect_attempt_01/SKILL.md
skills/reflect/reflect_attempt_02/SKILL.md
skills/reflect/reflect_attempt_03/SKILL.md
```

生成规则见 `skill_modes.md`。

每个生成的 skill 应是 Codex-style skill directory，markdown 入口文件为 `SKILL.md`。

Skill-generation token 用量不计入 solver 效率指标。

## 5. 运行 Base 实验

每个 test task 独立运行 3 次。Solver 只接收该 test task 的正式输入和允许的环境入口。

推荐记录布局：

```text
runs/base/test_001/attempt_01/answer.json
runs/base/test_001/attempt_01/score.yaml
runs/base/test_001/attempt_01/run_metadata.yaml
```

用对应 attempt 目录作为 workspace/cwd 启动每个 solver subagent：

```text
runs/base/test_001/attempt_01/
```

启动前，只将允许文件 staging 到该 attempt 目录：

- 从当前 test task 正式 `input/` 复制出的 `input/`。
- `environment_access.md` 或等价的简明说明，用于说明暴露的 Web/API/database 入口。

不要 staging `env/`、task outputs、task notes、evaluator files、train tasks、其他 test tasks、generated skills 或 base runs 的 prior run outputs。Solver 在自己的 attempt 目录中写入 `answer.json`。

## 6. 运行 Demo 实验

每个 test task 独立运行 3 次。Solver 接收该 test task 的正式输入、允许的环境入口，以及对应的独立生成 demonstration skill：

```text
attempt_01 uses skills/demo/demo_attempt_01/SKILL.md
attempt_02 uses skills/demo/demo_attempt_02/SKILL.md
attempt_03 uses skills/demo/demo_attempt_03/SKILL.md
```

每次运行仍然需要干净上下文。不要让一个 solver 解多个 test tasks。

从各自 attempt 目录启动 solver，例如：

```text
runs/demo/test_001/attempt_01/
```

只 staging 当前 test task 的 `input/`、环境入口，以及与 attempt 编号匹配的 generated skill 副本。不要暴露完整 `skills/` 目录，也不要暴露其他 attempt 编号的 skills。

## 7. 运行 Reflect 实验

每个 test task 独立运行 3 次。Solver 接收该 test task 的正式输入、允许的环境入口，以及对应的独立生成 reflection skill：

```text
attempt_01 uses skills/reflect/reflect_attempt_01/SKILL.md
attempt_02 uses skills/reflect/reflect_attempt_02/SKILL.md
attempt_03 uses skills/reflect/reflect_attempt_03/SKILL.md
```

每次运行仍然需要干净上下文。不要让一个 solver 解多个 test tasks。

从各自 attempt 目录启动 solver，例如：

```text
runs/reflect/test_001/attempt_01/
```

只 staging 当前 test task 的 `input/`、环境入口，以及与 attempt 编号匹配的 generated skill 副本。不要暴露完整 `skills/` 目录，也不要暴露其他 attempt 编号的 skills。

## 8. 打分和聚合

每个 solver 写出 `answer.json` 后，主 agent 调用对应 task evaluator，并写入 `score.yaml`。

每个 solver attempt 都必须有唯一 `eval_attempt_id`，并且该 ID 必须出现在 solver prompt、attempt 目录和 `run_metadata.yaml` 中。推荐格式：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

主 agent 从 Codex session trace 中回填 token 用量。不要只使用“最新文件”匹配 trace；应确认以下全部条件：

- Trace 的 `thread_source` 是 `subagent`。
- Trace 的 `parent_thread_id` 属于当前主评估 agent。
- Trace 的 `cwd` 是预期的 per-subagent workspace/cwd，例如 solver attempt 对应的 `runs/<condition>/test_<nn>/attempt_<mm>/` 目录。
- Trace 中包含对应 `eval_attempt_id`。

Codex traces 通常位于：

```text
~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

`token_count` event 记录 token 用量。

所有 runs 完成后，聚合三种条件的 `acc@3` 和平均 cached/input/output tokens。这些效率指标只统计 test solver subagents 写答案的过程：先对同一个 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。不要包含 skill 生成、环境启动、evaluator 执行或主 agent 汇总。

临时检查代码、聚合代码或环境启动 notes 可以放在 `scratch/`。这些材料不是正式评估数据。

## 9. 解释结果

在报告中解释：

- 三种条件的整体 `acc@3`。
- 每种 skill 条件相对 base 的提升。
- Reflection skill 是否优于 demonstration skill。
- 哪些 test tasks 提升明显，哪些没有。
- 任何环境不稳定、输出 schema 摩擦、evaluator 问题或可疑泄漏风险。
