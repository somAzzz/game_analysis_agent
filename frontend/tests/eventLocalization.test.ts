import { describe, expect, it } from "vitest";
import { localizedChoice } from "@/lib/eventLocalization";
import type { PlaythroughChoice } from "@/types";

function retainedChoice(
  choiceId: string,
  textEn: string,
  textZh: string,
): PlaythroughChoice {
  return {
    choice_id: choiceId,
    text: textEn,
    text_en: textEn,
    text_zh: textZh,
    requirements: {},
    success_rate: 1,
    success_effects: {},
    failure_effects: {},
    set_flag: "",
    next_event_id: "",
  };
}

describe("event choice localization", () => {
  it("uses stable Chinese source identity ahead of stale retained English copy", () => {
    const parentLoan = retainedChoice(
      "desperate_illegal_work_offer.choice_03_take_the_cash_job",
      "Take the cash job",
      "向同学或父母借钱",
    );
    const cashJob = retainedChoice(
      "desperate_illegal_work_offer.choice_04_use_food_banks/cheap_canteens",
      "Use food banks/cheap canteens",
      "接下现金黑工",
    );
    const foodBank = retainedChoice(
      "desperate_illegal_work_offer.choice_05_去食物救助/低价食堂",
      "去食物救助/低价食堂",
      "去食物救助/低价食堂",
    );

    expect(localizedChoice("desperate_illegal_work_offer", parentLoan, "en")).toBe(
      "Borrow from classmates or your parents",
    );
    expect(localizedChoice("desperate_illegal_work_offer", cashJob, "en")).toBe(
      "Take the cash-in-hand job",
    );
    expect(localizedChoice("desperate_illegal_work_offer", foodBank, "en")).toBe(
      "Use a food bank or a subsidized canteen",
    );
  });

  it("shows the restored semester-fee borrowing translation", () => {
    const semesterLoan = retainedChoice(
      "semester_fee_due.choice_03_handle_prudently",
      "Handle prudently",
      "找朋友周转学期费",
    );

    expect(localizedChoice("semester_fee_due", semesterLoan, "en")).toBe(
      "Ask a friend to cover the semester contribution",
    );
  });
});
