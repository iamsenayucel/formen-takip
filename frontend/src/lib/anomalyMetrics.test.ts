import { describe, expect, it } from "vitest";
import type { AnomalyListItem } from "../api/types";
import {
  changeWord,
  formatMetricValue,
  formatSignedUnitDiff,
  magnitudeWord,
  primaryDelta,
  rankAnomaliesByPriority,
  unitDiffSuffix,
} from "./anomalyMetrics";

function anomaly(overrides: Partial<AnomalyListItem>): AnomalyListItem {
  return {
    id: overrides.id ?? "a1",
    severity: "medium",
    status: "new",
    deviationPercent: 0,
    ...overrides,
  } as AnomalyListItem;
}

describe("rankAnomaliesByPriority", () => {
  it("filters out anomalies that are not in an open status", () => {
    const items = [
      anomaly({ id: "resolved", status: "resolved" as AnomalyListItem["status"], severity: "critical" }),
      anomaly({ id: "open", status: "new" }),
    ];
    expect(rankAnomaliesByPriority(items).map((a) => a.id)).toEqual(["open"]);
  });

  it("sorts by severity rank first (critical > high > medium > low)", () => {
    const items = [
      anomaly({ id: "low", severity: "low", status: "new" }),
      anomaly({ id: "critical", severity: "critical", status: "new" }),
      anomaly({ id: "medium", severity: "medium", status: "new" }),
      anomaly({ id: "high", severity: "high", status: "in_review" }),
    ];
    expect(rankAnomaliesByPriority(items).map((a) => a.id)).toEqual(["critical", "high", "medium", "low"]);
  });

  it("breaks ties within the same severity by absolute deviation magnitude", () => {
    const items = [
      anomaly({ id: "small", severity: "high", deviationPercent: -5, status: "new" }),
      anomaly({ id: "large", severity: "high", deviationPercent: 30, status: "action_pending" }),
    ];
    expect(rankAnomaliesByPriority(items).map((a) => a.id)).toEqual(["large", "small"]);
  });

  it("does not mutate the input array", () => {
    const items = [anomaly({ id: "a", status: "new" }), anomaly({ id: "b", status: "new" })];
    const copy = [...items];
    rankAnomaliesByPriority(items);
    expect(items).toEqual(copy);
  });

  it("returns an empty array when nothing is open", () => {
    const items = [anomaly({ id: "resolved", status: "resolved" as AnomalyListItem["status"] })];
    expect(rankAnomaliesByPriority(items)).toEqual([]);
  });
});

describe("primaryDelta", () => {
  it("computes absolute and percent difference", () => {
    expect(primaryDelta(120, 100)).toEqual({ absDiff: 20, pctDiff: 20 });
  });

  it("returns a null pctDiff when the reference is zero (division by zero guard)", () => {
    expect(primaryDelta(50, 0)).toEqual({ absDiff: 50, pctDiff: null });
  });

  it("handles a negative reference using its magnitude for the percent base", () => {
    expect(primaryDelta(-40, -50)).toEqual({ absDiff: 10, pctDiff: 20 });
  });
});

describe("formatMetricValue / unitDiffSuffix / formatSignedUnitDiff", () => {
  it("prefixes % values with %", () => {
    expect(formatMetricValue(12.345, "%", 2)).toBe("%12.35");
  });

  it("appends a unit for non-% values", () => {
    expect(formatMetricValue(12.345, "adet", 1)).toBe("12.3 adet");
  });

  it("translates % into 'yüzde puan' for a diff suffix, passes other units through", () => {
    expect(unitDiffSuffix("%")).toBe("yüzde puan");
    expect(unitDiffSuffix("adet")).toBe("adet");
  });

  it("signs a positive diff and appends the diff suffix", () => {
    expect(formatSignedUnitDiff(3.2, "%", 1)).toBe("+3.2 yüzde puan");
  });

  it("does not sign a negative diff", () => {
    expect(formatSignedUnitDiff(-3.2, "adet", 1)).toBe("-3.2 adet");
  });
});

describe("magnitudeWord / changeWord", () => {
  it("labels a negative value as 'düşük'/'Düşüş'", () => {
    expect(magnitudeWord(-1)).toBe("düşük");
    expect(changeWord(-1)).toBe("Düşüş");
  });

  it("labels a non-negative value as 'yüksek'/'Artış'", () => {
    expect(magnitudeWord(1)).toBe("yüksek");
    expect(changeWord(1)).toBe("Artış");
    expect(magnitudeWord(0)).toBe("yüksek");
    expect(changeWord(0)).toBe("Artış");
  });
});
