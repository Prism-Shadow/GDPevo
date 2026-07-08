# Codex 主控执行说明

Codex 是评估主控 agent。主控可以读取完整 task group，用于 staging 允许材料、
检查远程环境、调用 evaluator、保存 trace 和聚合 report，但不能直接解 test
tasks。

每次 skill generation 和每次 solver attempt 都必须作为独立的被测 agent
进程在 Docker 里运行。本 workspace 的被测 agent 是 Claude Code。

## Docker 隔离

容器只挂载当前 staged 目录和每个 attempt 专用的 Claude config 目录。不要挂载
完整 task group、完整 evaluation workspace、仓库根目录、上级 work 目录、home
目录、`env/`、`notes/`、evaluator 文件、源答案或之前的 runs。

容器需要网络，因为 Claude Code 需要访问模型 API，attempt 也可能需要访问
`GDPEVO_ENV_BASE_URL`。除非已经配置等价可用的代理，不要使用禁网容器。

## Claude Code 命令

使用本次运行配置的 Claude Code 模型。已发布 Claude Code workspace 使用
Claude Opus 4.8 和 `xhigh` effort。

Docker 内命令形态如下：

```bash
CLAUDE_CONFIG_DIR=/claude_config \
claude -p \
  --permission-mode bypassPermissions \
  --session-id "$CLAUDE_SESSION_ID" \
  "$PROMPT"
```

`CLAUDE_CONFIG_DIR=/claude_config` 是启动这一次 agent 进程时临时注入的运行时
环境变量。不要把它写进 `.env`、task 材料、生成的 skill 或 report，避免被误解为
任务环境配置。

模型和 effort 通过本次运行使用的 Claude Code 环境或配置设置；启动正式
attempt 前，应把实际观测到的值记录到 `scratch/`。不要加
`--no-session-persistence`，正式 attempt 必须留下 trace。

如果 `claude` 不在 `PATH` 中，应先定位它并把路径记录到 `scratch/`，不要在可复用
说明里写死某台机器的路径。

## Trace 保存

将原始 Claude Code session 文件作为主 trace 保存。创建 attempt trace 目录下的
Claude config 目录，仅在启动 agent 进程时设置
`CLAUDE_CONFIG_DIR=/claude_config`，传入唯一 `--session-id`，并保存下面的文件：

```text
original_traces/<condition>/<task_id>/attempt_<nn>/claude_config/projects/<sanitized-cwd>/<claude_session_id>.jsonl
```

stdout/stderr 命令运行日志不作为正式 trace 产物要求。不要使用
`--no-session-persistence`，也不要在 run 结束后依赖搜索用户全局 `~/.claude`
来猜测 trace。

一次 Docker run 只有在 `answer.json` 或 `SKILL.md`、以及主 session trace 或其
缺失原因都已保存后，才算完成。
