const v1LeaderboardRuns = [
  {
    model: "GPT-5.5",
    harness: "Codex",
    thinking: "xhigh",
    method: "skill-creator",
    modes: {
      base: { acc: 46.72, std: 5.13, lift: 0, rounds: 14.91, tokens: 735.3, cost: 1.137 },
      fewshot: { acc: 64.91, std: 6.36, lift: 18.19, rounds: 11.58, tokens: 451.7, cost: 0.805 },
      self: { acc: 54.99, std: 8.73, lift: 8.27, rounds: 9.71, tokens: 344.3, cost: 0.771 },
      "reflect-3": { acc: 57.45, std: 7.62, lift: 10.73, rounds: 10.83, tokens: 399.4, cost: 0.844 }
    }
  },
  {
    model: "Opus 4.8",
    harness: "Claude Code",
    thinking: "xhigh",
    method: "skill-creator",
    modes: {
      base: { acc: 49.11, std: 5.25, lift: 0, rounds: 14.62, tokens: 385.8, cost: 0.607 },
      fewshot: { acc: 70.9, std: 6.38, lift: 21.79, rounds: 11.1, tokens: 347.3, cost: 0.549 },
      self: { acc: 57.37, std: 6.79, lift: 8.26, rounds: 11.78, tokens: 433.9, cost: 0.61 },
      "reflect-3": { acc: 62.72, std: 6.68, lift: 13.62, rounds: 12.15, tokens: 433.4, cost: 0.605 }
    }
  },
  {
    model: "Opus 4.6",
    harness: "Panofy",
    thinking: "high",
    method: "agent-training",
    modes: {
      base: { acc: 50.4, std: 6.99, lift: 0, rounds: 15.16, tokens: 379.3, cost: 0.752 },
      fewshot: { acc: 71.47, std: 4.93, lift: 21.07, rounds: 13.48, tokens: 385.5, cost: 0.814 },
      self: { acc: 58.39, std: 5.74, lift: 7.99, rounds: 12.51, tokens: 341.8, cost: 0.707 },
      "reflect-3": { acc: 59.82, std: 7.31, lift: 9.41, rounds: 14.37, tokens: 394.8, cost: 0.767 }
    }
  },
  {
    model: "GLM-5.2",
    harness: "Claude Code",
    thinking: "max",
    method: "skill-creator",
    modes: {
      base: { acc: 47.73, std: 5.21, lift: 0, rounds: 17.57, tokens: 633.3, cost: 0.388 },
      fewshot: { acc: 69.55, std: 8.85, lift: 21.83, rounds: 15.49, tokens: 606.3, cost: 0.34 },
      self: { acc: 55.91, std: 7.84, lift: 8.18, rounds: 15.98, tokens: 634.8, cost: 0.348 },
      "reflect-3": { acc: 63.35, std: 7.51, lift: 15.62, rounds: 15.36, tokens: 572.6, cost: 0.324 }
    }
  },
  {
    model: "Kimi K2.6",
    harness: "Claude Code",
    thinking: "enabled",
    method: "skill-creator",
    modes: {
      base: { acc: 25.14, std: 12.15, lift: 0, rounds: 46.24, tokens: 1226.7, cost: 0.338 },
      fewshot: { acc: 30.48, std: 13.22, lift: 5.34, rounds: 37.87, tokens: 977, cost: 0.288 },
      self: { acc: 29.16, std: 14.18, lift: 4.02, rounds: 32.67, tokens: 821.6, cost: 0.25 },
      "reflect-3": { acc: 32.68, std: 14.25, lift: 7.54, rounds: 31.68, tokens: 950.5, cost: 0.28 }
    }
  },
  {
    model: "DeepSeek V4 Pro",
    harness: "Claude Code",
    thinking: "max",
    method: "skill-creator",
    modes: {
      base: { acc: 46.06, std: 6.9, lift: 0, rounds: 13.22, tokens: 503.4, cost: 0.031 },
      fewshot: { acc: 54.8, std: 9.65, lift: 8.74, rounds: 11.46, tokens: 439.9, cost: 0.032 },
      self: { acc: 48.69, std: 8.75, lift: 2.63, rounds: 10.53, tokens: 405.7, cost: 0.032 },
      "reflect-3": { acc: 49.22, std: 8.67, lift: 3.16, rounds: 10.26, tokens: 383.8, cost: 0.031 }
    }
  }
];

export const leaderboardModes = ["base", "fewshot", "self", "reflect-3"];

function createLeaderboardRows(version, runs) {
  return runs.flatMap((run) =>
    leaderboardModes.map((mode) => ({
      id: `${version}-${run.harness}-${run.model}-${mode}`.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-"),
      model: run.model,
      harness: run.harness,
      thinking: run.thinking,
      method: run.method,
      mode,
      ...run.modes[mode]
    }))
  );
}

export const leaderboardDataset = {
  taskRange: "001–012",
  rows: createLeaderboardRows("released", v1LeaderboardRuns)
};

export const radarRuns = [
  {
    id: "codex-gpt5-5",
    model: "GPT-5.5",
    harness: "Codex",
    thinking: "xhigh",
    method: "skill-creator",
    scores: {
      base: [44.43, 41.62, 57.84, 31.73, 35.09, 66.28, 38.4, 43.47, 41.87, 63.15, 51.68, 45.08],
      fewshot: [48.12, 51.17, 78.11, 60.94, 52.45, 72.39, 54.31, 95.55, 69.79, 71.44, 63.38, 61.24],
      self: [71.06, 45.36, 62.91, 25.74, 58.86, 70.46, 28.48, 62.44, 52.3, 68.99, 50.23, 63.01],
      "reflect-3": [68.34, 44.24, 57.76, 25.01, 59.51, 72.87, 43.44, 72.68, 68.33, 68.77, 47.61, 60.78]
    }
  },
  {
    id: "claude-opus-4-8",
    model: "Opus 4.8",
    harness: "Claude Code",
    thinking: "xhigh",
    method: "skill-creator",
    scores: {
      base: [48.75, 42.74, 46.69, 25.24, 51.15, 67.98, 39.54, 66.89, 51.76, 58.6, 41.56, 48.41],
      fewshot: [81.96, 58.48, 70.89, 54.55, 57.96, 72.98, 55.76, 93.6, 100, 63.45, 63.48, 77.66],
      self: [77.11, 49.84, 57.21, 38.35, 45.35, 74.72, 37.38, 68.93, 58.07, 60.67, 47.32, 73.48],
      "reflect-3": [71.84, 58.79, 56.48, 45.5, 58.97, 73.52, 51.45, 78.58, 76.68, 58.16, 48.03, 74.7]
    }
  },
  {
    id: "panofy-opus-4-6",
    model: "Opus 4.6",
    harness: "Panofy",
    thinking: "high",
    method: "agent-training",
    scores: {
      base: [63.93, 43.55, 55.16, 16, 47.84, 68.91, 35.56, 63.12, 60.78, 53.11, 49.55, 47.3],
      fewshot: [90.12, 60.03, 72.33, 57.95, 58.4, 67.05, 56.18, 90.94, 90.9, 70.29, 55.86, 87.58],
      self: [76.98, 48.72, 55.71, 19.24, 46.18, 70.76, 42.59, 65.34, 73.22, 72.01, 45.01, 84.91],
      "reflect-3": [76.59, 51.08, 47.47, 30.95, 44.23, 71.31, 43.94, 71.54, 76.78, 69.78, 50.89, 83.23]
    }
  },
  {
    id: "claude-glm-5-2",
    model: "GLM-5.2",
    harness: "Claude Code",
    thinking: "max",
    method: "skill-creator",
    scores: {
      base: [42.94, 40.92, 61.56, 19.68, 48.07, 58.37, 33.36, 56.27, 55.1, 61.54, 47.59, 47.3],
      fewshot: [81.65, 56.27, 74.9, 60.15, 62.44, 70.41, 55.84, 77.94, 88.31, 72.11, 54.4, 80.21],
      self: [61.77, 42.43, 65.65, 28.61, 54.97, 61.15, 35.21, 63.09, 63.45, 69.6, 46.38, 78.58],
      "reflect-3": [78.38, 47.71, 63.15, 42.93, 59.38, 62.07, 55.03, 76.41, 78.35, 64.61, 52, 80.16]
    }
  },
  {
    id: "claude-kimi-k2-6",
    model: "Kimi K2.6",
    harness: "Claude Code",
    thinking: "enabled",
    method: "skill-creator",
    scores: {
      base: [32.04, 30.29, 18.15, 22.56, 15.73, 25, 6.28, 15.73, 44.83, 23.22, 26.6, 41.26],
      fewshot: [44.24, 44, 29.19, 23.97, 11.19, 18.22, 8.5, 15.7, 49.38, 22.85, 40.49, 58.06],
      self: [22.43, 34.55, 19.54, 16.51, 20.93, 26.3, 12.34, 11.77, 58.93, 35.95, 37.08, 53.55],
      "reflect-3": [64.39, 33.63, 20.16, 15.85, 24.95, 27.35, 5.31, 15.46, 53.98, 35.89, 36.1, 59.05]
    }
  },
  {
    id: "claude-deepseek-v4-pro",
    model: "DeepSeek V4 Pro",
    harness: "Claude Code",
    thinking: "max",
    method: "skill-creator",
    scores: {
      base: [56.79, 40, 49.22, 22.63, 47.45, 63.35, 33.2, 56.93, 49.07, 40.33, 45.75, 48.04],
      fewshot: [57.97, 43.38, 38.14, 34.61, 61.99, 63.31, 44.26, 65.25, 72.59, 52.87, 45.07, 78.22],
      self: [64.45, 43.75, 38.63, 19.29, 31.64, 69.24, 32.14, 51.64, 53.01, 62.42, 41.78, 76.27],
      "reflect-3": [63.59, 48.34, 42.48, 23.16, 44.79, 65.61, 32.57, 47.27, 59.93, 51.74, 48.98, 62.2]
    }
  }
];

export const taskGroups = [
  { id: "001", label: "01", domain: "CRM", en: "Marketing lead capture", zh: "市场营销线索捕获" },
  { id: "002", label: "02", domain: "CRM", en: "B2B quote & account response", zh: "B2B 报价与客户响应" },
  { id: "003", label: "03", domain: "CRM", en: "Service ticket resolution", zh: "服务工单处理" },
  { id: "004", label: "04", domain: "CRM", en: "Retention & churn analytics", zh: "留存与流失分析" },
  { id: "005", label: "05", domain: "ERP", en: "Finance expense control & close", zh: "费用控制与账务结算" },
  { id: "006", label: "06", domain: "ERP", en: "Procurement, supplier & receiving", zh: "采购、供应商与收货" },
  { id: "007", label: "07", domain: "ERP", en: "Inventory & order fulfillment", zh: "库存与订单履约" },
  { id: "008", label: "08", domain: "Finance", en: "Personal advisory, tax & estate", zh: "个人理财、税务与遗产规划" },
  { id: "009", label: "09", domain: "Finance", en: "Operational modeling & reporting", zh: "运营建模与管理报表" },
  { id: "010", label: "10", domain: "Finance", en: "Investment strategy & portfolio risk", zh: "投资策略与组合风险" },
  { id: "011", label: "11", domain: "Finance", en: "Credit risk & lending committee", zh: "信用风险与信贷委员会" },
  { id: "012", label: "12", domain: "ERP", en: "HR employee lifecycle & policy", zh: "HR 员工流程与制度" },
  { id: "013", label: "13", domain: "Healthcare", domainKey: "healthcare", domainLabel: { en: "Healthcare", zh: "医药" }, en: "Patient intake, transfer & chart onboarding", zh: "患者接收、转诊与病历建档" },
  { id: "014", label: "14", domain: "Healthcare", domainKey: "healthcare", domainLabel: { en: "Healthcare", zh: "医药" }, en: "Payer authorization, appeals & reimbursement", zh: "医保授权、申诉与报销运营" },
  { id: "015", label: "15", domain: "Healthcare", domainKey: "healthcare", domainLabel: { en: "Healthcare", zh: "医药" }, en: "EHR data governance & record quality", zh: "电子病历数据治理与记录质控" },
  { id: "016", label: "16", domain: "Healthcare", domainKey: "healthcare", domainLabel: { en: "Healthcare", zh: "医药" }, en: "Clinical protocol decision support", zh: "临床方案与决策支持" },
  { id: "017", label: "17", domain: "Legal", domainKey: "legal", domainLabel: { en: "Legal", zh: "法律" }, en: "Investigation production review", zh: "调查材料调取与补救复核" },
  { id: "018", label: "18", domain: "Legal", domainKey: "legal", domainLabel: { en: "Legal", zh: "法律" }, en: "Court disposition & financial entries", zh: "法院处置命令与费用录入" },
  { id: "019", label: "19", domain: "Legal", domainKey: "legal", domainLabel: { en: "Legal", zh: "法律" }, en: "Regulatory licensing & compliance review", zh: "监管许可资格与合规审查" },
  { id: "020", label: "20", domain: "Legal", domainKey: "legal", domainLabel: { en: "Legal", zh: "法律" }, en: "M&A contract review & negotiation", zh: "并购合同审查与谈判" },
  { id: "021", label: "21", domain: "Data Analysis", domainKey: "data", domainLabel: { en: "Data Analysis", zh: "数据分析" }, en: "Data cleaning & quality pipeline", zh: "数据清洗与质量控制流程" },
  { id: "022", label: "22", domain: "Data Analysis", domainKey: "data", domainLabel: { en: "Data Analysis", zh: "数据分析" }, en: "SQL analytics & reconciliation", zh: "SQL 分析与数据核对" },
  { id: "023", label: "23", domain: "Data Analysis", domainKey: "data", domainLabel: { en: "Data Analysis", zh: "数据分析" }, en: "Public health statistical modeling", zh: "公共卫生统计建模审计" },
  { id: "024", label: "24", domain: "Data Analysis", domainKey: "data", domainLabel: { en: "Data Analysis", zh: "数据分析" }, en: "Engineering portfolio analytics", zh: "工程项目组合分析" }
];

const taskTopicSource = {
  "001": [
    ["train_001", "Train", "Event sponsor handoff", "Validate event attendance, sponsor status, qualified leads, and the next CRM follow-up."],
    ["train_002", "Train", "Exhibitor lead qualification", "Rank booth leads by fit, urgency, and account context before assigning sales ownership."],
    ["train_003", "Train", "Webinar import cleanup", "Deduplicate imported attendees and reconcile form answers with existing company records."],
    ["train_004", "Train", "Field-day campaign review", "Turn scattered event activity into clean campaign outcomes and follow-up queues."],
    ["train_005", "Train", "Target-account prospecting", "Identify the strongest prospects in a niche segment and prepare CRM-ready outreach notes."],
    ["test_001", "Test", "Executive forum handoff", "Audit a new event pipeline and decide which accounts deserve immediate sales action."],
    ["test_002", "Test", "Partner expo qualification", "Separate real opportunities from lookalike records after a partner-led marketing event."],
    ["test_003", "Test", "Imported lead normalization", "Clean a messy lead import and connect attendees to the right companies and campaigns."],
    ["test_004", "Test", "Industrial demo follow-up", "Reconcile demo attendance, sponsor signals, and account history into follow-up priorities."],
    ["test_005", "Test", "Regional account shortlist", "Build a prioritized prospect list using firmographic clues and recent engagement signals."]
  ],
  "002": [
    ["train_001", "Train", "Renewal quote triage", "Review a customer request and assemble the right quote details from account context."],
    ["train_002", "Train", "Enterprise upsell response", "Check contract terms, usage signals, and open opportunities before drafting a response."],
    ["train_003", "Train", "Procurement email routing", "Classify buyer questions and attach the right commercial owner and next step."],
    ["train_004", "Train", "Discount exception review", "Decide whether a requested discount fits policy, deal stage, and customer history."],
    ["train_005", "Train", "Account expansion brief", "Summarize renewal risk, expansion fit, and quote blockers for the account team."],
    ["test_001", "Test", "Quote revision request", "Resolve a changed scope request while preserving pricing, approval, and CRM consistency."],
    ["test_002", "Test", "Buyer objection response", "Use account records to answer procurement concerns without inventing commercial terms."],
    ["test_003", "Test", "Contract-change handoff", "Find the correct owner and required evidence for a contract or quote adjustment."],
    ["test_004", "Test", "Multi-site account quote", "Combine subsidiary records, seat counts, and timing into a clean quote recommendation."],
    ["test_005", "Test", "Escalation-ready account note", "Prepare a concise response plan for a customer whose quote needs extra approval."]
  ],
  "003": [
    ["train_001", "Train", "Priority ticket routing", "Read a support case and assign severity, owner, and the next customer action."],
    ["train_002", "Train", "SLA breach investigation", "Use ticket history to explain whether a service-level deadline was missed."],
    ["train_003", "Train", "Bug-report consolidation", "Merge related complaints into a clean support summary without losing customer impact."],
    ["train_004", "Train", "Escalation evidence pack", "Collect reproduction steps, account details, and recent support notes for engineering."],
    ["train_005", "Train", "Resolution quality check", "Verify whether a proposed response actually addresses the customer issue."],
    ["test_001", "Test", "Refund-risk support case", "Identify support history, promised actions, and the right path to preserve the account."],
    ["test_002", "Test", "Outage communication draft", "Summarize customer impact and produce a grounded update from service records."],
    ["test_003", "Test", "Duplicate-ticket cleanup", "Find duplicate cases and consolidate status, ownership, and customer-facing commitments."],
    ["test_004", "Test", "Technical escalation triage", "Decide if a case requires engineering escalation and list the missing diagnostics."],
    ["test_005", "Test", "Close-ready ticket audit", "Check whether a ticket can be closed or needs one more customer-confirmed step."]
  ],
  "004": [
    ["train_001", "Train", "At-risk account scan", "Detect churn risk from usage drops, support history, renewal timing, and stakeholder signals."],
    ["train_002", "Train", "Retention playbook selection", "Choose a save motion based on contract value, adoption pattern, and open issues."],
    ["train_003", "Train", "Customer health explanation", "Turn mixed account signals into a clear health score rationale."],
    ["train_004", "Train", "Renewal objection map", "Connect cancellation language to the right product, price, or support concern."],
    ["train_005", "Train", "Win-back segmenting", "Identify which former customers are realistic candidates for reactivation."],
    ["test_001", "Test", "Executive churn brief", "Summarize why a customer may leave and which actions are most time-sensitive."],
    ["test_002", "Test", "Usage-cohort comparison", "Compare similar customers to separate normal seasonality from real disengagement."],
    ["test_003", "Test", "Retention owner assignment", "Route each account to the correct success, sales, or support owner."],
    ["test_004", "Test", "Cancellation pattern review", "Extract repeated churn drivers from a set of recent customer records."],
    ["test_005", "Test", "Save-plan prioritization", "Rank at-risk customers by revenue impact and probability of recovery."]
  ],
  "005": [
    ["train_001", "Train", "Expense-policy audit", "Check employee expenses against category rules, limits, receipts, and approval status."],
    ["train_002", "Train", "Month-end close cleanup", "Find close blockers caused by unmatched invoices, late approvals, or miscoded items."],
    ["train_003", "Train", "Vendor invoice exception", "Resolve invoice mismatches by comparing purchase, receipt, and payment records."],
    ["train_004", "Train", "Card-spend reconciliation", "Match card transactions to employees, projects, and policy-compliant documentation."],
    ["train_005", "Train", "Accrual review", "Identify expenses that should be accrued before the reporting period closes."],
    ["test_001", "Test", "Late expense triage", "Decide which late claims can be approved and which need finance follow-up."],
    ["test_002", "Test", "Close variance explanation", "Explain budget variance using invoices, expense categories, and timing differences."],
    ["test_003", "Test", "Duplicate payment check", "Detect duplicate or suspicious payments across similar vendor records."],
    ["test_004", "Test", "Department spend review", "Summarize spend exceptions for a department head before close."],
    ["test_005", "Test", "Approval-chain repair", "Find missing approvals and route finance items to the correct approver."]
  ],
  "006": [
    ["train_001", "Train", "Purchase-order matching", "Match requested items, POs, receipts, and supplier invoices."],
    ["train_002", "Train", "Supplier onboarding check", "Verify required vendor records, tax forms, risk flags, and payment terms."],
    ["train_003", "Train", "Receiving discrepancy", "Resolve quantity or item mismatches between warehouse receipt and purchase order."],
    ["train_004", "Train", "Vendor performance review", "Compare late deliveries, defect notes, and contract terms for supplier follow-up."],
    ["train_005", "Train", "Emergency reorder decision", "Determine whether a rush purchase is justified by demand and stock status."],
    ["test_001", "Test", "Invoice hold release", "Decide what evidence is needed before releasing a blocked supplier invoice."],
    ["test_002", "Test", "Supplier substitution request", "Evaluate an alternate supplier using price, availability, and compliance context."],
    ["test_003", "Test", "Partial receipt reconciliation", "Update receiving status when only part of a purchase order arrives."],
    ["test_004", "Test", "Procurement exception summary", "Prepare a clean exception list for finance and operations review."],
    ["test_005", "Test", "Contract-term validation", "Check whether a purchasing decision follows negotiated supplier terms."]
  ],
  "007": [
    ["train_001", "Train", "Stockout prevention", "Spot items at risk of stockout and recommend reorder priorities."],
    ["train_002", "Train", "Order allocation review", "Allocate limited inventory across customer orders using priority and due dates."],
    ["train_003", "Train", "Warehouse transfer plan", "Move stock between locations to cover demand without creating new gaps."],
    ["train_004", "Train", "Backorder communication", "Summarize delayed orders and prepare accurate customer-facing status updates."],
    ["train_005", "Train", "Fulfillment exception audit", "Identify orders blocked by address, payment, inventory, or shipping issues."],
    ["test_001", "Test", "Demand spike response", "Decide how to fulfill urgent demand when inventory is split across sites."],
    ["test_002", "Test", "Aged inventory cleanup", "Find slow-moving items and suggest transfer, markdown, or hold actions."],
    ["test_003", "Test", "Shipment priority queue", "Rank open shipments by service level, customer importance, and promised date."],
    ["test_004", "Test", "Inventory count variance", "Explain count differences using recent receipts, shipments, and adjustments."],
    ["test_005", "Test", "Order rescue plan", "Create the next best action for orders that are close to missing fulfillment SLA."]
  ],
  "008": [
    ["train_001", "Train", "Tax-sensitive income review", "Assess income, deductions, and deadlines before recommending planning steps."],
    ["train_002", "Train", "Estate document checklist", "Identify missing estate-planning documents and beneficiary conflicts."],
    ["train_003", "Train", "Retirement cash-flow snapshot", "Summarize assets, spending, and timeline to guide retirement advice."],
    ["train_004", "Train", "Capital-gains planning", "Evaluate realized gains, holding periods, and tax-loss harvesting opportunities."],
    ["train_005", "Train", "Family advisory brief", "Turn scattered household records into an adviser-ready planning memo."],
    ["test_001", "Test", "Year-end tax action list", "Prioritize tax moves before filing or year-end deadlines."],
    ["test_002", "Test", "Trust and beneficiary review", "Spot mismatches between estate wishes, account titling, and beneficiary records."],
    ["test_003", "Test", "Liquidity-needs analysis", "Determine whether planned withdrawals can cover spending without disrupting strategy."],
    ["test_004", "Test", "Charitable giving scenario", "Compare charitable options using tax impact, timing, and portfolio context."],
    ["test_005", "Test", "Adviser meeting prep", "Prepare the key questions and recommendations for a personal finance review."]
  ],
  "009": [
    ["train_001", "Train", "Revenue-forecast refresh", "Update a forecast from actuals, pipeline changes, and seasonality notes."],
    ["train_002", "Train", "Operating KPI deck", "Choose the right metrics and explain movement for a management update."],
    ["train_003", "Train", "Budget variance bridge", "Explain the difference between plan and actuals across drivers."],
    ["train_004", "Train", "Scenario model check", "Evaluate upside and downside assumptions for a business scenario."],
    ["train_005", "Train", "Monthly report QA", "Find inconsistent totals, stale assumptions, and narrative gaps in a report."],
    ["test_001", "Test", "Board metric summary", "Turn operating data into a concise performance narrative for leadership."],
    ["test_002", "Test", "Forecast-risk callout", "Identify which assumptions create the largest risk to the next forecast."],
    ["test_003", "Test", "Department model reconciliation", "Align headcount, spend, and revenue assumptions across operating teams."],
    ["test_004", "Test", "Executive variance note", "Explain a surprising variance without overclaiming from incomplete data."],
    ["test_005", "Test", "Report correction plan", "Prioritize corrections needed before a financial model can be shared."]
  ],
  "010": [
    ["train_001", "Train", "Portfolio risk scan", "Measure concentration, drawdown exposure, and asset-class imbalance."],
    ["train_002", "Train", "Rebalancing recommendation", "Suggest trades that bring a portfolio closer to target allocation."],
    ["train_003", "Train", "Investment memo review", "Compare thesis, risk, valuation, and time horizon before recommending action."],
    ["train_004", "Train", "Stress-scenario summary", "Explain how a portfolio might behave under rate, inflation, or market shocks."],
    ["train_005", "Train", "Manager due-diligence notes", "Summarize performance, fees, mandate fit, and red flags for a fund manager."],
    ["test_001", "Test", "Risk-budget adjustment", "Decide how to adjust exposure when risk budget or client constraints change."],
    ["test_002", "Test", "Portfolio drift diagnosis", "Find which positions caused allocation drift and what to do next."],
    ["test_003", "Test", "Strategy comparison brief", "Compare candidate strategies using return drivers and downside controls."],
    ["test_004", "Test", "Liquidity stress review", "Check whether portfolio liquidity matches expected withdrawal needs."],
    ["test_005", "Test", "Committee-ready recommendation", "Prepare an investment action with supporting risk and rationale."]
  ],
  "011": [
    ["train_001", "Train", "Borrower risk summary", "Review financials, collateral, covenants, and recent performance for credit risk."],
    ["train_002", "Train", "Loan exception triage", "Identify missing documents and policy exceptions before committee review."],
    ["train_003", "Train", "Covenant breach analysis", "Explain whether a borrower has breached terms and what mitigation is needed."],
    ["train_004", "Train", "Lending memo preparation", "Condense borrower strengths, weaknesses, and proposed terms into a committee memo."],
    ["train_005", "Train", "Portfolio watchlist update", "Rank credits by deterioration signals and required monitoring actions."],
    ["test_001", "Test", "Renewal credit review", "Assess whether a loan renewal fits risk appetite and updated borrower data."],
    ["test_002", "Test", "Collateral sufficiency check", "Evaluate collateral coverage under updated values and outstanding exposure."],
    ["test_003", "Test", "Committee question pack", "Prepare likely committee questions from weaknesses in the credit file."],
    ["test_004", "Test", "Risk-rating adjustment", "Decide whether borrower risk rating should change based on new signals."],
    ["test_005", "Test", "Approval-condition drafting", "Write clear conditions needed before credit approval can proceed."]
  ],
  "012": [
    ["train_001", "Train", "Onboarding readiness audit", "Check whether a new hire has the right documents, systems, and manager actions."],
    ["train_002", "Train", "Leave-policy interpretation", "Apply company policy to a leave request with timing and eligibility constraints."],
    ["train_003", "Train", "Compensation-change routing", "Route a pay or role change through the correct approval and record updates."],
    ["train_004", "Train", "Employee-relations case summary", "Summarize a sensitive HR case with facts, dates, and required next steps."],
    ["train_005", "Train", "Offboarding checklist repair", "Find missing offboarding actions across IT, payroll, manager, and compliance."],
    ["test_001", "Test", "Internal transfer review", "Validate transfer eligibility and identify changes needed in HR systems."],
    ["test_002", "Test", "Policy exception decision", "Decide whether an exception request fits documented HR policy and precedent."],
    ["test_003", "Test", "Performance-cycle cleanup", "Identify missing reviews, calibration blockers, and manager follow-ups."],
    ["test_004", "Test", "Benefits enrollment case", "Resolve benefit eligibility and enrollment timing from employee records."],
    ["test_005", "Test", "Termination-risk handoff", "Prepare a compliant handoff for a complex employee exit."]
  ],
  "013": [
    ["train_001", "Train", "Transfer packet acceptance", "Check whether a transfer packet has the required medical, coverage, and contact materials."],
    ["train_002", "Train", "New patient registration", "Resolve registration readiness from intake forms, insurance status, and missing identifiers."],
    ["train_003", "Train", "Pharmacy and coverage check", "Verify pharmacy details, medication lists, and coverage blockers before service starts."],
    ["train_004", "Train", "Referral scheduling readiness", "Decide whether a referral can be scheduled or must return for missing documentation."],
    ["train_005", "Train", "Chronic-care enrollment", "Apply program rules to decide enrollment, follow-up owner, and next outreach."],
    ["test_001", "Test", "Transfer readiness decision", "Classify an incoming transfer and list the blockers that prevent acceptance."],
    ["test_002", "Test", "Registration issue resolution", "Find what must be corrected before a patient can enter the intake queue."],
    ["test_003", "Test", "Chart onboarding QA", "Check whether chart setup and demographic fields are complete enough for clinical handoff."],
    ["test_004", "Test", "Referral authorization follow-up", "Identify who should chase authorization, documents, or scheduling evidence."],
    ["test_005", "Test", "Program enrollment plan", "Determine the right program path and follow-up timing from mixed intake records."]
  ],
  "014": [
    ["train_001", "Train", "Prior authorization review", "Use payer rules and clinical evidence to decide whether an authorization request is ready."],
    ["train_002", "Train", "Coverage appeal preparation", "Build the evidence package for a drug or service coverage appeal."],
    ["train_003", "Train", "Reimbursement compliance check", "Check claim and reimbursement facts against payer and clinic policy rules."],
    ["train_004", "Train", "Service profitability review", "Compare payer terms, service cost, and utilization details before recommending action."],
    ["train_005", "Train", "Authorization intake routing", "Route authorization requests by urgency, missing evidence, and payer workflow."],
    ["test_001", "Test", "Denial appeal package", "Identify appeal grounds and required attachments after a payer denial."],
    ["test_002", "Test", "Drug assistance routing", "Choose the correct coverage, appeal, or assistance path for medication access."],
    ["test_003", "Test", "Claim correction review", "Find billing corrections and compliance blockers before resubmission."],
    ["test_004", "Test", "Payer evidence checklist", "Assemble the right evidence list without adding unsupported clinical claims."],
    ["test_005", "Test", "Escalation decision", "Decide when a case needs peer review, manual queueing, or payer follow-up."]
  ],
  "015": [
    ["train_001", "Train", "Duplicate chart merge", "Compare patient records and decide whether a merge is safe and auditable."],
    ["train_002", "Train", "Referral data-quality audit", "Check referral records for missing identifiers, dates, documents, and routing signals."],
    ["train_003", "Train", "Service request cleanup", "Normalize service requests while preserving clinical and operational evidence."],
    ["train_004", "Train", "Care-transition packet", "Review handoff materials for completeness, ownership, and follow-up timing."],
    ["train_005", "Train", "Code quality queue", "Find diagnosis or procedure coding issues that require correction or reviewer action."],
    ["test_001", "Test", "Patient identity reconciliation", "Resolve chart identity conflicts and state why a record should or should not merge."],
    ["test_002", "Test", "Referral readiness queue", "Classify referral records by readiness, missing data, and responsible team."],
    ["test_003", "Test", "Record quality correction", "Identify the chart fields and evidence needed before a clinical workflow proceeds."],
    ["test_004", "Test", "Transition handoff audit", "Check whether a care-transition packet supports safe follow-up."],
    ["test_005", "Test", "Follow-up queue assignment", "Assign data-quality issues to the right queue with clear remediation notes."]
  ],
  "016": [
    ["train_001", "Train", "Acute visit assessment", "Apply protocol rules to symptoms, risk signals, and required follow-up actions."],
    ["train_002", "Train", "Lab and medication protocol", "Interpret lab values and medication constraints under a written clinical protocol."],
    ["train_003", "Train", "High-risk care routing", "Decide whether a patient needs routine follow-up, escalation, or urgent review."],
    ["train_004", "Train", "Observation retrieval", "Find the relevant observation window and summarize the clinical evidence."],
    ["train_005", "Train", "Care-management escalation", "Combine comorbidities, labs, and notes into a protocol-bound next step."],
    ["test_001", "Test", "Clinical note decision", "Turn a patient note into a protocol-constrained assessment and plan."],
    ["test_002", "Test", "Medication safety follow-up", "Identify medication risks and the required lab or clinician follow-up."],
    ["test_003", "Test", "Observation window check", "Retrieve and use only observations that match patient, type, and time-window rules."],
    ["test_004", "Test", "Risk escalation triage", "Decide whether a case needs urgent escalation, scheduled review, or routine monitoring."],
    ["test_005", "Test", "Protocol answer audit", "Check a clinical recommendation against the exact allowed protocol actions."]
  ],
  "017": [
    ["train_001", "Train", "Subpoena production gap", "Compare subpoena categories with produced materials and identify missing items."],
    ["train_002", "Train", "Preservation hold review", "Check retention rules, hold dates, and custodian scope for production risk."],
    ["train_003", "Train", "Custodian collection audit", "Find which custodians, channels, or date ranges are missing from collection."],
    ["train_004", "Train", "Privilege log check", "Review withheld documents for privilege labels, descriptions, and defects."],
    ["train_005", "Train", "Remediation plan", "Turn production defects into retrieval, correction, or disclosure actions."],
    ["test_001", "Test", "Grand jury response audit", "Identify production gaps and evidence needed for a subpoena response."],
    ["test_002", "Test", "Regulator production review", "Check custodian scope, retention gaps, and missing attachments for a regulator request."],
    ["test_003", "Test", "Document set QC", "Find inconsistent labels, missing files, and remediation owners in a production set."],
    ["test_004", "Test", "Hold compliance memo", "Summarize whether preservation obligations were met and what remains at risk."],
    ["test_005", "Test", "Production remediation queue", "Prioritize follow-up actions before the next legal production deadline."]
  ],
  "018": [
    ["train_001", "Train", "Sentencing order audit", "Reconcile court orders, docket entries, and sentence details."],
    ["train_002", "Train", "Traffic disposition update", "Apply disposition rules to fines, license effects, and payment timing."],
    ["train_003", "Train", "Payment-plan calculation", "Calculate financial entries and installment rules from court records."],
    ["train_004", "Train", "Probation referral check", "Identify required probation, suspension, and compliance orders."],
    ["train_005", "Train", "Stale export conflict", "Resolve conflicts between docket updates and exported clerk records."],
    ["test_001", "Test", "Disposition reconciliation", "Align docket, order, and financial records before closing a case."],
    ["test_002", "Test", "Collateral order entry", "Determine which collateral orders must be entered after disposition."],
    ["test_003", "Test", "Fee ledger correction", "Find fee, payment, and waiver errors in the case ledger."],
    ["test_004", "Test", "Installment order review", "Check whether payment-plan terms match the judgment and local rules."],
    ["test_005", "Test", "Post-disposition audit", "List missing clerk actions before a case can leave the audit queue."]
  ],
  "019": [
    ["train_001", "Train", "Contractor license eligibility", "Evaluate license eligibility from insurance, bond, exams, and violation records."],
    ["train_002", "Train", "Alcohol license risk review", "Check premises, ownership, incidents, and restricted-license rules."],
    ["train_003", "Train", "Renewal queue triage", "Classify renewals by missing documents, compliance risk, and manual review needs."],
    ["train_004", "Train", "Address matching review", "Resolve business address conflicts across applications and public records."],
    ["train_005", "Train", "Compliance follow-up", "Turn licensing defects into applicant follow-up or enforcement actions."],
    ["test_001", "Test", "Eligibility batch review", "Approve, reject, or queue license applications with clear reasons."],
    ["test_002", "Test", "Restricted license package", "Prepare a staff package for a restricted or high-risk license."],
    ["test_003", "Test", "Manual review decision", "Decide when an application needs manual review instead of routine release."],
    ["test_004", "Test", "Violation impact check", "Determine how prior violations affect renewal or new license eligibility."],
    ["test_005", "Test", "Release boundary audit", "Identify which cases can be released and which need more evidence."]
  ],
  "020": [
    ["train_001", "Train", "Deal profile intake", "Extract buyer, seller, structure, consideration, and key risk terms from deal materials."],
    ["train_002", "Train", "Draft clause population", "Populate contract clauses from the deal profile and drafting playbook."],
    ["train_003", "Train", "Term benchmark review", "Compare requested terms with market benchmarks and internal policy."],
    ["train_004", "Train", "Cap table check", "Use ownership and option data to identify consent or allocation issues."],
    ["train_005", "Train", "Negotiation escalation", "Flag terms that require committee, legal, or business escalation."],
    ["test_001", "Test", "Buyer-side draft review", "Find missing and out-of-policy terms in a buyer-side transaction draft."],
    ["test_002", "Test", "Seller paper markup", "Review counterparty paper and identify negotiation positions."],
    ["test_003", "Test", "Escalation memo", "Summarize deal terms that exceed the playbook or need approval."],
    ["test_004", "Test", "Contract consistency check", "Reconcile schedules, definitions, and economics across transaction documents."],
    ["test_005", "Test", "Negotiation issue list", "Prepare prioritized issues and fallback positions for the deal team."]
  ],
  "021": [
    ["train_001", "Train", "Contact canonicalization", "Deduplicate contact records and choose canonical fields from noisy sources."],
    ["train_002", "Train", "Fuel data normalization", "Standardize fuel units, dates, and missing-value treatment for reporting."],
    ["train_003", "Train", "Freight category cleanup", "Normalize freight categories and quarantine records with conflicting evidence."],
    ["train_004", "Train", "Maintenance-event integrity", "Check maintenance events for duplicates, chronology, and provenance."],
    ["train_005", "Train", "Release decision audit", "Decide whether a cleaned dataset is safe to release for operations."],
    ["test_001", "Test", "Noisy contact export", "Produce a canonical contact export with duplicates and conflicts handled."],
    ["test_002", "Test", "Operational data QA", "Identify data-quality errors and the records that need quarantine."],
    ["test_003", "Test", "Provenance report", "Explain how source precedence and transformations affected final records."],
    ["test_004", "Test", "Integrity error list", "Return structured errors for date, lookup, category, and duplicate issues."],
    ["test_005", "Test", "Certification decision", "State whether the dataset passes quality gates and what remains blocked."]
  ],
  "022": [
    ["train_001", "Train", "Fulfillment cutoff query", "Write cutoff-consistent SQL analysis for orders, shipments, and refunds."],
    ["train_002", "Train", "Support and refund reconciliation", "Reconcile support records, refund events, and customer outcomes."],
    ["train_003", "Train", "Warehouse productivity", "Aggregate warehouse work while respecting time windows and status filters."],
    ["train_004", "Train", "Inventory analytics", "Compute inventory and fulfillment metrics without mixing stale snapshots."],
    ["train_005", "Train", "Controlled correction", "Apply a permitted database correction and verify the resulting query."],
    ["test_001", "Test", "Commerce KPI query", "Return business metrics from the authenticated SQL service with correct filters."],
    ["test_002", "Test", "Refund impact analysis", "Measure refund impact while excluding wrong statuses and duplicate rows."],
    ["test_003", "Test", "Warehouse exception report", "Find fulfillment or warehouse exceptions from joined operational tables."],
    ["test_004", "Test", "Inventory reconciliation", "Compare inventory, orders, and shipment tables for reconciliation gaps."],
    ["test_005", "Test", "Stateful requery", "Correct an earlier SQL result after new constraints are introduced."]
  ],
  "023": [
    ["train_001", "Train", "Release reconciliation", "Reconcile public-health releases, identifiers, and usable cohort boundaries."],
    ["train_002", "Train", "Cohort construction", "Build a state, county, or country cohort with documented inclusion rules."],
    ["train_003", "Train", "Regression audit", "Run or review statistical models and report robustness limitations."],
    ["train_004", "Train", "Indicator PCA review", "Construct indicator features and explain cross-level modeling choices."],
    ["train_005", "Train", "Transportability check", "Assess whether conclusions transfer across geography, year, or data source."],
    ["test_001", "Test", "Public-health model audit", "Audit a statistical result for cohort, variable, and interpretation errors."],
    ["test_002", "Test", "Long-format data check", "Find missing, imputed, or mismatched cells in long-format health data."],
    ["test_003", "Test", "Mediation analysis review", "Check whether a mediation or robustness claim is supported by the data."],
    ["test_004", "Test", "Cross-level conclusion", "Write a controlled conclusion that respects model and data limitations."],
    ["test_005", "Test", "Publication readiness", "Decide what must be corrected before publishing a health-analysis result."]
  ],
  "024": [
    ["train_001", "Train", "Engineering work mix", "Classify work items by portfolio category, delivery stream, and quarter."],
    ["train_002", "Train", "Reliability SLA aging", "Review reliability backlog age, ownership, and breach status."],
    ["train_003", "Train", "Security backlog review", "Prioritize security work items by severity, dependency, and service impact."],
    ["train_004", "Train", "Release readiness gate", "Assess whether dependencies, blockers, and risks allow a release to proceed."],
    ["train_005", "Train", "Delivery risk rollup", "Combine portfolio, blocker, and readiness signals into an executive rollup."],
    ["test_001", "Test", "Portfolio mix classification", "Classify engineering work and summarize the delivery mix for leadership."],
    ["test_002", "Test", "Backlog SLA review", "Identify overdue reliability or security items and assign follow-up owners."],
    ["test_003", "Test", "Release dependency audit", "Find blockers and readiness risks across linked work items."],
    ["test_004", "Test", "Delivery decision memo", "Recommend go, hold, or escalate based on work-item evidence."],
    ["test_005", "Test", "Combined risk dashboard", "Prepare a concise dashboard of delivery, SLA, and dependency risks."]
  ]
};

const taskTopicTranslations = {
  "001": {
    train_001: ["活动赞助商交接", "验证活动出席、赞助商身份、合格线索和下一步 CRM 跟进。"],
    train_002: ["展商线索资格判定", "在分配销售负责人前，根据匹配度、紧急度和客户上下文对展台线索排序。"],
    train_003: ["网络研讨会导入清洗", "对导入的参会者去重，并将表单答案与现有公司记录核对。"],
    train_004: ["现场活动营销复盘", "将零散的活动行为整理成清晰的营销结果和跟进队列。"],
    train_005: ["目标客户挖掘", "识别细分市场中最强的潜在客户，并准备可写入 CRM 的外联备注。"],
    test_001: ["高管论坛交接", "审计新的活动线索流水线，并决定哪些客户值得立即销售跟进。"],
    test_002: ["合作伙伴展会资格判定", "在合作伙伴主导的营销活动后，将真实机会与相似记录区分开。"],
    test_003: ["导入线索标准化", "清洗混乱的线索导入数据，并将参会者连接到正确的公司和活动。"],
    test_004: ["工业演示跟进", "整合演示出席、赞助商信号和客户历史，形成跟进优先级。"],
    test_005: ["区域客户短名单", "利用企业画像线索和近期互动信号，生成优先级排序的潜在客户列表。"]
  },
  "002": {
    train_001: ["续约报价分诊", "审核客户请求，并根据账户上下文整理正确的报价细节。"],
    train_002: ["企业追加销售响应", "在起草回复前，检查合同条款、使用信号和未结商机。"],
    train_003: ["采购邮件路由", "分类买方问题，并附上正确的商务负责人和下一步。"],
    train_004: ["折扣例外审核", "判断请求的折扣是否符合政策、交易阶段和客户历史。"],
    train_005: ["账户扩展简报", "为账户团队总结续约风险、扩展匹配度和报价阻塞点。"],
    test_001: ["报价修订请求", "在保持价格、审批和 CRM 一致性的前提下处理范围变更请求。"],
    test_002: ["买方异议回复", "使用账户记录回答采购疑虑，且不编造商务条款。"],
    test_003: ["合同变更交接", "为合同或报价调整找到正确负责人和所需证据。"],
    test_004: ["多站点账户报价", "整合子公司记录、席位数量和时间安排，形成清晰的报价建议。"],
    test_005: ["可升级账户备注", "为需要额外审批的客户报价准备简洁的响应计划。"]
  },
  "003": {
    train_001: ["高优先级工单路由", "阅读支持案例，并分配严重级别、负责人和下一步客户动作。"],
    train_002: ["SLA 违约调查", "使用工单历史解释服务级别截止时间是否被错过。"],
    train_003: ["缺陷报告合并", "将相关投诉合并成清晰的支持摘要，同时保留客户影响。"],
    train_004: ["升级证据包", "为工程团队收集复现步骤、账户细节和近期支持备注。"],
    train_005: ["解决质量检查", "验证拟定回复是否真正解决了客户问题。"],
    test_001: ["退款风险支持案例", "识别支持历史、承诺动作和保留账户的正确路径。"],
    test_002: ["故障沟通草稿", "总结客户影响，并基于服务记录产出可靠更新。"],
    test_003: ["重复工单清理", "找出重复案例，并合并状态、归属和面向客户的承诺。"],
    test_004: ["技术升级分诊", "判断案例是否需要工程升级，并列出缺失的诊断信息。"],
    test_005: ["可关闭工单审计", "检查工单能否关闭，还是需要客户确认的最后一步。"]
  },
  "004": {
    train_001: ["风险账户扫描", "从使用量下降、支持历史、续约时间和干系人信号中发现流失风险。"],
    train_002: ["留存方案选择", "根据合同价值、采用模式和未解决问题选择挽留动作。"],
    train_003: ["客户健康度解释", "将混合账户信号转化为清晰的健康评分依据。"],
    train_004: ["续约异议映射", "把取消意向连接到正确的产品、价格或支持问题。"],
    train_005: ["赢回客户分层", "识别哪些流失客户是现实可行的重新激活对象。"],
    test_001: ["高管流失简报", "总结客户可能流失的原因，以及哪些动作最具时效性。"],
    test_002: ["使用队列对比", "比较相似客户，将正常季节性波动与真实流失区分开。"],
    test_003: ["留存负责人分配", "将每个账户路由给正确的客户成功、销售或支持负责人。"],
    test_004: ["取消模式复盘", "从近期客户记录中提取反复出现的流失驱动因素。"],
    test_005: ["挽留计划优先级", "按收入影响和恢复概率对风险客户排序。"]
  },
  "005": {
    train_001: ["费用政策审计", "按照类别规则、限额、凭证和审批状态检查员工费用。"],
    train_002: ["月结清理", "找出未匹配发票、延迟审批或编码错误导致的关账阻塞点。"],
    train_003: ["供应商发票例外", "通过比较采购、收货和付款记录解决发票不匹配。"],
    train_004: ["公司卡支出核对", "将卡交易匹配到员工、项目和符合政策的凭证。"],
    train_005: ["应计费用复核", "识别在报告期关闭前应计提的费用。"],
    test_001: ["逾期费用分诊", "判断哪些逾期报销可以批准，哪些需要财务跟进。"],
    test_002: ["关账差异解释", "使用发票、费用类别和时间差异解释预算差异。"],
    test_003: ["重复付款检查", "在相似供应商记录中检测重复或可疑付款。"],
    test_004: ["部门支出复盘", "在关账前为部门负责人总结支出例外。"],
    test_005: ["审批链修复", "找出缺失审批，并将财务事项路由给正确审批人。"]
  },
  "006": {
    train_001: ["采购订单匹配", "匹配申请物料、采购订单、收货记录和供应商发票。"],
    train_002: ["供应商准入检查", "验证必需的供应商记录、税务表单、风险标记和付款条款。"],
    train_003: ["收货差异处理", "解决仓库收货与采购订单之间的数量或物料不匹配。"],
    train_004: ["供应商绩效复盘", "比较延迟交付、缺陷备注和合同条款，以便供应商跟进。"],
    train_005: ["紧急补货决策", "根据需求和库存状态判断紧急采购是否合理。"],
    test_001: ["发票冻结解除", "判断在释放被冻结供应商发票前需要哪些证据。"],
    test_002: ["供应商替代请求", "根据价格、可用性和合规上下文评估替代供应商。"],
    test_003: ["部分收货核对", "在采购订单仅部分到货时更新收货状态。"],
    test_004: ["采购例外摘要", "为财务和运营复核准备清晰的例外清单。"],
    test_005: ["合同条款校验", "检查采购决策是否遵循已谈判的供应商条款。"]
  },
  "007": {
    train_001: ["缺货预防", "发现有缺货风险的物料，并推荐补货优先级。"],
    train_002: ["订单分配复核", "基于优先级和到期日期在客户订单之间分配有限库存。"],
    train_003: ["仓库调拨计划", "在不制造新缺口的前提下，在地点之间调拨库存以覆盖需求。"],
    train_004: ["延期订单沟通", "总结延迟订单，并准备准确的客户状态更新。"],
    train_005: ["履约例外审计", "识别因地址、付款、库存或配送问题受阻的订单。"],
    test_001: ["需求激增响应", "在库存分散于多个站点时决定如何满足紧急需求。"],
    test_002: ["呆滞库存清理", "找出周转缓慢的物料，并建议调拨、降价或冻结动作。"],
    test_003: ["发货优先队列", "按服务级别、客户重要性和承诺日期对未结发货排序。"],
    test_004: ["库存盘点差异", "用近期收货、发货和调整解释盘点差异。"],
    test_005: ["订单抢救计划", "为接近错过履约 SLA 的订单制定下一步最佳动作。"]
  },
  "008": {
    train_001: ["税务敏感收入复核", "在建议规划步骤前评估收入、扣除项和截止日期。"],
    train_002: ["遗产文件清单", "识别缺失的遗产规划文件和受益人冲突。"],
    train_003: ["退休现金流快照", "总结资产、支出和时间线，以支持退休建议。"],
    train_004: ["资本利得规划", "评估已实现收益、持有期和税损收割机会。"],
    train_005: ["家庭顾问简报", "将分散的家庭记录整理成顾问可用的规划备忘录。"],
    test_001: ["年末税务行动清单", "在申报或年末截止日期前排列税务动作优先级。"],
    test_002: ["信托和受益人复核", "发现遗产意愿、账户登记和受益人记录之间的不匹配。"],
    test_003: ["流动性需求分析", "判断计划提款能否覆盖支出且不破坏投资策略。"],
    test_004: ["慈善捐赠场景", "根据税务影响、时间安排和投资组合上下文比较慈善选项。"],
    test_005: ["顾问会议准备", "为个人理财复盘准备关键问题和建议。"]
  },
  "009": {
    train_001: ["收入预测刷新", "根据实际值、管道变化和季节性备注更新预测。"],
    train_002: ["运营 KPI 汇报材料", "为管理层更新选择正确指标并解释变化。"],
    train_003: ["预算差异桥接", "按驱动因素解释计划与实际之间的差异。"],
    train_004: ["情景模型检查", "评估业务情景中的上行情形和下行情形假设。"],
    train_005: ["月度报告质检", "找出报告中的总数不一致、过期假设和叙事缺口。"],
    test_001: ["董事会指标摘要", "将运营数据转化为面向领导层的简洁表现叙事。"],
    test_002: ["预测风险提示", "识别哪些假设给下一版预测带来最大风险。"],
    test_003: ["部门模型核对", "对齐运营团队之间的人数、支出和收入假设。"],
    test_004: ["高管差异说明", "在数据不完整时解释意外差异且不过度推断。"],
    test_005: ["报告修正计划", "确定财务模型共享前最需要优先修正的问题。"]
  },
  "010": {
    train_001: ["投资组合风险扫描", "衡量集中度、回撤暴露和资产类别失衡。"],
    train_002: ["再平衡建议", "建议让投资组合更接近目标配置的交易。"],
    train_003: ["投资备忘录复核", "在建议动作前比较投资逻辑、风险、估值和时间周期。"],
    train_004: ["压力情景摘要", "解释投资组合在利率、通胀或市场冲击下可能如何表现。"],
    train_005: ["管理人尽调备注", "为基金管理人总结业绩、费用、授权匹配度和风险信号。"],
    test_001: ["风险预算调整", "在风险预算或客户约束变化时决定如何调整敞口。"],
    test_002: ["组合漂移诊断", "找出哪些持仓导致配置漂移以及下一步应做什么。"],
    test_003: ["策略对比简报", "使用收益驱动因素和下行控制比较候选策略。"],
    test_004: ["流动性压力复核", "检查投资组合流动性是否匹配预期提款需求。"],
    test_005: ["委员会可用建议", "准备带有风险和理由支撑的投资动作。"]
  },
  "011": {
    train_001: ["借款人风险摘要", "复核财务、抵押品、契约和近期表现以评估信用风险。"],
    train_002: ["贷款例外分诊", "在委员会复核前识别缺失文件和政策例外。"],
    train_003: ["契约违约分析", "解释借款人是否违反条款以及需要哪些缓释措施。"],
    train_004: ["信贷备忘录准备", "将借款人优势、劣势和拟议条款压缩成委员会备忘录。"],
    train_005: ["组合观察名单更新", "按恶化信号和所需监控动作对信用项目排序。"],
    test_001: ["续贷信用复核", "评估贷款续期是否符合风险偏好和更新后的借款人数据。"],
    test_002: ["抵押品充足性检查", "在更新价值和未偿敞口下评估抵押品覆盖度。"],
    test_003: ["委员会问题包", "根据授信文件中的弱点准备可能的委员会问题。"],
    test_004: ["风险评级调整", "根据信号判断借款人风险评级是否应调整。"],
    test_005: ["审批条件起草", "写出信贷审批继续前需要满足的清晰条件。"]
  },
  "012": {
    train_001: ["入职准备审计", "检查新员工是否具备正确文件、系统和经理动作。"],
    train_002: ["休假政策解释", "在时间和资格约束下将公司政策应用到休假请求。"],
    train_003: ["薪酬变更路由", "将薪酬或岗位变更路由到正确审批和记录更新流程。"],
    train_004: ["员工关系案例摘要", "用事实、日期和所需下一步总结敏感 HR 案例。"],
    train_005: ["离职清单修复", "找出 IT、薪资、经理和合规之间缺失的离职动作。"],
    test_001: ["内部调岗复核", "验证调岗资格，并识别 HR 系统中需要变更的内容。"],
    test_002: ["政策例外决策", "判断例外请求是否符合书面 HR 政策和先例。"],
    test_003: ["绩效周期清理", "识别缺失评审、校准阻塞点和经理跟进事项。"],
    test_004: ["福利登记案例", "根据员工记录解决福利资格和登记时间问题。"],
    test_005: ["离职风险交接", "为复杂员工退出准备合规交接。"]
  },
  "013": {
    train_001: ["转入资料接收", "检查转入资料是否包含必要的医疗、保险和联系人材料。"],
    train_002: ["新患者注册", "根据登记表、保险状态和缺失标识判断是否可以建档。"],
    train_003: ["药房与保险核对", "在服务开始前核对药房信息、用药清单和保险阻塞点。"],
    train_004: ["转诊排期准备度", "判断转诊能否排期，或是否必须退回补充资料。"],
    train_005: ["慢病项目登记", "根据项目规则判断登记资格、跟进负责人和下一步外联。"],
    test_001: ["转入准备度判断", "分类 incoming transfer，并列出阻止接收的缺口。"],
    test_002: ["注册问题处理", "找出患者进入接收队列前必须修正的内容。"],
    test_003: ["病历建档质检", "检查病历和人口信息字段是否足以交给临床团队。"],
    test_004: ["转诊授权跟进", "识别应由谁追踪授权、文件或排期证据。"],
    test_005: ["项目登记计划", "根据混合接收记录确定项目路径和跟进时间。"]
  },
  "014": {
    train_001: ["预授权审查", "根据 payer 规则和临床证据判断授权申请是否准备充分。"],
    train_002: ["coverage 申诉准备", "为药品或服务 coverage 申诉整理证据包。"],
    train_003: ["报销合规核对", "按照 payer 和诊所规则检查 claim 与报销事实。"],
    train_004: ["服务盈利性复核", "在建议动作前比较 payer 条款、服务成本和使用情况。"],
    train_005: ["授权接收分流", "按紧急程度、缺失证据和 payer 流程分流授权请求。"],
    test_001: ["拒批申诉材料", "在 payer 拒批后识别申诉理由和所需附件。"],
    test_002: ["药品援助路径", "为用药可及性选择 coverage、申诉或援助路径。"],
    test_003: ["claim 修正复核", "在重新提交前找出计费修正和合规阻塞点。"],
    test_004: ["payer 证据清单", "整理正确证据清单，避免添加没有依据的临床说法。"],
    test_005: ["升级处理判断", "判断案件何时需要同业评审、人工队列或 payer 跟进。"]
  },
  "015": {
    train_001: ["重复病历合并", "比较患者记录，判断合并是否安全且可审计。"],
    train_002: ["转诊数据质量审计", "检查转诊记录是否缺少标识、日期、文件和路由信号。"],
    train_003: ["服务请求清洗", "在保留临床和运营证据的前提下规范服务请求。"],
    train_004: ["护理交接资料包", "复核交接材料的完整性、负责人和跟进时间。"],
    train_005: ["编码质量队列", "找出需要修正或复核的诊断和流程编码问题。"],
    test_001: ["患者身份核对", "处理病历身份冲突，并说明记录是否应合并。"],
    test_002: ["转诊准备度队列", "按准备度、缺失数据和负责团队分类转诊记录。"],
    test_003: ["记录质量修正", "识别临床流程继续前所需的字段和证据。"],
    test_004: ["交接资料审计", "检查护理交接资料是否支持安全跟进。"],
    test_005: ["跟进队列分配", "把数据质量问题分配到正确队列，并写明修复备注。"]
  },
  "016": {
    train_001: ["急诊就诊评估", "根据症状、风险信号和后续动作应用临床方案规则。"],
    train_002: ["化验与用药方案", "在书面方案约束下解释化验值和用药限制。"],
    train_003: ["高风险护理路由", "判断患者需要常规跟进、升级处理还是紧急复核。"],
    train_004: ["观察记录检索", "找到相关观察窗口，并总结临床证据。"],
    train_005: ["护理管理升级", "结合共病、化验和病历备注，确定方案允许的下一步。"],
    test_001: ["临床记录决策", "把患者记录转化为符合方案的评估和计划。"],
    test_002: ["用药安全跟进", "识别用药风险以及必要的化验或医生跟进。"],
    test_003: ["观察窗口核对", "只使用匹配患者、类型和时间窗口的观察记录。"],
    test_004: ["风险升级分诊", "判断案件需要紧急升级、预约复核还是常规监测。"],
    test_005: ["方案答案审计", "检查临床建议是否符合明确允许的方案动作。"]
  },
  "017": {
    train_001: ["传票材料缺口", "对比传票类别和已提交材料，识别缺失项。"],
    train_002: ["证据保全复核", "检查保留规则、保全日期和保管人范围是否存在提交风险。"],
    train_003: ["保管人收集审计", "找出缺失的保管人、沟通渠道或日期范围。"],
    train_004: ["特权日志检查", "复核 withheld documents 的特权标签、描述和缺陷。"],
    train_005: ["补救计划", "把材料缺陷转化为检索、修正或披露动作。"],
    test_001: ["大陪审团响应审计", "识别传票响应中的材料缺口和所需证据。"],
    test_002: ["监管材料复核", "检查监管请求中的保管人范围、保留缺口和缺失附件。"],
    test_003: ["文件集质检", "找出材料集中的标签不一致、缺失文件和补救负责人。"],
    test_004: ["保全合规备忘录", "总结保全义务是否满足，以及仍有哪些风险。"],
    test_005: ["材料补救队列", "在下一次提交截止前排序后续动作。"]
  },
  "018": {
    train_001: ["判决命令审计", "核对法院命令、案卷记录和量刑细节。"],
    train_002: ["交通案件处置更新", "将处置规则应用到罚款、驾照影响和付款时间。"],
    train_003: ["付款计划计算", "根据法院记录计算费用录入和分期规则。"],
    train_004: ["缓刑转介检查", "识别所需的缓刑、暂停和合规命令。"],
    train_005: ["过期导出冲突", "处理案卷更新与书记员导出记录之间的冲突。"],
    test_001: ["处置记录核对", "在结案前对齐案卷、命令和财务记录。"],
    test_002: ["附带命令录入", "确定处置后必须录入哪些附带命令。"],
    test_003: ["费用台账修正", "找出案件台账中的费用、付款和减免错误。"],
    test_004: ["分期命令复核", "检查付款计划条款是否符合判决和地方法规。"],
    test_005: ["处置后审计", "列出案件离开审计队列前缺失的书记员动作。"]
  },
  "019": {
    train_001: ["承包商许可资格", "根据保险、保证金、考试和违规记录评估许可资格。"],
    train_002: ["酒类许可风险复核", "检查经营地点、所有权、事件和限制性许可规则。"],
    train_003: ["续期队列分诊", "按缺失文件、合规风险和人工复核需求分类续期。"],
    train_004: ["地址匹配复核", "处理申请和公开记录之间的营业地址冲突。"],
    train_005: ["合规跟进", "把许可缺陷转化为申请人跟进或执法动作。"],
    test_001: ["资格批量复核", "对许可申请作出通过、拒绝或入队决定，并给出理由。"],
    test_002: ["限制性许可材料", "为受限或高风险许可准备工作人员材料包。"],
    test_003: ["人工复核判断", "判断申请何时需要人工复核而不是常规放行。"],
    test_004: ["违规影响检查", "判断历史违规如何影响续期或新许可资格。"],
    test_005: ["放行边界审计", "识别哪些案件可以放行，哪些还需要更多证据。"]
  },
  "020": {
    train_001: ["交易信息接收", "从交易材料中提取买方、卖方、结构、对价和关键风险条款。"],
    train_002: ["合同条款填充", "根据交易信息和起草手册填充合同条款。"],
    train_003: ["条款基准复核", "将请求条款与市场基准和内部政策比较。"],
    train_004: ["股权表检查", "用所有权和期权数据识别同意或分配问题。"],
    train_005: ["谈判升级", "标记需要委员会、法务或业务升级的条款。"],
    test_001: ["买方草案复核", "找出买方交易草案中缺失和超出政策的条款。"],
    test_002: ["卖方文本审阅", "复核对方文本并识别谈判立场。"],
    test_003: ["升级备忘录", "总结超出手册或需要审批的交易条款。"],
    test_004: ["合同一致性检查", "核对交易文件中的附表、定义和经济条款。"],
    test_005: ["谈判问题清单", "为交易团队准备优先问题和备用立场。"]
  },
  "021": {
    train_001: ["联系人标准化", "对联系人记录去重，并从噪声来源中选择标准字段。"],
    train_002: ["燃料数据标准化", "为报告统一燃料单位、日期和缺失值处理。"],
    train_003: ["货运分类清洗", "规范货运类别，并隔离证据冲突的记录。"],
    train_004: ["维护事件完整性", "检查维护事件的重复、时间顺序和来源。"],
    train_005: ["发布决策审计", "判断清洗后的数据集是否可用于运营发布。"],
    test_001: ["噪声联系人导出", "生成标准联系人导出，并处理重复与冲突。"],
    test_002: ["运营数据质检", "识别数据质量错误和需要隔离的记录。"],
    test_003: ["来源报告", "解释来源优先级和转换如何影响最终记录。"],
    test_004: ["完整性错误清单", "返回日期、查找、分类和重复问题的结构化错误。"],
    test_005: ["认证决策", "说明数据集是否通过质量门槛以及仍有哪些阻塞点。"]
  },
  "022": {
    train_001: ["履约截止查询", "为订单、发货和退款编写符合截止口径的 SQL 分析。"],
    train_002: ["客服与退款核对", "核对客服记录、退款事件和客户结果。"],
    train_003: ["仓库生产率", "在正确时间窗口和状态过滤下聚合仓库工作。"],
    train_004: ["库存分析", "在不混用过期快照的前提下计算库存和履约指标。"],
    train_005: ["受控修正", "执行允许的数据库修正，并验证修正后的查询结果。"],
    test_001: ["商业指标查询", "从认证 SQL 服务返回带正确过滤条件的业务指标。"],
    test_002: ["退款影响分析", "排除错误状态和重复行后衡量退款影响。"],
    test_003: ["仓库异常报告", "从联表运营数据中找出履约或仓库异常。"],
    test_004: ["库存核对", "比较库存、订单和发货表，找出核对缺口。"],
    test_005: ["有状态重查", "在加入新限制后修正先前 SQL 结果。"]
  },
  "023": {
    train_001: ["发布版本核对", "核对公共卫生发布版本、标识和可用 cohort 边界。"],
    train_002: ["cohort 构建", "用明确纳入规则构建州、县或国家 cohort。"],
    train_003: ["回归审计", "运行或复核统计模型，并报告稳健性限制。"],
    train_004: ["指标 PCA 复核", "构造指标特征，并解释跨层级建模选择。"],
    train_005: ["可迁移性检查", "评估结论是否能跨地域、年份或数据源迁移。"],
    test_001: ["公共卫生模型审计", "审计统计结果中的 cohort、变量和解释错误。"],
    test_002: ["长表数据检查", "找出长格式健康数据中的缺失、插补或不匹配单元格。"],
    test_003: ["中介分析复核", "检查中介或稳健性结论是否被数据支持。"],
    test_004: ["跨层级结论", "写出受模型和数据限制约束的结论。"],
    test_005: ["发布准备度", "判断健康分析结果发布前必须修正什么。"]
  },
  "024": {
    train_001: ["工程工作组合", "按项目组合类别、交付流和季度分类工作项。"],
    train_002: ["可靠性 SLA 老化", "复核可靠性 backlog 的年龄、负责人和违约状态。"],
    train_003: ["安全 backlog 复核", "按严重度、依赖和服务影响排序安全工作项。"],
    train_004: ["发布准备门槛", "评估依赖、阻塞和风险是否允许发布继续。"],
    train_005: ["交付风险汇总", "把组合、阻塞和准备度信号汇总为管理层报告。"],
    test_001: ["项目组合分类", "分类工程工作，并为管理层总结交付结构。"],
    test_002: ["backlog SLA 复核", "识别逾期的可靠性或安全事项，并分配后续负责人。"],
    test_003: ["发布依赖审计", "在关联工作项中找出阻塞和准备度风险。"],
    test_004: ["交付决策备忘录", "根据工作项证据建议继续、暂停或升级。"],
    test_005: ["综合风险看板", "准备交付、SLA 和依赖风险的简洁看板。"]
  }
};

export const taskTopics = Object.fromEntries(
  Object.entries(taskTopicSource).map(([groupId, topics]) => [
    groupId,
    topics.map(([id, kind, title, desc]) => {
      const [zhTitle, zhDesc] = taskTopicTranslations[groupId]?.[id] ?? [title, desc];
      return {
        id,
        kind,
        title: { en: title, zh: zhTitle },
        desc: { en: desc, zh: zhDesc }
      };
    })
  ])
);
