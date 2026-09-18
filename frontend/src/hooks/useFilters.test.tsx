import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DATE_PRESETS, useFilters } from "./useFilters";

function wrapper(initialEntries: string[]) {
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
  );
}

describe("useFilters", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-15T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("falls back to the last-30-days range (relative to the current time) when no query params are present", () => {
    const { result } = renderHook(() => useFilters(), { wrapper: wrapper(["/"]) });
    // 2026-03-15 (faked "today", Europe/Istanbul) minus 30 days.
    expect(result.current.filters.dateFrom).toBe("2026-02-13");
    expect(result.current.filters.dateTo).toBe("2026-03-15");
    expect(result.current.filters.plantIds).toEqual([]);
  });

  it("recomputes the no-params default against the *current* time on a fresh mount, not a value frozen at module load", () => {
    const first = renderHook(() => useFilters(), { wrapper: wrapper(["/"]) });
    expect(first.result.current.filters).toMatchObject({ dateFrom: "2026-02-13", dateTo: "2026-03-15" });
    first.unmount();

    vi.setSystemTime(new Date("2026-04-20T12:00:00Z"));

    const second = renderHook(() => useFilters(), { wrapper: wrapper(["/"]) });
    expect(second.result.current.filters).toMatchObject({ dateFrom: "2026-03-21", dateTo: "2026-04-20" });
  });

  it("restores filter state from existing URL search params", () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: wrapper(["/?date_from=2026-01-01&date_to=2026-01-31&plant_ids=p1,p2&factory_ids=f1&shift_ids=s1"]),
    });
    expect(result.current.filters).toMatchObject({
      dateFrom: "2026-01-01",
      dateTo: "2026-01-31",
      plantIds: ["p1", "p2"],
      factoryIds: ["f1"],
      shiftIds: ["s1"],
      chiefIds: [],
      kpiIds: [],
      foremanIds: [],
    });
  });

  it("ignores an empty query param instead of producing a [''] array", () => {
    const { result } = renderHook(() => useFilters(), { wrapper: wrapper(["/?plant_ids="]) });
    expect(result.current.filters.plantIds).toEqual([]);
  });

  it("writes a partial filter update into the correct query param names", () => {
    const { result } = renderHook(() => useFilters(), { wrapper: wrapper(["/"]) });
    act(() => {
      result.current.setFilters({ plantIds: ["p1", "p2"], chiefIds: ["c1"] });
    });
    expect(result.current.filters.plantIds).toEqual(["p1", "p2"]);
    expect(result.current.filters.chiefIds).toEqual(["c1"]);
  });

  it("deletes a query param entirely when the list is cleared (not an empty string param)", () => {
    const { result } = renderHook(() => useFilters(), { wrapper: wrapper(["/?plant_ids=p1"]) });
    act(() => {
      result.current.setFilters({ plantIds: [] });
    });
    expect(result.current.filters.plantIds).toEqual([]);
    expect(result.current.asQueryParams.plant_ids).toBeUndefined();
  });

  it("resets all filters back to defaults on clearFilters", () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: wrapper(["/?plant_ids=p1&factory_ids=f1&kpi_ids=k1"]),
    });
    act(() => {
      result.current.clearFilters();
    });
    expect(result.current.filters.plantIds).toEqual([]);
    expect(result.current.filters.factoryIds).toEqual([]);
    expect(result.current.filters.kpiIds).toEqual([]);
    expect(result.current.filters.dateFrom).toBe("2026-02-13");
    expect(result.current.filters.dateTo).toBe("2026-03-15");
  });

  it("serializes list filters as comma-joined query params, omitting empty ones", () => {
    const { result } = renderHook(() => useFilters(), {
      wrapper: wrapper(["/?plant_ids=p1,p2&kpi_ids=k1"]),
    });
    expect(result.current.asQueryParams).toMatchObject({
      plant_ids: "p1,p2",
      kpi_ids: "k1",
      factory_ids: undefined,
      chief_ids: undefined,
      shift_ids: undefined,
      foreman_ids: undefined,
    });
  });

  it("always includes date_from/date_to in asQueryParams, matching the resolved filter state", () => {
    const { result } = renderHook(() => useFilters(), { wrapper: wrapper(["/"]) });
    expect(result.current.asQueryParams.date_from).toBe(result.current.filters.dateFrom);
    expect(result.current.asQueryParams.date_to).toBe(result.current.filters.dateTo);
  });
});

describe("DATE_PRESETS", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-03-15T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("'Bugün' returns today for both endpoints", () => {
    const preset = DATE_PRESETS.find((p) => p.label === "Bugün")!;
    expect(preset.getRange()).toEqual(["2026-03-15", "2026-03-15"]);
  });

  it("'Dün' returns yesterday for both endpoints", () => {
    const preset = DATE_PRESETS.find((p) => p.label === "Dün")!;
    expect(preset.getRange()).toEqual(["2026-03-14", "2026-03-14"]);
  });

  it("'Son 7 Gün' spans 7 days ending today", () => {
    const preset = DATE_PRESETS.find((p) => p.label === "Son 7 Gün")!;
    expect(preset.getRange()).toEqual(["2026-03-08", "2026-03-15"]);
  });

  it("'Bu Yıl' starts on Jan 1st of the current year", () => {
    const preset = DATE_PRESETS.find((p) => p.label === "Bu Yıl")!;
    expect(preset.getRange()).toEqual(["2026-01-01", "2026-03-15"]);
  });
});
