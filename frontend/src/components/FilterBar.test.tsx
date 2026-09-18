import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { FilterOptionsResponse } from "../api/types";
import type { FilterState } from "../hooks/useFilters";
import { FilterBar } from "./FilterBar";

const { useFilterOptionsMock, useForemenMock, useForemenByIdsMock } = vi.hoisted(() => ({
  useFilterOptionsMock: vi.fn(),
  useForemenMock: vi.fn(),
  useForemenByIdsMock: vi.fn(),
}));

vi.mock("../api/hooks", () => ({
  useFilterOptions: useFilterOptionsMock,
  useForemen: useForemenMock,
  useForemenByIds: useForemenByIdsMock,
}));

const OPTIONS: FilterOptionsResponse = {
  factories: [
    { id: "f1", code: "K1", name: "K1", location: "Karaman" },
    { id: "f2", code: "K2", name: "K2", location: "Karaman" },
  ],
  plants: [
    { id: "p1", code: "1", name: "1. Tesis", sequenceNumber: 1, factoryId: "f1" },
    { id: "p2", code: "28", name: "28. Tesis", sequenceNumber: 28, factoryId: "f2" },
  ],
  chiefs: [
    { id: "c1", employeeNumber: "SEF-001", name: "Şef Bir", plantIds: ["p1"] },
    { id: "c2", employeeNumber: "SEF-002", name: "Şef İki", plantIds: ["p2"] },
  ],
  shifts: [
    { id: "s1", code: "V1", name: "V1" },
    { id: "s2", code: "V2", name: "V2" },
  ],
  kpis: [{ id: "k1", code: "GSF", name: "GSF" }],
};

function baseFilters(overrides: Partial<FilterState> = {}): FilterState {
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

function setup(filters: FilterState, isLoading = false) {
  useFilterOptionsMock.mockReturnValue({ data: OPTIONS, isLoading });
  useForemenMock.mockReturnValue({ data: undefined });
  useForemenByIdsMock.mockReturnValue({ data: { items: [] } });
  const setFilters = vi.fn();
  const clearFilters = vi.fn();
  render(<FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />);
  return { setFilters, clearFilters };
}

describe("FilterBar active filter chips", () => {
  it("shows no removable chip besides the always-present date chip when nothing else is active", () => {
    setup(baseFilters());
    expect(screen.getByText(/Tarih:/)).toBeInTheDocument();
    expect(screen.queryByText(/^Tesis:/)).not.toBeInTheDocument();
  });

  it("shows a chip with the resolved plant name for an active plant filter", () => {
    setup(baseFilters({ plantIds: ["p1"] }));
    expect(screen.getByText("Tesis: 1. Tesis")).toBeInTheDocument();
  });

  it("removes only the targeted filter when a chip's remove button is clicked", async () => {
    const user = userEvent.setup();
    const { setFilters } = setup(baseFilters({ plantIds: ["p1"], kpiIds: ["k1"] }));
    await user.click(screen.getByRole("button", { name: "Tesis: 1. Tesis filtresini kaldır" }));
    // handlePlantChange always recomputes chiefIds alongside plantIds (it's
    // the same cascading-filter function the MultiSelect uses), even though
    // chiefIds is already empty here.
    expect(setFilters).toHaveBeenCalledWith({ plantIds: [], chiefIds: [] });
  });

  it("hides the clear-all button when no filter is active", () => {
    setup(baseFilters());
    expect(screen.queryByRole("button", { name: /Filtreleri temizle/ })).not.toBeInTheDocument();
  });

  it("shows the clear-all button with a count once filters are active", () => {
    setup(baseFilters({ plantIds: ["p1"], kpiIds: ["k1"] }));
    expect(screen.getByRole("button", { name: "Filtreleri temizle (2)" })).toBeInTheDocument();
  });

  it("calls clearFilters when the clear-all button is clicked", async () => {
    const user = userEvent.setup();
    const { clearFilters } = setup(baseFilters({ plantIds: ["p1"] }));
    await user.click(screen.getByRole("button", { name: "Filtreleri temizle (1)" }));
    expect(clearFilters).toHaveBeenCalledTimes(1);
  });
});

describe("FilterBar cascading factory -> plant -> chief", () => {
  it("drops plants and chiefs that fall outside a newly narrowed factory selection", async () => {
    const user = userEvent.setup();
    const { setFilters } = setup(baseFilters({ plantIds: ["p1", "p2"], chiefIds: ["c1", "c2"] }));
    await user.click(screen.getByRole("button", { name: "Fabrika" }));
    await user.click(screen.getByText("K1"));
    expect(setFilters).toHaveBeenCalledWith({
      factoryIds: ["f1"],
      plantIds: ["p1"],
      chiefIds: ["c1"],
    });
  });

  it("drops chiefs that fall outside a newly narrowed plant selection", async () => {
    const user = userEvent.setup();
    const { setFilters } = setup(baseFilters({ plantIds: ["p1", "p2"], chiefIds: ["c1", "c2"] }));
    await user.click(screen.getByRole("button", { name: "Tesis(2)" }));
    // Both plants start checked; clicking "1. Tesis" *unchecks* it, leaving
    // only p2 selected — and chiefIds narrows to whichever chief still
    // covers a remaining selected plant (c2, since c1 only covers p1).
    await user.click(screen.getByText("1. Tesis"));
    expect(setFilters).toHaveBeenCalledWith({
      plantIds: ["p2"],
      chiefIds: ["c2"],
    });
  });

  it("clearing the factory selection does not forcibly clear plants/chiefs (allowed=empty means unrestricted)", async () => {
    const user = userEvent.setup();
    const { setFilters } = setup(baseFilters({ factoryIds: ["f1"], plantIds: ["p1"] }));
    await user.click(screen.getByRole("button", { name: "Fabrika(1)" }));
    // Un-check the only selected factory.
    await user.click(screen.getByText("K1"));
    expect(setFilters).toHaveBeenCalledWith({
      factoryIds: [],
      plantIds: ["p1"],
      chiefIds: [],
    });
  });
});

describe("FilterBar loading state", () => {
  it("disables the Fabrika/Tesis selects while filter options are loading", () => {
    setup(baseFilters(), true);
    expect(screen.getByRole("button", { name: "Fabrika" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Tesis" })).toBeDisabled();
  });
});
