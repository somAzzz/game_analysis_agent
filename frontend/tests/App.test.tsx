import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "@/App";
import type {
  DecisionGraphManifest,
  FrontManifest,
  IssueManifest,
  JudgeExperiment,
  JudgeExperimentIndex,
  JudgeProviderStatus,
} from "@/types";

const apiMocks = vi.hoisted(() => ({
  fetchFrontManifest: vi.fn(),
  fetchIssueManifest: vi.fn(),
  fetchDecisionGraphManifest: vi.fn(),
  fetchJudgeProviderStatus: vi.fn(),
  fetchJudgeExperiments: vi.fn(),
  fetchJudgeExperiment: vi.fn(),
  fetchStaticJudgeExperiments: vi.fn(),
  fetchStaticJudgeExperiment: vi.fn(),
  testJudgeProvider: vi.fn(),
  createJudgeCampaign: vi.fn(),
  fetchJudgeCampaign: vi.fn(),
  submitHumanReview: vi.fn(),
}));

vi.mock("@/lib/api", () => apiMocks);

vi.mock("@xyflow/react", () => ({
  Background: () => <div data-testid="flow-background" />,
  Controls: () => <div data-testid="flow-controls" />,
  Handle: () => null,
  MarkerType: { ArrowClosed: "arrow-closed" },
  MiniMap: () => <div data-testid="flow-minimap" />,
  Position: { Bottom: "bottom", Top: "top" },
  ReactFlow: ({ children }: { children?: ReactNode }) => (
    <div data-testid="react-flow">{children}</div>
  ),
  ReactFlowProvider: ({ children }: { children?: ReactNode }) => (
    <>{children}</>
  ),
}));

const frontManifest: FrontManifest = {
  generated_at: "2026-07-12T10:00:00Z",
  counts: {
    issues: 2,
    decision_graphs: 1,
    total_runs: 15,
    total_anomalies: 6,
    total_critical: 1,
  },
  issues: [
    {
      kind: "balance",
      id: "critical-balance",
      slug: "balance/critical-balance",
      title: "Critical Balance",
      subtitle: "High-risk balance report",
      total_runs: 10,
      top_ending: {
        policy: "work",
        ending_id: "dropout",
        count: 6,
        rate: 0.6,
      },
      anomaly_total: 5,
      severity: "critical",
      has_decision_graph: true,
      policy: "work",
      scenario: "first semester",
      difficulty: "realistic",
    },
    {
      kind: "play",
      id: "play-report",
      slug: "play/play-report",
      title: "Calm Route",
      subtitle: "Balanced player walkthrough",
      total_runs: 5,
      top_ending: null,
      anomaly_total: 1,
      severity: "info",
      has_decision_graph: false,
      policy: "balanced",
      scenario: "first semester",
      difficulty: "normal",
    },
  ],
  issues_index: [
    {
      kind: "balance",
      id: "critical-balance",
      path: "browse/balance/critical-balance/manifest.json",
    },
    {
      kind: "play",
      id: "play-report",
      path: "browse/play/play-report/manifest.json",
    },
  ],
};

const issueManifest: IssueManifest = {
  kind: "play",
  id: "play-report",
  slug: "play/play-report",
  report_dir: "reports/play/play-report",
  summary: { scenario: "first semester", policy: "balanced" },
  endings: [],
  actions: [],
  events: [],
  choices: [],
  weekly_series: {},
  anomalies: [],
  value_findings: [],
  route_findings: {
    groups: [],
    crisis_response: [],
    ending_contradictions: [],
    route_separation: [],
  },
  agents: [],
  agent_markdown: {},
  gate_report: null,
  coverage_report: null,
  raw_runs_count: 5,
};

const graphManifest: DecisionGraphManifest = {
  issue_id: "graph one",
  run_id: 2,
  policy: "balanced",
  scenario: "first semester",
  seed: 42,
  max_weeks: 2,
  final_ending_id: "graduated",
  run: {
    run_id: 2,
    policy: "balanced",
    weekly_log: [
      {
        week: 0,
        triggered_event_id: "arrival",
        choice_index: 0,
        selected_action_ids: ["study"],
        after_state: { stress: 10 },
      },
    ],
  },
  event_graph: {
    events: [
      {
        id: "arrival",
        title: "Arrival week",
        event_type: "fixed",
        trigger: { week: 0 },
        choices: [{ text: "Get started", success_effects: { stress: -1 } }],
      },
    ],
  },
};

const providerStatus: JudgeProviderStatus = {
  schema_version: "judge-provider-status-v1",
  providers: {
    replay: { status: "available", mode: "prerecorded", requires_api_key: false, requires_game_runtime: false },
    vllm: {
      status: "available", mode: "local", model: "local-test-model", requires_api_key: false,
      endpoint_configured: true, game_runtime_configured: true, live_campaign_ready: true,
    },
    openai: {
      status: "unavailable", mode: "live", model: "gpt-5.6-luna", requires_api_key: true,
      api_key_configured: false, game_runtime_configured: false, live_campaign_ready: false,
    },
  },
};

const experiment: JudgeExperiment = {
  schema_version: "judge-public-experiment-v2",
  experiment_id: "cashflow-drift-repair-v1",
  title: "Signed cashflow drift repair",
  source_kind: "signed",
  source_label: "SIGNED REPLAY",
  provider: "replay",
  provider_mode: "prerecorded",
  model: "fixture-authoring-policy-v1",
  lifecycle_status: "proof_complete",
  campaign_id: "signed-replay-campaign",
  campaign: {
    gate_status: "passed",
    personas: ["newbie", "study", "money", "social", "visa", "slacker"],
    seeds: [42, 43, 44],
    max_weeks: 20, cells: 18, weeks: 342, target_members: 18, target_personas: 6,
    valid_rate: 1, fallback_rate: 0, provider_error_rate: 0, mean_final_money: 0, mean_max_stress: 100,
    request_fingerprint: "e".repeat(64), source_fingerprint: "f".repeat(64),
  },
  campaign_bundle_path: "examples/build_week_2026/vllm-25seed-audit/public",
  repair_bundle_path: "examples/build_week_2026/repair-proof/public",
  completed_at: "2026-07-16T12:00:00Z",
  evidence_fingerprint: "d".repeat(64),
  human_review: null,
  status: "passed",
  decision: "rejected",
  decision_reason: "Repair rejected because required proof failed: fixed_target, holdout_target",
  hypothesis: "Recurring survival-economy drift depletes spendable cash faster than persona strategies recover.",
  mechanism_class: "recurring_living_cost_drift",
  comparison: { fixed_member_delta: 0, fixed_relative_reduction: 0, holdout_member_delta: 0, holdout_relative_reduction: 0 },
  cohorts: [
    ["baseline_fixed", 0], ["patched_fixed", 18], ["baseline_holdout", 0], ["patched_holdout", 61],
  ].map(([name, money]) => ({
    cohort: name as "baseline_fixed", game_commit: "a".repeat(40), seeds: [42, 43, 44], cells: 18,
    decision_policy: "fixture-authoring-policy-v1",
    weeks: 342, target_members: 18, target_personas: 6, mean_final_money: money as number,
    mean_max_stress: 100, valid_rate: 1, fallback_rate: 0, provider_error_rate: 0,
    persona_alignment_rate: .5, ending_counts: { cashflow_collapse: 18 },
  })),
  gates: [
    { gate_id: "fixed_target", status: "failed", detail: "18 <= 12", evidence_paths: [] },
    { gate_id: "decision_validity", status: "passed", detail: "validity threshold met", evidence_paths: [] },
  ],
  patch: {
    baseline_commit: "a".repeat(40), patched_commit: "b".repeat(40), mechanism_class: "recurring_living_cost_drift",
    modified_paths: ["scripts/simulation/SimulationEngine.gd"], changed_files: 1, added_lines: 35, deleted_lines: 5,
    patch_path: "patch.diff", patch_sha256: "c".repeat(64),
    canonical_source_path: "demo/study-in-germany", disposition: "candidate_not_merged",
    diff: "--- a/scripts/simulation/SimulationEngine.gd\n+++ b/scripts/simulation/SimulationEngine.gd\n+const WEEKLY_ALLOWANCE := 248\n",
  },
  codex: {
    task_reference: "task", feedback_session_id: "session", model: "codex-runtime", skill: "playtest-forge",
    hypothesis_owned_by_codex: true, patch_owned_by_codex: true, decision_owned_by_codex: true,
  },
  mode: "prerecorded",
};

const acceptedExperiment: JudgeExperiment = {
  ...experiment,
  schema_version: "judge-public-experiment-v3",
  proof_kind: "content_correctness",
  experiment_id: "localization-choice-identity-v1",
  title: "Accepted · bilingual choice identity repair",
  source_label: "DETERMINISTIC GODOT",
  provider_mode: "offline-real-godot",
  model: "no-llm-deterministic-automation",
  campaign_id: "localization-choice-identity-v1",
  campaign: { ...experiment.campaign, personas: ["balanced"], seeds: [42, 43, 44, 1042, 1043, 1044], cells: 6, weeks: 120, target_members: 2, target_personas: 0 },
  decision: "accepted",
  decision_reason: "Both identity errors were removed while fixed and holdout semantics remained identical.",
  hypothesis: "Localized choices were matched by array position instead of stable Chinese source identity.",
  mechanism_class: "localized_choice_source_identity",
  comparison: null,
  cohorts: [],
  gates: [
    { gate_id: "choice_identity", status: "passed", detail: "focused economy identity errors: 2 → 0", evidence_paths: [] },
    { gate_id: "holdout_semantic_preservation", status: "passed", detail: "holdout trajectories remained identical", evidence_paths: [] },
  ],
  patch: { ...experiment.patch!, disposition: "integrated_uncommitted" },
  correctness_proof: {
    baseline_identity_errors: 2,
    patched_identity_errors: 0,
    fixed_seeds: [42, 43, 44],
    holdout_seeds: [1042, 1043, 1044],
    fixed_semantic_trajectory_equal: true,
    holdout_semantic_trajectory_equal: true,
    fixed_final_states_equal: true,
    holdout_final_states_equal: true,
    fixed_endings_equal: true,
    holdout_endings_equal: true,
    focused_economy: "passed",
    required_validators: ["content", "json-content", "economy", "risk", "route"],
    expected_demo_failure_count: 3,
    inspect: "passed",
    replay: "passed",
    pytest_passed: 492,
    pytest_skipped: 3,
    ruff: "passed",
    provider_calls: 0,
    artifacts: [],
  },
};

const experimentIndex: JudgeExperimentIndex = {
  schema_version: "judge-experiment-index-v1",
  experiments: [{
    schema_version: "judge-experiment-summary-v1",
    experiment_id: experiment.experiment_id, title: experiment.title,
    source_kind: experiment.source_kind, source_label: experiment.source_label,
    provider: experiment.provider, provider_mode: experiment.provider_mode, model: experiment.model,
    lifecycle_status: experiment.lifecycle_status, campaign_id: experiment.campaign_id, campaign: experiment.campaign,
    campaign_bundle_path: experiment.campaign_bundle_path, repair_bundle_path: experiment.repair_bundle_path,
    completed_at: experiment.completed_at,
  }],
};

const campaignOnlyExperiment: JudgeExperiment = {
  ...experiment,
  experiment_id: "local-campaign-test", title: "Local campaign test",
  source_kind: "local_vllm", source_label: "LOCAL vLLM", provider: "vllm", provider_mode: "local",
  model: "qwen3.6-27b-nvfp4", lifecycle_status: "campaign_complete", campaign_id: "local-campaign-test",
  campaign: { ...experiment.campaign, cells: 48, weeks: 912, target_members: 41 },
  campaign_bundle_path: "reports/persona-campaigns/local-campaign-test/public", repair_bundle_path: null,
  evidence_fingerprint: "1".repeat(64), decision: null, decision_reason: null, hypothesis: null, mechanism_class: null,
  comparison: null, cohorts: [], gates: [], patch: null, codex: null, mode: "local",
};
experimentIndex.experiments.push({
  schema_version: "judge-experiment-summary-v1", experiment_id: campaignOnlyExperiment.experiment_id,
  title: campaignOnlyExperiment.title, source_kind: campaignOnlyExperiment.source_kind, source_label: campaignOnlyExperiment.source_label,
  provider: campaignOnlyExperiment.provider, provider_mode: campaignOnlyExperiment.provider_mode, model: campaignOnlyExperiment.model,
  lifecycle_status: campaignOnlyExperiment.lifecycle_status, campaign_id: campaignOnlyExperiment.campaign_id, campaign: campaignOnlyExperiment.campaign,
  campaign_bundle_path: campaignOnlyExperiment.campaign_bundle_path, repair_bundle_path: null, completed_at: null,
});

function renderRoute(path: string) {
  return render(
    <MemoryRouter
      initialEntries={[path]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <App />
    </MemoryRouter>,
  );
}

describe("application routes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not found", { status: 404 })),
    );
    apiMocks.fetchFrontManifest.mockResolvedValue(frontManifest);
    apiMocks.fetchIssueManifest.mockResolvedValue(issueManifest);
    apiMocks.fetchDecisionGraphManifest.mockResolvedValue(graphManifest);
    apiMocks.fetchJudgeProviderStatus.mockResolvedValue(providerStatus);
    apiMocks.fetchJudgeExperiments.mockResolvedValue(experimentIndex);
    apiMocks.fetchJudgeExperiment.mockResolvedValue(experiment);
    apiMocks.fetchStaticJudgeExperiments.mockResolvedValue(experimentIndex);
    apiMocks.fetchStaticJudgeExperiment.mockResolvedValue(experiment);
  });

  it("tells the complete Campaign Repair Proof story on the evaluator route", async () => {
    const user = userEvent.setup();
    renderRoute("/");

    expect(await screen.findByRole("heading", { name: /A bounded patch faced its proof/i })).toBeInTheDocument();
    const missionNav = screen.getByRole("navigation", { name: "Competition pages" });
    expect(missionNav.closest("header")).toHaveClass("competition-top-nav");
    expect(within(missionNav).getByRole("link", { name: "Judge Mission" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText(/prerecorded evidence/i)).toBeInTheDocument();
    expect(screen.getByText("CAMPAIGN")).toBeInTheDocument();
    expect(screen.getByText("REPAIR")).toBeInTheDocument();
    expect(screen.getByText("PROOF")).toBeInTheDocument();
    expect(screen.getAllByText("REJECTED").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Machine recommendation").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("Awaiting human review")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The machine recommends. A human decides." })).toBeInTheDocument();
    expect(screen.getAllByText("18/18").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText(/OpenAI live subagent/i)).toBeInTheDocument();
    expect(screen.getByText(/View exact candidate diff/i)).toBeInTheDocument();
    expect(screen.getByText(/demo\/study-in-germany/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Exact candidate source diff/i)).toHaveTextContent("WEEKLY_ALLOWANCE");
    const patchDetails = screen.getByLabelText(/Exact candidate source diff/i).closest("details");
    expect(patchDetails).not.toHaveAttribute("open");
    await user.click(screen.getByRole("button", { name: "Review exact patch diff" }));
    expect(patchDetails).toHaveAttribute("open");
  });

  it("shows the accepted bilingual choice repair as a dedicated correctness proof", async () => {
    apiMocks.fetchJudgeExperiment.mockResolvedValue(acceptedExperiment);
    apiMocks.fetchJudgeExperiments.mockResolvedValue({
      schema_version: "judge-experiment-index-v1",
      experiments: [{
        schema_version: "judge-experiment-summary-v1",
        experiment_id: acceptedExperiment.experiment_id,
        title: acceptedExperiment.title,
        source_kind: acceptedExperiment.source_kind,
        source_label: acceptedExperiment.source_label,
        provider: acceptedExperiment.provider,
        provider_mode: acceptedExperiment.provider_mode,
        model: acceptedExperiment.model,
        lifecycle_status: acceptedExperiment.lifecycle_status,
        campaign_id: acceptedExperiment.campaign_id,
        campaign: acceptedExperiment.campaign,
        campaign_bundle_path: acceptedExperiment.campaign_bundle_path,
        repair_bundle_path: acceptedExperiment.repair_bundle_path,
        completed_at: acceptedExperiment.completed_at,
      }],
    });
    renderRoute("/");

    expect(await screen.findByRole("heading", { name: /A content identity defect faced its proof/i })).toBeInTheDocument();
    expect(screen.getAllByText("ACCEPTED").length).toBeGreaterThan(0);
    expect(screen.getByText("2", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getAllByText("0", { selector: "strong" }).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("heading", { name: /The defect disappeared without changing game outcomes/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review accepted patch diff" })).toHaveAttribute(
      "href",
      "#candidate-patch-diff",
    );
  });

  it("switches to a discovered local campaign without fabricating repair proof", async () => {
    const user = userEvent.setup();
    apiMocks.fetchJudgeExperiment.mockImplementation((experimentId?: string) =>
      Promise.resolve(experimentId === campaignOnlyExperiment.experiment_id ? campaignOnlyExperiment : experiment),
    );
    renderRoute("/");

    const selector = await screen.findByRole("combobox", { name: /Evidence set/ });
    expect(within(selector).getByRole("option", { name: /SIGNED REPLAY.*FULL PROOF/i })).toBeInTheDocument();
    expect(within(selector).getByRole("option", { name: /LOCAL vLLM.*CAMPAIGN ONLY/i })).toBeInTheDocument();
    await user.selectOptions(selector, campaignOnlyExperiment.experiment_id);

    expect(await screen.findByRole("heading", { name: "Local campaign test" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "No bounded repair has been published." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Fixed and unseen holdout proof has not run." })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record final decision" })).not.toBeInTheDocument();
  });

  it("switches frozen static evidence when the Judge API is unavailable", async () => {
    const user = userEvent.setup();
    apiMocks.fetchJudgeExperiments.mockRejectedValue(new Error("offline"));
    apiMocks.fetchJudgeExperiment.mockRejectedValue(new Error("offline"));
    apiMocks.fetchStaticJudgeExperiment.mockImplementation((experimentId?: string) =>
      Promise.resolve(experimentId === campaignOnlyExperiment.experiment_id ? campaignOnlyExperiment : experiment),
    );
    renderRoute("/");

    const selector = await screen.findByRole("combobox", { name: /Evidence set/ });
    expect(selector).toBeEnabled();
    await user.selectOptions(selector, campaignOnlyExperiment.experiment_id);

    expect(await screen.findByRole("heading", { name: "Local campaign test" })).toBeInTheDocument();
    expect(apiMocks.fetchStaticJudgeExperiment).toHaveBeenCalledWith(campaignOnlyExperiment.experiment_id);
    expect(screen.queryByRole("button", { name: "Record final decision" })).not.toBeInTheDocument();
  });

  it("runs the bounded Replay action from Judge Mode", async () => {
    const user = userEvent.setup();
    const created = {
      campaign_id: "judge-demo123", status: "completed", mode: "prerecorded",
      request: { provider: "replay", personas: ["newbie"], seeds: [42], max_weeks: 3 },
      created_at: "2026-07-16T10:00:00Z", updated_at: "2026-07-16T10:00:01Z",
      result: { completed_cells: 18, total_weeks: 342, valid_rate: 1 }, error: null,
    };
    apiMocks.createJudgeCampaign.mockResolvedValue(created);
    apiMocks.fetchJudgeCampaign.mockResolvedValue(created);
    renderRoute("/");

    await user.click(await screen.findByRole("button", { name: /Run bounded campaign/i }));
    expect(apiMocks.createJudgeCampaign).toHaveBeenCalledWith("replay");
    expect(await screen.findByText(/campaign completed with evidence attached/i)).toBeInTheDocument();
    expect(screen.getByText(/judge-demo123/i)).toBeInTheDocument();
  });

  it("records and exports a human decision on the same experiment", async () => {
    const user = userEvent.setup();
    const review = {
      schema_version: "judge-human-review-v1" as const,
      experiment_id: experiment.experiment_id,
      evidence_fingerprint: experiment.evidence_fingerprint,
      machine_recommendation: "rejected" as const,
      human_decision: "needs_more_evidence" as const,
      reviewer_note: "Need a pressure-sensitive unseen cohort.",
      overrides_machine_recommendation: true,
      reviewed_at: "2026-07-17T20:00:00Z",
      merge_performed: false as const,
    };
    apiMocks.submitHumanReview.mockResolvedValue(review);
    const createObjectURL = vi.fn(() => "blob:human-review");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderRoute("/");

    await user.click(await screen.findByRole("radio", { name: "Needs more evidence" }));
    await user.type(screen.getByLabelText(/Reviewer note/), review.reviewer_note);
    await user.click(screen.getByRole("button", { name: "Record final decision" }));

    await waitFor(() => expect(apiMocks.submitHumanReview).toHaveBeenCalledWith(
      experiment.experiment_id,
      experiment.evidence_fingerprint,
      "needs_more_evidence",
      review.reviewer_note,
    ));
    expect(await screen.findByText(/No merge was performed/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Export human_review.json" }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:human-review");
    click.mockRestore();
  });

  it("opens the actual Money strategy record and restores focus on Escape", async () => {
    const user = userEvent.setup();
    renderRoute("/");

    const money = await screen.findByRole("button", { name: "Inspect Money strategy" });
    await user.click(money);

    expect(screen.getByRole("dialog", { name: "Money" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Close Persona details" })).toHaveFocus());
    expect(screen.getByText("career tag")).toBeInTheDocument();
    expect(screen.getByText(/money-seed-42/i)).toBeInTheDocument();
    const replayLink = screen.getByRole("link", { name: /Inspect Money seed 42 replay/i });
    expect(replayLink).toHaveAttribute("href", "/playthrough-inspector?source=replay&persona=money&seed=42");
    await user.tab();
    expect(replayLink).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Close Persona details" })).toHaveFocus();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Money" })).not.toBeInTheDocument());
    expect(money).toHaveFocus();
  });

  it("keeps route nodes, week records, and evidence console synchronized", async () => {
    const user = userEvent.setup();
    renderRoute("/playthrough-inspector");

    expect(screen.getByRole("heading", { name: /Money runs the evidence/i })).toBeInTheDocument();
    const playthroughNav = screen.getByRole("navigation", { name: "Competition pages" });
    expect(playthroughNav.closest("header")).toHaveClass("competition-top-nav");
    expect(within(playthroughNav).getByRole("link", { name: "Playthrough Inspector" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Go to recorded week 1" })).toHaveAttribute("aria-current", "step");
    expect(screen.getByLabelText("Money current state at recorded week 1")).toHaveAttribute("data-runner-frame", "1");
    expect(screen.getByRole("heading", { name: "Arrival in Germany" })).toBeInTheDocument();
    expect(screen.getByText("Go to the dorm to drop off luggage")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "中文" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "EN" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Continuing Language Studies in Germany" })).toBeInTheDocument();
    expect(screen.getByLabelText("Money current state at recorded week 2")).toHaveAttribute("data-runner-frame", "2");

    await user.click(screen.getByRole("button", { name: "Previous" }));
    expect(screen.getByLabelText("Money current state at recorded week 1")).toHaveAttribute("data-runner-frame", "1");

    await user.click(screen.getByRole("button", { name: "W3 Attractor" }));
    expect(screen.getByRole("heading", { name: "Unregistered, Can't Attend Class" })).toBeInTheDocument();
    expect(screen.getByLabelText("Money current state at recorded week 3")).toHaveAttribute("data-runner-frame", "1");
    expect(screen.getByText("Stress 49 → 82")).toBeInTheDocument();
    expect(screen.getByText("Arrears €373 → €628")).toBeInTheDocument();
    expect(within(screen.getByRole("article")).getByText("€628")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go to recorded week 3" })).toHaveAttribute("aria-current", "step");

    await user.click(screen.getByRole("button", { name: /W19 Post-Exam Void/i }));
    expect(screen.getByRole("heading", { name: "Post-Exam Void" })).toBeInTheDocument();
    expect(screen.getAllByText("cashflow_collapse").length).toBeGreaterThan(0);
    expect(within(screen.getByRole("article")).getByText("€3,862")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go to recorded week 19" })).toHaveAttribute("aria-current", "step");
  });

  it("shows sanitized weekly progress from a Codex playtest session", async () => {
    const session = {
      schema_version: "persona-campaign-session-v1",
      campaign_id: "vllm-newbie-seed-42-20w",
      status: "running",
      truth_label: "local-vllm-real-godot",
      provider: "vllm",
      model: "qwen-local",
      request: { personas: ["newbie"], seeds: [42], max_weeks: 20, provider: "vllm" },
      progress: {
        completed_cells: 0,
        running_cells: 1,
        failed_cells: 0,
        completed_weeks: 7,
        total_cells: 1,
        total_requested_weeks: 20,
      },
      cells: [{
        cell_id: "newbie-seed-42",
        persona: "newbie",
        seed: 42,
        status: "running",
        phase: "completed",
        current_week: 7,
        completed_weeks: 7,
        max_weeks: 20,
      }],
      diagnostics: {
        logical_calls: 14,
        http_attempts: 15,
        fallback_count: 1,
        failure_count: 1,
        response_metadata_missing_attempts: 1,
        known_usage: { input_tokens: 12000, output_tokens: 2300, total_tokens: 14300 },
        failures: [{
          cell_id: "newbie-seed-42",
          persona: "newbie",
          seed: 42,
          week: 6,
          phase: "decision",
          category: "malformed_response",
          message: "actions.0: Input should be a valid string",
          attempts: 2,
        }],
      },
      latest: {
        cell_id: "newbie-seed-42",
        persona: "newbie",
        seed: 42,
        phase: "completed",
        week: 7,
        completed_weeks: 7,
        max_weeks: 20,
        selected_action_ids: ["study_library"],
        triggered_event_id: "student_job_offer",
        selected_choice_id: "student_job_offer.choice_01",
        state_after: { week: 8, money: 410 },
      },
      message: "newbie seed 42: week 7/20 completed",
    };
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("live-playthrough/session.json")) {
        return Promise.resolve(new Response(JSON.stringify(session), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }));
      }
      return Promise.resolve(new Response("not found", { status: 404 }));
    }));

    renderRoute("/playthrough-inspector");

    const card = await screen.findByRole("region", { name: "Codex playtest session" });
    expect(within(card).getByText("vllm-newbie-seed-42-20w")).toBeInTheDocument();
    expect(within(card).getByText("RUNNING")).toBeInTheDocument();
    expect(within(card).getByText("Newbie · seed 42 · W7/20")).toBeInTheDocument();
    expect(within(card).getByText("7/20")).toBeInTheDocument();
    expect(within(card).getByText("local-vllm-real-godot")).toBeInTheDocument();
    const diagnostics = within(card).getByRole("complementary", { name: "Partial campaign diagnostics" });
    expect(within(diagnostics).getByText("NOT EVIDENCE")).toBeInTheDocument();
    expect(within(diagnostics).getByText("W6 · decision · malformed_response")).toBeInTheDocument();
    expect(within(diagnostics).getByText("14,300")).toBeInTheDocument();
  });

  it("switches verified Persona paths and exposes a current-state-only runner tooltip", async () => {
    const user = userEvent.setup();
    renderRoute("/playthrough-inspector?persona=visa");

    expect(screen.getByRole("heading", { name: /Visa runs the evidence/i })).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Competition pages" })).getByRole("link", { name: "Mission Archive" })).toHaveAttribute("href", "/reports");
    expect(screen.getByRole("button", { name: "Use Visa strategy playthrough" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Visa current state at recorded week 1")).toBeInTheDocument();
    const tooltip = screen.getByRole("tooltip");
    expect(within(tooltip).getByText("€172")).toBeInTheDocument();
    expect(tooltip).not.toHaveTextContent("→");

    await user.click(screen.getByRole("button", { name: "W3 Attractor" }));
    expect(screen.getByText("Arrears €343 → €598")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Use Social strategy playthrough" }));
    expect(screen.getByRole("heading", { name: /Social runs the evidence/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Social current state at recorded week 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go to recorded week 1" })).toHaveAttribute("aria-current", "step");
  });

  it("renders the report index and filters cards with search and severity controls", async () => {
    const user = userEvent.setup();
    renderRoute("/reports");

    expect(
      await screen.findByRole("heading", { name: /Mission Archive/i }),
    ).toBeInTheDocument();
    const archiveNav = screen.getByRole("navigation", { name: "Competition pages" });
    expect(archiveNav.closest("header")).toHaveClass("competition-top-nav");
    expect(within(archiveNav).getByRole("link", { name: "Mission Archive" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("heading", { name: "Critical Balance" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Calm Route" })).toBeInTheDocument();

    await user.type(
      screen.getByPlaceholderText("policy, scenario, outcome, severity..."),
      "calm",
    );
    expect(screen.queryByRole("heading", { name: "Critical Balance" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Calm Route" })).toBeInTheDocument();

    await user.clear(
      screen.getByPlaceholderText("policy, scenario, outcome, severity..."),
    );
    await user.click(screen.getByRole("button", { name: "Info (1)" }));
    expect(screen.queryByRole("heading", { name: "Critical Balance" })).not.toBeInTheDocument();
    expect(screen.getByText("1 visible report")).toBeInTheDocument();

    await user.type(
      screen.getByPlaceholderText("policy, scenario, outcome, severity..."),
      "no-such-report",
    );
    expect(screen.getByRole("heading", { name: "No test cells match." })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Clear filters/i }));
    expect(screen.getByRole("heading", { name: "Critical Balance" })).toBeInTheDocument();
  });

  it("navigates from a report card to the issue page", async () => {
    const user = userEvent.setup();
    renderRoute("/reports");

    await user.click(
      await screen.findByRole("link", { name: /Calm Route/i }),
    );

    expect(
      await screen.findByRole("heading", { level: 1, name: "play report" }),
    ).toBeInTheDocument();
    expect(apiMocks.fetchIssueManifest).toHaveBeenCalledWith(
      "play",
      "play-report",
    );
    expect(screen.getByText(/play issue · first semester \/ balanced/i)).toBeInTheDocument();
  });

  it("renders an encoded decision-graph route", async () => {
    renderRoute("/decision-graph/graph%20one/2");

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: /Decision Graph/i,
      }),
    ).toBeInTheDocument();
    expect(apiMocks.fetchDecisionGraphManifest).toHaveBeenCalledWith(
      "graph one",
      2,
    );
    expect(screen.getByText("graduated")).toBeInTheDocument();
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Previous/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Next/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Go to week 0/i })).toHaveAttribute("aria-current", "step");
  });

  it("renders the 404 page and returns to the report index", async () => {
    const user = userEvent.setup();
    renderRoute("/not-a-real-route");

    expect(
      screen.getByRole("heading", { level: 1, name: /This route left the playable area/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /Open Judge Mission/i }));
    expect(await screen.findByRole("heading", { name: /A bounded patch faced its proof/i })).toBeInTheDocument();
  });

  it("shows a useful front-page loading failure", async () => {
    apiMocks.fetchFrontManifest.mockRejectedValue(
      new Error("manifest service unavailable"),
    );
    renderRoute("/reports");

    expect(
      await screen.findByRole("heading", { name: "The evidence index is offline." }),
    ).toBeInTheDocument();
    expect(screen.getByText("manifest service unavailable")).toBeInTheDocument();
  });
});
