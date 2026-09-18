import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import type { AuthMeResponse, FilterOptionsResponse, ReportExportMeta } from "../api/types";
import { PermissionProvider } from "../context/PermissionContext";
import { renderWithProviders } from "../test/renderWithProviders";
import { ReportsPage } from "./ReportsPage";

vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ isAuthenticated: true }) }));

const FILTER_OPTIONS: FilterOptionsResponse = {
  factories: [],
  plants: [],
  chiefs: [],
  shifts: [],
  kpis: [],
};

const REPORT: ReportExportMeta = {
  id: "r1",
  fileName: "tesis-karsilastirma-2026-03.xlsx",
  reportType: "plant_comparison",
  format: "xlsx",
  rowCount: 42,
  status: "completed",
  requestedBy: "Ayşe Yönetici",
  createdAt: "2026-03-10T08:00:00Z",
};

function authMeHandler(permissions: string[]) {
  return http.get("/api/v1/auth/me", () =>
    HttpResponse.json({
      data: { subject: "u1", displayName: "Test Kullanıcı", email: null, role: "OPERATIONS_MANAGER", permissions } as AuthMeResponse,
    })
  );
}

const filterOptionsHandler = http.get("/api/v1/meta/filters", () => HttpResponse.json({ data: FILTER_OPTIONS }));

function reportHistoryHandler(items: ReportExportMeta[]) {
  return http.get("/api/v1/reports", () =>
    HttpResponse.json({ data: items, pagination: { nextCursor: null, hasMore: false, total: items.length } })
  );
}

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function renderReportsPage(permissions: string[], extraHandlers: Parameters<typeof server.use> = []) {
  server.use(authMeHandler(permissions), filterOptionsHandler, ...extraHandlers);
  return renderWithProviders(<ReportsPage />, { wrap: (children) => <PermissionProvider>{children}</PermissionProvider> });
}

const ALL_PERMISSIONS = ["overview.view", "performance.view", "operational_intelligence.view", "operational_impact.contribute", "outputs.view", "reports.create", "reports.download"];

describe("ReportsPage — permission-gated actions", () => {
  it("shows the create-report form and per-row download links for a user with full report permissions", async () => {
    renderReportsPage(ALL_PERMISSIONS, [reportHistoryHandler([REPORT])]);
    expect(await screen.findByText("tesis-karsilastirma-2026-03.xlsx")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Yeni Rapor Oluştur" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "tesis-karsilastirma-2026-03.xlsx dosyasını indir" })).toBeInTheDocument();
  });

  it("hides report-creation and per-row download when the user only has outputs.view (page:view != action permissions)", async () => {
    // A synthetic permission set (no real role currently holds outputs.view
    // without also holding reports.create/download) that isolates the
    // contract: reaching this page's content must not imply the ability to
    // create or download a report — those are separate permission strings.
    renderReportsPage(["outputs.view"], [reportHistoryHandler([REPORT])]);
    expect(await screen.findByText("tesis-karsilastirma-2026-03.xlsx")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Yeni Rapor Oluştur" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /dosyasını indir/ })).not.toBeInTheDocument();
  });

  it("hides the 'download now' button after generating a report when the user lacks reports.download", async () => {
    const user = userEvent.setup();
    renderReportsPage(
      ["outputs.view", "reports.create"],
      [
        reportHistoryHandler([]),
        http.post("/api/v1/reports/generate", () => HttpResponse.json({ data: REPORT })),
      ]
    );
    await screen.findByRole("heading", { name: "Yeni Rapor Oluştur" });
    await user.click(screen.getByRole("button", { name: "Rapor Oluştur" }));
    expect(await screen.findByText(/oluşturuldu/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Şimdi İndir" })).not.toBeInTheDocument();
  });
});

describe("ReportsPage — report history states", () => {
  it("shows a loading state before the history request resolves", async () => {
    renderReportsPage(ALL_PERMISSIONS, [
      http.get("/api/v1/reports", async () => {
        await delay(50);
        return HttpResponse.json({ data: [REPORT], pagination: { nextCursor: null, hasMore: false, total: 1 } });
      }),
    ]);
    expect(screen.getByText("Yükleniyor...")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Yükleniyor...")).not.toBeInTheDocument());
    expect(screen.getByText("tesis-karsilastirma-2026-03.xlsx")).toBeInTheDocument();
  });

  it("shows an empty state when there is no report history yet", async () => {
    renderReportsPage(ALL_PERMISSIONS, [reportHistoryHandler([])]);
    expect(await screen.findByText("Henüz rapor oluşturulmadı.")).toBeInTheDocument();
  });

  it("shows an error state when the history request fails", async () => {
    renderReportsPage(ALL_PERMISSIONS, [
      http.get("/api/v1/reports", () => HttpResponse.json({ error: { code: "INTERNAL", message: "boom" } }, { status: 500 })),
    ]);
    expect(await screen.findByText("Veri yüklenirken bir hata oluştu.")).toBeInTheDocument();
  });
});

describe("ReportsPage — generate report flow", () => {
  it("sends the selected report type/format and the active date filters when generating a report", async () => {
    const user = userEvent.setup();
    let capturedBody: unknown;
    renderReportsPage(ALL_PERMISSIONS, [
      reportHistoryHandler([]),
      http.post("/api/v1/reports/generate", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ data: REPORT });
      }),
    ]);
    await screen.findByRole("heading", { name: "Yeni Rapor Oluştur" });

    await user.selectOptions(screen.getByDisplayValue("Tesis Karşılaştırma"), "KPI Analiz");
    await user.click(screen.getByRole("button", { name: "Rapor Oluştur" }));

    await waitFor(() => expect(capturedBody).toBeTruthy());
    expect(capturedBody).toMatchObject({ reportType: "kpi_analysis", format: "xlsx" });
  });

  it("shows a Turkish error message when report generation fails", async () => {
    const user = userEvent.setup();
    renderReportsPage(ALL_PERMISSIONS, [
      reportHistoryHandler([]),
      http.post("/api/v1/reports/generate", () => HttpResponse.json({ error: { code: "INTERNAL", message: "boom" } }, { status: 500 })),
    ]);
    await screen.findByRole("heading", { name: "Yeni Rapor Oluştur" });
    await user.click(screen.getByRole("button", { name: "Rapor Oluştur" }));
    expect(await screen.findByText("Rapor oluşturulamadı.")).toBeInTheDocument();
  });
});
