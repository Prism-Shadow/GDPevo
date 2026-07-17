# Codex 主控执行说明

Codex 是评估主控 agent。主控可以读取完整 task group，用于 staging 允许材料、
启动并检查环境、调用 evaluator、保存 trace 和聚合 report，但不能直接解 test
tasks。

每次 skill generation 和每次 solver attempt 都必须作为独立的被测 agent
进程在 Docker 里运行。本 workspace 的被测 agent 是 Codex。

## Docker 隔离

容器只挂载当前 staged 目录和每个 attempt 专用的 Codex home。不要挂载完整
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

将原始 Codex session 文件作为主 trace 保存。原始 session trace 通过每个
attempt 的专用 `CODEX_HOME` 落盘：创建 attempt trace 目录下的 Codex home，
仅在启动 agent 进程时设置 `CODEX_HOME=/codex_home`，并保存下面的文件：

```text
original_traces/<condition>/<task_id>/attempt_<nn>/codex_home/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl
```

stdout/stderr 命令运行日志不作为正式 trace 产物要求。不要把 stdout JSONL 当成
原始 `rollout-*.jsonl` session trace 的替代品，也不要在 run 结束后依赖搜索用户
全局 `~/.codex` 来猜测 trace。

一次 Docker run 只有在 `answer.json` 或以 `skill/SKILL.md` 为入口的完整 `skill/`
目录包、以及主 session trace 或其
缺失原因都已保存后，才算完成。
