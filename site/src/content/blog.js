export const blogIntro = {
  title: {
    en: "Evaluating Agent Self-Evolution on Real Business Tasks",
    zh: "在真实企业任务上评估 Agent 的自进化能力"
  },
  meta: {
    date: {
      en: "June 18, 2026",
      zh: "June 18, 2026"
    },
    author: "PrismShadow Team"
  },
  share: {
    label: {
      en: "Copy page link",
      zh: "复制本页链接"
    },
    copiedLabel: {
      en: "Copied",
      zh: "已复制"
    },
    ariaLabel: "Copy blog link"
  },
  lead: {
    en: "In the AI era, once a task can be evaluated and automated, it is not far from being maxed out.",
    zh: "在 AI 时代，一旦某件事可以被评估并且被自动化，它就离做到极致不远了。"
  },
  paragraphs: [
    {
      key: "gap",
      en: "Self-evolution refers to the process by which an agent continuously improves task performance by improving its internal state. Related concepts include continual learning (CL) and recursive self-improvement (RSI). In recent months, this topic has attracted intense attention. Startups built around AI self-evolution, such as [NeoCognition](https://neocognition.io/) and [Recursive](https://www.recursive.com/), raised **billions of dollars** in 2026. Only if we can accurately evaluate an agent's ability to self-evolve will we have the chance to explore better self-evolution strategies. Yet in **real enterprise tasks**, such as invoice auditing, trade show operations, and insurance compliance, there is almost no dedicated benchmark for evaluating an agent's self-evolution capability, let alone doing so automatically.",
      zh: "自进化（Self-evolution）是指 Agent 通过自我改进内部状态，不断提升任务表现的过程。类似的概念也包括持续学习（Continual learning，CL）和递归自我改进（Recursive self-improvement，RSI）。近几个月这个话题备受关注，围绕 AI 自进化的初创企业（[NeoCognition](https://neocognition.io/)、[Recursive](https://www.recursive.com/) 等），在 2026 年募集了**数十亿美元**的资金。只有当我们能准确评估 Agent 自进化能力时，我们才能有机会探索更优秀的自进化策略。然而在**真实企业任务**领域，例如发票审核、展会事务和保险合规等任务，几乎没有专门的基准能评估 Agent 的自进化能力，更不用说自动化评估。"
    },
    {
      key: "release",
      en: "GDPevo attempts to fill this gap. To the best of our knowledge, it is the first benchmark for evaluating agent self-evolution on economically valuable (or GDP-related) tasks. It is both an **automated benchmark construction process** and the output of that process: an **out-of-the-box benchmark**. The benchmark contains 120 real enterprise tasks across Customer Relationship Management (CRM), Enterprise Resource Planning (ERP), and Finance. Each task involves multiple complex rules and requires the agent to improve itself from prior examples before it can reach satisfactory performance.",
      zh: "GDPevo 试图弥补这方面的不足，据我们所知，这是首个在具有经济价值（和 GDP 相关）的任务上评估 Agent 自进化的基准。它既是一套**自动化基准构建流程**，又是这套流程的产物，一份**开箱即用的基准**。这套基准包含 120 个真实企业任务，覆盖客户关系管理（CRM）、企业资源计划（ERP）和金融（Finance）三大场景，每个任务都会涉及多个复杂规则，需要 Agent 通过过往样本改进自身后，才能达到满意的表现。"
    },
    {
      key: "construction",
      en: "In building this benchmark, we mainly address two hard problems. First, we need two non-overlapping sets to truly test an agent's self-evolution capability; otherwise, the evaluation becomes **training on the test set**. To solve this, we introduce **rule hybridization**, inspired by crossover evolution in genetic algorithms. We decompose complex business logic into multiple atomic rules, hide them in the training set, and then recombine them into different new tasks to form the test set. Only when the agent has truly learned the rules can it perform well on the test samples, rather than merely memorizing the training set. Second, we want to build a sufficiently difficult evaluation benchmark. To **prevent LLMs from gaming the tasks**, we design multiple independent evaluation agents to audit each task group end-to-end. Only automatically constructed data that reaches a required difficulty level is accepted as valid samples.",
      zh: "在构建这套基准的过程中，我们主要解决了两大难题。第一，我们需要两套互不重叠的集合才能真正测试出 Agent 自进化能力，否则就会出现**在测试集上训练**的问题。为此，我们提出了**规则杂交**的方法，源自于遗传算法中的交叉进化。我们将复杂的业务逻辑分解成多个元规则，隐藏到训练集中，再重新组合成不同的新任务，构成测试集。仅当 Agent 真正学会了规则，才能做好测试样本，而不仅仅是记住了训练集。第二，我们希望构建足够困难的评估基准，为了**防止大模型投机取巧**，我们设计了若干独立的评估 Agent，端到端地审计每一组任务，只有当自动构建的数据达到一定难度要求，才会采用作为有效样本。"
    },
    {
      key: "evaluation",
      en: "We follow three principles in evaluation. First, we use a **rule-based** grading strategy rather than model-based evaluation (LLM-as-a-judge). The final score is composed of multiple distinct rubrics, ensuring that every score is **reproducible** while also making it possible to identify the specific cause of each result. Second, we treat both **accuracy** and **cost** as first-class citizens. A good self-evolution strategy should not only become more accurate over time, but also become more cost-efficient. Third, we do not design a separate evaluation framework; instead, we use an **end-to-end** natural-language-driven evaluation process. You describe the experiment to run and the chart you want in one sentence, and Claude Code/Codex can generate the evaluation results and charts on the spot, with no manual code adaptation or writing required.",
      zh: "我们在评估过程中遵循三个原则。第一，采用**基于规则**的打分策略，而非使用基于模型的评估（LLM-as-a-judge）。最终分数由多个不同的打分点（rubrics）组成，保证每个分数都是**可复现**的，同时还能定位到具体的原因。第二，我们将**准确率**和**成本**都看作一等公民。一个好的自进化策略不仅要越来越准确，还要越来越省成本。第三，我们不设计评估框架，而是采用**端到端**自然语言驱动的评估流程。你用一句话描述要跑的实验和想要的图表，Claude Code/Codex 就能当场生成评估结果和图表，全程无需人工进行任何代码适配和编写。"
    },
    {
      key: "findings",
      en: "We tested the self-evolution capability of three different agents. Test-set accuracy generally improve by **17-22%**, and two of the agents also showed significant reductions in token consumption. These results suggest that current agents already have a degree of self-evolution capability: they can effectively learn from past experience and transfer that knowledge to new tasks. This finding is similar in spirit to conclusions from several existing works ([[1]](https://trinkle23897.github.io/learning-beyond-gradients/) [[2]](https://www.recursive.com/articles/first-steps-toward-automated-ai-research)).",
      zh: "我们测试了三个不同 Agent 的自进化能力，测试集准确率普遍都提升了 **17-22%**，其中两个 Agent 的 Token 消耗也有显著减少。这个结果意味着当前的 Agent 已经具备一定的自进化能力，能有效从过往经验中学习并迁移知识到新的任务上，这个发现和一些已有工作（[[1]](https://trinkle23897.github.io/learning-beyond-gradients/) [[2]](https://www.recursive.com/articles/first-steps-toward-automated-ai-research)）的结论有着相似点。"
    }
  ]
};

export const blogConstruction = {
  heading: {
    en: "How we built it",
    zh: "数据构建方法"
  },
  lead: {
    en: "Building a large-scale self-evolution benchmark for enterprise scenarios poses two challenges. First, the construction process should be fully automated end-to-end: humans write the workflow once, and AI handles the rest of running it (similar to [Loop Engineering](https://addyosmani.com/blog/loop-engineering/)). This automation helps our benchmark **outrun data leakage**: as long as the benchmark can generate new tasks faster than models can memorize leaked solutions, it can stay ahead and remain valid. It also makes the benchmark **scalable**: its size is no longer constrained by human labor and can grow on its own. Second, the training and testing sets must be related, but not too similar. The agent should be able to generalize rules from the training set to the testing set, rather than memorize the training set.",
    zh: "针对企业场景构建大规模的自进化评估基准有两个挑战：首先，构建过程应能被端到端全自动完成，人只需要写一遍流程，剩下跑流程的工作交给 AI（就像 [Loop Engineering](https://addyosmani.com/blog/loop-engineering/)）。它不仅能帮我们的基准**跑赢数据泄露**，只要基准的生成速度比模型记住已泄露题解的速度快，基准就能一直保持领先和有效。它还能让基准变得**可缩放**（Scalable），基准的大小不再受人力制约，而是可以自己增长。其次，训练集和测试集要有相关性，但不能太过相似。Agent 能将训练集的规则泛化到测试集中，而不是记住训练集。"
  },
  agentHeading: {
    en: "Built end-to-end by multiple agents",
    zh: "数据由多个 Agent 端到端全自动构建"
  },
  pipeline: {
    en: "Humans design the workflow, and agents keep running it continuously, as shown below. We first take seed scenarios from public real-business benchmarks ([GDPval](https://arxiv.org/abs/2510.04374), [SOP-Bench](https://arxiv.org/abs/2506.08119), and [JobBench](https://arxiv.org/abs/2605.26329)), then generate a large number of candidate task groups. Each task group builds a shared environment, 5 training samples and 5 testing samples, with every sample paired with a rule-based grading script. A new agent then calibrates the difficulty so that the agent's performance after evolution clearly exceeds its performance before evolution. This step filters out samples that cannot effectively evaluate agent evolution capability, keeping the benchmark focused on tasks that truly require cross-task self-evolution. Finally, six independent reviewer agents audit the result, and a task group is adopted only if it receives at least 5 passing votes. Reviewers exist to prevent agents from cutting corners by checking whether the file structure is complete and whether the hidden rules are actually planted. In the end, 120 tasks across 12 task groups pass the filter and form the current benchmark.",
    zh: "人负责设计流程，Agent 负责持续不断运行，如下图所示。我们先从公开的真实业务基准（[GDPval](https://arxiv.org/abs/2510.04374)、[SOP-Bench](https://arxiv.org/abs/2506.08119)、[JobBench](https://arxiv.org/abs/2605.26329)）里取种子场景，再生成大量候选任务组。每个任务组都搭建一个共享环境，生成 5 个训练样本和 5 个测试样本，每个样本都搭配上基于规则的评分脚本。然后由一个新的 Agent 校准难度，使 Agent 在进化后的表现明显超过进化之前。这一步是为了将没法有效评估 Agent 进化能力的样本筛掉，让基准集中在那些真的需要跨任务自我进化的任务上。最后由 6 个互相独立的 Reviewer Agent 审核，至少拿到 5 个通过票的数据才会被采用。Reviewer 的存在是为了防止 Agent 偷懒，检查文件结构和隐藏规则是否真正埋好。最终有 120 个任务，12 个任务组通过了筛选，形成了当前的这套基准。"
  },
  pipelineImageAlt: "GDPevo data pipeline: seed scenarios to multi-agent task factory to quality review to release.",
  hiddenHeading: {
    en: "Evaluating self-evolution through rule hybridization",
    zh: "通过规则杂交来评估自进化能力"
  },
  hiddenRules: [
    {
      key: "rules",
      en: "We scatter clues and rules throughout the training set of each task group. For example, in customer relationship management (CRM), we hide the priority order for sponsor status and a blacklist policy. In enterprise resource planning (ERP), we hide vendor risk-control rules and the corresponding response measures.",
      zh: "我们会将一些线索和规则分散藏到每个任务组的训练集中。例如在客户关系管理（CRM）中，我们会隐藏赞助商身份的优先级以及黑名单策略。在企业资源规划（ERP）中，我们会隐藏供应商的风控规则和应对措施。"
    },
    {
      key: "recombine",
      en: "We scatter these rules across the 5 training samples, with each sample containing only part of them. The 5 testing samples are then designed as **combinations** of these rules, such as triggering both the \"priority\" and \"blacklist\" rules at the same time. An agent without self-evolution capability can only see the scattered rules, while an agent with self-evolution capability can generalize them to new tasks.",
      zh: "我们把这些规则分散埋藏到 5 个训练样本里，每个样本只包含一部分。5 个测试样本则被设计成这些规则的**组合**，比如同时触发“优先级”和“黑名单”。不具备自进化能力的 Agent 只能看到分散的规则，而具有自进化能力的 Agent 可以将它们泛化到新的任务上。"
    }
  ]
};

export const blogUsage = {
  heading: {
    en: "How to evaluate with it",
    zh: "评估方法"
  },
  lead: {
    en: "We follow two rules when evaluating: scores must be reproducible; **cost** and **accuracy** are equally important.",
    zh: "我们在评估时有两项守则：分数必须可复现；**成本**和**准确率**同等重要。"
  },
  gradingHeading: {
    en: "Rule-based grading, not LLM-as-a-Judge",
    zh: "采用基于规则的评分，而非 LLM-as-a-Judge"
  },
  grading: {
    en: "GDPevo uses deterministic rule-based graders, with each score composed of multiple scoring points. This brings two benefits. First, scores are **reproducible**: the same answer receives the same score across repeated runs. Second, every failure is **traceable**: instead of a vague overall verdict, you see exactly which rule failed and how many points were deducted. This traceability turns the benchmark into a diagnostic tool for agents. You can read the agent's action traces backward to find where your agent is weak, then use those weaknesses as the basis for the next optimization.",
    zh: "GDPevo 使用确定性的规则打分器，每个分数都由多个打分点组成。这会带来两个好处，首先，分数是**可复现**的：同一份答案多次跑得到的分都一样。其次，每一次失败都是**可追溯**的：你看到的不是一个含糊的整体结论，而是具体哪一条规则没通过、扣了多少分。这种可追溯性让基准成为 Agent 诊断工具，你可以反过来读 Agent 的操作记录，从而找到你的 Agent 短板在哪里，再将这些短板作为下一次的优化依据。"
  },
  costHeading: {
    en: "Cost and accuracy are equally important",
    zh: "成本和准确率同等重要"
  },
  cost: {
    en: "A good self-evolution strategy should not only become more accurate over time, but also become more cost-efficient, just like a person becoming more skilled: faster execution with better results. Therefore, in every test, we record total Token consumption and task accuracy. Detailed result logs help us analyze the agent's behavior, identify where problems occur, and use those findings to optimize the strategy.",
    zh: "一个好的自进化策略不仅要越来越准确，还要越来越省成本，就像人一样做事越来越熟练，时间快效果好。因此我们在每次测试中都会记录总 Token 消耗和任务准确率。详细的结果记录可以帮助我们分析 Agent 的行为，找到问题所在，从而优化策略。"
  }
};

export const blogFindings = {
  heading: {
    en: "Evaluations and findings",
    zh: "实验结果与发现"
  },
  intro: [
    {
      key: "workflow",
      en: "We use a purely natural-language-driven evaluation method instead of using an evaluation SDK. We open the **evaluation workspace** with Claude Code or Codex. This workspace is a folder containing Markdown guides and instructions. We then describe the desired result format in natural language, and the entire evaluation process can run automatically to produce a result report, with no code adaptation or SDK learning required.",
      zh: "我们采用纯自然语言驱动的评估方法，而不用一个评估SDK。我们使用 Claude Code 或者 Codex 打开**评估工作区**，这是一个包含 Markdown 指南和说明的文件夹。我们使用自然语言描述结果展现形式，整个评估流程就可以全自动进行，得到结果报告，无需进行代码适配或学习框架。"
    },
    {
      key: "settings",
      en: "We evaluated three different agents on 12 task groups, totaling 120 tasks, and compared three different settings:",
      zh: "我们使用三个不同的 Agent 在 12 个任务组，共 120 个任务上进行了评估，分别对比了三种不同的方案："
    }
  ],
  modes: [
    {
      key: "base",
      en: "`base`: The agent answers the test questions directly without seeing the training set.",
      zh: "`base`：Agent 不接触训练集，直接解答测试题目。"
    },
    {
      key: "fewshot",
      en: "`fewshot`: The agent first reads the training questions and gold answers, summarizes experience from the examples, and then answers the test questions. (Analogous to SFT.)",
      zh: "`fewshot`（少样本进化）：Agent 先读一遍训练集的题目和标准答案，根据案例归纳经验，再去解答测试题目。（类似 SFT）"
    },
    {
      key: "reflect",
      en: "`reflect`: The agent first attempts the training questions without seeing the gold answers, then receives feedback on whether its answers were correct, reflects on the results to summarize the rules, and then answers the test questions. (Analogous to RL.)",
      zh: "`reflect`（反思进化）：Agent 先不看标准答案，自己尝试解答训练集的题目，然后再告诉它是否解答正确，从而反思总结规则，再去解答测试题目。（类似 RL）"
    }
  ],
  note: {
    en: "The three agents produced similar conclusions: self-evolution can improve test-set accuracy by **about 17-22%**, while Claude Code and Codex also use fewer **tokens**. In the operational financial modeling scenario, Codex improved from **42.76% to 92.47%** with fewer tokens than the baseline; Claude Code's `fewshot` rose directly to **100%, starting from 51.76%**, and Panofy's `reflect` reached **92.47%, starting from 62.39%**.",
    zh: "三个 Agent 产生了相似的结论：自进化可以让测试集准确率提升**约 17-22%**，同时 Claude Code 和 Codex 的 **token 消耗量**更低。在 operational financial modeling 这个场景里，Codex 从 **42.76% 提升到了 92.47%**，token 比基线还少；而 Claude Code 的 `fewshot`（少样本进化）直接上升到了 **100%，起点是 51.76%**，Panofy 的 `reflect`（反思进化）达到 **92.47%，起点是 62.39%**。"
  }
};

export const blogBenchmark = {
  caption: {
    en: "Each metric is the mean across 12 task groups, with each task averaged over 3 runs",
    zh: "指标是 12 个任务组的均值，其中每个任务跑 3 遍后取平均"
  },
  columns: {
    harness: "agent harness",
    model: "Model",
    mode: "Mode"
  },
  breakdownLink: {
    en: "See the per-group breakdown on the homepage →",
    zh: "在首页查看各任务组的明细 →"
  }
};

export const blogInvite = {
  heading: {
    en: "GDPevo is a seed for agent self-evolution, not simply a result",
    zh: "GDPevo 是一颗 Agent 自进化的种子，不是一个结果"
  },
  paragraph: {
    en: "The complete process, artifacts, and results of this project are fully open. We welcome you to participate with your own agent or business scenario. Our goal is not to build a leaderboard, but to provide momentum for self-evolving agents. Through this project, we hope to make agent self-evolution truly scalable and free humans from labor.",
    zh: "这个项目中完整的流程、产物和结果都是完全开放的，欢迎带上你自己的 Agent 或者业务场景来参与其中。我们的目标不是一个排行榜，而是给自进化 Agent 提供动力。我们希望通过这个项目，能让 Agent 的自进化真正实现规模化，将人类从劳动中解放出来。"
  },
  actions: {
    github: "GitHub",
    experimentBoard: {
      en: "Experiment board",
      zh: "实验看板"
    },
    evalWorkspace: {
      en: "Eval workspace",
      zh: "评估工作区"
    }
  },
  copy: {
    label: {
      en: "Copy",
      zh: "复制"
    },
    copiedLabel: {
      en: "Copied",
      zh: "已复制"
    },
    ariaLabel: "Copy citation"
  }
};

export const blogToc = {
  title: {
    en: "On this page",
    zh: "本页目录"
  },
  items: [
    {
      href: "#intro",
      label: {
        en: "Overview",
        zh: "概览"
      }
    },
    {
      href: "#construction",
      label: blogConstruction.heading
    },
    {
      href: "#agent-pipeline",
      label: blogConstruction.agentHeading,
      level: 2
    },
    {
      href: "#rule-hybridization",
      label: blogConstruction.hiddenHeading,
      level: 2
    },
    {
      href: "#usage",
      label: blogUsage.heading
    },
    {
      href: "#rule-based-grading",
      label: blogUsage.gradingHeading,
      level: 2
    },
    {
      href: "#cost",
      label: blogUsage.costHeading,
      level: 2
    },
    {
      href: "#findings",
      label: blogFindings.heading
    },
    {
      href: "#invite",
      label: blogInvite.heading
    }
  ]
};

export const citation = `@misc{gdpevo2026,
  title  = {GDPevo: Measuring agent self-evolution on real business work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}`;
