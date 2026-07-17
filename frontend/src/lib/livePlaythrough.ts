import type {
  PlaythroughBundle,
  PlaythroughCell,
  PlaythroughManifest,
  PlaythroughPersona,
  PlaythroughPersonaSlug,
  PlaytestSession,
} from "@/types";

const SESSION_STATUSES = new Set(["running", "finalizing", "completed", "failed"]);

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

const PERSONA_SLUGS = new Set<PlaythroughPersonaSlug>([
  "newbie",
  "study",
  "money",
  "social",
  "visa",
  "slacker",
]);

export async function loadLivePlaythrough(
  signal?: AbortSignal,
): Promise<PlaythroughBundle | null> {
  const root = `${import.meta.env.BASE_URL}live-playthrough`;
  const [manifestResponse, personasResponse] = await Promise.all([
    fetch(`${root}/manifest.json`, { signal }),
    fetch(`${root}/personas.json`, { signal }),
  ]);
  if (manifestResponse.status === 404 || personasResponse.status === 404)
    return null;
  if (!manifestResponse.ok || !personasResponse.ok) {
    throw new Error("Latest playthrough evidence is unavailable");
  }

  const manifest = (await manifestResponse.json()) as PlaythroughManifest;
  const personaDocument = (await personasResponse.json()) as {
    truth_label: string;
    personas: PlaythroughPersona[];
  };
  const activePersonas = (manifest.request?.personas ?? []).filter(
    (value): value is PlaythroughPersonaSlug => PERSONA_SLUGS.has(value),
  );
  const seed = manifest.request?.seeds[0];
  if (
    !manifest.playthrough_data_ready ||
    manifest.truth_label === "prerecorded-real-godot-replay" ||
    personaDocument.truth_label !== manifest.truth_label ||
    activePersonas.length === 0 ||
    seed === undefined
  ) {
    throw new Error("Latest playthrough evidence contract is invalid");
  }

  const entries = await Promise.all(
    activePersonas.map(async (slug) => {
      const response = await fetch(`${root}/cells/${slug}-seed-${seed}.json`, {
        signal,
      });
      if (!response.ok)
        throw new Error(`Latest ${slug} playthrough is unavailable`);
      return [slug, (await response.json()) as PlaythroughCell] as const;
    }),
  );
  const cells = Object.fromEntries(entries) as Partial<
    Record<PlaythroughPersonaSlug, PlaythroughCell>
  >;
  for (const [slug, cell] of entries) {
    if (
      cell.persona !== slug ||
      cell.seed !== seed ||
      cell.truth_label !== manifest.truth_label ||
      cell.provider !== manifest.source.provider ||
      cell.provider_mode !== manifest.source.provider_mode
    ) {
      throw new Error(`Latest ${slug} playthrough identity is invalid`);
    }
  }
  const cell = cells[activePersonas[0]];
  if (!cell) throw new Error("Latest playthrough has no representative cell");
  return {
    manifest,
    personas: personaDocument.personas,
    cell,
    cells,
  };
}
