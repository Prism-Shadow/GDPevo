import { useState } from "react";
import { blogBenchmark, blogConstruction, blogFindings, blogIntro, blogInvite, blogUsage, citation } from "../content/blog.js";
import { modes, summaryCards } from "../content/benchmark.js";
import { Lang, LocalizedMarkdown, LocalizedParagraph } from "../lib/i18n.jsx";
import { links } from "../content/links.js";

function metricValue(value) {
  return Number.parseFloat(String(value).replace(/[^\d.-]/g, ""));
}

const benchmarkMetrics = [
  {
    key: "avg",
    label: "AVG@3",
    column: "AVG@3",
    value: (row) => metricValue(row.avg),
    display: (row) => row.avg,
    max: 100
  },
  {
    key: "tokens",
    label: "TOKENS",
    column: "TOKENS (K)",
    value: (row) => metricValue(row.tokens),
    display: (row) => `${row.tokens}k`
  },
  {
    key: "usd",
    label: "USD",
    column: "USD",
    value: (row) => metricValue(row.usd),
    display: (row) => `$${row.usd}`
  }
];

function BlogBenchmarkFigure() {
  const [metricKey, setMetricKey] = useState("avg");
  const metric = benchmarkMetrics.find((item) => item.key === metricKey) ?? benchmarkMetrics[0];
  const metricMax = metric.max ?? Math.max(...summaryCards.flatMap((card) => card.rows.map(metric.value)), 1);

  return (
    <figure className="blog-benchmark-figure">
      <figcaption className="blog-benchmark-head">
        <div className="blog-benchmark-copy">
          <span>
            <Lang {...blogBenchmark.caption} />
          </span>
        </div>
        <div className="blog-benchmark-tools">
          <div className="blog-metric-toggle" role="group" aria-label="Metric">
            {benchmarkMetrics.map((item) => (
              <button
                type="button"
                key={item.key}
                className={item.key === metric.key ? "is-active" : ""}
                aria-pressed={item.key === metric.key}
                onClick={() => setMetricKey(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <span className="blog-benchmark-legend" aria-label="Chart legend">
            {modes.map((mode) => (
              <i key={mode}>
                <b className={`sw sw-${mode}`} />
                {mode}
              </i>
            ))}
          </span>
        </div>
      </figcaption>
      <div className="blog-benchmark-cols">
        <span>{blogBenchmark.columns.harness}</span>
        <span>{blogBenchmark.columns.model}</span>
        <span>{blogBenchmark.columns.mode}</span>
        <span>{metric.column}</span>
      </div>
      <div className="blog-benchmark-rows">
        {summaryCards.map((card) => {
          const [harness, model] = card.title.split(" · ");
          return (
            <div className="blog-benchmark-group" key={card.title}>
              <div className="blog-benchmark-name">
                <strong>{harness}</strong>
              </div>
              <div className="blog-benchmark-model">
                <strong>{model}</strong>
                <small>{card.thinking}</small>
              </div>
              <div className="blog-benchmark-bars">
                {card.rows.map((row) => (
                  <div className={`blog-benchmark-bar mode-${row.mode}`} key={row.mode}>
                    <code>{row.mode}</code>
                    <div className="blog-benchmark-measure">
                      <div className="blog-benchmark-track">
                        <span style={{ "--w": `${(metric.value(row) / metricMax) * 100}%` }} />
                      </div>
                      <b>{metric.display(row)}</b>
                    </div>
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

function BlogIntro() {
  return (
    <section className="section blog-head">
      <div className="wrap narrow">
        <h1 className="h2 blog-title">
          <Lang {...blogIntro.title} />
        </h1>
        <blockquote className="lead blog-quote">
          <LocalizedMarkdown copy={blogIntro.lead} />
        </blockquote>
        <div className="prose">
          {blogIntro.paragraphs.map((paragraph) => (
            <LocalizedParagraph key={paragraph.key} copy={paragraph} />
          ))}
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
          <Lang {...blogConstruction.heading} />
        </h2>
        <p className="lead">
          <LocalizedMarkdown copy={blogConstruction.lead} />
        </p>

        <h3 className="h3 h3-spaced h3-spaced-sm">
          <Lang {...blogConstruction.agentHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogConstruction.pipeline} />
        </div>
        <figure className="pipeline-figure">
          <img src="assets/gdpevo-pipeline.png" alt={blogConstruction.pipelineImageAlt} loading="lazy" />
        </figure>

        <h3 className="h3 h3-spaced">
          <Lang {...blogConstruction.hiddenHeading} />
        </h3>
        <div className="prose">
          {blogConstruction.hiddenRules.map((paragraph) => (
            <LocalizedParagraph key={paragraph.key} copy={paragraph} />
          ))}
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
          <Lang {...blogUsage.heading} />
        </h2>
        <p className="lead">
          <LocalizedMarkdown copy={blogUsage.lead} />
        </p>

        <h3 className="h3 h3-spaced">
          <Lang {...blogUsage.gradingHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogUsage.grading} />
        </div>

        <h3 className="h3 h3-spaced" id="cost">
          <Lang {...blogUsage.costHeading} />
        </h3>
        <div className="prose">
          <LocalizedParagraph copy={blogUsage.cost} />
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
          <Lang {...blogFindings.heading} />
        </h2>
        <div className="prose">
          {blogFindings.intro.map((paragraph) => (
            <LocalizedParagraph key={paragraph.key} copy={paragraph} />
          ))}
          <ul className="bullets">
            {blogFindings.modes.map((mode) => (
              <li key={mode.key}>
                <LocalizedMarkdown copy={mode} />
              </li>
            ))}
          </ul>
        </div>

        <BlogBenchmarkFigure />
        <p className="note">
          <LocalizedMarkdown copy={blogFindings.note} />
        </p>
        <p className="prose-link">
          <a href="index.html#results">
            <Lang {...blogBenchmark.breakdownLink} />
          </a>
        </p>
      </div>
    </section>
  );
}

function BlogInvite() {
  const [copied, setCopied] = useState(false);
  const { actions, copy } = blogInvite;

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
          <Lang {...blogInvite.heading} />
        </h2>
        <div className="prose">
          <LocalizedParagraph copy={blogInvite.paragraph} />
        </div>
        <div className="btn-row invite-actions">
          <a className="btn btn-dark" href={links.repo} target="_blank" rel="noreferrer">
            <span>{actions.github}</span>
          </a>
          <a className="btn btn-ghost" href={links.experimentBoard} target="_blank" rel="noreferrer">
            <span>
              <Lang {...actions.experimentBoard} />
            </span>
          </a>
          <a className="btn btn-ghost" href={links.evalWorkspace} target="_blank" rel="noreferrer">
            <span>
              <Lang {...actions.evalWorkspace} />
            </span>
          </a>
        </div>
        <div className="bibtex">
          <button type="button" className={`copy-btn ${copied ? "copied" : ""}`} aria-label={copy.ariaLabel} onClick={copyCitation}>
            <Lang {...(copied ? copy.copiedLabel : copy.label)} />
          </button>
          <pre><code>{citation}</code></pre>
        </div>
      </div>
    </section>
  );
}

export function BlogPage() {
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
