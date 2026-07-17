/**
 * TypeScript mirrors of the JSON shapes produced by
 * ``tools/emit_manifest.py``. Keep these in sync if the Python side
 * evolves; the React app will refuse to render against stale shapes
 * because it uses ``fetch + JSON.parse`` and prop-types at runtime.
 */

export type IssueKind = "balance" | "boundary" | "play";
export type Severity = "info" | "warning" | "error" | "critical";

export interface IssueCard {
  kind: IssueKind;
  id: string;
  slug: string;
  title: string;
  subtitle: string;
  total_runs: number;
  top_ending: { policy: string; ending_id: string; count: number; rate: number } | null;
  anomaly_total: number;
  severity: Severity;
  has_decision_graph: boolean;
  scenario?: string;
  difficulty?: string;
  policy?: string;
}

export interface FrontManifest {
  generated_at: string;
  public_demo?: boolean;
  public_notice?: string;
  source_counts?: {
    issues?: number;
    decision_graphs?: number;
    total_runs?: number;
    total_anomalies?: number;
    total_critical?: number;
  };
  counts: {
    issues: number;
    decision_graphs: number;
    total_runs: number;
    total_anomalies: number;
    total_critical: number;
  };
  issues: IssueCard[];
  issues_index: { kind: IssueKind; id: string; path: string }[];
}

export interface WeeklyPoint {
  week: number;
  mean: number;
  p10: number;
  p90: number;
}

export interface IssueManifest {
  kind: IssueKind;
  id: string;
  slug: string;
  report_dir: string;
  summary: Record<string, unknown>;
  endings: Record<string, string>[];
  actions: Record<string, string>[];
  events: Record<string, string>[];
  choices: Record<string, string>[];
  weekly_series: Record<string, WeeklyPoint[]>;
  anomalies: AnomalyRow[];
  value_findings: ValueFinding[];
  route_findings: {
    groups: ValueFinding[];
    crisis_response: ValueFinding[];
    ending_contradictions: ValueFinding[];
    route_separation: ValueFinding[];
  };
  agents: { label: string; file: string; bytes: string }[];
  agent_markdown: Record<string, string>;
  gate_report: { passed?: boolean; failures?: { gate: string; actual: number; threshold: number; message: string }[]; passed_count?: number } | null;
  coverage_report: unknown;
  raw_runs_count: number;
  public_demo?: boolean;
  public_notice?: string;
  source_summary?: {
    source_kind?: string;
    source_policy?: string;
    source_scenario?: string;
    source_difficulty?: string;
  };
}

export interface AnomalyRow {
  kind: string;
  severity: Severity;
  run_id: number;
  week: number;
  policy: string;
  evidence?: Record<string, unknown>;
  message?: string;
}

export interface ValueFinding {
  finding_id: string;
  scope: string;
  target_id: string;
  severity: Severity;
  metric: string;
  value: number;
  threshold: number;
  description: string;
}

export interface Choice {
  text?: string;
  label?: string;
  name?: string;
  description?: string;
  title?: string;
  next_event_id?: string;
  success_effects?: Record<string, number>;
  effects?: Record<string, number>;
  outcome_effects?: Record<string, number>;
}

export interface DecisionGraphEvent {
  id: string;
  title?: string;
  body?: string;
  event_type?: string;
  type?: string;
  kind?: string;
  trigger?: { week?: number; min_week?: number; start_week?: number; fire_week?: number; at_week?: number; first_week?: number; weeks?: number[] };
  source_order?: number;
  choices?: Choice[];
}

export interface DecisionGraphWeeklyEntry {
  week: number;
  triggered_event_id?: string;
  event_id?: string;
  event_choice_id?: string;
  selected_action_ids?: string[];
  actions?: string[];
  after_state?: Record<string, unknown>;
  choice_index?: number;
}

export interface DecisionGraphManifest {
  issue_id: string;
  run_id: number;
  policy: string;
  scenario: string;
  seed: number | null;
  max_weeks: number;
  final_ending_id: string;
  run: {
    run_id: number;
    policy: string;
    seed?: number;
    weekly_log?: DecisionGraphWeeklyEntry[];
    [key: string]: unknown;
  };
  event_graph: {
    events?: DecisionGraphEvent[];
    [key: string]: unknown;
  };
  public_demo?: boolean;
  public_notice?: string;
}

export interface TriggeredStep {
  week: number;
  event_id: string;
  title: string;
  body: string;
  event_type: string;
  choice_index: number;
  choice_id: string;
  choice_text: string;
  choice_effects: Record<string, number>;
  selected_actions: string[];
  after_state: Record<string, unknown>;
  x: number;
  y: number;
}

export interface GraphPayload {
  events: TriggeredStep[];
  lane_order: string[];
  max_week: number;
  diagnostics: string[];
  layout: {
    width: number;
    height: number;
    positions: Record<string, [number, number]>;
    lane_y: Record<string, number>;
    events: DecisionGraphEvent[];
    event_index: Record<string, DecisionGraphEvent>;
  };
}

export type JudgeProvider = "replay" | "openai";
export type JudgeJobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface JudgeProviderStatus {
  schema_version: string;
  providers: {
    replay: {
      status: "available";
      mode: "prerecorded";
      requires_api_key: false;
      requires_game_runtime: false;
    };
    openai: {
      status: "available" | "unavailable";
      mode: "live";
      model: string;
      requires_api_key: true;
      api_key_configured: boolean;
      game_runtime_configured: boolean;
      live_campaign_ready: boolean;
    };
  };
}

export interface JudgeCampaignJob {
  campaign_id: string;
  status: JudgeJobStatus;
  mode: "prerecorded" | "live";
  request: {
    provider: JudgeProvider;
    personas: string[];
    seeds: number[];
    max_weeks: number;
  };
  created_at: string;
  updated_at: string;
  result: Record<string, unknown> | null;
  error: { code: string; message: string; remediation: string } | null;
}

export interface JudgeCohort {
  cohort: "baseline_fixed" | "patched_fixed" | "baseline_holdout" | "patched_holdout";
  game_commit: string;
  seeds: number[];
  cells: number;
  weeks: number;
  target_members: number;
  target_personas: number;
  mean_final_money: number | null;
  mean_max_stress: number | null;
  valid_rate: number;
  fallback_rate: number;
  provider_error_rate: number;
  persona_alignment_rate: number | null;
  ending_counts: Record<string, number>;
}

export interface JudgeExperiment {
  schema_version: string;
  experiment_id: string;
  status: string;
  decision: "accepted" | "rejected";
  decision_reason: string;
  hypothesis: string;
  mechanism_class: string;
  comparison: {
    fixed_member_delta: number;
    fixed_relative_reduction: number;
    holdout_member_delta: number;
    holdout_relative_reduction: number;
  };
  cohorts: JudgeCohort[];
  gates: {
    gate_id: string;
    status: "passed" | "failed";
    detail: string;
    evidence_paths: string[];
  }[];
  patch: {
    baseline_commit: string;
    patched_commit: string;
    mechanism_class: string;
    modified_paths: string[];
    changed_files: number;
    added_lines: number;
    deleted_lines: number;
    patch_path: string;
    patch_sha256: string;
    canonical_source_path: string;
    disposition: "candidate_not_merged";
    diff: string;
  };
  codex: {
    task_reference: string;
    feedback_session_id: string;
    model: string;
    skill: string;
    hypothesis_owned_by_codex: true;
    patch_owned_by_codex: true;
    decision_owned_by_codex: true;
  };
  mode: "prerecorded";
}

export type PlaythroughPersonaSlug =
  | "newbie"
  | "study"
  | "money"
  | "social"
  | "visa"
  | "slacker";

export interface PlaythroughPersona {
  slug: PlaythroughPersonaSlug;
  contract: {
    description: string;
    priorities: string[];
    hard_avoid: string[];
    risk_tolerance: number;
    exploration: number;
    failure_intent: boolean;
    alignment_risk_guided?: boolean;
  };
  observed: {
    seeds: number[];
    cell_count: number;
    completed_cells: number;
    weeks: number;
    selected_action_count: number;
    action_tag_rates: Record<string, number>;
    first_cashflow_stress_attractor_weeks: number[];
    final_endings: Record<string, number>;
  };
}

export interface PlaythroughManifest {
  schema_version: string;
  campaign_id: string;
  truth_label: "prerecorded-real-godot-replay";
  cell_count: number;
  node_count: number;
  actual_edge_count: number;
  legal_event_choice_count: number;
  playthrough_data_ready: boolean;
  source: {
    agent_commit: string;
    game_commit: string;
    provider: string;
    provider_mode: string;
    provider_revision: string;
  };
}

export interface PlaythroughChoice {
  choice_id: string;
  text: string;
  next_event_id: string;
  requirements: Record<string, unknown>;
  success_effects: Record<string, number>;
  failure_effects: Record<string, number>;
  success_rate: number;
}

export interface PlaythroughNode {
  id: string;
  kind: "actual";
  week: number;
  finished: boolean;
  attractors: string[];
  selected_action_ids: string[];
  state_before: Record<string, unknown>;
  state_after: Record<string, unknown>;
  event: {
    id: string;
    selected_choice_id: string;
    legal_choices: PlaythroughChoice[];
  };
  evidence: {
    source_line: number;
    source_record_sha256: string;
    decision_request_fingerprint: string;
    event_request_fingerprint: string;
  };
}

export interface PlaythroughCell {
  schema_version: string;
  campaign_id: string;
  cell_id: string;
  truth_label: "prerecorded-real-godot-replay";
  persona: PlaythroughPersonaSlug;
  seed: number;
  scenario: string;
  difficulty: string;
  provider: string;
  provider_mode: string;
  provider_revision: string;
  game_commit: string;
  agent_commit: string;
  completed_weeks: number;
  final_ending: string;
  stop_reason: string;
  branch_semantics: {
    available_actions: string;
    event_choices: string;
    projected_counterfactual_states: false;
  };
  actual_edges: Array<{
    id: string;
    kind: "actual";
    from: string;
    to: string;
  }>;
  nodes: PlaythroughNode[];
}

export interface PlaythroughBundle {
  manifest: PlaythroughManifest;
  personas: PlaythroughPersona[];
  cell: PlaythroughCell;
  cells: Record<PlaythroughPersonaSlug, PlaythroughCell>;
}
