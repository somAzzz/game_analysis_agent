import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ManifestError,
  fetchDecisionGraphManifest,
  fetchFrontManifest,
  fetchIssueManifest,
} from "@/lib/api";
import type {
  DecisionGraphManifest,
  FrontManifest,
  IssueManifest,
} from "@/types";

const frontManifest: FrontManifest = {
  generated_at: "2026-07-12T10:00:00Z",
  counts: {
    issues: 1,
    decision_graphs: 0,
    total_runs: 4,
    total_anomalies: 1,
    total_critical: 0,
  },
  issues: [
    {
      kind: "play",
      id: "run-one",
      slug: "play/run-one",
      title: "Run one",
      subtitle: "A test report",
      total_runs: 4,
      top_ending: null,
      anomaly_total: 1,
      severity: "warning",
      has_decision_graph: false,
    },
  ],
  issues_index: [
    { kind: "play", id: "run-one", path: "browse/play/run-one/manifest.json" },
  ],
};

const issueManifest: IssueManifest = {
  kind: "play",
  id: "run-one",
  slug: "play/run-one",
  report_dir: "reports/play/run-one",
  summary: {},
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
  raw_runs_count: 4,
};

const graphManifest: DecisionGraphManifest = {
  issue_id: "run-one",
  run_id: 7,
  policy: "balanced",
  scenario: "first-semester",
  seed: 17,
  max_weeks: 2,
  final_ending_id: "graduated",
  run: {
    run_id: 7,
    policy: "balanced",
    weekly_log: [],
  },
  event_graph: { events: [] },
};

function responseWith(value: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: vi.fn().mockResolvedValue(value),
  } as unknown as Response;
}

describe("manifest API", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("returns a valid front manifest and requests JSON directly", async () => {
    fetchMock.mockResolvedValue(responseWith(frontManifest));

    await expect(fetchFrontManifest()).resolves.toEqual(frontManifest);
    expect(fetchMock).toHaveBeenCalledWith("/manifest.json", {
      headers: { Accept: "application/json" },
    });
  });

  it("maps encoded issue and graph identifiers to static manifest paths", async () => {
    fetchMock
      .mockResolvedValueOnce(responseWith(issueManifest))
      .mockResolvedValueOnce(responseWith(graphManifest));

    await expect(
      fetchIssueManifest("boundary/risk", "id / one"),
    ).resolves.toEqual(issueManifest);
    await expect(
      fetchDecisionGraphManifest("graph #1", 7),
    ).resolves.toEqual(graphManifest);

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/browse/boundary%2Frisk/id%20%2F%20one/manifest.json",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/browse/decision_graph/graph%20%231/7/manifest.json",
    );
  });

  it("preserves HTTP status on a missing manifest", async () => {
    fetchMock.mockResolvedValue(responseWith({}, 404));

    const request = fetchFrontManifest();
    await expect(request).rejects.toMatchObject<Partial<ManifestError>>({
      status: 404,
    });
    await expect(request).rejects.toThrow("/manifest.json → HTTP 404");
  });

  it("turns a JSON parser failure into a useful manifest error", async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockRejectedValue(new SyntaxError("Unexpected token <")),
    } as unknown as Response);

    await expect(fetchFrontManifest()).rejects.toThrow(
      "/manifest.json returned non-JSON: Unexpected token <",
    );
  });

  it("rejects a structurally invalid front manifest", async () => {
    fetchMock.mockResolvedValue(
      responseWith({ ...frontManifest, issues: "not-an-array" }),
    );

    await expect(fetchFrontManifest()).rejects.toThrow(
      "invalid front manifest: issues must be array",
    );
  });

  it("rejects structurally invalid issue and graph manifests", async () => {
    fetchMock
      .mockResolvedValueOnce(
        responseWith({ ...issueManifest, raw_runs_count: "four" }),
      )
      .mockResolvedValueOnce(
        responseWith({ ...graphManifest, event_graph: [] }),
      );

    await expect(fetchIssueManifest("play", "run-one")).rejects.toThrow(
      "invalid issue manifest: raw_runs_count must be number",
    );
    await expect(
      fetchDecisionGraphManifest("run-one"),
    ).rejects.toThrow(
      "invalid decision graph manifest: event_graph must be object",
    );
  });
});
