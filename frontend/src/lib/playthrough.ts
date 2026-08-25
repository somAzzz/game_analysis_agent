import manifestValue from "../../../examples/build_week_2026/playthrough-v1/manifest.json";
import personasValue from "../../../examples/build_week_2026/playthrough-v1/personas.json";
import newbieCellValue from "../../../examples/build_week_2026/playthrough-v1/cells/newbie-seed-42.json";
import studyCellValue from "../../../examples/build_week_2026/playthrough-v1/cells/study-seed-42.json";
import moneyCellValue from "../../../examples/build_week_2026/playthrough-v1/cells/money-seed-42.json";
import socialCellValue from "../../../examples/build_week_2026/playthrough-v1/cells/social-seed-42.json";
import visaCellValue from "../../../examples/build_week_2026/playthrough-v1/cells/visa-seed-42.json";
import slackerCellValue from "../../../examples/build_week_2026/playthrough-v1/cells/slacker-seed-42.json";
import type {
  PlaythroughBundle,
  PlaythroughCell,
  PlaythroughManifest,
  PlaythroughPersona,
  PlaythroughPersonaSlug,
} from "@/types";

const manifest = manifestValue as PlaythroughManifest;
const personasDocument = personasValue as unknown as {
  truth_label: string;
  personas: PlaythroughPersona[];
};
const cells: Record<PlaythroughPersonaSlug, PlaythroughCell> = {
  newbie: newbieCellValue as PlaythroughCell,
  study: studyCellValue as PlaythroughCell,
  money: moneyCellValue as PlaythroughCell,
  social: socialCellValue as PlaythroughCell,
  visa: visaCellValue as PlaythroughCell,
  slacker: slackerCellValue as PlaythroughCell,
};
const cell = cells.money;

function assertCompetitionEvidence(): void {
  const failures: string[] = [];
  if (manifest.truth_label !== "prerecorded-real-godot-replay") failures.push("manifest truth label");
  if (!manifest.playthrough_data_ready) failures.push("playthrough readiness");
  if (manifest.cell_count !== 18 || manifest.node_count !== 342 || manifest.actual_edge_count !== 324) {
    failures.push("campaign totals");
  }
  if (personasDocument.truth_label !== manifest.truth_label || personasDocument.personas.length !== 6) {
    failures.push("persona cohort");
  }
  for (const [slug, personaCell] of Object.entries(cells) as Array<[PlaythroughPersonaSlug, PlaythroughCell]>) {
    if (personaCell.truth_label !== manifest.truth_label || personaCell.persona !== slug || personaCell.seed !== 42) {
      failures.push(`${slug} cell identity`);
    }
    if (personaCell.nodes.length !== 19 || personaCell.actual_edges.length !== 18) {
      failures.push(`${slug} path shape`);
    }
    if (personaCell.branch_semantics.projected_counterfactual_states !== false) {
      failures.push(`${slug} branch semantics`);
    }
  }
  const money = personasDocument.personas.find((persona) => persona.slug === "money");
  if (money?.observed.action_tag_rates.career !== 0.004386) failures.push("Money career mismatch");
  if (failures.length > 0) {
    throw new Error(`Competition evidence contract failed: ${failures.join(", ")}`);
  }
}

assertCompetitionEvidence();

export const competitionPlaythrough: PlaythroughBundle = Object.freeze({
  manifest,
  personas: personasDocument.personas,
  cell,
  cells,
  cellReferences: Object.values(cells).map((item) => ({
    cell_id: item.cell_id,
    persona: item.persona,
    seed: item.seed,
    path: `cells/${item.persona}-seed-${item.seed}.json`,
    completed_weeks: item.completed_weeks,
    final_ending: item.final_ending,
    stop_reason: item.stop_reason,
    attractor_count: item.nodes.filter((node) => node.attractors.length > 0).length,
  })),
});
