# 任务设计

## Train-Predict 目标

task group 应体现 train-predict 工作模式：隔离的 fewshot generator 读取真实 train tasks 的 solver 可见输入和标准答案，将可迁移经验提炼为 skill，再由 test solver 在未见任务中使用。

设计时应同时满足：

- train 和 test 来自同一个场景、同一真实任务分布，并共享可迁移的业务背景、SOP、数据口径、工具使用方式或关键事实类型。
- train tasks 不能是教学题、教程题、worked examples、test 的低配版本或显式 SOP 演示；它们应是正式业务任务，只是在校准流程中先被暴露。
- train 与 test 不能只是同一模板换壳；任务之间需要有 diversity，包括不同子场景、数据形态、环境入口、输出 schema 或决策目标。
- 每个正式任务的复杂程度和难度应与第一阶段 examples 对齐，保持长程任务特征。
- test 不能只靠本地输入材料直接完成，必须有一部分 SOP、关键 facts、字段口径、工具选择经验或业务判断习惯需要从 fewshot skill generation 可见的 train inputs 和标准答案中归纳。

## Example 难度对齐

设计 task 前，应先阅读来源 examples，并识别它们的难度来源：数据量、系统或工具数量、来源选择歧义、跨记录校验、业务规则深度、长流程长度和必要验证步骤。

每个 train/test task 应落在同一难度区间。可以更换实体、生成数据和业务表面，但不能把 example 简化成小查表、单文件转换或短 prompt 执行；也不能通过无关系统、隐藏规则或过多缺失信息把任务做得远难于 example。

设计稿应包含 example difficulty audit：

| Source example | Difficulty drivers | Task-group design response |
| --- | --- | --- |
| `E001` | Multi-source CRM/event reconciliation, sponsor-vs-attendee distinction, validation workflow | Reused as event-to-CRM train/test tasks with comparable source conflicts and workflow length |

## 迁移距离控制

train/test 的迁移距离应足够近，让真实的 train-derived skill 能产生帮助；同时又不能近到 test 只是 train 的模板换壳。

## Diversity 带宽

diversity 应限制在可迁移带宽内。一个 task group 不应让 5 个 train tasks 覆盖五个彼此无关的工作流家族，然后每个家族只在 test 中考一次。这样得到的 train-derived skill 会变成宽而浅的速记：记录了很多孤立事实，但 fewshot attempts 仍然需要重新摸索每个 test 的主要业务逻辑。

更好的做法是，在同一个 scenario 内选择 2-3 个反复出现的操作家族。可以变化实体、账号、活动、campaign、产品、数据体量、噪声形态、来源冲突、环境入口和输出 schema，但需要保留足够重复的决策框架，让 train-derived experience 可以迁移。

可复用口径通常应在 train set 中出现不止一次；或者作为一个正式 train task 出现一次，并由另一个 train task 通过相同的来源优先级、字段口径、计算方式、路由逻辑或校验习惯进行强化。test task 仍然可以有不带 train anchor 的高权重点，用来衡量真实数据探索；但其依赖迁移的核心不应只依赖一个孤立的 train/test 配对。

合理的 diversity 变化包括：

- 新客户、活动、campaign、batch、地区、产品线或账号集合；
- 更大或更脏的记录、过期导出、重叠来源、缺失值和真实干扰项；
- 围绕同一业务对象的不同环境入口；
- 围绕同一决策框架的不同结构化输出。

不合理的 diversity 变化包括：

- train 中没有练过的新业务目标；
- 只出现在 test 中的新 SOP 家族；
- 无法从 train 中归纳出来的新隐藏政策、评分逻辑或来源优先级；
- train 中没有可比较聚合任务或重复组件工作流时，直接加入综合 board/rollup task。

每个 test task 应有一个有意义的迁移核心：一部分高权重 scoring points 的正确解法必须依赖可从 train inputs 和标准答案中归纳出的 SOP、来源优先级、字段口径、计算方式、输出约定或业务判断。这些 transfer-dependent scoring points 应有明确 train anchors，但这些 anchors 应是真实任务，不是简化的教学样例。其他高权重点可以来自 test 自身的数据探索、数据规模、噪声证据或长流程工作。

每个 test task 的设计稿都必须为那些依赖 train 迁移的 scoring points 提供 transfer coverage matrix：

| Test task | Test scoring point | Train anchor | What transfers | What changes |
| --- | --- | --- | --- | --- |
| `test_001` | `SP003` | `train_001` | Sponsor/attendee separation and lead qualification convention | New event, new source conflicts, larger CRM state |

不要求每个高权重 scoring point 都映射到 train。真正的要求是：test 中要有一部分非平凡的高权重点，只有迁移从真实 train tasks 中归纳出的方法才能稳定做对。没有 train anchor 的高权重点可以存在，但它们应衡量真实的任务特定数据探索或长流程工作，而不是未说明的新 SOP。

避免只做远迁移。如果 fewshot attempts 不能显著高于 base attempts，首先检查 diversity 是否过宽：是否有太多彼此无关的工作流家族、太多一次性 train anchors，或 test-only SOP 没有在 train 中重复出现。返工时优先收窄操作家族范围、补充可复用口径的真实 train 覆盖、拉近 train/test 分布，或明确哪些高权重点依赖迁移、哪些高权重点依赖 test-specific exploration，而不是只通过泄露步骤或把 test prompt 写得更程序化来修复。

## 复杂度来源

test 难度来源包括两类：

- 从 train 中迁移 SOP 和关键 facts。
- 任务自身复杂，例如流程长、软件多、API 多、Web 页面多、SQLite 查询服务复杂、数据量大、数据杂、数据脏、相似来源冲突或局部材料过时。

不要用任意歧义、坏格式、不可恢复的信息缺口来制造难度。难度应来自真实业务复杂性、长程操作、信息发现、来源选择和迁移失败。

## Prompt 和输入材料

`prompt.txt` 和 `input/payloads/` 是 solver 可见内容。

禁止在 prompt 或输入文件中直白写出：

- 可迁移 SOP 的完整步骤。
- 关键 facts 的答案式总结。
- 工具调用顺序。
- 解题流程清单，尤其是 `(1)(2)(3)(4)` 式步骤列表。
- 标准答案、评测规则或 notes 内容。

prompt 应像真实用户请求：说明目标、必要上下文、可用材料或环境入口、输出要求，但不教 solver 如何一步步完成。

如果任务需要共享 API、Web app 或其他运行中的环境，solver 可见的 prompt
和 payload 只能使用 `<TASK_ENV_BASE_URL>` 作为 base URL 占位符。不要在
`prompt.txt` 或 `input/payloads/` 中写死 localhost、私有 IP、公开部署
URL、端口或启动命令；真实 endpoint 由评估 workspace 的 `.env` 配置。

`input/payloads/` 应包含真实感强、来源多样、体量充足且可能有噪声的数据材料。payload 可以放 solver 可见的小型导出、邮件、表格、日志、模板或局部材料，但不应变成解题手册。

每个 train/test task 都必须包含 `input/payloads/answer_template.json`。该模板应定义输出 JSON schema、字段类型、数值精度、单位、稳定标识符、列表排序规则和可选枚举值。它用于降低格式摩擦，但不能泄露答案。

被评分输出应优先设计为数值、枚举、布尔、排序、集合或规范化结构字段。如果某个业务结果原本需要用自由文本字符串匹配，应改成受控选择字段，例如 `answer_template.json` 中的 enum 或选项列表。

## Task Group Design Draft

正式创建 task 文件前，主 agent 应先写：

```text
task_factory/scratch/task_group_design.md
```

设计稿至少包含：

- 来源 scenario 和 examples。
- example difficulty audit，说明 train/test 任务难度如何与来源 examples 对齐。
- train/test 的任务列表，必须包含 5 个 train tasks 和 5 个 test tasks。
- task-builder 分派计划，为 10 个任务分别写清 subagent brief。
- 每个任务的角色、复杂度、长程流程和输出形式。
- 哪些 SOP、facts、字段口径或环境经验应能从 train 真实任务中归纳出来并迁移到 test。
- diversity 带宽说明：哪些 2-3 个操作家族会在 task group 中反复出现，task 之间具体变化什么，哪些变化是刻意留给 task-specific exploration 的。
- transfer coverage matrix，将依赖 train 迁移的 test scoring points 映射到一个或多个 train anchors，并说明具体迁移什么。
- 共享 env blueprint，或指向 `scratch/env_blueprint.md`。
- 交给 env-builder coding subagent 实现的程序化数据生成计划。
- 评测和校准计划，包括每个任务预期的 6-10 个 scoring points、`1`/`2`/`3` 原始权重、至少 4 个语义上不同的业务结果、不得重复评价同一个判断或答案事实，以及确定性的整点通过或失败逻辑。
- `answer_template.json` 的输出形态计划，包括数值精度，以及面向字符串类输出的受控选择字段。
- 标注哪些 scoring points 依赖 train-derived experience、哪些依赖大量数据探索或长流程工作，确保多数分数不能由 base 通过简单读题获得。
- skill saturation 检查：train-derived skill 应该提升 test 表现，但不应该让大部分或全部 test 达到 `0.95` 以上或接近满分。

设计稿应分配 task 归属，并为每个 task-builder subagent 提供足够的 task-specific brief。设计稿不应直接生成每个 task 的 `input/`、`notes/`、`output/` 和 `eval/`。这些文件应由后续 10 个 task-builder subagents 分别生成。
