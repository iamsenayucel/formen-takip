import { describe, expect, it } from "vitest";
import { formatAxisDateTR, formatDateRangeTR, formatDateTimeTR, formatDateTR } from "./dateFormat";

describe("formatDateTR", () => {
  it("formats an ISO date in long Turkish form", () => {
    expect(formatDateTR("2026-03-05")).toBe("5 Mart 2026");
  });
});

describe("formatAxisDateTR", () => {
  it("formats an ISO date in short axis form (no year)", () => {
    expect(formatAxisDateTR("2026-03-05")).toBe("5 Mar");
  });
});

describe("formatDateTimeTR", () => {
  it("formats an ISO datetime including time", () => {
    const result = formatDateTimeTR("2026-03-05T14:30:00Z");
    expect(result).toMatch(/2026/);
    expect(result).toMatch(/5 Mar/);
  });
});

describe("formatDateRangeTR", () => {
  it("collapses a same-month range into a single 'D–long date' form", () => {
    expect(formatDateRangeTR("2026-03-01", "2026-03-15")).toBe("1–15 Mart 2026");
  });

  it("uses a full 'from – to' form across months", () => {
    expect(formatDateRangeTR("2026-03-25", "2026-04-05")).toBe("25 Mar 2026 – 5 Nis 2026");
  });

  it("uses a full 'from – to' form across years", () => {
    expect(formatDateRangeTR("2025-12-25", "2026-01-05")).toBe("25 Ara 2025 – 5 Oca 2026");
  });

  it("collapses a single-day range", () => {
    expect(formatDateRangeTR("2026-03-05", "2026-03-05")).toBe("5–5 Mart 2026");
  });
});
