import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

const competitionStyles = readFileSync("src/styles/competition.css", "utf8");

function zIndexFor(selector: string): number {
  const blockStart = competitionStyles.indexOf(`${selector} {`);
  const blockEnd = competitionStyles.indexOf("}", blockStart);
  const block = blockStart >= 0 && blockEnd > blockStart
    ? competitionStyles.slice(blockStart, blockEnd)
    : "";
  const value = block?.match(/z-index:\s*(\d+)/)?.[1];

  if (!value) throw new Error(`Missing numeric z-index for ${selector}`);
  return Number(value);
}

describe("competition modal stacking", () => {
  it("keeps the Persona drawer above the sticky competition navigation", () => {
    expect(zIndexFor(".competition-drawer-backdrop")).toBeGreaterThan(
      zIndexFor(".competition-top-nav"),
    );
  });
});
