# GDPevo：评估真实业务生产环境中的 Skill 迁移

GDPevo 是一个公开 benchmark，用于评估真实业务生产环境中的 agent skill 迁移能力。它关注现有任务完成型 benchmark 中仍然不充分的一类能力：agent 能否把相关 train 任务中的经验沉淀成可复用 skill，并迁移到同一业务环境下的 held-out 任务。这里的任务来自具备生产力属性的真实业务运营工作，例如线索交接、费用管控核对、供应商收货审核、库存履约决策、信贷审核、政策决策和运营分析。

## 摘要

现有 agent benchmark 已经在真实环境、工具调用和专业产物评测上取得了明显进展，但很多仍以独立任务粒度报告结果。这会让一个实际能力不够清晰：agent 是否能复用相关任务中学到的 procedure，避免在每条新任务上重新探索 source precedence、exclusion rules、calculation steps 和 schema discipline，并更可靠地完成后续业务任务。GDPevo 用来自真实业务生产场景的 task group 来评估这个缺口。每个 task group 包含一个共享业务环境、五个 train tasks、五个 held-out test tasks、标准答案、精确评测器和数据说明。我们比较三种条件：no_skill、demonstration_skill 和 reflection_skill。第一版公开实验包含 12 个 task groups、60 个 train tasks、60 个 test tasks 和 72 个生成的 skill packages。在 Codex GPT-5.5 xhigh 上，带 skill 的条件相对 no-skill baseline 提升了平均测试表现，并降低了平均 token/cost 用量，说明 benchmark 能够捕捉真实业务工作中的任务族迁移能力。

## 1. 引言

当前 agent benchmark 里有三个实际问题仍然不好回答。第一，agent 能否在相关任务之间复用 procedure。第二，这种复用能否提升同一环境下的 held-out 工作，并且不局限于 train examples。第三，当这些任务对应真实生产性业务工作时，这种提升能否同时通过精确任务得分和下游成本信号来观察，并保留 task notes 和 generated skills 这类可检查产物。

GDPevo 把这些问题落到 task group 这个数据单元上。一个 task group 包含一个共享业务环境，以及相关任务的 train/test 划分。Solver 可能需要操作 Web 工作台、查询 API 或数据库、检查业务记录、处理冲突文件、理解业务规则，并返回 JSON 对象或类似表格的决策结果。因为 train 和 test 共享环境，benchmark 可以测量已有任务经验是否形成了可迁移操作方法。

GDPevo 关注的是这种迁移过程，而不是孤立任务完成。Benchmark 关心经验能否演化成可复用 skill，用于真实业务生产环境中持续出现的工作，包括更正确的业务决策、更少无效搜索步骤，以及相似业务重复出现时更低的边际求解成本。这些工作产物可以是合格客户名单、财务核对结果、采购审核结论、HR 流程判断或运营分析输出。

这个 benchmark 围绕真实业务环境设计。一个 task group 可以暴露 CRM Web 控制台、REST-style APIs、数据库表、ERP 记录、财务报表文件、银行信审工作区、HR 流程或运营分析系统。Solver 需要通过该 task group 允许的环境入口完成长流程工作，evaluator 则根据具体业务结果打分，例如记录集合、金额、排序、分类、日期或结构化动作计数。

GDPevo 有三个核心设计承诺。第一，任务按环境组织，使迁移能力可以被测量。第二，train tasks 是真实任务，其参考资料不会直接暴露完整 SOP 和全部关键事实；有用的 skill 应该来自观察、尝试、对照答案和反思。第三，公开产物应当可检查：task notes 解释问题定义、预期解法、易错点和评测标准，generated skill packages 展示 skill 生成过程实际产出了什么。

## 2. 设计动机与相关 benchmark

GDPevo 所处的问题空间与几类已有 agent evaluation 相关。[GDPVal](https://openai.com/index/gdpval/) 聚焦具有经济价值的真实世界任务，任务来自真实职业中的专家级工作产物，而不是 exam-style prompts；[tau2-bench](https://github.com/sierra-research/tau2-bench) 研究带 policy、tools 和 user simulator 的领域模拟；[SOP-Bench](https://github.com/amazon-science/SOP-Bench) 评估工业 SOP 中的多步骤顺序推理、工具编排和隐含操作知识；[SaaS-Bench](https://github.com/UniPat-AI/SaaS-Bench) 评估自托管 SaaS 应用和浏览器驱动业务 workflow 中的 computer-use agents；[Terminal-Bench](https://github.com/harbor-framework/terminal-bench) 在真实 terminal 环境中评估端到端系统任务；[JobBench](https://github.com/Job-Bench/job-bench-eval) 关注专业人员希望卸载的多源预处理工作，并用 working directory 和 weighted rubrics 组织任务。

GDPevo 的角度是互补的：solver 能不能利用同一业务环境中的重复经验形成可复用 skill。这个问题需要不同的数据单元。单条任务无法暴露迁移；一组互不相关任务的 leaderboard 也无法说明 agent 是否从之前的例子中学习。因此，最自然的单位是 task group：一个环境、多个 train tasks、多个 test tasks，以及一组共同的可迁移 procedure。

独立样本上的 success curve 可以反映通用能力变化，但很难隔离经验积累：第 101 条任务和第 100 条任务之间可能没有设计上的关系。在 GDPevo 中，train tasks 明确提供前序经验来源，held-out test tasks 用来测量这些经验是否改变后续求解行为。因此，benchmark 聚焦的是 self-improving agent behavior 中一个可控切面：受控 skill-generation 条件下的 task-family skill transfer。

这个 benchmark 同时测两类能力：

1. 在真实业务环境中完成长流程任务。
2. 从 train tasks 中学习 skill，并迁移到相关 held-out test tasks。

这两类能力相互制约。如果任务太简单，skill transfer 没有信息量，因为 no-skill baseline 已经能做完。如果 train 和 test 太远，skill 就只是弱提示，而不是可迁移经验。因此，数据构造的目标是一个 transfer band：任务之间共享有意义的操作流程，同时仍然要求新的探索、具体数据检索和精确输出构造。

公开结果也不只看最终正确率。avg@3 衡量 held-out task correctness，token 和 cost metrics 则概括 solver 生成答案时的计算开销。

## 3. 数据构造 Pipeline

GDPevo 通过分阶段 pipeline 生产。Pipeline 从一个紧凑的 scenario seed 开始，最终产出可发布的 task groups、evaluation reports 和 generated skill packages。这个过程采用 multi-agent 协作：不同 clean-context agents 分别负责环境构建、单任务生成、难度校准、内部审核和最终质量审核。这样的分工是为了降低答案、隐藏 SOP 或过度简化的 shortcut 被无声写进 benchmark 的风险。

![GDPevo data construction pipeline](../../assets/figures/gdpevo-data-construction-pipeline.png)

**Figure 1.** GDPevo 数据构造 pipeline 概览。Scenario seed 通过 multi-agent task factory 扩展成 task group，并经过迭代校准、内部审核、clean-context reviewer agents 的质量审核，最终与 evaluation metrics、reports 和 generated skill packages 一起发布。

### 3.1 Scenario Seed

第一阶段准备 scenario seed。一个 seed 包含一个 scenario 和来自真实工作或 benchmark-like 任务背景的 n 个 examples。Scenario 定义业务场景和任务族；examples 提供具体工作模式和难度锚点。例如：活动后 CRM 记录核对、从展会目录筛选有效潜客、清洗联系人导入数据、计算财务控制指标、处理客服队列，或把政策规则应用到 HR / 采购案例中。

在这一阶段，seed 主要作为任务族和难度画像的紧凑锚点。后续阶段会保留这些难度来源，并把 seed 转化成可执行、可审核的 task group。

### 3.2 Multi-agent Task Factory

第二阶段把 seed 扩展成完整 task group。主 agent 先写 task-group blueprint，并负责最终集成。Blueprint 定义共享环境、train/test 覆盖、迁移计划、任务多样性、答案 schema、evaluator 策略和 task-builder 分工。

随后由专门 agent 构造具体产物：

- environment-builder agent 把 `env/` 实现成共享业务世界，而不是按任务拆开的数据包。
- task-builder agents 按任务粒度工作。每个 builder 负责一个 train 或 test task，包括 solver-visible input、reference answer、evaluator 和 task notes。
- calibration solvers 检查 direct solving 是否仍然足够困难，以及 train-derived skills 是否可以迁移但不会让 test tasks 变成 trivial。
- internal reviewer agent 检查正在形成的 task group 是否存在答案泄露、schema friction、弱 scoring goals、环境 shortcut 或 train/test mismatch。

Task factory 是迭代式的。如果 calibration solvers 或 internal reviewer 发现任务过简单、过分离、存在泄露或评分不可靠，task builders 会返工，并重新运行相关检查。只有通过内部检查的一轮才会形成 task-group 输出：一个共享环境、五个 train tasks、五个 test tasks、精确 evaluators 和解释性 task notes。

这种分工本身就是数据标准的一部分。因为 benchmark 测的是 skill transfer，所以生产过程需要避免把完整解题流程无意中写进 prompt 或环境接口。共享环境应该像一个公开办公系统：它可以暴露 Web 页面、API、数据库连接或文件，但不应该暴露 per-task answer endpoint 或 task-specific shortcuts。

### 3.3 Quality Review

第三阶段是独立质量审核。首先进行确定性结构检查，验证文件结构、answer templates、evaluators 和 task group 一致性。随后六个上下文干净的 reviewer agents 根据审核标准独立检查 task group。只有结构检查通过，并且六个 reviewer 中至少五票通过，task group 才能通过质量审核。

Reviewer 关注的是 benchmark 数据质量，而不只是文件是否存在。他们检查 task group 是否与 scenario seed 一致、train/test 迁移是否有意义、diversity 是否保持在可迁移范围内、环境边界是否合理、solver-visible 文件是否泄露答案、notes 是否具备解释性，以及 evaluator 是否评测精确业务结果。如果通过票少于五票，task group 会回到 task factory 返工，并重新审核。

### 3.4 Evaluation Release

第四阶段发布评估产物。对于每个通过审核的 task group，evaluation workspace 在三种 skill conditions 下运行同一批 held-out test tasks：no_skill、demonstration_skill 和 reflection_skill。核心结果是 avg@3，同时发布 token metrics 和看板层面的 cost estimates。结构化 reports 与 generated skill packages 一起发布，使读者既能查看最终分数，也能检查影响分数的 skill 产物。

## 4. Task Group 表示

Task group 是 GDPevo 的核心数据对象。它包含一个共享环境、五个 train tasks、五个 test tasks，以及复现评测所需的材料。

![Task group, skill transfer, and rule-based evaluation](../../assets/figures/task-group-skill-transfer-rule-based-eval-v3.png)

**Figure 2.** Task group 结构与评测协议。五个 train tasks 和五个 test tasks 共享同一业务环境；skills 在 demonstration 和 reflection 条件下生成，最终答案由确定性 rule-based evaluators 打分。

共享环境使 task group 区别于独立 prompt 集合。Solver 需要在一个持续存在的业务世界中工作：同一批账号、活动、政策、发票、工单、员工、供应商或记录可能跨任务出现。这就创造了可复用 procedure 的可能性。

每条正式任务包含以下结构：

| Component | Role |
| --- | --- |
| `input/` | solver 可见 prompt、payloads 和 answer template。 |
| `output/answer.json` | evaluator 使用的标准答案。 |
| `eval/` | 单任务精确评测器。 |
| `notes/notes.md` | 对任务定义、解法、失败模式和评分标准的人类可读说明。 |

Train tasks 和 test tasks 来自同一个真实任务分布。Train tasks 是同一任务族中的示例任务，但参考资料不会直接暴露完整 SOP 和全部关键事实；solver 或 skill-generation agent 必须从相关工作中推断有用 procedure，再迁移到 test tasks。Test tasks 会改变记录、实体、限制条件，有时也改变输出形态，因此 skill 可以指导 solver，但不能替代具体任务探索。

## 5. Skill Conditions

GDPevo 评估三种条件：

| Condition | Test solver 可见信息 | 目的 |
| --- | --- | --- |
| no_skill | Test task input 和允许的环境入口。 | 测量冷启动表现。 |
| demonstration_skill | Test task input、环境入口，以及由 train inputs/outputs 生成的 skill。 | 测试 input/output demonstrations 是否揭示可复用 procedure。 |
| reflection_skill | Test task input、环境入口，以及先盲做 train、对照答案、反思错误后生成的 skill。 | 测试实际尝试和纠错是否产生更好的操作方法。 |

## 6. Evaluation Protocol 与 Workspace

对于每种 skill condition，评估运行五个 held-out test tasks，每个 test task 独立运行三次 solver attempts。设 task group 为 \(g\)，condition 为 \(c\)，test set 为 \(T_g\)，held-out test task 为 \(t \in T_g\)，attempt index 为 \(a \in \{1,2,3\}\)，attempt score 为 \(s_{g,c,t,a}\)，avg@3 定义为：

$$
\mathrm{avg@3}(g,c)
=
\frac{1}{|T_g|}
\sum_{t \in T_g}
\left(
  \frac{1}{3}
  \sum_{a=1}^{3} s_{g,c,t,a}
\right),
\quad |T_g| = 5.
$$

每次 solver attempt 都是上下文干净的。Solver 只接收当前 test task input、允许的环境访问说明，以及当前 condition 所需的 skill 文件。主评估 agent 负责启动或准备环境、为每个 solver staging 最小工作目录、启动 clean-context subagents、在答案写出后调用 evaluator，并聚合结果。

Evaluation workspace 还记录同一批 solver answer-writing attempts 的 solver-side token metrics。Reports 记录 cached input tokens、input tokens 和 output tokens；公开表格中的 token 数以千为单位，即 k。Skill 生成、环境启动、evaluator 运行和主 agent 汇总不计入这些 token metrics。

Scoring 是精确且 task-specific 的。Evaluators 围绕业务结果设计：合格记录集合、排除原因、金额、日期、排序、分类、动作计数或必需 JSON 字段。这样比自由文本 judge 更可解释。当 agent 失败时，丢分通常可以对应到具体的检索遗漏、推理错误、标准化错误、计算错误或 schema 错误。

## 7. Rule-Based Judging 与 Rubric Design

GDPevo 使用 rule-based evaluators，而不是 LLM-as-judge scoring。我们的任务通常要求精确业务结果：正确的合格账号集合、正确的排除原因、正确的发票状态、指定精度下的金额、排序列表、截止日期或必需 JSON 字段。在这种场景下，概率式 judge 会带来两类不稳定性：一是它可能对“语义相近但字段不同”的答案给出不一致判断；二是它可能因为偶然格式差异扣分或放过错误，而这种行为难以复现。

因此，我们在 scoring 之前先约束输出。每条任务都会提供 solver-visible 的 `answer_template.json`，定义预期 JSON 结构、字段类型、数值精度、列表结构、稳定 ID 和 allowed choices。如果一个被评分结果原本像开放字符串，我们会尽量把它改成 controlled-choice field。例如 CRM 排除原因不会用自由文本相似度来评，而是表示成 `sponsor_attendee`、`existing_disqualified`、`inactive_sponsor_record` 或 `non_business_badge` 这样的 enum。这样可以减少意料外的格式丢分，同时保留真正要测的业务判断。

每条任务由多个 business-result checks 组成。一个 scoring point 不应该是很小的语法字段，而应该对应一个有意义的业务结果，例如完整 sponsor-status set、收入汇总、合格线索集合、排除列表、follow-up schedule 或 action-count summary。设 \(\phi_i(\hat{y}, y)\) 是第 \(i\) 个 scoring point 的确定性 pass/fail check，用来比较提交答案 \(\hat{y}\) 和标准答案 \(y\)。每个 scoring point 的 raw weight 只能是 1、2 或 3，task score 定义为：

$$
\mathrm{score}(\hat{y}, y)
=
\frac{
  \sum_{i=1}^{m} w_i \mathbf{1}\!\left[\phi_i(\hat{y}, y)\right]
}{
  \sum_{i=1}^{m} w_i
},
\quad w_i \in \{1,2,3\}.
$$

这种设计让 rubric 足够简单、可审核，同时仍然可以给关键业务结果更高权重。高权重点应留给需要真实数据探索、数据源核对、长流程推理或 train-task 经验迁移的检查。JSON parseability 或字段存在性可以是前置要求，但不应成为主要得分来源。

Rule-based judging 也让错误分析更清楚。因为每个 scoring point 都由确定性代码实现，失败 attempt 可以对应到具体 mismatch：缺失记录、错误 enum、错误金额、排序错误或 normalization rule 违反。这比单个整体文本 judge 更容易复现，也更容易 debug。

## 8. Case Study：SCN_001 CRM Marketing Lead Capture

SCN_001_crm_marketing_lead_capture 展示了 task group 的设计方式。这个场景覆盖 CRM marketing operations 的前段：活动、赞助、展会、联系人采集、导入清洗、campaign membership 和销售跟进。来源 examples 组合了三类业务模式：

1. Event sponsorship and CRM handoff：区分赞助商和普通参会者，对齐赞助状态、发票、付款和后续动作。
2. Trade-show prospecting：从展商目录中识别合格制造商或 OEM，同时排除经销商、服务商和相邻但不合格公司。
3. Contact import hygiene：标准化邮箱和电话，移除不可联系记录，处理 suppression list，并在 CRM 导入前去重。

构造出的 task group 使用共享 HarborCRM 环境。HarborCRM 通过公开 API 暴露活动元数据、赞助方案、财务发票、胸卡扫描、CRM 账号、联系人、商机、活动成员、展会、展商、会面兴趣、导入批次、原始联系人、suppression lists 和 policy summaries。环境中还包含 distractor records 和 near-miss entities，因此 solver 必须先根据正确 event、show 或 import batch 定位数据，不能直接面对一包已经按题整理好的答案数据。

五个 train tasks 和五个 test tasks 围绕三类可迁移操作展开。活动交接任务需要关联 event、sponsor、finance、CRM 和 badge 数据；展会任务需要受控 prospect qualification 和 exclusion reasoning；联系人导入任务需要 normalization、suppression 和 deduplication。Test tasks 在不同记录和输出要求下复用这些 procedure。好的 skill 应该帮助 solver 处理 source precedence、qualification rules、date calculations、deduplication policy 和 JSON schema discipline，但不应包含 test answers。

这个 case 展示了共享环境为什么重要。如果每条任务都是孤立文件包，solver 很容易把任务当成一次性抽取问题。而在 HarborCRM 中，solver 必须学习业务世界如何组织：活动订单在哪里、财务发票如何改变赞助状态、CRM 账号状态如何影响线索资格、展商描述如何映射到平台类型、suppression policy 如何约束联系人导入。正因为 train 和 test 共享这一操作环境，skill transfer 才可以被测量。

在第一版公开实验中，task_group_001 从 no_skill 的 44.43% 提升到 demonstration_skill 的 48.12% 和 reflection_skill 的 57.46%。这个提升不只是格式收益；最明显的收益来自 procedure knowledge，例如赞助状态判断、排除逻辑和 CRM 动作计数。

## 9. 公开结果

第一版公开实验使用 Codex GPT-5.5 xhigh，覆盖 12 个 task groups。两种 skill conditions 都相对 cold-start baseline 有提升。我们同时报告 solver-side token metrics 和估算 text-token cost。这些数字不包含 skill 生成、环境启动、evaluator 执行或主 agent 汇总。

| Condition | Overall avg@3 (%) | Cached tokens avg@3 (k) | Input tokens avg@3 (k) | Output tokens avg@3 (k) | Cost USD avg@3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| no_skill | 48.35% | 642.2k | 709.2k | 14.1k | 1.08 |
| demonstration_skill | 65.99% | 413.7k | 466.1k | 11.5k | 0.81 |
| reflection_skill | 67.13% | 409.1k | 458.7k | 11.3k | 0.79 |

demonstration_skill 相比 no_skill 平均提升 +17.64 个百分点；reflection_skill 平均提升 +18.78 个百分点。当前观察到的最大提升出现在 task_group_009，其中 demonstration_skill 从 42.76% 提升到 92.47%。Skill-conditioned solving 的平均成本也更低。相比 no_skill，demonstration_skill 将 total input tokens 降低 34.3%，output tokens 降低 19.0%，cost 降低 24.8%。reflection_skill 将 total input tokens 降低 35.3%，output tokens 降低 20.1%，cost 降低 26.7%。在 12 个 task groups 中，demonstration_skill 有 11 个降低了 cost，reflection_skill 有 12 个降低了 cost。

这些结果说明 train-derived skills 在这次运行中明显提升 held-out business task performance，同时常常减少重复环境探索。Token 和 cost 结果进一步扩展了这个结论：skill 并不是简单地用更多 reasoning 换更高分。在这次运行中，skill conditions 通常让 solver 更有方向，从而降低 token 用量，即便 solver 处理的是更有信息量的任务过程。对于具备生产力属性的任务来说，这种组合很关键：有用的 skill 应该同时提高业务结果质量，并减少产出该结果所需的下游计算量。

有些 task groups 更受益于 demonstration，因为 input/output pairs 直接暴露了重复规则；有些更受益于 reflection，因为尝试和诊断错误之后才更容易发现可复用 procedure。

- [Experiment board](https://github.com/Prism-Shadow/GDPevo/blob/main/experiments/EXPERIMENT_BOARD.md)
- [Report YAML](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/codex_gpt5_5_xhigh/reports)
- [Skill packages](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/codex_gpt5_5_xhigh/reports/skills)
