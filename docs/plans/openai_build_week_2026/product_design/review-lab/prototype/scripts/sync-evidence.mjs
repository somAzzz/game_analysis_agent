import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

async function findRepoRoot(start) {
  let cursor = path.resolve(start);
  while (true) {
    try {
      await fs.access(path.join(cursor, "pyproject.toml"));
      await fs.access(path.join(cursor, "judge-manifest.json"));
      return cursor;
    } catch {
      const parent = path.dirname(cursor);
      if (parent === cursor) throw new Error("Repository root not found");
      cursor = parent;
    }
  }
}

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function invariant(condition, message) {
  if (!condition) throw new Error(`Review evidence invariant failed: ${message}`);
}

const repoRoot = await findRepoRoot(process.cwd());
const sourceRoot = path.join(
  repoRoot,
  "examples/build_week_2026/playthrough-v1",
);
const outputRoot = path.join(process.cwd(), "public/evidence");
const selectedFiles = [
  "manifest.json",
  "personas.json",
  "cells/money-seed-42.json",
];

const payloads = new Map();
for (const relativePath of selectedFiles) {
  const bytes = await fs.readFile(path.join(sourceRoot, relativePath));
  payloads.set(relativePath, bytes);
}

const manifest = JSON.parse(payloads.get("manifest.json").toString("utf8"));
const personas = JSON.parse(payloads.get("personas.json").toString("utf8"));
const cell = JSON.parse(
  payloads.get("cells/money-seed-42.json").toString("utf8"),
);

invariant(
  manifest.truth_label === "prerecorded-real-godot-replay",
  "manifest truth label",
);
invariant(personas.personas.length === 6, "six strategy Personas");
const money = personas.personas.find((persona) => persona.slug === "money");
invariant(money, "Money Persona exists");
invariant(
  money.observed.action_tag_rates.career === 0.004386,
  "Money observed career rate is exact",
);
invariant(cell.persona === "money" && cell.seed === 42, "selected cell identity");
invariant(cell.nodes.length === 19, "selected cell has 19 week nodes");
invariant(cell.actual_edges.length === 18, "selected cell has 18 actual edges");
invariant(
  cell.branch_semantics.projected_counterfactual_states === false,
  "counterfactual states stay hidden",
);

const w1 = cell.nodes.find((node) => node.week === 1);
const w3 = cell.nodes.find((node) => node.week === 3);
const w19 = cell.nodes.find((node) => node.week === 19);
invariant(
  w1?.evidence.source_record_sha256.startsWith("4d66dd4714fe") &&
    w1.state_before.money === 500 &&
    w1.state_after.money === 142,
  "W1 evidence and money delta",
);
invariant(
  w3?.evidence.source_record_sha256.startsWith("4041083497b4") &&
    w3.attractors.includes("cashflow-stress-attractor") &&
    w3.state_before.stress === 49 &&
    w3.state_after.stress === 82,
  "W3 attractor evidence",
);
invariant(
  w19?.evidence.source_record_sha256.startsWith("e0458a9d636e") &&
    cell.final_ending === "cashflow_collapse",
  "W19 ending evidence",
);

await fs.rm(outputRoot, { recursive: true, force: true });
await fs.mkdir(path.join(outputRoot, "cells"), { recursive: true });

const provenance = {
  schema_version: "review-lab-provenance-v1",
  truth_label: manifest.truth_label,
  source_root: "examples/build_week_2026/playthrough-v1",
  selected_cell: cell.cell_id,
  files: {},
};

for (const [relativePath, bytes] of payloads.entries()) {
  const destination = path.join(outputRoot, relativePath);
  await fs.mkdir(path.dirname(destination), { recursive: true });
  await fs.writeFile(destination, bytes);
  provenance.files[relativePath] = { sha256: sha256(bytes), bytes: bytes.length };
}

await fs.writeFile(
  path.join(outputRoot, "provenance.json"),
  `${JSON.stringify(provenance, null, 2)}\n`,
);

console.log(
  JSON.stringify({
    status: "passed",
    personas: personas.personas.length,
    nodes: cell.nodes.length,
    actual_edges: cell.actual_edges.length,
    truth_label: manifest.truth_label,
  }),
);
