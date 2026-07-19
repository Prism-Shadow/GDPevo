# Evaluation Workflow

本文说明主评估 agent 如何运行一次完整 Codex 评估。

评估使用一个由 agent 容器通过网络访问的宿主机 task 环境和四种条件：

```text
base
fewshot
self
reflect-3
```

当用户要求你在这个工作区中运行评估时，该请求视为允许 Codex 作为主控组织实验，并用
Docker 内的 `codex exec` 启动隔离 agent run。每个 skill-generation 和 solver
run 都必须放在干净、专属的 staged 目录中，并将该目录作为 Docker 内 `/work`
挂载。

启动隔离 agent run 前先读 `CODEX_ORCHESTRATOR.md`。正式 Codex 命令形态为：

```bash
CODEX_HOME=/codex_home codex exec -C /work -m gpt-5.5 -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"
```

`CODEX_HOME` 是该 agent 进程运行时临时设置的环境变量，不是任务 `.env` 配置。
正式 attempt 不要使用 `codex exec --ephemeral`。每个进程必须使用
`agent_prompts.md` 中对应模式的固定 prompt，只替换声明的占位符，不追加提示或路径。

创建临时 home 前，先把主控当前可用的 Codex home 保存为
`HOST_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"`。每个 run 的临时 home 只复制
`$HOST_CODEX_HOME/auth.json`，权限设为 `0600`；随后在 agent image 中对同一挂载
执行 `CODEX_HOME=/codex_home codex login status`。登录文件缺失或认证无效时，该
run 应直接判定为 blocked。不能复制当前 Codex home 的其他内容，也不能让主控代替
未认证的被测 agent 运行。

## 1. 准备 Task Group

待评估 task group 应位于：

```text
task_group/<task_group_id>/
```

确认它包含 5 个 train tasks、5 个 test tasks、`env/`、每个 task 的正式
input、标准答案和 `eval/eval.sh`。不要修改 task group。

## 2. 启动并连接环境

读取 `.env`：

```text
GDPEVO_RUN_OWNER="<user_name>"
GDPEVO_ENV_BASE_URL=http://task-env:<TASK_ENV_PORT>/
GDPEVO_JUDGE_PATH=/api/judge
```

构建 `task_group/env/Dockerfile`。按照 `CODEX_ORCHESTRATOR.md` 的强制规范，
创建包含 owner/run 的 network 和环境容器；环境别名为 `task-env`，监听
`TASK_ENV_BIND=0.0.0.0` 和容器内
`TASK_ENV_PORT = 9000 + task group 数字编号`，不映射宿主机端口。每个 agent
接入为它分配的 network。根据 `env.state_mode` 决定在同一权限阶段共享 read-only
环境，或为每个 mutable attempt 启动新环境；开启 judge 的 reflect generation
不能和关闭 judge 的 test 共用。临时容器必须在同一 network 上通过 agent 实际
URL 检查 health / index endpoint，并将全部运行时名称、镜像、state mode、端口、
URL 和结果记录到 `scratch/environment.md`。

Skill-generation 和 solver runs 不得进入、列出或读取 `env/`。它们只能
使用主 agent staging 的容器可访问环境入口。

主 agent 从 `task_group/env/endpoints.txt` 读取 endpoint 名称。每次 staging 的
`environment_access.md` 都要包含 base URL、必要凭据，以及当前运行允许的全部
endpoint；endpoint 只按 `METHOD /path` 逐行列出，不附接口介绍。Skill
generation 和 test solving 可以使用业务 endpoint；只有 reflect skill
generation 可以额外看到 `/api/judge`；执行 agent 不能看到 `/health` 或
reset/reseed endpoint。

Judge endpoint 只用于 reflect skill generation 中的 train tasks。它不能
staging 给 test solver，也不能作为 test-time 工具写入生成的 skill。只有
reflect skill-generation runs 能收到它的调用说明：

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

- `fewshot`：train inputs、train 标准答案、容器可访问环境入口。
- `self`：train inputs 和容器可访问环境入口；无 train answers、无 judge feedback。
- `reflect-3`：train inputs、容器可访问环境入口、judge API 调用说明；无 train
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
- 包含容器可访问环境 URL、必要凭据和允许 endpoint 名称的 `environment_access.md`。
- 非 base 模式下与 attempt 编号匹配的完整 skill 包目录，统一命名为 `skill/`。

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

每次 solver attempt 都由 Codex 主控从该 attempt 目录启动一个 Dockerized Codex
进程。只挂载 attempt 目录和供 `CODEX_HOME` 使用的临时 Codex home，不要挂载完整
workspace 或 task group。临时 home 放在 `scratch/runtime_homes/`，不能直接放进
`original_traces/`。

## 5. 打分与聚合

每个 solver 写出 `answer.json` 后，主 agent 调用当前 test task 的
`eval/eval.sh`，把 prediction 路径传入，并保存 `score.yaml`。

每个 solver attempt 都必须有唯一 `eval_attempt_id`：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

该 ID 必须出现在 solver prompt、attempt 目录和 `run_metadata.yaml` 中。

进程结束后，主 agent 从 attempt 专用的临时 `CODEX_HOME` 中找到 Codex 主 session
trace，确认它使用预期 attempt 目录并包含匹配的 `eval_attempt_id`。只把该 JSONL
复制到正式 trace 目录，再从复制后的文件回填并核验 token 用量、费用、solver
turn count、tool-call count 和 `run_metadata.yaml`。完成后才能删除整个临时 Codex
home。

Codex 原始 session traces 应位于：

```text
original_traces/<condition>/<task_id>/attempt_<nn>/rollout-*.jsonl
```

在 `run_metadata.yaml` 中记录原始 session trace 路径。如果原始 session trace
缺失，将原始 trace 路径写为 `null`，trace 派生的效率字段也保持 `null`，并报告
trace 问题。

所有 runs 完成后，聚合四种条件的 `acc@3`、population `std@3`、平均 cached/input/output tokens 和 solver turn count 和 tool-call counts。
效率指标只统计 test solver 写答案的过程：先对同一个 test task 的 3 次
attempts 取平均，再对 5 个 test tasks 取平均。不要包含 skill generation、
环境检查、evaluator 执行或主 agent 汇总。

## 6. 解释结果

在报告中解释：

- 四种条件的整体 `acc@3` 和 population `std@3`。
- `fewshot`、`self` 和 `reflect-3` 相对 `base` 的提升。
- 哪些 test tasks 提升明显，哪些没有。
- 任何环境不稳定、输出 schema 摩擦、evaluator 问题或可疑泄漏风险。
