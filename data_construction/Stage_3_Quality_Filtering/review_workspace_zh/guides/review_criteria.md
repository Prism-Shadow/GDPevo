# 审核标准

## 脚本化检查范围

`check_task_group.py` 只检查确定性条件：

- `task_group.yaml` 可解析，并包含 `task_group`、`env`、`train_tasks`、`test_tasks`。
- `train_tasks` 和 `test_tasks` 各有 5 个任务。
- 每个 task 声明的 `input/`、`prompt.txt`、`payloads/answer_template.json`、`notes/notes.md`、`output/answer.json`、`eval/eval.sh` 和 evaluator 文件存在。
- `env.setup` 和 `env.files` 中声明的环境文件存在。
- `env.files` 声明了必需的 train-only judge endpoint 实现 `env/judge_api.py`。
- 所有 JSON/YAML 文件可以解析。
- 每个 task 的 `eval.rubric` 有 6-10 项，每项都有 `goal`，并且 `weight` 是 `{1, 2, 3}` 中的整数。
- 每个 task 的 evaluator 能对标准答案打满分；脚本只要求 evaluator stdout 是 JSON，并能从常见字段中判断满分，例如 `score`、`normalized_score`、`earned_score/max_score`、`earned_weight/total_weight`、`passed`、`points` 或 `checks`。
- `notes/notes.md` 至少包含中文说明；中文应只出现在 `notes/notes.md` 中。

脚本不判断业务真实性、任务难度、迁移设计、rubric 各点在语义上是否独立、权重在业务上是否合理、泄漏风险或评测设计质量；这些必须由 reviewer subagents 审核。

## Reviewer 输入

每个 reviewer 必须同时阅读：

```text
task_group/<task_group_id>/
scratch/
```

`task_group/` 是正式数据本体。`scratch/` 是第二阶段 `task_factory/scratch` 的副本，不是 solver 可见输入，也不进入最终评估任务。Reviewer 可按需要参考其中的设计、校准、尝试和返工记录。

`scratch/` 可以包含标准答案、构造 truth、盲做结果、反思、校准记录和返工过程，这些内容本身不算泄露。泄露检查只针对正式 task group 中 solver 可见的 surface：`input/prompt.txt`、`input/payloads/`、`answer_template.json`、公开 API、公开网页、公开数据库或其他运行时入口。如果 `scratch/` 中的答案、SOP 或构造 truth 被复制进这些 solver-visible surface，才应判为泄露。

## Reviewer 检查项

每个 reviewer 必须独立检查以下项目：

| 检查项 | 判断重点 |
| --- | --- |
| `scenario_lineage` | task group 是否来自同一个 scenario 的 examples，是否保留了来源 examples 的难度驱动 |
| `train_predict_design` | train/test 是否都是正式任务；train 不是教程题；test 是否需要从 train 迁移经验 |
| `transfer_band` | diversity 是否在可迁移带宽内，是否存在 2-3 个反复出现的 operation families，而不是一堆一次性 SOP |
| `environment_design` | `env/` 是否是共享公共数据与办公环境；是否运行在 agent 容器之外；Dockerized agent 能否通过已验证的网络路径访问，且没有挂载 env 源码或 truth |
| `leakage_control` | 正式 task group 的 solver-visible surface 是否泄露答案、完整 SOP、评分点、构造 truth 或解题步骤；`scratch/` 中的生产草稿和答案不作为泄露依据 |
| `notes_interpretability` | 每个 task 是否有中英双语 `notes/notes.md`，且说明问题定义、解答依据、迁移来源、易错点和评测标准 |
| `rubric_independence` | 每个 task 是否至少评估 3 个可以独立失败的业务问题或方面；points 是否没有重复同一个根本判断；`scratch/rubric_validation.md` 是否通过 selective perturbation 证明各 points 不会一起得分或失分 |
| `evaluation_design` | eval 是否围绕关键业务结果做确定性检查；天然可拆分的结果是否支持有文档说明的 point 内 partial credit；是否避免 schema 摩擦、自由文本匹配和碎片堆分 |
| `difficulty_calibration` | direct/post-skill 是否为使用固定 prompt、保留 trace 的隔离 Dockerized `codex exec` runs；overall direct `avg@2` 是否约为 `0.40-0.60`；overall gain 是否约为 `0.10-0.20`；是否避免大面积饱和 |
| `construction_process` | 是否能看到 env-builder 和 task-builder subagents，以及 Dockerized blind-train、skill-distillation、solver calibration、review/rework 和完整运行证据 |
| `overall` | 是否可以进入最终评估池 |

Reviewer 的 `decision` 应反映整体质量。某个小项有瑕疵但不影响 benchmark 有效性时，可以 `pass` 并在 `concerns` 中记录；如果存在答案泄漏、eval 不可信、train/test 迁移无效、结构缺失或校准无效，应 `fail`。

## 常见不通过原因

- solver-visible prompt、payload、answer template 或公开环境入口直接写出了 SOP、答案事实、评分点或解题步骤。
- `scratch/` 中的答案、构造 truth 或校准记录被复制进 solver-visible surface。
- `env/` 提供了答案计算器、task-specific data package 或 `/api/tasks/<task_id>/data` 这类近似答案接口。
- 校准或评估把 `env/` 挂载进 agent 容器，使用 agent 容器自己的 `localhost` 访问外部 API，或没有通过配置好的路径完成容器侧 health check。
- test 不需要 train 迁移也能拿到多数分。
- 表面上的 6-10 个 rubric rows 主要依赖同一个 answer field 或上游判断，导致它们一起通过或一起失败。
- 缺少 `scratch/rubric_validation.md`，单方面错误会让大部分 points 一起归零，或天然可拆分的 point 在没有理由的情况下仍只给满分或零分。
- Overall direct 不在约 `0.40-0.60`，skill gain 不在约 `0.10-0.20` 且没有可信解释，或大面积接近满分饱和。
- 难度证据来自主控系统 subagent、人工编写 prediction、非固定 prompt，或没有独立 staged work 与完整 Codex trace 的运行。
- eval 对自由文本、证据措辞、格式摩擦或无关字段打分，而不是对关键业务结果打分。
- notes 缺少迁移来源、解答依据或评测标准，导致数据不可解释。
- 缺少多 agent 构造记录，或者明显由一个总脚本生成所有 env、task、answer、notes、eval 和 skill。
