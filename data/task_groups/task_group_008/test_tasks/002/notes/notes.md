# Notes for test_002

## English

Data/source lineage: This task is derived from scenario SCN_008_personal_financial_advisory_tax_estate_planning using source examples E001, E002, and E003. The task uses the shared generated advisory environment under env/ and the task-local payloads input/payloads/answer_template.json and input/payloads/request_memo.md. The target client is CLT-2002.

Task definition: The solver must use the shared advisory API and local request memo to produce the required JSON planning output for "Okafor ILIT transfer and annual exclusion review". The visible prompt intentionally states the business goal and output contract without giving the solution workflow. The expected work includes resolving conflicting client facts, selecting the relevant account, policy, or trust records, applying the advisory tax constants, and producing controlled-choice recommendations plus exact dollar or date results.

Scenario fit: The task belongs to the personal financial advisory tax and estate planning scenario because it converts tax, retirement, trust, insurance, and estate-planning rules into a client-specific advisor work product. It preserves the source examples' emphasis on suitability framing, tax-aware calculations, estate-transfer implications, and clear professional recommendations.

Material map: The public API exposes /api/clients, /api/source-documents, /api/retirement-accounts, /api/life-insurance, /api/trust-candidates, /api/policies/tax, and /api/rmd-factors. The request memo identifies the engagement and target client. The answer template defines the exact schema, enum choices, numeric precision, and list-ordering rules.

Solution and evaluation basis: The standard answer in output/answer.json is generated from the shared environment records using the generic advisory calculation rules retained in env/advisory_rules.py. The evaluator exact-matches the following scoring goals:

- SP001 (1): Correct client, analysis type, and implementation recommendation.
- SP002 (2): Correct annual exclusion per beneficiary and beneficiary count.
- SP003 (3): Correct annual exclusion capacity, premium, and premium gap.
- SP004 (1): Correct Crummey notice count and contribution date.
- SP005 (3): Correct notice due date, withdrawal end date, and earliest premium payment date.
- SP006 (1): Correct dedicated bank account requirement.
- SP007 (3): Correct death benefit, estate inclusion risk, and outside-estate projection.
- SP008 (2): Correct source-resolution fields for beneficiaries and policy evidence.

Likely model pitfalls include using stale CRM facts over signed profile facts, ignoring custodian account records, treating an ILIT as owned by the grantor, paying premiums before the withdrawal window closes, using the wrong RMD start year or factor, confusing GRAT and CRAT remainder beneficiaries, and returning prose instead of the requested JSON.

Transfer design: This is a test task anchored by train_002 and train_004. Transfer-dependent points include source precedence, calculation conventions, and the advisory recommendation frame while the client facts and dollar amounts change.

Construction record: Author: Codex. Created: 2026-06-01. Updated: 2026-06-01. Major changes: Constructed as part of the SCN_008 train-predict task group with shared generated data and exact-match evaluators.

## 中文

数据来源：本任务来自场景 SCN_008_personal_financial_advisory_tax_estate_planning，参考源例子 E001、E002 和 E003。任务使用 env/ 下共享生成的顾问业务环境，以及本任务本地的 input/payloads/answer_template.json 和 input/payloads/request_memo.md。目标客户为 CLT-2002。

任务定义：求解者需要使用共享顾问 API 和本地请求备忘录，为“Okafor ILIT transfer and annual exclusion review”输出指定 JSON。可见 prompt 只说明业务目标和输出契约，不给出完整解题步骤。预期工作包括处理相互冲突的客户资料，选择相关账户、保单或信托记录，应用税务常数，并输出受控推荐、精确金额或日期结果。

场景匹配：本任务属于个人财务顾问税务与遗产规划场景，因为它把退休账户、保险信托、GRAT/CRAT、遗产税和传承目标转化为客户定制的顾问工作成果。它保留了源例子中的适配性判断、税务计算、遗产传承影响和专业推荐。

材料地图：公开 API 包括 /api/clients、/api/source-documents、/api/retirement-accounts、/api/life-insurance、/api/trust-candidates、/api/policies/tax 和 /api/rmd-factors。请求备忘录说明业务背景和目标客户。答案模板规定 JSON schema、枚举选项、数值精度和列表排序规则。

解答与评估依据：标准答案 output/answer.json 基于共享环境记录，并通过 env/advisory_rules.py 中的通用顾问计算规则生成。评估器精确匹配以下得分点：

- SP001（权重 1）：Correct client, analysis type, and implementation recommendation.
- SP002（权重 2）：Correct annual exclusion per beneficiary and beneficiary count.
- SP003（权重 3）：Correct annual exclusion capacity, premium, and premium gap.
- SP004（权重 1）：Correct Crummey notice count and contribution date.
- SP005（权重 3）：Correct notice due date, withdrawal end date, and earliest premium payment date.
- SP006（权重 1）：Correct dedicated bank account requirement.
- SP007（权重 3）：Correct death benefit, estate inclusion risk, and outside-estate projection.
- SP008（权重 2）：Correct source-resolution fields for beneficiaries and policy evidence.

常见失败包括优先使用过期 CRM 而非已签署客户档案、忽略托管方账户导出、把 ILIT 误认为 grantor 持有、在 withdrawal window 结束前支付保费、使用错误 RMD 起始年份或 factor、混淆 GRAT 和 CRAT 的 remainder beneficiary，以及输出说明文字而非 JSON。

迁移设计：这是测试任务，迁移锚点为 train_002 and train_004。高价值得分点依赖从训练任务中归纳出的资料优先级、计算口径和顾问判断框架，但客户事实和金额已变化。

构造记录：作者 Codex。创建日期 2026-06-01。更新日期 2026-06-01。主要变更：作为 SCN_008 train-predict 任务组的一部分完成，使用共享生成数据和精确匹配评估器。
