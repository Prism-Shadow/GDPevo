# Evaluation Workspace

本 workspace 是评估入口。你是这一阶段的主评估 agent。你的目标是对一个已经通过质量审核的 task group 进行正式评估，并在三种 skill 条件下使用 `acc@3` 指标。

本工作区一次只评估一个 task group。不要修改正在评估的 task group。如果你发现 task group 本身无效，应在报告中记录风险，并将数据退回到更早阶段。

## 目录

| 路径 | 用途 |
| --- | --- |
| `guides/` | 评估流程、skill modes、指标、打分和报告格式 |
| `task_group/` | 当前正在评估的单个正式 task group |
| `skills/` | 生成的 `fewshot` 和 `reflect` 文件 |
| `runs/` | 每种条件、每个 test task、每次 attempt 的 solver 输出和打分记录 |
| `scratch/` | 主评估 agent 创建的临时脚本、环境记录和中间检查 |
| `report/` | 当前 task group 的最终评估报告 |

## 指南

开始评估前按顺序阅读这些文件：

1. `guides/workflow.md` - 主 agent 评估流程
2. `guides/skill_modes.md` - 三种 skill 条件和信息边界
3. `guides/metric_and_scoring.md` - `acc@3`、单次 attempt 打分和聚合规则
4. `guides/report_format.md` - 最终报告格式

## 启动 Prompt

```text
Please evaluate task_group/<task_group_id> using README.md and guides/.
Model: <model>.
Run all three modes with acc@3 and write report/<task_group_id>.yaml.
```

## 工作流程

当用户要求你在这个工作区中运行评估时，该请求即视为允许使用 Claude Code subagents（Task / Agent 工具），包括 skill-generation subagents 和 solver subagents。如果需要的 subagent 数量超过 subagent 并发上限，应分批运行，直到所有 attempts 完成。不要减少 attempt 数量，不要把多个 test tasks 合并成一次 solver 运行，也不要让主 agent 直接解 test tasks。

Solver 和 skill-generation subagents 使用与主 agent 相同的 DeepSeek V4 Pro 配置。应先用 Claude Code + DeepSeek V4 Pro 配置启动主 agent；subagents 应继承该配置，无需单独传模型参数。

1. 确认 `task_group/` 下只包含一个 task group：

```text
task_group/<task_group_id>/
```

2. 检查工作区只包含一个 task group，并确认该 task group 包含 5 个 train tasks、5 个 test tasks、共享环境、标准答案和 evaluators。

3. 启动或准备 task-group 环境。如果需要端口，应在 `8000-8100` 中随机 roll 一个候选端口；如果被占用，再重新 roll。不要从 `8000` 开始向上扫描。记录启动命令、端口和环境说明。

4. 为每种 skill 条件生成 3 个独立 skills：

```text
skills/fewshot/fewshot_attempt_01/SKILL.md
skills/fewshot/fewshot_attempt_02/SKILL.md
skills/fewshot/fewshot_attempt_03/SKILL.md
skills/reflect/reflect_attempt_01/SKILL.md
skills/reflect/reflect_attempt_02/SKILL.md
skills/reflect/reflect_attempt_03/SKILL.md
```

5. 在三种条件下运行 test tasks：

```text
runs/base/
runs/fewshot/
runs/reflect/
```

每种条件下，每个 test task 独立运行 3 次。每次运行都必须由干净上下文的 solver subagent 完成。对于 skill 条件，solver 的 `attempt_<nn>` 使用相同编号的独立生成 skill。

6. 每个 solver 输出完成后，调用对应 task evaluator，并将分数保存到对应 attempt 目录。每个 attempt 目录还应包含 `run_metadata.yaml`，记录唯一的 `eval_attempt_id`、匹配到的 session transcript 引用、Claude Code transcript token 用量，以及 DeepSeek V4 Pro 计价依据。

7. 所有 score records 准备完成后，聚合三种条件的 `acc@3`，并聚合每种条件的 Claude Code transcript input、cache-creation input、cache-read input、output tokens 和 DeepSeek V4 Pro cost。最终报告写入 `report/<task_group_id>.yaml`。这些效率指标只统计 test solver subagents 写答案的过程：先对同一个 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。不要包含 skill 生成、环境启动、evaluator 执行或主 agent 汇总。临时检查或聚合代码可以放在 `scratch/` 下。

## Agent 边界

主 agent 可以读取完整 task group，以便启动环境、调用 evaluators 和汇总结果，但不能直接解 test tasks。

Skill-generation subagents 只负责生成 skills，不参与 test 解题。

Solver subagents 只能看到当前条件允许的信息。Solver 不应该看到 test 标准答案、test notes、evaluator 实现细节或 `env/` 源码。Skill-generation 和 solver subagents 不能进入、列出或读取 `env/`；它们只能通过主 agent 明确暴露的端口、Web/API URL 或数据库连接使用共享环境。

对于每次 solver attempt，主 agent 把允许的文件 staging 到一个专属 attempt 目录（例如 `runs/base/test_001/attempt_01/`），并启动一个干净上下文 subagent，将其限定在该目录内：subagent 只能读写该目录下的文件，不得访问该目录之外的任何路径。staging 当前 task 的 `input/`、环境访问说明，以及（仅 skill 条件下）与 attempt 编号匹配的 skill 副本。Skill 生成则把该模式允许的 train 材料 staging 到 `scratch/skill_generation/` 下的专属目录，并以同样方式将 subagent 限定在自己的目录内。

## Solver Prompt

给 solver subagent 的任务说明应简短明确：

```text
eval_attempt_id: <unique_eval_attempt_id>

Please solve this single test task. You may only read and write files inside this attempt directory; do not access any path outside it. Use only the staged task input, allowed environment access, and the skill file if one is provided. Write the final answer as answer.json following input/payloads/answer_template.json.
```

主 agent 之后使用 `eval_attempt_id` 在 session transcript 中定位该 subagent 的 turns，并回填 `token_usage`。
