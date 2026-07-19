# Codex 主控执行说明

Codex 是迁移热力图实验的主控 agent。主控可以读取 staged task groups，用于
staging 允许材料、调用 evaluator、保存 trace、聚合 cell reports 和渲染
heatmaps，但不能直接解目标 test tasks。

每次 solver attempt 都必须作为独立的 Codex 进程在 Docker 里运行。本 workspace
不生成新 skill。

## Docker 隔离

容器只挂载当前 solver attempt 目录和每个 attempt 专用的临时 Codex home。不要挂载
完整 `task_groups/` 树、完整 evaluation workspace、仓库根目录、上级 work
目录、home 目录、`env/`、notes、evaluator 文件、源答案或之前的 runs。

容器需要网络，因为 Codex 需要访问模型 API，attempt 还需要访问目标 task
group 的环境。环境固定在主控宿主机以 `TASK_ENV_BIND=0.0.0.0` 启动；每个
solver 容器都带 `--add-host=host.docker.internal:host-gateway`，并通过
`http://host.docker.internal:<TASK_ENV_PORT>/` 访问。不能挂载环境文件。

## Codex 命令

除非用户明确覆盖，使用 `heatmap_scope.json` 中的模型配置。默认是 `GPT-5.5`
和 `xhigh` reasoning effort。

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

`CODEX_HOME=/codex_home` 是启动这一次 solver 进程时临时注入的运行时环境变量。
不要把它写进 `.env`、task 材料、生成的 skill 或 report，避免被误解为任务环境配置。

不要加 `--ephemeral`，正式 attempt 必须留下 trace。

只能使用 `guides/agent_prompts.md` 中固定的 test-solver prompt，并只替换其中
声明的占位符。不能追加 task hint、答案摘要、evaluator 细节或其他文件路径。

## Trace 保存

只保存 Codex 的主 session JSONL。临时 Codex home 放在
`scratch/runtime_homes/`，仅在启动 solver 进程时设置
`CODEX_HOME=/codex_home`。进程结束后，把唯一匹配当前 run 的
`sessions/.../rollout-*.jsonl` 复制到：

```text
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/rollout-*.jsonl
```

确认复制的文件包含预期 run id 和 `/work` 路径后，先回填并核验
`run_metadata.yaml` 及 trace 派生的 token 字段，完成后才能删除整个临时 Codex home。
不要归档其中的配置、凭据、plugins、skills、缓存、日志、数据库或其他运行状态。
stdout/stderr 命令运行日志不作为正式 trace 产物要求；不要把 stdout JSONL 当成
原始 `rollout-*.jsonl` session trace 的替代品，也不要在 run 结束后搜索用户全局
`~/.codex` 来猜测 trace。
