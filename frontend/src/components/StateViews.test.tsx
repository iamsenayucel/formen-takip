import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Card, EmptyState, ErrorState, LoadingState } from "./StateViews";

describe("LoadingState", () => {
  it("renders the default Turkish loading message", () => {
    render(<LoadingState />);
    expect(screen.getByText("Yükleniyor...")).toBeInTheDocument();
  });

  it("renders a custom label when provided", () => {
    render(<LoadingState label="Formenler yükleniyor..." />);
    expect(screen.getByText("Formenler yükleniyor...")).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("renders the default Turkish error message", () => {
    render(<ErrorState />);
    expect(screen.getByText("Veri yüklenirken bir hata oluştu.")).toBeInTheDocument();
  });

  it("renders a custom message when provided", () => {
    render(<ErrorState message="Rapor oluşturulamadı." />);
    expect(screen.getByText("Rapor oluşturulamadı.")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders the default Turkish empty message", () => {
    render(<EmptyState />);
    expect(screen.getByText("Seçilen filtrelerle eşleşen veri bulunamadı.")).toBeInTheDocument();
  });

  it("renders a custom message when provided", () => {
    render(<EmptyState message="Henüz tespit yok." />);
    expect(screen.getByText("Henüz tespit yok.")).toBeInTheDocument();
  });
});

describe("Card", () => {
  it("renders children without a header when no title is given", () => {
    render(<Card>İçerik</Card>);
    expect(screen.getByText("İçerik")).toBeInTheDocument();
    expect(screen.queryByRole("heading")).not.toBeInTheDocument();
  });

  it("renders a title, subtitle and action alongside children", () => {
    render(
      <Card title="KPI Özeti" subtitle="Son 30 gün" action={<button>Yenile</button>}>
        İçerik
      </Card>
    );
    expect(screen.getByRole("heading", { name: "KPI Özeti" })).toBeInTheDocument();
    expect(screen.getByText("Son 30 gün")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Yenile" })).toBeInTheDocument();
    expect(screen.getByText("İçerik")).toBeInTheDocument();
  });

  it("omits the subtitle line when none is given", () => {
    render(<Card title="KPI Özeti">İçerik</Card>);
    expect(screen.getByRole("heading", { name: "KPI Özeti" })).toBeInTheDocument();
  });
});
