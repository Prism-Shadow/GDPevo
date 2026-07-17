# Notes for train_004

## English

Data/source lineage: This task is derived from scenario SCN_008_personal_financial_advisory_tax_estate_planning using source examples E001, E002, and E003. The task uses the shared generated advisory environment under env/ and the task-local payloads input/payloads/answer_template.json and input/payloads/request_memo.md. The target client is CLT-1004.

Task definition: The solver must use the shared advisory API and local request memo to produce the required JSON planning output for "Chen estate liquidity action plan". The visible prompt intentionally states the business goal and output contract without giving the solution workflow. The expected work includes resolving conflicting client facts, selecting the relevant account, policy, or trust records, applying the advisory tax constants, and producing controlled-choice recommendations plus exact dollar or date results.

Scenario fit: The task belongs to the personal financial advisory tax and estate planning scenario because it converts tax, retirement, trust, insurance, and estate-planning rules into a client-specific advisor work product. It preserves the source examples' emphasis on suitability framing, tax-aware calculations, estate-transfer implications, and clear professional recommendations.

Material map: The public API exposes /api/clients, /api/source-documents, /api/retirement-accounts, /api/life-insurance, /api/trust-candidates, /api/policies/tax, and /api/rmd-factors. The request memo identifies the engagement and target client. The answer template defines the exact schema, enum choices, numeric precision, and list-ordering rules.

Solution and evaluation basis: The standard answer in output/answer.json is generated from the shared environment records using the generic advisory calculation rules retained in env/advisory_rules.py. The evaluator exact-matches the following scoring goals:

- SP001 (2): Correct client, analysis type, primary action, and sequencing.
- SP002 (3): Correct estate taxable amount and estate-tax exposure.
- SP003 (2): Correct liquidity gap before planning.
- SP004 (3): Correct ILIT annual exclusion capacity and premium gap.
- SP005 (3): Correct ILIT estate-inclusion risk and outside-estate projection.
- SP006 (2): Correct trust strategy and projected heir remainder.
- SP007 (2): Correct estimated estate-tax reduction and charitable remainder context.
- SP008 (2): Correct sorted action set and source-resolution fields.

Likely model pitfalls include using stale CRM facts over signed profile facts, ignoring custodian account records, treating an ILIT as owned by the grantor, paying premiums before the withdrawal window closes, using the wrong RMD start year or factor, confusing GRAT and CRAT remainder beneficiaries, and returning prose instead of the requested JSON.

Transfer design: This is a formal train task. Solving it and comparing to the answer can reveal source precedence, the relevant calculation convention, and the controlled output style for later tasks.

Construction record: Author: Codex. Created: 2026-06-01. Updated: 2026-06-01. Major changes: Constructed as part of the SCN_008 train-predict task group with shared generated data and exact-match evaluators.

## 中文

数据来源：本任务来自场景 SCN_008_personal_financial_advisory_tax_estate_planning，参考源例子 E001、E002 和 E003。任务使用 env/ 下共享生成的顾问业务环境，以及本任务本地的 input/payloads/answer_template.json 和 input/payloads/request_memo.md。目标客户为 CLT-1004。

任务定义：求解者需要使用共享顾问 API 和本地请求备忘录，为“Chen estate liquidity action plan”输出指定 JSON。可见 prompt 只说明业务目标和输出契约，不给出完整解题步骤。预期工作包括处理相互冲突的客户资料，选择相关账户、保单或信托记录，应用税务常数，并输出受控推荐、精确金额或日期结果。

场景匹配：本任务属于个人财务顾问税务与遗产规划场景，因为它把退休账户、保险信托、GRAT/CRAT、遗产税和传承目标转化为客户定制的顾问工作成果。它保留了源例子中的适配性判断、税务计算、遗产传承影响和专业推荐。

材料地图：公开 API 包括 /api/clients、/api/source-documents、/api/retirement-accounts、/api/life-insurance、/api/trust-candidates、/api/policies/tax 和 /api/rmd-factors。请求备忘录说明业务背景和目标客户。答案模板规定 JSON schema、枚举选项、数值精度和列表排序规则。

解答与评估依据：标准答案 output/answer.json 基于共享环境记录，并通过 env/advisory_rules.py 中的通用顾问计算规则生成。评估器精确匹配以下得分点：

- SP001（权重 2）：Correct client, analysis type, primary action, and sequencing.
- SP002（权重 3）：Correct estate taxable amount and estate-tax exposure.
- SP003（权重 2）：Correct liquidity gap before planning.
- SP004（权重 3）：Correct ILIT annual exclusion capacity and premium gap.
- SP005（权重 3）：Correct ILIT estate-inclusion risk and outside-estate projection.
- SP006（权重 2）：Correct trust strategy and projected heir remainder.
- SP007（权重 2）：Correct estimated estate-tax reduction and charitable remainder context.
- SP008（权重 2）：Correct sorted action set and source-resolution fields.

常见失败包括优先使用过期 CRM 而非已签署客户档案、忽略托管方账户导出、把 ILIT 误认为 grantor 持有、在 withdrawal window 结束前支付保费、使用错误 RMD 起始年份或 factor、混淆 GRAT 和 CRAT 的 remainder beneficiary，以及输出说明文字而非 JSON。

迁移设计：这是正式训练任务，不是教程。通过盲做并对照答案，可以归纳资料优先级、计算口径和受控输出格式。

构造记录：作者 Codex。创建日期 2026-06-01。更新日期 2026-06-01。主要变更：作为 SCN_008 train-predict 任务组的一部分完成，使用共享生成数据和精确匹配评估器。
