# GDPevo Cross-Task Skill Transfer Workspace

这个工作区用于做一组 Codex-only 的 3x3 skill 迁移热力图实验。

目标不是重新跑完整 benchmark，而是固定 3 个代表 task group，比较 `fewshot`
和 `reflect-3` 的既有 skill 向另外两个领域迁移时的表现。

## 核心矩阵

每张热力图使用同一组行列：

```text
CRM      task_group_002
ERP      task_group_006
Finance  task_group_010
```

- 行：skill 来源 task group。
- 列：测试目标 task group。
- 单元格：用行对应 task group 的 3 个既有独立 skill，分别求解列对应 task
  group 的 5 个 test tasks 后得到的 `acc`。
- source 和 target 相同的主对角线单元格不跑。

本工作区只产出两张图：

```text
fewshot
reflect-3
```

不运行 `base`、`self`，也不运行其他 harness。

## 目录

| Path | Purpose |
| --- | --- |
| `CODEX_ORCHESTRATOR.md` | Codex 主控、Docker 隔离、`codex exec` 命令形态和 trace 保存 |
| `RUN_SCOPE.md` | 本次 3x3 迁移实验的固定范围 |
| `heatmap_scope.json` | 脚本读取的 task group、mode、label 定义 |
| `guides/` | 运行流程、固定 solver prompt、skill mode、评分和报告格式 |
| `task_groups/` | 本次迁移实验的 3 个代表 task group |
| `skills/` | 按 source task group 组织的既有 `fewshot` 和 `reflect-3` skills |
| `runs/` | 每个 mode/source/target/test/attempt 的隔离求解记录 |
| `original_traces/` | 每个 solver attempt 跑完后复制进来的 Codex 原始 session trace |
| `report/cells/` | 每个 3x3 单元格的结构化评分报告 |
| `heatmaps/` | 聚合后的矩阵数据和 HTML 渲染页 |
| `scripts/` | 聚合并生成 heatmap HTML 的脚本 |

## 推荐启动 prompt

```text
请阅读 README.md、CODEX_ORCHESTRATOR.md、RUN_SCOPE.md 和 guides/。只运行 Codex 的 3x3 跨任务 skill
迁移实验，mode 只包括 fewshot 和 reflect-3。每个 source task group 使用 3 个既有独立
skill 计算三次运行平均值。每个 solver attempt 都隔离在 runs/ 下。将每个 cell report 写入
report/cells/，最后在 heatmaps/ 下生成两张热力图。将每个匹配到的 Codex
原始 trace 复制到 original_traces/。
Model: GPT-5.5, reasoning_effort: xhigh.
```

## 环境

每个 task-group 环境都固定在主控宿主机上以 `TASK_ENV_BIND=0.0.0.0` 启动，
并令 `TASK_ENV_PORT` 取 `9000 + task group 数字编号`。各自 `.env` URL 写成
`http://host.docker.internal:<TASK_ENV_PORT>/`，每个 solver 容器都必须带
`--add-host=host.docker.internal:host-gateway`。这个 workspace 不重新生成 skill。
solver run 不能进入、列出、读取或挂载 `task_groups/*/env/`，只能使用主 agent
staging 给它们的容器可访问环境入口。

## 隔离 Solver Runs

当用户要求运行这个 workspace 时，该请求视为允许 Codex 作为主控组织实验，并用
Docker 内的 `codex exec` 启动隔离 solver run。所有 test attempts 都应由干净、
隔离的 Docker run 完成。如果所需 runs 数量超过实际并发能力，就分批运行，直到
所有 attempts 完成。

除非用户明确覆盖，否则使用 `heatmap_scope.json` 里的模型配置：

```text
model: GPT-5.5
reasoning_effort: xhigh
```

不要减少 attempt 数量，不要把多道 test tasks 合并到同一个 solver run，也不要由
main agent 直接解题。

使用 `CODEX_ORCHESTRATOR.md` 中的命令形态，并在启动 solver 进程时临时设置每个
attempt 专用的 `CODEX_HOME=/codex_home`。`CODEX_HOME` 不是任务 `.env` 配置。
正式 attempt 不要使用 `codex exec --ephemeral`。
每次运行都必须原样使用 `guides/agent_prompts.md` 中的固定 prompt，只替换其中
声明的占位符。

## 产出

完成后应至少包含：

```text
report/cells/fewshot/<source>__to__<target>.yaml
report/cells/reflect-3/<source>__to__<target>.yaml
report/matrix.yaml
report/matrix.json
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/
heatmaps/data/fewshot_matrix.csv
heatmaps/data/reflect-3_matrix.csv
heatmaps/data/matrices.json
heatmaps/index.html
```

生成聚合与 HTML：

```bash
python3 scripts/build_heatmaps.py
```

打开 `heatmaps/index.html` 即可查看两张 3x3 热力图。
