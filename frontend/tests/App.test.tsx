import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "@/App";
import type {
  DecisionGraphManifest,
  FrontManifest,
  IssueManifest,
} from "@/types";

const apiMocks = vi.hoisted(() => ({
  fetchFrontManifest: vi.fn(),
  fetchIssueManifest: vi.fn(),
  fetchDecisionGraphManifest: vi.fn(),
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
    apiMocks.fetchFrontManifest.mockResolvedValue(frontManifest);
    apiMocks.fetchIssueManifest.mockResolvedValue(issueManifest);
    apiMocks.fetchDecisionGraphManifest.mockResolvedValue(graphManifest);
  });

  it("renders the report index and filters cards with search and severity controls", async () => {
    const user = userEvent.setup();
    renderRoute("/");

    expect(
      await screen.findByRole("heading", { name: /The Analysis Console/i }),
    ).toBeInTheDocument();
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
  });

  it("navigates from a report card to the issue page", async () => {
    const user = userEvent.setup();
    renderRoute("/");

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
        name: /The decision graph/i,
      }),
    ).toBeInTheDocument();
    expect(apiMocks.fetchDecisionGraphManifest).toHaveBeenCalledWith(
      "graph one",
      2,
    );
    expect(screen.getByText("graduated")).toBeInTheDocument();
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
  });

  it("renders the 404 page and returns to the report index", async () => {
    const user = userEvent.setup();
    renderRoute("/not-a-real-route");

    expect(
      screen.getByRole("heading", { level: 1, name: /404 · lost the plot/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /Back to the front page/i }));
    expect(
      await screen.findByRole("heading", { name: /The Analysis Console/i }),
    ).toBeInTheDocument();
  });

  it("shows a useful front-page loading failure", async () => {
    apiMocks.fetchFrontManifest.mockRejectedValue(
      new Error("manifest service unavailable"),
    );
    renderRoute("/");

    expect(
      await screen.findByRole("heading", { name: "Failed to load manifest" }),
    ).toBeInTheDocument();
    expect(screen.getByText("manifest service unavailable")).toBeInTheDocument();
  });
});
