import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { Route, Routes } from "react-router-dom";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import type { AnomalyListItem, AnomalySummary, CursorPage, FilterOptionsResponse } from "../api/types";
import { renderWithProviders } from "../test/renderWithProviders";
import { AnomaliesPage } from "./AnomaliesPage";

const FILTER_OPTIONS: FilterOptionsResponse = {
  factories: [{ id: "f1", code: "K1", name: "K1", location: "Karaman" }],
  plants: [{ id: "p1", code: "1", name: "1. Tesis", sequenceNumber: 1, factoryId: "f1" }],
  chiefs: [],
  shifts: [{ id: "s1", code: "V1", name: "V1" }],
  kpis: [{ id: "k1", code: "GSF", name: "GSF" }],
};

const SUMMARY: AnomalySummary = {
  totalActive: 12,
  criticalCount: 2,
  highCount: 4,
  pendingAnalysisCount: 3,
  openedLast7Days: 5,
  resolvedCount: 20,
};

function anomaly(overrides: Partial<AnomalyListItem> = {}): AnomalyListItem {
  return {
    id: "a1",
    code: "ANM-001",
    title: "GSF sapması",
    factoryCode: "K1",
    factoryName: "K1",
    plantId: "p1",
    plantName: "1. Tesis",
    shiftId: "s1",
    shiftName: "V1",
    kpiId: "k1",
    kpiCode: "GSF",
    kpiName: "GSF Oranı",
    anomalyType: "deviation",
    anomalyTypeLabel: "Sapma",
    detectedAt: "2026-03-10T08:00:00Z",
    periodStart: "2026-03-01",
    periodEnd: "2026-03-10",
    deviationPercent: 12.5,
    mlConfidence: 0.87,
    severity: "high",
    severityLabel: "Yüksek",
    // "resolved" (a closed status) by default so a single-item fixture
    // renders in the table only, not also in the priority strip above it —
    // tests that specifically exercise the strip override this.
    status: "resolved",
    statusLabel: "Çözüldü",
    analysisStatus: "not_analyzed",
    analysisStatusLabel: "Analiz Edilmedi",
    ...overrides,
  };
}

function page(items: AnomalyListItem[]): CursorPage<AnomalyListItem> {
  return { items, pagination: { nextCursor: null, hasMore: false, total: items.length } };
}

const filterOptionsHandler = http.get("/api/v1/meta/filters", () => HttpResponse.json({ data: FILTER_OPTIONS }));
const summaryHandler = http.get("/api/v1/anomalies/summary", () => HttpResponse.json({ data: SUMMARY }));

function anomaliesHandler(items: AnomalyListItem[], onRequest?: (url: URL) => void) {
  return http.get("/api/v1/anomalies", ({ request }) => {
    onRequest?.(new URL(request.url));
    return HttpResponse.json(page(items));
  });
}

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderAnomaliesPage(extraHandlers: Parameters<typeof server.use> = []) {
  server.use(filterOptionsHandler, summaryHandler, ...extraHandlers);
  return renderWithProviders(
    <Routes>
      <Route path="/anomalies" element={<AnomaliesPage />} />
      <Route path="/anomalies/:anomalyId" element={<div>Tespit Detayı Sayfası</div>} />
    </Routes>,
    { initialEntries: ["/anomalies"] }
  );
}

describe("AnomaliesPage — summary and list states", () => {
  it("shows a loading state before the list resolves, then the table", async () => {
    server.use(filterOptionsHandler, summaryHandler, anomaliesHandler([anomaly()]));
    renderWithProviders(<AnomaliesPage />);
    expect(screen.getByText("Tespitler yükleniyor...")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Tespitler yükleniyor...")).not.toBeInTheDocument());
    expect(screen.getByText("GSF sapması")).toBeInTheDocument();
  });

  it("renders the summary tiles from /anomalies/summary", async () => {
    renderAnomaliesPage([anomaliesHandler([])]);
    expect(await screen.findByText("12")).toBeInTheDocument(); // totalActive
    expect(screen.getByText("Toplam Aktif Tespit")).toBeInTheDocument();
    // "Kritik" also appears as a <option> in the severity filter below, so
    // scope to the summary tile's own label element.
    expect(screen.getByText("Kritik", { selector: "p" })).toBeInTheDocument();
  });

  it("shows an empty state with a specific message when no anomalies match the filters", async () => {
    renderAnomaliesPage([anomaliesHandler([])]);
    expect(await screen.findByText("Seçilen filtrelerle eşleşen tespit bulunamadı.")).toBeInTheDocument();
  });

  it("shows an error state when the list request fails", async () => {
    renderAnomaliesPage([
      http.get("/api/v1/anomalies", () => HttpResponse.json({ error: { code: "INTERNAL", message: "boom" } }, { status: 500 })),
    ]);
    expect(await screen.findByText("Veri yüklenirken bir hata oluştu.")).toBeInTheDocument();
  });

  it("renders severity, status and deviation for each row", async () => {
    renderAnomaliesPage([anomaliesHandler([anomaly({ deviationPercent: -8.25 })])]);
    await screen.findByText("GSF sapması");
    expect(screen.getByText("%-8.3")).toBeInTheDocument();
    expect(screen.getAllByText("Yüksek").length).toBeGreaterThan(0); // severity badge
    expect(screen.getByText("Çözüldü", { selector: "span" })).toBeInTheDocument(); // status badge
  });
});

describe("AnomaliesPage — priority strip", () => {
  it("shows only open-status anomalies in the priority strip, ranked by severity", async () => {
    renderAnomaliesPage([
      anomaliesHandler([
        anomaly({ id: "resolved-one", title: "Çözülen", status: "resolved", severity: "critical" }),
        anomaly({ id: "open-one", title: "Açık Kritik", status: "new", severity: "critical" }),
      ]),
    ]);
    await screen.findByText("Öncelikli Tespitler");
    const strip = screen.getByText("Öncelikli Tespitler").parentElement!;
    expect(strip).toHaveTextContent("Açık Kritik");
    expect(strip).not.toHaveTextContent("Çözülen");
  });

  it("navigates to the anomaly detail page when a priority card is clicked", async () => {
    // A single open-status item shows up both as a priority card and as a
    // table row with the same title — click the card specifically (its
    // enclosing <button>) to avoid ambiguity between the two.
    renderAnomaliesPage([anomaliesHandler([anomaly({ status: "new", severity: "critical" })])]);
    const user = userEvent.setup();
    await screen.findByText("Öncelikli Tespitler");
    // The priority card's title uses class "text-body font-semibold";
    // the table row's uses "font-medium" — scope to the card specifically.
    await user.click(screen.getByText("GSF sapması", { selector: "p.text-body" }).closest("button")!);
    expect(await screen.findByText("Tespit Detayı Sayfası")).toBeInTheDocument();
  });
});

describe("AnomaliesPage — drill-down", () => {
  it("navigates to the anomaly detail route when a table row is activated", async () => {
    renderAnomaliesPage([anomaliesHandler([anomaly()])]);
    await screen.findByText("GSF sapması");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "GSF sapması tespitini görüntüle" }));
    expect(await screen.findByText("Tespit Detayı Sayfası")).toBeInTheDocument();
  });
});

describe("AnomaliesPage — filter integration", () => {
  it("sends the severity filter as a 'severity' query param on the anomalies request", async () => {
    const requestedSeverity: (string | null)[] = [];
    renderAnomaliesPage([
      anomaliesHandler([anomaly()], (url) => requestedSeverity.push(url.searchParams.get("severity"))),
    ]);
    await screen.findByText("GSF sapması");
    expect(requestedSeverity.at(-1)).toBeNull();

    // "Önem Seviyesi" <select>'i bir <label>'a htmlFor/id ile bağlı değil, bu
    // yüzden getByLabelText yerine DOM komşuluğuna (nextElementSibling) dayanıyoruz.
    const severitySelect = screen.getByText("Önem Seviyesi").nextElementSibling as HTMLSelectElement;
    const user = userEvent.setup();
    await user.selectOptions(severitySelect, "Kritik");

    await waitFor(() => expect(requestedSeverity.at(-1)).toBe("critical"));
  });

  it("sends the free-text search box value as the 'search' query param", async () => {
    const requestedSearch: (string | null)[] = [];
    renderAnomaliesPage([
      anomaliesHandler([anomaly()], (url) => requestedSearch.push(url.searchParams.get("search"))),
    ]);
    await screen.findByText("GSF sapması");

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Başlık veya açıklamada ara..."), "GSF");

    await waitFor(() => expect(requestedSearch.at(-1)).toBe("GSF"));
  });

  it("shows a clear-filters button with a count once a filter or search is active, and clears both on click", async () => {
    renderAnomaliesPage([anomaliesHandler([anomaly()])]);
    await screen.findByText("GSF sapması");
    expect(screen.queryByRole("button", { name: /Filtreleri temizle/ })).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Başlık veya açıklamada ara..."), "GSF");
    const clearButton = await screen.findByRole("button", { name: "Filtreleri temizle (1)" });

    await user.click(clearButton);
    expect(screen.getByPlaceholderText("Başlık veya açıklamada ara...")).toHaveValue("");
    expect(screen.queryByRole("button", { name: /Filtreleri temizle/ })).not.toBeInTheDocument();
  });
});
