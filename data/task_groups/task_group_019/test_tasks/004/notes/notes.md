# test_004 Notes

## English

### Data/source lineage

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using source examples `E001`, `E002`, and `E003` as the overall administrative licensing review distribution. The direct source family is the contractor eligibility workflow from `E001`.

The shared environment is the Cascadia Licensing Review Portal (CLRP) under `task_group/task_group_019/env/`. The target batch is `HS-2026-Q2B`, exposed to solvers through the public API and `/exports/contractor_batch_HS-2026-Q2B.csv`. Construction used the generated CLRP rows and the construction manifest only for lineage and anchor validation. Solver-visible local input is `input/prompt.txt` and `input/payloads/answer_template.json`.

### Task definition and scenario fit

The solver prepares a board-ready contractor regulatory impact screen for 13 applications in `HS-2026-Q2B` as of `2026-06-30`. The expected answer is a structured JSON object with per-application current decisions, the prior-rule counterfactual for each application, a `changed_by_bulletin` list, aggregate `counterfactual_counts`, and management-level escalation cases.

This fits the source scenario because the work requires administrative licensing reconciliation across applications, bulletins, bonds, insurance records, unresolved penalties, field notes, correspondence, and prior adverse conduct. The business product is not a narrative memo; it is a decision package that separates ordinary deficiencies from decisions caused by new regulatory bulletins.

### Material map

Important CLRP resources:

- `/api/contractors/applications?batch_id=HS-2026-Q2B` and `/exports/contractor_batch_HS-2026-Q2B.csv`: target application roster, trades, application dates, experience years, financial statement flags, background status, declared bonds, and declared insurance.
- `/api/contractors/bulletins?effective_on=2026-06-30`: effective 2026 contractor bulletins and prior-rule baselines.
- `/api/contractors/bonds?name=...`: active, short, and cancelled bonds.
- `/api/contractors/insurance?name=...`: active, expired, stale, and pending-verification insurance records.
- `/api/contractors/violations?name=...`: unresolved penalties and disqualifying conduct evidence.
- `/api/contractors/field-notes?name=...`: open inspector holds and resolved/distractor notes.
- `/api/contractors/correspondence?batch_id=HS-2026-Q2B`: material notices, cancellation notices, and nonblocking indexed or public-inquiry correspondence.
- `/api/contractors/complaints?name=...`: complaint context; not every open or closed complaint independently changes the decision.

### Solution basis

The answer contains all 13 application decisions in ascending application ID order.

Current decisions and counterfactual impact:

- `CA-2026-0038`: `HOLD` for `BOND_SHORTFALL`; Concrete bond meets the prior $10,000 baseline but fails the 2026 $12,000 requirement under `CB-2026-003`, so the decision changes from prior-rule `APPROVE` to current `HOLD`.
- `CA-2026-0039`: `HOLD` for `INSURANCE_VERIFY`; the insurance row is expired/stale, so the hold is a pre-existing deficiency rather than a bulletin-created decision.
- `CA-2026-0040`: `HOLD` for `INSURANCE_VERIFY`; the Electrical policy is active but carrier verification remains pending. The hold is unchanged under the prior-rule counterfactual.
- `CA-2026-0041`: `HOLD` for `FIELD_NOTE_HOLD`; the open inspector hold remains a pre-existing deficiency.
- `CA-2026-0042`: `HOLD` for `UNRESOLVED_PENALTY`; the unresolved high-severity penalty remains a pre-existing deficiency.
- `CA-2026-0043`: `HOLD` for `UNRESOLVED_PENALTY`; the exact-name unresolved penalty is a pre-existing hold rather than a new-rule-caused hold.
- `CA-2026-0044`: `HOLD` for `BOND_CANCELLED`; the surety cancellation is a pre-existing deficiency, not a bond-minimum bulletin change.
- `CA-2026-0045`: `HOLD` for `EXPERIENCE_VERIFY`; HVAC experience is two years, which met the prior two-year baseline but fails the three-year requirement under `CB-2026-011`, so the decision changes to a new-rule-caused hold.
- `CA-2026-0046`: `HOLD` for `CORRESPONDENCE_HOLD` and `FINANCIAL_STATEMENT_MISSING`; the missing financial statement would have held the application under prior rules, while `CB-2026-017` adds the current correspondence reason without changing the overall decision.
- `CA-2026-0047`: `HOLD` for `UNRESOLVED_PENALTY`; the unresolved exact-name penalty remains a pre-existing deficiency.
- `CA-2026-0048`: `HOLD` for `BOND_SHORTFALL`; Electrical bond meets the prior $14,000 baseline but fails the 2026 $16,000 requirement under `CB-2026-006`, so the decision changes from prior-rule `APPROVE` to current `HOLD`.
- `CA-2026-0049`: `DENY` for `DISQUALIFYING_CONDUCT`; the adverse background and fraudulent-registration history require board denial review and remain a pre-existing denial.
- `CA-2026-0050`: `APPROVE` with `NO_DEFICIENCY`; it remains clean under current and prior rules.

The `changed_by_bulletin` list is exactly `CA-2026-0038`, `CA-2026-0045`, and `CA-2026-0048`. Current counts are `APPROVE=1`, `HOLD=11`, `DENY=1`. Under prior rules the counts are `APPROVE=4`, `HOLD=8`, `DENY=1`. There are three new-rule-caused holds, eight pre-existing deficiency holds, one pre-existing denial, and one unchanged approval. One pre-existing hold (`CA-2026-0046`) gains an additional new-rule reason without changing the decision.

The only management escalation is `CA-2026-0049` with `BOARD_DENIAL_REVIEW`.

### Evaluation basis

The evaluator has 8 exact-match scoring points with raw weights 1, 2, or 3:

- `SP001`, weight 1: target batch, impact date, and complete application list in order.
- `SP002`, weight 2: current determination map for all 13 applications.
- `SP003`, weight 3: exact `changed_by_bulletin` rows and bulletin IDs.
- `SP004`, weight 2: bond cases, separating new-rule shortfalls from bond cancellation.
- `SP005`, weight 2: insurance, field-note, and experience-verification holds.
- `SP006`, weight 2: penalty, correspondence, financial-statement, and denial cases.
- `SP007`, weight 3: exact `counterfactual_counts`.
- `SP008`, weight 2: management escalation and clean approval set.

Likely model pitfalls include treating every material-looking correspondence row as a decision-changing bulletin impact, treating bond cancellation as a bond-minimum rule change, missing exact-name unresolved penalties on records whose construction anchor looked clean, counting `CA-2026-0046` as decision-changed even though the financial statement deficiency already holds it, and omitting zero or subset counts from `counterfactual_counts`.

### Transfer design

This test task transfers directly from `train_001` and `train_004`. From `train_001`, solvers should infer how to reconcile contractor applications with bond, insurance, field-note, violation, correspondence, and bulletin records; how to use controlled reason codes; and how to build bulletin-impact summaries from prior-rule baselines. From `train_004`, solvers should transfer the distinction between adverse history, bond cancellation, bond shortfall, insurance holds, correspondence/financial-statement holds, and rule-change summaries.

The high-value transfer-dependent points are `SP003`, `SP004`, `SP005`, `SP006`, and `SP007`. The task-specific exploration comes from the new Q2B entity set, the later 2026 bulletins, extra distractor correspondence and field notes, and random exact-name adverse records that are not described in the prompt.

### Construction record

Author: task-builder subagent for `test_004`. Created: 2026-07-07. Updated: 2026-07-07. Major changes: initial prompt, answer template, standard answer, bilingual notes, evaluator, and self-check report.

## 中文

### 数据和来源

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，以来源样例 `E001`、`E002`、`E003` 作为行政许可审查的总体分布。直接对应的是 `E001` 的承包商资格审查工作流。

共享环境是 `task_group/task_group_019/env/` 下的 Cascadia Licensing Review Portal（CLRP）。目标批次为 `HS-2026-Q2B`，求解器可通过公共 API 和 `/exports/contractor_batch_HS-2026-Q2B.csv` 获取。构造时使用生成的 CLRP 记录和 construction manifest 做来源与锚点校验。求解器本地可见输入只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。

### 任务定义和场景适配

求解器需要为 `HS-2026-Q2B` 的 13 个申请准备截至 `2026-06-30` 的董事会级承包商监管影响筛查。标准答案是结构化 JSON，包含每个申请的当前决定、旧规则反事实决定、`changed_by_bulletin` 列表、聚合 `counterfactual_counts`，以及需要管理层或董事会升级的案件。

该任务符合来源场景，因为它要求跨申请、公告规则、保证金、保险、未解决罚款、现场记录、来往函件和既往不良行为进行行政许可核对。业务产物不是叙述性备忘录，而是能够区分普通缺陷和新规则导致决定变化的决策包。

### 材料地图

关键 CLRP 资源包括：

- `/api/contractors/applications?batch_id=HS-2026-Q2B` 和 `/exports/contractor_batch_HS-2026-Q2B.csv`：目标申请清单、行业、申请日期、经验年限、财务报表标记、背景状态、申报保证金和申报保险。
- `/api/contractors/bulletins?effective_on=2026-06-30`：截至筛查日有效的 2026 年承包商公告及旧规则基线。
- `/api/contractors/bonds?name=...`：有效、金额不足和已取消的保证金。
- `/api/contractors/insurance?name=...`：有效、过期、陈旧和待核验保险记录。
- `/api/contractors/violations?name=...`：未解决罚款和取消资格行为证据。
- `/api/contractors/field-notes?name=...`：开放检查员暂停项以及已解决或干扰性现场记录。
- `/api/contractors/correspondence?batch_id=HS-2026-Q2B`：实质性通知、取消通知，以及非阻断性的已归档或公众询问函件。
- `/api/contractors/complaints?name=...`：投诉背景；并非每条开放或关闭投诉都会独立改变决定。

### 解答依据

答案按申请 ID 升序包含全部 13 个申请。

当前决定和反事实影响如下：

- `CA-2026-0038`：因 `BOND_SHORTFALL` 为 `HOLD`；Concrete 保证金符合旧规则 10,000 美元基线，但不符合 `CB-2026-003` 的 2026 年 12,000 美元要求，因此从旧规则 `APPROVE` 变为当前 `HOLD`。
- `CA-2026-0039`：因 `INSURANCE_VERIFY` 为 `HOLD`；保险记录为过期/陈旧，因此是既有缺陷，不是公告造成的决定变化。
- `CA-2026-0040`：因 `INSURANCE_VERIFY` 为 `HOLD`；Electrical 保险有效但承保机构核验仍待完成，该暂停在旧规则反事实下也存在。
- `CA-2026-0041`：因 `FIELD_NOTE_HOLD` 为 `HOLD`；开放检查员暂停项属于既有缺陷。
- `CA-2026-0042`：因 `UNRESOLVED_PENALTY` 为 `HOLD`；未解决的高严重性罚款属于既有缺陷。
- `CA-2026-0043`：因 `UNRESOLVED_PENALTY` 为 `HOLD`；精确名称匹配的未解决罚款是既有暂停原因，不是新规则导致。
- `CA-2026-0044`：因 `BOND_CANCELLED` 为 `HOLD`；保证金取消是既有缺陷，不是保证金最低额公告变化。
- `CA-2026-0045`：因 `EXPERIENCE_VERIFY` 为 `HOLD`；HVAC 经验为两年，符合旧规则两年基线，但不符合 `CB-2026-011` 的三年要求，因此成为新规则导致的暂停。
- `CA-2026-0046`：因 `CORRESPONDENCE_HOLD` 和 `FINANCIAL_STATEMENT_MISSING` 为 `HOLD`；财务报表缺失在旧规则下也会暂停，`CB-2026-017` 只增加当前函件原因，但不改变总体决定。
- `CA-2026-0047`：因 `UNRESOLVED_PENALTY` 为 `HOLD`；精确名称未解决罚款属于既有缺陷。
- `CA-2026-0048`：因 `BOND_SHORTFALL` 为 `HOLD`；Electrical 保证金符合旧规则 14,000 美元基线，但不符合 `CB-2026-006` 的 2026 年 16,000 美元要求，因此从旧规则 `APPROVE` 变为当前 `HOLD`。
- `CA-2026-0049`：因 `DISQUALIFYING_CONDUCT` 为 `DENY`；不利背景和虚假注册历史需要董事会拒绝复核，属于既有拒绝。
- `CA-2026-0050`：以 `NO_DEFICIENCY` 为 `APPROVE`；当前规则和旧规则下均无缺陷。

`changed_by_bulletin` 列表精确为 `CA-2026-0038`、`CA-2026-0045`、`CA-2026-0048`。当前计数为 `APPROVE=1`、`HOLD=11`、`DENY=1`。旧规则反事实计数为 `APPROVE=4`、`HOLD=8`、`DENY=1`。共有 3 个新规则导致的暂停、8 个既有缺陷暂停、1 个既有拒绝、1 个不变批准。`CA-2026-0046` 是一个既有暂停，但新增了新规则原因。

唯一管理层升级项是 `CA-2026-0049` 的 `BOARD_DENIAL_REVIEW`。

### 评估依据

评估器包含 8 个精确匹配评分点，原始权重为 1、2 或 3：

- `SP001`，权重 1：目标批次、影响日期和完整申请列表顺序。
- `SP002`，权重 2：13 个申请的当前决定映射。
- `SP003`，权重 3：精确的 `changed_by_bulletin` 行和公告 ID。
- `SP004`，权重 2：保证金案件，区分新规则金额不足和保证金取消。
- `SP005`，权重 2：保险、现场记录和经验核验暂停。
- `SP006`，权重 2：罚款、函件、财务报表和拒绝案件。
- `SP007`，权重 3：精确的 `counterfactual_counts`。
- `SP008`，权重 2：管理层升级和无缺陷批准集合。

常见失败点包括把所有看似实质性的函件都当作公告导致的决定变化、把保证金取消当作保证金最低额变化、漏掉锚点看似干净但实际有精确名称未解决罚款的记录、把 `CA-2026-0046` 计为决定受公告改变，以及遗漏 `counterfactual_counts` 中的零散或子集计数。

### 迁移设计

本测试任务直接迁移自 `train_001` 和 `train_004`。从 `train_001`，求解器应迁移如何把承包商申请与保证金、保险、现场记录、违规、函件和公告规则记录进行核对，如何使用受控 reason code，以及如何用旧规则基线构造公告影响摘要。从 `train_004`，求解器应迁移不良历史、保证金取消、保证金不足、保险暂停、函件/财务报表暂停和规则变化汇总之间的区分。

高价值迁移相关评分点为 `SP003`、`SP004`、`SP005`、`SP006` 和 `SP007`。任务自身探索难点来自新的 Q2B 实体集合、较晚的 2026 年公告、额外的干扰函件和现场记录，以及提示中没有明示的随机精确名称不良记录。

### 构造记录

作者：`test_004` 任务构造子代理。创建日期：2026-07-07。更新日期：2026-07-07。主要变更：初始提示、答案模板、标准答案、双语说明、评估器和自检报告。
