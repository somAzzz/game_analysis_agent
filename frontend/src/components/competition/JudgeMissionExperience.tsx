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
import type { PlaythroughPersona, PlaythroughPersonaSlug } from "@/types";

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

function percent(value: number, digits = 1): string {
  return `${(value * 100).toFixed(digits)}%`;
}

function firstEnding(persona: PlaythroughPersona): [string, number] {
  return Object.entries(persona.observed.final_endings)[0] ?? ["unknown", 0];
}

export function JudgeMissionExperience() {
  const { manifest, personas, cell } = competitionPlaythrough;
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
            <span>DEMO ROUTE · ACTUAL GODOT REPLAY</span>
            <strong>Money · seed 42 · 19 nodes · 18 recorded transitions</strong>
            <small>Solid path is committed evidence. Unselected legal choices are never presented as future state.</small>
          </div>
          <Link to="/playthrough-inspector" aria-label="Open Money seed 42 in Playthrough Inspector">
            <Play weight="fill" /> Inspect signed replay <ArrowRight />
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
            <Link className="competition-drawer-cta" to={`/playthrough-inspector?persona=${drawerPersona.slug}`}>
              <Play weight="fill" /> Inspect {PERSONA_LABELS[drawerPersona.slug]} seed 42 replay <ArrowRight />
            </Link>
            <section>
              <h3>Strategy contract</h3>
              <p>{drawerPersona.contract.description}</p>
              <Record label="Priorities" value={drawerPersona.contract.priorities.join(" · ")} />
              <Record label="Hard avoids" value={drawerPersona.contract.hard_avoid.join(" · ")} />
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
            <p className="competition-drawer-limit"><Info weight="fill" /> Replay proves reproducibility, not a fresh OpenAI call.</p>
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
  return (
    <aside className="competition-persona-summary" aria-live="polite">
      <div className="competition-summary-heading">
        <div><span>HOVER SUMMARY</span><h2>{PERSONA_LABELS[persona.slug]}</h2></div>
        <Info weight="fill" />
      </div>
      <p>{persona.contract.description}</p>
      <dl className="competition-contract-strip">
        <div><dt>Risk</dt><dd>{persona.contract.risk_tolerance.toFixed(2)}</dd></div>
        <div><dt>Explore</dt><dd>{persona.contract.exploration.toFixed(2)}</dd></div>
        <div><dt>Seeds</dt><dd>{persona.observed.seeds.join(" · ")}</dd></div>
      </dl>
      <h3>Observed action mix</h3>
      <div className="competition-rate-list">
        {rates.map(([label, value]) => (
          <div key={label}><span>{label}</span><b>{percent(value)}</b><progress max="1" value={value} /></div>
        ))}
      </div>
      {persona.slug === "money" && (
        <p className="competition-mismatch"><Info weight="fill" /> Career actions were only {percent(persona.observed.action_tag_rates.career, 2)}</p>
      )}
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
