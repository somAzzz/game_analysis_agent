import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchFrontManifest } from "@/lib/api";
import type { FrontManifest, IssueCard, IssueKind, Severity } from "@/types";

type SortMode = "severity" | "anomalies" | "runs" | "title";
type KindFilter = "all" | IssueKind;
type SeverityFilter = "all" | Severity;

const SEVERITY_ORDER: Record<string, number> = {
  critical: 4,
  error: 3,
  warning: 2,
  info: 1,
};

export function FrontPage() {
  const [manifest, setManifest] = useState<FrontManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<KindFilter>("all");
  const [severity, setSeverity] = useState<SeverityFilter>("all");
  const [sort, setSort] = useState<SortMode>("severity");

  useEffect(() => {
    fetchFrontManifest()
      .then(setManifest)
      .catch((err) => setError(err.message ?? String(err)));
  }, []);

  const filteredIssues = useMemo(() => {
    if (!manifest) return [];
    const q = query.trim().toLowerCase();
    return manifest.issues
      .filter((card) => kind === "all" || card.kind === kind)
      .filter((card) => severity === "all" || card.severity === severity)
      .filter((card) => {
        if (!q) return true;
        return [
          card.title,
          card.subtitle,
          card.kind,
          card.severity,
          card.policy,
          card.scenario,
          card.difficulty,
          card.top_ending?.ending_id,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(q);
      })
      .sort((a, b) => {
        if (a.has_decision_graph !== b.has_decision_graph) {
          return a.has_decision_graph ? -1 : 1;
        }
        if (sort === "anomalies") return b.anomaly_total - a.anomaly_total;
        if (sort === "runs") return b.total_runs - a.total_runs;
        if (sort === "title") return a.title.localeCompare(b.title);
        const sev = (SEVERITY_ORDER[b.severity] ?? 0) - (SEVERITY_ORDER[a.severity] ?? 0);
        return sev || b.anomaly_total - a.anomaly_total;
      });
  }, [manifest, query, kind, severity, sort]);

  if (error) {
    return (
      <div className="state-message">
        <h1>Failed to load manifest</h1>
        <pre>{error}</pre>
        <p>
          Run <code>python tools/build_public_demo.py --copy-to-public</code> for
          the public demo, or <code>python tools/build_dashboard.py all</code> for
          private local reports.
        </p>
      </div>
    );
  }

  if (!manifest) {
    return <div className="state-message">Loading report index...</div>;
  }

  const { counts } = manifest;
  const sourceCounts = manifest.source_counts;
  const kindCounts = countBy(manifest.issues, "kind");
  const severityCounts = countBy(manifest.issues, "severity");

  return (
    <div>
      <header className="masthead">
        <span className="kicker">Vol. 0.4 · Traceable reports</span>
        <span className="issue-line">
          {manifest.public_demo ? "Public sanitized edition" : "Private local edition"}
        </span>
        <span className="date">{formatDate(manifest.generated_at)}</span>
      </header>

      <section className="banner">
        <div className="banner-inner">
          <div>
            <h1>
              The Analysis
              <br />
              <span className="accent">
                <em>Console</em>
              </span>
            </h1>
            <p className="deck" style={{ marginTop: 22 }}>
              A dashboard for simulation balance, boundary probes, and LLM
              playtests. It keeps the design-readability of the old report, but
              adds the controls needed to find risky runs, compare test cells,
              and trace how each public page was derived.
            </p>
          </div>
          <div className="meta-col">
            <strong>{String(counts.issues).padStart(2, "0")}</strong>
            <span>public report cards</span>
            <strong style={{ marginTop: 12 }}>{counts.decision_graphs}</strong>
            <span>safe graph demo</span>
          </div>
        </div>
      </section>

      {manifest.public_notice && (
        <div className="notice-strip">
          <strong>Public data boundary</strong>
          <span>{manifest.public_notice}</span>
          {sourceCounts && (
            <span>
              Source corpus: {sourceCounts.issues ?? 0} private issues,{" "}
              {sourceCounts.total_runs ?? 0} runs.
            </span>
          )}
        </div>
      )}

      <main>
        <div className="section-rule">
          <span className="num">01</span>
          <span className="label">Signal board</span>
        </div>
        <div className="kpi-strip">
          <div className="kpi">
            <span className="num">{counts.total_runs}</span>
            <span className="label">Runs represented</span>
          </div>
          <div className="kpi">
            <span className="num">
              <em>{counts.total_anomalies}</em>
            </span>
            <span className="label">Anomaly observations</span>
            <span className="label" style={{ color: "var(--accent-deep)" }}>
              {counts.total_critical} critical cards
            </span>
          </div>
          <div className="kpi">
            <span className="num">{kindCounts.balance ?? 0}</span>
            <span className="label">Balance cells</span>
          </div>
          <div className="kpi">
            <span className="num">
              <em>{counts.decision_graphs}</em>
            </span>
            <span className="label">Decision graphs</span>
          </div>
        </div>

        <section className="dashboard-controls" aria-label="Report filters">
          <label className="search-box">
            <span>Search reports</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="policy, scenario, outcome, severity..."
            />
          </label>
          <SegmentedControl
            label="Kind"
            value={kind}
            options={[
              ["all", `All (${manifest.issues.length})`],
              ["balance", `Balance (${kindCounts.balance ?? 0})`],
              ["boundary", `Boundary (${kindCounts.boundary ?? 0})`],
              ["play", `Play (${kindCounts.play ?? 0})`],
            ]}
            onChange={(value) => setKind(value as KindFilter)}
          />
          <SegmentedControl
            label="Severity"
            value={severity}
            options={[
              ["all", "All"],
              ["critical", `Critical (${severityCounts.critical ?? 0})`],
              ["warning", `Warning (${severityCounts.warning ?? 0})`],
              ["info", `Info (${severityCounts.info ?? 0})`],
            ]}
            onChange={(value) => setSeverity(value as SeverityFilter)}
          />
          <label className="select-box">
            <span>Sort</span>
            <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)}>
              <option value="severity">Severity first</option>
              <option value="anomalies">Most anomalies</option>
              <option value="runs">Most runs</option>
              <option value="title">Title</option>
            </select>
          </label>
        </section>

        <div className="section-rule">
          <span className="num">02</span>
          <span className="label">
            {filteredIssues.length} visible report{filteredIssues.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="issue-shelf">
          {filteredIssues.map((card, idx) => (
            <IssueCardView key={`${card.kind}-${card.id}`} card={card} idx={idx} />
          ))}
        </div>

        {filteredIssues.length === 0 && (
          <div className="empty-panel">No reports match the current filters.</div>
        )}

        <div className="byline-rule">
          Game Analysis Agent · Reports Index · {formatDate(manifest.generated_at)}
        </div>
      </main>
    </div>
  );
}

function IssueCardView({ card, idx }: { card: IssueCard; idx: number }) {
  const topEnding = card.top_ending?.ending_id ?? "n/a";
  const topRate = card.top_ending ? `${(card.top_ending.rate * 100).toFixed(1)}%` : "n/a";
  return (
    <Link
      to={`/issue/${card.kind}/${encodeURIComponent(card.id)}`}
      className={`issue-card ${card.has_decision_graph ? "is-featured" : ""}`}
    >
      <span className="issue-num">
        #{String(idx + 1).padStart(2, "0")} · {card.kind.toUpperCase()}
        {card.has_decision_graph ? " · GRAPH" : ""}
      </span>
      {card.has_decision_graph && (
        <span className="graph-ribbon">Open decision graph</span>
      )}
      <h3>{card.title}</h3>
      <div className="deck">{card.subtitle || "(no subtitle)"}</div>
      <div className="chip-row">
        {card.policy && <span>{card.policy}</span>}
        {card.scenario && <span>{card.scenario}</span>}
        {card.difficulty && <span>{card.difficulty}</span>}
      </div>
      <div className="stats">
        <span>
          runs
          <strong>{card.total_runs}</strong>
        </span>
        <span>
          top outcome
          <strong style={{ fontSize: 13 }}>{truncate(topEnding, 24)}</strong>
        </span>
        <span>
          anomalies
          <strong>{card.anomaly_total}</strong>
        </span>
      </div>
      <div style={{ marginTop: 10 }}>
        <span className={`severity-badge ${card.severity}`}>
          {card.severity}
        </span>
        <span className="microcopy">top outcome rate · {topRate}</span>
      </div>
    </Link>
  );
}

function SegmentedControl({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (value: string) => void;
}) {
  return (
    <fieldset className="segmented">
      <legend>{label}</legend>
      <div>
        {options.map(([optionValue, optionLabel]) => (
          <button
            key={optionValue}
            type="button"
            className={value === optionValue ? "active" : ""}
            onClick={() => onChange(optionValue)}
          >
            {optionLabel}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function countBy<T, K extends keyof T>(items: T[], key: K): Record<string, number> {
  return items.reduce<Record<string, number>>((acc, item) => {
    const value = String(item[key] ?? "unknown");
    acc[value] = (acc[value] ?? 0) + 1;
    return acc;
  }, {});
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toUTCString();
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}...` : value;
}
