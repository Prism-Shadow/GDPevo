# Evaluation Workspace

本 workspace 是评估入口。你是这一阶段的主评估 agent。你的目标是对一个已经通过质量审核的 task group 进行正式评估，并在四种条件下使用 `acc`、population `std` 和 solver turn-count 和 tool-call 效率指标：`base`、`fewshot`、`self`、`reflect-3`。

本工作区一次只评估一个 task group。不要修改正在评估的 task group。如果你发现 task group 本身无效，应在报告中记录风险，并将数据退回到更早阶段。

## 目录

| 路径 | 用途 |
| --- | --- |
| `guides/` | 评估流程、skill modes、指标、打分和报告格式 |
| `task_group/` | 当前正在评估的单个正式 task group |
| `skills/` | 生成的 `fewshot`、`self` 和 `reflect-3` skill 包；每个 attempt 是一个目录，入口文件为 `SKILL.md` |
| `runs/` | 每种条件、每个 test task、每次 attempt 的 solver 输出和打分记录 |
| `original_traces/` | 每次 skill generation 和 solver attempt 复制进来的单个 Codex 主 `rollout-*.jsonl` |
| `scratch/` | 主评估 agent 创建的临时脚本、环境记录和中间检查 |
| `report/` | 当前 task group 的最终评估报告 |

## 指南

开始评估前按顺序阅读这些文件：

1. `CODEX_ORCHESTRATOR.md` - Codex 主控、Docker 隔离、`codex exec` 命令形态和 trace 保存
2. `guides/workflow.md` - 主 agent 评估流程
3. `guides/skill_modes.md` - 四种条件和信息边界
4. `guides/agent_prompts.md` - 固定的 skill-generation 和 solver prompts
5. `guides/metric_and_scoring.md` - `acc`、population `std`、turn/tool-call 记录、单次 attempt 打分和聚合规则
6. `guides/report_format.md` - 最终报告格式

## 启动 Prompt

```text
Please evaluate task_group/<task_group_id> using README.md and guides/.
Model: <model>, <reasoning_effort>.
Run all four modes with acc/std, collect solver turn and tool-call counts, and write report/<task_group_id>.yaml.
```

使用 `.env` 配置 agent 容器可访问的任务环境：

```text
GDPEVO_RUN_OWNER="<user_name>"
GDPEVO_ENV_BASE_URL=http://task-env:9001/
GDPEVO_JUDGE_PATH=/api/judge
```

## 工作流程

Codex 是主控评估 agent。当用户要求你在这个工作区中运行评估时，该请求即视为允许 Codex staging 干净目录、通过 Docker 内的 `codex exec` 启动隔离 agent run、调用 evaluators、保存 traces 并聚合 reports。不要减少 attempt 数量，不要把多个 test tasks 合并成一次 solver 运行，也不要让主 agent 直接解 test tasks。

每次 skill-generation run 和 solver attempt 都必须只从自己的 staged 目录在 Docker 内运行。使用 `CODEX_ORCHESTRATOR.md` 中的命令形态：`CODEX_HOME=/codex_home codex exec -C /work -m gpt-5.5 -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"`。`CODEX_HOME` 是该 agent 进程运行时临时设置的环境变量，不是任务 `.env` 配置。正式 attempt 不要使用 `codex exec --ephemeral`。

1. 确认 `task_group/` 下只包含一个 task group：

```text
task_group/<task_group_id>/
```

2. 检查工作区只包含一个 task group，并确认该 task group 包含 5 个 train tasks、5 个 test tasks、共享环境、标准答案和 evaluators。

3. 从 `task_group/<task_group_id>/env/Dockerfile` 构建环境镜像。每个运行 scope 都创建独立 Docker bridge network，名称必须包含规范化后的 `<user_name>`、task group 编号、权限阶段、必要时的 condition/task/attempt 和 8 位随机 suffix。环境接入该 network，别名为 `task-env`，监听 `TASK_ENV_BIND=0.0.0.0` 和容器内 `TASK_ENV_PORT = 9000 + task group 数字编号`，且不映射宿主机端口；agent 加入同一 network，通过 `http://task-env:<TASK_ENV_PORT>/` 访问。读取 `env.state_mode`：read-only 环境只能在同一权限阶段共享，mutable 环境每个 attempt 使用新的 environment 和 network。只有独立的 reflect skill-generation 阶段开启 `/api/judge`，正式 test 必须关闭。最后从相同 network 的临时容器检查 `/health`，并记录全部运行时名称和检查结果。

4. 为每种非 base 条件生成 3 个独立 skills：

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

5. 在四种条件下运行 test tasks：

```text
runs/base/
runs/fewshot/
runs/self/
runs/reflect-3/
```

每种条件下，每个 test task 独立运行 3 次。每次运行都必须由干净上下文的 Dockerized Codex run 完成。对于 skill 条件，solver 的 `attempt_<nn>` 使用相同编号的独立生成 skill。

6. 每个 solver 输出完成后，调用对应 task evaluator，并将分数保存到对应 attempt 目录。每个 attempt 目录还应包含 `run_metadata.yaml`，记录唯一的 `eval_attempt_id`、复制后的主 trace 路径、token 用量、solver turn count 和 tool-call count。每个 attempt 使用临时挂载的 `CODEX_HOME`；运行结束后，只把匹配的 `sessions/.../rollout-*.jsonl` 复制为 `original_traces/<condition>/<task_id>/attempt_<nn>/rollout-*.jsonl`。从该副本回填并核验 token、费用、轮次、工具调用和 metadata 后，才能删除整个临时 home。不要保存其中的配置、凭据、plugins、skills、缓存、日志、数据库，也不要把 stdout 当作 trace。

7. 所有 score records 准备完成后，聚合四种条件的 `acc` 和 population `std`，并聚合每种条件的平均 cached/input/output tokens、solver turns 和 tool calls。最终报告写入 `report/<task_group_id>.yaml`。这些效率指标只统计 test solver 进程 写答案的过程：先对同一个 test task 的 3 次 attempts 取平均，再对 5 个 test tasks 取平均。不要包含 skill 生成、环境检查、evaluator 执行或主 agent 汇总。临时检查或聚合代码可以放在 `scratch/` 下。

## Agent 边界

主 agent 可以读取完整 task group，以便确认 task 环境网络契约、调用 evaluators 和汇总结果，但不能直接解 test tasks。

Skill-generation runs 只负责生成 skills，不参与 test 解题。

Solver runs 只能看到当前条件允许的信息。Solver 不应该看到 test 标准答案、test notes、evaluator 实现细节或 `env/` 源码。Skill-generation 和 solver runs 不能进入、列出或读取 `env/`；它们只能通过主 agent 明确暴露的容器可访问的 Web/API URL 或数据库连接使用共享环境。只有 reflect skill-generation runs 应收到 train-only judge API 说明，且该 API 对 test-time solving 无效。

模式允许的训练阶段暴露不算污染：例如 fewshot skill 生成可以读取 train `output/answer.json`。但在 test-solving attempt 中，除当前 attempt 目录内 solver 自己写出的答案文件外，直接访问任何源任务的 `output/answer.json` 都是禁止的。

如果 solver/test run 误访问、列出或报告看到了禁止材料，例如 `env/`、test solving 阶段的源 `output/answer.json`、task notes、evaluator files、当前模式/阶段不允许的 train tasks 或 train answers，或其它 attempt 的 run files，该 attempt 视为污染。主 agent 必须及时报告给用户，不要打分或纳入聚合，在 attempt 目录记录原因，并用新的干净 attempt 目录重新测试受影响任务。

对于 solver attempts，应使用对应的全新 attempt 目录作为 Docker 内 `/work`，例如 `runs/base/test_001/attempt_01/`。主 agent 只放入当前 task 的 `input/`、环境访问说明，以及 skill 条件下与 attempt 编号匹配的完整 skill 包目录，并统一命名为 `skill/`。重跑不能复用旧 attempt 目录；应创建新的干净目录，并保留被判污染的 run 供审计。Skill 生成应使用 `scratch/skill_generation/` 下的独立目录，只放入该模式允许的 train 材料，并把生成的整个 `skill/` 目录复制到 `skills/` 下对应的 attempt 目录。

## 固定 Agent Prompts

严格使用 `guides/agent_prompts.md` 中与当前模式对应的 skill-generation 或
test-solver 模板。只替换模板声明的占位符，不要追加提示、隐藏上下文或其它路径。
主 agent 之后使用每次 run 的 id 匹配 Codex session trace，并回填 token、turn 和
tool-call 字段。
