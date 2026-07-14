# 校准运行方式与固定 Prompt

难度校准不使用主控系统的 subagent 机制。Blind-train、skill-distillation、
base 和 fewshot 的每一次运行，都必须是 Docker 中独立启动的非交互式
Codex 进程。

## 隔离契约

每次运行都要新建 staged work 目录和专属 Codex home，只挂载这两个目录：

```text
scratch/calibration_runs/<run_kind>/<run_id>/work/       -> /work
scratch/calibration_runs/<run_kind>/<run_id>/codex_home/ -> /codex_home
```

不能挂载仓库、完整 task group、父目录、用户 home、`env/`、notes、evaluators、
该运行不允许看到的标准答案、其他 attempts 或 review 材料。

环境 API 固定在主控宿主机上以 `TASK_ENV_BIND=0.0.0.0` 运行。每个 agent
容器都使用 `--add-host=host.docker.internal:host-gateway`，并通过
`http://host.docker.internal:<TASK_ENV_PORT>` 访问。该 URL 写入
`environment_access.md`；不能 staging 或挂载环境源码。

## Codex 命令

使用配置好的校准模型和 reasoning effort。宿主机统一使用以下启动形式：

```bash
docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  --env PROMPT \
  --mount type=bind,src="$WORK_DIR",dst=/work \
  --mount type=bind,src="$CODEX_HOME_DIR",dst=/codex_home \
  "$AGENT_IMAGE" \
  sh -lc 'CODEX_HOME=/codex_home codex exec -C /work -m <calibration_model> -c '\''model_reasoning_effort="<reasoning_effort>"'\'' --dangerously-bypass-approvals-and-sandbox --json "$PROMPT"'
```

`CODEX_HOME` 只是该进程运行时的临时变量。正式校准不能使用
`codex exec --ephemeral`；应把专属 `codex_home/` 下完整的
`rollout-*.jsonl` 保留为主 trace。校准记录还要保存模型、reasoning effort、
镜像、网络配置、run id、staged 文件、trace 路径和退出状态。

## Prompt 契约

每次 `codex exec` 只能使用下面对应的一份模板。只替换尖括号占位符，不能追加
task hints、答案摘要、rubric/evaluator 细节、notes、构造真值或 `/work` 外路径。

### Base Test Attempt

只 staging 当前 test 的 `input/` 和 `environment_access.md`。

```text
calibration_run_id: <unique_run_id>
run_type: base_test

Solve exactly one test task using only files staged in the current /work directory. Read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
```

### Blind Train Attempt

Staging 5 个 train 的 `input/` 和 `environment_access.md`，不能 staging train
answers 或 judge instructions。

```text
calibration_run_id: <unique_run_id>
run_type: blind_train

Attempt all five train tasks using only files staged in the current /work directory. For each train task, read its input/prompt.txt and every file under input/payloads/, use environment_access.md only for network access, and write the candidate answer under blind_attempts/<task_id>/answer.json. If any unexpected material is present in /work, stop and write contamination_report.txt instead of continuing.
```

### Skill Distillation

Staging 5 个 train inputs、保留的 blind attempts、放在
`train_answers/<task_id>/answer.json` 的 5 个 train 标准答案，以及
`environment_access.md`。不能 staging test 材料、notes、evaluators 或 judge
instructions。

```text
calibration_run_id: <unique_run_id>
run_type: skill_distillation

Build one reusable skill package using only files staged in the current /work directory. Compare each blind attempt with the corresponding train answer, identify concrete mistakes and transferable operating rules, and write the analysis to reflection.md. Create the skill directory and write its entry file to skill/SKILL.md. The skill may contain source precedence, business rules, environment-use strategy, calculations, field conventions, common pitfalls, validation checks, and supporting files inside skill/, but it must not copy train answers or include task-specific final values. If any unexpected material is present in /work, stop and write contamination_report.txt instead of producing a skill.
```

### Fewshot Test Attempt

只 staging 当前 test 的 `input/`、完整的 `skill/` 目录包和
`environment_access.md`。

```text
calibration_run_id: <unique_run_id>
run_type: fewshot_test

Solve exactly one test task using only files staged in the current /work directory. Read skill/SKILL.md and any files it references inside skill/, then read input/prompt.txt and every file under input/payloads/. Use environment_access.md only to reach the running task environment over the network. Do not call the judge API. If any unexpected material is present in /work, stop and write contamination_report.txt instead of an answer. Otherwise write the final answer to answer.json and follow input/payloads/answer_template.json exactly.
```

## 运行有效性

一次运行只有在以下条件全部满足时才有效：

- `/work` 为新建目录，且只包含该模式允许的材料；
- 使用与正式运行相同的容器网络完成环境 health check；
- 进程生成了预期的 `answer.json`、blind attempts 或 `skill/` 目录；
- 完整 Codex session trace 已保存，或明确记录了无法保存的原因；
- trace 中没有访问禁止材料；
- 评分由主 agent 在 Codex 进程之外执行。

受污染或不完整的运行不能计入 `avg@3`。保留原运行供审计，使用新的 run id
和干净目录重新执行。
