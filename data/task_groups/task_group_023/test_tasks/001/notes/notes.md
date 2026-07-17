# Construction and Review Notes

## Current whole-point evaluation boundary / 当前整点评分边界

The final rubric has eight binary points with raw weights `[1,3,3,3,3,3,3,2]`. Their complete goals are: resolved cohort summary; jackknife bias/extreme-deletion summary; pooled ridge prediction summary; bootstrap exceedance/inference; aggregate conformal coverage/width; leave-year trajectory stability; strict dual-source cohort; and controlled classification. Each point earns all of `weight/21` only when its declared required subcheck passes, otherwise zero. Other detailed comparisons are unscored diagnostics. This section supersedes historical partial-credit discussion below.

最终评分包含八个二元评分点，原始权重为 `[1,3,3,3,3,3,3,2]`。完整目标依次为：已解析队列摘要、jackknife 偏差与极端删除摘要、ridge 汇总预测结果、bootstrap 超越数与推断、conformal 汇总覆盖率与宽度、逐年删除轨迹稳定性、严格双来源队列、受控分类。只有声明的必需子检查通过时，该点才获得完整 `weight/21`，否则为零；其余详细比较只是不计分诊断。本节取代下文历史部分分讨论。

## English construction record

### Business question and third difficulty rework

This task remains in `SCN_023_public_health_statistical_modeling_audit`. The Public Health Observatory board must decide whether state food insecurity is a transportable signal for frequent mental distress over 2020-2024. The scope is the 50 states plus the District of Columbia, the reference year is 2024, and all source access remains through the read-only Web portal.

The GPT-5.5 `xhigh` round-3 diagnostic base rollout scored `1.0` on the second rework. The rollout was inspected in full. It downloaded the three portal tables, implemented a small reusable pure-Python linear-algebra layer, and then solved every former module in one script. Although that version contained fixed effects, a regional Wald test, a Freedman-Lane permutation, leave-one-division-out OLS, and a source audit, most work reduced to repeated four-predictor OLS calls after one release-resolution pass. The exact xorshift loop and ordinary matrix formulas were also directly recovered from the explicit contract. The result demonstrated that merely adding more OLS refits did not create independent algorithmic difficulty.

The third rework removed the easy primary cross-section point and gave almost all credit to six specialized reusable algorithms with high-dimensional audit outputs. Its contract still declared implementation-level conventions, which became the subject of the next diagnostic.

### Fourth rework: procedural-leakage removal

The GPT-5.5 `xhigh` round-4 smoke diagnostic scored `0.9762`. Inspection showed that the solver-facing contract supplied a transferable standard operating procedure: coordinate-update equations, a complete PRNG bit transition, detailed matrix rotations, and other answer-adjacent implementation instructions. This made the test almost self-solving even without the train-derived skill.

That rework changed only `prompt.txt`, `analysis_request.json`, and this bilingual note; the answer template already expressed only the output contract and therefore remained unchanged. The gold answer, evaluator, weights, rubric goals, task-specific release filters, years, measures, cohorts, feature ordering, seeds and stream, output fields, precision rules, and gate thresholds remained unchanged. The solver-facing contract named the standard delete-cluster FE jackknife, nested division-blocked ridge, PCG32/Webb wild-cluster bootstrap-t, grouped split conformal, Jacobi PCA/k-means stability, and source/year perturbation procedures, while removing formula-level pseudocode, iterative update equations, matrix-rotation recipes, and PRNG bit-update code.

The later protocol-dependency rework below completes this separation by moving the remaining shared defaults out of the test contract.

### Data resolution and cohorts

Eight state-health measures are resolved for 51 jurisdictions and five years with the declared final-release rules, producing `2040` selected health observations. The socioeconomic table contributes `255` selected jurisdiction-year records. The five-variable core complete-case counts are `[43, 45, 44, 46, 46]`. Requiring core completeness in all five years leaves 29 states and 145 observations; 22 states are excluded.

The 2024 broad-feature cohort requires the outcome and all 13 ordered health and socioeconomic features. It contains 35 states across all nine Census divisions. The strict dual-source five-year panel contains 28 states and 140 observations.

### Six independent hard modules

1. **Delete-cluster fixed effects.** The four variables are double demeaned on the 29-state balanced panel. The full exposure coefficient is `0.1373`. Every state is then deleted in ascending state-code order; double demeaning is recomputed and the model is refit. The 29 requested delete coefficients range from `0.1052` after deleting Nevada to `0.1935` after deleting New Jersey. The delete mean is `0.1370`, jackknife standard error `0.1044`, t statistic `1.3151`, two-sided t p value `0.1992`, and bias-corrected coefficient `0.1457`. Reporting the full ordered delete vector makes a partial implementation useful and independently auditable.

2. **Nested group-blocked ridge.** The broad cohort uses 13 ordered features. Each of nine outer folds holds out one division. For each of five lambdas, an inner leave-one-remaining-division-out loop recomputes training-only means and sample standard deviations, fits standard ridge with an unpenalized intercept, and pools validation residuals. The answer contains the complete `9 x 5` inner-RMSE matrix, fold sizes, nine chosen lambdas, and nine outer RMSEs. Lambda `0.1` wins every outer fold, but this is an output of 360 inner validation paths rather than a supplied answer. Pooled outer predictions yield RMSE `1.0653`, MAE `0.9173`, and Q-squared `0.5528`; South Atlantic is the worst outer division.

3. **Wild-cluster bootstrap-t.** The null-restricted fixed-effects residuals are multiplied by state-level Webb six-point weights over 1,999 replicates. The contract identifies the standard PCG32 variant and its seed and stream, the Webb index order, state draw order, CR1 studentization, batches, and nearest-rank quantiles without reproducing the generator's bit-update implementation. The first three complete 29-state weight-index rows and all 20 batch exceedance counts make PRNG or stream mistakes locally diagnosable. There are 365 exceedances; the plus-one p value is `0.1830`. The coefficient mean is `0.0025`, its sample SD is `0.0999`, and the five t quantiles are `[-2.0579, -1.3044, 0.0217, 1.4080, 2.1359]`.

4. **Grouped split conformal.** Each division is a test group. From the other divisions, the largest group with an ascending-name tie break is calibration; all remaining groups are proper training. A fixed lambda-one ridge is fit from scratch with training-only standardization. The finite-sample `alpha=0.20` absolute-residual quantile defines an inclusive interval. The answer reports all proper-training, calibration, and test sizes; nine calibration divisions; nine thresholds; nine coverages, widths, and MAEs. Row-weighted aggregate coverage is `0.8857` and mean width is `3.6246`.

5. **Trajectory PCA and clustering stability.** The 29 balanced states form a 10-column matrix of five outcome and five exposure trajectories. Columns are standardized; a fully specified symmetric Jacobi eigensolver supplies deterministic loadings and scores. The first two eigenvalues are `8.3350` and `0.7556`, explaining `0.8335` and `0.0756`, cumulatively `0.9091`. Deterministic farthest-first three-means starts from `AL`, `OK`, and `MI`; canonical clusters contain 4, 12, and 13 states. The answer provides both loading vectors, both 29-state score vectors, centroids, sizes, and all labels. Five complete leave-year-out PCA and clustering refits have adjusted Rand indices `[0.8018, 1.0000, 0.9217, 1.0000, 0.8018]` and aligned agreements `[0.9310, 1.0000, 0.9655, 1.0000, 0.9310]`.

6. **Exhaustive source-by-year perturbation.** On one strict 28-state dual-source cohort, the fixed-effects model is fit for every year subset of size three, four, or five, first with the health exposure and then with the socioeconomic exposure. This creates 32 model fits and requires two ordered coefficient vectors, two ordered CR1 p-value vectors, and 16 source-shift values. Only 8 of 16 subsets retain the same coefficient sign. The median absolute shift is `112.7078%`, the maximum is `314.4789%`, and the worst subset is `2020-2021-2022`.

### Gates and controlled decision

The delete-cluster gate passes because the coefficient is positive and the jackknife p value is at most `0.20`. The ridge gate passes (`Q² >= 0.50`, RMSE `<= 1.10`). The bootstrap gate passes (`p <= 0.20`). The conformal gate passes (coverage `>= 0.80`, width `<= 3.75`). The trajectory gate passes (minimum ARI `>= 0.80`, cumulative two-component ratio `>= 0.85`). The source-year gate fails because same-sign fraction is only `0.50` and maximum shift is above `150%`. Five gates pass, so the final classification is `ROBUST_SECONDARY_SIGNAL`, not the primary classification.

### Rubric and validation

The evaluator has exactly eight points and raw weights `[1, 3, 3, 3, 3, 3, 3, 2]`, total 21:

- `SP001` (1): resolve releases and establish yearly, balanced, and broad cohorts;
- `SP002` (3): delete-one-state fixed-effects jackknife and bias correction;
- `SP003` (3): nested division-blocked ridge and outer predictions;
- `SP004` (3): deterministic PCG32/Webb wild-cluster bootstrap-t;
- `SP005` (3): grouped split-conformal folds and aggregates;
- `SP006` (3): PCA, deterministic clustering, and leave-year-out stability;
- `SP007` (3): all 16 source/year perturbations;
- `SP008` (2): six gates and controlled classification.

Each hard point is decomposed into three or four semantic modules rather than many element-weighted fields. Exact-length aligned arrays are first compared positionally, then converted to declared integrity levels of `1.00`, `0.75`, `0.50`, `0.25`, or `0.00`. Within an ordered audit module, the formal order, checkpoint, or critical result is bound conjunctively to its supporting vectors: perfect evidence can earn at most 20% of that module when its critical key or summary is wrong. State sets still use normalized F1, and four-decimal numbers still use a half-unit last-place tolerance. A missing field affects its semantic module and any audit that necessarily depends on it. Malformed JSON, a non-object root, missing prediction files, and bad invocation produce a structured eight-point zero result.

### Fifth rework: semantic aggregation and anti-dilution validation

The round-5 preserved GPT-5.5 `xhigh` smoke prediction exposed two aggregation defects without changing the underlying business task. In `SP004`, the declared PCG32 stream, observed fit, and first three weight rows were correct, but 17 of 20 batch exceedance counts, total exceedances, bootstrap p value, and all five bootstrap-t quantiles were wrong. The former field-weighted evaluator still awarded `0.6100` for the point. In `SP007`, all numeric vectors were present, but `subset_order` and `worst_shift_subset` used arrays of years instead of the required ordered string identifiers; the vectors therefore lacked valid formal alignment keys, yet the point still earned `0.8667`.

The evaluator now aggregates each hard point through named business-semantic modules: panel/setup integrity, ordered fold/grid/checkpoint audits, critical inference summaries, and stability or invariance summaries. Long arrays are useful evidence, not a collection of independent tiny accomplishments. A critical summary and its audit evidence are coupled through explicit partial levels, so a wrong critical result cannot be hidden by many correct rows. This is not whole-point binary scoring: one wrong row retains useful partial credit, complete modules remain fully credited, and unrelated rubric points are unchanged.

After the change, the preserved smoke prediction scores `0.848452380952381` overall. `SP004` is `0.5475`: protocol/observed fit and random-stream checkpoints remain fully credited, while the incorrect replicate inference module earns `0.05` and the mixed distribution module earns `0.52`. `SP007` is `0.4250`: the strict cohort remains correct, but the invalid alignment key caps both ordered coefficient and ordered inference audits at `0.20`; the partially correct stability summary earns `0.725`. Gold remains exactly `1.0`. Focused mutations of one critical field or one ordered audit changed only the intended rubric point; empty input, malformed JSON, and a missing file all scored `0.0` with exactly eight points and the unchanged raw weights.

The gold answer evaluates to exactly `1.0`. Eight isolated mutations were run, one per point; in every run only the intended point fell below full credit. A malformed JSON probe and a missing-file probe both scored `0.0`. No temporary files remain in the task directory.

### Difficulty expectation

The one-weight release/cohort point is the only low-complexity credit. A solver that only resolves the portal and fits a conventional regression earns at most `1/21`. Useful partial implementations can earn intermediate credit from ordered fold, bootstrap-batch, PCA-score, or perturbation arrays, but full credit requires six distinct algorithm families: cluster jackknife inference, nested penalized optimization, seeded cluster resampling, finite-sample conformal calibration, eigendecomposition plus clustering stability, and exhaustive source/year sensitivity.

A paired training skill can legitimately transfer reusable routines for release resolution, pure-Python matrices, ridge coordinate descent, PCG32, conformal quantiles, Jacobi PCA, label alignment, and partial-credit output checks. It cannot carry test-specific state lists or numerical results. This structure is intended to move a capable no-skill GPT-5.5 `xhigh` base solver toward the `0.4-0.6` range while allowing a correct reusable skill to add roughly `0.1-0.2`: partial modules are rewarded, but the six algorithms are sufficiently independent that one generic OLS script no longer saturates the task.

### Sixth rework: registered-protocol transfer dependency

The solver-facing request now declares `protocol_id` `PHO_STATE_TRANSPORT_AUDIT_V1` and contains only task-specific overrides. The paired `train_tasks/001` example remains the full reusable six-module SOP: it demonstrates the two-way within/jackknife conventions; the ridge grid, division-blocked fold construction, training-only feature engineering, solver and convergence behavior; the PCG32/Webb generator, checkpoint schedule and bootstrap summaries; grouped conformal mechanics; Jacobi PCA and deterministic clustering; leave-year alignment; exhaustive subset construction; and standard ordered aggregation conventions. Those shared defaults are no longer duplicated in this test request.

The test still independently supplies everything that must not be inferred from the training answer: the mental-distress and food-insecurity entities, final-release filters, 2020-2024 and reference-year scope, core/broad/dual-source cohort variables, the 13 test feature semantics, the health-versus-socioeconomic source choice, test-only seed `23072026` and stream `54`, four-decimal reporting, all business gates, decision labels, and the unchanged output-field contract. Every state list, row count, fold result, random checkpoint, coefficient, p value, stability statistic, gate outcome, and classification must therefore be discovered or computed from this test's Web portal evidence.

This is the intended train-transfer fairness boundary. A base solver receives the protocol name but not the reusable SOP and must reconstruct the common procedures itself. A few-shot skill generated from `train_tasks/001` can infer and transfer that SOP, yet it receives no test-specific evidence or answer. The expected few-shot gain therefore measures procedural transfer rather than leaked test facts. This sixth rework changes only `test_tasks/001/input/prompt.txt`, `test_tasks/001/input/payloads/analysis_request.json`, and this note. The answer template and its key contract, gold answer, evaluator, goals, and weights are byte-for-byte unchanged.

### Seventh rework: result-cardinality leakage removal

The construction review found that the solver-visible answer template still hard-coded the data-derived balanced-cohort and broad-cohort sizes. Those constants also appeared indirectly as the widths or lengths of the delete-one, bootstrap, PCA-score, and cluster-label arrays. They disclosed cohort results that should instead be established from this test's Web evidence.

The template now uses relational cardinality rules. `delete_cluster_fixed_effects.state_order` must have the submitted `state_n` length and its coefficient vector must align to that order; `nested_ridge_division_cv.broad_state_order` must have the submitted `broad_state_n` length; bootstrap and trajectory state orders must match the delete-cluster order; and every bootstrap row, PCA score vector, and cluster-label vector must align positionally to that shared state order. No data-derived state count remains encoded as a numeric template dimension.

Numeric dimensions remain where they are fixed by the request or registered protocol rather than discovered from data: five analysis years, nine divisions, the declared feature spaces, five ridge-grid values, three random checkpoints and clusters, twenty bootstrap batches, five quantiles and leave-year refits, and sixteen year subsets. This rework changes only `answer_template.json` and this bilingual construction note. The request, gold answer, evaluator behavior, eight rubric points, goals, and weights are unchanged; the gold answer still satisfies every relation and evaluates to exactly `1.0`.

## 中文构建记录

### 业务问题与第三次难度返工

本任务仍属于 `SCN_023_public_health_statistical_modeling_audit`。公共卫生观测站需要判断，州级食物不安全是否能够作为 2020—2024 年频繁心理困扰的可迁移政策信号。范围是 50 州加哥伦比亚特区，参考年为 2024 年，全部数据只从只读 Web 门户获取。

第二次返工在第三轮 GPT-5.5 `xhigh` 基础诊断中仍得到了 `1.0`。完整轨迹显示，求解器一次下载三张门户表，写出一套纯 Python 小型线性代数代码，然后让固定效应、区域 Wald、Freedman-Lane 置换、division 留一验证和来源审计都复用同一种四变量 OLS。原版本虽然模块名称不同，但计算骨架高度重合。第三次返工因此删除容易的主横截面评分点，把几乎全部权重放到六种真正不同的可复用算法上，并要求有用的高维中间审计数组。

### 第四次返工：移除程序化泄漏

第四轮 GPT-5.5 `xhigh` 冒烟诊断得分为 `0.9762`。轨迹检查表明，解题侧契约仍给出了可直接照搬的 SOP，包括坐标更新方程、完整的随机数位更新、细粒度矩阵旋转步骤和其他接近答案的实现提示。因此，即使没有训练技能，测试也接近可直接复现。

该轮只修改了 `prompt.txt`、`analysis_request.json` 和本双语说明；答案模板原本仅描述输出契约，所以保持不变。标准答案、评分器、权重、评分目标，以及所有任务特定的发布筛选、年份、指标、队列、特征顺序、随机种子与流、输出字段、精度规则和门槛都没有变化。该轮契约以标准名称指定删簇固定效应 jackknife、division 分组嵌套 ridge、PCG32/Webb wild-cluster bootstrap-t、grouped split conformal、Jacobi PCA/k-means 稳定性和来源—年份扰动，同时删除了公式级伪代码、迭代更新式、矩阵旋转配方和 PRNG 位更新代码。

下述协议依赖返工进一步完成了这一分离，把测试契约中剩余的共享默认规则也移出了解题输入。

### 队列与六个困难模块

八个州级健康指标按最终发布规则解析后共有 `2040` 条所选观测，社会经济发布共有 `255` 条。五年核心完整数为 `[43,45,44,46,46]`；严格平衡后剩 29 州、145 条观测。2024 年 13 特征宽队列有 35 州，五年双来源严格队列有 28 州、140 条观测。

六个高权重模块分别为：

1. 在 29 州平衡面板上做双向去均值，并进行 29 次删一州重新去均值、重新拟合的固定效应 jackknife；
2. 在 13 个有序特征上完成九个外层 division 留出、五个 lambda、内层 division 留出的嵌套 ridge 与坐标下降；
3. 使用明确定义的 PCG32 状态机、Webb 六点权重和 1,999 次 CR1 学生化的 wild-cluster bootstrap-t；
4. 逐 division 建立 proper-training、calibration 与 test 三组分离的有限样本 split-conformal 区间；
5. 对十列五年轨迹完成 Jacobi PCA、确定性三均值聚类以及五次留一年稳定性重算；
6. 在同一个严格队列上遍历全部 16 个三年至五年子集，并分别用主来源与平行来源拟合，共得到 32 套固定效应结果。

标准答案包含每州删除系数、完整 `9 x 5` 内层 RMSE、九折外层 RMSE、前三个 29 州随机权重索引、20 个 bootstrap 批次超越数、九折 conformal 阈值与覆盖率、两套 29 州 PCA 得分、聚类标签、五个留年 ARI，以及 16 个子集的两来源系数、p 值和相对变化。这样，不完整实现可以获得合理部分分，同时每一类算法都能被独立核查。

### 门槛、评分与预期难度

删州固定效应、嵌套 ridge、wild bootstrap、grouped conformal 和轨迹稳定性五道门通过；来源—年份稳定门失败，因为同号比例只有 `0.5000`，最大来源变化达到 `314.4789%`。最终共有五门通过，受控结论为 `ROBUST_SECONDARY_SIGNAL`。

评分器恰好有八点，原始权重 `[1,3,3,3,3,3,3,2]`，总权重 21。`SP001` 只负责发布与队列；`SP002` 到 `SP007` 分别对应六个困难模块；`SP008` 负责六门和最终分类。每个困难点不再把大量元素直接线性相加，而是聚合为三到四个语义模块。长向量和矩阵先按正式顺序比较，再映射到 `1.00`、`0.75`、`0.50`、`0.25`、`0.00` 五档完整性；有序审计的关键顺序键、检查点或结果摘要错误时，即使证据数组完整，该语义模块也最多获得 20%。州集合仍使用规范化 F1，四位小数仍使用末位半单位容差。标准答案严格为 `1.0`；定向隔离扰动只降低目标评分点；非法 JSON、空输入与缺失文件均为 `0.0`。

### 第五次返工：语义聚合与防元素稀释

第五轮保留的 GPT-5.5 `xhigh` 冒烟答案暴露了两处聚合问题，但业务任务本身无需改变。`SP004` 的 PCG32 流、观测拟合和前三行权重索引正确，但 20 个批次中有 17 个超越数错误，总超越数、bootstrap p 值和全部五个 bootstrap-t 分位数也错误；旧评分器仍给该点 `0.6100`。`SP007` 的数值向量虽然正确，但 `subset_order` 与 `worst_shift_subset` 使用年份数组，而不是输出契约要求的有序字符串标识；这些向量因此缺少有效对齐键，旧评分仍达到 `0.8667`。

当前评分器把每个困难点组织为具名业务语义模块：面板或协议完整性、有序折叠/网格/检查点审计、关键推断摘要、稳定性或不变性摘要。长数组是审计证据，不再被视为许多互相独立的小成果。关键摘要与证据数组通过明确的部分分档位绑定，因此大量正确行不能掩盖关键结果错误。这并非整点二元评分：单行错误仍保留合理部分分，完整语义模块仍得满分，无关评分点不受影响。

返工后，保留冒烟答案的总分为 `0.848452380952381`。`SP004` 为 `0.5475`：协议/观测拟合与随机流检查点仍满分，但错误的重复推断模块仅得 `0.05`，混合正确与错误的分布摘要模块得 `0.52`。`SP007` 为 `0.4250`：严格队列仍正确，但无效对齐键把有序系数审计和有序推断审计都限制在 `0.20`，部分正确的稳定性摘要得 `0.725`。gold 仍严格为 `1.0`；关键字段与有序审计的定向突变只影响目标评分点；空输入、非法 JSON 与缺失文件均为 `0.0`，评分点仍恰好八个，原始权重不变。

基础模型即使完成门户解析和普通回归，也最多拿到 `1/21`。它需要分别实现多种算法才能继续得分，因此预期 GPT-5.5 `xhigh` 无技能基础均分会向 `0.4-0.6` 移动。配套训练技能可以提供发布解析、矩阵运算、ridge、PCG32、conformal、Jacobi PCA、标签对齐等通用代码，但不得包含本测试的州清单或数值答案；合理目标是带来约 `0.1-0.2` 的可迁移提升而不饱和。

### 第六次返工：注册协议的训练迁移依赖

当前解题侧请求声明 `protocol_id` 为 `PHO_STATE_TRANSPORT_AUDIT_V1`，并且只保留本题覆盖项。配对的 `train_tasks/001` 仍完整展示六模块可复用 SOP，包括双向组内变换与 jackknife、ridge 网格和 division 分组折、仅训练集特征工程、求解与收敛约定、PCG32/Webb 随机生成、默认检查点与 bootstrap 汇总、grouped conformal、Jacobi PCA 与确定性聚类、留年标签对齐、穷举年份子集，以及标准有序聚合规则。测试请求不再重复这些可由训练技能学习的默认规则。

测试仍独立给出所有不得从训练答案推断的内容：心理困扰与食物不安全实体、最终发布筛选、2020—2024 年与参考年范围、核心/宽特征/双来源队列变量、13 个测试特征语义、健康来源与社会经济来源的选择、本题专属 seed `23072026` 和 stream `54`、四位小数规则、全部业务门槛、决策标签，以及未改变的输出字段契约。州列表、记录数、各折结果、随机检查点、系数、p 值、稳定性统计、门槛结果和最终分类仍必须从本测试 Web 门户独立探索或计算。

这明确了训练迁移的公平边界：base 只看到协议名称，看不到可复用 SOP，必须自行重建共同流程；由 `train_tasks/001` 生成的 few-shot skill 可以推断并迁移该 SOP，但无法取得任何测试特定证据或答案。因此，few-shot 增益来自程序性迁移，而不是测试事实泄漏。本次只修改 `test_tasks/001/input/prompt.txt`、`test_tasks/001/input/payloads/analysis_request.json` 与本说明；答案模板及其键契约、gold、评分器、目标和权重均逐字节不变。

### 第七次返工：移除结果基数泄漏

构建复核发现，解题侧可见的答案模板仍把由数据决定的平衡队列州数和宽队列州数写成固定数字，并通过删州系数、bootstrap 权重行、PCA 得分与聚类标签的长度或宽度再次间接暴露这些结果。这些队列规模应当由求解者从本测试的 Web 证据中独立建立，而不是从输出模板读取。

当前模板改用关系型基数约束：`delete_cluster_fixed_effects.state_order` 的长度必须等于提交的 `state_n`，删州系数向量须与其逐位置对齐；`nested_ridge_division_cv.broad_state_order` 的长度必须等于提交的 `broad_state_n`；bootstrap 与轨迹模块的州顺序必须和删州模块完全一致；每行 bootstrap 权重、两套 PCA 得分以及聚类标签都必须按共同州顺序逐位置对齐。模板不再用数字维度编码任何由数据推导的州数。

由请求或注册协议直接固定、而非由数据发现的维度继续保留，包括五个分析年份、九个 division、已声明的特征空间、五个 ridge 网格值、三个随机检查点与三个聚类、二十个 bootstrap 批次、五个分位数与留年重算，以及十六个年份子集。本次返工只修改 `answer_template.json` 与本双语构建说明；请求、标准答案、评分器行为、八个评分点、目标和权重均未改变，gold 仍满足全部关系且严格评分为 `1.0`。

- 初始作者：独立任务构建代理 `/root/build_test_001`。
- 第一次难度返工：校准返工代理，后由 `/root/finish_test_001` 完成。
- 第二次难度返工：专用任务代理 `/root/hard2_test_001`。
- 第三次难度返工：专用任务代理 `/root/hard3_test_001`。
- 第四次程序化泄漏返工：专用任务代理 `/root/deproc_test_001`。
- 第五次语义聚合返工：专用评分代理 `/root/score_test_001`。
- 第六次协议依赖返工：专用协议代理 `/root/protocol_test_001`。
- 第七次结果基数防泄漏返工：专用任务返工代理 `/root/test001_template_rework`。
- 第三次返工日期：2026-07-15。
- 第四次返工日期：2026-07-15。
- 第六次返工日期：2026-07-15。
- 当前修改范围：第六次返工仅编辑 `test_tasks/001/input/prompt.txt`、`test_tasks/001/input/payloads/analysis_request.json` 与本双语说明；未编辑答案模板、标准答案、评分器、训练任务、环境、YAML、scratch 或其他任务。
- 当前第七次返工仅编辑 `test_tasks/001/input/payloads/answer_template.json` 与本双语说明；未编辑请求、标准答案、评分器或其他任务。

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source relevance: `E001` supplies the state-level release filtering, joins, regression diagnostics, and policy-claim audit lineage; `E002` supplies standardized multivariate trajectories, PCA, clustering, and cross-source anomaly auditing; `E003` supplies long-format health/socioeconomic reconciliation, identifier discipline, and source-sensitivity lineage. This task combines those drivers without copying a source answer.
- Task brief: independently audit whether state food insecurity is a transportable signal for frequent mental distress using six reproducible robustness modules and a controlled decision.
- Environment lineage: the shared seeded Public Health Observatory Web environment exposes state health and socioeconomic publications through business endpoints; solvers never receive the SQLite file, generator, seed manifest, environment source, or answer-like endpoint.
- Payload lineage: `analysis_request.json` contains held-out entities, scopes, thresholds, seed, and protocol overrides; `answer_template.json` contains only the typed response contract. Reusable protocol mechanics are learned from the paired solved training answer, while every held-out value must be retrieved or computed anew.
- Author: independent task-builder agent `/root/build_test_001`.
- Created: 2026-07-15.
- Updated: 2026-07-16.
- Major changes: difficulty expansion; procedural leakage removal; semantic-module evaluator hardening; registered-protocol transfer boundary; data-derived cardinality leakage removal; final lineage completion.

## 沿袭与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源关联：`E001` 提供州级发布筛选、连接、回归诊断与政策主张审计沿袭；`E002` 提供标准化多变量轨迹、PCA、聚类和跨来源异常审计；`E003` 提供长表健康/社会经济对账、标识符纪律和来源敏感性沿袭。本题组合这些难度驱动，但不复制来源答案。
- 任务简述：通过六个可复现稳健性模块和受控结论，独立审计州级食物不安全能否作为频繁心理困扰的可迁移信号。
- 环境沿袭：共享、固定种子的公共卫生观测站 Web 环境通过业务端点提供州级健康和社会经济发布；求解者看不到 SQLite 文件、生成程序、种子清单、环境源码或答案型端点。
- 载荷沿袭：`analysis_request.json` 仅承载留出实体、范围、门槛、种子和协议覆盖项；`answer_template.json` 仅承载带类型响应契约。可复用协议机制从配对训练标准答案中学习，所有留出值都必须重新检索或计算。
- 作者：独立任务构建代理 `/root/build_test_001`。
- 创建日期：2026-07-15。
- 更新日期：2026-07-16。
- 主要变更：扩展难度；移除程序化泄漏；强化语义模块评分；建立注册协议迁移边界；移除数据推导的基数泄漏；补齐最终沿袭记录。
