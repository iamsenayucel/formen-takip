import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { Route, Routes } from "react-router-dom";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import type { CursorPage, FilterOptionsResponse, PlantListItem } from "../api/types";
import { renderWithProviders } from "../test/renderWithProviders";
import { PlantsPage } from "./PlantsPage";

const FILTER_OPTIONS: FilterOptionsResponse = {
  factories: [{ id: "f1", code: "K1", name: "K1", location: "Karaman" }],
  plants: [{ id: "p1", code: "1", name: "1. Tesis", sequenceNumber: 1, factoryId: "f1" }],
  chiefs: [],
  shifts: [],
  kpis: [],
};

function plant(overrides: Partial<PlantListItem> = {}): PlantListItem {
  return {
    id: "p1",
    code: "1",
    name: "1. Tesis",
    sequenceNumber: 1,
    factory: { id: "f1", code: "K1", name: "K1" },
    isActive: true,
    totalScore: 87.4,
    level: { name: "Hedefte", description: "", color: "#16a34a", icon: "check-circle" },
    activeForemanCount: 4,
    recordCount: 120,
    group: null,
    ...overrides,
  };
}

function page(items: PlantListItem[]): CursorPage<PlantListItem> {
  return { items, pagination: { nextCursor: null, hasMore: false, total: items.length } };
}

const filterOptionsHandler = http.get("/api/v1/meta/filters", () => HttpResponse.json({ data: FILTER_OPTIONS }));
const emptyForemenHandler = http.get("/api/v1/foremen", () => HttpResponse.json({ data: [], pagination: { nextCursor: null, hasMore: false, total: 0 } }));

function plantsHandler(items: PlantListItem[], onRequest?: (url: URL) => void) {
  return http.get("/api/v1/plants", ({ request }) => {
    onRequest?.(new URL(request.url));
    return HttpResponse.json(page(items));
  });
}

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderPlantsPage(extraHandlers: Parameters<typeof server.use> = []) {
  server.use(filterOptionsHandler, emptyForemenHandler, ...extraHandlers);
  return renderWithProviders(
    <Routes>
      <Route path="/plants" element={<PlantsPage />} />
      <Route path="/plants/:plantId" element={<div>Tesis Detayı Sayfası</div>} />
    </Routes>,
    { initialEntries: ["/plants"] }
  );
}

describe("PlantsPage — list states", () => {
  it("shows a loading state before data resolves, then the table", async () => {
    server.use(filterOptionsHandler, emptyForemenHandler, plantsHandler([plant()]));
    renderWithProviders(<PlantsPage />, { initialEntries: ["/plants"] });
    expect(screen.getByText("Yükleniyor...")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Yükleniyor...")).not.toBeInTheDocument());
    expect(screen.getByText("1. Tesis")).toBeInTheDocument();
  });

  it("renders plant rows with their score and performance level", async () => {
    renderPlantsPage([plantsHandler([plant({ name: "5. Tesis", totalScore: 92.1 })])]);
    expect(await screen.findByText("5. Tesis")).toBeInTheDocument();
    expect(screen.getByText("92.1")).toBeInTheDocument();
    expect(screen.getByText("Hedefte")).toBeInTheDocument();
  });

  it("shows an empty state when no plants match the filters", async () => {
    renderPlantsPage([plantsHandler([])]);
    expect(await screen.findByText("Seçilen filtrelerle eşleşen veri bulunamadı.")).toBeInTheDocument();
  });

  it("shows an error state when the request fails", async () => {
    renderPlantsPage([
      http.get("/api/v1/plants", () => HttpResponse.json({ error: { code: "INTERNAL", message: "boom" } }, { status: 500 })),
    ]);
    expect(await screen.findByText("Veri yüklenirken bir hata oluştu.")).toBeInTheDocument();
  });
});

describe("PlantsPage — sorting", () => {
  it("defaults to sorting by sequence ascending, and toggles direction on repeated clicks", async () => {
    const requestedParams: string[] = [];
    renderPlantsPage([
      plantsHandler([plant()], (url) => requestedParams.push(`${url.searchParams.get("sort_by")}:${url.searchParams.get("sort_dir")}`)),
    ]);
    await screen.findByText("1. Tesis");
    expect(requestedParams.at(-1)).toBe("sequence:asc");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Toplam Puan sütununa göre sırala/ }));
    await waitFor(() => expect(requestedParams.at(-1)).toBe("score:desc"));

    await user.click(screen.getByRole("button", { name: /Toplam Puan sütununa göre sırala/ }));
    await waitFor(() => expect(requestedParams.at(-1)).toBe("score:asc"));
  });
});

describe("PlantsPage — filter integration", () => {
  it("sends the FilterBar's selected plant as a plant_ids query param to the plants list request", async () => {
    const requestedPlantIds: (string | null)[] = [];
    renderPlantsPage([
      plantsHandler([plant()], (url) => requestedPlantIds.push(url.searchParams.get("plant_ids"))),
    ]);
    await screen.findByText("1. Tesis");
    expect(requestedPlantIds.at(-1)).toBeNull();

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Tesis" }));
    await user.click(screen.getByText("1. Tesis", { selector: "label span" }));

    await waitFor(() => expect(requestedPlantIds.at(-1)).toBe("p1"));
  });

  it("sends the free-text search box value as the 'search' query param", async () => {
    const requestedSearch: (string | null)[] = [];
    renderPlantsPage([
      plantsHandler([plant()], (url) => requestedSearch.push(url.searchParams.get("search"))),
    ]);
    await screen.findByText("1. Tesis");

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Tesis adı veya kodu ara..."), "GSF");

    await waitFor(() => expect(requestedSearch.at(-1)).toBe("GSF"));
  });
});

describe("PlantsPage — drill-down", () => {
  it("navigates to the plant detail route when a row is activated", async () => {
    renderPlantsPage([plantsHandler([plant()])]);
    await screen.findByText("1. Tesis");

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "1. Tesis detayına git" }));

    expect(await screen.findByText("Tesis Detayı Sayfası")).toBeInTheDocument();
  });
});
