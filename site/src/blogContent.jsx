export const blogIntro = {
  title: {
    en: "Measuring Agent Self-Evolution on Real Business Work",
    zh: "在真实业务工作上衡量 Agent 的自我进化"
  },
  lead: {
    en: "In the AI era, once something can be evaluated and that evaluation can be automated, the problem is essentially solved. Better evaluation begets better agents; better agents in turn drive sharper evaluation — and the loop converges fast.",
    zh: "在 AI 时代，一件事如果能被评估，并且评估可以被自动化，那它基本上就已经被解决了。更好的评估孕育更好的 agent，更好的 agent 又反过来推动更精细的评估——这个循环收敛得很快。"
  },
  paragraphs: [
    {
      key: "gap",
      en: (
        <>
          Self-evolution — agents that rewrite their own memory, procedures, or harness to get better at a class of tasks over time — is a problem the field clearly cares about.
          Companies built around agentic self-improvement (Cognition, Reflection AI, and others) have raised on the order of <strong>billions of dollars</strong> in 2025 alone.
          Yet on <strong>real productivity work</strong> — auditing AP invoices, reconciling event sponsorship across CRM and finance, building a branch close-out package — there is essentially <em>no benchmark</em> for whether an agent can actually self-evolve.
          It can't be measured today, let alone measured automatically.
        </>
      ),
      zh: (
        <>
          Self-evolution——agent 通过自己改写 memory、procedure 或 harness，在一类任务上越做越好——是一个业界很关注的问题。
          围绕 agent 自我进化的公司（Cognition、Reflection AI 等）仅 2025 一年就募集了约 <strong>数十亿美元</strong>的资金。
          然而在<strong>真实生产力工作</strong>这一面——审核 AP 发票、把展会赞助在 CRM 和财务两边对账、做一个分行月度结账包——几乎<em>没有 benchmark</em>能告诉我们 agent 到底有没有 self-evolve。
          目前它根本测不了，更谈不上自动化测。
        </>
      )
    },
    {
      key: "release",
      en: (
        <>
          GDPevo fills that gap.
          It is both a <strong>process</strong> for automatically building self-evolution benchmarks on real-job tasks, and a released <strong>benchmark</strong> produced by that process — twelve task groups across CRM, ERP, and Finance, each with five train tasks and five test tasks under a shared environment and rule-based graders.
          The construction-and-evaluation pipeline is shown in later sections.
        </>
      ),
      zh: (
        <>
          GDPevo 就是来补这个 gap 的。
          它既是一套<strong>流程</strong>——在真实业务任务上自动化地构建 self-evolution benchmark；也是这套流程的产物，一份<strong>已发布的 benchmark</strong>——12 组 task group，覆盖 CRM、ERP、Finance，每组 5 个 train + 5 个 test，共享同一个环境，用基于规则的 grader 打分。
          构建与评估的整体流程在后续章节中展示。
        </>
      )
    },
    {
      key: "construction",
      en: (
        <>
          Automating the construction and evaluation of productivity-flavored datasets has two hard problems on the construction side.
          <strong> First</strong>, train and test must be cleanly separated so the agent can actually <em>evolve</em> on train and have that change <em>show up</em> on test — many existing benchmarks fail this and end up training and testing on the same set.
          We solve it with <strong>Hidden Rules</strong>: operational rules are planted across the train tasks in pieces and recombined on the test, so a passing score requires real abstraction, not memorization.
          <strong> Second</strong>, LLMs are lazy — they declare victory while quietly skipping work.
          We add a <strong>review mechanism</strong>: a panel of independent reviewer agents audits each task group end-to-end, and a group only ships when the reviewers confirm everything was actually delivered.
        </>
      ),
      zh: (
        <>
          在生产力相关的数据集上做自动化构建与评估，<em>构建</em>侧有两大难点。
          <strong>第一</strong>，必须把 train 和 test 干净地分开，让模型真的能在 train 后<em>发生进化</em>，并且在 test 上<em>体现</em>出来——很多现有 benchmark 就是没做到这点，最后在 train 上训、在 train 上测。
          我们用<strong>Hidden Rules</strong>来解决这个问题：把业务规则拆散埋进 train，再在 test 上重新组合，要拿分就必须真的把规则抽象出来，而不是死记硬背。
          <strong>第二</strong>，大模型会偷懒——经常嘴上说"做完了"实际跳过了步骤。
          我们加了一套 <strong>review 机制</strong>：由若干独立的 reviewer agent 端到端审计每一组任务，所有内容确认交付了，这一组才会放行。
        </>
      )
    },
    {
      key: "evaluation",
      en: (
        <>
          In addition, our evaluation makes three commitments.
          <strong> One</strong>, grading is <strong>rule-based</strong>, not LLM-as-a-judge — every score is reproducible and every failure points to a specific rule.
          <strong> Two</strong>, both <strong>cost</strong> and <strong>accuracy</strong> are first-class citizens — a useful agent isn't just one that gets the right answer, it's one that gets there <em>more cheaply</em> over time.
          <strong> Three</strong>, the workspace is <strong>natural-language driven</strong> — you describe the experiment and the chart you want in one sentence, and a coding agent generates the analysis on the fly; you don't write code yourself.
        </>
      ),
      zh: (
        <>
          在评估侧，我们坚持三件事。
          <strong>第一</strong>，<strong>规则化打分</strong>，不用 LLM-as-a-judge——每一个分都是可复现的，每一次失败都能定位到具体的规则。
          <strong>第二</strong>，<strong>cost</strong> 与 <strong>accuracy</strong> 同为一等公民——一个好用的 agent 不仅要答得对，还要随时间推移、用<em>更少的代价</em>把题做出来。
          <strong>第三</strong>，工作区<strong>由自然语言驱动</strong>——你用一句话描述要跑的实验和想要的图表，一个 coding agent 当场生成分析代码出图；你自己不需要写代码。
        </>
      )
    },
    {
      key: "findings",
      en: (
        <>
          We close with evaluation and findings.
          On all three agent harnesses we tested, self-evolution lifts held-out accuracy by <strong>+17 to +22 points</strong>; on two of them token usage actually goes <em>down</em>, not up — fluency, not just a higher score.
          Below, we walk through how this benchmark is built, and how it is used.
        </>
      ),
      zh: (
        <>
          最后是 evaluation 和 findings。
          在我们测的三套 agent harness 上，self-evolution 都把 held-out 准确率提升了 <strong>+17 到 +22 个百分点</strong>；其中两套 harness 上 token 消耗不增<em>反降</em>——变得更熟练，不止是分数变高。
          下面我们就来看看这个 benchmark 是怎么被构建出来的，以及怎么使用。
        </>
      )
    }
  ]
};
