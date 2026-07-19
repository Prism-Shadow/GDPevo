# Codex 主控执行说明

Codex 是迁移热力图实验的主控 agent。主控可以读取 staged task groups，用于
staging 允许材料、调用 evaluator、保存 trace、聚合 cell reports 和渲染
heatmaps，但不能直接解目标 test tasks。

每次 solver attempt 都必须作为独立的 Codex 进程在 Docker 里运行。本 workspace
不生成新 skill。

## Docker 隔离

容器只挂载当前 solver attempt 目录。如果需要认证，只以只读方式挂载最小的
凭据/bootstrap 文件，例如 `/run/gdpevo-bootstrap/auth.json`；不要挂载宿主机的
`CODEX_HOME`、home 目录或任何完整运行时目录。agent 的运行时 home 在容器内部创建为
`/tmp/gdpevo-codex-home`。不要挂载完整 `task_groups/` 树、完整 evaluation
workspace、仓库根目录、上级 work 目录、home 目录、`env/`、notes、evaluator 文件、
源答案或之前的 runs。

容器需要网络，因为 Codex 需要访问模型 API，attempt 还需要访问目标 task
group 的环境。环境固定在主控宿主机以 `TASK_ENV_BIND=0.0.0.0` 启动；每个
solver 容器都带 `--add-host=host.docker.internal:host-gateway`，并通过
`http://host.docker.internal:<TASK_ENV_PORT>/` 访问。不能挂载环境文件。

## Codex 命令

除非用户明确覆盖，使用 `heatmap_scope.json` 中的模型配置。默认是 `GPT-5.5`
和 `xhigh` reasoning effort。

先记录主控当前可用的认证来源，但不要把它作为 agent 的运行时 home：

```bash
HOST_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
```

每个 solver attempt 都创建一个不带 `--rm` 的命名 agent 容器。如果需要认证，只读
挂载 `$HOST_CODEX_HOME/auth.json` 到 `/run/gdpevo-bootstrap/auth.json`，并在容器内
初始化运行时 home：

```bash
export CODEX_HOME=/tmp/gdpevo-codex-home
install -d -m 700 "$CODEX_HOME"
install -m 600 /run/gdpevo-bootstrap/auth.json "$CODEX_HOME/auth.json"
CODEX_HOME="$CODEX_HOME" codex login status
```

不要复制 `config.toml` 或其他 Codex 状态，不能把凭据 staging 到 `/work`，也不能将其
保留为实验产物。如果容器内 home 无法初始化或登录无效，应在启动 solver 前将 run
标记为 blocked。

正式启动前，必须在同一个具名容器及其容器内 home 中执行 `codex login status`。
只有确认登录有效后才能继续；认证缺失或失效时，该 run 应直接判定为 blocked，不能
让主控代替被测 solver 运行。

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

`CODEX_HOME=/tmp/gdpevo-codex-home` 是启动这一次 solver 进程时临时注入的运行时环境变量。
不要把它写进 `.env`、task 材料、生成的 skill 或 report，避免被误解为任务环境配置。

不要加 `--ephemeral`，正式 attempt 必须留下 trace。

只能使用 `guides/agent_prompts.md` 中固定的 test-solver prompt，并只替换其中
声明的占位符。不能追加 task hint、答案摘要、evaluator 细节或其他文件路径。

## Trace 保存

只保存 Codex 的主 session JSONL。运行时 home 始终位于命名容器内部，绝不作为宿主机
目录挂载。创建容器时不要使用 `--rm`；solver 退出后先保留 stopped container，直到
trace 和 metadata 核验完成。使用 `docker cp` 只把容器内
`/tmp/gdpevo-codex-home/sessions/` 临时提取到 `scratch/trace_extract/<run_id>/`，
或直接复制已知的 rollout 文件。只选择一个匹配当前 run 的
`sessions/.../rollout-*.jsonl`，再把这个文件复制到：

```text
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/rollout-*.jsonl
```

确认复制的文件包含预期 run id 和 `/work` 路径后，先回填并核验
`run_metadata.yaml` 及 trace 派生的 token 字段。写入 answer、score、复制后的 trace
（或缺失原因）和 metadata 后，删除临时提取目录，再删除 stopped container。不要归档
容器内完整 home，其中的配置、凭据、plugins、skills、缓存、日志、数据库或其他运行
状态都不属于 trace。stdout/stderr 命令运行日志不作为正式 trace 产物要求；不要把
stdout JSONL 当成原始 `rollout-*.jsonl` session trace 的替代品，也不要在 run 结束后
搜索用户全局 `~/.codex` 来猜测 trace。文件缺失或无法唯一匹配时，记录原因并用新的
run id 重跑。
