import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchFrontManifest } from "@/lib/api";
import type { FrontManifest, IssueCard } from "@/types";

/**
 * The front page — magazine cover with KPI strip + issue shelf.
 * Mirrors the static front_page.html the Python pipeline used to emit.
 */
export function FrontPage() {
  const [manifest, setManifest] = useState<FrontManifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchFrontManifest()
      .then(setManifest)
      .catch((err) => setError(err.message ?? String(err)));
  }, []);

  if (error) {
    return (
      <div style={{ padding: 60 }}>
        <h1 style={{ color: "var(--critical)" }}>Failed to load manifest</h1>
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
        <p style={{ fontFamily: "var(--body)", color: "var(--ink-soft)" }}>
          Make sure you ran <code>python tools/emit_manifest.py</code> and (for
          development) copied the JSON into <code>frontend/public/</code>.
        </p>
      </div>
    );
  }

  if (!manifest) {
    return <div style={{ padding: 60 }}>Loading…</div>;
  }

  const { counts, issues } = manifest;

  return (
    <div>
      <header className="masthead">
        <span className="kicker">Vol. 0.3 · Field reports</span>
        <span className="issue-line">No. ∞ · A continuous publication</span>
        <span className="date">{new Date(manifest.generated_at).toUTCString()}</span>
      </header>

      <section className="banner">
        <div className="banner-inner">
          <div>
            <h1>
              The Analytical
              <br />
              <span className="accent">
                <em>Review</em>
              </span>
            </h1>
            <p className="deck" style={{ marginTop: 22 }}>
              A field journal from the <em>study-in-germany</em> development
              pipeline — where <span className="mn">godot</span> runs ten
              thousand weeks, Python finds the rules the engine forgot, and
              seven language models argue about which ending feels earned.
              <br />
              <span style={{ fontSize: 14 }}>
                Now served as a <em>React + React Flow</em> single-page app.
              </span>
            </p>
          </div>
          <div className="meta-col">
            <strong>{String(counts.issues).padStart(2, "0")}</strong>
            <span>issues in print</span>
            <strong style={{ marginTop: 12 }}>{counts.decision_graphs}</strong>
            <span>decision graphs</span>
          </div>
        </div>
      </section>

      <main>
        <div className="section-rule">
          <span className="num">§I</span>
          <span className="label">The numbers that didn&apos;t lie</span>
        </div>
        <div className="kpi-strip">
          <div className="kpi">
            <span className="num">{counts.total_runs}</span>
            <span className="label">Total weeks simulated</span>
          </div>
          <div className="kpi">
            <span className="num">
              <em>{counts.total_anomalies}</em>
            </span>
            <span className="label">Anomalies surfaced</span>
            <span className="label" style={{ color: "var(--accent-deep)" }}>
              {counts.total_critical} critical
            </span>
          </div>
          <div className="kpi">
            <span className="num">{counts.issues}</span>
            <span className="label">Issues</span>
          </div>
          <div className="kpi">
            <span className="num">
              <em>{counts.decision_graphs}</em>
            </span>
            <span className="label">Decision graphs</span>
          </div>
        </div>

        <div className="section-rule">
          <span className="num">§II</span>
          <span className="label">
            In this edition — issues to read cover-to-cover
          </span>
        </div>
        <div className="issue-shelf">
          {issues.slice(0, 24).map((card, idx) => (
            <IssueCardView key={`${card.kind}-${card.id}`} card={card} idx={idx} />
          ))}
        </div>

        <div
          className="byline-rule"
          style={{
            marginTop: 64,
            display: "flex",
            alignItems: "center",
            gap: 14,
            fontFamily: "var(--mono)",
            fontSize: 11,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "var(--ink-soft)",
          }}
        >
          Game Analysis Agent · Reports Index · {new Date(manifest.generated_at).toUTCString()}
        </div>
      </main>
    </div>
  );
}

function IssueCardView({ card, idx }: { card: IssueCard; idx: number }) {
  const topEnding = card.top_ending?.ending_id ?? "—";
  const topRate = card.top_ending ? card.top_ending.rate.toFixed(3) : "—";
  return (
    <Link to={`/issue/${card.kind}/${encodeURIComponent(card.id)}`} className="issue-card">
      <span className="issue-num">
        № {String(idx + 1).padStart(3, "0")} · {card.kind.toUpperCase()}
        {card.has_decision_graph ? " · ↗ GRAPH" : ""}
      </span>
      <h3>{card.title}</h3>
      <div className="deck">{card.subtitle || "(no subtitle)"}</div>
      <div className="stats">
        <span>
          runs
          <strong>{card.total_runs}</strong>
        </span>
        <span>
          top end.
          <br />
          <strong style={{ fontSize: 13 }}>{topEnding.slice(0, 18)}</strong>
        </span>
        <span>
          anom.
          <br />
          <strong>{card.anomaly_total}</strong>
        </span>
      </div>
      <div style={{ marginTop: 10 }}>
        <span className={`severity-badge ${card.severity}`}>
          {card.severity}
        </span>
        <span
          style={{
            fontFamily: "var(--mono)",
            fontSize: 11,
            color: "var(--muted)",
            letterSpacing: "0.1em",
          }}
        >
          ENDING DISTRIBUTION · {topRate}
        </span>
      </div>
    </Link>
  );
}