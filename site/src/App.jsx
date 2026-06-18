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

function Header({ lang, setLang, themeChoice, setThemeChoice }) {
  return (
    <header className="nav">
      <div className="nav-inner">
        <a className="brand" href="#top" aria-label="GDPevo home">
          <BrandLogo />
          <span className="brand-name">
            GDP<span className="brand-accent">evo</span>
          </span>
        </a>
        <div className="nav-right">
          <nav className="page-nav" aria-label="Primary">
            <a className="is-active" href="#top">
              <Lang en="Home" zh="首页" />
            </a>
            <a href="blog.html">
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
          <a className="icon-link" href="https://github.com/Prism-Shadow/GDPevo" aria-label="GitHub repository">
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
            — but <strong>can it learn from related tasks to get better?</strong>
          </span>
          <span className="lang-zh">
            不是问<em>这个 agent 能不能解决这个任务</em>，
            <br />
            而是问<strong>它能不能通过相关任务的经验，越来越擅长这一类任务</strong>。
          </span>
        </p>
        <p className="hero-meta">
          <Lang en="Public Benchmark Release · 2026 · PrismShadow team" zh="公开基准发布 · 2026 · PrismShadow 团队" />
        </p>
        <div className="btn-row">
          <a className="btn btn-dark" href="https://github.com/Prism-Shadow/GDPevo">
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
          <a className="btn btn-ghost" href="https://github.com/Prism-Shadow/GDPevo/blob/main/experiments/EXPERIMENT_BOARD.md">
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
              <Lang en="Held-out accuracy lift from experience" zh="经验带来的 held-out 准确率提升" />
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
            Experience makes agents more accurate while spending <span className="accent">fewer</span> tokens.
          </span>
          <span className="lang-zh">
            经验让 agent 更准,同时花<span className="accent">更少</span>的 token。
          </span>
        </h2>
        <p className="lead">
          <span className="lang-en">
            Each group has 5 train and 5 held-out test tasks. We compare a cold-start baseline (<code>base</code>) against two learning modes: <code>demo</code> learns from worked examples, while <code>reflect</code> learns from its own mistakes. The score measures lift on tasks the agent never saw.
          </span>
          <span className="lang-zh">
            每组有 5 个 train、5 个 held-out test。我们用冷启动基线（<code>base</code>）对比两种学习模式：<code>demo</code> 从样例中学，<code>reflect</code> 从自己的错误中学；分数衡量的是 agent 在没见过的任务上的提升。
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
            <Lang en="Why can experience cost less? Read the blog →" zh="为什么有经验反而更省？阅读博客 →" />
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
            Each group is one shared business world with lookalike records mixed in, seeded from real-job sources such as <a href="https://openai.com/index/gdpval/" target="_blank" rel="noopener noreferrer">GDPVal</a> and <a href="https://github.com/amazon-science/SOP-Bench" target="_blank" rel="noopener noreferrer">SOP-Bench</a>.
          </span>
          <span className="lang-zh">
            每组都是一个共享的业务世界,混入了大量"长得很像"的干扰记录;场景来自像 <a href="https://openai.com/index/gdpval/" target="_blank" rel="noopener noreferrer">GDPVal</a> 和 <a href="https://github.com/amazon-science/SOP-Bench" target="_blank" rel="noopener noreferrer">SOP-Bench</a> 这样的真实工作任务源。
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
        <a className="footer-link" href="https://github.com/Prism-Shadow/GDPevo">github.com/Prism-Shadow/GDPevo</a>
      </div>
    </footer>
  );
}

export default function App() {
  const [lang, setLang] = useState(initialLang);
  const [themeChoice, setThemeChoice] = useState(initialThemeChoice);

  useEffect(() => {
    if (!window.location.hash) return;
    requestAnimationFrame(() => {
      document.querySelector(window.location.hash)?.scrollIntoView();
    });
  }, []);

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
      <Header lang={lang} setLang={setLang} themeChoice={themeChoice} setThemeChoice={setThemeChoice} />
      <main id="top">
        <Hero />
        <ResultsSection />
        <TasksSection />
      </main>
      <Footer />
    </>
  );
}
