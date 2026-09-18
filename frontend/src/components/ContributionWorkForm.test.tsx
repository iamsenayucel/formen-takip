import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FilterOptionsResponse } from "../api/types";
import { ContributionWorkForm } from "./ContributionWorkForm";

const { useFilterOptionsMock, useForemenMock, useCreateMock, useUpdateMock, useNavigateMock } = vi.hoisted(() => ({
  useFilterOptionsMock: vi.fn(),
  useForemenMock: vi.fn(),
  useCreateMock: vi.fn(),
  useUpdateMock: vi.fn(),
  useNavigateMock: vi.fn(),
}));

vi.mock("../api/hooks", () => ({
  useFilterOptions: useFilterOptionsMock,
  useForemen: useForemenMock,
  useCreateContributionWork: useCreateMock,
  useUpdateContributionWork: useUpdateMock,
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ user: { subject: "u1", fullName: "Test Yönetici", email: null } }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => useNavigateMock };
});

const OPTIONS: FilterOptionsResponse = {
  factories: [{ id: "f1", code: "K1", name: "K1", location: "Karaman" }],
  plants: [{ id: "p1", code: "1", name: "1. Tesis", sequenceNumber: 1, factoryId: "f1" }],
  chiefs: [],
  shifts: [],
  kpis: [],
};

function renderForm(onClose = vi.fn()) {
  render(
    <MemoryRouter>
      <ContributionWorkForm onClose={onClose} />
    </MemoryRouter>
  );
  return { onClose };
}

describe("ContributionWorkForm", () => {
  let mutateAsync: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    useFilterOptionsMock.mockReturnValue({ data: OPTIONS, isLoading: false });
    useForemenMock.mockReturnValue({ data: undefined });
    mutateAsync = vi.fn();
    useCreateMock.mockReturnValue({ mutateAsync, isPending: false });
    useUpdateMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("disables 'Taslak Olarak Kaydet' until a title is entered", async () => {
    const user = userEvent.setup();
    renderForm();
    const draftButton = screen.getByRole("button", { name: "Taslak Olarak Kaydet" });
    expect(draftButton).toBeDisabled();

    const titleInput = screen.getByLabelText("Çalışma Başlığı");
    await user.type(titleInput, "SMED iyileştirmesi");

    expect(draftButton).toBeEnabled();
  });

  it("computes and displays the per-occurrence time saving once both durations are entered", async () => {
    const user = userEvent.setup();
    renderForm();
    // "5. Zamandan Kazanç" is a collapsed Section by default.
    await user.click(screen.getByRole("button", { name: /5\. Zamandan Kazanç/ }));
    const previous = screen.getByLabelText("Önceki İşlem Süresi");
    const next = screen.getByLabelText("Yeni İşlem Süresi");
    await user.type(previous, "100");
    await user.type(next, "60");
    expect(screen.getByText(/İşlem başına kazanç:/)).toHaveTextContent("İşlem başına kazanç: 40 dakika");
  });

  it("shows a warning instead of a computed saving when the new duration is not shorter", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: /5\. Zamandan Kazanç/ }));
    const previous = screen.getByLabelText("Önceki İşlem Süresi");
    const next = screen.getByLabelText("Yeni İşlem Süresi");
    await user.type(previous, "60");
    await user.type(next, "90");
    expect(
      screen.getByText("Yeni işlem süresi öncekinden büyük veya eşit olduğu için kazanç hesaplanamıyor.")
    ).toBeInTheDocument();
    expect(screen.queryByText(/İşlem başına kazanç:/)).not.toBeInTheDocument();
  });

  it("renders server-side field errors and the summary message from a 422 response", async () => {
    const user = userEvent.setup();
    mutateAsync.mockRejectedValueOnce({
      response: {
        status: 422,
        data: { detail: { message: "Yayımlamak için zorunlu alanlar eksik.", errors: { title: "Başlık zorunludur." } } },
      },
    });
    renderForm();
    await user.type(screen.getByLabelText("Çalışma Başlığı"), "x");
    await user.click(screen.getByRole("button", { name: "Kaydet ve Yayımla" }));

    await waitFor(() => {
      expect(screen.getByText("Yayımlamak için zorunlu alanlar eksik.")).toBeInTheDocument();
    });
    expect(screen.getByText("Başlık zorunludur.")).toBeInTheDocument();
  });

  it("shows a generic error message for a non-validation failure", async () => {
    const user = userEvent.setup();
    mutateAsync.mockRejectedValueOnce(new Error("network down"));
    renderForm();
    await user.type(screen.getByLabelText("Çalışma Başlığı"), "x");
    await user.click(screen.getByRole("button", { name: "Kaydet ve Yayımla" }));

    await waitFor(() => {
      expect(screen.getByText("Kaydedilemedi. Lütfen tekrar deneyin.")).toBeInTheDocument();
    });
  });

  it("closes and navigates to the new work's detail page after a successful publish", async () => {
    const user = userEvent.setup();
    mutateAsync.mockResolvedValueOnce({ id: "cw-123" });
    const { onClose } = renderForm();
    await user.type(screen.getByLabelText("Çalışma Başlığı"), "SMED iyileştirmesi");
    await user.click(screen.getByRole("button", { name: "Kaydet ve Yayımla" }));

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(useNavigateMock).toHaveBeenCalledWith("/improvement-works/cw-123", { state: { justPublished: true } });
  });

  it("does not navigate after a successful draft save (only published works do)", async () => {
    const user = userEvent.setup();
    mutateAsync.mockResolvedValueOnce({ id: "cw-123" });
    const { onClose } = renderForm();
    await user.type(screen.getByLabelText("Çalışma Başlığı"), "SMED iyileştirmesi");
    await user.click(screen.getByRole("button", { name: "Taslak Olarak Kaydet" }));

    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(useNavigateMock).not.toHaveBeenCalled();
  });

  it("confirms with the user before closing a dirty form, and respects a cancelled confirmation", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { onClose } = renderForm();
    await user.type(screen.getByLabelText("Çalışma Başlığı"), "x");
    await user.click(screen.getByRole("button", { name: "Kapat" }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
  });

  it("closes without prompting when the form has not been touched", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm");
    const { onClose } = renderForm();
    await user.click(screen.getByRole("button", { name: "Kapat" }));

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

describe("ContributionWorkForm accessibility", () => {
  beforeEach(() => {
    useFilterOptionsMock.mockReturnValue({ data: OPTIONS, isLoading: false });
    useForemenMock.mockReturnValue({ data: undefined });
    useCreateMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
    useUpdateMock.mockReturnValue({ mutateAsync: vi.fn(), isPending: false });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // Her alan etiketi, kontrolüne htmlFor/id (özel combobox'larda aria-labelledby) ile
  // bağlı olmalı ki getByLabelText bulabilsin. Metinler ContributionWorkForm.tsx'teki
  // gerçek Türkçe etiketlerdir.
  it("exposes every visible field label as its control's accessible name", async () => {
    const user = userEvent.setup();
    renderForm();
    expect(screen.getByLabelText("İlgili Formen(ler)")).toBeInTheDocument();
    expect(screen.getByLabelText("Fabrika(lar)")).toBeInTheDocument();
    expect(screen.getByLabelText("Tesis(ler)")).toBeInTheDocument();
    expect(screen.getByLabelText("Kaydı Oluşturan Yönetici")).toBeInTheDocument();

    // Single-date mode by default: only the start-date input renders.
    expect(screen.getAllByLabelText("Çalışma Tarihi")).toHaveLength(1);
    // Switching to a date range renders a second input sharing the same group label.
    await user.click(screen.getByRole("radio", { name: "Tarih aralığı" }));
    expect(screen.getAllByLabelText("Çalışma Tarihi")).toHaveLength(2);

    expect(screen.getByLabelText("Çalışma Başlığı")).toBeInTheDocument();
    expect(screen.getByLabelText("Çalışma Türü")).toBeInTheDocument();
    expect(screen.getByLabelText("Etki Seviyesi")).toBeInTheDocument();
    expect(screen.getByLabelText("Kısa Özet")).toBeInTheDocument();
    expect(screen.getByLabelText("Detaylı Açıklama")).toBeInTheDocument();
    expect(screen.getByLabelText("Tespit Edilen Problem")).toBeInTheDocument();
    expect(screen.getByLabelText("Uygulanan Çözüm")).toBeInTheDocument();
    expect(screen.getByLabelText("Elde Edilen Sonuç")).toBeInTheDocument();
  });

  it("exposes the conditional financial-gain fields once 'Maddi Kazanç Var mı?' is set to Evet", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: /4\. Maddi Kazanç/ }));
    await user.selectOptions(screen.getByLabelText("Maddi Kazanç Var mı?"), "Evet");

    expect(screen.getByLabelText("Kazanç Tutarı")).toBeInTheDocument();
    expect(screen.getByLabelText("Para Birimi")).toBeInTheDocument();
    expect(screen.getByLabelText("Kazanç Periyodu")).toBeInTheDocument();
  });

  it("exposes the time-saving fields with distinct accessible names", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: /5\. Zamandan Kazanç/ }));

    expect(screen.getByLabelText("Önceki İşlem Süresi")).toBeInTheDocument();
    expect(screen.getByLabelText("Yeni İşlem Süresi")).toBeInTheDocument();
    expect(screen.getByLabelText("Süre Birimi")).toBeInTheDocument();
    expect(screen.getByLabelText("Tekrar Periyodu")).toBeInTheDocument();
  });

  it("gives each 'Diğer Kazanımlar' row its own uniquely addressable fields, with a named remove button", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.click(screen.getByRole("button", { name: /6\. Diğer Kazanımlar/ }));
    await user.click(screen.getByRole("button", { name: "Kazanım Ekle" }));
    await user.click(screen.getByRole("button", { name: "Kazanım Ekle" }));

    // Two rows exist; each has its own "Kazanım Türü" field, individually
    // reachable (not just "some element somewhere" via duplicate ids).
    const typeSelects = screen.getAllByLabelText("Kazanım Türü");
    expect(typeSelects).toHaveLength(2);
    expect(typeSelects[0].id).not.toBe(typeSelects[1].id);

    expect(screen.getByRole("button", { name: "Kazanım 1 kaldır" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Kazanım 2 kaldır" })).toBeInTheDocument();
  });
});
