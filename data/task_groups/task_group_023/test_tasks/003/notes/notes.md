# test_003 — Country preventable-mortality burden and longevity-stall audit

## Current whole-point evaluation boundary / 当前整点评分边界

The final rubric uses eight whole points with raw weights `[2,3,2,3,2,2,3,2]`. The complete pass conditions are: all reconciliation counts; the complete revision/anomaly state; all matrix-audit counts; retained PCA dimension; the exact ordered cluster-size profile; the exact high-burden set; the complete panel summary; and the controlled conclusion. A point earns its full `weight/19` or zero, with no within-point fractions. Historical F1 or positional fractions below are diagnostic only.

最终评分采用八个整点，原始权重为 `[2,3,2,3,2,2,3,2]`。完整通过条件依次为：全部协调计数、完整修订与异常状态、全部矩阵审计计数、PCA 保留维度、精确有序聚类规模、精确高负担集合、完整面板摘要和受控结论。每点只能获得完整 `weight/19` 或零，不存在点内部分分。下文历史 F1 或位置比例仅用于诊断。

## English construction and evaluation record

### Lineage, task definition, and scenario fit

This test task belongs to `SCN_023_public_health_statistical_modeling_audit` and `task_group_023`. Its design abstracts the country-level statistical audit work in source examples `E001`, `E002`, and `E003`: reconcile records across differently keyed sources, establish effective publication state, build an explicit eligible cohort, run a multivariate model, audit data quality, and issue a controlled business conclusion. The portal data are generated Observatory data published through the shared read-only Web workplace; no task-specific answer endpoint or task-specific dataset is used.

The business request is a 2023 preventable-mortality burden audit for 52 named countries (`QAA` through `QBZ` after reconciliation). It uses nine burden indicators, a requested four-cluster profile, and a 2018–2023 life-expectancy panel. The committee asks whether the highest-burden profile has a statistically supported, non-improving longevity trend. The solver sees `input/prompt.txt`, `input/payloads/analysis_request.json`, `input/payloads/answer_template.json`, and the public portal rooted at `<TASK_ENV_BASE_URL>`. The expected deliverable is one structured JSON object matching the template.

This is a scenario-fit test because it combines geography/alias reference data, longitudinal observations, release metadata, revision notices, indicator definitions, missingness, cross-sectional PCA, clustering, and a panel business decision. The data flow is country label → stable ISO3 → effective country-indicator observation → revision/anomaly state → eligible 2023 matrix → PCA/cluster membership → 2018–2023 panel interaction → controlled conclusion. Each stage can be audited through a different public portal surface.

### Material map and public evidence

- `input/prompt.txt` gives the realistic committee request, portal base URL, reporting precision, and the operational stall definition. It intentionally does not enumerate the reusable Observatory conventions.
- `input/payloads/analysis_request.json` fixes the 52 supplied labels, the nine indicator IDs, the 2023 reference year, four requested clusters, the 2018–2023 panel window, `life_expectancy`, region controls, and the target interaction.
- `input/payloads/answer_template.json` declares every required key, type, unit, enum, stable identifier, precision rule, and list order without exposing any answer value or rubric weight.
- `/catalog` supplies dataset columns, coverage, indicator units, and indicator direction.
- `/geographies/countries` and the matching `countries` CSV export reconcile canonical names, portal labels, alternate labels, ISO3 codes, and regions.
- `/data/country-indicators` and its filtered CSV export provide year, indicator, release status, revision, release date, value, unit, and quality flag.
- `/data/revisions` and its filtered CSV export distinguish `APPLIED`, `PENDING`, and `WITHDRAWN` notices.
- `/methodology` provides current release-lifecycle, country-revision, quality, alias, direction, and unit documents; superseded or draft text is not governing evidence.
- `output/answer.json` is the exact standard result. `eval/eval.sh` launches `eval/evaluator.py`, which contains the deterministic eight-point rubric and diagnostics.

### Standard-answer construction

The 52 request labels reconcile one-to-one to `QAA`–`QBZ`. Fourteen supplied `Republic of ...` labels use the non-canonical portal-label path, while all 52 resolve to a stable ISO3. For every ISO3/year/indicator, the effective observation is the highest revision among final releases. Applied country scale corrections within the requested indicators and panel window are `QAA/adult_mortality/2018`, `QAB/infant_mortality/2019`, `QAC/poverty_rate/2020`, and `QAE/unemployment/2021`; their later final revision values govern before screening. The unresolved breaks are `QAG/immunization_gap/2022` (`PENDING`), `QAI/alcohol_harm/2023` (`PENDING`), and `QAJ/schooling_gap/2019` (`WITHDRAWN`). Those three ISO3s are logged and excluded; a pending or withdrawn correction value is not substituted.

The resulting 2023 burden matrix has 49 countries and nine indicators. Before imputation it has 47 missing cells distributed across 30 countries. Each column is median-imputed within this eligible 2023 cross-section. All nine dictionary directions are higher-worse, so no favorable-direction reversal is needed. Columns are standardized with sample standard deviations. PCA retains eigenvalues strictly greater than 1, and PC1 is signed so increasing scores represent increasing overall burden. One component is retained; PC1 explains `0.7318`. The descending absolute PC1 loading order is `adult_mortality`, `infant_mortality`, `poverty_rate`, `immunization_gap`, `health_spending_gap`, `unemployment`, `schooling_gap`, `hiv_burden`, `alcohol_harm`.

Four-cluster k-means is fit to the retained PCA scores (`n_init=50`, deterministic seed 42). Raw labels are relabeled by ascending cluster mean PC1 so their stable burden ranks have sizes `[7, 17, 18, 7]`. The highest-burden set is `QAQ`, `QBA`, `QBD`, `QBE`, `QBM`, `QBQ`, `QBU`.

For the panel, the same anomaly exclusions and effective-final observation rule are used. Nonmissing `life_expectancy` produces 268 country-year rows from 49 countries. OLS includes an intercept, `year - 2018`, a highest-burden indicator, their interaction, and portal-region fixed effects (Africa is the omitted reference). The other-country annual slope is `0.1982`, the high-burden-by-year interaction is `-0.1649` with p-value `0.7479`, and the resulting high-burden annual slope is `0.0332`. The interaction is not statistically significant and the high-burden slope is positive, so the controlled conclusion is `STALL_NOT_SUPPORTED`.

### Rubric, independence, and partial credit

The raw weights are exactly `[2, 3, 2, 3, 2, 2, 3, 2]` (total 19), normalized by `weight / 19`.

1. `SP001` (2): requested-label, ISO3-match, and portal-alias counts; three equal exact subchecks.
2. `SP002` (3): applied correction state, unresolved event state, and anomaly exclusions. Counts and event sets receive documented shares; event and ISO3 sets use normalized precision/recall F1.
3. `SP003` (2): eligible matrix size, missing-cell count, affected-country count, and imputation count; four equal exact subchecks.
4. `SP004` (3): retained component count (0.25), PC1 variance (0.25), and full loading order (0.50). The ordered list receives an LCS-based sequence F1, which penalizes omissions, additions, and inversions.
5. `SP005` (2): four burden-ranked cluster sizes; positional partial credit with an explicit length penalty.
6. `SP006` (2): high-burden ISO3 membership; normalized set F1.
7. `SP007` (3): panel country/row coverage, other-country slope, target interaction, p-value, and high-burden slope. Shares are 0.10, 0.10, 0.15, 0.30, 0.20, and 0.15.
8. `SP008` (2): exact controlled conclusion enum.

Four-decimal statistics use a half-unit tolerance (`0.00005` plus floating-point epsilon). Identifiers are trimmed and case-normalized; set-like lists are deduplicated; ordered PCA and cluster-size lists retain order. JSON or root-type failures score zero with diagnostics. The rubric spans independently fail-able reconciliation, publication/revision state, missingness, dimension reduction, cluster structure, priority membership, longitudinal inference, and policy classification. Upstream cohort choices affect true downstream calculations, but prediction fields are scored separately so a solver can receive deterministic credit for correctly completed business aspects.

Likely pitfalls include matching an ambiguous short country name instead of the supplied full label, using provisional or lower final revisions, applying pending/withdrawn replacement values, treating a scale break as an ordinary outlier or silently dividing it by ten, zero-filling missing indicators, using population rather than sample standard deviation, leaving PC1 sign arbitrary, clustering all nine standardized columns instead of retained PCA scores, trusting raw k-means label numbers, fitting the panel to all 52 requested countries, omitting region effects, or interpreting a negative but non-significant interaction as a supported stall.

### Transfer design

`train_003` is the primary anchor. It establishes the country-family habits needed to reconcile labels, distinguish applied revisions from unresolved scale anomalies, orient burden variables, build an imputed standardized PCA cross-section, interpret cluster burden, and read a region-controlled panel result. Release precedence is also anchored by `train_001` and `train_004`, which reinforce final-over-provisional selection and highest governing final revision.

- `SP002` is transfer-dependent for correction/anomaly precedence: the solver must infer from `train_003` and the release anchors that applied corrections govern before scale screening and that pending or withdrawn notices do not authorize replacement. Task-specific exploration is still required to discover the seven in-window events and the exact `QAG/QAI/QAJ` exclusions.
- `SP004` is transfer-dependent for burden orientation, within-cross-section median imputation, sample-SD standardization, PCA retention, and a stable burden-facing PC1 sign. Task-specific exploration determines the 47 missing cells, the one-component result, `0.7318`, and the nine-indicator loading order.
- `SP007` is transfer-dependent for carrying the eligible cluster definition into a region-controlled panel and interpreting the interaction as a difference in annual longevity slope. Task-specific exploration determines the later 2018–2023 coverage, 268 rows, profile membership, coefficient, p-value, and derived high-burden slope.

The remaining points deliberately preserve exploration difficulty: the 52-label alias mix, 2023 missingness pattern, four-cluster sizes, high-burden set, and exact stall conclusion are not stated by any train answer. Solver-visible materials state the business request and output contract but do not restate these hidden conventions or results.

### Construction record

- Author: Codex task builder `/root/build_test_003`
- Created: 2026-07-15
- Updated: 2026-07-15
- Major changes: created the distinct 52-country request and nine-indicator/four-cluster audit; derived exact gold exclusively from live portal surfaces through disposable containers; implemented the eight-point normalized evaluator; documented transfer anchors and deterministic partial scoring.

## 中文构建与评估记录

### 数据血缘、任务定义与场景适配

本测试任务属于 `SCN_023_public_health_statistical_modeling_audit` 和 `task_group_023`。设计抽象自来源示例 `E001`、`E002`、`E003` 中的国家级统计审计工作：跨不同键值的数据源核对记录，确定有效发布状态，构造明确的合格队列，运行多变量模型，审计数据质量，并形成受控业务结论。门户数据是通过共享只读 Web 工作区发布的观测站生成数据；任务不使用专用答案端点或专用任务数据集。

业务请求针对核对后为 `QAA` 至 `QBZ` 的 52 个国家，执行 2023 年可预防死亡负担审计。任务使用九个负担指标、四个聚类和 2018—2023 年预期寿命面板，判断最高负担组是否存在具有统计支持且不再改善的寿命趋势。求解者可见 `input/prompt.txt`、`input/payloads/analysis_request.json`、`input/payloads/answer_template.json`，以及以 `<TASK_ENV_BASE_URL>` 为根地址的公共门户；交付物是一个符合模板的 JSON 对象。

该任务符合场景，因为它把地理与别名参考、纵向观测、发布元数据、修订通知、指标定义、缺失性、横截面主成分分析、聚类和面板业务判断连接在一起。数据流为：国家标签 → 稳定 ISO3 → 有效国家指标观测 → 修订与异常状态 → 2023 年合格矩阵 → 主成分与聚类成员 → 2018—2023 年面板交互项 → 受控结论。每个阶段都可通过不同的公共门户页面审计。

### 材料映射与公共证据

- `input/prompt.txt` 提供委员会请求、门户地址、报告精度和停滞定义，但不列举可复用的内部约定。
- `input/payloads/analysis_request.json` 固定 52 个标签、九个指标、2023 年参考期、四个聚类、2018—2023 年面板窗口、`life_expectancy`、地区控制变量和目标交互项。
- `input/payloads/answer_template.json` 声明必需键、类型、单位、枚举、稳定标识符、精度和列表顺序，不泄露答案值或权重。
- `/catalog` 用于确认数据列、覆盖年份、单位和指标方向。
- `/geographies/countries` 及 `countries` CSV 导出用于核对规范名称、门户标签、替代标签、ISO3 和地区。
- `/data/country-indicators` 及筛选后的 CSV 导出提供年份、指标、发布状态、修订号、发布日期、数值、单位和质量标志。
- `/data/revisions` 及筛选后的 CSV 导出用于区分 `APPLIED`、`PENDING` 和 `WITHDRAWN` 通知。
- `/methodology` 提供当前有效的发布周期、国家修订、质量、别名、方向和单位文档；已取代或草案文本不作为控制证据。
- `output/answer.json` 保存精确标准答案；`eval/eval.sh` 启动 `eval/evaluator.py`，后者包含确定性的八点评分和诊断。

### 标准答案构造

52 个请求标签一一核对到 `QAA`—`QBZ`；其中 14 个 `Republic of ...` 标签通过非规范门户标签路径匹配。每个 ISO3、年份和指标都选择最终发布记录中的最高修订。窗口内已应用的尺度修订为 `QAA/adult_mortality/2018`、`QAB/infant_mortality/2019`、`QAC/poverty_rate/2020` 和 `QAE/unemployment/2021`，其后续最终修订先于异常筛查生效。未解决的尺度断点为 `QAG/immunization_gap/2022`（待定）、`QAI/alcohol_harm/2023`（待定）和 `QAJ/schooling_gap/2019`（已撤回）。这三个 ISO3 被记录并排除；不得使用待定或已撤回通知中的替代值。

排除后，2023 年负担矩阵包含 49 个国家和九个指标。插补前共有 47 个缺失单元，分布在 30 个国家。每列在本次合格横截面内用中位数插补，并以样本标准差标准化。九个指标均为数值越高负担越差。主成分保留特征值严格大于 1 的成分，并统一 PC1 符号，使分数越高表示总体负担越重。最终保留一个成分，PC1 解释比例为 `0.7318`。绝对载荷降序为 `adult_mortality`、`infant_mortality`、`poverty_rate`、`immunization_gap`、`health_spending_gap`、`unemployment`、`schooling_gap`、`hiv_burden`、`alcohol_harm`。

在保留的主成分分数上执行四类 k 均值聚类，使用 50 次初始化和固定种子 42。原始标签按聚类平均 PC1 从低到高重新编号，四组规模为 `[7, 17, 18, 7]`。最高负担组为 `QAQ`、`QBA`、`QBD`、`QBE`、`QBM`、`QBQ`、`QBU`。

面板沿用相同异常排除和有效最终发布规则。非缺失 `life_expectancy` 得到 49 个国家的 268 条国家年度记录。普通最小二乘模型包含截距、`year - 2018`、最高负担组指示变量、两者交互项和门户地区固定效应，以非洲为省略类别。其他国家年斜率为 `0.1982`，最高负担组与年份交互项为 `-0.1649`，p 值为 `0.7479`，最高负担组总年斜率为 `0.0332`。交互项不显著且总斜率为正，因此结论是 `STALL_NOT_SUPPORTED`。

### 评分、独立性与部分得分

原始权重严格为 `[2, 3, 2, 3, 2, 2, 3, 2]`，总计 19，并按 `weight / 19` 归一化。

1. `SP001`（2）：请求标签数、ISO3 匹配数和门户别名匹配数，三个等份精确子检查。
2. `SP002`（3）：已应用修订、未解决事件和异常排除；计数和事件集按明示份额评分，集合使用规范化精确率与召回率 F1。
3. `SP003`（2）：合格矩阵规模、缺失单元数、受影响国家数和插补数，四个等份精确子检查。
4. `SP004`（3）：保留成分数占 0.25，PC1 解释比例占 0.25，完整载荷顺序占 0.50；顺序列表使用基于最长公共子序列的序列 F1，同时惩罚遗漏、增加和倒序。
5. `SP005`（2）：四个按负担排序的聚类规模，提供带长度惩罚的位置部分得分。
6. `SP006`（2）：最高负担 ISO3 成员集合，使用集合 F1。
7. `SP007`（3）：面板国家数、行数、其他国家斜率、目标交互项、p 值和最高负担组斜率，份额依次为 0.10、0.10、0.15、0.30、0.20、0.15。
8. `SP008`（2）：受控结论枚举精确匹配。

四位小数统计量采用末位半单位容差 `0.00005` 并附加浮点误差余量。标识符去除首尾空白并统一大小写，集合列表去重，PCA 与聚类规模列表保留顺序。JSON 解析或根类型错误得到零分并输出诊断。八点评分覆盖可独立失败的标签核对、发布修订、缺失性、降维、聚类结构、重点成员、纵向推断和政策分类。真实计算存在上游依赖，但预测字段分开评分，因此可对已正确完成的业务部分给予确定性得分。

常见错误包括使用含糊的国家简称、选择临时发布或较低最终修订、应用待定或撤回的替代值、把尺度断点当作普通离群值或直接除以十、把缺失值填零、使用总体标准差、任由 PC1 符号不确定、直接聚类九个原始标准化变量、依赖 k 均值原始标签、把全部 52 国纳入面板、遗漏地区效应，或把不显著的负交互项解释为已支持停滞。

### 迁移设计

`train_003` 是主要锚点，提供国家标签核对、已应用修订与未解决异常区分、负担方向、插补标准化主成分分析、聚类负担解释和地区控制面板结果的可迁移知识。`train_001` 与 `train_004` 是发布规则锚点，强化最终发布优先于临时发布以及使用最高有效最终修订。

- `SP002` 的迁移难点是修订与异常的先后关系：需要从 `train_003` 及发布锚点推断，已应用修订应先于尺度筛查生效，而待定或撤回通知不能授权替换。任务特定探索仍需发现窗口内七个事件及 `QAG/QAI/QAJ` 排除集合。
- `SP004` 的迁移难点是负担方向、横截面内中位数插补、样本标准差、成分保留和稳定的负担方向 PC1 符号。任务特定探索决定 47 个缺失单元、单成分、`0.7318` 以及九指标载荷次序。
- `SP007` 的迁移难点是把合格聚类成员带入地区控制面板，并把交互项解释为年寿命斜率差。任务特定探索决定新的 2018—2023 年覆盖、268 行、成员集合、系数、p 值和派生斜率。

其余评分点保留了探索难度：52 标签组合、2023 年缺失模式、四组规模、最高负担集合和最终判断均未由训练答案直接陈述。求解者可见材料只给出业务请求和输出契约，不重述隐藏约定或结果。

### 构建记录

- 作者：Codex 任务构建者 `/root/build_test_003`
- 创建日期：2026-07-15
- 更新日期：2026-07-15
- 主要变更：创建独立的 52 国、九指标和四聚类审计；仅通过一次性容器访问实时门户推导精确标准答案；实现八点评估器；记录训练锚点、迁移关系与确定性部分评分。
