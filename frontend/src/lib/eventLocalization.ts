import catalogValue from "../../../game-overlays/study-in-germany/data/localization/events.json";
import type { PlaythroughChoice } from "@/types";

export type EventLocale = "en" | "zh";

type LocalizedField = Record<EventLocale, string>;
type EventCopy = {
  title: LocalizedField;
  body: LocalizedField;
  choices: LocalizedField[];
};
type EventCatalog = {
  default_locale: EventLocale;
  events: Record<string, EventCopy>;
};

const catalog = catalogValue as EventCatalog;
const CHOICE_INDEX = /\.choice_(\d+)_/;

export const DEFAULT_EVENT_LOCALE: EventLocale = catalog.default_locale;

export function localizedEvent(eventId: string, locale: EventLocale): {
  title: string;
  body: string;
} {
  const copy = catalog.events[eventId];
  return {
    title: copy?.title[locale] ?? humanizeEventId(eventId),
    body: copy?.body[locale] ?? "",
  };
}

export function localizedChoice(
  eventId: string,
  choice: PlaythroughChoice | undefined,
  locale: EventLocale,
): string {
  if (!choice) return locale === "en" ? "No event choice" : "没有事件选项";
  const sourceText = choice.text_zh ?? choice.text;
  const sourceMatch = catalog.events[eventId]?.choices.find(
    (item) => item.zh === sourceText,
  );
  if (sourceMatch?.[locale]) return sourceMatch[locale];
  const direct = locale === "en" ? choice.text_en : choice.text_zh;
  if (direct) return direct;
  const match = CHOICE_INDEX.exec(choice.choice_id);
  const index = match ? Number(match[1]) - 1 : -1;
  return catalog.events[eventId]?.choices[index]?.[locale] ?? sourceText;
}

function humanizeEventId(eventId: string): string {
  return eventId
    .split("_")
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}
