# 校准与 Review

## 校准目标

5 个 test tasks 的 overall base `avg@3` 目标约为 `0.40-0.60`。单个 task
通常也应接近这一范围；允许存在有充分理由的离群值，但不能靠“很简单的题”和
“几乎不可能完成的题”互相平均来通过校准。

使用 train set 提炼出的 skill 后，overall fewshot `avg@3` 相对 base 的
目标提升约为 `0.10-0.20`。还应逐题检查 intended transfer points 是否提升，
同时避免大部分任务达到 `0.95` 以上或接近满分。

train-derived skill 不应该让每个 test 都拿到特别高的分数。如果大部分或全部 test 在使用 skill 后达到 `0.95` 以上或接近满分，说明 SOP 可能过于简单、过于机械，或 test 解法太容易从 train tasks 中直接归纳出来。

这里的目标不是让所有 test 都变简单，而是验证 5 个包含标准答案的 train examples 能否为隔离的 fewshot generator 提供足够证据，使其归纳出可迁移的 SOP、facts、字段口径、环境使用方式或业务判断经验。

## Base Test Attempts

base 用于估计未学习 train 的表现。

运行难度测试前，主 agent 构建 task group 的环境镜像，并在主控创建的 Docker
bridge network 中启动环境。环境以 `TASK_ENV_BIND=0.0.0.0` 监听，容器内
`TASK_ENV_PORT` 取 `9000 + task group 数字编号`；例如 `task_group_001` 使用
`9001`，`task_group_024` 使用 `9024`。环境的 network 别名是 `task-env`，
不映射宿主机端口；`environment_access.md` 写入
`http://task-env:<TASK_ENV_PORT>/`，并从 `env/endpoints.txt` 加入当前运行允许
的全部业务 endpoint，每行只写 `METHOD /path`。先从相同 network 上的临时
容器检查 health endpoint，并把 owner-scoped network/容器名、镜像、state mode、
容器内端口、URL 和结果记录到 `scratch/difficulty_calibration.md`。不能把
`env/` staging 或挂载进校准 agent。只有 `env.state_mode: read_only` 时，同一
校准阶段的并发 attempts 才能共享环境；`mutable` 环境为每个 attempt 启动新的
environment 和 network。

每个 test task 必须运行 3 次 base attempts，5 个 test tasks 共 15 个相互
独立的 Dockerized `codex exec` 进程。不能用主控系统的 solver subagent 替代。
每个进程只收到一个新 staging 的目标 test task，并使用
`calibration_runtime.md` 中固定的 base prompt。每个 test task 的 base
`avg@3` 由三次评分取平均得到。

Codex 进程只能看到：

- 目标 test 的 `input/`
- 必要的环境入口，例如 URL、API endpoint，或带鉴权信息的 SQLite 查询服务 URL

Codex 进程不能看到：

- train tasks
- notes
- 标准答案
- eval
- task group design
- review 记录
- `env/` 目录、源码、生成数据文件、数据库 dump、seed、manifest 或 setup 脚本

## Train-Derived Skill

按照正式评测的 `fewshot` 条件，使用 3 个相互隔离的 Dockerized `codex exec`
进程生成 3 个独立校准 skill。每个 generator 只能看到：

- 5 个 train tasks 的 solver 可见输入
- 5 个 train tasks 对应的标准 `output/answer.json`
- 必要的环境入口，例如 URL、API endpoint，或带鉴权信息的 SQLite 查询服务 URL

每个进程使用 `calibration_runtime.md` 中固定的 fewshot skill-generation prompt，
独立地从完整 train examples 中提炼可迁移工作经验。三个进程不能共享工作目录、
Codex home、已有 skill 或 trace。

每个 generator 不能看到：

- test tasks
- notes
- eval
- task group design
- review 记录
- `env/` 目录、源码、生成数据文件、数据库 dump、seed、manifest 或 setup 脚本

这些 skill 只用于校准，放在 `scratch/` 下，不进入最终 `task_group/`。每个
attempt 目录就是完整 skill package root，`SKILL.md` 是入口文件：

```text
scratch/train_skill/fewshot_attempt_01/SKILL.md
scratch/train_skill/fewshot_attempt_02/SKILL.md
scratch/train_skill/fewshot_attempt_03/SKILL.md
```

每个 package 应包含从 train 中归纳出的工作方法：来源优先级、可复用业务规则、
环境使用策略、字段和输出口径、计算规则、常见陷阱和最终校验清单。其他支持文件
可以放在同一个 attempt 目录中。整个目录不能复制 train answers，也不能包含
test-specific facts 或 test 标准答案。

## Fewshot Test Attempts

fewshot 用于验证 train-derived skill 的迁移收益。

每个 test task 必须运行 3 次 fewshot attempts，5 个 test tasks 共 15 个相互
独立的 Dockerized `codex exec` 进程。不能使用主控系统的 solver subagent。
attempt 01 使用 `fewshot_attempt_01`，attempt 02 使用 `fewshot_attempt_02`，
attempt 03 使用 `fewshot_attempt_03`；每个进程再接收一个新 staging 的目标 test
task，并使用 `calibration_runtime.md` 中固定的 fewshot prompt。每个 test task
的 fewshot `avg@3` 由三次评分取平均得到。

Codex 进程可以看到：

- train-derived skill
- 目标 test 的 `input/`
- 必要的环境入口，例如 URL、API endpoint，或带鉴权信息的 SQLite 查询服务 URL

不能看到 notes、标准答案、eval、构造草稿或 `env/` 实现文件。

## Calibration Record

校准记录放在：

```text
scratch/difficulty_calibration.md
```

至少记录：

- 15 次 base attempts 的 solver、输入、预测文件、评测命令和得分。
- 每个进程的校准模型、reasoning effort、agent 和环境镜像、owner-scoped
  network/容器名、环境 state mode、固定 prompt 类型、run id、staged 文件和
  主 Codex trace 路径。
- 3 次独立 fewshot skill generation 的 generator metadata、staged train inputs 和 answers、skill package 路径及主 trace 路径。
- 15 次 fewshot attempts 的 solver、输入、预测文件、评测命令和得分。
- 每个 test task 的 base `avg@3`、fewshot `avg@3` 和 gain。
- 5 个 test tasks 的 overall base `avg@3` 和 overall fewshot `avg@3`。
- Overall base `avg@3` 是否约为 `0.40-0.60`，以及单题离群值是否有充分理由。
- Overall fewshot gain 是否约为 `0.10-0.20`，并逐题说明哪些 transfer-dependent rubric points 发生变化。
- skill test 分数是否在大部分或全部 test 上过度饱和，如果是，记录哪些 scoring points 变得过于容易。
- 低分来源是否来自迁移失败或任务复杂度，而不是 prompt 歧义、schema 摩擦或评测脆弱。

builder 手写、人工改写、合成或反事实 prediction 文件不能计入难度校准。它们只能作为 evaluator sensitivity checks 单独记录。

## 返工闭环

如果校准或 review 不通过，该 task group 必须返工并重新检查，不能直接进入 `data_construction/task_groups/<task_group_id>/`。

当 overall base `avg@3` 不在约 `0.40-0.60` 范围内，或单题明显过易、
几乎不可能完成时，主 agent 可以返工以下任意组合：

- scoring points，如果过多分数来自低难度检查；
- task design，如果 test 不依赖 train 迁移也能完成；
- solver-facing prompt 或 payloads，如果它们泄露了过多流程、来源选择或关键 facts；
- `scratch/env_blueprint.md`，如果环境过窄、过直给、过干净、数据量过小，或暴露了接近答案的接口。

如果需要返工环境，主 agent 应修改 `scratch/env_blueprint.md`，并交回上下文干净的 env-builder coding subagent 实现。环境侧返工可以包括增加数据量、加入真实噪声、扩大 API/Web/数据库入口、移除直接答案接口、加入过期或重叠来源、调整哪些材料放在 payloads 而哪些必须通过 `env/` 查询，或让来源选择更接近真实业务。

当 overall train-derived skill gain 低于约 `0.10` 时，返工应集中在 train/test 迁移距离和 diversity 宽度。检查那些设计为依赖迁移的高权重点是否真的依赖可从真实 train tasks 中归纳出的方法；同时检查 task group 是否覆盖了太多一次性工作流家族，导致每个 test 只有一个很窄的 train anchor。如果迁移距离过宽，应把 task group 收窄到 2-3 个反复出现的操作家族，让可复用口径在多个 train tasks 中重复出现，或重设 test scoring points，使其迁移核心来自重复的 train 证据。如果 test 需要 train 中无法覆盖的 SOP、来源优先级、计算方法或业务判断，应补充真实 train-task 覆盖或重设这些 scoring points。如果 test 中没有任何有意义的高权重点需要 train 迁移，应补充这样的 scoring points。不要求每个高权重点都有 train anchor，也不要通过把 train 写成教学题、把 test prompt 写成步骤清单或泄露 SOP 来修复迁移失败。

当 overall gain 明显高于约 `0.20` 时，应检查 skill 是否过度揭示 test 解法、
train/test 变体是否过于机械相似，或相关 rubric points 是否都在重复奖励同一个
学习到的判断。应返工迁移设计，而不是直接接受被放大的 gain。

当 fewshot `avg@3` 显示 train-derived skill 在大部分或全部 test 上分数过高时，应返工让 SOP 不那么机械，并让 test 不能被 train examples 直接套出来。主 agent 可以在同一真实任务分布内提高 train/test 多样性，要求更多 test-specific evidence discovery，增加更大或更脏的数据，扩大环境入口，把部分简单 payload 信息移入 `env/` 查询，或重设 scoring points，让 skill 有帮助但不能直接回答整个任务。不要通过增加歧义、隐藏必要信息、脆弱 schema 或不公平 evaluator 来压低分数。

当 review 发现结构、泄漏、评测或数据生成问题时，主 agent 将返工分派给对应 subagent，重新集成产物，重新跑 evaluator，必要时重新校准，并再次 review。最终通过前，在最后一次相关返工之后，每个 test task 都必须有 3 次有效 base attempts 和 3 次有效 fewshot attempts。

## Review

reviewer subagent 应检查：

- 是否从同一个 scenario 的 examples 抽象出 task group。
- train 和 test 是否都是来自同一真实任务分布的正式任务，而不是把 train 做成教学题、worked examples 或低配样例。
- train/test 难度是否与来源 examples 的难度来源对齐，而不是明显更简单、更窄或任意变得更难。
- train/test 是否同时具备 diversity 和迁移性。
- diversity 是否限制在可迁移带宽内，是否存在反复出现的操作家族和可复用口径，而不是许多互不相关的一次性 SOP 家族。
- 每个 test task 是否有一部分高权重 scoring points 需要 train 迁移，且这些 transfer-dependent points 是否有明确 train anchors。
- 是否按照要求完成 multi-agent 构造：一个 env-builder coding subagent，以及 10 个 task-builder subagents，每个 task 一个。
- 构造过程是否避免了 `build_task_group_*.py` 式总脚本直接从一个固定 specification 生成 `env/`、所有任务、隐藏答案、notes、evaluators、设计文档和校准 skill。
- 每个任务是否保持长程任务复杂度。
- prompt 和 payload 是否泄露 SOP、关键 facts 或步骤清单。
- `env/` 是否是面向整个 task group 的公共数据与办公环境，而不是单任务临时工具。
- solver-facing env 是否按共享业务领域和接口组织，而不是按 per-task 数据包或 `/api/tasks/<task_id>/data` 这类 endpoint 组织。
- `env/` 是否由上下文干净的 env-builder coding subagent 根据 `scratch/env_blueprint.md` 实现，而不是由主 agent 直接手写。
- `env/endpoints.txt` 是否以 `METHOD /path` 且不附说明的方式列全所有可访问 endpoint，agent 可见的 `environment_access.md` 是否只包含当前运行允许的 endpoint。
- 数据库型任务是否把 SQLite 保留在环境容器内，并只通过带鉴权的运行中查询
  服务开放任务所需的读写能力；不能使用 PostgreSQL，也不能让 solver agents
  直接访问 `.db`、`env/`、schema 或生成数据文件。
- 大量数据是否由程序和随机数生成，并保留 seed 和脚本。
- 每个任务是否有 `notes/notes.md`，且 test task 说明迁移设计和迁移来源。
- 每个 `notes/notes.md` 是否中英双语，便于人工审核。
- 中文是否只出现在 `notes/notes.md`；solver 可见输入、answer template、标准答案、evaluator、task metadata 和 env 文件应保持英文。
- 每个 train/test task 是否都有 `input/payloads/answer_template.json`，且 `output/answer.json` 是否符合该模板。
- 评测是否 rule-based、可复现，并覆盖关键业务判断。
- 每个 task 是否有 6-10 个 scoring points，原始权重是否只使用 `1`、`2` 或 `3`，最终分数是否按 `weight / sum(weight)` 归一化。
- rubric 是否覆盖至少 4 个可以独立失败的业务问题或方面，而不是把一个根本判断拆成许多会同时得分或失分的重复 points。
- `scratch/rubric_validation.md` 是否记录 rubric dependency map，并通过 selective perturbation 证明不同错误只损失对应分值。
- 不可拆分的 point 是否使用 deterministic exact match；天然可拆分的 point 是否使用文档化、确定性的 partial credit，并输出 `[0, 1]` 内的 earned fraction。
- scoring points 是否优先评估数值、枚举、布尔、排序、集合或规范化结构结果；如需字符串匹配，是否已改成受控选择字段以避免 schema 摩擦。
- 大部分 scoring points 是否真实依赖 train 迁移、大量数据探索或长流程工作，而不是不学习 train、不深入探索数据也能拿到。
- `scratch/difficulty_calibration.md` 是否包含 15 次有效 base 和 15 次有效 fewshot Dockerized `codex exec` attempts，且都使用固定 prompt、专属 staged work 和 Codex-home 目录。
- 是否由 3 个相互隔离的 Dockerized 进程基于 5 个 train inputs 和对应标准答案生成了 3 个独立 fewshot skills，并分别保存到 `scratch/train_skill/fewshot_attempt_<nn>/`。
- Overall base `avg@3` 是否约为 `0.40-0.60`，不合理的单题离群值是否已返工或说明。
- Overall fewshot gain 是否约为 `0.10-0.20`，且收益来自预期的 transfer-dependent aspects，而不是重复 rubric points。
- fewshot `avg@3` 是否避免在大部分或全部 test 上过度饱和；如果 skill 后大部分任务达到 `0.95` 以上或接近满分，是否需要返工 SOP、任务多样性、数据探索、env 或 scoring points。
