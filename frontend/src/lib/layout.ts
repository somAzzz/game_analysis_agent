/**
 * TypeScript port of the Python decision-graph layout + choice extraction
 * in ``tools/build_dashboard.py``. Mirrors the same five-axis adaptive
 * logic so the React Flow view stays in lockstep with the static SVG
 * view:
 *
 *   1. Lanes derived from event_type (no hardcoded "fixed/conditional/random")
 *   2. Lane y auto-spaced by lane count
 *   3. Trigger week from any of week / min_week / start_week / fire_week / ...
 *   4. Choice index from any of 7 different on-the-wire formats
 *   5. Defensive field access (text/label/name; success_effects/effects/...)
 *
 * The Python side remains the source of truth; this file is the
 * runtime mirror so React can compute graph geometry in the browser
 * without a round-trip.
 */

import type {
  DecisionGraphEvent,
  DecisionGraphManifest,
  DecisionGraphWeeklyEntry,
  TriggeredStep,
} from "@/types";

export interface GraphLayout {
  width: number;
  height: number;
  maxWeek: number;
  positions: Record<string, [number, number]>;
  laneY: Record<string, number>;
  laneOrder: string[];
  events: DecisionGraphEvent[];
  eventIndex: Record<string, DecisionGraphEvent>;
}

export interface ComputedGraph {
  layout: GraphLayout;
  events: TriggeredStep[];
  diagnostics: string[];
  laneOrder: string[];
  maxWeek: number;
}

/* ------------------------------------------------------------ */
/* Schema-tolerant field accessors                              */
/* ------------------------------------------------------------ */

export function triggerWeek(trigger: unknown): number | null {
  if (!trigger || typeof trigger !== "object") return null;
  const t = trigger as Record<string, unknown>;
  for (const key of [
    "week",
    "min_week",
    "start_week",
    "first_week",
    "at_week",
    "fire_week",
  ]) {
    const v = t[key];
    if (typeof v === "number" && v >= 0) return v;
  }
  const weeksList = t.weeks;
  if (Array.isArray(weeksList) && weeksList.length > 0) {
    const first = weeksList[0];
    if (typeof first === "number" && first >= 0) return first;
  }
  return null;
}

export function laneFor(ev: DecisionGraphEvent): string {
  const raw = ev.event_type ?? ev.type ?? ev.kind;
  if (typeof raw !== "string" || raw.trim() === "") return "uncategorised";
  return raw.trim().toLowerCase();
}

export function safeChoiceText(choice: unknown): string {
  if (!choice || typeof choice !== "object") return "";
  const c = choice as Record<string, unknown>;
  for (const key of ["text", "label", "name", "description", "title"]) {
    const v = c[key];
    if (typeof v === "string" && v.trim()) return v;
  }
  return "";
}

export function safeChoiceEffects(choice: unknown): Record<string, number> {
  if (!choice || typeof choice !== "object") return {};
  const c = choice as Record<string, unknown>;
  for (const key of ["success_effects", "effects", "outcome_effects"]) {
    const v = c[key];
    if (v && typeof v === "object") {
      const out: Record<string, number> = {};
      for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
        if (typeof val === "number") out[k] = val;
      }
      return out;
    }
  }
  return {};
}

const CHOICE_PATTERNS = [
  /\.choice_(\d+)_/, // event.choice_01_text
  /\.choice_(\d+)$/, // event.choice_01
  /\/c(\d+)$/, // event/c1
  /\/choice(\d+)$/, // event/choice1
  /:choice_?(\d+)$/, // event:choice1
  /:(\d+)$/, // event:1
  /_(\d+)$/, // event_1
];

export function choiceIndexFromId(
  choiceId: string,
  numChoices: number,
): number {
  if (!choiceId || numChoices <= 0) return -1;
  for (const pat of CHOICE_PATTERNS) {
    const match = new RegExp(pat.source).exec(choiceId);
    if (match) {
      const idx = parseInt(match[1], 10) - 1;
      if (idx >= 0 && idx < numChoices) return idx;
    }
  }
  return -1;
}

function choiceIndexFromRecord(
  week: DecisionGraphWeeklyEntry,
  numChoices: number,
): number {
  if (typeof week.choice_index === "number" && week.choice_index >= 0) {
    return week.choice_index < numChoices ? week.choice_index : -1;
  }
  if (
    typeof week.choice_index === "number" &&
    week.choice_index < numChoices
  ) {
    return week.choice_index;
  }
  return choiceIndexFromId(week.event_choice_id ?? "", numChoices);
}

/* ------------------------------------------------------------ */
/* Layout                                                        */
/* ------------------------------------------------------------ */

const PLOT_WIDTH = 1280;
const PAD_LEFT = 130;
const PAD_RIGHT = 60;
const PAD_TOP = 80;
const PAD_BOTTOM = 60;
const LANE_BAND = 130;
const MIN_HEIGHT = 320;

export function computeLayout(
  events: DecisionGraphEvent[],
  maxWeek: number,
  width: number = PLOT_WIDTH,
): GraphLayout {
  // Bucket by lane name.
  const byLane = new Map<string, DecisionGraphEvent[]>();
  for (const ev of events) {
    const lane = laneFor(ev);
    if (!byLane.has(lane)) byLane.set(lane, []);
    byLane.get(lane)!.push(ev);
  }

  // Sort lanes by frequency desc, then name asc.
  const laneOrder = Array.from(byLane.keys()).sort((a, b) => {
    const ac = byLane.get(a)!.length;
    const bc = byLane.get(b)!.length;
    if (ac !== bc) return bc - ac;
    return a < b ? -1 : a > b ? 1 : 0;
  });

  // Auto-size canvas.
  const nLanes = Math.max(laneOrder.length, 1);
  const height = Math.max(
    PAD_TOP + PAD_BOTTOM + LANE_BAND * nLanes,
    MIN_HEIGHT,
  );
  const plotW = width - PAD_LEFT - PAD_RIGHT;
  const plotH = height - PAD_TOP - PAD_BOTTOM;

  // Lane y anchors.
  const laneY: Record<string, number> = {};
  laneOrder.forEach((lane, idx) => {
    if (nLanes === 1) {
      laneY[lane] = PAD_TOP + plotH / 2;
    } else {
      laneY[lane] = PAD_TOP + ((idx + 0.5) * plotH) / nLanes;
    }
  });

  // Index events.
  const eventIndex: Record<string, DecisionGraphEvent> = {};
  for (const ev of events) {
    if (ev.id) eventIndex[ev.id] = ev;
  }

  // Compute positions.
  const positions: Record<string, [number, number]> = {};
  for (const [lane, laneEvents] of byLane) {
    const anchorY = laneY[lane];
    laneEvents.forEach((ev, idx) => {
      if (!ev.id) return;
      const week = triggerWeek(ev.trigger);
      let x: number;
      if (week !== null) {
        x = PAD_LEFT + (week / maxWeek) * plotW;
      } else {
        const order = typeof ev.source_order === "number" ? ev.source_order : idx;
        x = PAD_LEFT + (order / Math.max(laneEvents.length, 1)) * plotW;
      }
      const order = typeof ev.source_order === "number" ? ev.source_order : 0;
      const offset = ((order % 7) - 3) * 8;
      positions[ev.id] = [x, anchorY + offset];
    });
  }

  return {
    width,
    height,
    maxWeek,
    positions,
    laneY,
    laneOrder,
    events,
    eventIndex,
  };
}

/* ------------------------------------------------------------ */
/* Decision-graph payload (mirrors _decision_graph_payload)     */
/* ------------------------------------------------------------ */

export function computeGraph(
  manifest: DecisionGraphManifest,
): ComputedGraph {
  const diagnostics: string[] = [];
  let maxWeek = Number(manifest.max_weeks) || 20;
  const log = manifest.run?.weekly_log ?? [];
  const observedMax = log.reduce((acc, w) => {
    const weekNo = Number(w.week ?? 0);
    return weekNo > acc ? weekNo : acc;
  }, 0);
  if (observedMax > maxWeek) maxWeek = observedMax;

  const layout = computeLayout(
    manifest.event_graph?.events ?? [],
    maxWeek,
  );

  const triggered: TriggeredStep[] = [];
  for (const week of log) {
    if (!week || typeof week !== "object") {
      diagnostics.push(`Skipped non-object weekly_log entry`);
      continue;
    }
    const evId =
  week.triggered_event_id ??
  week.event_id ??
  ((week as unknown as Record<string, unknown>).event as string | undefined) ??
  "";
    if (!evId) continue;
    const ev = layout.eventIndex[evId];
    if (!ev) {
      diagnostics.push(
        `Triggered event "${evId}" not found in event_graph.json — skipped`,
      );
      continue;
    }
    const choices = ev.choices ?? [];
    const ci = choiceIndexFromRecord(week, choices.length);
    if (ci === -1 && week.event_choice_id) {
      diagnostics.push(
        `Could not parse choice_index from "${week.event_choice_id}" for ${evId} (choices=${choices.length})`,
      );
    }
    const choice = ci >= 0 && ci < choices.length ? choices[ci] : null;
    const pos = layout.positions[evId] ?? [0, 0];
    triggered.push({
      week: Number(week.week ?? 0),
      event_id: evId,
      title: ev.title ?? "",
      body: ev.body ?? "",
      event_type: laneFor(ev),
      choice_index: ci,
      choice_id: week.event_choice_id ?? "",
      choice_text: safeChoiceText(choice),
      choice_effects: safeChoiceEffects(choice),
      selected_actions: (week.selected_action_ids ?? week.actions ?? []).map(
        (a) => String(a),
      ),
      after_state:
        (week.after_state as Record<string, unknown> | undefined) ?? {},
      x: pos[0],
      y: pos[1],
    });
  }

  return {
    layout,
    events: triggered,
    diagnostics,
    laneOrder: layout.laneOrder,
    maxWeek,
  };
}