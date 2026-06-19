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
- 解答和评测依据：关键证据、规则、计算、输出 schema、答案构造、预期 6-10 个 scoring goals、打分权重、exact-match 检查和模型易错点。
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
5. Solution and evaluation basis: key evidence, rules, calculations, output schema, answer construction, 6-10 scoring goals, raw scoring weights, exact-match checks, and likely model pitfalls.
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

`eval/eval.sh` 是评测入口。每个 task 最好包含 6-10 个 scoring points。scoring point 是最小计分单元，应对应一个关键业务结果，而不是一个零碎字段或一句解释。

每个 scoring point 的原始 `weight` 只能设为 `1`、`2` 或 `3`。最终得分权重按以下方式归一化：

```text
normalized_weight = scoring_point.weight / sum(all scoring_point.weight)
```

如果一个 task 的原始权重为 `[2, 3, 1, 2, 1, 3, 2, 1]`，总权重为 `15`，则原始权重为 `3` 的 scoring point 最终贡献 `3 / 15 = 0.20`。

每个 scoring point 应采用 exact match：命中则获得该点完整权重，未命中则为 `0`。一个 scoring point 内可以检查多个字段，但这些字段必须共同定义同一个关键业务结果；只要核心业务判断或关键数值错误，该点不得给部分分。

scoring points 应尽量围绕数值、枚举、布尔、排序、集合、聚合或其他规范化结构结果。避免直接对自由文本字符串打分。如果某个结果天然像字符串分类、状态、原因代码、动作名或标签，应在 `answer_template.json` 中做成受控选择字段，并对选择值做 exact match。

大部分 scoring points 必须是真实有难度的业务结果点。它们应至少满足以下一种条件：

- 需要迁移从真实 train tasks 中归纳出的 SOP、facts、字段口径、工具选择或业务判断经验。
- 需要在大量数据、多个系统入口、复杂 API、Web 页面、数据库或文件之间探索和交叉验证。
- 需要完成长流程工作，例如过滤、追踪状态、重建有效业务状态、处理冲突来源、聚合计算、排序取舍和最终业务决策。

不要把多数分数给到低难度项目，例如 JSON 可解析、字段存在、照抄 prompt 中的实体名、使用单个小 payload 直接查值、输出格式正确、证据字符串相似或无需 train 经验的常识判断。这些可以作为前置校验或少量低权重 scoring points，但不能成为主要得分来源。

推荐的 rubric 形态：

```yaml
rubric:
  - goal: Correct target entity set and inclusion/exclusion decisions.
    weight: 2
  - goal: Correct final classifications and required actions.
    weight: 3
```

继续补足到 6-10 个 scoring points。`rubric` 只作为评测目标的简洁索引；答案路径、exact-match 逻辑、归一化、容差和实现细节放在评测文件中。

评测应尽量使用可复现的规则检查，例如：

- 字段存在性和 JSON 可解析性。
- 枚举、状态、标签和分类。
- 数值、排序、覆盖率和聚合结果。
- 关键业务判断。
- 是否正确使用从 train 迁移来的 SOP、facts 或数据口径。

数值结果应按任务声明的精度做确定性比较，例如金额精确到分、比例精确到指定小数位。列表或集合应先做清晰的规范化，例如按稳定 key 排序、去除非业务空白、统一枚举大小写规则；规范化规则必须写在 evaluator 或 notes 中。

不要依赖主观文本质量判断。不要让评测只检查完整文件相等，除非该任务答案本身就是单一、完全规范化的机器字段。不要把证据措辞、格式摩擦、无关字段或偶然字符串作为独立 scoring point。涉及字符串类得分字段时，应尽量改成 enum 或选择题式字段。
