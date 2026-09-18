import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PerformanceLevel } from "../api/types";
import { OutstandingPerformanceBadge, PerformanceLevelBadge, resolveLevelIcon } from "./PerformanceLevelBadge";

function level(overrides: Partial<PerformanceLevel> = {}): PerformanceLevel {
  return {
    name: "Hedefte",
    description: "Performans hedefin üzerinde.",
    color: "#16a34a",
    icon: "check-circle",
    outstandingPerformance: false,
    ...overrides,
  };
}

describe("resolveLevelIcon", () => {
  it("resolves a known icon key", () => {
    expect(resolveLevelIcon("check-circle")).not.toBeUndefined();
  });

  it("falls back to a default icon for an unknown key instead of throwing", () => {
    expect(() => resolveLevelIcon("not-a-real-icon")).not.toThrow();
  });
});

describe("PerformanceLevelBadge", () => {
  it("renders the level name", () => {
    render(<PerformanceLevelBadge level={level({ name: "Kritik" })} />);
    expect(screen.getByText("Kritik")).toBeInTheDocument();
  });

  it("does not show the description as a tooltip by default", () => {
    const { container } = render(<PerformanceLevelBadge level={level({ description: "Açıklama metni" })} />);
    const badge = container.querySelector("[title]");
    expect(badge).toBeNull();
  });

  it("shows the description as a title/tooltip when showDescription is true", () => {
    const { container } = render(
      <PerformanceLevelBadge level={level({ description: "Açıklama metni" })} showDescription />
    );
    expect(container.querySelector('[title="Açıklama metni"]')).not.toBeNull();
  });

  it("does not render the outstanding-performance badge when the flag is falsy", () => {
    render(<PerformanceLevelBadge level={level({ outstandingPerformance: false })} />);
    expect(screen.queryByText("Üstün Performans")).not.toBeInTheDocument();
  });

  it("renders the outstanding-performance badge when the flag is true", () => {
    render(<PerformanceLevelBadge level={level({ outstandingPerformance: true })} />);
    expect(screen.getByText("Üstün Performans")).toBeInTheDocument();
  });
});

describe("OutstandingPerformanceBadge", () => {
  it("renders with its fixed label and threshold tooltip", () => {
    const { container } = render(<OutstandingPerformanceBadge />);
    expect(screen.getByText("Üstün Performans")).toBeInTheDocument();
    expect(container.querySelector('[title="Genel performans puanı 105 ve üzerinde"]')).not.toBeNull();
  });
});
