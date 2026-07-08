# Codex 主控执行说明

Codex 是迁移热力图实验的主控 agent。主控可以读取 staged task groups，用于
staging 允许材料、调用 evaluator、保存 trace、聚合 cell reports 和渲染
heatmaps，但不能直接解目标 test tasks。

每次 solver attempt 都必须作为独立的 Codex 进程在 Docker 里运行。本 workspace
不生成新 skill。

## Docker 隔离

容器只挂载当前 solver attempt 目录和每个 attempt 专用的 Codex home。不要挂载
完整 `task_groups/` 树、完整 evaluation workspace、仓库根目录、上级 work
目录、home 目录、`env/`、notes、evaluator 文件、源答案或之前的 runs。

容器需要网络，因为 Codex 需要访问模型 API，attempt 也可能需要访问目标 task
group 的远程环境 URL。

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

## Trace 保存

将原始 Codex session 文件作为主 trace 保存。原始 session trace 通过每个
attempt 的专用 `CODEX_HOME` 落盘：创建 attempt trace 目录下的 Codex home，
仅在启动 solver 进程时设置 `CODEX_HOME=/codex_home`，并保存下面的文件：

```text
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/codex_home/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

stdout/stderr 命令运行日志不作为正式 trace 产物要求。不要把 stdout JSONL 当成
原始 `rollout-*.jsonl` session trace 的替代品，也不要在 run 结束后依赖搜索用户
全局 `~/.codex` 来猜测 trace。
