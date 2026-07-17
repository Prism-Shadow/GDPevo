import { useMemo, useState } from "react";
import { leaderboardDataset, leaderboardModes, modes, summaryCards } from "../content/benchmark.js";
import { blogBenchmark } from "../content/blog.js";
import { Lang } from "../lib/i18n.jsx";

function metricValue(value) {
  return Number.parseFloat(String(value).replace(/[^\d.-]/g, ""));
}

const summaryMetrics = [
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

const benchmarkMetrics = [
  {
    key: "acc",
    label: { en: "ACC", zh: "准确率" },
    direction: "desc",
    max: 100,
    display: (value) => `${value.toFixed(2)}%`
  },
  {
    key: "lift",
    label: { en: "LIFT", zh: "准确率提升" },
    direction: "desc",
    display: (value) => (value === 0 ? "—" : `+${value.toFixed(2)} pp`)
  },
  {
    key: "cost",
    label: { en: "COST", zh: "费用" },
    direction: "asc",
    display: (value) => `$${value < 0.1 ? value.toFixed(3) : value.toFixed(2)}`
  },
  {
    key: "rounds",
    label: { en: "ROUNDS", zh: "轮次" },
    direction: "asc",
    display: (value) => value.toFixed(2)
  },
  {
    key: "tokens",
    label: { en: "TOKENS", zh: "令牌数" },
    direction: "asc",
    display: (value) => `${value.toFixed(1)}k`
  }
];

const methodLabels = {
  "skill-creator": "Skill Creator",
  "agent-training": "Agent Training"
};

function compareRows(left, right, sort) {
  const valueDelta = left[sort.key] - right[sort.key];
  if (valueDelta !== 0) return sort.direction === "asc" ? valueDelta : -valueDelta;
  return `${left.model}-${left.mode}`.localeCompare(`${right.model}-${right.mode}`);
}

function SummaryBenchmarkFigure({ className = "", modeLabels = {}, caption = blogBenchmark.caption }) {
  const [metricKey, setMetricKey] = useState("acc");
  const metric = summaryMetrics.find((item) => item.key === metricKey) ?? summaryMetrics[0];
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
            {summaryMetrics.map((item) => (
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

function LeaderboardBenchmarkFigure({ className = "", modeLabels = {}, caption = blogBenchmark.caption }) {
  const [sort, setSort] = useState({ key: "acc", direction: "desc" });
  const dataset = leaderboardDataset;
  const versionRows = dataset.rows;
  const activeMetric = benchmarkMetrics.find((metric) => metric.key === sort.key) ?? benchmarkMetrics[0];
  const activeMax = activeMetric.max
    ?? Math.max(...versionRows.map((row) => Math.abs(row[activeMetric.key])), 1);
  const orderedMetrics = [
    activeMetric,
    ...benchmarkMetrics.filter((metric) => metric.key !== activeMetric.key)
  ];
  const modeLabel = (mode) => modeLabels[mode] ?? mode;
  const rows = useMemo(
    () => [...versionRows].sort((left, right) => compareRows(left, right, sort)),
    [sort, versionRows]
  );

  const selectMetric = (metric) => {
    setSort((current) => ({
      key: metric.key,
      direction:
        current.key === metric.key
          ? current.direction === "asc" ? "desc" : "asc"
          : metric.direction
    }));
  };

  return (
    <figure className={["blog-benchmark-figure", "blog-leaderboard", className].filter(Boolean).join(" ")}>
      <figcaption className="blog-benchmark-head">
        <div className="blog-benchmark-copy">
          <strong>
            <Lang en="GDPevo Benchmark Leaderboard" zh="GDPevo 评测排行榜" />
          </strong>
          <span>
            <Lang {...caption} />
            <em className="blog-benchmark-range">
              <Lang
                en={`task groups ${dataset.taskRange}`}
                zh={`任务组 ${dataset.taskRange}`}
              />
            </em>
          </span>
        </div>
        <div className="blog-benchmark-actions">
          <span className="blog-benchmark-legend" aria-label="Chart legend">
            {leaderboardModes.map((mode) => (
              <i key={mode}>
                <b className={`sw sw-${mode}`} />
                {modeLabel(mode)}
              </i>
            ))}
          </span>
        </div>
      </figcaption>

      <div className="blog-benchmark-table" id="gdpevo-leaderboard">
        <table>
          <thead>
            <tr>
              <th className="rank-column" scope="col">#</th>
              <th className="model-column" scope="col">
                <Lang en="Model" zh="模型" />
              </th>
              <th className="harness-column" scope="col">Harness</th>
              <th className="mode-column" scope="col">
                <Lang en="Evolution source" zh="进化来源" />
              </th>
              <th className="method-column" scope="col">
                <Lang en="Evolution method" zh="进化方法" />
              </th>
              {orderedMetrics.map((metric) => {
                const isActive = metric.key === activeMetric.key;
                return (
                  <th
                    className={["metric-column", isActive ? "is-active" : ""].filter(Boolean).join(" ")}
                    scope="col"
                    key={metric.key}
                    aria-sort={isActive ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}
                  >
                    <button type="button" onClick={() => selectMetric(metric)}>
                      <span className="metric-heading">
                        <Lang {...metric.label} />
                        <span className="sort-arrow" aria-hidden="true">
                          {isActive ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}
                        </span>
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr className={`mode-${row.mode}`} key={row.id}>
                <td className="rank-column">
                  <span className={index < 3 ? `rank rank-${index + 1}` : "rank"}>{index + 1}</span>
                </td>
                <th className="model-column" scope="row">
                  <strong>{row.model}</strong>
                  <small>{row.thinking}</small>
                </th>
                <td className="harness-column">{row.harness}</td>
                <td className="mode-column">
                  <code>
                    <i aria-hidden="true" />
                    {modeLabel(row.mode)}
                  </code>
                </td>
                <td className="method-column">
                  {row.mode === "base" ? "-" : methodLabels[row.method]}
                </td>
                {orderedMetrics.map((metric) => {
                  const isActive = metric.key === activeMetric.key;
                  return (
                    <td
                      className={["metric-column", isActive ? "is-active" : ""].filter(Boolean).join(" ")}
                      key={metric.key}
                    >
                      {isActive ? (
                        <div className="leaderboard-measure">
                          <div className="leaderboard-track" aria-hidden="true">
                            <span style={{ "--w": `${(Math.abs(row[metric.key]) / activeMax) * 100}%` }} />
                          </div>
                          <b>{metric.display(row[metric.key])}</b>
                        </div>
                      ) : (
                        <span className="metric-value">{metric.display(row[metric.key])}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

export function BenchmarkFigure({ variant = "summary", ...props }) {
  if (variant === "leaderboard") return <LeaderboardBenchmarkFigure {...props} />;
  return <SummaryBenchmarkFigure {...props} />;
}
