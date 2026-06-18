import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { harnesses, modes, resultGroups, summaryCards, taskGroups, taskTopics } from "./data.js";

function initialLang() {
  try {
    const saved = localStorage.getItem("gdpevo-lang");
    if (saved === "en" || saved === "zh") return saved;
  } catch (e) {
    // Ignore storage access errors in restricted browser contexts.
  }
  return navigator.language && navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
}

function initialThemeChoice() {
  try {
    const saved = localStorage.getItem("gdpevo-theme");
    if (saved === "light" || saved === "dark" || saved === "system") return saved;
  } catch (e) {
    // Ignore storage access errors in restricted browser contexts.
  }
  return "system";
}

function resolveTheme(choice) {
  if (choice !== "system") return choice;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function Lang({ en, zh }) {
  return (
    <>
      <span className="lang-en">{en}</span>
      <span className="lang-zh">{zh}</span>
    </>
  );
}

function BrandLogo() {
  return (
    <span className="brand-logo" aria-hidden="true">
      <svg viewBox="0 0 28 28" width="22" height="22" fill="none">
        <path d="M4 20 L11 11 L16 16 L24 6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="24" cy="6" r="2.4" fill="currentColor" />
      </svg>
    </span>
  );
}

function GitHubIcon({ size = 20 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" aria-hidden="true">
      <path d="M12 .5A11.5 11.5 0 0 0 .5 12a11.5 11.5 0 0 0 7.86 10.92c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.34-1.3-1.7-1.3-1.7-1.06-.72.08-.71.08-.71 1.17.08 1.79 1.2 1.79 1.2 1.04 1.79 2.73 1.27 3.4.97.1-.76.41-1.27.74-1.56-2.56-.29-5.26-1.28-5.26-5.71 0-1.26.45-2.3 1.19-3.11-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.19a11 11 0 0 1 5.8 0c2.2-1.5 3.17-1.19 3.17-1.19.63 1.59.23 2.76.11 3.05.74.81 1.19 1.85 1.19 3.11 0 4.44-2.7 5.42-5.27 5.7.42.37.8 1.09.8 2.2v3.26c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12 11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  );
}

function NavIcon({ name }) {
  if (name === "chart") {
    return (
      <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true">
        <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" strokeLinecap="round" />
      </svg>
    );
  }
  if (name === "blog") {
    return (
      <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true">
        <path d="M4 5h16M4 12h16M4 19h10" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true">
      <path d="m8 6-5 6 5 6M16 6l5 6-5 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ThemeIcon({ choice }) {
  if (choice === "light") {
    return (
      <svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true">
        <circle cx="12" cy="12" r="4.2" />
        <path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4M18.8 5.2l-1.4 1.4M6.6 17.4l-1.4 1.4" strokeLinecap="round" />
      </svg>
    );
  }
  if (choice === "dark") {
    return (
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true">
        <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8Z" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.9" aria-hidden="true">
      <rect x="4" y="5" width="16" height="11" rx="1.8" />
      <path d="M9 20h6M12 16v4" strokeLinecap="round" />
    </svg>
  );
}

function Header({ page, lang, setLang, themeChoice, setThemeChoice }) {
  const homeHref = page === "home" ? "#top" : "index.html";

  return (
    <header className="nav">
      <div className="nav-inner">
        <a className="brand" href={homeHref} aria-label="GDPevo home">
          <BrandLogo />
          <span className="brand-name">
            GDP<span className="brand-accent">evo</span>
          </span>
        </a>
        <div className="nav-right">
          <nav className="page-nav" aria-label="Primary">
            <a className={page === "home" ? "is-active" : undefined} href={homeHref}>
              <Lang en="Home" zh="首页" />
            </a>
            <a className={page === "blog" ? "is-active" : undefined} href="blog.html">
              <Lang en="Blog" zh="博客" />
            </a>
          </nav>
          <div className="theme-segment" role="group" aria-label="Color theme">
            {["light", "dark", "system"].map((choice) => (
              <button
                key={choice}
                type="button"
                className={`theme-choice ${themeChoice === choice ? "is-active" : ""}`}
                data-theme-choice={choice}
                aria-label={`${choice} theme`}
                aria-pressed={themeChoice === choice}
                onClick={() => setThemeChoice(choice)}
              >
                <ThemeIcon choice={choice} />
              </button>
            ))}
          </div>
          <div className="lang-segment" role="group" aria-label="Language">
            {["en", "zh"].map((choice) => (
              <button
                key={choice}
                type="button"
                className={`lang-choice ${lang === choice ? "is-active" : ""}`}
                data-lang-choice={choice}
                aria-label={choice === "en" ? "English" : "Chinese"}
                aria-pressed={lang === choice}
                onClick={() => setLang(choice)}
              >
                {choice.toUpperCase()}
              </button>
            ))}
          </div>
          <a className="icon-link" href="https://github.com/Prism-Shadow/GDPevo" target="_blank" rel="noreferrer" aria-label="GitHub repository">
            <GitHubIcon />
          </a>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero">
      <div className="hero-glow" aria-hidden="true" />
      <div className="wrap hero-inner">
        <h1 className="hero-title">
          <span className="lang-en">
            <span className="accent">GDPevo</span>: Measuring Agent
            <br className="hero-break" />
            {" "}Self-Evolution on Real Business Work
          </span>
          <span className="lang-zh">
            <span className="accent">GDPevo</span>：在真实业务工作上
            <br className="hero-break" />
            衡量 Agent 的自我进化
          </span>
        </h1>
        <p className="hero-sub">
          <span className="lang-en">
            Not <em>can the agent solve this task?</em>
            <br />
            — but <strong>can it evolve across related tasks to get better?</strong>
          </span>
          <span className="lang-zh">
            不是问<em>这个 agent 能不能解决这个任务</em>，
            <br />
            而是问<strong>它能不能借由相关任务完成自我进化，越来越擅长这一类任务</strong>。
          </span>
        </p>
        <p className="hero-meta">
          <Lang en="PrismShadow Team · 2026" zh="PrismShadow Team · 2026" />
        </p>
        <div className="btn-row">
          <a className="btn btn-dark" href="https://github.com/Prism-Shadow/GDPevo" target="_blank" rel="noreferrer">
            <GitHubIcon size={17} />
            <span>GitHub</span>
          </a>
          <a className="btn btn-ghost" href="#results">
            <NavIcon name="chart" />
            <span>
              <Lang en="Results" zh="结果" />
            </span>
          </a>
          <a className="btn btn-ghost" href="blog.html">
            <NavIcon name="blog" />
            <span>
              <Lang en="Read the blog" zh="阅读博客" />
            </span>
          </a>
          <a className="btn btn-ghost" href="https://github.com/Prism-Shadow/GDPevo/blob/main/experiments/EXPERIMENT_BOARD.md" target="_blank" rel="noreferrer">
            <NavIcon name="code" />
            <span>
              <Lang en="Experiment board" zh="实验看板" />
            </span>
          </a>
        </div>
        <div className="stat-band">
          <div className="stat">
            <span className="stat-num">120</span>
            <span className="stat-label">
              <Lang en="GDP-worthy tasks" zh="真实业务任务" />
            </span>
          </div>
          <div className="stat">
            <span className="stat-num">12</span>
            <span className="stat-label">
              <Lang en="Task groups · CRM · ERP · Finance" zh="任务组 · CRM · ERP · Finance" />
            </span>
          </div>
          <div className="stat">
            <span className="stat-num stat-tba">
              <Lang en="TBD" zh="暂定" />
            </span>
            <span className="stat-label">
              <Lang en="Held-out accuracy lift from self-evolution" zh="自我进化带来的 held-out 准确率提升" />
            </span>
          </div>
          <div className="stat">
            <span className="stat-num stat-tba">
              <Lang en="TBD" zh="暂定" />
            </span>
            <span className="stat-label">
              <Lang en="Token cost — fewer, not more" zh="token 成本 —— 更少，而非更多" />
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

function SummaryCard({ card }) {
  return (
    <div className="htable">
      <div className="ht-cap">
        <span>{card.title}</span>
        <small>
          <span className="lang-en">{card.thinking} · avg@3 over 12 task groups</span>
          <span className="lang-zh">{card.thinking} · 12 个 task group 的 avg@3</span>
        </small>
      </div>
      <div className="ht-row ht-head">
        <span>
          <Lang en="Mode" zh="模式" />
        </span>
        <span className="num">avg@3</span>
        <span className="num">
          <Lang en="Tokens (k)" zh="Tokens (k)" />
        </span>
        <span className="num">USD</span>
      </div>
      {card.rows.map((row) => (
        <div key={row.mode} className={`ht-row ${row.best ? "best" : ""}`}>
          <code>{row.mode}</code>
          <span className="num">{row.avg}</span>
          <span className="num">{row.tokens}</span>
          <span className="num">{row.usd}</span>
        </div>
      ))}
    </div>
  );
}

function metricValue(value) {
  return Number.parseFloat(String(value).replace(/[^\d.-]/g, ""));
}

function BlogBenchmarkFigure() {
  return (
    <figure className="blog-benchmark-figure">
      <figcaption className="blog-benchmark-head">
        <div>
          <strong>
            <Lang en="Agent performance — all harnesses" zh="三套 harness 的 agent 表现" />
          </strong>
          <span>
            <Lang en="12 task groups · avg@3 · three evaluation modes" zh="12 个 task group · avg@3 · 三种评估模式" />
          </span>
        </div>
        <span className="blog-benchmark-legend" aria-label="Chart legend">
          {modes.map((mode) => (
            <i key={mode}>
              <b className={`sw sw-${mode}`} />
              {mode}
            </i>
          ))}
        </span>
      </figcaption>
      <div className="blog-benchmark-cols">
        <span>Harness</span>
        <span>Mode</span>
        <span>avg@3</span>
        <span>Tokens (k)</span>
        <span>USD</span>
      </div>
      <div className="blog-benchmark-rows">
        {summaryCards.map((card) => {
          const [harness, model] = card.title.split(" · ");
          return (
            <div className="blog-benchmark-group" key={card.title}>
              <div className="blog-benchmark-name">
                <strong>{harness}</strong>
                <span>{model}</span>
                <small>{card.thinking}</small>
              </div>
              <div className="blog-benchmark-bars">
                {card.rows.map((row) => (
                  <div className={`blog-benchmark-bar mode-${row.mode}`} key={row.mode}>
                    <code>{row.mode}</code>
                    <div className="blog-benchmark-measure">
                      <div className="blog-benchmark-track">
                        <span style={{ "--w": `${metricValue(row.avg)}%` }} />
                      </div>
                      <b>{row.avg}</b>
                    </div>
                    <span className="blog-benchmark-token">{row.tokens}</span>
                    <span className="blog-benchmark-usd">{row.usd}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </figure>
  );
}

function Meter({ value, mode }) {
  return (
    <div className={`ob-meter mode-${mode}`}>
      <div className="ob-track">
        <span className={`fl ${mode}`} style={{ "--w": `${value.toFixed(2)}%` }} />
      </div>
      <b>{value.toFixed(1)}</b>
    </div>
  );
}

function HarnessRows({ harness, group }) {
  return (
    <div className="ob-harness-block">
      <span className="ob-harness">{harness.harness}</span>
      <span className="ob-model">{harness.model}</span>
      <span className="ob-thinking">{harness.thinking}</span>
      <div className="ob-condition-rows">
        {modes.map((mode, index) => (
          <div className="ob-row" key={mode}>
            <code>{mode}</code>
            <Meter value={group[harness.key][index]} mode={mode} />
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultsChart() {
  const ref = useRef(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (!ref.current) return undefined;
    if (!("IntersectionObserver" in window)) {
      setShown(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setShown(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return (
    <figure ref={ref} className={`panel chart merged-chart ${shown ? "shown" : ""}`} id="chart">
      <figcaption className="panel-head">
        <span className="panel-title">
          <Lang en="Held-out accuracy by task group (avg@3, %)" zh="各 task group 的 held-out 准确率 (avg@3, %)" />
        </span>
        <span className="legend">
          <span className="leg">
            <i className="sw sw-base" />
            base
          </span>
          <span className="leg">
            <i className="sw sw-demo" />
            demo
          </span>
          <span className="leg">
            <i className="sw sw-reflect" />
            reflect
          </span>
        </span>
      </figcaption>
      <div className="combined-bars">
        <div className="ob-head">
          <span>
            <Lang en="Task group" zh="Task group" />
          </span>
          <span>Harness</span>
          <span>Model</span>
          <span>Thinking level</span>
          <span>
            <Lang en="Setting" zh="设定" />
          </span>
          <span>Accuracy</span>
        </div>
        {resultGroups.map((group) => {
          const chip = group.domain === "Finance" ? "fin" : group.domain.toLowerCase();
          return (
            <div className="ob-group" key={group.id}>
              <div className="ob-name">
                <strong>{group.id}</strong>
                <i className={`chip ${chip}`}>{group.domain}</i>
                <span>
                  <Lang en={group.en} zh={group.zh} />
                </span>
              </div>
              <div className="ob-rows">
                {harnesses.map((harness) => (
                  <HarnessRows key={harness.key} harness={harness} group={group} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </figure>
  );
}

function ResultsSection() {
  return (
    <section className="section" id="results">
      <div className="wrap results-wrap">
        <h2 className="h2">
          <span className="lang-en">
            Self-evolution makes agents more accurate while spending <span className="accent">fewer</span> tokens.
          </span>
          <span className="lang-zh">
            自我进化让 agent 更准,同时花<span className="accent">更少</span>的 token。
          </span>
        </h2>
        <p className="lead">
          <span className="lang-en">
            Each group has 5 train and 5 held-out test tasks. We compare a baseline (<code>base</code>) against two evolution modes: <code>demo</code> evolves from worked examples, while <code>reflect</code> evolves from its own mistakes. The score measures lift on tasks the agent never saw.
          </span>
          <span className="lang-zh">
            每组有 5 个 train、5 个 held-out test。我们用基线（<code>base</code>）对比两种进化模式：<code>demo</code> 基于样例进化，<code>reflect</code> 基于自己的错误进化；分数衡量的是 agent 在没见过的任务上的提升。
          </span>
        </p>
        <div className="htables">
          {summaryCards.map((card) => (
            <SummaryCard key={card.title} card={card} />
          ))}
        </div>
        <ResultsChart />
        <p className="note">
          <span className="lang-en">
            <strong>avg@3</strong> = mean held-out accuracy over 3 attempts per task. The task-group chart below keeps Codex, Claude Code, and Panofy side by side under the same base, demo, and reflect settings.
          </span>
          <span className="lang-zh">
            <strong>avg@3</strong> = 每个任务 3 次尝试的 held-out 准确率均值。下面的 task-group 图并排展示 Codex、Claude Code 与 Panofy 在 base、demo、reflect 下的结果。
          </span>
        </p>
        <p className="note">
          <span className="lang-en">
            Accuracy lift / cost change: <strong>+20.31 pp / −8.69%</strong> (Claude Code) · <strong>+18.21 pp / −25.75%</strong> (Codex) · <strong>+17.94 pp / +11.82%</strong> (Panofy).
          </span>
          <span className="lang-zh">
            准确率提升 / Cost 变化：<strong>+20.31 pp / −8.69%</strong>（Claude Code）· <strong>+18.21 pp / −25.75%</strong>（Codex）· <strong>+17.94 pp / +11.82%</strong>（Panofy）。
          </span>
        </p>
        <p className="note">
          <span className="lang-en">
            Full per-task reports under <code>experiments/codex_gpt5_5_xhigh/</code>, <code>experiments/claude_code_opus_4_8_xhigh/</code>, and <code>experiments/panofy_claude_opus_4_6_high/</code>.
          </span>
          <span className="lang-zh">
            完整逐任务报告见 <code>experiments/codex_gpt5_5_xhigh/</code>、<code>experiments/claude_code_opus_4_8_xhigh/</code> 与 <code>experiments/panofy_claude_opus_4_6_high/</code>。
          </span>
        </p>
        <p className="note">
          <a href="blog.html#cost">
            <Lang en="Why can self-evolution cost less? Read the blog →" zh="为什么自我进化反而更省？阅读博客 →" />
          </a>
        </p>
      </div>
    </section>
  );
}

function TaskDetail({ groupId }) {
  const tasks = taskTopics[groupId] ?? [];
  const sections = useMemo(
    () => [
      ["Train", "train", "5 examples", tasks.filter((task) => task[1] === "Train")],
      ["Test", "test", "5 held-out", tasks.filter((task) => task[1] === "Test")]
    ],
    [tasks]
  );

  return (
    <div className="tg-detail" id={`task-detail-${groupId}`}>
      <div className="tg-detail-head">
        <strong>
          <Lang en="Task themes" zh="Task 主题" />
        </strong>
        <span>
          <Lang en="5 train · 5 test" zh="5 个 train · 5 个 test" />
        </span>
      </div>
      <div className="task-sets">
        {sections.map(([kind, label, count, items]) => (
          <section className={`task-set task-set-${label}`} key={kind}>
            <div className="task-set-head">
              <strong>{label}</strong>
              <span>{count}</span>
            </div>
            <div className="task-list">
              {items.map(([taskId, , title, desc]) => {
                const taskNo = String(Number(taskId.split("_")[1])).padStart(2, "0");
                return (
                  <div className="task-item" key={taskId}>
                    <span className="task-id">task {taskNo}</span>
                    <span className="task-title">{title}</span>
                    <span className="task-desc">{desc}</span>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function TasksSection() {
  const [openGroup, setOpenGroup] = useState(null);

  return (
    <section className="section band" id="tasks">
      <div className="wrap">
        <h2 className="h2">
          <Lang en="Real company interfaces — CRM, ERP, Finance." zh="真实的公司业务接口 —— CRM、ERP、Finance。" />
        </h2>
        <p className="lead">
          <span className="lang-en">
            Each group is one shared business world with lookalike records mixed in, seeded from real-job sources such as <a href="https://openai.com/index/gdpval/" target="_blank" rel="noopener noreferrer">GDPval</a> and <a href="https://github.com/amazon-science/SOP-Bench" target="_blank" rel="noopener noreferrer">SOP-Bench</a>.
          </span>
          <span className="lang-zh">
            每组都是一个共享的业务世界,混入了大量"长得很像"的干扰记录;场景来自像 <a href="https://openai.com/index/gdpval/" target="_blank" rel="noopener noreferrer">GDPval</a> 和 <a href="https://github.com/amazon-science/SOP-Bench" target="_blank" rel="noopener noreferrer">SOP-Bench</a> 这样的真实工作任务源。
          </span>
        </p>
        <div className="tg-table">
          <div className="tg-row tg-head">
            <span>
              <Lang en="Group" zh="编号" />
            </span>
            <span>
              <Lang en="Domain" zh="领域" />
            </span>
            <span>
              <Lang en="Business focus" zh="业务场景" />
            </span>
          </div>
          {taskGroups.map((group) => {
            const open = openGroup === group.id;
            const chip = group.domain === "Finance" ? "fin" : group.domain.toLowerCase();
            return (
              <Fragment key={group.id}>
                <button
                  type="button"
                  className={`tg-row ${open ? "is-open" : ""}`}
                  data-task-group={group.id}
                  aria-expanded={open}
                  aria-controls={`task-detail-${group.id}`}
                  onClick={() => setOpenGroup(open ? null : group.id)}
                >
                  <span className="tg-id">{group.label}</span>
                  <span>
                    <i className={`chip ${chip}`}>{group.domain}</i>
                  </span>
                  <span>
                    <Lang en={group.en} zh={group.zh} />
                  </span>
                </button>
                {open ? <TaskDetail groupId={group.id} /> : null}
              </Fragment>
            );
          })}
        </div>
        <p className="note">
          <span className="lang-en">
            How the hidden rules are planted, how the data is built and graded by agents, and why cost goes down — <a href="blog.html"><strong>read the blog →</strong></a>
          </span>
          <span className="lang-zh">
            隐藏规则怎么埋、数据怎么由 agent 构造与评分、成本为什么会下降 —— <a href="blog.html"><strong>阅读博客 →</strong></a>
          </span>
        </p>
      </div>
    </section>
  );
}

function BlogIntro() {
  return (
    <section className="section blog-head">
      <div className="wrap narrow">
        <h1 className="h2 blog-title">
          <Lang en="Measuring Agent Self-Evolution on Real Business Work" zh="在真实业务工作上衡量 Agent 的自我进化" />
        </h1>
        <p className="lead">
          <Lang
            en="In the AI era, once something can be evaluated and that evaluation can be automated, the problem is essentially solved. Better evaluation begets better agents; better agents in turn drive sharper evaluation — and the loop converges fast."
            zh="在 AI 时代，一件事如果能被评估，并且评估可以被自动化，那它基本上就已经被解决了。更好的评估孕育更好的 agent，更好的 agent 又反过来推动更精细的评估——这个循环收敛得很快。"
          />
        </p>
        <div className="prose">
          <p>
            <span className="lang-en">Self-evolution — agents that rewrite their own memory, procedures, or harness to get better at a class of tasks over time — is a problem the field clearly cares about. Companies built around agentic self-improvement (Cognition, Reflection AI, and others) have raised on the order of <strong>billions of dollars</strong> in 2025 alone. Yet on <strong>real productivity work</strong> — auditing AP invoices, reconciling event sponsorship across CRM and finance, building a branch close-out package — there is essentially <em>no benchmark</em> for whether an agent can actually self-evolve. It can't be measured today, let alone measured automatically.</span>
            <span className="lang-zh">Self-evolution——agent 通过自己改写 memory、procedure 或 harness，在一类任务上越做越好——是一个业界很关注的问题。围绕 agent 自我进化的公司（Cognition、Reflection AI 等）仅 2025 一年就募集了约 <strong>数十亿美元</strong>的资金。然而在<strong>真实生产力工作</strong>这一面——审核 AP 发票、把展会赞助在 CRM 和财务两边对账、做一个分行月度结账包——几乎<em>没有 benchmark</em>能告诉我们 agent 到底有没有 self-evolve。目前它根本测不了，更谈不上自动化测。</span>
          </p>
          <p>
            <span className="lang-en">GDPevo fills that gap. It is both a <strong>process</strong> for automatically building self-evolution benchmarks on real-job tasks, and a released <strong>benchmark</strong> produced by that process — twelve task groups across CRM, ERP, and Finance, each with five train tasks and five test tasks under a shared environment and rule-based graders. The construction-and-evaluation pipeline is shown in later sections.</span>
            <span className="lang-zh">GDPevo 就是来补这个 gap 的。它既是一套<strong>流程</strong>——在真实业务任务上自动化地构建 self-evolution benchmark；也是这套流程的产物，一份<strong>已发布的 benchmark</strong>——12 组 task group，覆盖 CRM、ERP、Finance，每组 5 个 train + 5 个 test，共享同一个环境，用基于规则的 grader 打分。构建与评估的整体流程在后续章节中展示。</span>
          </p>
          <p>
            <span className="lang-en">Automating the construction and evaluation of productivity-flavored datasets has two hard problems on the construction side. <strong>First</strong>, train and test must be cleanly separated so the agent can actually <em>evolve</em> on train and have that change <em>show up</em> on test — many existing benchmarks fail this and end up training and testing on the same set. We solve it with <strong>Hidden Rules</strong>: operational rules are planted across the train tasks in pieces and recombined on the test, so a passing score requires real abstraction, not memorization. <strong>Second</strong>, LLMs are lazy — they declare victory while quietly skipping work. We add a <strong>review mechanism</strong>: a panel of independent reviewer agents audits each task group end-to-end, and a group only ships when the reviewers confirm everything was actually delivered.</span>
            <span className="lang-zh">在生产力相关的数据集上做自动化构建与评估，<em>构建</em>侧有两大难点。<strong>第一</strong>，必须把 train 和 test 干净地分开，让模型真的能在 train 后<em>发生进化</em>，并且在 test 上<em>体现</em>出来——很多现有 benchmark 就是没做到这点，最后在 train 上训、在 train 上测。我们用<strong>Hidden Rules</strong>来解决这个问题：把业务规则拆散埋进 train，再在 test 上重新组合，要拿分就必须真的把规则抽象出来，而不是死记硬背。<strong>第二</strong>，大模型会偷懒——经常嘴上说"做完了"实际跳过了步骤。我们加了一套 <strong>review 机制</strong>：由若干独立的 reviewer agent 端到端审计每一组任务，所有内容确认交付了，这一组才会放行。</span>
          </p>
          <p>
            <span className="lang-en">In addition, our evaluation makes three commitments. <strong>One</strong>, grading is <strong>rule-based</strong>, not LLM-as-a-judge — every score is reproducible and every failure points to a specific rule. <strong>Two</strong>, both <strong>cost</strong> and <strong>accuracy</strong> are first-class citizens — a useful agent isn't just one that gets the right answer, it's one that gets there <em>more cheaply</em> over time. <strong>Three</strong>, the workspace is <strong>natural-language driven</strong> — you describe the experiment and the chart you want in one sentence, and a coding agent generates the analysis on the fly; you don't write code yourself.</span>
            <span className="lang-zh">在评估侧，我们坚持三件事。<strong>第一</strong>，<strong>规则化打分</strong>，不用 LLM-as-a-judge——每一个分都是可复现的，每一次失败都能定位到具体的规则。<strong>第二</strong>，<strong>cost</strong> 与 <strong>accuracy</strong> 同为一等公民——一个好用的 agent 不仅要答得对，还要随时间推移、用<em>更少的代价</em>把题做出来。<strong>第三</strong>，工作区<strong>由自然语言驱动</strong>——你用一句话描述要跑的实验和想要的图表，一个 coding agent 当场生成分析代码出图；你自己不需要写代码。</span>
          </p>
          <p>
            <span className="lang-en">We close with evaluation and findings. On all three agent harnesses we tested, self-evolution lifts held-out accuracy by <strong>+17 to +22 points</strong>; on two of them token usage actually goes <em>down</em>, not up — fluency, not just a higher score. Below, we walk through how this benchmark is built, and how it is used.</span>
            <span className="lang-zh">最后是 evaluation 和 findings。在我们测的三套 agent harness 上，self-evolution 都把 held-out 准确率提升了 <strong>+17 到 +22 个百分点</strong>；其中两套 harness 上 token 消耗不增<em>反降</em>——变得更熟练，不止是分数变高。下面我们就来看看这个 benchmark 是怎么被构建出来的，以及怎么使用。</span>
          </p>
        </div>
      </div>
    </section>
  );
}

function BlogConstruction() {
  return (
    <section className="section" id="construction">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang en="How we built it." zh="我们怎么构建。" />
        </h2>
        <p className="lead">
          <span className="lang-en">Building a self-evolution benchmark for real business work poses two challenges. <strong>First</strong>, the construction should be agent-driven end-to-end — humans write the procedure once, agents do the rest. This matters for two reasons. It helps the benchmark <em>outrun data leakage</em>: as long as agents can spawn fresh tasks faster than models absorb the leaked ones, the benchmark stays ahead. It also lets the benchmark <em>scale</em>: when agents both build and evaluate, the loop is closed — no human bottleneck — and the benchmark can keep growing on its own. <strong>Second</strong>, train and test have to be related but not redundant: the train tasks must teach a real, hidden lesson that pays off only when the lesson is extracted, not memorized.</span>
          <span className="lang-zh">为真实业务工作构建一个 self-evolution benchmark，有两个 challenge。<strong>第一</strong>，构建过程应该是 agent 端到端跑出来的——人只把流程写一次，剩下交给 agent。这件事之所以重要有两个原因。它能帮 benchmark <em>跑赢数据泄露</em>：只要 agent 生成新题的速度比模型吸收已泄露题的速度快，benchmark 就一直保持领先。它也让 benchmark 能<em>真正 scale</em>：当 agent 既负责构造、又负责评测，整个回路就闭合了——没有人力瓶颈，左脚踩右脚，benchmark 可以自己长大。<strong>第二</strong>，train 和 test 要相关、但不能冗余：train 必须真的"教"一个隐藏的规则，这个规则只有被抽象出来才会在 test 上派上用场，而不是被死记下来。</span>
        </p>

        <h3 className="h3 h3-spaced h3-spaced-sm">
          <Lang en="Built end-to-end by agents." zh="从头到尾，全部由 agent 完成。" />
        </h3>
        <div className="prose">
          <p>
            <span className="lang-en">Humans wrote the pipeline once. After that, agents do everything (illustrated below). They pull seed scenarios from public real-job benchmarks (GDPval, SOP-Bench, JobBench) and spawn many candidate task groups from those seeds. For each group, they build a shared environment and author 5 train + 5 test tasks with rule-based evaluators. A calibrator then tunes difficulty so that an <code>evolution</code> setup clearly beats a <code>no-evolution</code> setup — this filters out tasks where evolution wouldn't change the answer, keeping the benchmark focused on agents that actually have to evolve across related work. Finally, six independent reviewer agents audit the result, and a group ships only when 5 of 6 pass — these reviewers exist because agents have a habit of declaring victory while quietly skipping work, so completeness, file presence, and planted hidden rules are exactly what gets checked. Twelve task groups make it through this filter and form the public release.</span>
            <span className="lang-zh">人只写一次 pipeline，之后全靠 agent（如下图所示）。先从公开的真实业务 benchmark（GDPval、SOP-Bench、JobBench）里取种子场景，再据此 spawn 出大量候选 task group。每组里搭一个共享 env，写 5 个 train + 5 个 test 任务并配上基于规则的 evaluator。然后 calibrator 调难度，让 <code>evolution</code> 设定明显超过 <code>no-evolution</code> 设定——这一步是为了把那些"是否进化都不影响答案"的题筛掉，让 benchmark 集中在那些真的需要跨相关任务自我进化的 agent 上。最后由 6 个互相独立的 reviewer agent 审核，6 个里 5 个通过这一组才放行——之所以要 reviewer，是因为 agent 经常嘴上说"做完了"、实际偷懒，所以审核的就是结构、完整性、文件是否齐全、隐藏规则是否真的埋了进去。最终通过这层筛选活下来、进入公开发布的，是 12 组 task group。</span>
          </p>
        </div>
        <figure className="pipeline-figure">
          <img src="assets/gdpevo-pipeline.png" alt="GDPevo data pipeline: seed scenarios to multi-agent task factory to quality review to release." loading="lazy" />
        </figure>

        <h3 className="h3 h3-spaced">
          <Lang en="Hidden rules, spread across the train tasks." zh="隐藏规则，分散到各个 train task 里。" />
        </h3>
        <div className="prose">
          <p>
            <span className="lang-en">For every task group we plant a small set of hidden operational rules. A CRM lead-capture group might encode a <em>sponsor-status precedence rule</em> (finance invoices outrank badge scans) and a <em>suppression-list policy</em> (don't contact certain segments). A procurement-readiness group enforces that <em>open vendor-risk events and AP holds force a "held" line</em>, regardless of how clean the PO looks.</span>
            <span className="lang-zh">每个 task group 我们都会埋一小组隐藏的业务规则。CRM 销售线索组可能埋了两条：<em>赞助商身份的优先级</em>（财务发票优先于胸卡扫描），以及 <em>suppression list 政策</em>（某些细分人群禁止联系）。采购就绪组则要求：<em>只要供应商有 open 的 risk event 或 AP hold，对应行就必须 held</em>，不管 PO 看起来多干净。</span>
          </p>
          <p>
            <span className="lang-en">We <em>spread</em> these rules across the 5 train tasks, so each train task only exercises a subset. The 5 test tasks are deliberately built as <strong>combinations</strong> — say, the precedence rule together with the suppression policy. An agent that solves each train in isolation only sees rule fragments. An agent that turns them into an evolution update has them all in one place — and when the test asks for two at once, it doesn't need to rediscover them. That's why a higher test score is real evidence of evolution, not luck.</span>
            <span className="lang-zh">我们把这些规则<em>分散</em>到 5 个 train 里，每个 train 只触发一部分。5 个 test 故意被设计成这些规则的<strong>组合</strong>——比如同时触发"优先级 + suppression"。只盯着单个 train 做的 agent 看到的是碎片；能把这些规则转成一次 evolution update 的 agent，则把它们放在一处——test 同时问两条时，它不需要重新发现。这就是 test 分数变高的原因，是真的发生了进化，而不是运气。</span>
          </p>
        </div>
      </div>
    </section>
  );
}

function BlogUsage() {
  return (
    <section className="section" id="usage">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang en="How to evaluate with it." zh="怎么用它做评估。" />
        </h2>
        <p className="lead">
          <span className="lang-en">Two things we want from an evaluation harness: it should grade in a way you can audit; and it should treat <em>cost</em> as a first-class citizen alongside accuracy. Each one motivated a specific design.</span>
          <span className="lang-zh">我们对评估 harness 有两个要求：评分必须可被人审计；<em>cost</em> 要和 accuracy 同等重要。下面两块就是为了满足这两个要求。</span>
        </p>

        <h3 className="h3 h3-spaced">
          <Lang en={'Rule-based grading, not "ask another LLM".'} zh={'基于规则的评分，而不是"再叫一个 LLM 来判"。'} />
        </h3>
        <div className="prose">
          <p>
            <span className="lang-en">GDPevo grades with deterministic, rule-based checkers — for example, was the right set of records returned, did the amount round to the right precision. Two things follow. First, the score is <strong>reproducible</strong>: the same answer always gets the same grade, regardless of who runs it or when. Second, every failure is <strong>traceable</strong>: instead of a vague verdict, you see exactly which rule was violated and by how much. That trace is what makes the benchmark useful for diagnosis — you can read it back to find weak spots in your agent and feed those weak spots into the next round of memory or procedure updates.</span>
            <span className="lang-zh">GDPevo 用确定性的 rule-based checker 打分——比如返回的记录集对不对、金额是否遵守了要求的精度。这带来两个好处。第一，评分是<strong>可复现</strong>的：同一份答案，谁跑、什么时候跑，得到的分都一样。第二，每一次失败都是<strong>可追溯</strong>的：你看到的不是一个含糊的整体结论，而是具体哪一条规则被违反、扣了多少分。这种可追溯性让 benchmark 成为诊断工具——你可以反过来读这些 trace，找到你的 agent 短板在哪儿，再把这些短板喂回下一轮 memory 或 procedure 更新。</span>
          </p>
        </div>

        <h3 className="h3 h3-spaced" id="cost">
          <Lang en="Cost and accuracy, both first-class." zh="cost 和 accuracy 都是一等公民。" />
        </h3>
        <div className="prose">
          <p>
            <span className="lang-en">A useful agent isn't just one that gets the right answer — it's one that <em>stops redoing</em> the same legwork every time a similar task comes in. Self-evolution should look like a human getting fluent: more accurate <em>and</em> faster, with fewer tokens, fewer steps, and cleaner moves. So we instrument every run end-to-end: per-agent total token spend, plus a breakdown by reasoning, tool calls, and stage. That observability isn't only for our analysis — those traces also become raw material for the agent's next evolution update.</span>
            <span className="lang-zh">一个有用的 agent 不仅要答得对，还得<em>不再每次都把同样的活儿重做一遍</em>。Self-evolution 应该像人变熟练：更准、<em>更快</em>，用更少的 token、更少的步数、更干净的做法。所以我们对每一次运行都做端到端打点：每个 agent 的总 token 消耗，以及按 reasoning、工具调用、不同阶段的 breakdown。这套 observability 不只服务我们自己的分析——这些 trace 本身也是 agent 下一次 self-evolve 的材料。</span>
          </p>
        </div>
      </div>
    </section>
  );
}

function BlogFindings() {
  return (
    <section className="section" id="findings">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang en="Evaluations and findings." zh="实测与结果。" />
        </h2>
        <div className="prose">
          <p>
            <span className="lang-en">Every run below was driven by natural language: we pointed a coding agent (Codex or Claude Code) at the evaluation workspace — a folder of plain Markdown guides, prompts, and directory conventions — typed one sentence describing the experiment and the chart we wanted, and the agent generated the analysis code, called the graders, and wrote the report. No hand-written harness, no SDK to learn.</span>
            <span className="lang-zh">下面这些实验都是用自然语言驱动跑出来的：我们把一个 coding agent（Codex 或 Claude Code）指向评估工作区——一个装满纯 Markdown 指南、prompt 和目录约定的文件夹——用一句话说清要跑什么实验、想要什么样的图，agent 就会自己生成分析代码、调 grader、写 report。没有手写的 harness，也没有要学的 SDK。</span>
          </p>
          <p>
            <span className="lang-en">We ran the same 12 task groups under three settings, on three different agent harnesses:</span>
            <span className="lang-zh">我们在同样的 12 组 task group 上跑了三种设定，跨三套不同的 agent harness：</span>
          </p>
          <ul className="bullets">
            <li>
              <span className="lang-en"><code>base</code> — the agent solves the 5 test tasks cold, with no prior exposure to the 5 train tasks.</span>
              <span className="lang-zh"><code>base</code>——agent 直接做 5 个 test，没接触过 5 个 train。</span>
            </li>
            <li>
              <span className="lang-en"><code>demo</code> — the agent reads the 5 train tasks <em>with their gold answers</em> first, turns them into an evolution update, and then takes the test. (Analogous to SFT.)</span>
              <span className="lang-zh"><code>demo</code>——agent 先读 5 个 train 的题目和<em>标准答案</em>，把它们转成一次 evolution update，再去做 test。（类似 SFT。）</span>
            </li>
            <li>
              <span className="lang-en"><code>reflect</code> — the agent attempts the 5 train tasks <em>without</em> seeing answers, gets back graded reward and feedback, updates its memory or procedure from what it got wrong, then takes the test. (Analogous to RL.)</span>
              <span className="lang-zh"><code>reflect</code>——agent <em>看不到答案</em>，自己做 5 个 train，事后拿到 reward 和反馈，更新自己的 memory 或 procedure，再去做 test。（类似 RL。）</span>
            </li>
          </ul>
        </div>

        <BlogBenchmarkFigure />
        <p className="note">
          <span className="lang-en">The shape is the same on all three harnesses: self-evolution lifts held-out accuracy by <strong>~17–22 points</strong>, and on the GPT-5.5 / Opus 4.8 setups tokens go <em>down</em>, not up — the fluency story, not just a higher score. On one task group (operational financial modeling), Codex went from <strong>42.76% to 92.47%</strong> with fewer tokens than the baseline; on the same group, Claude Code's <code>demo</code> reached <strong>100%, up from 51.76%</strong>.</span>
          <span className="lang-zh">三套 harness 形状一致：self-evolution 让 held-out 准确率提升 <strong>约 17–22 个百分点</strong>，且在 GPT-5.5 / Opus 4.8 这两套上，<em>花的 token 反而更少</em>——这正是"变熟练"，而不仅仅是分数更高。在 operational financial modeling 这一组上，Codex 从 <strong>42.76% 升到 92.47%</strong>，token 比基线还少；同一组上，Claude Code 的 <code>demo</code> 直接到了 <strong>100%，起点是 51.76%</strong>。</span>
        </p>
        <p className="prose-link">
          <a href="index.html#results">
            <Lang en="See the per-group breakdown on the homepage →" zh="在首页查看逐组的明细 →" />
          </a>
        </p>
      </div>
    </section>
  );
}

function BlogInvite() {
  const [copied, setCopied] = useState(false);
  const citation = `@misc{gdpevo2026,
  title  = {GDPevo: Measuring Agent Self-Evolution on Real Business Work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}`;

  const copyCitation = async () => {
    if (!navigator.clipboard) return;
    await navigator.clipboard.writeText(citation);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="section band" id="invite">
      <div className="wrap narrow">
        <h2 className="h2">
          <Lang en="GDPevo is a seed, not a finished product." zh="GDPevo 是一颗种子，不是一件成品。" />
        </h2>
        <div className="prose">
          <p>
            <span className="lang-en">The tasks, environments, graders, generated updates, and full reports are open. Bring your own agents and scenarios. Submit harder hidden rules. The goal is not a leaderboard, but a public interface where agents that actually do productive work can be trained — and where the evidence of that improvement is open to inspection.</span>
            <span className="lang-zh">任务、环境、grader、生成的更新、完整 report 都是开放的。欢迎带上你自己的 agent、你自己的业务场景，欢迎来挑战、欢迎提交更难的隐藏规则。我们的目标不是一张 leaderboard，而是一个公共接口 —— 让真正能干生产力工作的 agent 在这里被训练出来，并且这种"它真的变好了"的证据可以被任何人审计。</span>
          </p>
        </div>
        <div className="btn-row invite-actions">
          <a className="btn btn-dark" href="https://github.com/Prism-Shadow/GDPevo" target="_blank" rel="noreferrer">
            <span>GitHub</span>
          </a>
          <a className="btn btn-ghost" href="https://github.com/Prism-Shadow/GDPevo/blob/main/experiments/EXPERIMENT_BOARD.md" target="_blank" rel="noreferrer">
            <span>
              <Lang en="Experiment board" zh="实验看板" />
            </span>
          </a>
          <a className="btn btn-ghost" href="https://github.com/Prism-Shadow/GDPevo/tree/main/experiments/eval_workspace" target="_blank" rel="noreferrer">
            <span>
              <Lang en="Eval workspace" zh="评估工作区" />
            </span>
          </a>
        </div>
        <div className="bibtex">
          <button type="button" className={`copy-btn ${copied ? "copied" : ""}`} aria-label="Copy citation" onClick={copyCitation}>
            <Lang en={copied ? "Copied" : "Copy"} zh={copied ? "已复制" : "复制"} />
          </button>
          <pre><code>{citation}</code></pre>
        </div>
      </div>
    </section>
  );
}

function HomePage() {
  return (
    <main id="top">
      <Hero />
      <ResultsSection />
      <TasksSection />
    </main>
  );
}

function BlogPage() {
  return (
    <main id="top">
      <BlogIntro />
      <BlogConstruction />
      <BlogUsage />
      <BlogFindings />
      <BlogInvite />
    </main>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div className="wrap footer-inner">
        <div className="brand">
          <span className="brand-name">
            GDP<span className="brand-accent">evo</span>
          </span>
        </div>
        <p className="footer-tag">
          <Lang en="Measuring agent self-evolution on GDP-worthy work." zh="在真实业务工作上衡量 Agent 的自我进化。" />
        </p>
        <a className="footer-link" href="https://github.com/Prism-Shadow/GDPevo" target="_blank" rel="noreferrer">github.com/Prism-Shadow/GDPevo</a>
      </div>
    </footer>
  );
}

export default function App() {
  const [lang, setLang] = useState(initialLang);
  const [themeChoice, setThemeChoice] = useState(initialThemeChoice);
  const page = window.location.pathname.endsWith("/blog.html") ? "blog" : "home";

  useEffect(() => {
    if (!window.location.hash) return;
    requestAnimationFrame(() => {
      const id = window.location.hash.slice(1);
      document.getElementById(id)?.scrollIntoView();
    });
  }, [page]);

  useEffect(() => {
    document.body.classList.toggle("blog", page === "blog");
    document.title = page === "blog"
      ? "GDPevo Blog — Measuring Agent Self-Evolution on Real Business Work"
      : "GDPevo — Measuring Agent Self-Evolution on Real Business Work";
  }, [page]);

  useEffect(() => {
    document.documentElement.setAttribute("data-lang", lang);
    document.documentElement.setAttribute("lang", lang === "zh" ? "zh-Hans" : "en");
    try {
      localStorage.setItem("gdpevo-lang", lang);
    } catch (e) {
      // Ignore storage access errors in restricted browser contexts.
    }
  }, [lang]);

  useEffect(() => {
    const apply = () => {
      document.documentElement.setAttribute("data-theme", resolveTheme(themeChoice));
      document.documentElement.setAttribute("data-theme-choice", themeChoice);
    };
    apply();
    try {
      localStorage.setItem("gdpevo-theme", themeChoice);
    } catch (e) {
      // Ignore storage access errors in restricted browser contexts.
    }
    const mq = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
    if (!mq || themeChoice !== "system") return undefined;
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [themeChoice]);

  return (
    <>
      <Header page={page} lang={lang} setLang={setLang} themeChoice={themeChoice} setThemeChoice={setThemeChoice} />
      {page === "blog" ? <BlogPage /> : <HomePage />}
      <Footer />
    </>
  );
}
