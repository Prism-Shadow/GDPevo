# Evaluation Workflow

本文说明 Codex 主控评估 agent 如何运行一次完整 Claude Code 评估。

评估使用一个由 agent 容器通过网络访问的宿主机 task 环境和四种条件：

```text
base
fewshot
self
reflect-3
```

当用户要求你在这个工作区中运行评估时，该请求视为允许 Codex 作为主控组织实验，并用
Docker 内的 `claude -p` 启动隔离 Claude Code run。每个 skill-generation 和 solver
run 都必须放在干净、专属的 staged 目录中，并将该目录作为 Docker 内 `/work`
挂载。

启动隔离 agent run 前先读 `CODEX_ORCHESTRATOR.md`。正式 Claude Code 命令形态为：

```bash
CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config claude -p --permission-mode bypassPermissions --session-id "$CLAUDE_SESSION_ID" "$PROMPT"
```

`CLAUDE_CONFIG_DIR` 是该 agent 进程运行时临时设置的环境变量，不是任务 `.env`
配置。正式 attempt 不要使用 `--no-session-persistence`。每个进程必须使用
`agent_prompts.md` 中对应模式的固定 prompt，只替换声明的占位符，不追加提示或路径。

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
endpoint。GET endpoint 只按 `METHOD /path` 逐行列出，不附业务介绍。对于每个
允许的 POST endpoint，主 agent 必须核对实际运行时接口，并补充 content type、
必要鉴权 header、必填和可选 JSON 字段及其值类型，以及一条使用占位值的最小
请求示例。只写机械调用格式，不得暴露业务规则、隐藏值、标准答案、evaluator
行为或 task-specific 查询结果。Skill generation 和 test solving 可以使用业务
endpoint；只有 reflect skill generation 可以额外看到 `/api/judge`；执行 agent
不能看到 `/health` 或 reset/reseed endpoint。

`environment_access.md` 中非 judge POST endpoint 使用以下格式：

```text
POST /path
Content-Type: application/json
必要 headers：<header 名称和运行时值，或无>
JSON body：{"field": "<string>", "optional_field": ["<value>"]}
示例：curl ...
```

替换占位符后，示例必须可以直接运行，并与实际接口字段和鉴权位置一致。

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

每次 skill-generation run 都启动一个不带 `--rm` 的具名 agent 容器，并让
`CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` 留在容器内部，配合唯一 session ID。
需要认证时只读挂载最小的凭据引导文件，不要挂载宿主机 `.claude` 目录或完整配置树。
运行结束后保留停止状态的容器，使用 `docker cp` 只提取
`projects/<sanitized-cwd>/<claude_session_id>.jsonl` 中匹配的主 session 文件（必要时
先把 `projects/` 暂存到 `scratch/trace_extract/<run_id>/`），复制到：

```text
original_traces/skill_generation/<condition>/attempt_<nn>/<claude_session_id>.jsonl
```

从复制后的文件回填并核验用量和费用，确认 trace 与 metadata 均已落盘后，再删除
暂存目录和停止状态的容器。不要保存容器内完整配置、凭据、plugins、缓存、日志、
数据库，也不要把 stdout/stderr 当作 trace。

对应的用量记录写到：

```text
scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml
```

按照 solver run 相同的 `message.id` 去重规则从 session trace 回填各 token 桶，
再按 `metric_and_scoring.md` 中的价格计算费用。Skill-generation token 用量作为
evolve 用量单独报告，不计入 solver 效率指标。

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
- 包含容器可访问环境 URL、必要凭据、允许 endpoint 名称和上述 POST 请求格式的
  `environment_access.md`。
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

每次 solver attempt 都由 Codex 主控从该 attempt 目录启动一个不带 `--rm` 的
Dockerized Claude Code 进程。只挂载 attempt 目录，并让
`CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` 留在容器内部；需要认证时只读挂载
最小凭据引导文件，不要挂载完整 workspace、task group 或宿主机配置目录。

## 5. 打分与聚合

每个 solver 写出 `answer.json` 后，主 agent 调用当前 test task 的
`eval/eval.sh`，把 prediction 路径传入，并保存 `score.yaml`。

每个 solver attempt 都必须有唯一 `eval_attempt_id`：

```text
<task_group_id>__<condition>__<task_id>__attempt_<nn>__<timestamp>
```

该 ID 必须出现在 solver prompt、attempt 目录和 `run_metadata.yaml` 中。

运行结束后，先保留停止状态的容器，主 agent 根据唯一 session ID 从容器内的
`CLAUDE_CONFIG_DIR` 找到对应的 Claude Code 主 session JSONL，必要时只把
`projects/` 暂存到 `scratch/trace_extract/<run_id>/`。核对工作目录，并只把这个文件
复制到 `original_traces/`。从复制后的文件回填 token、费用、solver turn count 和
tool-call count。按 `message.id` 去重：input/cache 桶取任一条记录，
`output_tokens` 取同一 message id 的最大值，然后跨响应求和。

Claude Code session traces 应位于：

```text
original_traces/<condition>/<task_id>/attempt_<nn>/<claude_session_id>.jsonl
```

在 `run_metadata.yaml` 中记录复制后的主 session trace 路径。确认 trace、token、
费用、turn、tool-call 和 metadata 都已完整落盘后，再删除暂存目录和停止状态的
容器。不要保存完整的容器内 `CLAUDE_CONFIG_DIR` 或 stdout。如果 session trace
缺失或匹配不唯一，则 trace 路径写 `null`，token、turn 和 tool-call 字段也保持
`null`，记录原因，清理暂存目录和容器，并使用新的 session ID 重跑。

所有 runs 完成后，聚合四种条件的 `acc@3`、population `std@3`、各桶 token 和 solver turn count 和 tool-call counts。效率指标只统计
test solver 写答案的过程：先对同一个 test task 的 3 次 attempts 取平均，再对
5 个 test tasks 取平均。不要包含 skill generation、环境检查、evaluator
执行或主 agent 汇总。

另行把每个非 base 模式的 3 份 skill-generation trace 和
`evolve_metadata.yaml` 聚合到 report 顶层 `evolve` 区块。metadata 和 trace 路径
仅保留在工作区审计文件中。正式 report 只保留每次 attempt 的 token 和费用
字段，以及三次 attempt 的每个 token bucket 和美元费用算术平均值。

## 6. 解释结果

在报告中解释：

- 四种条件的整体 `acc@3` 和 population `std@3`。
- `fewshot`、`self` 和 `reflect-3` 相对 `base` 的提升。
- 哪些 test tasks 提升明显，哪些没有。
- 任何环境不稳定、输出 schema 摩擦、evaluator 问题或可疑泄漏风险。
