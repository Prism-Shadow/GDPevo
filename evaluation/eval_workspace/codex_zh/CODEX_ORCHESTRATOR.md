# Codex 主控执行说明

Codex 是评估主控 agent。主控可以读取完整 task group，用于 staging 允许材料、
启动并检查环境、调用 evaluator、保存 trace 和聚合 report，但不能直接解 test
tasks。

每次 skill generation 和每次 solver attempt 都必须作为独立的被测 agent
进程在 Docker 里运行。本 workspace 的被测 agent 是 Codex。

## Docker 隔离

容器只挂载当前 staged 目录和每个 attempt 专用的临时 Codex home。不要挂载完整
task group、完整 evaluation workspace、仓库根目录、上级 work 目录、home
目录、`env/`、`notes/`、evaluator 文件、源答案或之前的 runs。

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

## Codex 命令

使用本次运行配置的模型。已发布 Codex workspace 使用 `gpt-5.5` 和 `xhigh`
reasoning effort。

在改写 `CODEX_HOME` 前，先在主控侧保存当前可用的 Codex home：

```bash
HOST_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
```

每次 skill generation 和 solver attempt 都要新建临时 home，并且只继承登录凭据：

```bash
install -d -m 700 "$CODEX_HOME_DIR"
test -f "$HOST_CODEX_HOME/auth.json" || {
  echo "Evaluation blocked: active Codex auth.json was not found" >&2
  exit 1
}
install -m 600 "$HOST_CODEX_HOME/auth.json" "$CODEX_HOME_DIR/auth.json"
```

这一步由主控在宿主机上完成，然后再把临时目录挂载为 `/codex_home`。不要复制
整个 Codex home，也不要复制 `config.toml`、历史 sessions、数据库、日志、skills、
plugins、缓存或其他状态。模型和思考强度由启动参数明确指定。绝不能把
`auth.json` staging 到 `/work`，也不能把它保留为实验产物。

正式启动前，必须使用相同的 agent image 和临时 home 挂载，执行
`CODEX_HOME=/codex_home codex login status`。只有确认当前登录有效后才能继续；
否则应停止并报告该 run 被阻塞，不能启动未认证的 attempt，也不能让主控代跑。

Docker 内命令形态如下：

```bash
CODEX_HOME=/codex_home \
codex exec \
  -C /work \
  -m gpt-5.5 \
  -c 'model_reasoning_effort="xhigh"' \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$PROMPT"
```

`CODEX_HOME=/codex_home` 是启动这一次 agent 进程时临时注入的运行时环境变量。
不要把它写进 `.env`、task 材料、生成的 skill 或 report，避免被误解为任务环境配置。

外层 Docker 已提供硬隔离时，`--dangerously-bypass-approvals-and-sandbox` 是用于非交互运行的开放权限口径。不要加 `--ephemeral`，正式 attempt 必须留下 trace。

如果 `codex` 不在 `PATH` 中，应先定位它并把路径记录到 `scratch/`，不要在可复用
说明里写死某台机器的路径。

## 固定 Prompt 契约

`$PROMPT` 必须使用 `guides/agent_prompts.md` 中对应模式的模板，只替换其中声明的
占位符。不要追加提示、答案摘要、notes、rubric/evaluator 细节或额外路径。信息边界
由 staged `/work` 内容和 Docker 挂载强制保证，prompt 只负责说明当前 run。

## Trace 保存

只保存 Codex 的主 session JSONL。每次 skill generation 和 solver attempt 都使用
位于 `original_traces/` 外的临时 `CODEX_HOME`，仅在启动 agent 进程时设置
`CODEX_HOME=/codex_home`。进程结束后，从临时 home 的
`sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl` 中找到唯一匹配当前 run id 和
`/work` 路径的文件，并复制到：

```text
original_traces/<condition>/<task_id>/attempt_<nn>/rollout-*.jsonl
```

后续 token、费用、轮次、工具调用、污染检查和 metadata 都读取复制后的 JSONL。
这些字段完整回填并核验后，才能删除整个临时 Codex home。不要保存完整
`CODEX_HOME`，其中的配置、凭据、日志、skills、
plugins、缓存、数据库和其他运行状态都不属于 trace。stdout/stderr 命令运行日志
也不作为正式 trace 产物；不要把 stdout JSONL 当成原始 `rollout-*.jsonl` 的
替代品，也不要在 run 结束后搜索用户全局 `~/.codex` 来猜测 trace。文件缺失或
无法唯一匹配时，记录原因并使用新的 run id 重跑，不要随意挑选文件。

一次 Docker run 只有在 `answer.json` 或以 `skill/SKILL.md` 为入口的完整 `skill/`
目录包、主 session trace 或其缺失原因，以及临时 Codex home 已清理的记录都已
保存后，才算完成。
