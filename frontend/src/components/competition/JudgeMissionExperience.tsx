import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Info,
  Play,
  ShieldCheck,
  X,
} from "@phosphor-icons/react";
import personaRoster from "@/assets/competition/persona-roster-v2.webp";
import moneyRunner from "@/assets/competition/money-runner-v1.png";
import missionMap from "@/assets/competition/judge-mission-map-v1.png";
import { competitionPlaythrough } from "@/lib/playthrough";
import type { PlaythroughBundle, PlaythroughPersona, PlaythroughPersonaSlug } from "@/types";
import { loadLivePlaythrough } from "@/lib/livePlaythrough";

const PERSONA_ORDER: PlaythroughPersonaSlug[] = [
  "newbie",
  "study",
  "money",
  "social",
  "visa",
  "slacker",
];

const PERSONA_LABELS: Record<PlaythroughPersonaSlug, string> = {
  newbie: "Newbie",
  study: "Study",
  money: "Money",
  social: "Social",
  visa: "Visa",
  slacker: "Slacker",
};

const PERSONA_DESCRIPTIONS: Record<PlaythroughPersonaSlug, string> = {
  newbie: "A first-time player who follows visible risk guidance and tries understandable options.",
  study: "An academic-first player focused on APS, TestDaF, coursework, and exam readiness.",
  money: "A cashflow-first player who prioritizes paid work and career progress.",
  social: "A relationship-first player who builds language confidence, contacts, and social support.",
  visa: "A compliance-first player who protects registration, insurance, banking, and residence deadlines.",
  slacker: "A comfort-first, failure-seeking player who lowers short-term stress and ignores some long-term risks.",
};

function percent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function humanizeToken(value: string): string {
  return value.replaceAll("_", " ");
}

function firstEnding(persona: PlaythroughPersona): [string, number] {
  return Object.entries(persona.observed.final_endings)[0] ?? ["unknown", 0];
}

export function JudgeMissionExperience() {
  const [latestPlaythrough, setLatestPlaythrough] = useState<PlaythroughBundle | null>(null);
  const [evidenceSource, setEvidenceSource] = useState<"latest" | "replay">("latest");
  const bundle = evidenceSource === "latest" && latestPlaythrough
    ? latestPlaythrough
    : competitionPlaythrough;
  const { manifest, personas, cell } = bundle;
  const isLatest = bundle === latestPlaythrough;
  const [selectedSlug, setSelectedSlug] = useState<PlaythroughPersonaSlug>("money");
  const [hoveredSlug, setHoveredSlug] = useState<PlaythroughPersonaSlug | null>(null);
  const [drawerSlug, setDrawerSlug] = useState<PlaythroughPersonaSlug | null>(null);
  const returnFocusRef = useRef<HTMLButtonElement | null>(null);
  const drawerRef = useRef<HTMLElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const selectedPersona = personas.find((persona) => persona.slug === selectedSlug) ?? personas[0];
  const previewPersona = personas.find(
    (persona) => persona.slug === (hoveredSlug ?? selectedSlug),
  ) ?? selectedPersona;
  const drawerPersona = personas.find((persona) => persona.slug === drawerSlug) ?? null;
  const drawerCell = bundle.cellReferences.find((item) => item.persona === drawerSlug);
  useEffect(() => {
    const controller = new AbortController();
    loadLivePlaythrough(controller.signal, { persona: "money" })
      .then((value) => setLatestPlaythrough(value))
      .catch(() => setLatestPlaythrough(null));
    return () => controller.abort();
  }, []);


  useEffect(() => {
    if (!drawerSlug) return undefined;
    window.requestAnimationFrame(() => closeButtonRef.current?.focus());
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setDrawerSlug(null);
        window.setTimeout(() => returnFocusRef.current?.focus(), 0);
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = drawerRef.current?.querySelectorAll<HTMLElement>(
        "a[href], button:not([disabled]), [tabindex]:not([tabindex='-1'])",
      );
      if (!focusable?.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [drawerSlug]);

  function openDrawer(slug: PlaythroughPersonaSlug, trigger: HTMLButtonElement): void {
    returnFocusRef.current = trigger;
    setSelectedSlug(slug);
    setDrawerSlug(slug);
  }

  function closeDrawer(): void {
    setDrawerSlug(null);
    window.setTimeout(() => returnFocusRef.current?.focus(), 0);
  }

  return (
    <section className="competition-mission" aria-labelledby="competition-squad-title">
      <div className="competition-proof-strip" aria-label="Verified playthrough evidence">
        <div><strong>{manifest.cell_count}/{manifest.cell_count}</strong><span>cells complete</span></div>
        <div><strong>{manifest.node_count}</strong><span>actual nodes</span></div>
        <div><strong>{manifest.actual_edge_count}</strong><span>actual edges</span></div>
        <div><strong>{manifest.legal_event_choice_count.toLocaleString("en-US")}</strong><span>legal choices</span></div>
        <p><ShieldCheck weight="fill" /> {manifest.truth_label}</p>
        <div className="competition-evidence-source" aria-label="Judge Mission evidence source">
          <button type="button" disabled={!latestPlaythrough} aria-pressed={isLatest} onClick={() => setEvidenceSource("latest")}>Latest campaign</button>
          <button type="button" aria-pressed={!isLatest} onClick={() => setEvidenceSource("replay")}>Signed Replay</button>
        </div>
      </div>

      <div className="competition-squad-layout">
        <div className="competition-squad">
          <header>
            <span id="competition-squad-title">STRATEGY SQUAD</span>
            <b>6 / 6</b>
          </header>
          <div className="competition-roster">
            <img
              src={personaRoster}
              alt="Six human strategy Personas: Newbie, Study, Money, Social, Visa, and Slacker"
            />
            <div className="competition-roster-controls">
              {PERSONA_ORDER.map((slug) => (
                <button
                  key={slug}
                  className={[
                    selectedSlug === slug ? "is-selected" : "",
                    hoveredSlug === slug ? "is-hovered" : "",
                  ].filter(Boolean).join(" ")}
                  type="button"
                  onMouseEnter={() => setHoveredSlug(slug)}
                  onMouseLeave={() => setHoveredSlug(null)}
                  onFocus={() => setHoveredSlug(slug)}
                  onBlur={() => setHoveredSlug(null)}
                  onClick={(event) => openDrawer(slug, event.currentTarget)}
                  aria-label={`Inspect ${PERSONA_LABELS[slug]} strategy`}
                >
                  <span>{PERSONA_LABELS[slug]}</span>
                </button>
              ))}
            </div>
          </div>
          <p>Hover for observed strategy evidence · click for the full contract</p>
        </div>
        <PersonaSummary persona={previewPersona} />
      </div>

      <div className="competition-route-card">
        <div className="competition-route-map" style={{ backgroundImage: `url(${missionMap})` }}>
          <div className="competition-route-line" aria-hidden="true">
            {cell.nodes.map((node) => (
              <span
                key={node.id}
                className={[
                  node.attractors.length > 0 ? "is-attractor" : "",
                  node.finished ? "is-terminal" : "",
                ].filter(Boolean).join(" ")}
              />
            ))}
          </div>
          <img className="competition-map-runner" src={moneyRunner} alt="Money strategy Persona at the first recorded attractor" />
          <div className="competition-route-label is-start">W1 · START</div>
          <div className="competition-route-label is-attractor">W3 · FIRST ATTRACTOR</div>
          <div className="competition-route-label is-ending">W19 · {cell.final_ending}</div>
        </div>
        <div className="competition-route-action">
          <div>
            <span>DEMO ROUTE · {isLatest ? "LATEST VERIFIED CAMPAIGN" : "SIGNED GODOT REPLAY"}</span>
            <strong>{PERSONA_LABELS[cell.persona]} · seed {cell.seed} · {cell.nodes.length} nodes · {cell.actual_edges.length} recorded transitions</strong>
            <small>Solid path is committed evidence. Unselected legal choices are never presented as future state.</small>
          </div>
          <Link
            to={`/playthrough-inspector?source=${isLatest ? "latest" : "replay"}&persona=${cell.persona}&seed=${cell.seed}`}
            aria-label={`Open ${PERSONA_LABELS[cell.persona]} seed ${cell.seed} in Playthrough Inspector`}
          >
            <Play weight="fill" /> Inspect {isLatest ? "latest path" : "signed replay"} <ArrowRight />
          </Link>
        </div>
      </div>

      {drawerPersona && (
        <div
          className="competition-drawer-backdrop"
          onMouseDown={(event) => event.target === event.currentTarget && closeDrawer()}
        >
          <aside
            ref={drawerRef}
            className="competition-persona-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="competition-drawer-title"
          >
            <header>
              <div><span>STRATEGY RECORD</span><h2 id="competition-drawer-title">{PERSONA_LABELS[drawerPersona.slug]}</h2></div>
              <button ref={closeButtonRef} type="button" onClick={closeDrawer} aria-label="Close Persona details"><X /></button>
            </header>
            <Link
              className="competition-drawer-cta"
              to={`/playthrough-inspector?source=${isLatest ? "latest" : "replay"}&persona=${drawerPersona.slug}&seed=${drawerCell?.seed ?? 42}`}
            >
              <Play weight="fill" /> Inspect {PERSONA_LABELS[drawerPersona.slug]} seed {drawerCell?.seed ?? 42} {isLatest ? "latest path" : "replay"} <ArrowRight />
            </Link>
            <section>
              <h3>Strategy contract</h3>
              <p>{PERSONA_DESCRIPTIONS[drawerPersona.slug]}</p>
              <Record label="Priorities" value={drawerPersona.contract.priorities.map(humanizeToken).join(" · ")} />
              <Record label="Hard avoids" value={drawerPersona.contract.hard_avoid.map(humanizeToken).join(" · ")} />
              <Record label="Risk / explore" value={`${drawerPersona.contract.risk_tolerance.toFixed(2)} / ${drawerPersona.contract.exploration.toFixed(2)}`} />
            </section>
            <section>
              <h3>Observed behavior</h3>
              <div className="competition-drawer-rates">
                {Object.entries(drawerPersona.observed.action_tag_rates).map(([label, value]) => (
                  <Record key={label} label={`${label} tag`} value={percent(value)} />
                ))}
              </div>
            </section>
            <section>
              <h3>Outcome and evidence</h3>
              <Record label="First attractor" value={`W${drawerPersona.observed.first_cashflow_stress_attractor_weeks.join(" / W")}`} />
              <Record label="Ending distribution" value={formatEnding(drawerPersona)} danger />
              <Record label="Seeds" value={drawerPersona.observed.seeds.join(" · ")} />
              <Record label="Completed cells" value={`${drawerPersona.observed.completed_cells}/${drawerPersona.observed.cell_count}`} />
              {drawerPersona.slug === "money" && <Record label="Selected trace" value={`${cell.cell_id} · ${cell.nodes.length} cited rows`} mono />}
            </section>
            <p className="competition-drawer-limit"><Info weight="fill" /> {isLatest ? "Latest campaign preserves its exact provider truth label." : "Replay proves reproducibility, not a fresh model call."}</p>
          </aside>
        </div>
      )}
    </section>
  );
}

function PersonaSummary({ persona }: { persona: PlaythroughPersona }) {
  const rates = Object.entries(persona.observed.action_tag_rates)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  const expectedTags = persona.contract.alignment_action_tags?.map(humanizeToken)
    ?? (persona.contract.alignment_risk_guided ? ["risk-guided choices"] : []);
  const topObserved = rates[0];
  return (
    <aside className="competition-persona-summary" aria-live="polite">
      <div className="competition-summary-heading">
        <div><span>HOVER SUMMARY</span><h2>{PERSONA_LABELS[persona.slug]}</h2></div>
        <Info weight="fill" />
      </div>
      <p>{PERSONA_DESCRIPTIONS[persona.slug]}</p>
      <dl className="competition-contract-strip">
        <div><dt>Risk</dt><dd>{persona.contract.risk_tolerance.toFixed(2)}</dd></div>
        <div><dt>Explore</dt><dd>{persona.contract.exploration.toFixed(2)}</dd></div>
        <div><dt>Intent</dt><dd>{persona.contract.failure_intent ? "Failure-seeking" : "Goal-seeking"}</dd></div>
      </dl>
      <h3>Observed divergence from strategy</h3>
      <div className="competition-rate-list">
        {rates.map(([label, value]) => (
          <div key={label}><span>{label}</span><b>{percent(value)}</b><progress max="1" value={value} /></div>
        ))}
      </div>
      <p className="competition-mismatch"><Info weight="fill" /> Strategy targets {expectedTags.join(" · ")}; observed top tag was {topObserved ? `${humanizeToken(topObserved[0])} at ${percent(topObserved[1])}` : "not recorded"}.</p>
      <div className="competition-summary-outcome">
        <span>First attractor</span><b>W{persona.observed.first_cashflow_stress_attractor_weeks.join(" / W")}</b>
        <span>Ending</span><b className="is-danger">{formatEnding(persona)}</b>
      </div>
    </aside>
  );
}

function formatEnding(persona: PlaythroughPersona): string {
  const [ending, count] = firstEnding(persona);
  return `${ending} · ${count}/${persona.observed.cell_count}`;
}

function Record({
  label,
  value,
  danger = false,
  mono = false,
}: {
  label: string;
  value: string;
  danger?: boolean;
  mono?: boolean;
}) {
  return (
    <div className={`competition-record ${danger ? "is-danger" : ""} ${mono ? "is-mono" : ""}`}>
      <span>{label}</span><b>{value}</b>
    </div>
  );
}
