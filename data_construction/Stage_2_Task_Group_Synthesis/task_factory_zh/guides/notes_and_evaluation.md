# Notes 与 Evaluation

## Notes

每个任务必须包含：

```text
notes/notes.md
```

该文件不作为 solver 输入，用于保证数据生产的可解释性。

`notes/notes.md` 应中英双语。中文部分仅用于人工审核和理解。

最终 task group 中只有 `notes/notes.md` 应包含中文。solver 可见文件和可执行产物应保持英文，包括 `prompt.txt`、`input/payloads/`、`answer_template.json`、`output/answer.json`、`eval/`、`task_group.yaml`、`env/`、生成数据和校准运行记录。

整体风格应和第一阶段 example notes 一致：不要求固定标题模板，但必须把后续构造、审核和评测需要的信息讲清楚。至少覆盖：

- 数据和来源链路：来源 scenario、来源 example IDs、task design brief、生成或公开的环境数据、task-local payloads。
- 任务定义：业务背景、solver 可见输入、预期输出、关键约束、重要对象和预期工作流程。
- 场景归属：解释该 task 为什么属于当前 scenario 和 task group，包括它体现的业务流程、对象关系、数据流转或系统协同。
- 材料说明：说明每个重要 payload、公开环境入口、生成数据集、policy、table、API 或支持文件的用途。
- 解答和评测依据：关键证据、规则、计算、输出 schema、答案构造、预期 6-10 个 scoring goals、打分权重、语义不同且不重复的业务结果、整点通过或失败的检查，以及模型易错点。
- 迁移设计：
  - 对 train task，说明通过完成这个真实任务并对照答案，可以归纳出什么可迁移 SOP、facts、字段口径、工具使用习惯或业务判断。
  - 对 test task，说明需要从哪些 train task 迁移知识、具体需要归纳和迁移什么知识，以及哪些高价值 scoring goals 依赖迁移而不只是依赖当前 task 的本地探索。
  - 对 test task，说明这种迁移应该如何帮助解题，同时不能把隐藏 SOP 或答案路径直接写进 solver-visible prompt。
- 构造记录：作者、创建日期、更新日期和主要变更。

## Notes 构造 Prompt

task-builder subagent 编写 `notes/notes.md` 时可使用这个 prompt：

```text
Write the hidden `notes/notes.md` file for <task_id>.

The notes are not solver input. They are for data construction, human review, debugging, and evaluation auditability. The final notes file must be bilingual in English and Chinese. Solver-visible files, answer files, evaluation files, task metadata, env files, generated data, and calibration artifacts must remain English-only.

Do not force a rigid section template. Use clear headings that fit the task, but cover all of the following content:

1. Data/source lineage: source scenario, source example IDs, task design brief, generated or public environment data, and task-local payloads used by this task.
2. Task definition: business background, visible inputs, expected output, key constraints, important objects, and expected work process.
3. Scenario fit: why this task belongs to the current scenario and task group, including the workflow, object relationships, data flow, or system coordination it represents.
4. Material map: what each important payload, public environment entry point, generated dataset, policy, table, API, or support file is used for.
5. Solution and evaluation basis: key evidence, rules, calculations, output schema, answer construction, 6-10 scoring goals, raw scoring weights, distinct non-duplicate business outcomes, whole-point pass/fail checks, and likely model pitfalls.
6. Transfer design:
   - If this is a train task, explain what transferable SOP, facts, field conventions, tool-use habits, or business judgment can be inferred from solving this real task and comparing the attempt against the answer. Do not describe the train task as a tutorial or worked example.
   - If this is a test task, name the train task(s) that anchor the transferable knowledge, describe what knowledge must be inferred and transferred, and identify which important scoring goals rely on transfer.
   - For test tasks, also separate transfer-dependent difficulty from task-specific exploration difficulty.
7. Construction record: author, created date, updated date, and major changes.

Keep the notes concrete. Refer to actual files, task IDs, field names, APIs, tables, business rules, scoring goals, and output fields whenever possible. Do not leak notes content into solver-visible input files.
```

## Standard Answer

`output/answer.json` 保存标准答案。不同任务可以使用不同 JSON schema，但同一个 task group 内应尽量保持字段风格一致。

每个 task 还必须提供 solver 可见的 `input/payloads/answer_template.json`。该模板定义必需输出结构、字段类型、数值精度、单位、稳定标识符、排序规则和可选项。`answer.json` 应符合该模板。

标准答案应能由 `notes/notes.md` 中记录的依据、规则和数据生成过程解释清楚。

## Evaluation

`eval/eval.sh` 是评测入口。每个 task 最好包含 6-10 个 scoring points。Scoring point 是带权重的业务结果维度，而不是一个零碎字段或一句解释。

Rubric 必须覆盖至少 4 个语义上不同的业务结果。不能设置多个 points，换一种说法重复检查同一个判断、答案事实或根本决策。不同 points 可以使用同一份来源证据，但必须评价真正不同的结论。

每个 scoring point 的原始 `weight` 只能设为 `1`、`2` 或 `3`。该 point 的分值按以下方式计算：

```text
assigned_score = scoring_point.weight / sum(all scoring_point.weight)
```

如果一个 task 的原始权重为 `[2, 3, 1, 2, 1, 3, 2, 1]`，总权重为 `15`，则原始权重为 `3` 的 scoring point 最终贡献 `3 / 15 = 0.20`。

每个 scoring point 的打分都必须是确定性的，并且整体通过或整体失败。完整业务目标通过时获得该点全部分值，否则得零分；point 内不允许部分得分。资格、截止日期、必须采取的动作、纳入或排除等真正不同的业务结果，应拆成有业务意义的独立 points。不要为了制造分数粒度而拆出零碎字段，也不要用不同名称重复奖励同一个结果。

每个 point 的 evaluator 输出应包含该点分值、布尔型通过结果、实际得分（只能等于该点全部分值或 `0`），以及确定性的检查详情。总分按以下方式计算：

```text
score = sum(assigned_score * point_pass)
point_pass in {0, 1}
```

这样既保留 `1`/`2`/`3` 原始权重，也允许任务总分处于 `0` 与 `1` 之间：不同 points 可以分别通过或失败，但任何单个 point 都不能只获得一部分分值。

scoring points 应尽量围绕数值、枚举、布尔、排序、集合、聚合或其他规范化结构结果。避免直接对自由文本字符串打分。如果某个结果天然像字符串分类、状态、原因代码、动作名或标签，应在 `answer_template.json` 中做成受控选择字段，并对选择值做 exact match。

大部分 scoring points 必须是真实有难度的业务结果点。它们应至少满足以下一种条件：

- 需要迁移从真实 train tasks 中归纳出的 SOP、facts、字段口径、工具选择或业务判断经验。
- 需要在大量数据、多个系统入口、复杂 API、Web 页面、数据库或文件之间探索和交叉验证。
- 需要完成长流程工作，例如过滤、追踪状态、重建有效业务状态、处理冲突来源、聚合计算、排序取舍和最终业务决策。

不要把多数分数给到低难度项目，例如 JSON 可解析、字段存在、照抄 prompt 中的实体名、使用单个小 payload 直接查值、输出格式正确、证据字符串相似或无需 train 经验的常识判断。这些可以作为前置校验或少量低权重 scoring points，但不能成为主要得分来源。

推荐的 rubric 形态：

```yaml
rubric:
  - goal: Correct target entity set under the documented inclusion and exclusion rules.
    weight: 2
  - goal: Correct eligibility or policy classification for each selected entity.
    weight: 3
  - goal: Correct numeric exposure, amount, or aggregate calculation.
    weight: 2
  - goal: Correct priority ordering and required operational actions.
    weight: 2
```

继续补足到 6-10 个 scoring points，并至少覆盖 4 个真正不同的业务结果。`rubric` 只作为评测目标的简洁索引；答案路径、整点通过或失败的逻辑、分值计算、容差和实现细节放在评测文件中。

校准前必须创建 `scratch/rubric_validation.md`，并确认每个 task 满足以下规则：rubric 至少覆盖 4 个不同业务结果；不同 points 没有重复评价同一个判断、答案事实或根本决策；每个 point 始终只能获得该点全部分值或零分。不满足这些规则的 points 必须在校准前合并或重新设计。

评测应尽量使用可复现的规则检查，例如：

- 字段存在性和 JSON 可解析性。
- 枚举、状态、标签和分类。
- 数值、排序、覆盖率和聚合结果。
- 关键业务判断。
- 是否正确使用从 train 迁移来的 SOP、facts 或数据口径。

数值结果应按任务声明的精度做确定性比较，例如金额精确到分、比例精确到指定小数位。列表或集合应先做清晰的规范化，例如按稳定 key 排序、去除非业务空白、统一枚举大小写规则；规范化规则必须写在 evaluator 或 notes 中。

不要依赖主观文本质量判断。不要让评测只检查完整文件相等，除非该任务答案本身就是单一、完全规范化的机器字段。不要把证据措辞、格式摩擦、无关字段或偶然字符串作为独立 scoring point。涉及字符串类得分字段时，应尽量改成 enum 或选择题式字段。共享 parser 或前置校验可以拒绝不可读答案，但一般业务错误应只让相关 rubric points 归零，而不是让整套 rubric 全部归零。
