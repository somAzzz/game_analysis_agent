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
}

export interface FrontManifest {
  generated_at: string;
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