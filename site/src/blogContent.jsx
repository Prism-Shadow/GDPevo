export const blogIntro = {
  title: {
    en: "Measuring Agent Self-Evolution on Real Business Work",
    zh: "在真实业务工作上衡量 Agent 的自我进化"
  },
  lead: {
    en: "In the AI era, once a task can be measured and automated, it is not far from being maxed out.",
    zh: "在 AI 时代，一旦一个任务可以被衡量并自动化，它离被做到极致就不远了。"
  },
  paragraphs: [
    {
      key: "gap",
      en: (
        <>
          Self-evolution means agents rewrite their own memory, procedures, or harness to get better at a class of tasks over time. It is a problem the field clearly cares about.
          Companies built around agentic self-improvement (Cognition, Reflection AI, and others) have raised on the order of <strong>billions of dollars</strong> in 2025 alone.
          Yet on <strong>real productivity work</strong>, such as auditing AP invoices, reconciling event sponsorship across CRM and finance, or building a branch close-out package, there is essentially <em>no benchmark</em> for whether an agent can actually self-evolve.
          It can't be measured today, let alone measured automatically.
        </>
      ),
      zh: (
        <>
          Self-evolution 指 agent 通过自己改写 memory、procedure 或 harness，在一类任务上越做越好。这是一个业界很关注的问题。
          围绕 agent 自我进化的公司（Cognition、Reflection AI 等）仅 2025 一年就募集了约 <strong>数十亿美元</strong>的资金。
          然而在<strong>真实生产力工作</strong>这一面，比如审核 AP 发票、把展会赞助在 CRM 和财务两边对账、做一个分行月度结账包，几乎<em>没有 benchmark</em>能告诉我们 agent 到底有没有 self-evolve。
          目前它根本测不了，更谈不上自动化测。
        </>
      )
    },
    {
      key: "release",
      en: (
        <>
          GDPevo fills that gap.
          It is both a <strong>process</strong> for automatically building self-evolution benchmarks on real-job tasks, and a released <strong>benchmark</strong> produced by that process: twelve task groups across CRM, ERP, and Finance, each with five train tasks and five test tasks under a shared environment and rule-based graders.
          The construction-and-evaluation pipeline is shown in later sections.
        </>
      ),
      zh: (
        <>
          GDPevo 就是来补这个 gap 的。
          它既是一套<strong>流程</strong>，在真实业务任务上自动化地构建 self-evolution benchmark；也是这套流程的产物，一份<strong>已发布的 benchmark</strong>：12 组 task group，覆盖 CRM、ERP、Finance，每组 5 个 train + 5 个 test，共享同一个环境，用基于规则的 grader 打分。
          构建与评估的整体流程在后续章节中展示。
        </>
      )
    },
    {
      key: "construction",
      en: (
        <>
          Automating the construction and evaluation of productivity-flavored datasets has two hard problems on the construction side.
          <strong> First</strong>, train and test must be cleanly separated so the agent can actually <em>evolve</em> on train and have that change <em>show up</em> on test. Many existing benchmarks fail this and end up training and testing on the same set.
          We solve it with <strong>Hidden Rules</strong>: operational rules are planted across the train tasks in pieces and recombined on the test, so a passing score requires real abstraction, not memorization.
          <strong> Second</strong>, LLMs are lazy: they declare victory while quietly skipping work.
          We add a <strong>review mechanism</strong>: a panel of independent reviewer agents audits each task group end-to-end, and a group only ships when the reviewers confirm everything was actually delivered.
        </>
      ),
      zh: (
        <>
          在生产力相关的数据集上做自动化构建与评估，<em>构建</em>侧有两大难点。
          <strong>第一</strong>，必须把 train 和 test 干净地分开，让模型真的能在 train 后<em>发生进化</em>，并且在 test 上<em>体现</em>出来。很多现有 benchmark 就是没做到这点，最后在 train 上训、在 train 上测。
          我们用<strong>Hidden Rules</strong>来解决这个问题：把业务规则拆散埋进 train，再在 test 上重新组合，要拿分就必须真的把规则抽象出来，而不是死记硬背。
          <strong>第二</strong>，大模型会偷懒，经常嘴上说"做完了"实际跳过了步骤。
          我们加了一套 <strong>review 机制</strong>：由若干独立的 reviewer agent 端到端审计每一组任务，所有内容确认交付了，这一组才会放行。
        </>
      )
    },
    {
      key: "evaluation",
      en: (
        <>
          In addition, our evaluation makes three commitments.
          <strong> One</strong>, grading is <strong>rule-based</strong>, not LLM-as-a-judge. Every score is reproducible and every failure points to a specific rule.
          <strong> Two</strong>, both <strong>cost</strong> and <strong>accuracy</strong> are first-class citizens. A useful agent isn't just one that gets the right answer, it's one that gets there <em>more cheaply</em> over time.
          <strong> Three</strong>, the workspace is <strong>natural-language driven</strong>. You describe the experiment and the chart you want in one sentence, and a coding agent generates the analysis on the fly; you don't write code yourself.
        </>
      ),
      zh: (
        <>
          在评估侧，我们坚持三件事。
          <strong>第一</strong>，<strong>规则化打分</strong>，不用 LLM-as-a-judge。每一个分都是可复现的，每一次失败都能定位到具体的规则。
          <strong>第二</strong>，<strong>cost</strong> 与 <strong>accuracy</strong> 同为一等公民。一个好用的 agent 不仅要答得对，还要随时间推移、用<em>更少的代价</em>把题做出来。
          <strong>第三</strong>，工作区<strong>由自然语言驱动</strong>。你用一句话描述要跑的实验和想要的图表，一个 coding agent 当场生成分析代码出图；你自己不需要写代码。
        </>
      )
    },
    {
      key: "findings",
      en: (
        <>
          We close with evaluation and findings.
          On all three agent harnesses we tested, self-evolution lifts held-out accuracy by <strong>+17 to +22 points</strong>; on two of them token usage actually goes <em>down</em>, not up. This points to fluency, not just a higher score.
          Below, we walk through how this benchmark is built, and how it is used.
        </>
      ),
      zh: (
        <>
          最后是 evaluation 和 findings。
          在我们测的三套 agent harness 上，self-evolution 都把 held-out 准确率提升了 <strong>+17 到 +22 个百分点</strong>；其中两套 harness 上 token 消耗不增<em>反降</em>。这说明 agent 变得更熟练，而不只是分数变高。
          下面我们就来看看这个 benchmark 是怎么被构建出来的，以及怎么使用。
        </>
      )
    }
  ]
};

export const blogConstruction = {
  heading: {
    en: "How we built it.",
    zh: "我们怎么构建。"
  },
  lead: {
    en: (
      <>
        Building a self-evolution benchmark for real business work poses two challenges.
        <strong> First</strong>, the construction should be agent-driven end-to-end: humans write the procedure once, agents do the rest.
        This matters for two reasons.
        It helps the benchmark <em>outrun data leakage</em>: as long as agents can spawn fresh tasks faster than models absorb the leaked ones, the benchmark stays ahead.
        It also lets the benchmark <em>scale</em>: when agents both build and evaluate, the loop is closed, with no human bottleneck, and the benchmark can keep growing on its own.
        <strong> Second</strong>, train and test have to be related but not redundant: the train tasks must teach a real, hidden lesson that pays off only when the lesson is extracted, not memorized.
      </>
    ),
    zh: (
      <>
        为真实业务工作构建一个 self-evolution benchmark，有两个 challenge。
        <strong>第一</strong>，构建过程应该是 agent 端到端跑出来的：人只把流程写一次，剩下交给 agent。
        这件事之所以重要有两个原因。
        它能帮 benchmark <em>跑赢数据泄露</em>：只要 agent 生成新题的速度比模型吸收已泄露题的速度快，benchmark 就一直保持领先。
        它也让 benchmark 能<em>真正 scale</em>：当 agent 既负责构造、又负责评测，整个回路就闭合了，没有人力瓶颈，benchmark 可以自己长大。
        <strong>第二</strong>，train 和 test 要相关、但不能冗余：train 必须真的"教"一个隐藏的规则，这个规则只有被抽象出来才会在 test 上派上用场，而不是被死记下来。
      </>
    )
  },
  agentHeading: {
    en: "Built end-to-end by agents.",
    zh: "从头到尾，全部由 agent 完成。"
  },
  pipeline: {
    en: (
      <>
        Humans wrote the pipeline once.
        After that, agents do everything (illustrated below).
        They pull seed scenarios from public real-job benchmarks (GDPval, SOP-Bench, JobBench) and spawn many candidate task groups from those seeds.
        For each group, they build a shared environment and author 5 train + 5 test tasks with rule-based evaluators.
        A calibrator then tunes difficulty so that an <code>evolution</code> setup clearly beats a <code>no-evolution</code> setup. This filters out tasks where evolution wouldn't change the answer, keeping the benchmark focused on agents that actually have to evolve across related work.
        Finally, six independent reviewer agents audit the result, and a group ships only when 5 of 6 pass. These reviewers exist because agents have a habit of declaring victory while quietly skipping work, so completeness, file presence, and planted hidden rules are exactly what gets checked.
        Twelve task groups make it through this filter and form the public release.
      </>
    ),
    zh: (
      <>
        人只写一次 pipeline，之后全靠 agent（如下图所示）。
        先从公开的真实业务 benchmark（GDPval、SOP-Bench、JobBench）里取种子场景，再据此 spawn 出大量候选 task group。
        每组里搭一个共享 env，写 5 个 train + 5 个 test 任务并配上基于规则的 evaluator。
        然后 calibrator 调难度，让 <code>evolution</code> 设定明显超过 <code>no-evolution</code> 设定。这一步是为了把那些"是否进化都不影响答案"的题筛掉，让 benchmark 集中在那些真的需要跨相关任务自我进化的 agent 上。
        最后由 6 个互相独立的 reviewer agent 审核，6 个里 5 个通过这一组才放行。之所以要 reviewer，是因为 agent 经常嘴上说"做完了"、实际偷懒，所以审核的就是结构、完整性、文件是否齐全、隐藏规则是否真的埋了进去。
        最终通过这层筛选活下来、进入公开发布的，是 12 组 task group。
      </>
    )
  },
  hiddenHeading: {
    en: "Hidden rules, spread across the train tasks.",
    zh: "隐藏规则，分散到各个 train task 里。"
  },
  hiddenRules: [
    {
      key: "rules",
      en: (
        <>
          For every task group we plant a small set of hidden operational rules.
          A CRM lead-capture group might encode a <em>sponsor-status precedence rule</em> (finance invoices outrank badge scans) and a <em>suppression-list policy</em> (don't contact certain segments).
          A procurement-readiness group enforces that <em>open vendor-risk events and AP holds force a "held" line</em>, regardless of how clean the PO looks.
        </>
      ),
      zh: (
        <>
          每个 task group 我们都会埋一小组隐藏的业务规则。
          CRM 销售线索组可能埋了两条：<em>赞助商身份的优先级</em>（财务发票优先于胸卡扫描），以及 <em>suppression list 政策</em>（某些细分人群禁止联系）。
          采购就绪组则要求：<em>只要供应商有 open 的 risk event 或 AP hold，对应行就必须 held</em>，不管 PO 看起来多干净。
        </>
      )
    },
    {
      key: "recombine",
      en: (
        <>
          We <em>spread</em> these rules across the 5 train tasks, so each train task only exercises a subset.
          The 5 test tasks are deliberately built as <strong>combinations</strong>, say, the precedence rule together with the suppression policy.
          An agent that solves each train in isolation only sees rule fragments.
          An agent that turns them into an evolution update has them all in one place; when the test asks for two at once, it doesn't need to rediscover them.
          That's why a higher test score is real evidence of evolution, not luck.
        </>
      ),
      zh: (
        <>
          我们把这些规则<em>分散</em>到 5 个 train 里，每个 train 只触发一部分。
          5 个 test 故意被设计成这些规则的<strong>组合</strong>，比如同时触发"优先级 + suppression"。
          只盯着单个 train 做的 agent 看到的是碎片；能把这些规则转成一次 evolution update 的 agent，则把它们放在一处。test 同时问两条时，它不需要重新发现。
          这就是 test 分数变高的原因，是真的发生了进化，而不是运气。
        </>
      )
    }
  ]
};

export const blogUsage = {
  heading: {
    en: "How to evaluate with it.",
    zh: "怎么用它做评估。"
  },
  lead: {
    en: (
      <>
        Two things we want from an evaluation harness: it should grade in a way you can audit; and it should treat <em>cost</em> as a first-class citizen alongside accuracy.
        Each one motivated a specific design.
      </>
    ),
    zh: (
      <>
        我们对评估 harness 有两个要求：评分必须可被人审计；<em>cost</em> 要和 accuracy 同等重要。
        下面两块就是为了满足这两个要求。
      </>
    )
  },
  gradingHeading: {
    en: 'Rule-based grading, not "ask another LLM".',
    zh: '基于规则的评分，而不是"再叫一个 LLM 来判"。'
  },
  grading: {
    en: (
      <>
        GDPevo grades with deterministic, rule-based checkers. For example, was the right set of records returned, did the amount round to the right precision.
        Two things follow.
        First, the score is <strong>reproducible</strong>: the same answer always gets the same grade, regardless of who runs it or when.
        Second, every failure is <strong>traceable</strong>: instead of a vague verdict, you see exactly which rule was violated and by how much.
        That trace is what makes the benchmark useful for diagnosis: you can read it back to find weak spots in your agent and feed those weak spots into the next round of memory or procedure updates.
      </>
    ),
    zh: (
      <>
        GDPevo 用确定性的 rule-based checker 打分，比如返回的记录集对不对、金额是否遵守了要求的精度。
        这带来两个好处。
        第一，评分是<strong>可复现</strong>的：同一份答案，谁跑、什么时候跑，得到的分都一样。
        第二，每一次失败都是<strong>可追溯</strong>的：你看到的不是一个含糊的整体结论，而是具体哪一条规则被违反、扣了多少分。
        这种可追溯性让 benchmark 成为诊断工具：你可以反过来读这些 trace，找到你的 agent 短板在哪儿，再把这些短板喂回下一轮 memory 或 procedure 更新。
      </>
    )
  },
  costHeading: {
    en: "Cost and accuracy, both first-class.",
    zh: "cost 和 accuracy 都是一等公民。"
  },
  cost: {
    en: (
      <>
        A useful agent isn't just one that gets the right answer. It is one that <em>stops redoing</em> the same legwork every time a similar task comes in.
        Self-evolution should look like a human getting fluent: more accurate <em>and</em> faster, with fewer tokens, fewer steps, and cleaner moves.
        So we instrument every run end-to-end: per-agent total token spend, plus a breakdown by reasoning, tool calls, and stage.
        That observability isn't only for our analysis; those traces also become raw material for the agent's next evolution update.
      </>
    ),
    zh: (
      <>
        一个有用的 agent 不仅要答得对，还得<em>不再每次都把同样的活儿重做一遍</em>。
        Self-evolution 应该像人变熟练：更准、<em>更快</em>，用更少的 token、更少的步数、更干净的做法。
        所以我们对每一次运行都做端到端打点：每个 agent 的总 token 消耗，以及按 reasoning、工具调用、不同阶段的 breakdown。
        这套 observability 不只服务我们自己的分析，这些 trace 本身也是 agent 下一次 self-evolve 的材料。
      </>
    )
  }
};

export const blogFindings = {
  heading: {
    en: "Evaluations and findings.",
    zh: "实测与结果。"
  },
  intro: [
    {
      key: "workflow",
      en: (
        <>
          Every run below was driven by natural language: we pointed a coding agent (Codex or Claude Code) at the evaluation workspace, a folder of plain Markdown guides, prompts, and directory conventions, typed one sentence describing the experiment and the chart we wanted, and the agent generated the analysis code, called the graders, and wrote the report.
          No hand-written harness, no SDK to learn.
        </>
      ),
      zh: (
        <>
          下面这些实验都是用自然语言驱动跑出来的：我们把一个 coding agent（Codex 或 Claude Code）指向评估工作区，也就是一个装满纯 Markdown 指南、prompt 和目录约定的文件夹；用一句话说清要跑什么实验、想要什么样的图，agent 就会自己生成分析代码、调 grader、写 report。
          没有手写的 harness，也没有要学的 SDK。
        </>
      )
    },
    {
      key: "settings",
      en: "We ran the same 12 task groups under three settings, on three different agent harnesses:",
      zh: "我们在同样的 12 组 task group 上跑了三种设定，跨三套不同的 agent harness："
    }
  ],
  modes: [
    {
      key: "base",
      en: (
        <>
          <code>base</code>: the agent solves the 5 test tasks cold, with no prior exposure to the 5 train tasks.
        </>
      ),
      zh: (
        <>
          <code>base</code>：agent 直接做 5 个 test，没接触过 5 个 train。
        </>
      )
    },
    {
      key: "demo",
      en: (
        <>
          <code>demo</code>: the agent reads the 5 train tasks <em>with their gold answers</em> first, turns them into an evolution update, and then takes the test. (Analogous to SFT.)
        </>
      ),
      zh: (
        <>
          <code>demo</code>：agent 先读 5 个 train 的题目和<em>标准答案</em>，把它们转成一次 evolution update，再去做 test。（类似 SFT。）
        </>
      )
    },
    {
      key: "reflect",
      en: (
        <>
          <code>reflect</code>: the agent attempts the 5 train tasks <em>without</em> seeing answers, gets back graded reward and feedback, updates its memory or procedure from what it got wrong, then takes the test. (Analogous to RL.)
        </>
      ),
      zh: (
        <>
          <code>reflect</code>：agent <em>看不到答案</em>，自己做 5 个 train，事后拿到 reward 和反馈，更新自己的 memory 或 procedure，再去做 test。（类似 RL。）
        </>
      )
    }
  ],
  note: {
    en: (
      <>
        The shape is the same on all three harnesses: self-evolution lifts held-out accuracy by <strong>~17–22 points</strong>, and on the GPT-5.5 / Opus 4.8 setups tokens go <em>down</em>, not up. This is the fluency story, not just a higher score.
        On one task group (operational financial modeling), Codex went from <strong>42.76% to 92.47%</strong> with fewer tokens than the baseline; on the same group, Claude Code's <code>demo</code> reached <strong>100%, up from 51.76%</strong>.
      </>
    ),
    zh: (
      <>
        三套 harness 形状一致：self-evolution 让 held-out 准确率提升 <strong>约 17–22 个百分点</strong>，且在 GPT-5.5 / Opus 4.8 这两套上，<em>花的 token 反而更少</em>。这正是"变熟练"，而不仅仅是分数更高。
        在 operational financial modeling 这一组上，Codex 从 <strong>42.76% 升到 92.47%</strong>，token 比基线还少；同一组上，Claude Code 的 <code>demo</code> 直接到了 <strong>100%，起点是 51.76%</strong>。
      </>
    )
  }
};

export const blogInvite = {
  heading: {
    en: "GDPevo is a seed, not a finished product.",
    zh: "GDPevo 是一颗种子，不是一件成品。"
  },
  paragraph: {
    en: (
      <>
        The tasks, environments, graders, generated updates, and full reports are open.
        Bring your own agents and scenarios.
        Submit harder hidden rules.
        The goal is not a leaderboard, but a public interface where agents that actually do productive work can be trained, with evidence of that improvement open to inspection.
      </>
    ),
    zh: (
      <>
        任务、环境、grader、生成的更新、完整 report 都是开放的。
        欢迎带上你自己的 agent、你自己的业务场景，欢迎来挑战、欢迎提交更难的隐藏规则。
        我们的目标不是一张 leaderboard，而是一个公共接口：让真正能干生产力工作的 agent 在这里被训练出来，并且这种"它真的变好了"的证据可以被任何人审计。
      </>
    )
  }
};

export const citation = `@misc{gdpevo2026,
  title  = {GDPevo: Measuring Agent Self-Evolution on Real Business Work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}`;
