# train_002 Notes - International Equity Correlation Review

## English

Data lineage: This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk`, source examples `E001`, `E002`, and `E003`, with the closest source anchor being `E002` international equity correlation review. The shared generated environment is `task_group/task_group_010_institutional_portfolio_risk/env/`; this task uses `env/data/portfolios.json`, `env/data/policies.json`, `env/data/indices.json`, and `env/data/index_levels.json`. The task-local solver payload is `input/payloads/review_request.json`.

Task definition: The solver prepares a compact CIO JSON review for `PF-INT-NEXVEN`, using current Asteria environment data and the requested nine-index universe. The expected output reports the level window, index set, strongest and weakest Pearson correlation pairs, a China/Asia dependence classification, diversification candidates, and two sleeve actions. Solver-visible files define the output shape but do not expose the answer values or scoring weights.

Scenario fit and material map: This is the train-set instance of the international equity correlation family. The portfolio record shows NexVen's EM, Asia ex Japan, China, India, Latin America, EAFE, and World sleeves. The policy data supplies the high and low correlation thresholds. The index metadata confirms the monthly USD index series, and the index levels provide the current source for monthly simple-return calculations.

Solution basis: For the nine requested indices, monthly simple returns were computed from consecutive levels from `2025-05-30` through `2026-04-30`, producing 11 return observations per index. Pearson correlations were calculated for every alphabetical pair and rounded to three decimals. The highest positive pair is `IDX_EM` / `IDX_WORLD` at `0.974`. The lowest pair is `IDX_CHINA` / `IDX_LATAM` at `-0.825`. The portfolio has material EM, Asia ex Japan, and China sleeves, while China is highly correlated with EM and Asia-related beta; this supports `CHINA_ASIA_DEPENDENCE`. `IDX_LATAM` is the strongest low-correlation diversifier, and `IDX_EM_EX_CHINA` is included as a candidate to reduce direct China dependence inside EM exposure. The two recommended sleeve actions are to trim China and add Latin America.

Evaluation basis: The evaluator has six exact-match scoring points. `SP001` checks the review window and index set, raw weight 1. `SP002` checks the highest positive pair and rounded correlation, raw weight 3. `SP003` checks the lowest pair and rounded correlation, raw weight 3. `SP004` checks the concentration flag object, raw weight 2. `SP005` checks the diversification candidate set, raw weight 2. `SP006` checks the two sleeve action objects, raw weight 2. Numeric values are rounded to three decimals before comparison. Likely model pitfalls include using level correlations instead of return correlations, omitting `IDX_ACWI_IMI` or `IDX_EM_EX_CHINA`, using stale or incomplete local information instead of current environment levels, and reversing pair id order.

Transfer design: As a train task, this exposes several transferable conventions through answer comparison: use current shared environment data, calculate correlations from monthly simple returns derived from consecutive index levels, round correlations to three decimals, keep pair ids alphabetized, and turn correlation concentration into controlled action enums rather than prose. These conventions are intended to transfer to later correlation and composite risk tasks without making this task a tutorial.

Construction record: Created by task-builder 2 on 2026-06-03. Initial files added for `train_002`: prompt, request payload, answer template, standard answer, evaluator, shell wrapper, and bilingual notes.

## 中文

数据来源：本任务属于 `SCN_010_institutional_investment_strategy_portfolio_risk`，来源示例为 `E001`、`E002`、`E003`，其中最直接的业务锚点是 `E002` 的国际股票相关性复核。共享生成环境位于 `task_group/task_group_010_institutional_portfolio_risk/env/`；本任务使用 `env/data/portfolios.json`、`env/data/policies.json`、`env/data/indices.json` 和 `env/data/index_levels.json`。任务本地的可见材料是 `input/payloads/review_request.json`。

任务定义：求解者需要为 `PF-INT-NEXVEN` 准备一份紧凑的 CIO JSON 复核结果，使用当前 Asteria 环境数据和指定的九个指数。标准输出包括指数水平区间、指数集合、最高正相关和最低相关的 Pearson 相关性组合、中国/亚洲依赖分类、分散化候选项以及两个组合袖套操作。求解者可见文件只定义输出格式，不暴露答案值或评分权重。

场景匹配与材料地图：这是训练集中“国际股票相关性”操作族的样本。组合记录显示 NexVen 持有新兴市场、亚洲不含日本、中国、印度、拉丁美洲、EAFE 和全球参考袖套。政策数据给出高相关和低相关阈值。指数元数据确认月度美元指数序列，指数水平数据提供当前的月度简单收益计算来源。

解题依据：对九个指定指数，从 `2025-05-30` 到 `2026-04-30` 的连续指数水平计算月度简单收益，每个指数得到 11 个收益观测值。随后对所有按字母排序的指数对计算 Pearson 相关性，并四舍五入到三位小数。最高正相关组合是 `IDX_EM` / `IDX_WORLD`，相关性为 `0.974`。最低相关组合是 `IDX_CHINA` / `IDX_LATAM`，相关性为 `-0.825`。组合在新兴市场、亚洲不含日本和中国上有较大敞口，且中国与新兴市场和亚洲相关 beta 相关性较高，因此支持 `CHINA_ASIA_DEPENDENCE`。`IDX_LATAM` 是最明显的低相关分散化候选项，`IDX_EM_EX_CHINA` 可用于降低新兴市场敞口中的直接中国依赖。两个建议操作是降低中国袖套并增加拉丁美洲袖套。

评估依据：评估器包含六个精确匹配评分点。`SP001` 检查复核区间和指数集合，原始权重 1。`SP002` 检查最高正相关组合及三位小数相关性，原始权重 3。`SP003` 检查最低相关组合及三位小数相关性，原始权重 3。`SP004` 检查集中度标记对象，原始权重 2。`SP005` 检查分散化候选集合，原始权重 2。`SP006` 检查两个袖套操作对象，原始权重 2。数值比较前会保留三位小数。常见错误包括用指数水平而不是收益计算相关性、遗漏 `IDX_ACWI_IMI` 或 `IDX_EM_EX_CHINA`、使用过期或不完整的本地信息而不是当前环境指数水平，以及没有按字母顺序写指数对。

迁移设计：作为训练任务，本任务通过答案对比暴露可迁移约定：使用当前共享环境数据；从连续月度指数水平计算简单收益再做相关性；相关性保留三位小数；指数对按字母顺序排列；将相关性集中风险转换为受控枚举操作而不是自由文本。这些约定应迁移到后续相关性和组合型风险任务，但本任务本身不作为教程或示范题。

构建记录：由 task-builder 2 于 2026-06-03 创建。首次添加 `train_002` 的 prompt、请求 payload、答案模板、标准答案、评估器、shell 包装脚本和双语 notes。
