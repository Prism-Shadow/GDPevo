# Test 003 Notes: Specialty Medication Appeal And Assistance Docket

## English

Builder: `builder_test_003`

Task goal: create a formal test task for a specialty medication appeal docket. Solvers must query the shared SQL service, identify the `test_drug_batch` cases, and produce structured appeal and assistance business results without receiving a procedural SOP in the solver-visible prompt.

Data lineage:
- Target bucket: `test_drug_batch`
- Target medication cases: `MED00005`, `MED00006`, `MED00007`, `MED00008`
- Primary tables used: `medication_cases`, `members`, `plans`, `appeals`, `medication_trials`, `drug_policy_requirements`, `assistance_programs`, `household_financials`
- Construction source: shared generated SQLite database in the task group environment.

Solution basis:
- Plan type comes from `medication_cases.member_id -> members.plan_id -> plans.plan_type`; `appeals.plan_type` is only intake metadata and is intentionally stale for `MED00006`.
- Appeal filing deadline is 60 calendar days after `appeals.adverse_notice_date`; all four target appeals were received timely.
- Diagnosis gates used for this docket: Humira `M06.9`; Remicade `K50.90` or `M06.9`; Dupixent `L20.9` or `J45.50`; Eliquis `I48.91` or `I82.409`.
- Step or evidence gates accept only documented failed, not tolerated, contraindicated, or partial-response evidence for the relevant therapy. Humira accepts a preferred biosimilar trial or exception. Remicade requires both a preferred biosimilar trial or exception and explicit TB screening evidence. Dupixent requires topical therapy failure. Eliquis has only the diagnosis gate in this dataset.
- In policy evidence traces, trial IDs that are present for the case but do not satisfy a requirement are recorded as rejected for that requirement when they are part of the same policy-evidence review path.
- `MED00005` has Humira diagnosis and documented failed adalimumab biosimilar evidence, so the appeal is ready. Household income, commercial insurance, denial letter, and consent support manufacturer assistance through `AP005`.
- `MED00006` has Remicade diagnosis but lacks relevant biosimilar step evidence and TB screen evidence. It has an expedited attestation, so the expedited request needs pharmacy evidence review. Manufacturer assistance is blocked by income over limit, government insurance, lack of commercial insurance, and missing denial letter.
- `MED00007` has Dupixent asthma diagnosis but lacks topical failure evidence. Assistance is blocked by government insurance and lack of commercial insurance.
- `MED00008` has Eliquis diagnosis and is ready for expedited internal appeal. Assistance has no permanent plan or income block, but consent is missing, so the manufacturer assistance team follows up.
- Household income uses 2025 FPL of 15650 dollars for household size 1, plus 5500 dollars per additional person. Assistance blocking reason order is income, commercial insurance, government plan, denial letter, consent.
- Pharmacy clinician routing is required for timely, clinically incomplete medication appeals where policy evidence must be interpreted or collected before internal appeal submission.
- External review is not the next active path until the internal appeal is filed or completed; incomplete policy evidence keeps external review not ready.

Transfer anchors:
- From `train_003`: appeal and manufacturer assistance are separate paths; government-plan exclusions can block assistance even when payer appeal remains active; step therapy and documentation gates must be checked per drug.
- From `train_002`: clinical ambiguity and unclear required criteria route to a clinician rather than being treated as a final adverse determination by non-clinical staff.

Scoring design:
- Six exact-match structured business-result points with raw weights 1, 3, 1, 3, 3, and 3.
- The reworked scoring groups high-level docket labels into compact summary checks and gives additional weight to policy evidence traces, assistance income-threshold math, and complete appeal/assistance trace bundles.
- The evaluator compares normalized JSON fields, not SQL text.
- Case rows are matched by stable `med_case_id`; scalar lists are sorted before comparison.

Construction record:
- Created only under the assigned write scope: `test_tasks/003/**`.
- Non-note files are English only.
- Solver-visible prompt discloses only the fixed synthetic Basic Auth credentials; prompt and payloads avoid complete SOPs, numbered rule checklists, scoring logic, and hidden answer paths.

## Chinese

构建者：`builder_test_003`

任务目标：创建一个正式测试任务，用于 specialty medication 申诉和援助 docket。解题者必须通过共享 SQL 服务查询 `test_drug_batch` 案例，并产出结构化的申诉与援助业务结果；面向解题者的 prompt 不提供流程化 SOP。

数据来源：
- 目标批次：`test_drug_batch`
- 目标药品案例：`MED00005`、`MED00006`、`MED00007`、`MED00008`
- 主要数据表：`medication_cases`、`members`、`plans`、`appeals`、`medication_trials`、`drug_policy_requirements`、`assistance_programs`、`household_financials`
- 构建来源：任务组环境中共享生成的 SQLite 数据库。

标准答案依据：
- 计划类型来自 `medication_cases.member_id -> members.plan_id -> plans.plan_type`；`appeals.plan_type` 只是 intake 元数据，并且 `MED00006` 中故意存在过期值。
- 申诉提交截止日为 `appeals.adverse_notice_date` 后 60 个自然日；四个目标案例都按时收到。
- 本 docket 使用的诊断门槛：Humira 为 `M06.9`；Remicade 为 `K50.90` 或 `M06.9`；Dupixent 为 `L20.9` 或 `J45.50`；Eliquis 为 `I48.91` 或 `I82.409`。
- 阶梯治疗或证据门槛只接受相关治疗的 documented failed、not tolerated、contraindicated 或 partial-response 证据。Humira 接受首选生物类似药试用或例外。Remicade 同时需要首选生物类似药试用或例外，以及明确的结核筛查证据。Dupixent 需要外用治疗失败。Eliquis 在本数据集中只有诊断门槛。
- 在政策证据追踪中，病例中存在但不能满足某项要求的 trial ID，如果属于同一个政策证据审核路径，会作为该要求的 rejected trial 记录。
- `MED00005` 有 Humira 诊断和 documented failed adalimumab biosimilar 证据，因此申诉已就绪。家庭收入、商业保险、拒付信和同意书均支持通过 `AP005` 申请厂家援助。
- `MED00006` 有 Remicade 诊断，但缺少相关生物类似药阶梯治疗证据和结核筛查证据。该案例有加急声明，因此加急请求需要药房临床人员进行证据审查。厂家援助因收入超限、政府保险、缺少商业保险和缺少拒付信而受阻。
- `MED00007` 有 Dupixent 哮喘诊断，但缺少外用治疗失败证据。厂家援助因政府保险和缺少商业保险而受阻。
- `MED00008` 有 Eliquis 诊断，适合提交加急内部申诉。厂家援助没有永久性的保险或收入阻断因素，但缺少同意书，因此由厂家援助团队跟进。
- 家庭收入使用 2025 年 FPL：1 人家庭为 15650 美元，每增加 1 人增加 5500 美元。援助阻断原因顺序为收入、商业保险、政府计划、拒付信、同意书。
- 对于及时收到但临床证据不完整的药品申诉，需要药房临床人员先解释或补齐政策证据，再提交内部申诉。
- 在内部申诉提交或完成之前，外部审查不是当前下一步；政策证据不完整会使外部审查暂不可用。

迁移锚点：
- 来自 `train_003`：申诉路径和厂家援助路径必须分开；即使付款方申诉仍可继续，政府计划排除也可能阻断厂家援助；阶梯治疗和文档门槛必须按药品逐项检查。
- 来自 `train_002`：临床不明确或必要标准不清楚时，应转给临床人员，而不是由非临床人员直接当作最终不利决定处理。

评分设计：
- 六个精确匹配的结构化业务结果评分点，原始权重为 1、3、1、3、3、3。
- 重做后的评分将高层 docket 标签合并为少量汇总检查，并更重视政策证据追踪、援助收入阈值计算以及完整的申诉/援助追踪组合。
- 评估器比较归一化后的 JSON 字段，而不是 SQL 文本。
- 案例行按稳定的 `med_case_id` 匹配；标量列表在比较前排序。

构建记录：
- 只在指定写入范围 `test_tasks/003/**` 下创建。
- 非 notes 文件全部为英文。
- 面向解题者的 prompt 只公开固定合成 Basic Auth 凭据；prompt 和 payloads 不包含完整 SOP、编号规则清单、评分逻辑或隐藏答案路径。
