import { describe, expect, it } from "vitest";
import {
  computeChange,
  computeMonthlyTotal,
  computeTimeSaving,
  durationToMinutes,
  formatMinutes,
  formatMoney,
  formatPercent,
} from "./contributionCalc";

describe("durationToMinutes", () => {
  it("converts seconds to minutes", () => {
    expect(durationToMinutes(120, "second")).toBe(2);
  });

  it("converts hours to minutes", () => {
    expect(durationToMinutes(1.5, "hour")).toBe(90);
  });

  it("passes minutes through unchanged", () => {
    expect(durationToMinutes(45, "minute")).toBe(45);
  });

  it("returns null when value is null/undefined", () => {
    expect(durationToMinutes(null, "minute")).toBeNull();
    expect(durationToMinutes(undefined, "minute")).toBeNull();
  });

  it("returns null when unit is missing", () => {
    expect(durationToMinutes(10, null)).toBeNull();
    expect(durationToMinutes(10, undefined)).toBeNull();
  });

  it("returns 0 for a zero value", () => {
    expect(durationToMinutes(0, "hour")).toBe(0);
  });
});

describe("computeTimeSaving", () => {
  it("returns the positive difference when the new duration is shorter", () => {
    expect(computeTimeSaving(100, 60)).toBe(40);
  });

  it("returns null when the new duration is equal to the previous one (no saving)", () => {
    expect(computeTimeSaving(60, 60)).toBeNull();
  });

  it("returns null when the new duration is longer (regression, not a saving)", () => {
    expect(computeTimeSaving(60, 90)).toBeNull();
  });

  it("returns null when either input is missing", () => {
    expect(computeTimeSaving(null, 60)).toBeNull();
    expect(computeTimeSaving(60, undefined)).toBeNull();
  });

  it("rounds to 2 decimals", () => {
    expect(computeTimeSaving(10.005, 3.001)).toBe(7);
  });
});

describe("computeMonthlyTotal", () => {
  it("multiplies per-occurrence minutes by repeat count and monthly occurrence rate", () => {
    expect(computeMonthlyTotal(10, "monthly", 1)).toBe(10);
  });

  it("uses the daily occurrence approximation (30/month)", () => {
    expect(computeMonthlyTotal(2, "daily", 1)).toBe(60);
  });

  it("uses the weekly occurrence approximation (4.345/month)", () => {
    expect(computeMonthlyTotal(10, "weekly", 1)).toBeCloseTo(43.45, 2);
  });

  it("returns null when any required input is missing", () => {
    expect(computeMonthlyTotal(null, "monthly", 1)).toBeNull();
    expect(computeMonthlyTotal(10, null, 1)).toBeNull();
    expect(computeMonthlyTotal(10, "monthly", null)).toBeNull();
  });

  it("returns 0 when repeatCount is 0", () => {
    expect(computeMonthlyTotal(10, "monthly", 0)).toBe(0);
  });
});

describe("computeChange", () => {
  it("computes absolute and percent change for a positive move", () => {
    expect(computeChange(100, 120)).toEqual({ amount: 20, percent: 20 });
  });

  it("computes a negative percent change", () => {
    expect(computeChange(100, 80)).toEqual({ amount: -20, percent: -20 });
  });

  it("returns a null percent when the previous value is zero (division by zero guard)", () => {
    expect(computeChange(0, 50)).toEqual({ amount: 50, percent: null });
  });

  it("returns nulls when either input is missing", () => {
    expect(computeChange(null, 50)).toEqual({ amount: null, percent: null });
    expect(computeChange(50, undefined)).toEqual({ amount: null, percent: null });
  });

  it("computes percent relative to the magnitude of a negative previous value", () => {
    expect(computeChange(-50, -25)).toEqual({ amount: 25, percent: 50 });
  });
});

describe("formatMoney", () => {
  it("formats with a currency suffix", () => {
    expect(formatMoney(1234.5, "TRY")).toBe("1.234,5 TRY");
  });

  it("formats without a currency suffix when currency is missing", () => {
    expect(formatMoney(1234.5, null)).toBe("1.234,5");
  });

  it("renders a dash for null/undefined values", () => {
    expect(formatMoney(null, "TRY")).toBe("-");
    expect(formatMoney(undefined, "TRY")).toBe("-");
  });

  it("formats zero as a real value, not a dash", () => {
    expect(formatMoney(0, "TRY")).toBe("0 TRY");
  });

  it("formats negative values", () => {
    expect(formatMoney(-500, "USD")).toBe("-500 USD");
  });
});

describe("formatPercent", () => {
  it("prefixes with % and takes the absolute value", () => {
    expect(formatPercent(-12.345)).toBe("%12,35");
    expect(formatPercent(12.345)).toBe("%12,35");
  });

  it("renders a dash for null/undefined", () => {
    expect(formatPercent(null)).toBe("-");
    expect(formatPercent(undefined)).toBe("-");
  });
});

describe("formatMinutes", () => {
  it("appends the Turkish 'dakika' unit", () => {
    expect(formatMinutes(12.3)).toBe("12,3 dakika");
  });

  it("renders a dash for null/undefined", () => {
    expect(formatMinutes(null)).toBe("-");
    expect(formatMinutes(undefined)).toBe("-");
  });
});
