import { describe, expect, it } from "vitest";
import { previousPeriodParams } from "./period";

describe("previousPeriodParams", () => {
  it("shifts a multi-day range back by its own length, immediately preceding it", () => {
    // 2026-03-10..2026-03-15 is a 6-day period; the previous period should be
    // the 6 days immediately before it, i.e. ending the day before date_from.
    expect(previousPeriodParams({ date_from: "2026-03-10", date_to: "2026-03-15" })).toEqual({
      date_from: "2026-03-04",
      date_to: "2026-03-09",
    });
  });

  it("shifts a single-day range back by exactly one day", () => {
    expect(previousPeriodParams({ date_from: "2026-03-10", date_to: "2026-03-10" })).toEqual({
      date_from: "2026-03-09",
      date_to: "2026-03-09",
    });
  });

  it("crosses a month boundary correctly", () => {
    expect(previousPeriodParams({ date_from: "2026-03-01", date_to: "2026-03-05" })).toEqual({
      date_from: "2026-02-24",
      date_to: "2026-02-28",
    });
  });

  it("crosses a year boundary correctly", () => {
    expect(previousPeriodParams({ date_from: "2026-01-01", date_to: "2026-01-03" })).toEqual({
      date_from: "2025-12-29",
      date_to: "2025-12-31",
    });
  });

  it("preserves any extra fields on the input object", () => {
    const result = previousPeriodParams({ date_from: "2026-03-10", date_to: "2026-03-10", plant_ids: "p1" });
    expect(result.plant_ids).toBe("p1");
  });

  it("is unaffected by the local machine's timezone (pure UTC calendar math)", () => {
    // Leap day: Feb 2028 is a leap year, so Feb 29 exists — the day before is Feb 28.
    expect(previousPeriodParams({ date_from: "2028-03-01", date_to: "2028-03-01" })).toEqual({
      date_from: "2028-02-29",
      date_to: "2028-02-29",
    });
  });
});
