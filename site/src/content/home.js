export const homeContent = {
  documentTitle: {
    home: "GDPevo: Evaluating Agent Self-Evolution on Real Business Tasks",
    blog: "GDPevo Blog: Evaluating Agent Self-Evolution on Real Business Tasks"
  },
  footer: {
    tagline: {
      en: "Evaluating agent self-evolution on GDP-worthy work.",
      zh: "在真实业务任务上评估 Agent 的自我进化。"
    },
    repoLabel: "github.com/Prism-Shadow/GDPevo"
  },
  header: {
    home: {
      en: "Home",
      zh: "首页"
    },
    blog: {
      en: "Blog",
      zh: "博客"
    }
  },
  hero: {
    title: {
      brand: "GDPevo",
      en: ["Evaluating Agent", "Self-Evolution on Real Business Tasks"],
      zh: ["在真实业务任务上", "评估 Agent 的自我进化"]
    },
    subtitle: {
      en: "The focus is not whether an agent can solve one task, but **whether it can evolve across related tasks to get better**.",
      zh: "我们关注的不是*一个 agent 能不能解决某个单题*，而是**它能不能借由相关任务完成自我进化，越来越擅长这一类任务**。"
    },
    meta: {
      en: "PrismShadow Team · 2026",
      zh: "PrismShadow Team · 2026"
    },
    actions: {
      github: "GitHub",
      results: {
        en: "Results",
        zh: "结果"
      },
      blog: {
        en: "Read the blog",
        zh: "阅读博客"
      },
      experimentBoard: {
        en: "Experiment board",
        zh: "实验看板"
      }
    },
    stats: [
      {
        key: "tasks",
        value: "120",
        label: {
          en: "GDP-worthy tasks",
          zh: "真实业务任务"
        }
      },
      {
        key: "groups",
        value: "12",
        label: {
          en: "task groups",
          zh: "任务组"
        }
      },
      {
        key: "accuracy",
        value: "+18.82",
        unit: "pp",
        positive: true,
        label: {
          en: "held-out accuracy lift from self-evolution",
          zh: "自我进化带来的 held-out 准确率提升"
        }
      },
      {
        key: "cost",
        value: "−7.54",
        unit: "%",
        positive: true,
        label: {
          en: "token cost: fewer, not more",
          zh: "token 成本：更少，而非更多"
        }
      }
    ]
  },
  summary: {
    captionSuffix: {
      en: "avg@3 over 12 task groups",
      zh: "12 个 task group 的 avg@3"
    },
    columns: {
      mode: {
        en: "Mode",
        zh: "模式"
      },
      tokens: {
        en: "Tokens (k)",
        zh: "Tokens (k)"
      }
    }
  },
  results: {
    heading: {
      en: "Self-evolution makes agents more accurate while spending **fewer** tokens.",
      zh: "自我进化让 agent 更准，同时花**更少**的 token。"
    },
    lead: {
      en: "Each group has 5 train and 5 held-out test tasks. We compare a baseline (`base`) against two evolution modes: `demo` evolves from worked examples, while `reflect` evolves from its own mistakes. The score measures lift on tasks the agent never saw.",
      zh: "每组有 5 个 train、5 个 held-out test。我们用基线（`base`）对比两种进化模式：`demo` 基于样例进化，`reflect` 基于自己的错误进化；分数衡量的是 agent 在没见过的任务上的提升。"
    },
    notes: [
      {
        key: "avg",
        en: "**avg@3** = mean held-out accuracy over 3 attempts per task. The task-group chart below keeps Codex, Claude Code, and Panofy side by side under the same base, demo, and reflect settings.",
        zh: "**avg@3** = 每个任务 3 次尝试的 held-out 准确率均值。下面的 task-group 图并排展示 Codex、Claude Code 与 Panofy 在 base、demo、reflect 下的结果。"
      },
      {
        key: "lift",
        en: "Accuracy lift / cost change: **+20.31 pp / −8.69%** (Claude Code) · **+18.21 pp / −25.75%** (Codex) · **+17.94 pp / +11.82%** (Panofy).",
        zh: "准确率提升 / Cost 变化：**+20.31 pp / −8.69%**（Claude Code）· **+18.21 pp / −25.75%**（Codex）· **+17.94 pp / +11.82%**（Panofy）。"
      },
      {
        key: "reports",
        en: "Full per-task reports are under [`experiments/codex_gpt5_5_xhigh/`](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/codex_gpt5_5_xhigh), [`experiments/claude_code_opus_4_8_xhigh/`](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/claude_code_opus_4_8_xhigh), and [`experiments/panofy_claude_opus_4_6_high/`](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/panofy_claude_opus_4_6_high).",
        zh: "完整逐任务报告见 [`experiments/codex_gpt5_5_xhigh/`](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/codex_gpt5_5_xhigh)、[`experiments/claude_code_opus_4_8_xhigh/`](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/claude_code_opus_4_8_xhigh) 与 [`experiments/panofy_claude_opus_4_6_high/`](https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/panofy_claude_opus_4_6_high)。"
      }
    ],
    blogLink: {
      en: "Why can self-evolution lift accuracy and cost less? Read the blog →",
      zh: "为什么自我进化能提升准确率，还能更省？阅读博客 →"
    },
    chartTitle: {
      en: "Held-out accuracy by task group (avg@3, %)",
      zh: "各 task group 的 held-out 准确率 (avg@3, %)"
    },
    chartColumns: {
      taskGroup: {
        en: "Task group",
        zh: "Task group"
      },
      harness: "Harness",
      model: "Model",
      thinking: "Thinking level",
      setting: {
        en: "Setting",
        zh: "设定"
      },
      accuracy: "Accuracy"
    }
  },
  tasks: {
    heading: {
      en: "Real company interfaces: CRM, ERP, Finance.",
      zh: "真实的公司业务接口：CRM、ERP、Finance。"
    },
    domainDefinitions: [
      {
        term: "CRM",
        en: "Customer Relationship Management",
        zh: "客户关系管理"
      },
      {
        term: "ERP",
        en: "Enterprise Resource Planning",
        zh: "企业资源计划"
      },
      {
        term: "Finance",
        en: "Financial Services",
        zh: "金融业务"
      }
    ],
    lead: {
      en: "Each group is one shared business world with lookalike records mixed in, seeded from real-job sources such as [GDPval](https://openai.com/index/gdpval/) and [SOP-Bench](https://github.com/amazon-science/SOP-Bench).",
      zh: "每组都是一个共享的业务世界，混入了大量\"长得很像\"的干扰记录；场景来自像 [GDPval](https://openai.com/index/gdpval/) 和 [SOP-Bench](https://github.com/amazon-science/SOP-Bench) 这样的真实工作任务源。"
    },
    note: {
      en: "How the hidden rules are planted, how the data is built and graded by agents, and why cost goes down. [**Read the blog →**](blog.html)",
      zh: "隐藏规则怎么埋、数据怎么由 agent 构造与评分、成本为什么会下降，[**阅读博客 →**](blog.html)"
    },
    tableColumns: {
      group: {
        en: "Group",
        zh: "编号"
      },
      domain: {
        en: "Domain",
        zh: "领域"
      },
      focus: {
        en: "Business focus",
        zh: "业务场景"
      }
    },
    detail: {
      heading: {
        en: "Task themes",
        zh: "Task 主题"
      },
      count: {
        en: "5 train · 5 test",
        zh: "5 个 train · 5 个 test"
      },
      taskPrefix: "task",
      sets: [
        {
          kind: "Train",
          label: "train",
          count: "5 examples"
        },
        {
          kind: "Test",
          label: "test",
          count: "5 held-out"
        }
      ]
    }
  }
};
