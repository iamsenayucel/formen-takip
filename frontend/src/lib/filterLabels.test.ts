import { describe, expect, it } from "vitest";
import type { FilterState } from "../hooks/useFilters";
import { periodLabel, scopeLabel, scopeSegments, summarizeNames } from "./filterLabels";

function makeFilters(overrides: Partial<FilterState> = {}): FilterState {
  return {
    dateFrom: "2026-03-01",
    dateTo: "2026-03-15",
    plantIds: [],
    factoryIds: [],
    chiefIds: [],
    shiftIds: [],
    kpiIds: [],
    foremanIds: [],
    ...overrides,
  };
}

describe("periodLabel", () => {
  it("collapses a same-month range into a single 'Month Year' label", () => {
    expect(periodLabel(makeFilters({ dateFrom: "2026-03-01", dateTo: "2026-03-15" }))).toBe("Mart 2026");
  });

  it("uses a 'from – to year' label across months", () => {
    expect(periodLabel(makeFilters({ dateFrom: "2026-02-20", dateTo: "2026-03-10" }))).toBe("20 Şub – 10 Mar 2026");
  });
});

describe("scopeLabel", () => {
  it("labels a single selected plant", () => {
    expect(scopeLabel(makeFilters({ plantIds: ["p1"] }))).toBe("1 Tesis");
  });

  it("labels multiple selected plants with a count", () => {
    expect(scopeLabel(makeFilters({ plantIds: ["p1", "p2"] }))).toBe("2 Tesis");
  });

  it("falls back to factory count when no plant is selected", () => {
    expect(scopeLabel(makeFilters({ factoryIds: ["f1"] }))).toBe("1 Fabrika");
    expect(scopeLabel(makeFilters({ factoryIds: ["f1", "f2"] }))).toBe("2 Fabrika");
  });

  it("prefers plant scope over factory scope when both are present", () => {
    expect(scopeLabel(makeFilters({ plantIds: ["p1"], factoryIds: ["f1", "f2"] }))).toBe("1 Tesis");
  });

  it("falls back to 'Tüm Tesisler' when nothing is selected", () => {
    expect(scopeLabel(makeFilters())).toBe("Tüm Tesisler");
  });
});

describe("summarizeNames", () => {
  it("joins names under the max count", () => {
    expect(summarizeNames(["A", "B"])).toBe("A, B");
  });

  it("truncates with a '+N' suffix beyond the max count", () => {
    expect(summarizeNames(["A", "B", "C", "D"])).toBe("A, B +2");
  });

  it("respects a custom max", () => {
    expect(summarizeNames(["A", "B", "C"], 1)).toBe("A +2");
  });

  it("returns an empty string for an empty list", () => {
    expect(summarizeNames([])).toBe("");
  });
});

describe("scopeSegments", () => {
  it("returns ['Tüm Tesisler'] when no factory/plant filter is set", () => {
    expect(scopeSegments(makeFilters(), new Map(), new Map())).toEqual(["Tüm Tesisler"]);
  });

  it("resolves factory and plant ids to real names when the maps are populated", () => {
    const factoryNameById = new Map([["f1", "K1"]]);
    const plantNameById = new Map([["p1", "1. Tesis"]]);
    expect(
      scopeSegments(makeFilters({ factoryIds: ["f1"], plantIds: ["p1"] }), factoryNameById, plantNameById)
    ).toEqual(["K1", "1. Tesis"]);
  });

  it("falls back to a count label when ids are selected but names are not loaded yet", () => {
    expect(scopeSegments(makeFilters({ factoryIds: ["f1", "f2"] }), new Map(), new Map())).toEqual(["2 Fabrika"]);
  });

  it("silently drops ids that have no matching name instead of showing a raw id", () => {
    const plantNameById = new Map([["p1", "1. Tesis"]]);
    expect(scopeSegments(makeFilters({ plantIds: ["p1", "unknown-id"] }), new Map(), plantNameById)).toEqual([
      "1. Tesis",
    ]);
  });
});
