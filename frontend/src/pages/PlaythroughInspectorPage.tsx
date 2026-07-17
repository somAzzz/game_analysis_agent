import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CaretLeft,
  CaretRight,
  Check,
  Fingerprint,
  Pause,
  Play,
} from "@phosphor-icons/react";
import newbieRunner from "@/assets/competition/personas/persona-newbie-runner-v1.png";
import newbieRunnerFrameB from "@/assets/competition/personas/persona-newbie-runner-frame-b-v1.png";
import studyRunner from "@/assets/competition/personas/persona-study-runner-v1.png";
import studyRunnerFrameB from "@/assets/competition/personas/persona-study-runner-frame-b-v2.png";
import moneyRunner from "@/assets/competition/personas/persona-money-runner-v1.png";
import moneyRunnerFrameB from "@/assets/competition/personas/persona-money-runner-frame-b-v1.png";
import socialRunner from "@/assets/competition/personas/persona-social-runner-v1.png";
import socialRunnerFrameB from "@/assets/competition/personas/persona-social-runner-frame-b-v2.png";
import visaRunner from "@/assets/competition/personas/persona-visa-runner-v1.png";
import visaRunnerFrameB from "@/assets/competition/personas/persona-visa-runner-frame-b-v1.png";
import slackerRunner from "@/assets/competition/personas/persona-slacker-runner-v1.png";
import slackerRunnerFrameB from "@/assets/competition/personas/persona-slacker-runner-frame-b-v2.png";
import missionMap from "@/assets/competition/judge-mission-map-v1.png";
import { ForgeTopNav } from "@/components/competition/ForgeWorkspace";
import {
  DEFAULT_EVENT_LOCALE,
  localizedChoice,
  localizedEvent,
} from "@/lib/eventLocalization";
import { competitionPlaythrough } from "@/lib/playthrough";
import { loadLivePlaythrough, loadLivePlaythroughCell, loadPlaytestSession } from "@/lib/livePlaythrough";
import type {
  PlaytestSession,
  PlaythroughBundle,
  PlaythroughNode,
  PlaythroughPersonaSlug,
} from "@/types";

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

const PERSONA_RUNNERS: Record<PlaythroughPersonaSlug, readonly [string, string]> = {
  newbie: [newbieRunner, newbieRunnerFrameB],
  study: [studyRunner, studyRunnerFrameB],
  money: [moneyRunner, moneyRunnerFrameB],
  social: [socialRunner, socialRunnerFrameB],
  visa: [visaRunner, visaRunnerFrameB],
  slacker: [slackerRunner, slackerRunnerFrameB],
};

const METRICS = [
  ["money", "Money", "€"],
  ["energy", "Energy", ""],
  ["stress", "Stress", ""],
  ["hunger", "Hunger", ""],
  ["arrears_amount", "Arrears", "€"],
  ["cash_shortfall_count", "Shortfall", "×"],
] as const;

function stateNumber(state: Record<string, unknown>, key: string): number | null {
  const value = state[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function displayMetric(value: number | null, prefix: string): string {
  if (value === null) return "—";
  if (prefix === "€") return `€${value.toLocaleString("en-US")}`;
  if (prefix === "×") return `${value}×`;
  return String(value);
}

function selectedChoice(node: PlaythroughNode) {
  return node.event.legal_choices.find(
    (choice) => choice.choice_id === node.event.selected_choice_id,
  );
}

function isPersonaSlug(value: string | null): value is PlaythroughPersonaSlug {
  return PERSONA_ORDER.some((slug) => slug === value);
}
export function PlaythroughInspectorPage() {
  const [latestPlaythrough, setLatestPlaythrough] = useState<PlaythroughBundle | null>(null);
  const [latestError, setLatestError] = useState("");
  const [liveSession, setLiveSession] = useState<PlaytestSession | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const useLatest = Boolean(latestPlaythrough && searchParams.get("source") !== "replay");
  const bundle = useLatest ? latestPlaythrough! : competitionPlaythrough;
  const { manifest, cells, cellReferences } = bundle;
  const availablePersonas = PERSONA_ORDER.filter((slug) => (
    cellReferences.some((reference) => reference.persona === slug)
  ));
  const requestedPersona = searchParams.get("persona");
  const desiredPersona = isPersonaSlug(requestedPersona)
    && availablePersonas.includes(requestedPersona)
    ? requestedPersona
    : useLatest ? (availablePersonas[0] ?? "newbie") : "money";
  const requestedSeed = Number(searchParams.get("seed"));
  const availableSeeds = cellReferences
    .filter((reference) => reference.persona === desiredPersona)
    .map((reference) => reference.seed)
    .sort((left, right) => left - right);
  const desiredSeed = availableSeeds.includes(requestedSeed)
    ? requestedSeed
    : (availableSeeds[0] ?? 42);
  const cell = useLatest
    ? bundle.cell
    : (cells[desiredPersona] ?? bundle.cell);
  const personaSlug = cell.persona;
  const personaLabel = PERSONA_LABELS[personaSlug];
  const selectedPathPosition = cellReferences.findIndex((reference) => (
    reference.persona === cell.persona && reference.seed === cell.seed
  )) + 1;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const safeCurrentIndex = Math.min(currentIndex, Math.max(0, cell.nodes.length - 1));
  const currentNode = cell.nodes[safeCurrentIndex];
  const runnerFrameIndex = (currentNode.week - 1) % 2;
  const runnerAsset = PERSONA_RUNNERS[personaSlug][runnerFrameIndex];
  const choice = selectedChoice(currentNode);
  const eventCopy = localizedEvent(currentNode.event.id, DEFAULT_EVENT_LOCALE);
  const progress = currentIndex / Math.max(1, cell.nodes.length - 1);
  const runnerPosition = 5 + progress * 90;
  const metricRows = useMemo(
    () => METRICS.map(([key, label, prefix]) => ({
      key, label, prefix,
      before: stateNumber(currentNode.state_before, key),
      after: stateNumber(currentNode.state_after, key),
    })),
    [currentNode],
  );
  const stressMetric = metricRows.find((metric) => metric.key === "stress");
  const arrearsMetric = metricRows.find((metric) => metric.key === "arrears_amount");
  const sessionPercent = liveSession
    ? liveSession.status === "completed"
      ? 100
      : Math.min(99, Math.round(
          liveSession.progress.completed_weeks
          / Math.max(1, liveSession.progress.total_requested_weeks)
          * 100,
        ))
    : 0;
  useEffect(() => {
    const controller = new AbortController();
    loadLivePlaythrough(controller.signal)
      .then((value) => setLatestPlaythrough(value))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLatestError(error instanceof Error ? error.message : "Latest campaign unavailable");
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!useLatest || !latestPlaythrough) return undefined;
    if (latestPlaythrough.cell.persona === desiredPersona && latestPlaythrough.cell.seed === desiredSeed) {
      return undefined;
    }
    const reference = latestPlaythrough.cellReferences.find((item) => (
      item.persona === desiredPersona && item.seed === desiredSeed
    ));
    if (!reference) return undefined;
    const controller = new AbortController();
    loadLivePlaythroughCell(latestPlaythrough.manifest, reference, controller.signal)
      .then((nextCell) => setLatestPlaythrough((current) => current
        && current.manifest.campaign_id === latestPlaythrough.manifest.campaign_id
        ? { ...current, cell: nextCell, cells: { ...current.cells, [nextCell.persona]: nextCell } }
        : current))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLatestError(error instanceof Error ? error.message : "Selected path unavailable");
      });
    return () => controller.abort();
  }, [desiredPersona, desiredSeed, latestPlaythrough, useLatest]);

  useEffect(() => {
    const controller = new AbortController();
    let refreshing = false;
    const refresh = async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const session = await loadPlaytestSession(controller.signal);
        setLiveSession(session);
        if (
          session?.status === "completed"
          && latestPlaythrough?.manifest.campaign_id !== session.campaign_id
        ) {
          const completed = await loadLivePlaythrough(controller.signal);
          setLatestPlaythrough(completed);
        }
      } catch (error: unknown) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setLatestError(error instanceof Error ? error.message : "Live session unavailable");
      } finally {
        refreshing = false;
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1500);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [latestPlaythrough?.manifest.campaign_id]);

  useEffect(() => {
    setPlaying(false);
    setCurrentIndex(0);
  }, [cell.seed, personaSlug, manifest.campaign_id]);

  useEffect(() => {
    if (!playing) return undefined;
    const timer = window.setInterval(() => {
      setCurrentIndex((index) => {
        if (index >= cell.nodes.length - 1) {
          setPlaying(false);
          return index;
        }
        return index + 1;
      });
    }, 850);
    return () => window.clearInterval(timer);
  }, [cell.nodes.length, playing]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      const isFormControl = Boolean(target?.closest("input, textarea, select, [contenteditable='true']"));
      if (isFormControl) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        setPlaying(false);
        setCurrentIndex((index) => Math.max(0, index - 1));
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        setPlaying(false);
        setCurrentIndex((index) => Math.min(cell.nodes.length - 1, index + 1));
      } else if (event.code === "Space" && !target?.closest("button, a")) {
        event.preventDefault();
        setPlaying((value) => !value);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [cell.nodes.length]);

  function selectIndex(index: number): void {
    setPlaying(false);
    setCurrentIndex(Math.max(0, Math.min(cell.nodes.length - 1, index)));
  }

  function selectWeek(week: number): void {
    const index = cell.nodes.findIndex((node) => node.week === week);
    if (index >= 0) selectIndex(index);
  }
  function selectPersona(slug: PlaythroughPersonaSlug): void {
    const next = new URLSearchParams(searchParams);
    const seeds = cellReferences
      .filter((reference) => reference.persona === slug)
      .map((reference) => reference.seed);
    next.set("persona", slug);
    next.set("seed", String(seeds.includes(desiredSeed) ? desiredSeed : (seeds[0] ?? 42)));
    setSearchParams(next, { replace: true });
  }
  function selectSeed(seed: number): void {
    const next = new URLSearchParams(searchParams);
    next.set("seed", String(seed));
    setSearchParams(next, { replace: true });
  }


  function selectSource(source: "replay" | "latest"): void {
    const next = new URLSearchParams(searchParams);
    if (source === "replay") next.set("source", "replay");
    else next.delete("source");
    setSearchParams(next, { replace: true });
  }


  return (
    <div className="judge-shell playthrough-shell">
      <ForgeTopNav active="playthrough" truthLabel={manifest.truth_label} />

      <main className="playthrough-page">
        <section className="playthrough-heading">
          <Link to="/"><ArrowLeft /> Judge Mission</Link>
          <div>
            <p className="playthrough-eyebrow">PLAYTHROUGH INSPECTOR · SIGNED ACTUAL PATH</p>
            <h1>{personaLabel} runs the evidence, one week at a time.</h1>
          </div>
          <dl>
            <div><dt>Persona</dt><dd>{personaLabel}</dd></div>
            <div><dt>Seed</dt><dd>{cell.seed}</dd></div>
            <div><dt>Nodes</dt><dd>{cell.nodes.length}</dd></div>
            <div><dt>Edges</dt><dd>{cell.actual_edges.length}</dd></div>
          </dl>
        </section>

        {liveSession && (
          <section
            className={`playthrough-session is-${liveSession.status}`}
            aria-label="Codex playtest session"
            aria-live="polite"
          >
            <header>
              <div><span>CODEX PLAYTEST SESSION</span><strong>{liveSession.campaign_id}</strong></div>
              <b>{liveSession.status.toUpperCase()}</b>
            </header>
            <div className="playthrough-session-progress">
              <span style={{ width: `${sessionPercent}%` }} />
            </div>
            <dl>
              <div><dt>Provider</dt><dd>{liveSession.provider} · {liveSession.model}</dd></div>
              <div><dt>Cells</dt><dd>{liveSession.progress.completed_cells}/{liveSession.progress.total_cells}</dd></div>
              <div><dt>Weeks recorded</dt><dd>{liveSession.progress.completed_weeks}/{liveSession.progress.total_requested_weeks}</dd></div>
              <div><dt>Truth</dt><dd>{liveSession.truth_label}</dd></div>
            </dl>
            {liveSession.latest && (
              <p>
                <strong>{PERSONA_LABELS[liveSession.latest.persona]} · seed {liveSession.latest.seed} · W{liveSession.latest.week}/{liveSession.latest.max_weeks}</strong>
                <span>{liveSession.latest.phase} · {liveSession.latest.triggered_event_id || "choosing next action"}</span>
              </p>
            )}
            <small>{liveSession.message}</small>
          </section>
        )}

        <section className="playthrough-persona-switcher playthrough-source-switcher" aria-label="Evidence source">
          <header>
            <span>EVIDENCE SOURCE</span>
            <small>{latestError || (latestPlaythrough ? "Generated campaign evidence is ready" : "Signed Replay fallback is active")}</small>
          </header>
          <div>
            <button type="button" className={!useLatest ? "is-active" : ""} aria-pressed={!useLatest} onClick={() => selectSource("replay")}>
              <span>Signed Replay</span><small>prerecorded · real Godot</small>
            </button>
            <button type="button" disabled={!latestPlaythrough} className={useLatest ? "is-active" : ""} aria-pressed={useLatest} onClick={() => selectSource("latest")}>
              <span>Latest campaign</span><small>{latestPlaythrough?.manifest.truth_label ?? "not generated"}</small>
            </button>
          </div>
        </section>

        <section className="playthrough-persona-switcher" aria-label="Playthrough strategy">
          <header>
            <span>PLAY AS STRATEGY</span>
            <small>{useLatest ? `${manifest.source.provider} · ${manifest.truth_label}` : "Each Persona opens its own verified seed 42 path"}</small>
          </header>
          <div>
            {availablePersonas.map((slug) => (
              <button
                key={slug}
                type="button"
                className={slug === personaSlug ? "is-active" : ""}
                aria-pressed={slug === personaSlug}
                aria-label={`Use ${PERSONA_LABELS[slug]} strategy playthrough`}
                onClick={() => selectPersona(slug)}
              >
                <img src={PERSONA_RUNNERS[slug][0]} alt="" />
                <span>{PERSONA_LABELS[slug]}</span>
                <small>seed {slug === personaSlug ? cell.seed : (cellReferences.find((item) => item.persona === slug)?.seed ?? "—")}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="playthrough-path-selector" aria-labelledby="playthrough-seed-title">
          <div>
            <span id="playthrough-seed-title">SEED PATH</span>
            <small>Path {Math.max(1, selectedPathPosition)} of {cellReferences.length} in this evidence source</small>
          </div>
          <label>
            <span>Seed</span>
            <select value={desiredSeed} onChange={(event) => selectSeed(Number(event.target.value))}>
              {availableSeeds.map((seed) => <option key={seed} value={seed}>seed {seed}</option>)}
            </select>
          </label>
          <p><b>{cell.final_ending}</b><span>{cell.completed_weeks} decisions · {cell.stop_reason.replaceAll("_", " ")}</span></p>
        </section>

        <section className="playthrough-route" aria-labelledby="playthrough-route-title">
          <header>
            <span id="playthrough-route-title">{useLatest ? `ACTUAL ${cell.provider_mode.toUpperCase()} PATH` : "ACTUAL REPLAY PATH"}</span>
            <div className="playthrough-live-signal" aria-live="polite">
              <strong>{eventCopy.title}</strong>
              <span>Stress {displayMetric(stressMetric?.before ?? null, "")} → {displayMetric(stressMetric?.after ?? null, "")}</span>
              <span>Arrears {displayMetric(arrearsMetric?.before ?? null, "€")} → {displayMetric(arrearsMetric?.after ?? null, "€")}</span>
            </div>
            <b>W{currentNode.week} / W{cell.completed_weeks}</b>
          </header>
          <div className="playthrough-route-scroll">
            <div className="playthrough-route-stage" style={{ backgroundImage: `url(${missionMap})` }}>
              <div
                className={`playthrough-runner-anchor ${currentIndex >= 13 ? "is-late" : ""}`}
                style={{ left: `${runnerPosition}%` }}
                data-runner-frame={runnerFrameIndex + 1}
                tabIndex={0}
                aria-label={`${personaLabel} current state at recorded week ${currentNode.week}`}
                aria-describedby="playthrough-runner-state"
              >
                <img
                  className="playthrough-runner"
                  src={runnerAsset}
                  alt=""
                />
                <div id="playthrough-runner-state" className="playthrough-runner-tooltip" role="tooltip">
                  <span>CURRENT STATE · W{currentNode.week}</span>
                  <strong>{personaLabel}</strong>
                  <dl>
                    {metricRows.map((metric) => (
                      <div key={metric.key}>
                        <dt>{metric.label}</dt>
                        <dd>{displayMetric(metric.after, metric.prefix)}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </div>
              <ol>
                {cell.nodes.map((node, index) => {
                  const unselectedChoices = node.event.legal_choices.filter(
                    (item) => item.choice_id !== node.event.selected_choice_id,
                  );
                  return (
                    <li
                      key={node.id}
                      className={[
                        index < currentIndex ? "is-past" : "",
                        index === currentIndex ? "is-active" : "",
                        node.attractors.length > 0 ? "is-attractor" : "",
                        node.finished ? "is-terminal" : "",
                      ].filter(Boolean).join(" ")}
                    >
                      <button
                        type="button"
                        onClick={() => selectIndex(index)}
                        aria-label={`Go to recorded week ${node.week}`}
                        aria-current={index === currentIndex ? "step" : undefined}
                      >
                        {node.week}
                      </button>
                      <span className="playthrough-option-stubs" aria-hidden="true">
                        {unselectedChoices.slice(0, 3).map((item) => <i key={item.choice_id} />)}
                      </span>
                      {(node.week === 1 || node.week === 3 || node.week === 19) && (
                        <small>{node.week === 1 ? "START" : node.week === 3 ? "FIRST ATTRACTOR" : "ENDING"}</small>
                      )}
                    </li>
                  );
                })}
              </ol>
            </div>
          </div>
          <footer>
            <span><i className="is-actual" /> recorded transition</span>
            <span><i className="is-legal" /> legal option · not executed</span>
            <span><i className="is-risk" /> attractor / terminal risk</span>
          </footer>
        </section>

        <section className="playthrough-controls" aria-label="Replay controls">
          <div>
            <button type="button" disabled={currentIndex === 0} onClick={() => selectIndex(currentIndex - 1)}><CaretLeft /> Previous</button>
            <button type="button" className="is-play" onClick={() => setPlaying((value) => !value)}>
              {playing ? <Pause weight="fill" /> : <Play weight="fill" />} {playing ? "Pause" : "Play"}
            </button>
            <button type="button" disabled={currentIndex === cell.nodes.length - 1} onClick={() => selectIndex(currentIndex + 1)}>Next <CaretRight /></button>
          </div>
          <div aria-label="Key review weeks">
            <span>JUMP TO</span>
            <button type="button" onClick={() => selectWeek(1)}>W1 Start</button>
            <button type="button" onClick={() => selectWeek(3)}>W3 Attractor</button>
            <button type="button" onClick={() => selectWeek(19)}>W19 Ending</button>
          </div>
          <small>Keyboard: ← → · Space</small>
        </section>

        <section className="playthrough-record-grid">
          <article className="playthrough-week-record">
            <header>
              <span>W{currentNode.week.toString().padStart(2, "0")}</span>
              <div className="playthrough-event-heading"><small>EVENT · {currentNode.event.id}</small><h2>{eventCopy.title}</h2><p>{eventCopy.body}</p></div>
              {currentNode.attractors.length > 0 && <b>FIRST ATTRACTOR</b>}
              {currentNode.finished && <b className="is-terminal">{cell.final_ending}</b>}
            </header>
            <div className="playthrough-week-columns">
              <section>
                <h3>Selected actions</h3>
                <ul className="playthrough-action-list">
                  {currentNode.selected_action_ids.map((action) => <li key={action}>{action}</li>)}
                </ul>
                <h3>Event choices</h3>
                <ul className="playthrough-choice-list">
                  {currentNode.event.legal_choices.map((item) => {
                    const isSelected = item.choice_id === currentNode.event.selected_choice_id;
                    return (
                      <li key={item.choice_id} className={isSelected ? "is-selected" : ""}>
                        <span>{isSelected ? <Check weight="bold" /> : null}</span>
                        <div><b>{localizedChoice(currentNode.event.id, item, DEFAULT_EVENT_LOCALE)}</b><small>{isSelected ? "observed result" : "legal here · future not executed"}</small></div>
                      </li>
                    );
                  })}
                </ul>
              </section>
              <section>
                <h3>State delta</h3>
                <dl className="playthrough-state-delta">
                  {metricRows.map((metric) => (
                    <div key={metric.key} className={["stress", "hunger", "arrears_amount"].includes(metric.key) ? "is-risk" : ""}>
                      <dt>{metric.label}</dt>
                      <dd><span>{displayMetric(metric.before, metric.prefix)}</span><ArrowRight /><b>{displayMetric(metric.after, metric.prefix)}</b></dd>
                    </div>
                  ))}
                </dl>
                <div className="playthrough-selected-choice"><small>SELECTED CHOICE</small><strong>{localizedChoice(currentNode.event.id, choice, DEFAULT_EVENT_LOCALE)}</strong></div>
              </section>
            </div>
          </article>

          <aside className="playthrough-console" aria-label="Evidence console">
            <header><span>EVIDENCE CONSOLE</span><b>{cell.nodes.length} cited rows</b></header>
            <div className="playthrough-console-head"><span>WEEK</span><span>EVENT / CHOICE</span><span>HASH</span></div>
            <div className="playthrough-console-rows">
              {cell.nodes.map((node, index) => (
                <button key={node.id} type="button" className={index === currentIndex ? "is-active" : ""} onClick={() => selectIndex(index)}>
                  <span>W{node.week}</span>
                  <span><b>{localizedEvent(node.event.id, DEFAULT_EVENT_LOCALE).title}</b><small>{localizedChoice(node.event.id, selectedChoice(node), DEFAULT_EVENT_LOCALE)}</small></span>
                  <code>{node.evidence.source_record_sha256.slice(0, 8)}</code>
                </button>
              ))}
            </div>
          </aside>
        </section>

        <section className="playthrough-provenance">
          <Fingerprint weight="fill" />
          <div><span>SOURCE LINE</span><b>{currentNode.evidence.source_line}</b></div>
          <div><span>ROW SHA-256</span><code>{currentNode.evidence.source_record_sha256}</code></div>
          <div><span>PROVENANCE</span><b>{cell.provider_mode} · real Godot · {cell.game_commit.slice(0, 12)}</b></div>
        </section>
      </main>
    </div>
  );
}
