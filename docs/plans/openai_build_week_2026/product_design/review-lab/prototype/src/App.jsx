import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CaretLeft,
  CaretRight,
  Check,
  Fingerprint,
  Info,
  Pause,
  Play,
  ShieldCheck,
  X,
} from "@phosphor-icons/react";

const PERSONA_ORDER = ["newbie", "study", "money", "social", "visa", "slacker"];
const PERSONA_LABELS = {
  newbie: "Newbie",
  study: "Study",
  money: "Money",
  social: "Social",
  visa: "Visa",
  slacker: "Slacker",
};

const REVIEW_STATES = [
  { id: "S1", label: "Judge default", view: "mission" },
  { id: "S2", label: "Money hover", view: "mission" },
  { id: "S3", label: "Persona detail", view: "mission" },
  { id: "S4", label: "Inspector W1", view: "inspector", week: 1 },
  { id: "S5", label: "Inspector W3", view: "inspector", week: 3 },
  { id: "S6", label: "Inspector W19", view: "inspector", week: 19 },
];

const STATE_METRICS = [
  ["money", "Money", "€"],
  ["energy", "Energy", ""],
  ["stress", "Stress", ""],
  ["hunger", "Hunger", ""],
  ["arrears_amount", "Arrears", "€"],
  ["cash_shortfall_count", "Shortfall", "×"],
];

async function loadJson(path) {
  const response = await fetch(`${import.meta.env.BASE_URL}${path}`);
  if (!response.ok) throw new Error(`${path} → HTTP ${response.status}`);
  return response.json();
}

function percent(value, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

function selectedChoice(node) {
  return node.event.legal_choices.find(
    (choice) => choice.choice_id === node.event.selected_choice_id,
  );
}

function firstEnding(persona) {
  return Object.entries(persona.observed.final_endings)[0] ?? ["unknown", 0];
}

function metricValue(value, prefix) {
  if (value === undefined || value === null) return "—";
  if (prefix === "€") return `€${Number(value).toLocaleString("en-US")}`;
  if (prefix === "×") return `${value}×`;
  return String(value);
}

export function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [view, setView] = useState("mission");
  const [reviewState, setReviewState] = useState("S1");
  const [selectedPersona, setSelectedPersona] = useState("money");
  const [hoveredPersona, setHoveredPersona] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const returnFocusRef = useRef(null);

  useEffect(() => {
    Promise.all([
      loadJson("evidence/manifest.json"),
      loadJson("evidence/personas.json"),
      loadJson("evidence/cells/money-seed-42.json"),
      loadJson("evidence/provenance.json"),
    ])
      .then(([manifest, personas, cell, provenance]) => {
        setData({ manifest, personas: personas.personas, cell, provenance });
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, []);

  const currentNode = data?.cell.nodes[currentIndex] ?? null;

  useEffect(() => {
    if (!playing || !data) return undefined;
    const timer = window.setInterval(() => {
      setCurrentIndex((index) => {
        if (index >= data.cell.nodes.length - 1) {
          setPlaying(false);
          return index;
        }
        return index + 1;
      });
    }, 900);
    return () => window.clearInterval(timer);
  }, [playing, data]);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape" && drawerOpen) {
        setDrawerOpen(false);
        window.setTimeout(() => returnFocusRef.current?.focus(), 0);
        return;
      }
      if (view !== "inspector" || !data) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setPlaying(false);
        setCurrentIndex((index) => Math.max(0, index - 1));
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        setPlaying(false);
        setCurrentIndex((index) => Math.min(data.cell.nodes.length - 1, index + 1));
      }
      if (event.code === "Space" && event.target === document.body) {
        event.preventDefault();
        setPlaying((value) => !value);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [data, drawerOpen, view]);

  function goToWeek(week) {
    if (!data) return;
    const index = data.cell.nodes.findIndex((node) => node.week === week);
    if (index >= 0) setCurrentIndex(index);
    setPlaying(false);
  }

  function applyReviewState(state) {
    setReviewState(state.id);
    setView(state.view);
    setPlaying(false);
    if (state.id === "S1") {
      setHoveredPersona(null);
      setDrawerOpen(false);
    }
    if (state.id === "S2") {
      setSelectedPersona("money");
      setHoveredPersona("money");
      setDrawerOpen(false);
    }
    if (state.id === "S3") {
      setSelectedPersona("money");
      setHoveredPersona(null);
      setDrawerOpen(true);
    }
    if (state.week) goToWeek(state.week);
  }

  function openDrawer(slug, element) {
    returnFocusRef.current = element;
    setSelectedPersona(slug);
    setDrawerOpen(true);
    setReviewState(slug === "money" ? "S3" : "custom");
  }

  function closeDrawer() {
    setDrawerOpen(false);
    window.setTimeout(() => returnFocusRef.current?.focus(), 0);
  }

  if (error) {
    return (
      <main className="loading-screen is-error">
        <span>EVIDENCE LOAD FAILED</span>
        <h1>The review cannot render without verified data.</h1>
        <p>{error}</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="loading-screen">
        <span>PLAYTEST FORGE / REVIEW LAB</span>
        <h1>Verifying the signed route…</h1>
      </main>
    );
  }

  const selected = data.personas.find((persona) => persona.slug === selectedPersona);
  const preview = data.personas.find(
    (persona) => persona.slug === (hoveredPersona ?? selectedPersona),
  );

  return (
    <div className="review-lab">
      <ReviewHeader
        view={view}
        truthLabel={data.provenance.truth_label}
        onView={(next) => {
          setView(next);
          setReviewState(next === "mission" ? "S1" : "S4");
          if (next === "inspector") goToWeek(1);
        }}
      />
      <ReviewStateBar current={reviewState} onSelect={applyReviewState} />

      {view === "mission" ? (
        <MissionView
          manifest={data.manifest}
          personas={data.personas}
          preview={preview}
          selectedPersona={selectedPersona}
          hoveredPersona={hoveredPersona}
          onHover={setHoveredPersona}
          onOpen={openDrawer}
          onPlay={() => {
            setView("inspector");
            setReviewState("S4");
            goToWeek(1);
          }}
        />
      ) : (
        <InspectorView
          cell={data.cell}
          manifest={data.manifest}
          currentIndex={currentIndex}
          currentNode={currentNode}
          playing={playing}
          onPlaying={setPlaying}
          onIndex={(index) => {
            setPlaying(false);
            setCurrentIndex(index);
            const week = data.cell.nodes[index].week;
            setReviewState(week === 1 ? "S4" : week === 3 ? "S5" : week === 19 ? "S6" : "custom");
          }}
          onWeek={(week) => {
            goToWeek(week);
            setReviewState(week === 1 ? "S4" : week === 3 ? "S5" : "S6");
          }}
          onBack={() => {
            setView("mission");
            setReviewState("S1");
            setPlaying(false);
          }}
        />
      )}

      <ApprovalGate />
      {drawerOpen && selected && (
        <PersonaDrawer persona={selected} cell={data.cell} onClose={closeDrawer} />
      )}
    </div>
  );
}

function ReviewHeader({ view, truthLabel, onView }) {
  return (
    <header className="review-header">
      <div className="wordmark">
        <span>PLAYTEST</span>
        <b>FORGE</b>
      </div>
      <nav aria-label="Review pages">
        <button className={view === "mission" ? "is-active" : ""} onClick={() => onView("mission")}>
          Judge Mission
        </button>
        <button className={view === "inspector" ? "is-active" : ""} onClick={() => onView("inspector")}>
          Playthrough Inspector
        </button>
      </nav>
      <div className="truth-chip"><ShieldCheck weight="fill" /> {truthLabel}</div>
    </header>
  );
}

function ReviewStateBar({ current, onSelect }) {
  return (
    <div className="review-state-bar" aria-label="Review state selector">
      <span>REVIEW STATES</span>
      <div>
        {REVIEW_STATES.map((state) => (
          <button
            key={state.id}
            className={current === state.id ? "is-active" : ""}
            onClick={() => onSelect(state)}
            aria-pressed={current === state.id}
          >
            <b>{state.id}</b> {state.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function MissionView({
  manifest,
  personas,
  preview,
  selectedPersona,
  hoveredPersona,
  onHover,
  onOpen,
  onPlay,
}) {
  return (
    <main className="mission-page">
      <section className="mission-hero" aria-labelledby="mission-title">
        <div className="mission-number"><strong>01</strong><span>CAMPAIGN</span></div>
        <div className="mission-copy">
          <p className="eyebrow">Mission brief · campaign → repair → proof</p>
          <h1 id="mission-title">A patch passed its unit test. <em>We still rejected it.</em></h1>
          <p>Six strategy Personas played the same real Godot demo. The campaign is reproducible; the candidate repair still failed its player-level goal.</p>
        </div>
        <aside className="verdict-box">
          <span>FINAL DECISION</span>
          <strong>REJECTED</strong>
          <small>candidate_not_merged</small>
        </aside>
      </section>

      <section className="mission-facts" aria-label="Verified campaign facts">
        <Fact value={`${manifest.cell_count}/${manifest.cell_count}`} label="cells complete" />
        <Fact value={manifest.node_count} label="observed weeks" />
        <Fact value={manifest.actual_edge_count} label="actual edges" />
        <Fact value={manifest.legal_event_choice_count.toLocaleString("en-US")} label="legal choices" />
      </section>

      <section className="squad-layout" aria-labelledby="squad-title">
        <div className="squad-main">
          <div className="section-label"><span>STRATEGY SQUAD</span><b>6 / 6</b></div>
          <div className="persona-roster">
            <img src={`${import.meta.env.BASE_URL}assets/persona-roster-v2.webp`} alt="Six human strategy Personas: Newbie, Study, Money, Social, Visa, and Slacker" />
            <div className="persona-hotspots">
              {PERSONA_ORDER.map((slug) => (
                <button
                  key={slug}
                  className={`${selectedPersona === slug ? "is-selected" : ""} ${hoveredPersona === slug ? "is-hovered" : ""}`}
                  onMouseEnter={() => onHover(slug)}
                  onMouseLeave={() => onHover(null)}
                  onFocus={() => onHover(slug)}
                  onBlur={() => onHover(null)}
                  onClick={(event) => onOpen(slug, event.currentTarget)}
                  aria-label={`Inspect ${PERSONA_LABELS[slug]} strategy`}
                >
                  <span>{PERSONA_LABELS[slug]}</span>
                </button>
              ))}
            </div>
          </div>
          <p className="roster-hint">Hover for observed strategy evidence · click for the full contract</p>
        </div>
        <PersonaSummary persona={preview} />
      </section>

      <section className="mission-action">
        <div>
          <span>DEMO ROUTE</span>
          <strong>Money · seed 42 · W1 → W3 attractor → W19 ending</strong>
          <small>Solid path only. Legal alternatives stop as dotted affordances.</small>
        </div>
        <button onClick={onPlay}><Play weight="fill" /> Play signed replay <ArrowRight /></button>
      </section>
    </main>
  );
}

function Fact({ value, label }) {
  return <div><strong>{value}</strong><span>{label}</span></div>;
}

function PersonaSummary({ persona }) {
  const rates = Object.entries(persona.observed.action_tag_rates)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  const [ending, endingCount] = firstEnding(persona);
  return (
    <aside className="persona-summary" aria-live="polite">
      <div className="summary-heading">
        <div><span>HOVER SUMMARY</span><h2>{PERSONA_LABELS[persona.slug]}</h2></div>
        <Info weight="fill" />
      </div>
      <p>{persona.contract.description}</p>
      <dl className="contract-strip">
        <div><dt>Risk</dt><dd>{persona.contract.risk_tolerance.toFixed(2)}</dd></div>
        <div><dt>Explore</dt><dd>{persona.contract.exploration.toFixed(2)}</dd></div>
        <div><dt>Seeds</dt><dd>{persona.observed.seeds.join(" · ")}</dd></div>
      </dl>
      <h3>Observed action mix</h3>
      <div className="rate-list">
        {rates.map(([label, value]) => (
          <div key={label}><span>{label}</span><b>{percent(value)}</b><progress max="1" value={value} /></div>
        ))}
      </div>
      {persona.slug === "money" && (
        <p className="mismatch"><span>Mismatch</span> career actions were only {percent(persona.observed.action_tag_rates.career, 2)}</p>
      )}
      <div className="summary-outcome">
        <span>First attractor</span><b>W{persona.observed.first_cashflow_stress_attractor_weeks.join(" / W")}</b>
        <span>Ending</span><b className="is-danger">{ending} · {endingCount}/3</b>
      </div>
    </aside>
  );
}

function PersonaDrawer({ persona, cell, onClose }) {
  const [ending, endingCount] = firstEnding(persona);
  return (
    <div className="drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside className="persona-drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <header>
          <div><span>STRATEGY RECORD</span><h2 id="drawer-title">{PERSONA_LABELS[persona.slug]}</h2></div>
          <button onClick={onClose} aria-label="Close Persona details"><X /></button>
        </header>
        <section>
          <h3>Strategy contract</h3>
          <p>{persona.contract.description}</p>
          <Record label="Priorities" value={persona.contract.priorities.join(" · ")} />
          <Record label="Hard avoids" value={persona.contract.hard_avoid.join(" · ")} />
          <Record label="Risk / explore" value={`${persona.contract.risk_tolerance.toFixed(2)} / ${persona.contract.exploration.toFixed(2)}`} />
        </section>
        <section>
          <h3>Observed behavior</h3>
          <div className="drawer-rates">
            {Object.entries(persona.observed.action_tag_rates).map(([label, value]) => (
              <Record key={label} label={`${label} tag`} value={percent(value)} />
            ))}
          </div>
        </section>
        <section>
          <h3>Outcome</h3>
          <Record label="First attractor" value={`W${persona.observed.first_cashflow_stress_attractor_weeks.join(" / W")}`} />
          <Record label="Ending distribution" value={`${ending} · ${endingCount}/3`} danger />
        </section>
        <section>
          <h3>Evidence</h3>
          <Record label="Seeds" value={persona.observed.seeds.join(" · ")} />
          <Record label="Completed cells" value={`${persona.observed.completed_cells}/${persona.observed.cell_count}`} />
          {persona.slug === "money" && <Record label="Selected trace" value={`${cell.cell_id} · 19 cited rows`} mono />}
        </section>
        <p className="drawer-limit"><Info weight="fill" /> Replay proves reproducibility, not a fresh OpenAI call.</p>
      </aside>
    </div>
  );
}

function Record({ label, value, danger = false, mono = false }) {
  return <div className={`record ${danger ? "is-danger" : ""} ${mono ? "is-mono" : ""}`}><span>{label}</span><b>{value}</b></div>;
}

function InspectorView({
  cell,
  manifest,
  currentIndex,
  currentNode,
  playing,
  onPlaying,
  onIndex,
  onWeek,
  onBack,
}) {
  const choice = selectedChoice(currentNode);
  const progress = (currentIndex / (cell.nodes.length - 1)) * 100;
  const metrics = STATE_METRICS.map(([key, label, prefix]) => ({
    key,
    label,
    prefix,
    before: currentNode.state_before[key],
    after: currentNode.state_after[key],
  })).filter((metric) => metric.before !== undefined || metric.after !== undefined);

  return (
    <main className="inspector-page">
      <section className="inspector-heading">
        <button onClick={onBack}><ArrowLeft /> Judge Mission</button>
        <div>
          <p className="eyebrow">PLAYTHROUGH INSPECTOR · SIGNED ACTUAL PATH</p>
          <h1>Money runs the evidence, one week at a time.</h1>
        </div>
        <dl>
          <div><dt>Persona</dt><dd>Money</dd></div>
          <div><dt>Seed</dt><dd>42</dd></div>
          <div><dt>Nodes</dt><dd>{cell.nodes.length}</dd></div>
          <div><dt>Edges</dt><dd>{cell.actual_edges.length}</dd></div>
        </dl>
      </section>

      <section className="route-section" aria-labelledby="route-title">
        <div className="section-label"><span id="route-title">ACTUAL REPLAY PATH</span><b>W{currentNode.week} / W{cell.completed_weeks}</b></div>
        <div className="route-scroll">
          <div className="route-stage">
            <img
              className={`route-runner ${playing ? "is-moving" : ""}`}
              style={{ left: `${progress}%` }}
              src={`${import.meta.env.BASE_URL}assets/money-runner-v1.png`}
              alt="Money strategy Persona on the current recorded week"
            />
            <ol className="route-list">
              {cell.nodes.map((node, index) => {
                const classes = [
                  index < currentIndex ? "is-past" : "",
                  index === currentIndex ? "is-active" : "",
                  node.attractors.length ? "is-attractor" : "",
                  node.finished ? "is-terminal" : "",
                ].filter(Boolean).join(" ");
                return (
                  <li key={node.id} className={classes}>
                    <button onClick={() => onIndex(index)} aria-label={`Go to recorded week ${node.week}`} aria-current={index === currentIndex ? "step" : undefined}>
                      {node.week}
                    </button>
                    {(node.week === 1 || node.week === 3 || node.week === 19) && (
                      <span>{node.week === 1 ? "START" : node.week === 3 ? "FIRST ATTRACTOR" : "ENDING"}</span>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
        <div className="path-legend">
          <span><i className="legend-line" /> recorded transition</span>
          <span><i className="legend-stub" /> legal option · future not executed</span>
          <span><i className="legend-risk" /> attractor / terminal risk</span>
        </div>
      </section>

      <PlaybackControls
        currentIndex={currentIndex}
        length={cell.nodes.length}
        playing={playing}
        onPlaying={onPlaying}
        onIndex={onIndex}
        onWeek={onWeek}
      />

      <section className="inspector-grid">
        <div className="week-record">
          <header>
            <span>W{currentNode.week.toString().padStart(2, "0")}</span>
            <div><small>EVENT</small><h2>{currentNode.event.id}</h2></div>
            {currentNode.attractors.length > 0 && <b>FIRST ATTRACTOR</b>}
            {currentNode.finished && <b className="is-terminal">{cell.final_ending}</b>}
          </header>

          <div className="week-columns">
            <section>
              <h3>Selected actions</h3>
              <ul className="action-list">{currentNode.selected_action_ids.map((action) => <li key={action}>{action}</li>)}</ul>
              <h3>Event choices</h3>
              <ul className="choice-list">
                {currentNode.event.legal_choices.map((item) => (
                  <li key={item.choice_id} className={item.choice_id === currentNode.event.selected_choice_id ? "is-selected" : ""}>
                    <span>{item.choice_id === currentNode.event.selected_choice_id ? <Check weight="bold" /> : null}</span>
                    <div><b>{item.text}</b><small>{item.choice_id === currentNode.event.selected_choice_id ? "observed result" : "legal here · future not executed"}</small></div>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h3>State delta</h3>
              <dl className="state-delta">
                {metrics.map((metric) => (
                  <div key={metric.key} className={metric.key === "stress" || metric.key === "hunger" || metric.key === "arrears_amount" ? "is-risk" : ""}>
                    <dt>{metric.label}</dt>
                    <dd><span>{metricValue(metric.before, metric.prefix)}</span><ArrowRight /><b>{metricValue(metric.after, metric.prefix)}</b></dd>
                  </div>
                ))}
              </dl>
              <div className="selected-choice">
                <small>SELECTED CHOICE</small>
                <strong>{choice?.text ?? "No event choice"}</strong>
              </div>
            </section>
          </div>
        </div>

        <EvidenceConsole nodes={cell.nodes} currentIndex={currentIndex} onIndex={onIndex} />
      </section>

      <section className="evidence-footer">
        <Fingerprint weight="fill" />
        <div><span>SOURCE LINE</span><b>{currentNode.evidence.source_line}</b></div>
        <div><span>ROW SHA-256</span><code>{currentNode.evidence.source_record_sha256}</code></div>
        <div><span>PROVENANCE</span><b>{cell.provider_mode} · real Godot · {manifest.source.game_commit.slice(0, 12)}</b></div>
      </section>
    </main>
  );
}

function PlaybackControls({ currentIndex, length, playing, onPlaying, onIndex, onWeek }) {
  return (
    <div className="playback-controls">
      <div className="control-cluster">
        <button disabled={currentIndex === 0} onClick={() => onIndex(Math.max(0, currentIndex - 1))}><CaretLeft /> Previous</button>
        <button className="play-button" onClick={() => onPlaying(!playing)}>
          {playing ? <Pause weight="fill" /> : <Play weight="fill" />} {playing ? "Pause" : "Play"}
        </button>
        <button disabled={currentIndex === length - 1} onClick={() => onIndex(Math.min(length - 1, currentIndex + 1))}>Next <CaretRight /></button>
      </div>
      <div className="jump-cluster" aria-label="Key review weeks">
        <span>JUMP TO</span>
        <button onClick={() => onWeek(1)}>W1 Start</button>
        <button onClick={() => onWeek(3)}>W3 Attractor</button>
        <button onClick={() => onWeek(19)}>W19 Ending</button>
      </div>
      <small>Keyboard: ← → · Space</small>
    </div>
  );
}

function EvidenceConsole({ nodes, currentIndex, onIndex }) {
  return (
    <aside className="evidence-console">
      <header><span>EVIDENCE CONSOLE</span><b>{nodes.length} cited rows</b></header>
      <div className="console-head"><span>WEEK</span><span>EVENT / CHOICE</span><span>HASH</span></div>
      <div className="console-rows">
        {nodes.map((node, index) => (
          <button key={node.id} className={index === currentIndex ? "is-active" : ""} onClick={() => onIndex(index)}>
            <span>W{node.week}</span>
            <span><b>{node.event.id}</b><small>{selectedChoice(node)?.text ?? "—"}</small></span>
            <code>{node.evidence.source_record_sha256.slice(0, 8)}</code>
          </button>
        ))}
      </div>
    </aside>
  );
}

function ApprovalGate() {
  return (
    <footer className="approval-gate">
      <span>REVIEW LAB · NOT PRODUCTION</span>
      <p>Approve story, Persona semantics, path grammar, synchronized logs, motion, and accessibility before migration.</p>
      <b>FRONTEND GATE — WAITING FOR REVIEW</b>
    </footer>
  );
}
