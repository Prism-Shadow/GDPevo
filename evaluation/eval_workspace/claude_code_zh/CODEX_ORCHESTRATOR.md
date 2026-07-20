# Codex 主控执行说明

Codex 是评估主控 agent。主控可以读取完整 task group，用于 staging 允许材料、
启动并检查环境、调用 evaluator、保存 trace 和聚合 report，但不能直接解 test
tasks。

每次 skill generation 和每次 solver attempt 都必须作为独立的被测 agent
进程在 Docker 里运行。本 workspace 的被测 agent 是 Claude Code。

## Docker 隔离

容器只挂载当前 staged 目录。如果需要认证或配置 bootstrap，只以只读方式挂载最小
必需文件到专用路径；不要挂载宿主机 `.claude` 目录、home 目录或完整 Claude 运行时
目录。`CLAUDE_CONFIG_DIR` 在容器内部设置为 `/tmp/gdpevo-claude-config`。不要挂载
完整 task group、完整 evaluation workspace、仓库根目录、上级 work 目录、`env/`、
`notes/`、evaluator 文件、源答案或之前的 runs。

主控从 `env/Dockerfile` 构建环境镜像，并把环境容器和 agent 接入主控创建的
Docker bridge network。环境监听 `0.0.0.0:<TASK_ENV_PORT>`，network 别名为
`task-env`，不映射宿主机端口；agent 通过
`http://task-env:<TASK_ENV_PORT>/` 访问，并保留模型 API 出站能力。不能把
bridge 创建为 `--internal` network；必须保留 Docker 默认的出站 NAT 和 DNS。
不能把 `env/` staging 或挂载进 agent 容器。
如果缺少 `env/Dockerfile` 或 `env.state_mode`，应停止并报告这是不兼容的旧版
task group，不能退回宿主机环境方案。

所有名称由主控而不是被测 agent 生成。名称必须包含规范化后的 `<user_name>`、
task group 编号、权限阶段、必要时的 condition/task/attempt 和 8 位随机 suffix；
例如 `gdp-<user_name>-013-test-few-t001-a01-7f3a91c2-net`。容器使用相同 scope，
并分别以 `-env` 和 `-agent` 结尾。`task-env` 只能作为当前 network 的别名，
不能作为全局固定容器名。

主控从 `task_group.yaml` 读取 `env.state_mode`。`read_only` 环境可以在同一个
权限阶段供多个 attempt 并发共享；`mutable` 环境的每个 attempt 都使用新的
network、环境容器和可写层，可按服务器能力并发运行。开启 judge 的 reflect
skill generation 必须与关闭 judge 的 calibration、其他 skill generation 和
正式 test 分开。test 环境设置 `TASK_ENV_ENABLE_JUDGE=0`。正式运行前，必须从
同一 network 上的临时容器通过 agent 实际 URL 检查 `/health`。

## Claude Code 命令

使用本次运行配置的 Claude Code 模型。已发布 Claude Code workspace 使用
Claude Opus 4.8 和 `xhigh` effort。

Docker 内命令形态如下：

```bash
CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config \
claude -p \
  --permission-mode bypassPermissions \
  --session-id "$CLAUDE_SESSION_ID" \
  "$PROMPT"
```

`CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config` 是启动这一次 agent 进程时临时注入的运行时
环境变量。不要把它写进 `.env`、task 材料、生成的 skill 或 report，避免被误解为
任务环境配置。

模型和 effort 通过本次运行使用的 Claude Code 环境或配置设置；启动正式
attempt 前，应把实际观测到的值记录到 `scratch/`。不要加
`--no-session-persistence`，正式 attempt 必须留下 trace。

如果 `claude` 不在 `PATH` 中，应先定位它并把路径记录到 `scratch/`，不要在可复用
说明里写死某台机器的路径。

## 固定 Prompt 契约

`$PROMPT` 必须使用 `guides/agent_prompts.md` 中对应模式的模板，只替换其中声明的
占位符。不要追加提示、答案摘要、notes、rubric/evaluator 细节或额外路径。信息边界
由 staged `/work` 内容和 Docker 挂载强制保证，prompt 只负责说明当前 run。

## Trace 保存

每次 run 只保存一个完整的 Claude Code 主 session JSONL。运行时 config 始终位于
命名容器内部，绝不作为宿主机目录挂载。创建容器时不要使用 `--rm`；Claude 退出后
先保留 stopped container，直到 trace 和 metadata 核验完成。在容器内设置
`CLAUDE_CONFIG_DIR=/tmp/gdpevo-claude-config`，并传入唯一 `--session-id`。使用
`docker cp` 直接复制准确的 session 文件；需要发现路径时，只把 `projects/` 子目录
临时提取到 `scratch/trace_extract/<run_id>/`：

```text
/tmp/gdpevo-claude-config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
```

核对 session ID 和工作目录后，只把这一个 JSONL 复制到：

```text
original_traces/skill_generation/<condition>/attempt_<nn>/<claude_session_id>.jsonl
original_traces/<condition>/<task_id>/attempt_<nn>/<claude_session_id>.jsonl
```

每次 skill generation 还要写入对应的 token 与费用记录：

```text
scratch/skill_generation/<condition>_attempt_<nn>/evolve_metadata.yaml
```

先用复制后的主 session JSONL 回填并核验 token、费用、turn 和 tool-call 数据。确认
answer 或 skill、复制后的 trace（或缺失原因）和 metadata 都已写入宿主机后，删除临时
提取目录，再删除 stopped container。不要归档容器内完整 config，其中的配置、凭据、
plugins、缓存、日志、数据库或其他运行状态都不属于 trace。stdout/stderr 命令运行日志
不作为正式 trace 产物要求。不要使用 `--no-session-persistence`，也不要在 run 结束后
依赖搜索用户全局 `~/.claude` 来猜测 trace。如果目标 session 文件缺失或匹配不唯一，
记录原因并使用新的 session ID 重跑。

一次 Docker run 只有在 `answer.json` 或以 `skill/SKILL.md` 为入口的完整 `skill/`
目录包、主 session trace 或其缺失
原因，以及对应的 run/evolve metadata 都已保存后，才算完成。
