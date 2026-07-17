# train_003 — Country burden and revision audit

## Current whole-point evaluation boundary / 当前整点评分边界

The final eight-point rubric uses raw weights `[2,3,3,2,2,2,3,2]`. Every point is binary: all deterministic checks belonging to that complete business result must pass for the point to earn `weight/19`; any failure earns zero for that point. Set, ordering, and numeric comparison details are retained only as diagnostics. This final rule supersedes historical partial-credit descriptions below.

最终八点评分的原始权重为 `[2,3,3,2,2,2,3,2]`。每个评分点均为二元结果：属于该完整业务结果的所有确定性检查必须全部通过，才能获得 `weight/19`；任一失败则该点为零。集合、顺序和数值比较细节只保留为诊断。本最终规则取代下文历史部分分说明。

## English construction and audit record

### Lineage and task definition

This train task belongs to `SCN_023_public_health_statistical_modeling_audit` and derives its workload profile from source examples `E001`, `E002`, and `E003`, with the country/cross-level ambiguity of `E002` as its closest source analogue. The task design brief is `train_003`: reconcile a supplied 48-country label cohort, reconstruct released country-indicator values, audit revision and scale anomalies, produce a 2022 burden PCA and requested three-cluster segmentation, and estimate the 2017–2022 association of life expectancy with PC1 burden while controlling for region.

All gold evidence was obtained on 2026-07-15 from the running Public Health Observatory Web portal at `http://task-env:9023/` through disposable Docker containers attached to `gdp-qx-023-build-tasks-25c05efd-net`. No environment source file, manifest, seed, database, or mounted environment artifact was inspected. The solver receives the placeholder base URL `<TASK_ENV_BASE_URL>`, `input/payloads/analysis_request.json`, and `input/payloads/answer_template.json`. The request fixes the 48 labels, reference and panel years, eight burden indicator IDs, life-expectancy outcome, and requested cluster count. The template fixes only the result schema, precision, identifiers, list ordering, and controlled enums; it does not disclose the result or rubric.

The business deliverable is one structured JSON audit. It connects country aliases to ISO3, final publication state and revision notices to effective indicator cells, quality screening to a completed analysis matrix, that matrix to PCA and clustering, and the resulting PC1 burden score to a region-adjusted country-year model and controlled advisory. This is a realistic Observatory modeling audit because each downstream result depends on a traceable but independently auditable upstream object.

### Public material map

- Portal home `/` gives the business context and release notices.
- `/catalog` supplies dataset columns, supported filters, row coverage, the measure dictionary, units, and indicator directions.
- `/geographies/countries` and the `countries` CSV export supply `iso3`, canonical names, portal labels, alternate labels, and region.
- `/data/country-indicators` and the `country_indicators` CSV export supply country-year-indicator release rows, statuses, revisions, values, units, and quality flags.
- `/data/revisions` and the `revisions` CSV export supply revision-event IDs, status, effective year, old/new values, and reason codes.
- `/methodology` supplies current public policies for stable identifiers, aliases, release lifecycle, indicator direction and units, revision notices, and quality flags.
- `input/payloads/analysis_request.json` is the task-local analyst request and is the sole source for cohort labels, years, indicator set, outcome, and requested `k=3`.
- `input/payloads/answer_template.json` describes the solver's exact output contract.
- `eval/build_gold.py` is the retained reproducibility helper. It reads only the public Web CSV exports, reconstructs the result, and prints the answer JSON. It requires Python with NumPy, pandas, scikit-learn, and statsmodels and accepts `--base-url`.
- `output/answer.json` is the standard answer; `eval/evaluator.py` and `eval/eval.sh` provide deterministic local scoring.

### Effective-state and statistical basis

Country labels are case-insensitively compared with canonical, portal, and alternate labels, but only unique matches are accepted. All 48 labels resolve to `QAA` through `QBV`; 14 supplied labels differ from the canonical name. ISO3 lists are uppercase, unique, and ascending.

For every ISO3/year/indicator cell, the governing observation is the highest revision of a `FINAL` row, with release timestamp and observation ID as deterministic final tie breakers. Provisional rows never govern. Applied revision notices are realized by later final revisions; pending or withdrawn notices do not replace the released value. In the 2017–2022 requested burden scope the applicable applied events are `RV00000001`, `RV00000002`, `RV00000003`, and `RV00000004`; non-applied events are `RV00000007` and `RV00000010`.

An unresolved scale break is a selected latest-final row flagged `SCALE_REVIEW` whose absolute value is at least five times each available positive adjacent-year value. Screening occurs only after release/revision selection. This records `QAG|2022|immunization_gap` and `QAJ|2019|schooling_gap`; the affected cells are excluded rather than divided by ten. The 2022 raw cross-section has 50 ordinary missing cells and one anomaly exclusion, so 51 cells are imputed. Median imputation is by indicator within the requested 2022 cross-section, leaving a 48-by-8 usable matrix.

All eight requested fields are burden measures for which higher is worse. Each completed column is centered and divided by its sample standard deviation (`ddof=1`). PCA uses the full deterministic SVD. PC1 sign is oriented so the sum of its burden loadings is positive, making a larger score higher burden. Components with eigenvalue strictly greater than 1 are retained. One component is retained; PC1 explains `0.7426`. The three largest absolute PC1 coefficients are `adult_mortality` (`0.3744`), `infant_mortality` (`0.3696`), and `poverty_rate` (`0.3695`) in that order.

Clustering uses the retained PCA score matrix and Euclidean k-means with seed `2307` and 50 initializations. Candidate silhouette coefficients for `k=2..5` are `0.6392`, `0.5589`, `0.5993`, and `0.6102`, so the silhouette choice is 2 even though the requested operational segmentation is 3. The three clusters are labeled by ascending cluster mean PC1 as `LOW_BURDEN`, `MIDDLE_BURDEN`, and `HIGH_BURDEN`; sizes are 22, 15, and 11. High-burden members are `QAA`, `QAG`, `QAQ`, `QBA`, `QBD`, `QBE`, `QBG`, `QBK`, `QBM`, `QBQ`, and `QBU`.

For the panel, each 2017–2022 burden row uses the 2022 indicator medians, means, sample standard deviations, and oriented PC1 coefficient vector, which preserves a common burden reference over time. Missing or excluded predictor cells use the 2022 median; country-years missing life expectancy are not modeled. OLS includes an intercept, PC1 burden, and categorical region fixed effects (alphabetically first region omitted). The 264 usable observations yield a PC1 coefficient of `-2.9507` life-expectancy years per score unit, standard error `0.0594`, two-sided p-value `0.0000`, and `R²=0.9385`. A negative association at `p<0.05` maps to `PRIORITIZE_HIGH_BURDEN_CLUSTER`; a negative non-significant coefficient maps to `MONITOR_GRADIENT`; a nonnegative coefficient maps to `NO_ADVERSE_GRADIENT`.

### Evaluation design and likely pitfalls

The evaluator has exactly eight business points with raw weights `[2,3,3,2,2,2,3,2]`, total 19:

1. `SP001` (2): label counts, alias count, ISO3 precision/recall, and stable ordering.
2. `SP002` (3): applied and non-applied revision-event sets plus unresolved anomaly keys.
3. `SP003` (3): raw missingness, anomaly and imputation counts, and usable matrix dimensions.
4. `SP004` (2): retained component count and PC1 variance fraction.
5. `SP005` (2): loading rank positions, exact order, and per-indicator signed loading values.
6. `SP006` (2): silhouette-selected `k`, four silhouette values, three sizes, and high-burden membership.
7. `SP007` (3): panel sample, coefficient, standard error, p-value, fit, and region-control declaration.
8. `SP008` (2): controlled advisory.

Each point contributes `weight/19`. Within-point shares are declared in `evaluator.py`; count and enum checks are exact, decimals are rounded half-up to four places before comparison, and set-like lists use trimmed normalized membership with F1 partial credit. Ordering has a separate small subcheck where the template requires stable ascending lists. The loading result uses meaningful positional and per-indicator numeric shares. Parse failure produces eight zeroed points with a diagnostic rather than an exception. The gold answer must score exactly `1.0`; a single-aspect wrong answer should normally reduce only its associated point, while naturally decomposable incomplete sets or model summaries earn a score strictly between zero and one.

Validation on 2026-07-15 confirmed gold `1.0`. Changing only the advisory scored `0.8947368421` and affected only `SP008`; retaining only one of the two anomaly keys scored `0.9815789474` with `SP002` fraction `0.8833333333`; swapping the first two loading rows scored `0.9526315789` with `SP005` fraction `0.55`. A missing prediction file returned `0.0` with all eight point diagnostics. These probes demonstrate both selective isolation and normalized partial credit.

Likely pitfalls are choosing a provisional or first-final row, treating pending/withdrawn notices as corrections, screening before incorporating applied final revisions, silently dividing scale breaks, treating missing cells as zero, using population instead of sample standard deviations, accepting arbitrary PCA sign, clustering raw fields, reporting the silhouette optimum instead of the requested three-group membership, re-estimating incomparable PCA bases by year, or coding region as an ordinal number.

### Transfer value

This solved train task establishes observable conventions for later country audits without presenting a tutorial in the solver prompt. Comparing the input, standard answer, and portal evidence lets an analyst infer stable ISO3 reconciliation; latest-final applied-revision precedence; correction before anomaly screening; explicit exclusion rather than silent scale repair; cross-section median imputation; burden orientation; sample-standardized PCA with deterministic sign and component retention; semantic cluster labels; and a common-reference, region-adjusted panel interpretation. The unseen country task changes the cohort, years, indicators, number of clusters, missingness, anomalies, and final inference, so these conventions transfer while the task-specific evidence and numerical work must still be performed.

### Construction record

- Author: OpenAI Codex task builder for `train_003`
- Created: 2026-07-15
- Updated: 2026-07-15
- Major changes: created the task-local analyst request and schema; extracted gold evidence exclusively from live Web surfaces; retained a reproducible gold builder; implemented the standard answer and eight-point partial-credit evaluator; recorded revision, anomaly, PCA, clustering, panel, transfer, and validation bases.

## 中文构建与审计记录

### 血缘与任务定义

本训练任务属于 `SCN_023_public_health_statistical_modeling_audit`，工作量设计参考来源样例 `E001`、`E002`、`E003`，其中最接近的是 `E002` 的国家层面和跨层级数据歧义。`train_003` 的设计要求是：核对 48 个国家标签并映射到 ISO3，重建正式发布的国家指标值，审计修订和尺度异常，形成 2022 年负担 PCA 与指定的三类分组，并在控制地区后估计 2017–2022 年预期寿命与 PC1 负担的关系。

全部标准答案证据均于 2026-07-15 从运行中的 Public Health Observatory Web 门户 `http://task-env:9023/` 获取；访问通过连接到 `gdp-qx-023-build-tasks-25c05efd-net` 的一次性 Docker 容器完成。构建过程中没有查看环境源文件、清单、种子、数据库或挂载任何环境构件。求解者只会看到占位地址 `<TASK_ENV_BASE_URL>`、`analysis_request.json` 与 `answer_template.json`。请求文件固定国家标签、年份、八项负担指标、预期寿命结局以及三类分组；模板只公开输出结构、精度、稳定标识符、排序和受控枚举，不公开答案或评分权重。

该业务交付物是一份结构化 JSON 审计。它把国家别名连接到 ISO3，把正式发布状态和修订通告连接到有效指标单元格，把质量筛查连接到完整分析矩阵，再把矩阵连接到 PCA、聚类、面板模型和受控建议。这与本场景的统计建模审计高度一致，因为每个下游结论都有可追踪且可独立审计的上游对象。

### 公共材料地图

- 门户首页 `/` 提供业务背景与发布提示。
- `/catalog` 提供数据列、筛选项、覆盖范围、指标字典、单位和方向。
- `/geographies/countries` 及 `countries` CSV 提供 ISO3、标准名称、门户标签、备选标签和地区。
- `/data/country-indicators` 及 `country_indicators` CSV 提供国家—年份—指标发布记录、状态、修订号、数值、单位和质量标志。
- `/data/revisions` 及 `revisions` CSV 提供修订事件编号、状态、生效年份、新旧值和原因代码。
- `/methodology` 提供稳定地理标识、别名、发布生命周期、指标方向与单位、修订通告及质量标志的现行政策。
- `analysis_request.json` 是本任务的分析请求，也是国家标签、年份、指标集、结局和 `k=3` 的唯一任务本地来源。
- `answer_template.json` 规定求解者的准确输出契约。
- `eval/build_gold.py` 是保留的可复现辅助程序，只读取公共 Web CSV，重建结果并打印答案 JSON。
- `output/answer.json` 是标准答案，`evaluator.py` 与 `eval.sh` 提供确定性本地评分。

### 有效状态与统计依据

国家标签以不区分大小写方式与标准名称、门户标签和备选标签比较，但只接受唯一匹配。48 个标签全部解析为 `QAA` 至 `QBV`，其中 14 个输入标签不同于标准名称。ISO3 列表使用大写、去重并按升序排列。

每个 ISO3—年份—指标单元格选择 `FINAL` 记录中的最高修订号；发布时间和观测编号作为确定性最终破同规则。临时发布不会成为正式值。已应用修订通过后续正式修订体现，待处理或撤回通告不替换发布值。2017–2022 年所需负担范围内，已应用事件为 `RV00000001` 至 `RV00000004`，未应用事件为 `RV00000007` 和 `RV00000010`。

未解决的尺度断点定义为：最终选中记录的质量标志为 `SCALE_REVIEW`，且其绝对值至少为每个可用正值相邻年份的五倍。筛查必须在发布与修订选择之后进行。最终记录 `QAG|2022|immunization_gap` 和 `QAJ|2019|schooling_gap`，这些单元格被排除，不能静默除以十。2022 年原始截面有 50 个普通缺失单元格和 1 个异常排除单元格，因此共插补 51 个单元格。按指标使用请求截面内中位数插补后，得到 48×8 矩阵。

八个字段均为数值越高负担越重的指标。每列以样本标准差（`ddof=1`）标准化。PCA 使用完整确定性 SVD；通过让 PC1 负担载荷之和为正来固定符号，使较高得分表示较高负担。保留特征值严格大于 1 的成分。最终保留 1 个成分，PC1 解释 `0.7426` 的方差。绝对载荷前三项依次是 `adult_mortality`（`0.3744`）、`infant_mortality`（`0.3696`）和 `poverty_rate`（`0.3695`）。

聚类使用保留的 PCA 得分、欧氏 k-means、随机种子 `2307` 和 50 次初始化。`k=2..5` 的轮廓系数依次为 `0.6392`、`0.5589`、`0.5993`、`0.6102`，所以诊断最优值为 2，但业务要求的实际分组仍为 3。三类按平均 PC1 从低到高标记为 `LOW_BURDEN`、`MIDDLE_BURDEN`、`HIGH_BURDEN`，规模为 22、15、11；高负担集合为 `QAA`、`QAG`、`QAQ`、`QBA`、`QBD`、`QBE`、`QBG`、`QBK`、`QBM`、`QBQ`、`QBU`。

面板阶段对 2017–2022 年统一使用 2022 年的中位数、均值、样本标准差和定向 PC1 系数向量，以保证时间上的共同负担基准。预测指标的缺失或异常使用 2022 年中位数，缺失预期寿命的国家年份不进入模型。OLS 包含截距、PC1 负担和分类地区固定效应。264 个观测得到系数 `-2.9507`、标准误 `0.0594`、双侧 p 值 `0.0000` 和 `R²=0.9385`。负系数且 `p<0.05` 映射到 `PRIORITIZE_HIGH_BURDEN_CLUSTER`。

### 评分、陷阱与迁移

评估器恰好包含八个业务评分点，原始权重为 `[2,3,3,2,2,2,3,2]`，总权重 19。八点分别评估标签协调、修订与异常、矩阵可用性、PCA 保留、载荷排序、聚类、面板模型和建议。每点最大贡献为 `weight/19`。四位小数采用半入舍入后精确比较；集合使用标准化成员关系和 F1 部分分，稳定排序另设小比例子检查；载荷使用位置与按指标数值的自然部分分。解析失败会返回带诊断的八个零分评分点。标准答案必须得到 `1.0`，单项错误通常只损失对应评分点，缺失部分集合或模型摘要会得到严格介于 0 与 1 之间的分数。

2026-07-15 的验证结果如下：标准答案得分 `1.0`；只修改建议时得分 `0.8947368421`，仅影响 `SP008`；异常集合只保留一个键时得分 `0.9815789474`，`SP002` 内部分数为 `0.8833333333`；交换前两个载荷行时得分 `0.9526315789`，`SP005` 内部分数为 `0.55`；缺失预测文件返回 `0.0` 和八点诊断。这些探针验证了评分隔离与归一化部分分。

常见错误包括选择临时发布或首个正式修订、把待处理或撤回通告当作已应用修订、在修订前筛查异常、把尺度断点静默除以十、把缺失当零、使用总体标准差、任意保留 PCA 符号、在原始字段上聚类、用轮廓最优分组替代指定三类成员、逐年重新估计不可比 PCA 基准，或把地区编码为连续数值。

本训练任务可让后续国家审计迁移以下惯例：ISO3 稳定协调、最高正式修订优先、先应用修订再筛查异常、异常排除而非静默修复、截面中位数插补、负担定向、样本标准化 PCA、确定性符号和成分保留、语义化聚类标签，以及共同参照下的地区调整面板解释。未见测试任务会改变国家集合、年份、指标、聚类数、缺失、异常和最终推断，因此惯例能够迁移，但仍需重新探索任务特定证据并完成数值计算。

### 构建记录

- 作者：OpenAI Codex `train_003` 任务构建者
- 创建日期：2026-07-15
- 更新日期：2026-07-15
- 主要变更：创建本地分析请求与模板；只从实时 Web 页面提取标准证据；保留可复现答案构建器；实现标准答案和八点评估器；记录修订、异常、PCA、聚类、面板、迁移和验证依据。
