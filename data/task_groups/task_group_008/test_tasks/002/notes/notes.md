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

