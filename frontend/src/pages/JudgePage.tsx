import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  createJudgeCampaign,
  fetchJudgeCampaign,
  fetchJudgeExperiment,
  fetchJudgeProviderStatus,
  fetchStaticJudgeExperiment,
  testJudgeProvider,
} from "@/lib/api";
import type {
  JudgeCampaignJob,
  JudgeCohort,
  JudgeExperiment,
  JudgeProvider,
  JudgeProviderStatus,
} from "@/types";

const PROVIDER_LABEL: Record<JudgeProvider, string> = {
  replay: "Deterministic policy Replay",
  openai: "OpenAI live subagent",
};

function cohort(experiment: JudgeExperiment, id: JudgeCohort["cohort"]): JudgeCohort {
  const match = experiment.cohorts.find((item) => item.cohort === id);
  if (!match) throw new Error(`Missing required cohort: ${id}`);
  return match;
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function errorMessage(error: unknown): string {
  if (!(error instanceof Error)) return String(error);
  const remediation = "remediation" in error ? String(error.remediation ?? "") : "";
  return remediation ? `${error.message} ${remediation}` : error.message;
}

export function JudgePage() {
  const [experiment, setExperiment] = useState<JudgeExperiment | null>(null);
  const [providerStatus, setProviderStatus] = useState<JudgeProviderStatus | null>(null);
  const [provider, setProvider] = useState<JudgeProvider>("replay");
  const [source, setSource] = useState<"api" | "static">("api");
  const [campaign, setCampaign] = useState<JudgeCampaignJob | null>(null);
  const [activity, setActivity] = useState("Loading the signed public evidence…");
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([fetchJudgeProviderStatus(), fetchJudgeExperiment()]).then(async ([status, proof]) => {
      if (!active) return;
      if (status.status === "fulfilled") setProviderStatus(status.value);
      if (proof.status === "fulfilled") {
        setExperiment(proof.value);
        setActivity("Judge API connected. Replay is ready; live mode is configuration-gated.");
        return;
      }
      try {
        const frozen = await fetchStaticJudgeExperiment();
        if (!active) return;
        setExperiment(frozen);
        setSource("static");
        setActivity("Static evaluator mode: signed prerecorded evidence is available without a server.");
      } catch (error) {
        if (active) setActivity(`Evidence unavailable: ${errorMessage(error)}`);
      }
    });
    return () => {
      active = false;
      if (pollRef.current !== null) window.clearTimeout(pollRef.current);
    };
  }, []);

  const openAIReady = providerStatus?.providers.openai.live_campaign_ready === true;
  const providerDisabled = source === "static" || (provider === "openai" && !openAIReady);

  async function handleProviderTest() {
    setBusy(true);
    setActivity(`Testing ${PROVIDER_LABEL[provider]}…`);
    try {
      await testJudgeProvider(provider);
      setActivity(`${PROVIDER_LABEL[provider]} passed its bounded provider check.`);
    } catch (error) {
      setActivity(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function handleCampaign() {
    setBusy(true);
    setActivity(`Starting ${PROVIDER_LABEL[provider]} campaign…`);
    try {
      const created = await createJudgeCampaign(provider);
      setCampaign(created);
      const poll = async () => {
        try {
          const current = await fetchJudgeCampaign(created.campaign_id);
          setCampaign(current);
          if (current.status === "queued" || current.status === "running") {
            pollRef.current = window.setTimeout(poll, 350);
          } else {
            setBusy(false);
            setActivity(
              current.status === "completed"
                ? `${PROVIDER_LABEL[provider]} campaign completed with evidence attached.`
                : current.error?.message ?? `Campaign ${current.status}.`,
            );
          }
        } catch (error) {
          setBusy(false);
          setActivity(errorMessage(error));
        }
      };
      await poll();
    } catch (error) {
      setBusy(false);
      setActivity(errorMessage(error));
    }
  }

  const campaignResult = useMemo(() => {
    if (!campaign?.result) return null;
    return Object.entries(campaign.result)
      .filter(([key]) => ["completed_cells", "total_weeks", "valid_rate"].includes(key))
      .map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`)
      .join(" · ");
  }, [campaign]);

  if (!experiment) {
    return (
      <main className="judge-shell judge-loading">
        <p className="judge-kicker">Playtest Forge / evaluator view</p>
        <h1>Evidence is being verified.</h1>
        <p role="status">{activity}</p>
      </main>
    );
  }

  const baselineFixed = cohort(experiment, "baseline_fixed");
  const patchedFixed = cohort(experiment, "patched_fixed");
  const baselineHoldout = cohort(experiment, "baseline_holdout");
  const patchedHoldout = cohort(experiment, "patched_holdout");

  return (
    <div className="judge-shell">
      <header className="judge-nav">
        <Link className="judge-wordmark" to="/">PLAYTEST / FORGE</Link>
        <span>Codex-led causal game testing</span>
        <Link to="/reports">Report archive ↗</Link>
      </header>

      <section className="judge-hero" aria-labelledby="judge-title">
        <div>
          <p className="judge-kicker">OpenAI Build Week 2026 · Judge Mode</p>
          <h1 id="judge-title">A patch passed its unit test.<br /><em>We still rejected it.</em></h1>
        </div>
        <aside className="judge-verdict" aria-label="Experiment verdict">
          <span>Final decision</span>
          <strong>{experiment.decision}</strong>
          <small>{experiment.experiment_id}</small>
        </aside>
        <p className="judge-thesis">
          Codex plans the campaign, coordinates persona playthroughs against a real Godot game,
          proposes one bounded repair, and lets fixed plus unseen holdout evidence—not optimism—decide.
        </p>
        <p className="judge-mode"><span aria-hidden="true">●</span> {source === "static" ? "Static evaluator copy" : "Judge API connected"} · prerecorded evidence · hashes verified before publication</p>
      </section>

      <main className="judge-ledger">
        <section className="judge-stage" aria-labelledby="campaign-title">
          <div className="judge-stage-marker"><span>01</span><b>CAMPAIGN</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">Observe before editing</p>
            <h2 id="campaign-title">Six personas converged on one failure.</h2>
            <div className="judge-metrics" aria-label="Campaign facts">
              <Metric value="18" label="persona × seed cells" />
              <Metric value="342" label="Godot weeks" />
              <Metric value="100%" label="valid actions" />
              <Metric value="18/18" label="cashflow collapse" intent="danger" />
            </div>
            <p className="judge-copy">The game runtime is automated; the action provider is swappable. Replay is a deterministically authored persona-policy fixture—not a recorded LLM run. OpenAI runs the same bounded interface as a live persona subagent when server configuration is ready.</p>

            <div className="judge-console">
              <fieldset>
                <legend>Action provider</legend>
                {(["replay", "openai"] as JudgeProvider[]).map((item) => (
                  <label key={item} className={provider === item ? "is-selected" : ""}>
                    <input
                      type="radio"
                      name="provider"
                      value={item}
                      checked={provider === item}
                      onChange={() => setProvider(item)}
                    />
                    <span>{PROVIDER_LABEL[item]}</span>
                    <small>{item === "replay" ? "fixture policy · no key" : openAIReady ? "live · server key ready" : "live · configuration required"}</small>
                  </label>
                ))}
              </fieldset>
              <div className="judge-actions">
                <button type="button" className="judge-button-secondary" disabled={busy || providerDisabled} onClick={handleProviderTest}>Test provider</button>
                <button type="button" className="judge-button-primary" disabled={busy || providerDisabled} onClick={handleCampaign}>{busy ? "Running…" : "Run bounded campaign"}</button>
              </div>
              <p className="judge-activity" role="status" aria-live="polite">{activity}</p>
              {campaign && <p className="judge-job"><b>{campaign.status.toUpperCase()}</b> · {campaign.campaign_id}{campaignResult ? ` · ${campaignResult}` : ""}</p>}
            </div>
          </div>
        </section>

        <section className="judge-stage" aria-labelledby="repair-title">
          <div className="judge-stage-marker"><span>02</span><b>REPAIR</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">One hypothesis · one bounded mechanism</p>
            <h2 id="repair-title">Codex changed the recurring cost drift.</h2>
            <blockquote>{experiment.hypothesis}</blockquote>
            <div className="judge-patch">
              <div>
                <span>Candidate patch</span>
                <strong>{experiment.patch.changed_files} files · +{experiment.patch.added_lines} / −{experiment.patch.deleted_lines}</strong>
                <code>{experiment.patch.patched_commit.slice(0, 12)}</code>
              </div>
              <ul>
                {experiment.patch.modified_paths.map((path) => <li key={path}>{path}</li>)}
              </ul>
              <div className="judge-stamp" aria-label="Candidate repair rejected">REJECTED</div>
            </div>
            <details className="judge-diff">
              <summary>
                <span>View exact candidate diff</span>
                <code>sha256 {experiment.patch.patch_sha256.slice(0, 12)}</code>
              </summary>
              <div className="judge-diff-meta">
                <p><span>Canonical demo</span><code>{experiment.patch.canonical_source_path} @ {experiment.patch.baseline_commit.slice(0, 12)}</code></p>
                <p><span>Disposition</span><strong>{experiment.patch.disposition.replaceAll("_", " ")}</strong></p>
              </div>
              <pre aria-label="Exact candidate source diff"><code>{experiment.patch.diff.split("\n").map((line, index) => (
                <span
                  // A patch can contain identical text on different lines.
                  key={`${index}-${line}`}
                  className={line.startsWith("+") && !line.startsWith("+++") ? "is-addition" : line.startsWith("-") && !line.startsWith("---") ? "is-deletion" : undefined}
                >{line}{"\n"}</span>
              ))}</code></pre>
            </details>
            <p className="judge-copy">The focused Godot validator passed. That proves the implementation is internally legal; it does not prove the player-level failure was repaired.</p>
            <dl className="judge-provenance">
              <div><dt>Planner</dt><dd>Codex main agent</dd></div>
              <div><dt>Skill</dt><dd>{experiment.codex.skill}</dd></div>
              <div><dt>Mechanism lock</dt><dd>{experiment.mechanism_class}</dd></div>
            </dl>
          </div>
        </section>

        <section className="judge-stage" aria-labelledby="proof-title">
          <div className="judge-stage-marker"><span>03</span><b>PROOF</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">Fixed seeds + unseen holdout</p>
            <h2 id="proof-title">Cash improved. The failure did not.</h2>
            <div className="judge-comparison">
              <CohortPair label="Fixed cohort" baseline={baselineFixed} patched={patchedFixed} reduction={experiment.comparison.fixed_relative_reduction} />
              <CohortPair label="Unseen holdout" baseline={baselineHoldout} patched={patchedHoldout} reduction={experiment.comparison.holdout_relative_reduction} />
            </div>
            <div className="judge-gates">
              <h3>Acceptance gates</h3>
              <ol>
                {experiment.gates.map((gate) => (
                  <li key={gate.gate_id} className={gate.status === "failed" ? "failed" : "passed"}>
                    <span aria-hidden="true">{gate.status === "failed" ? "×" : "✓"}</span>
                    <div><b>{gate.gate_id.replaceAll("_", " ")}</b><small>{gate.detail}</small></div>
                    <em>{gate.status}</em>
                  </li>
                ))}
              </ol>
            </div>
            <p className="judge-decision"><span>Decision</span><strong>{experiment.decision}</strong>{experiment.decision_reason}</p>
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({ value, label, intent }: { value: string; label: string; intent?: "danger" }) {
  return <div className={intent === "danger" ? "is-danger" : ""}><strong>{value}</strong><span>{label}</span></div>;
}

function CohortPair({ label, baseline, patched, reduction }: { label: string; baseline: JudgeCohort; patched: JudgeCohort; reduction: number }) {
  return (
    <article>
      <h3>{label}</h3>
      <div className="judge-outcome"><span>baseline</span><strong>{baseline.target_members}/{baseline.cells}</strong><small>€{baseline.mean_final_money?.toFixed(0) ?? "—"} mean cash</small></div>
      <span className="judge-arrow" aria-hidden="true">→</span>
      <div className="judge-outcome"><span>patched</span><strong>{patched.target_members}/{patched.cells}</strong><small>€{patched.mean_final_money?.toFixed(0) ?? "—"} mean cash</small></div>
      <p><b>{percent(reduction)}</b> failure reduction</p>
    </article>
  );
}
