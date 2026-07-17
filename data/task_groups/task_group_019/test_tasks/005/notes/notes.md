# test_005 Notes

## English

### Data and Source Lineage

This task belongs to `task_group_019`, scenario `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, with source-example lineage from `E001`, `E002`, and `E003`. It uses the shared Cascadia Licensing Review Portal (CLRP) environment under `task_group/task_group_019/env/`.

The task-builder brief is a mixed review: build a renewal manual-review queue for release batch `RV-2026-FALL` with release boundary `2026-10-15`, and flag one May 2026 successor alcohol premises for restricted-license follow-up. The target alcohol anchor is `AA-2026-0017` / `PM-2026-017`, matching the brief and avoiding reuse of the heavier `PM-2026-036` case already covered by `test_003`.

Solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt gives the base URL placeholder `http://localhost:<PORT>`, the renewal batch and boundary, and the target alcohol review month/application/premises IDs. The template defines controlled enums, ordering rules, integer/date fields, and required JSON structure.

### Task Definition and Scenario Fit

The primary business task is a Fall renewal screen: rank exactly 12 current `RV-2026-FALL` licensees for manual review before release. Each queue row must include the current roster facility name, match confidence, pre-boundary violation count, latest pre-boundary violation date, and a controlled next-step label.

The secondary business task is a restricted-license follow-up flag for the May target premises. The target has same-premises successor risk, a prior warning settlement with controls, a high-severity unresolved late-night disorder incident, a later assault citation, and current restrictions that must be separated into standard obligations versus premises-specific controls.

This fits the scenario because it combines renewal roster-to-violation reconciliation from source example `E003` with same-premises restricted-license judgment from source example `E002`.

### Material Map

For renewal review:

- `renewal_licensees` provides the current `RV-2026-FALL` roster, facility names, addresses, cities, statuses, license types, and successor hints.
- `renewal_violations` provides historical violation rows by historical name, address, city, violation date, code, theme, disposition, fine, ALERT flag, and severity.
- `/api/renewals/licensees?release_batch=RV-2026-FALL`, `/exports/renewal_roster_RV-2026-FALL.csv`, `/api/renewals/violations?city=...`, and `/api/search/address?address=...` are the intended public CLRP surfaces.

For the alcohol successor review:

- `alcohol_applications` identifies `AA-2026-0017`, `PM-2026-017`, `Garden Room 17`, `TAVERN`, and `review_month = 2026-05`.
- `alcohol_premises` supplies same-premises basis, prior licensee `Lantern Hospitality LLC`, and risk summary.
- `alcohol_incidents` supplies four incident rows, including unresolved high-severity `AI-2026-0006`.
- `alcohol_settlements` supplies prior warning settlement `AS-2026-0006`.
- `alcohol_restrictions` supplies `AR-2026-0011` as standard-obligation training evidence and `AR-2026-0012` as the premises-specific patio limit.
- `alcohol_standard_obligations` supplies TAVERN and ALL standard obligations.

### Solution and Evaluation Basis

Renewal matching starts from the current `RV-2026-FALL` roster. Usable violation rows match by city and normalized service address, treating `Suite B, ` as the same address. Exact names, supported close historical names, and shared-address/manual cases must be distinguished. Rows after `2026-10-15` are excluded from ranking, counts, and latest-date fields, but counted in `method_flags.excluded_post_boundary_count`. The Fall matched post-boundary exclusion count is `14`.

The standard queue is:

1. `LIC-RV-2026-0107` Vista Lounge 107
2. `LIC-RV-2026-0134` Signal Hall 134
3. `LIC-RV-2026-0112` Drift Diner 112
4. `LIC-RV-2026-0144` Blue Grill 144
5. `LIC-RV-2026-0128` Crescent Cellar 128
6. `LIC-RV-2026-0138` Hearth Hall 138
7. `LIC-RV-2026-0143` Vista Hall 143
8. `LIC-RV-2026-0135` Copper Hall 135
9. `LIC-RV-2026-0105` Urban Lounge 105
10. `LIC-RV-2026-0110` Signal Diner 110
11. `LIC-RV-2026-0154` Depot Grill 154
12. `LIC-RV-2026-0106` Depot Lounge 106

The queue covers severe/suspension history, exact and close matches, ALERT-pattern manual checks, fine-history manual checks, and one shared-address/additional-record case. `method_flags` records `exact_match_count = 8`, `close_match_count = 3`, `shared_address_manual_count = 1`, `board_review_count = 8`, `manual_fine_check_count = 1`, `manual_ALERT_check_count = 2`, and `additional_record_check_count = 1`.

For the successor premises, `PM-2026-017` is flagged as `ISSUE_RESTRICTED_WITH_MONITORING` with follow-up required. The risk assessment uses same-address overlap, one unresolved high-severity incident (`AI-2026-0006`), four total incidents, prior warning settlement `AS-2026-0006`, one premises-specific control (`PATIO_LIMIT` from `AR-2026-0012`), and separated standard obligations including TAVERN standards, ALL standards, and `TRAINING_STANDARD` from `AR-2026-0011`.

The evaluator has 9 exact-match scoring points:

- `SP001`, weight 2: exact queue membership and current facility names.
- `SP002`, weight 2: ranks 1-4 in exact order.
- `SP003`, weight 2: ranks 5-12 in exact order.
- `SP004`, weight 2: match-confidence values.
- `SP005`, weight 2: pre-boundary counts and latest dates.
- `SP006`, weight 2: next-step labels.
- `SP007`, weight 3: method flags, including `excluded_post_boundary_count`.
- `SP008`, weight 3: successor target, recommendation, follow-up flag, and risk assessment.
- `SP009`, weight 3: successor verification gaps, standard obligations, premises-specific controls, and first-90-day checks.

Likely model pitfalls include ranking only the manifest anchors, using post-boundary Fall violations in the queue, missing close-name history, spreading shared-address evidence to clean licensees, using free-form labels, mixing standard alcohol obligations with premises-specific restrictions, or selecting the already-used `PM-2026-036` target instead of the requested `PM-2026-017`.

### Transfer Design

The renewal portion transfers primarily from `train_003`. The useful inferred method is to start from the current release roster, match histories by city/address/name, accept close names only when continuity is supported, keep shared-address ambiguity as manual, exclude post-boundary rows while counting them, and use controlled next-step labels.

The successor-premises portion transfers from `train_002` and `train_005`. The useful inferred method is to treat same-premises successor risk as material, separate standard license obligations from location-specific restrictions, turn unresolved incidents and prior settlements into verification gaps, and convert premises controls into first-90-day monitoring checks.

Transfer-dependent scoring points are `SP001`, `SP003`, `SP004`, `SP006`, `SP007`, `SP008`, and `SP009`. `SP002` and `SP005` also benefit from transfer but depend heavily on Fall-specific data exploration.

### Construction Record

Author: task-builder subagent for `test_005`, GPT-5.5 xhigh.
Created: 2026-07-07.
Updated: 2026-07-07.
Major changes: initial construction of prompt, answer template, standard answer, evaluator, and bilingual notes.

## 中文

### 数据与来源

本任务属于 `task_group_019`，场景为 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，来源样例包括 `E001`、`E002` 和 `E003`。任务使用共享的 Cascadia Licensing Review Portal（CLRP）环境，路径为 `task_group/task_group_019/env/`。

任务构造要求是混合复核：为续期发布批次 `RV-2026-FALL`、边界日期 `2026-10-15` 建立人工复核队列，并标记一个 2026 年 5 月的继任经营场所进入限制许可后续复核。酒类场所锚点采用 `AA-2026-0017` / `PM-2026-017`，符合任务简述，也避免重复使用已在 `test_003` 中承担重型案例的 `PM-2026-036`。

求解者可见材料包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示词给出基础 URL 占位符 `http://localhost:<PORT>`、续期批次和边界日期，以及酒类复核月份、申请 ID 和场所 ID。模板定义了枚举值、排序规则、整数和日期字段，以及所需 JSON 结构。

### 任务定义与场景适配

主要业务任务是秋季续期筛查：从 `RV-2026-FALL` 当前花名册中排出 12 个需要人工复核的持证人。每个队列行必须包含当前花名册机构名称、匹配置信度、边界前使用的违规数量、最近边界前违规日期，以及受控下一步标签。

次要业务任务是为 5 月目标场所标记限制许可后续复核。该目标存在同场所继任风险、带控制项的既往警告和解、一个未结的高严重性深夜秩序事件、一个较新的袭击报警引用，以及需要区分标准义务和场所特定控制的现有限制。

本任务符合源场景，因为它把 `E003` 的续期花名册与违规历史匹配工作，和 `E002` 的同场所限制许可判断合并到一个真实办公式输出中。

### 材料地图

续期部分：

- `renewal_licensees` 提供 `RV-2026-FALL` 当前花名册、机构名称、地址、城市、状态、许可类型和继任提示。
- `renewal_violations` 提供历史机构名、地址、城市、违规日期、代码、主题、处置、罚款、ALERT 标志和严重性。
- 预期公共入口包括当前续期花名册 API、该批次花名册导出、按城市查询违规历史 API，以及地址搜索 API。

酒类继任场所部分：

- `alcohol_applications` 确认 `AA-2026-0017`、`PM-2026-017`、`Garden Room 17`、`TAVERN` 和 `review_month = 2026-05`。
- `alcohol_premises` 提供同场所依据、既往持证人 `Lantern Hospitality LLC` 和风险摘要。
- `alcohol_incidents` 提供四条事件记录，其中 `AI-2026-0006` 是未结的高严重性事件。
- `alcohol_settlements` 提供既往警告和解 `AS-2026-0006`。
- `alcohol_restrictions` 提供作为标准义务证据的 `AR-2026-0011`，以及场所特定的 patio 限制 `AR-2026-0012`。
- `alcohol_standard_obligations` 提供 TAVERN 和 ALL 类标准义务。

### 解题与评价依据

续期匹配从 `RV-2026-FALL` 当前花名册出发。可用违规记录按城市和规范化服务地址匹配，其中 `Suite B, ` 被视为同一地址。需要区分精确名称、受支持的近似历史名称，以及共享地址人工判断。`2026-10-15` 之后的记录不得用于排名、计数或最近日期，但要计入 `method_flags.excluded_post_boundary_count`。秋季批次匹配但被排除的边界后记录数量为 `14`。

标准队列依次为 `LIC-RV-2026-0107`、`LIC-RV-2026-0134`、`LIC-RV-2026-0112`、`LIC-RV-2026-0144`、`LIC-RV-2026-0128`、`LIC-RV-2026-0138`、`LIC-RV-2026-0143`、`LIC-RV-2026-0135`、`LIC-RV-2026-0105`、`LIC-RV-2026-0110`、`LIC-RV-2026-0154`、`LIC-RV-2026-0106`。

该队列覆盖严重/暂停历史、精确和近似匹配、ALERT 人工检查、罚款人工检查，以及一个共享地址补充记录检查案例。`method_flags` 中记录精确匹配 8 个、近似匹配 3 个、共享地址人工 1 个；董事会复核 8 个、罚款人工检查 1 个、ALERT 人工检查 2 个、补充记录检查 1 个。

继任场所部分将 `PM-2026-017` 标记为 `ISSUE_RESTRICTED_WITH_MONITORING`，并要求后续复核。风险评估依据同地址重叠、一个未结高严重性事件 `AI-2026-0006`、四条总事件、既往警告和解 `AS-2026-0006`、一个场所特定控制 `AR-2026-0012`，以及从 TAVERN 标准、ALL 标准和 `AR-2026-0011` 拆分出的标准义务。

评估器包含 9 个精确匹配评分点，原始权重为 2、2、2、2、2、2、3、3、3。评分覆盖队列成员和当前名称、前四名顺序、第五到第十二名顺序、匹配置信度、违规计数和日期、下一步标签、方法标志、继任场所风险判断，以及继任场所的缺口、义务、控制和 90 天检查。

常见错误包括：只排名 manifest 锚点；把秋季边界后的违规用于排名；漏掉近似名称历史；把共享地址证据扩散给干净持证人；使用自由文本标签；混淆标准酒类义务和场所特定限制；或选择已经在 `test_003` 使用的 `PM-2026-036` 而不是要求的 `PM-2026-017`。

### 迁移设计

续期部分主要迁移自 `train_003`。训练后应能推断出的做法包括：先取当前发布批次花名册，按城市、地址和名称匹配历史；只有存在连续性支持时接受近似名称；把共享地址不确定性保留为人工判断；排除但统计边界后的记录；并使用固定下一步标签。

继任场所部分迁移自 `train_002` 和 `train_005`。训练后应能推断出的做法包括：同场所继任风险本身具有实质意义；标准许可义务要与场所特定限制分离；未结事件和既往和解要转化为验证缺口；场所控制要转化为前 90 天监测检查。

依赖迁移的评分点是 `SP001`、`SP003`、`SP004`、`SP006`、`SP007`、`SP008` 和 `SP009`。`SP002` 和 `SP005` 也受迁移帮助，但更依赖秋季批次的具体数据探索。

### 构造记录

作者：`test_005` task-builder subagent，GPT-5.5 xhigh。
创建日期：2026-07-07。
更新日期：2026-07-07。
主要变更：首次创建提示词、答案模板、标准答案、评估器和双语说明。
