# Task Factory 工作区中文说明

`task_factory_zh/` 是英文 `task_factory/` 文档的中文翻译镜像，用于团队阅读和讨论。实际数据构造工作区、seed scenario、构造中的 task group 和 scratch 材料仍以 `data_construction/task_factory/` 为准。

`task_factory/` 是第二阶段生产 benchmark 的英文工作规范。目标是从第一阶段一个场景下的几个 examples 出发，构造一个包含 5 个 train tasks 和 5 个 test tasks 的 train-predict task group。train tasks 和 test tasks 都应来自同一真实任务分布；train tasks 不是教学题、教程题或简化样例，其 solver 可见输入和标准答案作为 fewshot skill generation 使用的完整示例。

该工作区定义目录结构、生产要求和固定的校准 prompt。运行时仍需填写模型、推理强度、端口和 run id 等参数，但交给 agent 的材料布局和网络拓扑不再由生产 agent 自行选择。

## 翻译目录

| 路径 | 用途 |
| --- | --- |
| `guides/` | 英文 guides 的中文翻译，按主题拆分 |

## 原工作区目录

| 路径 | 用途 |
| --- | --- |
| `task_factory/guides/` | 数据构造说明，按主题拆分 |
| `task_factory/seed_scenario/` | 放置从第一阶段复制来的 1 个 scenario 及其若干 examples |
| `task_factory/task_group/` | 放置构造中的 task group |
| `task_factory/scratch/` | 放置设计草稿、数据生成记录、校准记录、检查结果和中间材料 |

构造完成并通过 review 后，再将结果移动到 `data_construction/task_groups/<task_group_id>/`。

## 构造说明

开始构造前按顺序阅读：

1. `guides/task_structure.md` - 文件结构和 `task_group.yaml`
2. `guides/task_design.md` - train-predict 任务设计
3. `guides/environment_and_data.md` - env 基础设施和程序化造数
4. `guides/notes_and_evaluation.md` - notes、标准答案和评测要求
5. `guides/workflow.md` - 主 agent 与 subagent 协作流程
6. `guides/calibration_runtime.md` - Dockerized Codex 校准运行方式和固定 prompt
7. `guides/calibration_and_review.md` - 迁移校准和 review

## 核心原则

- 一个 task group 来自一个 scenario 及其若干 examples。
- 完整 task group 应包含 5 个 train tasks 和 5 个 test tasks。
- train 和 test 都应来自同一真实任务分布；train 只是校准流程中先暴露的样本，不是教学题。
- task group 需要同时具备 diversity 和可迁移的 SOP、经验、关键 facts。
- diversity 应限制在可迁移带宽内。优先选择 2-3 个反复出现的操作家族，在实体、数据规模、噪声、来源冲突和输出 schema 上变化，而不是放入五个彼此无关且只出现一次的 SOP 家族。
- 每个 test task 都应包含一部分依赖从 train inputs 和标准答案中归纳经验的高权重 scoring points。这些 transfer-dependent points 应有明确 train anchors；其他高权重点可以来自 test 自身的数据探索、数据规模或长流程工作。
- train tasks 不能显式教授 SOP、不能是 test 的低配版本，也不能让 benchmark 退化成机械套模板；skill 应从完整 train examples 中归纳可迁移经验，不能复制 task-specific final values。
- 每个正式任务都应保持长程任务复杂度，且难度应与来源 examples 对齐；不能把生成任务做得明显更简单、更窄或更像 toy task。
- 大量数据应由程序和随机数生成，不手写生产规模数据。
- `env/` 应是面向整个 task group 的公共数据与办公环境，可包含 Web、API 或基于 SQLite 的业务基础设施，但不能按 task 切成独立数据包或接近答案的 task-specific endpoint。数据库型环境必须使用 SQLite，不能使用 PostgreSQL 或其他服务端数据库引擎。
- 环境 API 固定在主控宿主机上运行，使用 `TASK_ENV_BIND=0.0.0.0`，并令 `TASK_ENV_PORT` 取 `9000 + task group 数字编号`（`task_group_001` 使用 `9001`，`task_group_024` 使用 `9024`）。每个 solver 或 skill-generation 容器都通过 `http://host.docker.internal:<TASK_ENV_PORT>/` 访问，并带上 `--add-host=host.docker.internal:host-gateway`；不能把 `env/` 挂载进 agent 容器，也不能把容器自己的 `localhost` 当成环境地址。
- solver 和测试 agent 可以使用 URL、API endpoint，或带鉴权信息的 SQLite 查询服务 URL，但不能直接查看 `env/` 目录、SQLite 数据库文件、源码、生成数据文件、seed、manifest 或 setup 脚本。
- `env/endpoints.txt` 必须以 `METHOD /path` 且不附接口介绍的方式列出所有可访问 endpoint；校准和正式评估只把当前运行允许的 endpoint 名称写入 `environment_access.md`。
- `env/` 实现应由上下文干净的 env-builder coding subagent 根据 `scratch/env_blueprint.md` 完成；主 agent 负责 blueprint 和最终集成。
- task 文件，包括 `input/`、`notes/`、`output/` 和 `eval/`，应由 task-builder subagents 分别为自己负责的 task 生成。主 agent 不应直接用一个总 builder 脚本生成所有 task 文件和答案。
- `scratch/build_task_group_*.py` 这类脚本不能从一个固定 specification 里同时创建共享环境、10 个任务目录、隐藏标准答案、notes、evaluators、task-group 索引、scratch 设计文档和校准 skill。即使生成文件结构看起来正确，这也属于流程违规。
- 脚本只能用于边界清晰的局部工作，例如共享 `env/` 数据生成、单个 task-builder 自己任务内的转换或 evaluator 辅助、以及集成后的校验；不能替代 env-builder 和 task-builder subagents。
- 使用 3 个相互隔离的进程生成 3 个独立 fewshot skill。每个 generator 接收 5 个 train inputs、对应的 train `output/answer.json` 和环境入口，并把完整 skill 目录包写到 `scratch/train_skill/fewshot_attempt_<nn>/`，其中 `SKILL.md` 是入口文件。
- 难度校准不能把主控系统的 subagent 当 solver。fewshot skill generation、base 和 fewshot 的每次运行都必须是独立的 Dockerized `codex exec` 进程，使用专属 staged `/work`、临时 `CODEX_HOME`、固定 prompt，并保留原始 trace。
- Overall base `avg@3` 目标约为 `0.40-0.60`；fewshot 的 overall gain 目标约为 `0.10-0.20`，且不能让大部分 test 分数饱和。
- `notes/notes.md` 是每个任务的可解释性文件，包含问题定义、解答方法、迁移来源、模型易错点、评测标准和数据生成说明；该文件应中英双语，方便人工审核。
- 最终 task group 中只有 `notes/notes.md` 应包含中文；solver 可见输入、answer template、标准答案、evaluator、task metadata 和 env 文件应保持英文。
- 每个 train/test task 都必须包含 `input/payloads/answer_template.json`，明确规定输出 JSON 结构、字段类型、数值精度和可选枚举值。
- 每个任务最好包含 6-10 个 scoring points，并覆盖至少 4 个可以独立失败的业务问题或方面。把同一个根本判断拆成许多会一起得分、一起失分的相关行，不属于多维评测。
- 每个点的原始权重为 `1`、`2` 或 `3`，最大分值按 `weight / sum(weight)` 归一化。若一个业务结果天然包含可独立判断的子项，可以在该 point 内使用确定性的 partial credit；evaluator 必须明确输出 earned fraction，不能让整套 rubric 因单一依赖变成全对或全错。
- scoring points 应优先评估数值、枚举、布尔、排序、集合或规范化结构结果。若需要字符串匹配，应在 `answer_template.json` 中改成选择题式字段，避免 schema 摩擦。
- 大部分 scoring points 必须依赖迁移学习、大量数据探索或长流程工作，不能让 base 靠简单读题和格式填充拿到多数分。
- solver 可见的 `prompt.txt` 和 `input/payloads/` 不应直白泄露 SOP、关键事实、工具流程或 `(1)(2)(3)(4)` 式解题步骤。
