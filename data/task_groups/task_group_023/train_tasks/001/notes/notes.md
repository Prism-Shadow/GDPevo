# Construction and Review Notes

## Current whole-point evaluation boundary / 当前整点评分边界

This section is authoritative for the final artifact and supersedes historical wording below about partial or element-level credit. The task has eight rubric points with raw weights `[1,3,3,3,3,3,3,2]`. For every point, all of its named deterministic subchecks must pass; the point then earns its complete `weight/21`, otherwise it earns zero. Subcheck fractions remain evaluator diagnostics only and never contribute fractional score.

本节是最终产物的权威评分说明，并取代下文历史记录中关于部分分或元素级得分的表述。任务包含八个评分点，原始权重为 `[1,3,3,3,3,3,3,2]`。每个评分点的全部命名确定性子检查都必须通过；通过时获得完整的 `weight/21`，否则为零。子检查比例仅用于诊断，不产生任何点内部分分。

## English construction record

### Solved-answer V1 transfer registry

The versioned registry for `PHO_STATE_TRANSPORT_AUDIT_V1` in family `PHO_STATE_ALGORITHMIC_TRANSPORT_FAMILY_V1` appears only as optional top-level `protocol_registry_record` metadata in the solved standard answer. The registry contains exactly one child, `portable_protocol_profile`, and therefore carries reusable method semantics but no request snapshot or instance binding. The solver-visible request remains a formal business task containing task-local entities, years, sources, variables, grids, random settings, thresholds, precision, standard method names, and requested evidence.

This placement makes transfer learnable from a completed training example without putting formulas, pseudocode, bit operations, solver updates, fold-allocation recipes, or generic tie/aggregation tutorials in solver-visible input. The template does not name or describe the registry. The evaluator ignores it completely: omission or mutation has no score effect, SP001 remains release/cohort work, and the task still has exactly eight business-aligned points.

The solver-visible answer template also avoids disclosing cohort results through fixed array dimensions. State-indexed delete-one, bootstrap, PCA, and cluster arrays now use relational cardinality rules tied to the submitted `state_order` and `state_n`; the broad-cohort order is tied to the submitted `broad_state_n`. Consequently, the balanced-state and broad-state counts must be discovered from the Web evidence. Numeric lengths remain only where the request itself fixes them, including years, divisions, features, lambda grid points, random-check rows, bootstrap batches, quantiles, clusters, and year subsets.

### Business question and third difficulty rework

This task remains in `SCN_023_public_health_statistical_modeling_audit`. The Public Health Observatory board must decide whether state adult obesity is a transportable longevity signal over 2020-2024. The outcome is life expectancy, the exposure is adult obesity, the reference year is 2023, the universe is the 50 states plus the District of Columbia, and solver data access remains limited to the read-only public Web portal.

The third rework preserves those training-specific entities but replaces the former conventional cross-section, regional interaction, permutation, blocked OLS, and sparse county-rollup audits with six independently demanding algorithms. Almost all credit depends on ordered high-dimensional intermediate results. The complete reusable convention set is available only from the solved answer snapshot; the formal input states the local business specification without teaching the implementation.

The paired test task was used only as a transferable algorithm-family pattern. This training task independently resolves life-expectancy/adult-obesity releases, uses a different reference year and feature semantics, obtains its own cohorts and state arrays, uses an independent PCG32 seed and stream, and reaches a different controlled classification. No test gold numbers, test entity lists, test random checkpoints, test seed, or test conclusion appear in the solver-visible training artifacts.

### Release resolution and cohorts

Eight age-adjusted direct-survey state-health measures are resolved for 51 jurisdictions and five years under the declared final-release rules. This yields `2040` selected jurisdiction-year-measure observations before complete-case filtering. The final socioeconomic release contributes `255` selected jurisdiction-year records. Suppressed, invalid-quality, and blank values remain unavailable and are never zero-filled.

The five-variable core series consists of life expectancy, age-adjusted direct-survey adult obesity, poverty, bachelor's attainment, and median income. Its yearly complete-case counts in 2020-2024 order are `[44, 45, 47, 46, 47]`. Exact five-year balance leaves 27 states and 135 observations. The 2023 broad cohort requires life expectancy and all 13 ordered health and socioeconomic features; it contains 34 states spanning all nine Census divisions. The source-perturbation cohort additionally requires crude direct-survey adult obesity in every year and contains 24 states and 120 observations.

The parallel series is deliberately the independently resolved crude direct-survey adult-obesity publication. The county-rollup series is too sparse to produce any nonempty five-year strict cohort, so it cannot support the required exhaustive fixed-effects subset audit. Using the crude direct-survey series preserves the adult-obesity business entity while making every requested three-, four-, and five-year perturbation mathematically defined.

### Six specialized modules

1. **Delete-cluster fixed effects.** The 27-state panel is sorted by state code and year. Life expectancy and all four predictors are double demeaned, then fit without an intercept. The full obesity coefficient is `-0.1062`. Every state is deleted in ascending code order; all state means, year means, and grand means are recomputed before refitting. The 27 requested coefficients range from `-0.1334` after deleting Pennsylvania to `-0.0864` after deleting Oklahoma. Their mean is `-0.1062`, the delete-cluster jackknife standard error is `0.0555`, the t statistic is `-1.9157`, the two-sided 26-df p value is `0.0665`, and the bias-corrected coefficient is `-0.1063`.

2. **Nested division-blocked ridge.** The 2023 broad cohort uses 13 ordered features: seven health measures beginning with adult obesity and six socioeconomic variables. Each of nine outer folds holds out one division. Within every outer training set, each of five lambdas is assessed by leaving out every remaining division in ascending order. Every fit recomputes training-only sample means and `ddof=1` standard deviations and runs cyclic coordinate descent to the declared `1e-12` tolerance. The gold answer contains the complete `9 x 5` inner RMSE matrix, all fold sizes, all selected lambdas, and all outer RMSE values. Lambda `0.1` wins eight outer folds and lambda `1.0` wins West South Central. The pooled outer predictions have RMSE `0.5911`, MAE `0.5013`, and Q-squared `0.9290`; West South Central is the worst outer division.

3. **PCG32/Webb wild-cluster bootstrap-t.** The restricted fixed-effects residuals are multiplied by one Webb six-point weight per state for each of 1,999 replicates. The training-specific random configuration is seed `14022023` and stream `17`. The answer reports the first three complete 27-state weight-index rows and all 20 batch exceedance counts, so PRNG initialization, stream continuity, draw order, and batching mistakes are locally visible. Every synthetic sample refits the full model and recomputes the CR1 standard error. The observed CR1 t statistic is `-2.0601`; 114 bootstrap statistics are at least as extreme, giving plus-one p value `0.0575`. Bootstrap coefficients have mean `-0.0004` and sample SD `0.0567`; the requested t quantiles are `[-2.1038, -1.3491, -0.0328, 1.4033, 2.0836]`.

4. **Grouped split conformal.** Every division becomes a test group. Among the remaining divisions, the largest group, with ascending-name tie breaking, is calibration; all other divisions are proper training. A lambda-one ridge is fit from scratch using only proper-training standardization. The finite-sample `alpha=0.20` rank of calibration absolute residuals defines an inclusive interval. The answer includes all calibration divisions, proper-training/calibration/test sizes, thresholds, fold coverages, widths, and MAEs. Row-weighted aggregate coverage is `0.9706` and mean width is `2.6914` life-expectancy years.

5. **Trajectory Jacobi PCA and clustering.** The 27 balanced states form a ten-column matrix: five annual life-expectancy values followed by five annual age-adjusted adult-obesity values. After sample-SD standardization, the fully specified symmetric Jacobi eigensolver produces deterministic components. The first two eigenvalues are `9.1947` and `0.3173`, with explained ratios `0.9195` and `0.0317` and cumulative ratio `0.9512`. Deterministic farthest-first three-means initializes at Alaska, Oklahoma, and Washington; canonical clusters have sizes 11, 10, and 6. The answer includes both loading vectors, both 27-state score vectors, all centroids, sizes, and aligned labels. Five complete leave-year-out refits yield adjusted Rand indices `[1.0000, 0.3747, 0.7703, 0.9041, 0.8707]` and aligned agreements `[1.0000, 0.7407, 0.9259, 0.9630, 0.9630]`.

6. **Exhaustive source/year fixed-effects perturbation.** The strict 24-state cohort is unchanged across every fit. Year subsets are ordered by size three, then four, then five, and lexicographically within size, producing 16 subsets. For each subset the four-predictor double-demeaned model is fit once with age-adjusted obesity and once with crude obesity, and both CR1 p values are recomputed. The answer therefore carries two 16-coefficient vectors, two 16-p-value vectors, and 16 absolute percentage shifts. Ten subsets retain the same sign, a fraction of `0.6250`. The median shift is `97.8868%`; the maximum is `962.0522%` for `2020-2021-2024`.

### Gates and controlled decision

The gate thresholds are intentionally publication-grade rather than calibrated to make the focal exposure pass:

- Delete-cluster FE fails because jackknife p `0.0665` exceeds `0.05`, although the coefficient is negative.
- Nested ridge passes because Q-squared `0.9290` is at least `0.85` and RMSE `0.5911` is at most `0.75`.
- Wild-cluster bootstrap fails because p `0.0575` exceeds `0.05`.
- Grouped split conformal passes because coverage exceeds `0.80` and mean width is below `3.25`.
- Trajectory stability fails because the minimum leave-year-out ARI is below `0.75`, despite cumulative two-component variance above `0.90`.
- Source-year stability fails because same-sign fraction is below `0.75` and median shift is above `50%`.

Only two of six gates pass. The all-six primary rule and at-least-four limited-transportability rule both fail, so the controlled result is `NO_TRANSPORTABLE_LONGEVITY_SIGNAL`. This does not deny a cross-sectional association; it says the evidence does not meet the declared transportability publication standard.

### Evaluator, probes, and size controls

The evaluator has exactly eight scoring points and raw weights `[1, 3, 3, 3, 3, 3, 3, 2]`, totaling 21:

- `SP001` (1): releases and core, balanced, broad cohorts;
- `SP002` (3): delete-one-state fixed-effects jackknife;
- `SP003` (3): nested 13-feature division-blocked ridge;
- `SP004` (3): PCG32/Webb wild-cluster bootstrap-t;
- `SP005` (3): grouped split-conformal folds and aggregates;
- `SP006` (3): Jacobi PCA, three-means, and leave-year-out stability;
- `SP007` (3): all 16 dual-series year-subset fixed-effects refits;
- `SP008` (2): six gates and controlled classification.

Every high-weight point is decomposed into cohort/order, intermediate vector or matrix, and summary checks. Exact-length arrays receive position-wise partial credit. State exclusion sets use normalized F1 after trimming, uppercasing, and duplicate removal. Four-decimal numbers use half-unit last-place tolerance. Missing fields affect only their own subchecks.

The gold answer scores exactly `1.0`; omitting or arbitrarily mutating `protocol_registry_record` also scores `1.0`. A publication-cohort mutation reduces only SP001, and the controlled-classification mutation reduces only SP008. A malformed JSON document, a missing prediction file, no invocation argument, and extra invocation arguments return a structured eight-point score of `0.0`. After the final method-only boundary reduction, the self-contained gold is `24,631` bytes; removing only `protocol_registry_record` yields a byte-equivalent projection of the prior analytical gold. The temporary construction program and all task-local probe artifacts were removed after validation.

The training task can transfer reusable routines for release resolution, small-matrix algebra, double demeaning, cluster covariance, ridge coordinate descent, PCG32, conformal ranks, Jacobi eigendecomposition, k-means label canonicalization, adjusted Rand index, and aligned-array validation. It cannot transfer the paired test task's entities, states, numerical values, random configuration, or controlled result.

## 中文构建记录

### 已解答标准答案中的 V1 迁移注册记录

协议 `PHO_STATE_TRANSPORT_AUDIT_V1` 及协议族 `PHO_STATE_ALGORITHMIC_TRANSPORT_FAMILY_V1` 的版本化注册记录，仅作为已解答标准答案中的可选顶层 `protocol_registry_record` 元数据出现。注册对象只有 `portable_protocol_profile` 一个子项，因此只携带可复用方法语义，不含请求快照或实例绑定。求解者可见请求仍是正式业务任务，保留本题实体、年份、来源、变量、网格、随机设置、门槛、精度、标准方法名称和所需证据。

这种位置使迁移知识可以从已解答训练示例中学习，又不会在求解前暴露公式、伪代码、位运算、求解器更新、折分配步骤或通用并列/汇总教程。模板不命名也不描述注册对象。评测器完全忽略注册对象：省略或篡改都不影响得分，SP001 仍只负责发布与队列，任务仍恰有八个业务评分点。

求解者可见答案模板也不再通过固定数组维度泄露队列结果。删一州、bootstrap、PCA 与聚类的州级数组改用关联基数规则，与作答中的 `state_order` 和 `state_n` 对齐；宽队列州序则与作答中的 `broad_state_n` 对齐。因此，平衡州数与宽队列州数必须由 Web 证据计算得到。只有年份、division、特征、lambda 网格、随机检查行、bootstrap 批次、分位点、聚类数和年份子集等由请求本身明确规定的尺寸继续使用数值长度。

### 业务问题与第三次难度返工

本任务仍属于 `SCN_023_public_health_statistical_modeling_audit`。公共卫生观测站需要判断，州级成人肥胖是否是 2020—2024 年寿命结果的可迁移信号。结果变量为预期寿命，暴露变量为成人肥胖，参考年为 2023 年，范围为 50 州加哥伦比亚特区；求解者只能使用只读公共 Web 门户。

第三次返工保留训练任务独有的预期寿命、成人肥胖和 2023 年实体，但用六种相互独立的专门算法替换原有的常规横截面、区域交互、置换、留组 OLS 与稀疏县级汇总审计。绝大多数分值依赖高维、有序的中间审计数组。完整可复用约定只由已解答答案快照提供；正式输入陈述本地业务规格，但不教学实现过程。

配对测试任务只提供算法族的可迁移模式。本训练任务独立解析发布、建立自己的队列与州数组，使用独立 PCG32 种子和流，并得到不同的受控结论。求解者可见训练产物中没有复制测试 gold 数字、测试实体列表、随机检查点、种子或结论。

### 队列与六个困难模块

八个州级健康指标按最终发布规则解析后共有 `2040` 条辖区—年份—指标记录，社会经济记录共有 `255` 条。核心五变量逐年完整数为 `[44,45,47,46,47]`；五年严格平衡后剩 27 州、135 条观测。2023 年 13 特征宽队列有 34 州。来源扰动还要求粗率直接调查肥胖在五年均可用，最终严格队列有 24 州、120 条观测。

县级汇总肥胖序列没有任何非空五年严格州队列，因此无法完成要求的 16 个固定效应子集重算。平行序列改为独立解析的粗率直接调查成人肥胖；它保留相同业务实体，同时使所有三年、四年、五年子集均有严格且不变的队列。

六个高权重模块为：

1. 在 27 州平衡面板上双向去均值，并按州代码完成 27 次删一州、重新去均值、重新拟合的固定效应 jackknife；完整系数 `-0.1062`，jackknife 标准误 `0.0555`、p 值 `0.0665`。
2. 在 34 州、13 个有序特征上完成九个外层 division 留出、五个 lambda 和所有内层 division 留出的嵌套 ridge；汇总 RMSE `0.5911`、MAE `0.5013`、Q 方 `0.9290`。
3. 使用训练任务专属 seed `14022023`、stream `17`、PCG32 状态机、Webb 六点权重和 1,999 次 CR1 学生化 wild bootstrap；超越数 114，加一 p 值 `0.0575`。
4. 逐 division 分离 proper-training、calibration 与 test，使用 lambda-one ridge 建立有限样本 split-conformal 区间；行加权覆盖率 `0.9706`、平均宽度 `2.6914`。
5. 对十列五年寿命—肥胖轨迹完成 Jacobi PCA、确定性三均值和五次留一年稳定性重算；前两成分累计解释率 `0.9512`，留年 ARI 为 `[1.0000,0.3747,0.7703,0.9041,0.8707]`。
6. 在不变的 24 州队列上遍历全部 16 个年份子集，分别以年龄调整肥胖与粗率肥胖拟合，共得到 32 套固定效应结果；同号比例 `0.6250`，变化中位数 `97.8868%`，最大值 `962.0522%`。

标准答案包含完整删州系数向量、`9 x 5` 内层 RMSE、九个外层 RMSE、前三个 27 州随机权重索引、20 个 bootstrap 批次超越数、九折 conformal 全部诊断、两套 27 州 PCA 得分、聚类标签、五个留年稳定性结果，以及 16 个子集的双来源系数、p 值和变化。因此，不完整但正确的实现可以获得细粒度部分分。

### 门槛、结论与验证

删州 FE 因 p 值高于 `0.05` 而失败；嵌套 ridge 通过；wild bootstrap 因 p 值 `0.0575` 高于 `0.05` 而失败；grouped conformal 通过；轨迹稳定性因最小 ARI 低于 `0.75` 而失败；来源—年份稳定性因同号比例低于 `0.75` 且变化中位数高于 `50%` 而失败。六门中只有两门通过，最终受控结论为 `NO_TRANSPORTABLE_LONGEVITY_SIGNAL`。该结论并非否认横截面相关，而是表示证据未达到预先声明的可迁移发表标准。

评分器恰好有八点，原始权重为 `[1,3,3,3,3,3,3,2]`，总权重 21。`SP001` 只负责发布与队列；`SP002`—`SP007` 分别对应六个困难模块；`SP008` 负责六道门和最终分类。注册元数据不参与评分。长向量与矩阵均按位置给部分分，州集合用规范化 F1，四位小数采用末位半单位容差，缺失字段只影响对应子检查。

Gold 得分严格为 `1.0`；省略或任意篡改 `protocol_registry_record` 也得 `1.0`。发布队列变异只降低 SP001，受控分类变异只降低 SP008；非法 JSON、缺失预测、无参数和多余参数返回结构化八点评分且总分为 `0.0`。最终方法边界收敛后，自包含标准答案为 `24,631` 字节；仅移除注册对象得到的分析投影与旧金标逐字节等价。验证完成后已删除临时构造程序和任务目录内的全部探针文件。

- 原作者：独立任务构建代理 `/root/build_train_001`。
- 第二次难度返工：专用任务代理 `/root/hard2_train_001`。
- 第三次难度返工：专用任务代理 `/root/hard3_train_001`。
- 第三次返工日期：2026-07-15。
- 修改范围：仅 `train_tasks/001` 的标准提示、正式 payload、标准答案、评分器和双语说明；未编辑环境、YAML、scratch、测试任务或其他训练任务。

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source example `E001`: abstracts long-form public-health release reconciliation, exact cohort filtering, missingness handling, and regression audit evidence.
- Source example `E002`: abstracts competing-source and cross-level reconciliation, revision precedence, identifier alignment, and anomaly handling.
- Source example `E003`: abstracts multivariable modeling, dimension reduction, deterministic clustering, sensitivity analysis, and a controlled operational conclusion.
- Author: `/root/build_train_001`.
- Created: 2026-07-15.
- Updated: 2026-07-16.
- Major changes: initial Web-evidence task construction; two high-difficulty algorithmic reworks; formal state-transport protocol registration; reduction to optional, unscored method-only solved-answer metadata; solver-visible SOP and registry-name redaction; replacement of result-derived fixed array lengths with relational cardinality rules.

## 谱系与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源示例 `E001`：抽象长表公共卫生发布对账、精确队列筛选、缺失处理和回归审计证据。
- 来源示例 `E002`：抽象竞争来源与跨层级对账、修订优先级、标识符匹配和异常处理。
- 来源示例 `E003`：抽象多变量建模、降维、确定性聚类、敏感性分析和受控业务结论。
- 作者：`/root/build_train_001`。
- 创建日期：2026-07-15。
- 更新日期：2026-07-16。
- 主要变更：初始 Web 证据任务构建；两轮高难度算法改造；正式州级迁移协议注册；将注册记录收敛为可选、不评分且只含方法的已解答答案元数据；整改求解侧 SOP 与注册名称泄露；将结果推导的固定数组长度替换为关联基数规则。

## Portable protocol profile rework

Formal calibration round 2 produced valid runs but only `+0.052760` overall gain because two of three generated skills generalized away exact protocol identities. The optional, unscored solved-answer registry now consists solely of a concise `portable_protocol_profile`: exact ID/version/family, exact-ID activation, deterministic override resolution, an instance-value exclusion boundary, and executable reusable definitions for every registered module. It contains no scenario entity, calendar, geography, seed, grid value, business threshold, cohort, result, flag, or conclusion. The final independent-review rework also removed the registry name from the solver-visible template; analytical answer fields, evaluator, tests, and Web evidence remain unchanged.

## 便携协议档案返工

第二轮正式校准运行均有效，但总增益只有 `+0.052760`，原因是三份生成技能中有两份把精确协议身份泛化掉。可选且不评分的已解答答案注册记录现仅含简洁 `portable_protocol_profile`：精确 ID/版本/协议族、精确 ID 激活、确定性覆盖解析、实例值排除边界，以及每个注册模块的可执行复用定义。档案不含场景实体、年份、地域、种子、网格值、业务阈值、队列、结果、标志或结论。最终独立复核整改还从求解者可见模板删除了注册名称；分析答案字段、评分器、测试题与 Web 证据保持不变。
