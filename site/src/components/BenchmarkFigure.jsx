import { useState } from "react";
import { modes, summaryCards } from "../content/benchmark.js";
import { blogBenchmark } from "../content/blog.js";
import { Lang } from "../lib/i18n.jsx";

function metricValue(value) {
  return Number.parseFloat(String(value).replace(/[^\d.-]/g, ""));
}

const benchmarkMetrics = [
  {
    key: "acc",
    label: "ACC",
    column: "ACC",
    value: (row) => metricValue(row.acc),
    display: (row) => row.acc,
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
    label: "COST",
    column: "COST",
    value: (row) => metricValue(row.usd),
    display: (row) => `$${row.usd}`
  }
];

export function BenchmarkFigure({ className = "", modeLabels = {}, caption = blogBenchmark.caption }) {
  const [metricKey, setMetricKey] = useState("acc");
  const metric = benchmarkMetrics.find((item) => item.key === metricKey) ?? benchmarkMetrics[0];
  const metricMax = metric.max ?? Math.max(...summaryCards.flatMap((card) => card.rows.map(metric.value)), 1);
  const modeLabel = (mode) => modeLabels[mode] ?? mode;

  return (
    <figure className={["blog-benchmark-figure", className].filter(Boolean).join(" ")}>
      <figcaption className="blog-benchmark-head">
        <div className="blog-benchmark-copy">
          <span>
            <Lang {...caption} />
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
                {modeLabel(mode)}
              </i>
            ))}
          </span>
        </div>
      </figcaption>
      <div className="blog-benchmark-table">
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
                      <code>{modeLabel(row.mode)}</code>
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
      </div>
    </figure>
  );
}
