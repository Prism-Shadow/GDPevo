# Codex 主控执行说明

Codex 是评估主控 agent。主控可以读取完整 task group，用于 staging 允许材料、
启动并检查环境、调用 evaluator、保存 trace 和聚合 report，但不能直接解 test
tasks。

每次 skill generation 和每次 solver attempt 都必须作为独立的被测 agent
进程在 Docker 里运行。本 workspace 的被测 agent 是 Codex。

## Docker 隔离

容器只挂载当前 staged 目录。如果需要认证，只以只读方式挂载最小的 bootstrap
凭据，例如 `/run/gdpevo-bootstrap/auth.json`；不要挂载宿主机的 `CODEX_HOME`、
home 目录或任何完整运行时目录。agent 的 `CODEX_HOME` 在容器内部创建，例如
`/tmp/gdpevo-codex-home`。不要挂载完整 task group、完整 evaluation workspace、
仓库根目录、上级 work 目录、`env/`、`notes/`、evaluator 文件、源答案或之前的 runs。

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

先在主控侧记录当前可用的认证来源，但不要把它作为 agent 的运行时 home：

```bash
HOST_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
```

每次 skill generation 和 solver attempt 都要创建一个不带 `--rm` 的命名 agent 容器。
如果需要认证，只读挂载认证文件，并在启动 Codex 前把它复制到容器内部的运行时 home：

```bash
test -f "$HOST_CODEX_HOME/auth.json" || {
  echo "Evaluation blocked: active Codex auth.json was not found" >&2
  exit 1
}
docker create --name "$CONTAINER_NAME" \
  ... \
  -v "$HOST_CODEX_HOME/auth.json:/run/gdpevo-bootstrap/auth.json:ro" \
  ...
```

容器内的 wrapper 应初始化并使用内部 home，例如：

```bash
export CODEX_HOME=/tmp/gdpevo-codex-home
install -d -m 700 "$CODEX_HOME"
install -m 600 /run/gdpevo-bootstrap/auth.json "$CODEX_HOME/auth.json"
CODEX_HOME="$CODEX_HOME" codex login status
```

不要复制或挂载完整 Codex home，也不要复制 `config.toml`、历史 sessions、数据库、
日志、skills、plugins、缓存或其他状态。模型和思考强度由启动参数明确指定。绝不能把
`auth.json` staging 到 `/work`，也不能把它保留为实验产物。如果容器内 home 无法初始化
或登录无效，应在正式 attempt 前将 run 标记为 blocked。

正式启动前，必须在同一个容器内部的运行时 home 中完成登录检查。只有确认当前登录
有效后才能继续；否则应停止并报告该 run 被阻塞，不能启动未认证的 attempt，也不能让
主控代跑。

Docker 内命令形态如下：

```bash
CODEX_HOME=/tmp/gdpevo-codex-home \
codex exec \
  -C /work \
  -m gpt-5.5 \
  -c 'model_reasoning_effort="xhigh"' \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$PROMPT"
```

`CODEX_HOME=/tmp/gdpevo-codex-home` 是启动这一次 agent 进程时临时注入的运行时环境变量。
不要把它写进 `.env`、task 材料、生成的 skill 或 report，避免被误解为任务环境配置。

外层 Docker 已提供硬隔离时，`--dangerously-bypass-approvals-and-sandbox` 是用于非交互运行的开放权限口径。不要加 `--ephemeral`，正式 attempt 必须留下 trace。

如果 `codex` 不在 `PATH` 中，应先定位它并把路径记录到 `scratch/`，不要在可复用
说明里写死某台机器的路径。

## 固定 Prompt 契约

`$PROMPT` 必须使用 `guides/agent_prompts.md` 中对应模式的模板，只替换其中声明的
占位符。不要追加提示、答案摘要、notes、rubric/evaluator 细节或额外路径。信息边界
由 staged `/work` 内容和 Docker 挂载强制保证，prompt 只负责说明当前 run。

## Trace 保存

只保存 Codex 的主 session JSONL。运行时 home 始终位于命名容器内部，绝不作为宿主机
目录挂载。创建容器时不要使用 `--rm`；agent 退出后先保留 stopped container，直到
trace 和 metadata 核验完成。使用 `docker cp` 只把容器内
`/tmp/gdpevo-codex-home/sessions/` 临时提取到 `scratch/trace_extract/<run_id>/`，
或直接复制已知的 rollout 文件。只选择一个同时匹配 run id 和 `/work` 路径的
`rollout-*.jsonl`，再把这个文件复制到：

```text
original_traces/<condition>/<task_id>/attempt_<nn>/rollout-*.jsonl
```

后续 token、费用、轮次、工具调用、污染检查和 metadata 都读取复制后的 JSONL。
这些字段完整回填并核验后，才能删除临时提取目录和容器。不要保存容器内完整的
`CODEX_HOME`，其中的配置、凭据、日志、skills、plugins、缓存、数据库和其他运行
状态都不属于 trace。stdout/stderr 命令运行日志也不作为正式 trace 产物；不要把
stdout JSONL 当成原始 `rollout-*.jsonl` 的替代品，也不要在 run 结束后搜索用户全局
`~/.codex` 来猜测 trace。文件缺失或无法唯一匹配时，记录原因并清理临时提取目录，
删除 stopped container，使用新的 run id 重跑，不要随意挑选文件。

一次 Docker run 只有在 `answer.json` 或以 `skill/SKILL.md` 为入口的完整 `skill/`
目录包、主 session trace 或其缺失原因，以及对应的 metadata 和容器清理记录都已
保存后，才算完成。
