import { beforeEach, describe, expect, it, vi } from "vitest";
import { loadLivePlaythrough } from "@/lib/livePlaythrough";
import type {
  PlaythroughCell,
  PlaythroughCellIndex,
  PlaythroughManifest,
} from "@/types";

const manifest: PlaythroughManifest = {
  schema_version: "playthrough-evidence-manifest-v1",
  campaign_id: "local-campaign",
  truth_label: "local-vllm-real-godot",
  cell_count: 2,
  node_count: 38,
  actual_edge_count: 36,
  legal_event_choice_count: 12,
  playthrough_data_ready: true,
  source: {
    agent_commit: "a".repeat(40),
    game_commit: "b".repeat(40),
    provider: "vllm",
    provider_mode: "local",
    provider_revision: "model:local-test",
  },
};

const index: PlaythroughCellIndex = {
  schema_version: "playthrough-cell-index-v1",
  campaign_id: manifest.campaign_id,
  truth_label: manifest.truth_label,
  cell_count: 2,
  cells: [42, 43].map((seed) => ({
    cell_id: `money-seed-${seed}`,
    persona: "money" as const,
    seed,
    path: `cells/money-seed-${seed}.json`,
    completed_weeks: 19,
    final_ending: "semester_complete",
    stop_reason: "game_finished",
    attractor_count: 0,
  })),
};

function cell(seed: number): PlaythroughCell {
  return {
    schema_version: "playthrough-view-v1",
    campaign_id: manifest.campaign_id,
    cell_id: `money-seed-${seed}`,
    truth_label: manifest.truth_label,
    persona: "money",
    seed,
    scenario: "default_first_semester",
    difficulty: "normal",
    provider: "vllm",
    provider_mode: "local",
    provider_revision: "model:local-test",
    game_commit: "b".repeat(40),
    agent_commit: "a".repeat(40),
    completed_weeks: 19,
    final_ending: "semester_complete",
    stop_reason: "game_finished",
    branch_semantics: {
      available_actions: "legal-options",
      event_choices: "legal-options",
      projected_counterfactual_states: false,
    },
    actual_edges: [],
    nodes: [],
  };
}

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("live playthrough index", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("loads only the exact selected persona and seed trace", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/manifest.json")) return Promise.resolve(jsonResponse(manifest));
      if (url.endsWith("/personas.json")) {
        return Promise.resolve(jsonResponse({ truth_label: manifest.truth_label, personas: [] }));
      }
      if (url.endsWith("/index.json")) return Promise.resolve(jsonResponse(index));
      if (url.endsWith("/cells/money-seed-43.json")) {
        return Promise.resolve(jsonResponse(cell(43)));
      }
      throw new Error(`unexpected fetch: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    const bundle = await loadLivePlaythrough(undefined, { persona: "money", seed: 43 });

    expect(bundle?.cell.seed).toBe(43);
    expect(bundle?.cellReferences.map((item) => item.seed)).toEqual([42, 43]);
    expect(fetchMock.mock.calls.map(([input]) => String(input))).not.toContain(
      "/live-playthrough/cells/money-seed-42.json",
    );
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });
});
