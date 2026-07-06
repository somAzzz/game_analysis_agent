/**
 * Tiny fetch helpers used by every page. The Python pipeline writes
 * static JSON under reports/ which we copy into frontend/public/ at
 * build time. So the React app fetches them as if they were a normal
 * CDN.
 */

import type {
  DecisionGraphManifest,
  FrontManifest,
  IssueManifest,
} from "@/types";

export class ManifestError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.status = status;
  }
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    throw new ManifestError(`${url} → HTTP ${res.status}`, res.status);
  }
  try {
    return (await res.json()) as T;
  } catch (err) {
    throw new ManifestError(
      `${url} returned non-JSON: ${(err as Error).message}`,
    );
  }
}

export function fetchFrontManifest(): Promise<FrontManifest> {
  return fetchJSON<FrontManifest>("/manifest.json");
}

export function fetchIssueManifest(
  kind: string,
  id: string,
): Promise<IssueManifest> {
  return fetchJSON<IssueManifest>(
    `/browse/${encodeURIComponent(kind)}/${encodeURIComponent(id)}/manifest.json`,
  );
}

export function fetchDecisionGraphManifest(
  issueId: string,
  runId = 0,
): Promise<DecisionGraphManifest> {
  return fetchJSON<DecisionGraphManifest>(
    `/browse/decision_graph/${encodeURIComponent(issueId)}/${runId}/manifest.json`,
  );
}