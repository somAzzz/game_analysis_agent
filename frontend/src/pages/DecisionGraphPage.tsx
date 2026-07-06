import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type EdgeMarker,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import dagre from "dagre";
import { fetchDecisionGraphManifest } from "@/lib/api";
import { computeGraph, type ComputedGraph } from "@/lib/layout";
import type {
  DecisionGraphManifest,
  TriggeredStep,
} from "@/types";

/* ------------------------------------------------------------------ */
/* Custom node types                                                  */
/* ------------------------------------------------------------------ */

interface EventNodeData extends Record<string, unknown> {
  event_id: string;
  week: number;
  title: string;
  event_type: string;
  choice_index: number;
  isCurrent: boolean;
  totalChoices?: number;
}

function EventNode({ data }: NodeProps<Node<EventNodeData>>) {
  const d = data as unknown as EventNodeData;
  const cls = [
    "event-node",
    d.event_type || "uncategorised",
    d.isCurrent ? "is-current" : "",
    "is-triggered",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} title={d.title || d.event_id || ""}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="node-id">W{d.week}</div>
      <div style={{ marginTop: 4, fontSize: 9 }}>{d.event_type}</div>
      {d.choice_index >= 0 ? (
        <div className="node-choice">choice #{d.choice_index + 1}</div>
      ) : (
        <div className="node-choice-none">no choice</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

interface BgEventNodeData extends Record<string, unknown> {
  id: string;
  title: string;
  eventType: string;
}

function BackgroundEventNode({ data }: NodeProps<Node<BgEventNodeData>>) {
  const d = data as unknown as BgEventNodeData;
  const cls = ["event-node", d.eventType || "uncategorised"].join(" ");
  return (
    <div className={cls} title={d.title || ""}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
    </div>
  );
}

const NODE_TYPES = {
  event: EventNode,
  backgroundEvent: BackgroundEventNode,
};

const DEFAULT_MARKER: EdgeMarker = { type: MarkerType.ArrowClosed, color: "var(--accent)" };

/* ------------------------------------------------------------------ */
/* Layout with dagre                                                  */
/* ------------------------------------------------------------------ */

function layoutWithDagre(
  triggered: TriggeredStep[],
  allEventIds: string[],
): { nodes: Node[]; edges: Edge[] } {
  // Background event nodes (faint dots) — placed on a separate dagre layer.
  const bgG = new dagre.graphlib.Graph();
  bgG.setDefaultEdgeLabel(() => ({}));
  bgG.setGraph({ rankdir: "LR", nodesep: 20, ranksep: 50 });

  const bgNodes: Node[] = [];
  const triggeredIds = new Set(triggered.map((t) => t.event_id));
  for (const evId of allEventIds) {
    if (triggeredIds.has(evId)) continue;
    bgG.setNode(evId, { width: 16, height: 16 });
    bgNodes.push({
      id: `bg-${evId}`,
      type: "backgroundEvent",
      position: { x: 0, y: 0 },
      data: { id: evId, title: evId, eventType: "uncategorised" },
      draggable: false,
      selectable: false,
    });
  }
  dagre.layout(bgG);
  for (const node of bgNodes) {
    const layoutNode = bgG.node((node.data as { id: string }).id);
    if (layoutNode) {
      node.position = { x: layoutNode.x, y: layoutNode.y };
    }
  }

  // Foreground (triggered) event nodes — laid out by week on the X axis.
  const fgG = new dagre.graphlib.Graph();
  fgG.setDefaultEdgeLabel(() => ({}));
  fgG.setGraph({ rankdir: "LR", nodesep: 40, ranksep: 80 });

  const fgNodes: Node[] = [];
  const fgEdges: Edge[] = [];
  triggered.forEach((step, idx) => {
    fgG.setNode(step.event_id, { width: 96, height: 96 });
    fgNodes.push({
      id: step.event_id,
      type: "event",
      position: { x: 0, y: 0 },
      data: {
        event_id: step.event_id,
        week: step.week,
        title: step.title,
        event_type: step.event_type,
        choice_index: step.choice_index,
        isCurrent: false,
        totalChoices: 4,
      },
      draggable: true,
    });
    if (idx > 0) {
      const prev = triggered[idx - 1];
      fgG.setEdge(prev.event_id, step.event_id);
      fgEdges.push({
        id: `e-${prev.event_id}->${step.event_id}`,
        source: prev.event_id,
        target: step.event_id,
        type: "default",
        animated: false,
        markerEnd: DEFAULT_MARKER,
        className: "",
      });
    }
  });
  dagre.layout(fgG);
  for (const node of fgNodes) {
    const layoutNode = fgG.node(node.id);
    if (layoutNode) {
      node.position = { x: layoutNode.x - 48, y: layoutNode.y - 48 };
    }
  }
  return { nodes: [...bgNodes, ...fgNodes], edges: fgEdges };
}

/* ------------------------------------------------------------------ */
/* Page component                                                     */
/* ------------------------------------------------------------------ */

export function DecisionGraphPage() {
  const { runId, runIndex } = useParams<{ runId: string; runIndex?: string }>();
  const decodedRunId = runId ? decodeURIComponent(runId) : "";
  const runIdxNum = runIndex ? parseInt(runIndex, 10) || 0 : 0;

  const [manifest, setManifest] = useState<DecisionGraphManifest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentWeek, setCurrentWeek] = useState<number>(0);
  const [autoPlay, setAutoPlay] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rfRef = useRef<unknown>(null);

  useEffect(() => {
    if (!decodedRunId) return;
    fetchDecisionGraphManifest(decodedRunId, runIdxNum)
      .then(setManifest)
      .catch((err) => setError(err.message ?? String(err)));
  }, [decodedRunId, runIdxNum]);

  const computed: ComputedGraph | null = useMemo(() => {
    if (!manifest) return null;
    return computeGraph(manifest);
  }, [manifest]);

  const layout = useMemo(() => {
    if (!computed) return null;
    const allEventIds = (manifest?.event_graph?.events ?? [])
      .filter((e) => typeof e.id === "string")
      .map((e) => e.id as string);
    return layoutWithDagre(computed.events, allEventIds);
  }, [computed, manifest]);

  // Highlight: nodes whose week <= currentWeek get is-current=true.
  // Edges get is-path=true when their source week's step is <= current.
  const styled = useMemo(() => {
    if (!layout || !computed) return { nodes: [], edges: [] };
    const triggeredById = new Map(computed.events.map((e) => [e.event_id, e]));
    const nodes = layout.nodes.map((n) => {
      if (n.type !== "event") return n;
      const ev = triggeredById.get(n.id);
      if (!ev) return n;
      return {
        ...n,
        data: { ...n.data, isCurrent: ev.week <= currentWeek },
      };
    });
    const edges = layout.edges.map((e) => {
      const sourceWeek = triggeredById.get(e.source)?.week ?? 0;
      return {
        ...e,
        className:
          sourceWeek < currentWeek
            ? "is-path"
            : sourceWeek > currentWeek
              ? "is-faded"
              : "",
      };
    });
    return { nodes, edges };
  }, [layout, computed, currentWeek]);

  // Auto-play: tick the slider every 700ms.
  useEffect(() => {
    if (!autoPlay || !computed) return;
    const id = setInterval(() => {
      setCurrentWeek((w) => {
        if (w >= computed.maxWeek) {
          setAutoPlay(false);
          return w;
        }
        return w + 1;
      });
    }, 700);
    return () => clearInterval(id);
  }, [autoPlay, computed]);

  if (error) {
    return (
      <div style={{ padding: 60 }}>
        <h1>Decision graph not found</h1>
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

  if (!computed || !layout || !manifest) {
    return <div style={{ padding: 60 }}>Loading decision graph…</div>;
  }

  const currentStep =
    computed.events.find((e) => e.week === currentWeek) ?? computed.events[0];

  return (
    <ReactFlowProvider>
      <div>
        <header className="masthead">
          <span className="kicker">
            <Link to={`/issue/balance/${encodeURIComponent(decodedRunId)}`}>
              ← Back to issue
            </Link>
          </span>
          <span className="issue-line">
            Decision graph · run seed {String(manifest.seed ?? "—")} · policy{" "}
            <em>{manifest.policy}</em>
          </span>
          <span className="date">{new Date().toUTCString()}</span>
        </header>

        <section className="cover">
          <div className="issue-meta">
            <span>
              <strong>{manifest.policy}</strong>
              policy played
            </span>
            <span>
              <strong>{computed.events.length}</strong>
              events triggered
            </span>
            <span>
              <strong>{computed.maxWeek}</strong>
              weeks simulated
            </span>
            <span>
              <strong>{manifest.final_ending_id || "unknown"}</strong>
              final ending
            </span>
          </div>
          <h1>
            The decision <em>graph</em>
          </h1>
          <p className="deck">
            {manifest.public_notice ??
              `Every event the engine could trigger is drawn on a single canvas,
              one lane per event_type seen in the data, ${computed.maxWeek} weeks
              across. The terracotta line is the path this run actually took.`}
          </p>
        </section>

        {manifest.public_demo && (
          <div className="notice-strip">
            <strong>Illustrative graph</strong>
            <span>
              This public graph is intentionally small. It demonstrates the
              interaction model without publishing the private full event graph.
            </span>
          </div>
        )}

        <div className="dg-shell">
          {/* Legend */}
          <div
            style={{
              display: "flex",
              gap: 18,
              flexWrap: "wrap",
              alignItems: "center",
              fontFamily: "var(--mono)",
              fontSize: 11,
              letterSpacing: "0.08em",
              color: "var(--ink-soft)",
              margin: "18px 0",
            }}
          >
            {computed.laneOrder.map((lane) => (
              <span key={lane}>
                <span
                  className={`swatch ${lane}`}
                  style={{
                    display: "inline-block",
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    verticalAlign: "middle",
                    marginRight: 6,
                    border: "1px solid var(--ink)",
                    background: "var(--paper)",
                  }}
                />
                {lane} event (
                {computed.layout.events.filter((e) => {
                  const t = e.event_type ?? e.type ?? e.kind;
                  return (typeof t === "string" ? t.toLowerCase() : "uncategorised") === lane;
                }).length}
                )
              </span>
            ))}
            <span>
              <span
                style={{
                  display: "inline-block",
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  verticalAlign: "middle",
                  marginRight: 6,
                  background: "var(--accent)",
                  border: "1px solid var(--accent)",
                }}
              />
              agent path
            </span>
          </div>

          {/* React Flow canvas */}
          <div
            ref={containerRef}
            style={{
              width: "100%",
              height: 640,
              border: "1px solid var(--ink)",
              borderTop: "4px double var(--ink)",
              borderBottom: "4px double var(--ink)",
              background: "var(--paper-deep)",
            }}
          >
            <ReactFlow
              nodes={styled.nodes}
              edges={styled.edges}
              nodeTypes={NODE_TYPES}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              proOptions={{ hideAttribution: true }}
              nodesDraggable
              elementsSelectable
              onInit={(instance) => {
                rfRef.current = instance;
              }}
              onNodeClick={(_, node) => {
                if (node.type !== "event") return;
                const ev = computed.events.find((e) => e.event_id === node.id);
                if (ev) setCurrentWeek(ev.week);
              }}
            >
              <Background gap={20} size={1} />
              <Controls />
              <MiniMap
                nodeColor={(n) =>
                  n.type === "event" ? "var(--ink)" : "var(--muted)"
                }
                style={{
                  background: "var(--paper)",
                  border: "1px solid var(--ink)",
                }}
              />
            </ReactFlow>
          </div>

          {/* Toolbar */}
          <div className="dg-toolbar">
            <div className="timeline-strip">
              {Array.from({ length: computed.maxWeek + 1 }, (_, w) => {
                const triggeredHere = computed.events.find((e) => e.week === w);
                return (
                  <div
                    key={w}
                    className={`timeline-cell ${
                      triggeredHere ? "is-triggered" : ""
                    } ${w === currentWeek ? "is-current" : ""}`}
                    onClick={() => setCurrentWeek(w)}
                  >
                    <span className="w">{w}</span>
                    <span className="dot" />
                  </div>
                );
              })}
            </div>
            <div className="dg-controls">
              <div className="row">
                <button
                  onClick={() => {
                    setCurrentWeek(0);
                    setAutoPlay(false);
                  }}
                >
                  ⟲ Reset
                </button>
                <button onClick={() => setAutoPlay((p) => !p)}>
                  {autoPlay ? "⏸ Pause" : "▶ Play"}
                </button>
                <span style={{ color: "var(--muted)" }}>W</span>
                <input
                  type="range"
                  min={0}
                  max={computed.maxWeek}
                  value={currentWeek}
                  onChange={(e) => setCurrentWeek(Number(e.target.value))}
                />
                <span
                  style={{
                    color: "var(--accent)",
                    fontWeight: 600,
                    minWidth: 28,
                  }}
                >
                  {currentWeek}
                </span>
              </div>
              <div className="row" style={{ color: "var(--muted)" }}>
                click any week · drag slider
              </div>
            </div>
          </div>

          {/* Side panels */}
          <div className="dg-side-panel">
            <div>
              <h2
                style={{
                  fontFamily: "var(--serif)",
                  fontStyle: "italic",
                  fontSize: 32,
                  fontVariationSettings:
                    '"opsz" 96, "wght" 360, "SOFT" 100',
                  margin: "0 0 12px",
                }}
              >
                What the agent did this week
              </h2>
              {currentStep ? (
                <WeekDetail step={currentStep} />
              ) : (
                <p
                  style={{
                    fontStyle: "italic",
                    color: "var(--muted)",
                  }}
                >
                  No event triggered in week {currentWeek}.
                </p>
              )}
            </div>
            <aside>
              {currentStep ? <ChoicePanel step={currentStep} /> : null}
            </aside>
          </div>

          {/* Diagnostics */}
          {computed.diagnostics.length > 0 && (
            <details
              style={{
                margin: "18px 0 0",
                fontFamily: "var(--mono)",
                fontSize: 11,
                lineHeight: 1.55,
                color: "var(--ink-soft)",
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  letterSpacing: "0.16em",
                  textTransform: "uppercase",
                  color: "var(--ink-soft)",
                  padding: "6px 0",
                  borderTop: "1px dotted var(--rule)",
                  borderBottom: "1px dotted var(--rule)",
                }}
              >
                Adaptive diagnostics · {computed.diagnostics.length} note(s)
              </summary>
              <div
                style={{
                  padding: "10px 14px",
                  background: "var(--paper-deep)",
                  borderLeft: "2px solid var(--accent)",
                  marginTop: 6,
                }}
              >
                {computed.diagnostics.map((d, i) => (
                  <div key={i}>· {d}</div>
                ))}
              </div>
            </details>
          )}
        </div>
      </div>
    </ReactFlowProvider>
  );
}

function WeekDetail({ step }: { step: TriggeredStep }) {
  const actions =
    step.selected_actions.length > 0 ? (
      step.selected_actions.map((a, i) => (
        <code
          key={i}
          style={{
            marginRight: 6,
            background: "var(--paper-deep)",
            padding: "1px 6px",
          }}
        >
          {a}
        </code>
      ))
    ) : (
      <em style={{ color: "var(--muted)" }}>no actions recorded</em>
    );
  return (
    <div
      style={{
        fontFamily: "var(--body)",
        fontSize: 17,
        lineHeight: 1.6,
        color: "var(--ink-soft)",
      }}
    >
      <p style={{ margin: 0 }}>
        <strong
          style={{
            fontFamily: "var(--mono)",
            fontSize: 12,
            color: "var(--accent)",
            letterSpacing: "0.12em",
          }}
        >
          W{step.week} · {step.event_id}
        </strong>
      </p>
      <p
        style={{
          fontFamily: "var(--serif)",
          fontStyle: "italic",
          fontSize: 22,
          lineHeight: 1.3,
          color: "var(--ink)",
          margin: "6px 0",
        }}
      >
        {step.title || step.event_id}
      </p>
      <p style={{ fontSize: 14 }}>
        The agent picked choice{" "}
        <strong style={{ color: "var(--accent)" }}>
          #{step.choice_index + 1}
        </strong>
        : <span style={{ fontStyle: "italic" }}>&quot;{step.choice_text || "(none)"}&quot;</span>
      </p>
      <p style={{ fontSize: 13, color: "var(--ink-soft)", marginTop: 14 }}>
        <strong>Actions this week:</strong> {actions}
      </p>
      <p
        style={{
          fontSize: 11,
          color: "var(--muted)",
          fontFamily: "var(--mono)",
        }}
      >
        {Object.entries(step.after_state)
          .slice(0, 6)
          .map(([k, v]) => `${k}: ${String(v)}`)
          .join(" · ")}
      </p>
    </div>
  );
}

function ChoicePanel({ step }: { step: TriggeredStep }) {
  const effects = step.choice_effects;
  const effectRows = Object.entries(effects).map(([k, v]) => {
    const cls = v >= 0 ? "pos" : "neg";
    const sign = v >= 0 ? "+" : "";
    return (
      <span key={k} className={cls}>
        {k} {sign}
        {v}
      </span>
    );
  });
  return (
    <div className="panel-card">
      <h4>
        W{step.week} · choice #{step.choice_index + 1}
      </h4>
      <span className="pick-text">&quot;{step.choice_text || "(no text)"}&quot;</span>
      <p style={{ fontSize: 11, color: "var(--muted)" }}>{step.event_id}</p>
      <h4 style={{ marginTop: 14 }}>Effects</h4>
      <div className="effects">
        {effectRows.length > 0 ? effectRows : <span style={{ color: "var(--muted)" }}>no effects recorded</span>}
      </div>
    </div>
  );
}
