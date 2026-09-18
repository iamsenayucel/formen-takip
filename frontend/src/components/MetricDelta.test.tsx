import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PERFORMANCE_COLORS } from "../lib/kpiDirection";
import { MetricDelta } from "./MetricDelta";

describe("MetricDelta", () => {
  it("shows a signed positive value in the improved color", () => {
    render(<MetricDelta value={4.2} />);
    const el = screen.getByText("+4.2");
    expect(el).toHaveStyle({ color: PERFORMANCE_COLORS.improved });
  });

  it("shows an unsigned negative value in the worsened color", () => {
    render(<MetricDelta value={-4.2} />);
    const el = screen.getByText("-4.2");
    expect(el).toHaveStyle({ color: PERFORMANCE_COLORS.worsened });
  });

  it("shows an em dash in the unknown color for a null value", () => {
    render(<MetricDelta value={null} />);
    const el = screen.getByText("—");
    expect(el).toHaveStyle({ color: PERFORMANCE_COLORS.unknown });
  });

  it("respects a custom decimals prop", () => {
    render(<MetricDelta value={4.2789} decimals={2} />);
    expect(screen.getByText("+4.28")).toBeInTheDocument();
  });
});
