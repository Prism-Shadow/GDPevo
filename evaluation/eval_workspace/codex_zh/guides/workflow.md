# Evaluation Workflow

本文说明主评估 agent 如何运行一次完整 Codex 评估。

评估现在使用远程 task 环境和四种条件：

```text
base
fewshot
self
reflect-3
```

当用户要求你在这个工作区中运行评估时，该请求即视为允许使用 Codex
subagents。每个 skill-generation 和 solver run 都必须放在干净、专属的
workspace/cwd 中。

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

Codex 评估不再本地启动 `task_group/env` 服务。确认远程环境的 health / index
端点可访问，并把 URL 记录到 `scratch/environment.md`。

Skill-generation 和 solver subagents 不得进入、列出或读取 `env/`。它们只能
使用主 agent staging 的远程环境入口。

Judge endpoint 只用于 train 阶段。只有 reflect skill-generation subagents
能收到它的调用说明：

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
  answers。对 5 个 train tasks 精确运行 3 个 epochs，将每个 candidate 提交给
  judge，再从累积反馈中提炼最终 skill。

Skill-generation token 用量不计入 solver 效率指标。

## 4. 运行 Test Solvers

每种条件、每个 test task、每次 attempt 都独立运行：

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

不要 staging `env/`、train tasks、test answers、task notes、evaluator files、
其他 test tasks、其他 attempt 的 generated skills、prior runs，或给 test
solver 的 judge 调用说明。

Solver 在自己的 attempt 目录中写 `answer.json`。

## 5. 打分与聚合

每个 solver 写出 `answer.json` 后，主 agent 调用当前 test task 的
`eval/eval.sh`，把 prediction 路径传入，并保存 `score.yaml`。

每个 solver attempt 都必须有唯一 `eval_attempt_id`：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

该 ID 必须出现在 solver prompt、attempt 目录和 `run_metadata.yaml` 中。

主 agent 从 Codex session trace 中回填 token 用量。不要只用“最新文件”匹配
trace；应确认：

- `thread_source` 是 `subagent`。
- `parent_thread_id` 属于当前主评估 agent。
- `cwd` 是预期的 attempt 目录。
- trace 中包含匹配的 `eval_attempt_id`。

Codex traces 通常位于：

```text
~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

所有 runs 完成后，聚合四种条件的 `acc@3` 和平均 cached/input/output tokens。
效率指标只统计 test solver 写答案的过程：先对同一个 test task 的 3 次
attempts 取平均，再对 5 个 test tasks 取平均。不要包含 skill generation、
远程环境检查、evaluator 执行或主 agent 汇总。

## 6. 解释结果

在报告中解释：

- 四种条件的整体 `acc@3`。
- `fewshot`、`self` 和 `reflect-3` 相对 `base` 的提升。
- 哪些 test tasks 提升明显，哪些没有。
- 任何环境不稳定、输出 schema 摩擦、evaluator 问题或可疑泄漏风险。
