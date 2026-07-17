import type {
  PlaythroughBundle,
  PlaythroughCell,
  PlaythroughCellIndex,
  PlaythroughCellReference,
  PlaythroughManifest,
  PlaythroughPersona,
  PlaythroughPersonaSlug,
  PlaytestSession,
} from "@/types";

const SESSION_STATUSES = new Set(["running", "finalizing", "completed", "failed"]);
const PERSONA_SLUGS = new Set<PlaythroughPersonaSlug>([
  "newbie",
  "study",
  "money",
  "social",
  "visa",
  "slacker",
]);

export async function loadPlaytestSession(
  signal?: AbortSignal,
): Promise<PlaytestSession | null> {
  const root = `${import.meta.env.BASE_URL}live-playthrough`;
  const response = await fetch(`${root}/session.json?time=${Date.now()}`, {
    signal,
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Live playtest session is unavailable");
  const session = (await response.json()) as PlaytestSession;
  if (
    session.schema_version !== "persona-campaign-session-v1"
    || !SESSION_STATUSES.has(session.status)
    || !session.campaign_id
    || !session.truth_label
    || !Array.isArray(session.cells)
  ) {
    throw new Error("Live playtest session contract is invalid");
  }
  return session;
}

export async function loadLivePlaythrough(
  signal?: AbortSignal,
  selection?: { persona?: PlaythroughPersonaSlug; seed?: number },
): Promise<PlaythroughBundle | null> {
  const root = `${import.meta.env.BASE_URL}live-playthrough`;
  const [manifestResponse, personasResponse, indexResponse] = await Promise.all([
    fetch(`${root}/manifest.json`, { signal, cache: "no-store" }),
    fetch(`${root}/personas.json`, { signal, cache: "no-store" }),
    fetch(`${root}/index.json`, { signal, cache: "no-store" }),
  ]);
  if (manifestResponse.status === 404 || personasResponse.status === 404) return null;
  if (!manifestResponse.ok || !personasResponse.ok || !indexResponse.ok) {
    throw new Error("Latest playthrough evidence is unavailable");
  }

  const manifest = (await manifestResponse.json()) as PlaythroughManifest;
  const personaDocument = (await personasResponse.json()) as {
    truth_label: string;
    personas: PlaythroughPersona[];
  };
  const index = (await indexResponse.json()) as PlaythroughCellIndex;
  const references = validateIndex(manifest, personaDocument, index);
  const selected = references.find((item) => (
    (!selection?.persona || item.persona === selection.persona)
    && (selection?.seed === undefined || item.seed === selection.seed)
  )) ?? references.find((item) => item.persona === selection?.persona) ?? references[0];
  if (!selected) throw new Error("Latest playthrough has no indexed cell");
  const cell = await loadLivePlaythroughCell(manifest, selected, signal);
  return {
    manifest,
    personas: personaDocument.personas,
    cell,
    cells: { [cell.persona]: cell },
    cellReferences: references,
  };
}

export async function loadLivePlaythroughCell(
  manifest: PlaythroughManifest,
  reference: PlaythroughCellReference,
  signal?: AbortSignal,
): Promise<PlaythroughCell> {
  if (!/^cells\/[a-z]+-seed--?\d+\.json$/.test(reference.path)) {
    throw new Error("Latest playthrough cell path is unsafe");
  }
  const root = `${import.meta.env.BASE_URL}live-playthrough`;
  const response = await fetch(`${root}/${reference.path}`, {
    signal,
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Latest ${reference.persona} seed ${reference.seed} playthrough is unavailable`);
  const cell = (await response.json()) as PlaythroughCell;
  if (
    cell.cell_id !== reference.cell_id
    || cell.persona !== reference.persona
    || cell.seed !== reference.seed
    || cell.truth_label !== manifest.truth_label
    || cell.provider !== manifest.source.provider
    || cell.provider_mode !== manifest.source.provider_mode
  ) {
    throw new Error("Latest playthrough cell identity is invalid");
  }
  return cell;
}

function validateIndex(
  manifest: PlaythroughManifest,
  personaDocument: { truth_label: string; personas: PlaythroughPersona[] },
  index: PlaythroughCellIndex,
): PlaythroughCellReference[] {
  const references = index.cells;
  const identities = new Set<string>();
  if (
    !manifest.playthrough_data_ready
    || manifest.truth_label === "prerecorded-real-godot-replay"
    || personaDocument.truth_label !== manifest.truth_label
    || index.schema_version !== "playthrough-cell-index-v1"
    || index.campaign_id !== manifest.campaign_id
    || index.truth_label !== manifest.truth_label
    || index.cell_count !== manifest.cell_count
    || !Array.isArray(references)
    || references.length !== manifest.cell_count
  ) {
    throw new Error("Latest playthrough evidence contract is invalid");
  }
  for (const reference of references) {
    const identity = `${reference.persona}:${reference.seed}`;
    if (
      !PERSONA_SLUGS.has(reference.persona)
      || !Number.isInteger(reference.seed)
      || !reference.cell_id
      || identities.has(identity)
      || !/^cells\/[a-z]+-seed--?\d+\.json$/.test(reference.path)
    ) {
      throw new Error("Latest playthrough cell index is invalid");
    }
    identities.add(identity);
  }
  return [...references].sort((left, right) => (
    left.persona.localeCompare(right.persona) || left.seed - right.seed
  ));
}
