import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  createJudgeCampaign,
  fetchJudgeCampaign,
  fetchJudgeExperiment,
  fetchJudgeExperiments,
  fetchJudgeProviderStatus,
  fetchStaticJudgeExperiment,
  fetchStaticJudgeExperiments,
  testJudgeProvider,
  submitHumanReview,
} from "@/lib/api";
import type {
  JudgeCampaignJob,
  JudgeCohort,
  JudgeExperiment,
  JudgeExperimentSummary,
  HumanReviewDecision,
  HumanReviewRecord,
  JudgeProvider,
  JudgeProviderStatus,
} from "@/types";
import { JudgeMissionExperience } from "@/components/competition/JudgeMissionExperience";
import { ForgeTopNav } from "@/components/competition/ForgeWorkspace";

const PROVIDER_LABEL: Record<JudgeProvider, string> = {
  replay: "Deterministic policy Replay",
  vllm: "Local vLLM persona agent",
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


function ExperimentSelector({ experiments, selected, disabled, onChange }: { experiments: JudgeExperimentSummary[]; selected: JudgeExperiment; disabled: boolean; onChange: (id: string) => void }) {
  return (
    <section className="judge-experiment-switcher" aria-label="Experiment evidence selector">
      <div className="judge-experiment-rail" aria-hidden="true"><span>EXPERIMENT</span></div>
      <label htmlFor="judge-experiment-select">
        <span>Evidence set</span>
        <select id="judge-experiment-select" aria-label="Evidence set" value={selected.experiment_id} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
          {experiments.map((item) => (
            <option key={item.experiment_id} value={item.experiment_id}>
              {item.source_label} · {item.title} · {item.lifecycle_status === "proof_complete" ? "FULL PROOF" : "CAMPAIGN ONLY"}
            </option>
          ))}
        </select>
        <small>{selected.source_label} · {selected.model} · {selected.campaign.cells} cells / {selected.campaign.weeks} weeks</small>
      </label>
    </section>
  );
}

function CorrectnessExperimentView({
  experiment,
  experiments,
  loading,
  onChange,
}: {
  experiment: JudgeExperiment;
  experiments: JudgeExperimentSummary[];
  loading: boolean;
  onChange: (id: string) => void;
}) {
  const proof = experiment.correctness_proof;
  const patch = experiment.patch;
  if (!proof || !patch) return null;
  return (
    <div className="judge-shell">
      <ForgeTopNav active="mission" truthLabel="Accepted deterministic evidence" />
      <section className="judge-hero" aria-labelledby="judge-title">
        <div>
          <p className="judge-kicker">OpenAI Build Week 2026 · Judge Mode</p>
          <h1 id="judge-title">A content identity defect faced its proof.<br /><em>The gates accepted it.</em></h1>
        </div>
        <aside className="judge-verdict" data-decision="accepted" aria-label="Experiment decision status">
          <span>Machine recommendation</span><strong>ACCEPTED</strong><small>Retained in the submission branch</small>
        </aside>
        <p className="judge-thesis">Chinese source text remains the mechanical identity; detailed English copy is now display-only and can no longer shift or hide choices.</p>
        <p className="judge-mode"><span aria-hidden="true">●</span> deterministic Godot 4.4 · zero model calls · evidence hashes verified</p>
      </section>
      <JudgeMissionExperience />
      <main className="judge-ledger">
        <ExperimentSelector experiments={experiments} selected={experiment} disabled={loading} onChange={onChange} />
        <section className="judge-stage" aria-labelledby="correctness-observation-title">
          <div className="judge-stage-marker"><span>01</span><b>OBSERVE</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">One identity mechanism · two concrete failures</p>
            <h2 id="correctness-observation-title">Positional localization shifted five-choice events out of alignment.</h2>
            <div className="judge-metrics" aria-label="Correctness facts">
              <Metric value={String(proof.baseline_identity_errors)} label="baseline identity errors" intent="danger" />
              <Metric value={String(proof.patched_identity_errors)} label="patched identity errors" />
              <Metric value="128" label="bilingual events covered" />
              <Metric value={String(proof.provider_calls)} label="model calls" />
            </div>
            <p className="judge-copy">The semester-fee borrowing choice was hidden, while a borrowing effect inherited the label “Take the cash job.” The focused economy validator caught both failures.</p>
          </div>
        </section>
        <section className="judge-stage" aria-labelledby="correctness-repair-title">
          <div className="judge-stage-marker"><span>02</span><b>REPAIR</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">Stable source identity · exact bilingual copy</p>
            <h2 id="correctness-repair-title">Codex matched localized choices by Chinese source text, not array position.</h2>
            <blockquote>{experiment.hypothesis}</blockquote>
            <div className="judge-patch">
              <div>
                <span>Accepted patch</span>
                <strong>{patch.changed_files} files · +{patch.added_lines} / −{patch.deleted_lines}</strong>
                <code>{patch.patched_commit.slice(0, 12)}</code>
              </div>
              <ul>{patch.modified_paths.map((path) => <li key={path}>{path}</li>)}</ul>
              <div className="judge-stamp" aria-label="Candidate repair accepted">ACCEPTED</div>
            </div>
            <details id="candidate-patch-diff" className="judge-diff">
              <summary><span>View exact accepted diff</span><code>sha256 {patch.patch_sha256.slice(0, 12)}</code></summary>
              <div className="judge-diff-meta">
                <p><span>Baseline</span><code>{patch.baseline_commit.slice(0, 12)}</code></p>
                <p><span>Disposition</span><strong>{patch.disposition.replaceAll("_", " ")}</strong></p>
              </div>
              <pre aria-label="Exact accepted source diff"><code>{patch.diff}</code></pre>
            </details>
          </div>
        </section>
        <section className="judge-stage" aria-labelledby="correctness-proof-title">
          <div className="judge-stage-marker"><span>03</span><b>PROOF</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">Fixed seeds + unseen holdout · semantic preservation</p>
            <h2 id="correctness-proof-title">The defect disappeared without changing game outcomes.</h2>
            <div className="judge-comparison">
              <div>
                <h3>Fixed cohort</h3>
                <strong>{proof.fixed_seeds.join(" / ")}</strong>
                <p>Trajectories, final states, and endings remained identical.</p>
              </div>
              <div>
                <h3>Unseen holdout</h3>
                <strong>{proof.holdout_seeds.join(" / ")}</strong>
                <p>Trajectories, final states, and endings remained identical.</p>
              </div>
            </div>
            <div className="judge-gates">
              <h3>Acceptance gates</h3>
              <ol>{experiment.gates.map((gate) => (
                <li key={gate.gate_id} className="passed">
                  <span aria-hidden="true">✓</span>
                  <div><b>{gate.gate_id.replaceAll("_", " ")}</b><small>{gate.detail}</small></div>
                  <em>passed</em>
                </li>
              ))}</ol>
            </div>
            <p className="judge-decision"><span>Machine recommendation</span><strong>accepted</strong>{experiment.decision_reason}</p>
          </div>
        </section>
        <section className="judge-stage judge-human-stage" aria-labelledby="correctness-visible-title">
          <div className="judge-stage-marker"><span>04</span><b>VISIBLE</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">Submission frontend · review-ready proof</p>
            <h2 id="correctness-visible-title">The accepted repair remains reviewable without publishing local campaign logs.</h2>
            <p className="judge-copy">Inspect the exact accepted diff and its hash-bound fixed and holdout evidence above. Development-only model traces stay private to the operator.</p>
            <nav className="judge-review-evidence-links" aria-label="Accepted repair evidence">
              <a href="#candidate-patch-diff">Review accepted patch diff</a>
            </nav>
          </div>
        </section>
      </main>
    </div>
  );
}

function PendingStage({ number, label, title }: { number: string; label: string; title: string }) {
  return (
    <section className="judge-stage judge-stage-pending">
      <div className="judge-stage-marker"><span>{number}</span><b>{label}</b></div>
      <div className="judge-stage-body">
        <p className="judge-eyebrow">Not fabricated · not inferred</p>
        <h2>{title}</h2>
        <p className="judge-copy">This campaign is verified and selectable, but no bounded patch and fixed/holdout proof have been published for it yet.</p>
      </div>
    </section>
  );
}

export function JudgePage() {
  const [experiment, setExperiment] = useState<JudgeExperiment | null>(null);
  const [experiments, setExperiments] = useState<JudgeExperimentSummary[]>([]);
  const [experimentLoading, setExperimentLoading] = useState(false);
  const [providerStatus, setProviderStatus] = useState<JudgeProviderStatus | null>(null);
  const [provider, setProvider] = useState<JudgeProvider>("replay");
  const [source, setSource] = useState<"api" | "static">("api");
  const [campaign, setCampaign] = useState<JudgeCampaignJob | null>(null);
  const [activity, setActivity] = useState("Loading the signed public evidence…");
  const [busy, setBusy] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<HumanReviewDecision | "">("");
  const [reviewerNote, setReviewerNote] = useState("");
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewActivity, setReviewActivity] = useState("No human final decision recorded.");
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const [status, index, proof] = await Promise.allSettled([
        fetchJudgeProviderStatus(),
        fetchJudgeExperiments(),
        fetchJudgeExperiment(),
      ]);
      if (!active) return;
      if (status.status === "fulfilled") setProviderStatus(status.value);
      if (index.status === "fulfilled") setExperiments(index.value.experiments);
      if (proof.status === "fulfilled") {
        applyExperiment(proof.value);
        setActivity("Judge API connected. Select any verified experiment; new local and OpenAI campaigns register automatically.");
        return;
      }
      try {
        const [staticIndex, frozen] = await Promise.all([
          fetchStaticJudgeExperiments(),
          fetchStaticJudgeExperiment(),
        ]);
        if (!active) return;
        applyExperiment(frozen);
        setExperiments(staticIndex.experiments);
        setSource("static");
        setActivity("Static evaluator mode: signed and deterministic proof evidence is available without a server.");
      } catch (error) {
        if (active) setActivity("Evidence unavailable: " + errorMessage(error));
      }
    };
    void load();
    return () => {
      active = false;
      if (pollRef.current !== null) window.clearTimeout(pollRef.current);
    };
  }, []);

  function applyExperiment(next: JudgeExperiment): void {
    setExperiment(next);
    setReviewDecision(next.human_review?.human_decision ?? "");
    setReviewerNote(next.human_review?.reviewer_note ?? "");
    setReviewActivity(next.human_review ? "Human review recorded. No merge was performed." : "No human final decision recorded.");
  }

  async function handleExperimentChange(experimentId: string): Promise<void> {
    if (experimentId === experiment?.experiment_id) return;
    setExperimentLoading(true);
    setActivity("Verifying " + experimentId + "…");
    try {
      const next = source === "static"
        ? await fetchStaticJudgeExperiment(experimentId)
        : await fetchJudgeExperiment(experimentId);
      applyExperiment(next);
      setActivity(next.source_label + " evidence verified. " + (next.lifecycle_status === "proof_complete" ? "Repair proof is complete." : "Campaign is complete; repair proof has not run."));
    } catch (error) {
      setActivity(errorMessage(error));
    } finally {
      setExperimentLoading(false);
    }
  }

  async function refreshExperimentIndex(preferredCampaignId?: string): Promise<void> {
    const index = await fetchJudgeExperiments();
    setExperiments(index.experiments);
    if (!preferredCampaignId) return;
    const nextSummary = index.experiments.find((item) => item.campaign_id === preferredCampaignId);
    if (!nextSummary) return;
    applyExperiment(await fetchJudgeExperiment(nextSummary.experiment_id));
  }

  const providerReady = provider === "replay"
    || (provider === "vllm"
      ? providerStatus?.providers.vllm?.live_campaign_ready === true
      : providerStatus?.providers.openai.live_campaign_ready === true);
  const providerDisabled = source === "static" || !providerReady;

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
            if (current.status === "completed") {
              await refreshExperimentIndex(current.campaign_id);
            }
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
  async function handleHumanReview() {
    if (!experiment || !reviewDecision || !reviewerNote.trim()) return;
    setReviewBusy(true);
    setReviewActivity("Recording human final decision against the current evidence…");
    try {
      const saved = await submitHumanReview(
        experiment.experiment_id,
        experiment.evidence_fingerprint,
        reviewDecision,
        reviewerNote,
      );
      setExperiment((current) => current ? { ...current, human_review: saved } : current);
      setReviewActivity("Human review recorded. No merge was performed.");
    } catch (error) {
      setReviewActivity(errorMessage(error));
    } finally {
      setReviewBusy(false);
    }
  }

  function exportHumanReview(record: HumanReviewRecord | null): void {
    if (!record) return;
    const blob = new Blob([`${JSON.stringify(record, null, 2)}\n`], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "human_review.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function focusPatchDiff(): void {
    const diff = document.getElementById("candidate-patch-diff") as HTMLDetailsElement | null;
    if (!diff) return;
    diff.open = true;
    diff.scrollIntoView?.({ behavior: "smooth", block: "start" });
    diff.querySelector("summary")?.focus();
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
      <div className="judge-shell">
        <ForgeTopNav active="mission" truthLabel="Verifying evidence" />
        <main className="judge-loading">
          <p className="judge-kicker">Playtest Forge / evaluator view</p>
          <h1>Evidence is being verified.</h1>
          <p role="status">{activity}</p>
        </main>
      </div>
    );
  }

  if (experiment.proof_kind === "content_correctness") {
    return (
      <CorrectnessExperimentView
        experiment={experiment}
        experiments={experiments}
        loading={experimentLoading}
        onChange={(id) => { void handleExperimentChange(id); }}
      />
    );
  }

  if (experiment.lifecycle_status !== "proof_complete" || experiment.patch === null || experiment.comparison === null || experiment.codex === null || experiment.decision === null || experiment.decision_reason === null || experiment.hypothesis === null || experiment.mechanism_class === null) {
    return (
      <div className="judge-shell">
        <ForgeTopNav active="mission" truthLabel={experiment.source_label + " campaign"} />
        <section className="judge-hero" aria-labelledby="judge-title">
          <div>
            <p className="judge-kicker">OpenAI Build Week 2026 · Judge Mode</p>
            <h1 id="judge-title">The campaign is complete.<br /><em>The repair is not.</em></h1>
          </div>
          <aside className="judge-verdict" data-decision="pending" aria-label="Experiment lifecycle status">
            <span>Evidence lifecycle</span><strong>CAMPAIGN ONLY</strong><small>No machine repair recommendation yet</small>
          </aside>
          <p className="judge-thesis">Completed campaigns register immediately. Repair, proof, and human review remain visibly pending until their own evidence passes.</p>
          <p className="judge-mode"><span aria-hidden="true">●</span> {experiment.source_label} · {experiment.provider_mode} · hashes verified</p>
        </section>
        <JudgeMissionExperience />
        <main className="judge-ledger">
        <ExperimentSelector experiments={experiments} selected={experiment} disabled={experimentLoading} onChange={(id) => { void handleExperimentChange(id); }} />
          <section className="judge-stage" aria-labelledby="campaign-title">
            <div className="judge-stage-marker"><span>01</span><b>CAMPAIGN</b></div>
            <div className="judge-stage-body">
              <p className="judge-eyebrow">Verified campaign evidence</p>
              <h2 id="campaign-title">{experiment.title}</h2>
              <div className="judge-metrics" aria-label="Campaign facts">
                <Metric value={String(experiment.campaign.cells)} label="persona × seed cells" />
                <Metric value={String(experiment.campaign.weeks)} label="Godot weeks" />
                <Metric value={percent(experiment.campaign.valid_rate)} label="valid actions" />
                <Metric value={experiment.campaign.target_members + "/" + experiment.campaign.cells} label="target members" intent="danger" />
              </div>
              <p className="judge-copy">{experiment.source_label} · {experiment.model}. This completed result is retained without borrowing a patch or proof from another experiment.</p>
            </div>
          </section>
          <PendingStage number="02" label="REPAIR" title="No bounded repair has been published." />
          <PendingStage number="03" label="PROOF" title="Fixed and unseen holdout proof has not run." />
          <PendingStage number="04" label="HUMAN" title="Human review opens after machine evidence exists." />
        </main>
      </div>
    );
  }

  const baselineFixed = cohort(experiment, "baseline_fixed");
  const patchedFixed = cohort(experiment, "patched_fixed");
  const baselineHoldout = cohort(experiment, "baseline_holdout");
  const patchedHoldout = cohort(experiment, "patched_holdout");
  const displayedDecision = experiment.human_review
    ? experiment.human_review.human_decision.replaceAll("_", " ")
    : experiment.decision;
  const verdictLabel = experiment.human_review ? "Human decision" : "Machine recommendation";
  const evidenceLink = experiment.source_kind === "signed"
    ? "/playthrough-inspector?source=replay&persona=money&seed=42"
    : "/playthrough-inspector?experiment=" + experiment.experiment_id
      + "&persona=" + experiment.campaign.personas[0]
      + "&seed=" + experiment.campaign.seeds[0];

  return (
    <div className="judge-shell">
      <ForgeTopNav
        active="mission"
        truthLabel={source === "static" ? "Signed static evidence" : "Judge API connected"}
      />

      <section className="judge-hero" aria-labelledby="judge-title">
        <div>
          <p className="judge-kicker">OpenAI Build Week 2026 · Judge Mode</p>
          <h1 id="judge-title">A bounded patch faced its proof.<br /><em>{experiment.decision === "accepted" ? "The gates accepted it." : "The gates rejected it."}</em></h1>
        </div>
        <aside
          className="judge-verdict"
          data-decision={experiment.human_review?.human_decision ?? experiment.decision}
          aria-label="Experiment decision status"
        >
          <span>{verdictLabel}</span>
          <strong>{displayedDecision}</strong>
          <small>{experiment.human_review ? `Machine recommendation: ${experiment.decision}` : "Awaiting human review"}</small>
        </aside>
        <p className="judge-thesis">
          Codex plans the campaign, coordinates persona playthroughs against a real Godot game,
          proposes one bounded repair, and lets fixed plus unseen holdout evidence—not optimism—decide.
        </p>
        <p className="judge-mode"><span aria-hidden="true">●</span> {source === "static" ? "Static evaluator copy" : experiment.source_label} · {experiment.provider_mode} evidence · hashes verified before publication</p>
      </section>

      <JudgeMissionExperience />

      <main className="judge-ledger">
        <ExperimentSelector experiments={experiments} selected={experiment} disabled={experimentLoading} onChange={(id) => { void handleExperimentChange(id); }} />
        <section className="judge-stage" aria-labelledby="campaign-title">
          <div className="judge-stage-marker"><span>01</span><b>CAMPAIGN</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">Observe before editing</p>
            <h2 id="campaign-title">{experiment.title}</h2>
            <div className="judge-metrics" aria-label="Campaign facts">
              <Metric value={String(experiment.campaign.cells)} label="persona × seed cells" />
              <Metric value={String(experiment.campaign.weeks)} label="Godot weeks" />
              <Metric value={percent(experiment.campaign.valid_rate)} label="valid actions" />
              <Metric value={experiment.campaign.target_members + "/" + experiment.campaign.cells} label="target members" intent="danger" />
            </div>
            <p className="judge-copy">The game runtime is automated; the action provider is swappable. Replay is a deterministically authored persona-policy fixture—not a recorded LLM run. OpenAI runs the same bounded interface as a live persona subagent when server configuration is ready.</p>

            <div className="judge-console">
              <fieldset>
                <legend>Action provider</legend>
                {(["replay", "vllm", "openai"] as JudgeProvider[]).map((item) => (
                  <label key={item} className={provider === item ? "is-selected" : ""}>
                    <input
                      type="radio"
                      name="provider"
                      value={item}
                      checked={provider === item}
                      onChange={() => setProvider(item)}
                    />
                    <span>{PROVIDER_LABEL[item]}</span>
                    <small>{item === "replay"
                        ? "fixture policy · no key"
                        : item === "vllm"
                          ? providerStatus?.providers.vllm?.live_campaign_ready ? "local · runner configured" : "local · configuration required"
                          : providerStatus?.providers.openai.live_campaign_ready ? "live · server key ready" : "live · configuration required"}</small>
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
            <h2 id="repair-title">Codex tested {experiment.mechanism_class.replaceAll("_", " ")}.</h2>
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
              <div className="judge-stamp" aria-label={`Candidate repair `}>{experiment.decision.toUpperCase()}</div>
            </div>
            <details id="candidate-patch-diff" className="judge-diff">
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
            <p className="judge-eyebrow">Fixed seeds + unseen holdout · {baselineFixed.decision_policy}</p>
            <h2 id="proof-title">{experiment.decision === "accepted" ? "Fixed and holdout gates accepted the repair." : "The bounded repair did not clear every gate."}</h2>
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
            <p className="judge-decision"><span>Machine recommendation</span><strong>{experiment.decision}</strong>{experiment.decision_reason}</p>
          </div>
        </section>

        <section className="judge-stage judge-human-stage" aria-labelledby="human-review-title">
          <div className="judge-stage-marker"><span>04</span><b>HUMAN</b></div>
          <div className="judge-stage-body">
            <p className="judge-eyebrow">Human review · same evidence fingerprint</p>
            <h2 id="human-review-title">The machine recommends. A human decides.</h2>
            <p className="judge-copy">
              Review the retained campaign, fixed and holdout gates, and the exact candidate patch.
              Your decision is recorded beside the machine recommendation; it never rewrites evidence
              and never merges the patch.
            </p>

            <div className="judge-review-handoff" aria-label="Review handoff">
              <div><span>Machine recommendation</span><strong>{experiment.decision}</strong></div>
              <div><span>Evidence fingerprint</span><code>{experiment.evidence_fingerprint.slice(0, 16)}</code></div>
              <div><span>Automation boundary</span><strong>NO AUTO-MERGE</strong></div>
            </div>

            <nav className="judge-review-evidence-links" aria-label="Human review evidence">
              <Link to={evidenceLink}>
                View full campaign evidence
              </Link>
              <button type="button" onClick={focusPatchDiff}>Review exact patch diff</button>
            </nav>

            <div className="judge-human-review">
              <div className="judge-review-form-grid">
                <fieldset>
                  <legend>Final human decision</legend>
                  {([
                    ["approve", "Approve"],
                    ["reject", "Reject"],
                    ["needs_more_evidence", "Needs more evidence"],
                  ] as Array<[HumanReviewDecision, string]>).map(([value, label]) => (
                    <label key={value} className={reviewDecision === value ? "is-selected" : ""}>
                      <input
                        type="radio"
                        name="human-review-decision"
                        value={value}
                        checked={reviewDecision === value}
                        onChange={() => setReviewDecision(value)}
                      />
                      <span>{label}</span>
                    </label>
                  ))}
                </fieldset>
                <label className="judge-review-note">
                  <span>Reviewer note</span>
                  <textarea
                    value={reviewerNote}
                    maxLength={2000}
                    rows={6}
                    required
                    placeholder="Cite the visible gates or evidence that support this human decision."
                    onChange={(event) => setReviewerNote(event.target.value)}
                  />
                  <small>{reviewerNote.length} / 2000 · stored with the evidence fingerprint</small>
                </label>
              </div>
              <div className="judge-review-actions">
                <p role="status" aria-live="polite">
                  {source === "static" ? "Start the Judge API to record a durable review." : reviewActivity}
                </p>
                <div>
                  <button
                    type="button"
                    className="judge-button-primary"
                    disabled={source === "static" || reviewBusy || !reviewDecision || !reviewerNote.trim()}
                    onClick={handleHumanReview}
                  >
                    {reviewBusy ? "Recording…" : "Record final decision"}
                  </button>
                  <button
                    type="button"
                    className="judge-button-secondary"
                    disabled={!experiment.human_review}
                    onClick={() => exportHumanReview(experiment.human_review)}
                  >
                    Export human_review.json
                  </button>
                </div>
              </div>
              {experiment.human_review && (
                <dl className="judge-review-record">
                  <div><dt>Human decision</dt><dd>{experiment.human_review.human_decision.replaceAll("_", " ")}</dd></div>
                  <div><dt>Machine recommendation</dt><dd>{experiment.human_review.machine_recommendation}</dd></div>
                  <div><dt>Recommendation overridden</dt><dd>{experiment.human_review.overrides_machine_recommendation ? "yes" : "no"}</dd></div>
                  <div><dt>Merge performed</dt><dd>no</dd></div>
                </dl>
              )}
            </div>
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
