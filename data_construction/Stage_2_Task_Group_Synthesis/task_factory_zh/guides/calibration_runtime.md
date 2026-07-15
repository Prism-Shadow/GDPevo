# 校准运行方式与固定 Prompt

难度校准不使用主控系统的 subagent 机制。fewshot skill generation、base 和
fewshot 的每一次运行，都必须是 Docker 中独立启动的非交互式 Codex 进程。

## 隔离契约

每次运行都要新建 staged work 目录和专属 Codex home，只挂载这两个目录：

```text
scratch/calibration_runs/<run_kind>/<run_id>/work/       -> /work
scratch/calibration_runs/<run_kind>/<run_id>/codex_home/ -> /codex_home
```

不能挂载仓库、完整 task group、父目录、用户 home、`env/`、notes、evaluators、
该运行不允许看到的标准答案、其他 attempts 或 review 材料。

主控从 `env/Dockerfile` 构建环境镜像，并把环境容器与每个 calibration agent
接入主控创建的 Docker bridge network。环境以 `TASK_ENV_BIND=0.0.0.0` 监听，
`TASK_ENV_PORT` 取 `9000 + task group 数字编号`，network 别名固定为
`task-env`，且不映射宿主机端口。写入 `environment_access.md` 的地址是
`http://task-env:<TASK_ENV_PORT>/`，同时从 `env/endpoints.txt` 中取出当前运行
允许的全部业务 endpoint，以 `METHOD /path` 逐行写入，不附接口介绍。
base/fewshot 校准输入不能包含 `/health`、reset/reseed endpoint 或
`/api/judge`，环境实例设置 `TASK_ENV_ENABLE_JUDGE=0`。不能 staging 或挂载
环境源码。创建 bridge 时不能使用 `--internal`，以便 agent 通过 Docker 默认
NAT 和 DNS 保留模型 API 出站能力。

所有运行时名称都由主控生成，必须包含规范化后的 `GDPEVO_RUN_OWNER` 或当前
用户名、task group 编号、`cal`、运行类型、必要时的 task/attempt 和 8 位随机
suffix。例如 `gdp-<user_name>-013-cal-base-t001-a01-7f3a91c2-net`；环境容器和
agent 容器使用相同 scope，并分别以 `-env` 和 `-agent` 结尾。`task-env` 只能
作为 network 别名，不能作为全局固定容器名。

主控读取 `task_group.yaml` 中的 `env.state_mode`。`read_only` 环境可以在同一
calibration 阶段供多个并发 agent 共用；`mutable` 环境的每个 calibration
attempt 都使用独立 network 和新环境容器。只要命名唯一，主控可以按服务器能力
并发启动多个 attempt。

## Codex 命令

使用配置好的校准模型和 reasoning effort。主控创建 network 并确认环境健康后，
agent 统一使用以下启动形式：

```bash
docker run --rm \
  --name "$AGENT_CONTAINER_NAME" \
  --network "$NETWORK_NAME" \
  --env PROMPT \
  --mount type=bind,src="$WORK_DIR",dst=/work \
  --mount type=bind,src="$CODEX_HOME_DIR",dst=/codex_home \
  "$AGENT_IMAGE" \
  sh -lc 'CODEX_HOME=/codex_home codex exec -C /work -m <calibration_model> -c '\''model_reasoning_effort="<reasoning_effort>"'\'' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"'
```

`CODEX_HOME` 只是该进程运行时的临时变量。正式校准不能使用
`codex exec --ephemeral`；应把专属 `codex_home/` 下完整的
`rollout-*.jsonl` 保留为主 trace。校准记录还要保存模型、reasoning effort、
agent 和环境镜像、owner、network 和容器名、state mode、run id、staged 文件、
trace 路径和退出状态。

## Prompt 契约

每次 `codex exec` 只能使用下面对应的一份模板。只替换尖括号占位符，不能追加
task hints、答案摘要、rubric/evaluator 细节、notes、构造真值或 `/work` 外路径。

### Base Test Attempt

只 staging 当前 test 的 `input/` 和 `environment_access.md`。

```text
calibration_run_id: <unique_run_id>
run_type: base_test

Solve exactly one test task using only files staged in the current /work directory. Read input/prompt.txt and every file under input/payloads/. Use only the base URL, credentials, and allowed METHOD /path entries listed in environment_access.md to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
```

### Fewshot Skill Generation

Staging 5 个 train 的 `input/`、放在
`train_answers/<task_id>/answer.json` 的 5 个对应标准答案，以及
`environment_access.md`。不能 staging test 材料、notes、evaluators、judge
instructions 或其他 skill attempt。使用该 prompt 启动 3 个相互隔离的进程，
生成 3 个独立 skill package。

```text
calibration_run_id: <unique_run_id>
run_type: skill_generation
condition: fewshot

Generate one reusable skill package using only files staged in the current /work directory. Read all five train inputs from train_tasks/train_001/input/ through train_tasks/train_005/input/, including every payload, and the five matching standard answers from train_answers/train_001/answer.json through train_answers/train_005/answer.json. Use only the base URL, credentials, and allowed METHOD /path entries listed in environment_access.md to reach the running environment over the network. If any unexpected material is present in /work, stop and write contamination_report.txt. Otherwise create skill/ and write the reusable entry instructions to skill/SKILL.md without copying task-specific answer values. Keep any supporting files inside skill/.
```

每个进程结束后，把 `/work/skill/` 的全部内容保留为对应的 package root：

```text
scratch/train_skill/fewshot_attempt_01/SKILL.md
scratch/train_skill/fewshot_attempt_02/SKILL.md
scratch/train_skill/fewshot_attempt_03/SKILL.md
```

### Fewshot Test Attempt

只 staging 当前 test 的 `input/`、完整的 `skill/` 目录包和
`environment_access.md`。

```text
calibration_run_id: <unique_run_id>
run_type: fewshot_test

Solve exactly one test task using only files staged in the current /work directory. Read skill/SKILL.md and any files it references inside skill/, then read input/prompt.txt and every file under input/payloads/. Use only the base URL, credentials, and allowed METHOD /path entries listed in environment_access.md to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
```

## 运行有效性

一次运行只有在以下条件全部满足时才有效：

- `/work` 为新建目录，且只包含该模式允许的材料；
- 临时容器已在相同 Docker network 中通过
  `http://task-env:<TASK_ENV_PORT>/` 完成环境 health check；
- 进程生成了预期的 `answer.json` 或完整 skill package；
- 完整 Codex session trace 已保存，或明确记录了无法保存的原因；
- trace 中没有访问禁止材料；
- 评分由主 agent 在 Codex 进程之外执行。

受污染或不完整的运行不能计入 `avg@3`。保留原运行供审计，使用新的 run id
和干净目录重新执行。
