import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { fetchDecisionGraphManifest, fetchIssueManifest } from "@/lib/api";
import { DecisionGraphExplorer } from "@/pages/DecisionGraphPage";
import type {
  AnomalyRow,
  DecisionGraphManifest,
  IssueManifest,
  ValueFinding,
  WeeklyPoint,
} from "@/types";

const SPARK_METRICS: { key: string; color: string; label: string }[] = [
  { key: "stress", color: "var(--accent)", label: "stress" },
  { key: "hunger", color: "var(--warn)", label: "hunger" },
  { key: "money", color: "var(--forest)", label: "money" },
  { key: "academic_progress", color: "var(--ink)", label: "academic" },
];

export function IssuePage() {
  const { kind, id } = useParams<{ kind: string; id: string }>();
  const [manifest, setManifest] = useState<IssueManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const decodedId = id ? decodeURIComponent(id) : "";

  useEffect(() => {
    if (!kind || !decodedId) return;
    fetchIssueManifest(kind, decodedId)
      .then(setManifest)
      .catch((err) => setError(err.message ?? String(err)));
  }, [kind, decodedId]);

  if (error) {
    return (
      <div style={{ padding: 60 }}>
        <h1>Issue not found</h1>
        <pre
          style={{
            background: "var(--paper-deep)",
            padding: 18,
            fontFamily: "var(--mono)",
            fontSize: 12,
            color: "var(--ink-soft)",
            whiteSpace: "pre-wrap",
          }}
        >
          {error}
        </pre>
        <Link to="/">← Back to front page</Link>
      </div>
    );
  }

  if (!manifest) {
    return <div style={{ padding: 60 }}>Loading issue…</div>;
  }

  return (
    <div>
      <Cover manifest={manifest} />

      {manifest.gate_report && (
        <div
          style={{
            padding: "0 60px",
            marginTop: 24,
          }}
        >
          <GateBanner report={manifest.gate_report} />
        </div>
      )}

      <nav className="tab-rail">
        <a href="#findings">Findings</a>
        <a href="#pulse">Pulse</a>
        <a href="#value">Value findings</a>
        <a href="#agents">Agent columns</a>
        {manifest.anomalies.length > 0 && <a href="#anomalies">Anomalies</a>}
        {manifest.hasOwnProperty("source_summary") && <a href="#trace">Trace</a>}
        {manifest.kind === "balance" && (
          <a className="tab-cta" href="#decision-graph">
            Decision graph
          </a>
        )}
      </nav>

      <main>
        <TracePanel manifest={manifest} />
        <EndingGrid manifest={manifest} />
        {manifest.kind === "balance" && <EmbeddedDecisionGraph issueId={manifest.id} />}
        <PulseSection manifest={manifest} />
        <ValueFindingsSection manifest={manifest} />
        <AnomaliesSection manifest={manifest} />
        <AgentColumns manifest={manifest} />
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

function Cover({ manifest }: { manifest: IssueManifest }) {
  const summary = manifest.summary ?? {};
  const subtitle = [
    manifest.source_summary?.source_scenario ?? summary.scenario,
    manifest.source_summary?.source_policy ?? summary.policy,
    manifest.source_summary?.source_difficulty ?? summary.difficulty,
  ]
    .filter(Boolean)
    .join(" / ");
  return (
    <section className="cover">
      <div className="issue-meta">
        <span>
          <strong>{manifest.raw_runs_count || 0}</strong>
          runs simulated
        </span>
        <span>
          <strong>{manifest.anomalies.length}</strong>
          anomalies surfaced
        </span>
        <span>
          <strong>{manifest.value_findings.length}</strong>
          value findings
        </span>
        <span>
          <strong>{Object.keys(manifest.agent_markdown ?? {}).length}</strong>
          agent outputs
        </span>
        {manifest.public_demo && (
          <span>
            <strong>PUBLIC</strong>
            sanitized dataset
          </span>
        )}
      </div>
      <h1>{manifest.id.replace(/-/g, " ")}</h1>
      <p className="deck">
        {subtitle
          ? `${manifest.kind} issue · ${subtitle}`
          : `${manifest.kind} issue`}
      </p>
    </section>
  );
}

function EmbeddedDecisionGraph({ issueId }: { issueId: string }) {
  const [manifest, setManifest] = useState<DecisionGraphManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDecisionGraphManifest(issueId, 0)
      .then(setManifest)
      .catch((err) => setError(err.message ?? String(err)));
  }, [issueId]);

  return (
    <section
      id="decision-graph"
      className="graph-spotlight graph-spotlight-embedded"
      aria-label="Decision graph"
    >
      <div className="graph-spotlight-copy">
        <span className="graph-eyebrow">Interactive flow map</span>
        <h2>Decision graph</h2>
        <p>
          Highlighted path plus mock branches. Click any node to inspect route
          options.
        </p>
      </div>
      {error && <div className="graph-inline-state">Graph unavailable: {error}</div>}
      {!error && !manifest && <div className="graph-inline-state">Loading graph...</div>}
      {manifest && <DecisionGraphExplorer manifest={manifest} embedded />}
    </section>
  );
}

function TracePanel({ manifest }: { manifest: IssueManifest }) {
  const summary = manifest.summary ?? {};
  return (
    <section id="trace" className="trace-panel">
      <div>
        <h2>Traceability</h2>
        <p>
          {manifest.public_notice ??
            "This view is backed by a generated manifest. Use the report manifest for replay-level debugging."}
        </p>
      </div>
      <dl>
        <div>
          <dt>report kind</dt>
          <dd>{manifest.kind}</dd>
        </div>
        <div>
          <dt>runs</dt>
          <dd>{manifest.raw_runs_count || String(summary.total_runs ?? "n/a")}</dd>
        </div>
        <div>
          <dt>scenario</dt>
          <dd>{String(manifest.source_summary?.source_scenario ?? summary.scenario ?? "n/a")}</dd>
        </div>
        <div>
          <dt>policy</dt>
          <dd>{String(manifest.source_summary?.source_policy ?? summary.policy ?? "mixed")}</dd>
        </div>
      </dl>
    </section>
  );
}

function GateBanner({ report }: { report: NonNullable<IssueManifest["gate_report"]> }) {
  const passed = !!report.passed;
  const failures = report.failures ?? [];
  if (passed) {
    return <div className="gate-pass">GATE PASS — every check honoured</div>;
  }
  return (
    <div className="gate-fail">
      GATE FAIL — {failures.length} violation(s):{" "}
      {failures
        .map((f) => f.gate)
        .slice(0, 4)
        .join(", ")}
    </div>
  );
}

function EndingGrid({ manifest }: { manifest: IssueManifest }) {
  if (manifest.endings.length === 0) return null;
  return (
    <section id="findings" className="endgrid">
      <div>
        <h3
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: 32,
            fontVariationSettings: '"opsz" 96, "wght" 380, "SOFT" 100',
            margin: "0 0 12px",
          }}
        >
          Where the runs came to rest
        </h3>
        <div className="endtable">
          <table>
            <thead>
              <tr>
                <th>policy</th>
                <th>ending</th>
                <th className="right">n</th>
                <th className="right">rate</th>
              </tr>
            </thead>
            <tbody>
              {manifest.endings.slice(0, 12).map((row, i) => {
                const rate = parseFloat(row.rate ?? "0") || 0;
                return (
                  <tr key={`${row.policy}-${row.ending_id}-${i}`}>
                    <td>{row.policy}</td>
                    <td>{row.ending_id}</td>
                    <td className="right">{row.count}</td>
                    <td className="right">
                      <span
                        className="bar"
                        style={{ width: `${Math.min(rate * 80, 240)}px` }}
                      />
                      {rate.toFixed(3)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      <div>
        <h3
          style={{
            fontFamily: "var(--serif)",
            fontStyle: "italic",
            fontSize: 32,
            fontVariationSettings: '"opsz" 96, "wght" 380, "SOFT" 100',
            margin: "0 0 12px",
          }}
        >
          Actions at the top of the heap
        </h3>
        <div className="endtable">
          <table>
            <thead>
              <tr>
                <th>policy</th>
                <th>action_id</th>
                <th className="right">rate/run</th>
              </tr>
            </thead>
            <tbody>
              {manifest.actions.slice(0, 12).map((row, i) => (
                <tr key={`${row.policy}-${row.action_id}-${i}`}>
                  <td>{row.policy}</td>
                  <td>{row.action_id}</td>
                  <td className="right">
                    {parseFloat(row.rate_per_run ?? "0").toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function PulseSection({ manifest }: { manifest: IssueManifest }) {
  const series = manifest.weekly_series ?? {};
  const blocks = SPARK_METRICS.flatMap((m) => {
    const pts = series[m.key] ?? [];
    if (pts.length === 0) return [];
    return [{ metric: m, points: pts }];
  });
  if (blocks.length === 0) return null;
  return (
    <section id="pulse" style={{ marginTop: 32 }}>
      <h2
        style={{
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 36,
          fontVariationSettings: '"opsz" 96, "wght" 360, "SOFT" 100',
          margin: "0 0 16px",
        }}
      >
        Pulse of the simulation
      </h2>
      <p
        style={{
          fontStyle: "italic",
          color: "var(--ink-soft)",
          fontSize: 16,
          margin: "0 0 18px",
        }}
      >
        Four key metrics, drawn week by week. Solid line is the cohort mean;
        stroke-dashoffset animation reveals the line on mount.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 18,
        }}
      >
        {blocks.map((b) => (
          <SparkBlock key={b.metric.key} metric={b.metric.key} color={b.metric.color} points={b.points} />
        ))}
      </div>
    </section>
  );
}

function SparkBlock({
  metric,
  color,
  points,
}: {
  metric: string;
  color: string;
  points: WeeklyPoint[];
}) {
  const W = 720, H = 160;
  const xs = points.map((p) => p.week);
  const ys = points.flatMap((p) => [p.mean, p.p10, p.p90]);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs, xMin + 1);
  const yMin = Math.min(...ys);
  const yMax = Math.max(...ys, yMin + 1);
  const path = points
    .map((p, i) => {
      const px = ((p.week - xMin) / (xMax - xMin)) * (W - 20) + 10;
      const py = (1 - (p.mean - yMin) / (yMax - yMin)) * (H - 30) + 10;
      return `${i === 0 ? "M" : "L"} ${px.toFixed(1)} ${py.toFixed(1)}`;
    })
    .join(" ");
  const bandTop = points
    .map((p, i) => {
      const px = ((p.week - xMin) / (xMax - xMin)) * (W - 20) + 10;
      const py = (1 - (p.p90 - yMin) / (yMax - yMin)) * (H - 40) + 12;
      return `${i === 0 ? "M" : "L"} ${px.toFixed(1)} ${py.toFixed(1)}`;
    })
    .join(" ");
  const bandBottom = [...points]
    .reverse()
    .map((p) => {
      const px = ((p.week - xMin) / (xMax - xMin)) * (W - 20) + 10;
      const py = (1 - (p.p10 - yMin) / (yMax - yMin)) * (H - 40) + 12;
      return `L ${px.toFixed(1)} ${py.toFixed(1)}`;
    })
    .join(" ");
  const band = `${bandTop} ${bandBottom} Z`;
  const last = points[points.length - 1];
  const lx = ((last.week - xMin) / (xMax - xMin)) * (W - 20) + 10;
  const ly = (1 - (last.mean - yMin) / (yMax - yMin)) * (H - 30) + 10;
  return (
    <div className="sparkblock">
      <h4>{metric}</h4>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${metric} by week`}>
        <path d={band} fill={color} opacity={0.14} />
        <path
          className="sparkline-path"
          d={path}
          stroke={color}
          strokeWidth={2}
          fill="none"
        />
        <circle cx={lx} cy={ly} r={3} fill={color} />
      </svg>
      <div className="spark-meta">
        mean {last.mean.toFixed(1)} · p10 {last.p10.toFixed(1)} · p90 {last.p90.toFixed(1)}
      </div>
    </div>
  );
}

function ValueFindingsSection({ manifest }: { manifest: IssueManifest }) {
  const findings = [
    ...manifest.value_findings,
    ...flattenRouteFindings(manifest),
  ].slice(0, 12);
  if (findings.length === 0) return null;
  return (
    <section id="value" style={{ marginTop: 48 }}>
      <h2
        style={{
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 32,
          fontVariationSettings: '"opsz" 96, "wght" 360, "SOFT" 100',
          margin: "0 0 16px",
        }}
      >
        What the number nerds found
      </h2>
      <div className="endtable">
        <table>
          <thead>
            <tr>
              <th>sev</th>
              <th>finding</th>
              <th className="right">value</th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f) => (
              <tr key={f.finding_id}>
                <td>
                  <span className={`severity-badge ${f.severity}`}>
                    {f.severity}
                  </span>
                </td>
                <td>{f.description.slice(0, 200)}</td>
                <td className="right">{String(f.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AnomaliesSection({ manifest }: { manifest: IssueManifest }) {
  if (manifest.anomalies.length === 0) return null;
  const groups = groupAnomalies(manifest.anomalies);
  return (
    <section id="anomalies" style={{ marginTop: 48 }}>
      <h2
        style={{
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 32,
          fontVariationSettings: '"opsz" 96, "wght" 360, "SOFT" 100',
          margin: "0 0 16px",
        }}
      >
        Anomaly marginalia
      </h2>
      <div className="anomaly-summary">
        {groups.slice(0, 6).map((group) => (
          <span key={`${group.kind}-${group.severity}`}>
            <strong>{group.count}</strong> {group.kind} · {group.severity}
          </span>
        ))}
      </div>
      <div className="anomaly-list">
        {manifest.anomalies.slice(0, 12).map((a, idx) => (
          <div
            key={`${a.kind}-${a.run_id}-${a.week}-${idx}`}
            style={{ padding: "6px 0", borderBottom: "1px dotted var(--rule)" }}
          >
            <span
              style={{
                display: "inline-block",
                width: 22,
                height: 22,
                border: "1px solid var(--ink)",
                borderRadius: "50%",
                textAlign: "center",
                lineHeight: "20px",
                fontFamily: "var(--serif)",
                fontSize: 13,
                color: "var(--accent)",
                marginRight: 12,
              }}
            >
              {idx + 1}
            </span>
            <span>
              #{idx + 1} · {a.kind} · run {a.run_id}, w{a.week}, {a.severity}
            </span>
            {a.message && (
              <span style={{ marginLeft: 12, color: "var(--muted)" }}>
                — {a.message.slice(0, 100)}
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function AgentColumns({ manifest }: { manifest: IssueManifest }) {
  const sections = useMemo(() => {
    const items: { label: string; md: string }[] = [];
    for (const a of manifest.agents) {
      const key = a.file.replace(".md", "");
      const md =
        (manifest.agent_markdown as Record<string, string>)[key] ?? "";
      if (md.trim()) {
        items.push({ label: a.label, md });
      }
    }
    return items;
  }, [manifest.agents, manifest.agent_markdown]);

  if (sections.length === 0) return null;
  return (
    <div id="agents" style={{ marginTop: 48 }}>
      {sections.map((s, idx) => (
        <article
          key={s.label}
          className="article fade-in"
          style={
            idx === 0
              ? undefined
              : { borderTop: 0 }
          }
        >
          <div className="column">
            <ReactMarkdown>{s.md}</ReactMarkdown>
          </div>
          <aside className="marginalia">
            <h4>{s.label}</h4>
            <div style={{ fontSize: 11, color: "var(--muted)" }}>
              {s.md.length} chars · rendered with react-markdown
            </div>
          </aside>
        </article>
      ))}
    </div>
  );
}

function flattenRouteFindings(manifest: IssueManifest): ValueFinding[] {
  return Object.values(manifest.route_findings ?? {}).flatMap((rows) => rows ?? []);
}

function groupAnomalies(rows: AnomalyRow[]): { kind: string; severity: string; count: number }[] {
  const counts = new Map<string, { kind: string; severity: string; count: number }>();
  for (const row of rows) {
    const key = `${row.kind}:${row.severity}`;
    const current = counts.get(key) ?? { kind: row.kind, severity: row.severity, count: 0 };
    current.count += 1;
    counts.set(key, current);
  }
  return [...counts.values()].sort((a, b) => b.count - a.count);
}
