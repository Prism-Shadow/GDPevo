# Workflow

本工作区只运行 Codex harness 的跨 task group skill 迁移实验，不重新生成 skill。

当用户要求运行这个 workspace 时，该请求视为允许 Codex 作为主控组织实验，并用
Docker 内的 `codex exec` 启动隔离 solver run。每个 solver run 都必须在干净、
独立的 attempt 目录中完成，并将该目录作为 Docker 内 `/work` 挂载。如果所需
runs 数量超过实际并发能力，就分批运行，直到所有 attempts 完成。不要减少
attempt 数量，不要把多道 test tasks 合并到同一个 solver run，也不要由 main agent
直接解题。

启动 solver run 前先读 `CODEX_ORCHESTRATOR.md`。正式命令形态为：

```bash
CODEX_HOME=/codex_home codex exec -C /work -m gpt-5.5 -c 'model_reasoning_effort="xhigh"' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"
```

`CODEX_HOME` 是该 solver 进程运行时临时设置的环境变量，不是任务 `.env` 配置。
正式 attempt 不要使用 `codex exec --ephemeral`。只能使用
`guides/agent_prompts.md` 中的固定 prompt，并只替换声明的占位符。

覆盖 `CODEX_HOME` 前先保存当前可用的 Codex home。每个临时 run home 只复制其中
的 `auth.json`，权限设为 `0600`，并使用
`CODEX_HOME=/codex_home codex login status` 验证挂载后的登录状态。认证缺失时该
run 应直接判定为 blocked，不能复制完整 Codex home。

除非用户明确覆盖，否则使用 `heatmap_scope.json` 里的模型配置：

```text
model: GPT-5.5
reasoning_effort: xhigh
```

运行前请先读：

1. `README.md`
2. `RUN_SCOPE.md`
3. `guides/skill_modes.md`
4. `guides/metric_and_scoring.md`
5. `guides/report_format.md`

## 1. Check Scope

确认 `task_groups/` 下只有本次范围内的 3 个代表 task group：

```text
task_group_002
task_group_006
task_group_010
```

确认 `heatmap_scope.json` 与 `RUN_SCOPE.md` 一致。

## 2. 启动并检查环境

在主控宿主机上以 `TASK_ENV_BIND=0.0.0.0` 和三个不同端口启动环境，并在
`.env` 中写入：

```text
GDPEVO_TASK_GROUP_002_ENV_BASE_URL=http://host.docker.internal:<TG002_PORT>/
GDPEVO_TASK_GROUP_006_ENV_BASE_URL=http://host.docker.internal:<TG006_PORT>/
GDPEVO_TASK_GROUP_010_ENV_BASE_URL=http://host.docker.internal:<TG010_PORT>/
```

每个 solver `docker run` 都必须带
`--add-host=host.docker.internal:host-gateway`。开始计分运行前，先从临时容器
通过完全相同的配置 URL 验证每个 health/index endpoint。

主 agent 可以检查 `task_groups/*/env/` 和 evaluator，用于确认环境契约、staging
材料和评分。solver 进程不允许进入、列出、读取或挂载任何 `env/` 源文件。

## 3. Check Source Skills

确认下列既有 skills 已经存在：

```text
skills/fewshot/<source_task_group_id>/fewshot_attempt_01/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_02/SKILL.md
skills/fewshot/<source_task_group_id>/fewshot_attempt_03/SKILL.md

skills/reflect-3/<source_task_group_id>/reflect-3_attempt_01/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_02/SKILL.md
skills/reflect-3/<source_task_group_id>/reflect-3_attempt_03/SKILL.md
```

同一个 source/mode 下的 3 个 attempt skills 必须彼此独立。如果缺少任何必要
skill，应停止并报告缺失产物，不要现场重新生成。

## 4. Run Cross-Task Solvers

对每个 mode、非对角线 source/target 组合、test task、attempt 建立独立求解目录：

```text
runs/<mode>/<source_task_group_id>__to__<target_task_group_id>/test_001/attempt_01/
```

每个 attempt 目录只放：

- 当前 target test task 的 `input/`。
- `environment_access.md`，只含 target task group 的容器可访问环境入口。
- 当前 source task group、mode 和 attempt 编号对应的完整 skill 目录包，以
  `skill/` staging，入口文件为 `skill/SKILL.md`。

不要 staging：

- `env/`
- train tasks
- source `output/answer.json`
- test 标准答案
- test notes
- evaluator files
- 其他 attempt 的 run 文件

solver 输出：

```text
answer.json
run_metadata.yaml
```

每个 solver attempt 都必须由 clean-context Dockerized Codex run 使用配置好的模型和
思考强度完成。main agent 负责 staging attempt 目录、启动隔离 solver run，并在
solver 写出 `answer.json` 后评分和聚合。

原样使用 `guides/agent_prompts.md` 中的固定 solver prompt，不能追加内容。

## 5. Score

主 agent 在 solver 完成后调用 target test task 的 evaluator，保存：

```text
runs/<mode>/<source>__to__<target>/test_001/attempt_01/score.yaml
```

每个 attempt 必须有唯一 `eval_attempt_id`：

```text
transfer__<mode>__<source>__to__<target>__<test_id>__attempt_<nn>__<timestamp>
```

评分后，从 attempt 专用的临时 `CODEX_HOME` 读取 solver 的 Codex 原始 session
trace，确认它与当前 run 匹配，并只复制该文件到：

```text
original_traces/<mode>/<source>__to__<target>/<test_id>/attempt_<nn>/rollout-*.jsonl
```

应确认 trace 使用预期 attempt 目录，并且包含匹配的 `eval_attempt_id`。这个原始
session 文件是主 trace。在 `run_metadata.yaml` 中记录复制后的 session trace 路径，
回填并核验 trace 派生的 token 字段，完成后才能删除整个临时 Codex home；不要保存
完整 home 或 stdout。如果原始 session trace 缺失或匹配不唯一，将 trace 路径写为
`null`，记录原因，清理临时 home，并使用新的 run ID 重跑。

token usage 可以在 `run_metadata.yaml` 里记录，但 heatmap 默认只使用 score。

## 6. Aggregate And Render

每个非对角线 `<mode>/<source>__to__<target>` 写一个 cell report：

```text
report/cells/<mode>/<source>__to__<target>.yaml
```

全部 12 个 cell report 完成后运行：

```bash
python3 scripts/build_heatmaps.py
```

脚本会生成：

```text
report/matrix.yaml
report/matrix.json
heatmaps/data/matrices.json
heatmaps/data/fewshot_matrix.csv
heatmaps/data/reflect-3_matrix.csv
heatmaps/index.html
```

打开 `heatmaps/index.html` 查看两张 3x3 热力图。

## 7. Contamination Handling

如果 solver/test attempt 访问了 forbidden material，停止使用该结果：

1. 在该 attempt 目录写入污染说明。
2. 不 score、不聚合该 attempt。
3. 在新的 clean attempt 目录重跑。
4. 在 cell report 的 `notes` 或 `excluded_attempts` 中记录。

匹配 source/mode/attempt 的既有 skill 目录包是允许材料。test solver 不能直接读取 source
或 target 的 train tasks、标准答案、notes、evaluator、env 源文件或其他 run 目录。
