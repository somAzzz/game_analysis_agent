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
  JudgeProviderStatus,
} from "@/types";

const apiMocks = vi.hoisted(() => ({
  fetchFrontManifest: vi.fn(),
  fetchIssueManifest: vi.fn(),
  fetchDecisionGraphManifest: vi.fn(),
  fetchJudgeProviderStatus: vi.fn(),
  fetchJudgeExperiment: vi.fn(),
  fetchStaticJudgeExperiment: vi.fn(),
  testJudgeProvider: vi.fn(),
  createJudgeCampaign: vi.fn(),
  fetchJudgeCampaign: vi.fn(),
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
    openai: {
      status: "unavailable", mode: "live", model: "gpt-5.6-luna", requires_api_key: true,
      api_key_configured: false, game_runtime_configured: false, live_campaign_ready: false,
    },
  },
};

const experiment: JudgeExperiment = {
  schema_version: "judge-public-experiment-v1",
  experiment_id: "cashflow-drift-repair-v1",
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
    apiMocks.fetchJudgeExperiment.mockResolvedValue(experiment);
    apiMocks.fetchStaticJudgeExperiment.mockResolvedValue(experiment);
  });

  it("tells the complete Campaign Repair Proof story on the evaluator route", async () => {
    renderRoute("/");

    expect(await screen.findByRole("heading", { name: /A patch passed its unit test/i })).toBeInTheDocument();
    const missionNav = screen.getByRole("navigation", { name: "Competition pages" });
    expect(missionNav.closest("header")).toHaveClass("competition-top-nav");
    expect(within(missionNav).getByRole("link", { name: "Judge Mission" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText(/prerecorded evidence/i)).toBeInTheDocument();
    expect(screen.getByText("CAMPAIGN")).toBeInTheDocument();
    expect(screen.getByText("REPAIR")).toBeInTheDocument();
    expect(screen.getByText("PROOF")).toBeInTheDocument();
    expect(screen.getAllByText("REJECTED").length).toBeGreaterThan(0);
    expect(screen.getAllByText("18/18").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText(/OpenAI live subagent/i)).toBeInTheDocument();
    expect(screen.getByText(/View exact candidate diff/i)).toBeInTheDocument();
    expect(screen.getByText(/demo\/study-in-germany/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Exact candidate source diff/i)).toHaveTextContent("WEEKLY_ALLOWANCE");
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
    expect(replayLink).toHaveAttribute("href", "/playthrough-inspector?persona=money");
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
    await user.click(screen.getByRole("button", { name: "中文" }));
    expect(screen.getByRole("heading", { name: "抵达德国" })).toBeInTheDocument();
    expect(screen.getByText("先去宿舍放行李")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "EN" }));

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
    expect(screen.getByText("cashflow_collapse")).toBeInTheDocument();
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
    expect(await screen.findByRole("heading", { name: /A patch passed its unit test/i })).toBeInTheDocument();
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
