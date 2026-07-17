/**
 * Tiny fetch helpers used by every page. The Python pipeline writes
 * static JSON under reports/ which we copy into frontend/public/ at
 * build time. So the React app fetches them as if they were a normal
 * CDN.
 */

import type {
  DecisionGraphManifest,
  FrontManifest,
  HumanReviewDecision,
  HumanReviewRecord,
  IssueManifest,
  JudgeCampaignJob,
  JudgeExperimentIndex,
  JudgeExperiment,
  JudgeProvider,
  JudgeProviderStatus,
} from "@/types";

const BASE_URL = import.meta.env.BASE_URL || "/";

type FieldKind = "array" | "number" | "object" | "string";
type ManifestShape = Record<string, FieldKind>;

const FRONT_MANIFEST_SHAPE: ManifestShape = {
  generated_at: "string",
  counts: "object",
  issues: "array",
  issues_index: "array",
};

const ISSUE_MANIFEST_SHAPE: ManifestShape = {
  kind: "string",
  id: "string",
  slug: "string",
  report_dir: "string",
  summary: "object",
  endings: "array",
  actions: "array",
  events: "array",
  choices: "array",
  weekly_series: "object",
  anomalies: "array",
  value_findings: "array",
  route_findings: "object",
  agents: "array",
  agent_markdown: "object",
  raw_runs_count: "number",
};

const DECISION_GRAPH_MANIFEST_SHAPE: ManifestShape = {
  issue_id: "string",
  run_id: "number",
  policy: "string",
  scenario: "string",
  max_weeks: "number",
  final_ending_id: "string",
  run: "object",
  event_graph: "object",
};

function matchesKind(value: unknown, kind: FieldKind): boolean {
  if (kind === "array") return Array.isArray(value);
  if (kind === "object") {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }
  if (kind === "number") {
    return typeof value === "number" && Number.isFinite(value);
  }
  return typeof value === kind;
}

function decodeManifest<T>(
  value: unknown,
  url: string,
  label: string,
  shape: ManifestShape,
): T {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new ManifestError(url + " returned invalid " + label + " manifest: root must be an object");
  }
  const record = value as Record<string, unknown>;
  const invalidField = Object.entries(shape).find(
    ([field, kind]) => !matchesKind(record[field], kind),
  );
  if (invalidField) {
    const [field, kind] = invalidField;
    throw new ManifestError(
      url + " returned invalid " + label + " manifest: " + field + " must be " + kind,
    );
  }
  return value as T;
}

export function assetPath(path: string): string {
  const cleanBase = BASE_URL.endsWith("/") ? BASE_URL : `${BASE_URL}/`;
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  return `${cleanBase}${cleanPath}`;
}

export class JudgeAPIError extends Error {
  status?: number;
  code?: string;
  remediation?: string;
}

async function judgeJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new JudgeAPIError(`/api/${path} returned non-JSON`);
  }
  if (!response.ok) {
    const detail = value as { error?: { code?: string; message?: string; remediation?: string } };
    const error = new JudgeAPIError(detail.error?.message ?? `/api/${path} → HTTP ${response.status}`);
    error.status = response.status;
    error.code = detail.error?.code;
    error.remediation = detail.error?.remediation;
    throw error;
  }
  return value as T;
}

export function fetchJudgeProviderStatus(): Promise<JudgeProviderStatus> {
  return judgeJSON<JudgeProviderStatus>("provider-status");
}

export function testJudgeProvider(provider: JudgeProvider): Promise<Record<string, unknown>> {
  return judgeJSON<Record<string, unknown>>("provider-test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
}

export function createJudgeCampaign(provider: JudgeProvider): Promise<JudgeCampaignJob> {
  return judgeJSON<JudgeCampaignJob>("campaigns", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider }),
  });
}

export function fetchJudgeCampaign(campaignId: string): Promise<JudgeCampaignJob> {
  return judgeJSON<JudgeCampaignJob>(`campaigns/${encodeURIComponent(campaignId)}`);
}

export function fetchJudgeExperiments(): Promise<JudgeExperimentIndex> {
  return judgeJSON<JudgeExperimentIndex>("experiments");
}

export function fetchJudgeExperiment(experimentId = "cashflow-drift-repair-v1"): Promise<JudgeExperiment> {
  return judgeJSON<JudgeExperiment>("experiments/" + encodeURIComponent(experimentId));
}

export function submitHumanReview(
  experimentId: string,
  evidenceFingerprint: string,
  decision: HumanReviewDecision,
  reviewerNote: string,
): Promise<HumanReviewRecord> {
  return judgeJSON<HumanReviewRecord>(
    `experiments/${encodeURIComponent(experimentId)}/human-review`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        evidence_fingerprint: evidenceFingerprint,
        decision,
        reviewer_note: reviewerNote,
      }),
    },
  );
}

export async function fetchStaticJudgeExperiments(): Promise<JudgeExperimentIndex> {
  const path = assetPath("experiment-index.json");
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new ManifestError(`${path} → HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<JudgeExperimentIndex>;
}

export async function fetchStaticJudgeExperiment(
  experimentId = "cashflow-drift-repair-v1",
): Promise<JudgeExperiment> {
  const path = experimentId === "cashflow-drift-repair-v1"
    ? assetPath("judge-demo.json")
    : assetPath(`experiments/${encodeURIComponent(experimentId)}/judge-experiment.json`);
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new ManifestError(`${path} → HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<JudgeExperiment>;
}

export class ManifestError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

async function fetchJSON<T>(
  url: string,
  label: string,
  shape: ManifestShape,
): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    throw new ManifestError(`${url} → HTTP ${res.status}`, res.status);
  }
  let value: unknown;
  try {
    value = await res.json();
  } catch (err) {
    throw new ManifestError(
      `${url} returned non-JSON: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
  return decodeManifest<T>(value, url, label, shape);
}

export function fetchFrontManifest(): Promise<FrontManifest> {
  return fetchJSON<FrontManifest>(
    assetPath("manifest.json"),
    "front",
    FRONT_MANIFEST_SHAPE,
  );
}

export function fetchIssueManifest(
  kind: string,
  id: string,
): Promise<IssueManifest> {
  return fetchJSON<IssueManifest>(
    assetPath(`browse/${encodeURIComponent(kind)}/${encodeURIComponent(id)}/manifest.json`),
    "issue",
    ISSUE_MANIFEST_SHAPE,
  );
}

export function fetchDecisionGraphManifest(
  issueId: string,
  runId = 0,
): Promise<DecisionGraphManifest> {
  return fetchJSON<DecisionGraphManifest>(
    assetPath(`browse/decision_graph/${encodeURIComponent(issueId)}/${runId}/manifest.json`),
    "decision graph",
    DECISION_GRAPH_MANIFEST_SHAPE,
  );
}
