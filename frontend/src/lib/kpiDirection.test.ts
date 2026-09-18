import { describe, expect, it } from "vitest";
import {
  formatPct,
  formatSignedPct,
  isHigherBetter,
  performanceDirection,
  targetDeviationSeverity,
} from "./kpiDirection";

describe("isHigherBetter", () => {
  it("returns true for 'high'", () => {
    expect(isHigherBetter("high")).toBe(true);
  });

  it("returns false for 'low'", () => {
    expect(isHigherBetter("low")).toBe(false);
  });

  it("returns null for an unknown/null direction", () => {
    expect(isHigherBetter(null)).toBeNull();
  });
});

describe("performanceDirection", () => {
  it("is 'improved' when a higher-is-better KPI moves positively", () => {
    expect(performanceDirection("high", true)).toBe("improved");
  });

  it("is 'worsened' when a higher-is-better KPI moves negatively", () => {
    expect(performanceDirection("high", false)).toBe("worsened");
  });

  it("is 'improved' when a lower-is-better KPI moves negatively", () => {
    expect(performanceDirection("low", false)).toBe("improved");
  });

  it("is 'worsened' when a lower-is-better KPI moves positively", () => {
    expect(performanceDirection("low", true)).toBe("worsened");
  });

  it("is 'unknown' when direction is null", () => {
    expect(performanceDirection(null, true)).toBe("unknown");
  });
});

describe("formatSignedPct / formatPct", () => {
  it("prefixes a positive value with +%", () => {
    expect(formatSignedPct(5.5)).toBe("+%5.5");
  });

  it("does not prefix a negative value (native minus)", () => {
    expect(formatSignedPct(-5.5)).toBe("%-5.5");
  });

  it("does not prefix zero", () => {
    expect(formatSignedPct(0)).toBe("%0.0");
  });

  it("formats an unsigned percent with default 2 decimals", () => {
    expect(formatPct(12.3456)).toBe("%12.35");
  });
});

describe("targetDeviationSeverity", () => {
  it("returns unknown when direction is null", () => {
    expect(targetDeviationSeverity(90, 100, null)).toBe("unknown");
  });

  it("returns unknown when target is null or zero", () => {
    expect(targetDeviationSeverity(90, null, "high")).toBe("unknown");
    expect(targetDeviationSeverity(90, 0, "high")).toBe("unknown");
  });

  it("is 'normal' when a higher-is-better value is at or above target", () => {
    expect(targetDeviationSeverity(100, 100, "high")).toBe("normal");
    expect(targetDeviationSeverity(110, 100, "high")).toBe("normal");
  });

  it("is 'warning' for a higher-is-better value moderately below target", () => {
    // 100 -> 93: 7% below target, between default warningPct=5 and criticalPct=15
    expect(targetDeviationSeverity(93, 100, "high")).toBe("warning");
  });

  it("is 'critical' for a higher-is-better value far below target", () => {
    expect(targetDeviationSeverity(80, 100, "high")).toBe("critical");
  });

  it("is 'normal' when a lower-is-better value is at or below target", () => {
    expect(targetDeviationSeverity(100, 100, "low")).toBe("normal");
    expect(targetDeviationSeverity(90, 100, "low")).toBe("normal");
  });

  it("is 'critical' for a lower-is-better value far above target", () => {
    expect(targetDeviationSeverity(120, 100, "low")).toBe("critical");
  });

  it("respects custom warning/critical thresholds", () => {
    // 100 -> 92: 8% below target — below a widened 10% warning threshold -> normal
    expect(targetDeviationSeverity(92, 100, "high", 10, 20)).toBe("normal");
  });

  it("treats the boundary values as inclusive", () => {
    expect(targetDeviationSeverity(95, 100, "high", 5, 15)).toBe("warning");
    expect(targetDeviationSeverity(85, 100, "high", 5, 15)).toBe("critical");
  });
});
