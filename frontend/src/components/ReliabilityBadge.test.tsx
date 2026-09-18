import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReliabilityBadge } from "./ReliabilityBadge";

describe("ReliabilityBadge", () => {
  it("shows 'Tam' with no warning icon when data is reliable", () => {
    const { container } = render(<ReliabilityBadge isReliable={true} />);
    expect(screen.getByText("Tam")).toBeInTheDocument();
    expect(container.querySelector("svg")).toBeNull();
  });

  it("shows 'Eksik veri' with a warning icon when data is not reliable", () => {
    const { container } = render(<ReliabilityBadge isReliable={false} />);
    expect(screen.getByText("Eksik veri")).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
