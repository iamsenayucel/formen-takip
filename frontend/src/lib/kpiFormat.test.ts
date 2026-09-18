import { describe, expect, it } from "vitest";
import {
  formatKpiScore,
  formatKpiUnitValue,
  formatScoreDelta,
  kpiScoreCardTitle,
  kpiScoreStatus,
  KPI_SCORE_STATUS_GOOD_THRESHOLD,
  KPI_SCORE_STATUS_WARNING_THRESHOLD,
  scoreDeltaColor,
} from "./kpiFormat";
import { PERFORMANCE_COLORS } from "./kpiDirection";

describe("formatKpiUnitValue", () => {
  it("appends % directly without a space", () => {
    expect(formatKpiUnitValue(98.456, "%", 1)) .toBe("98.5%");
  });

  it("appends a non-percent unit with a space", () => {
    expect(formatKpiUnitValue(12.3, "adet", 1)).toBe("12.3 adet");
  });

  it("omits the unit when it is an empty string", () => {
    expect(formatKpiUnitValue(12.3, "", 1)).toBe("12.3");
  });

  it("renders an em dash for null/undefined/non-finite", () => {
    expect(formatKpiUnitValue(null, "%")).toBe("—");
    expect(formatKpiUnitValue(undefined, "%")).toBe("—");
    expect(formatKpiUnitValue(NaN, "%")).toBe("—");
    expect(formatKpiUnitValue(Infinity, "%")).toBe("—");
  });

  it("formats zero as a real value", () => {
    expect(formatKpiUnitValue(0, "%")).toBe("0.0%");
  });
});

describe("formatKpiScore / formatScoreDelta", () => {
  it("formats a score to the given decimals", () => {
    expect(formatKpiScore(87.654, 1)).toBe("87.7");
  });

  it("renders an em dash for non-finite scores", () => {
    expect(formatKpiScore(null)).toBe("—");
    expect(formatKpiScore(NaN)).toBe("—");
  });

  it("prefixes a positive delta with +", () => {
    expect(formatScoreDelta(3.2)).toBe("+3.2");
  });

  it("does not prefix a negative delta (native minus sign)", () => {
    expect(formatScoreDelta(-3.2)).toBe("-3.2");
  });

  it("does not prefix a zero delta", () => {
    expect(formatScoreDelta(0)).toBe("0.0");
  });

  it("renders an em dash for non-finite deltas", () => {
    expect(formatScoreDelta(null)).toBe("—");
    expect(formatScoreDelta(undefined)).toBe("—");
  });
});

describe("scoreDeltaColor", () => {
  it("uses the improved color for a positive delta", () => {
    expect(scoreDeltaColor(1)).toBe(PERFORMANCE_COLORS.improved);
  });

  it("uses the worsened color for a negative delta", () => {
    expect(scoreDeltaColor(-1)).toBe(PERFORMANCE_COLORS.worsened);
  });

  it("uses the unknown color for exactly zero", () => {
    expect(scoreDeltaColor(0)).toBe(PERFORMANCE_COLORS.unknown);
  });

  it("uses the unknown color for null/undefined/non-finite", () => {
    expect(scoreDeltaColor(null)).toBe(PERFORMANCE_COLORS.unknown);
    expect(scoreDeltaColor(undefined)).toBe(PERFORMANCE_COLORS.unknown);
    expect(scoreDeltaColor(NaN)).toBe(PERFORMANCE_COLORS.unknown);
  });
});

describe("kpiScoreStatus", () => {
  it("returns unknown when there are no records", () => {
    expect(kpiScoreStatus(95, 0)).toBe("unknown");
    expect(kpiScoreStatus(95, -1)).toBe("unknown");
  });

  it("returns unknown for a non-finite score", () => {
    expect(kpiScoreStatus(NaN, 5)).toBe("unknown");
  });

  it("returns success at and above the good threshold", () => {
    expect(kpiScoreStatus(KPI_SCORE_STATUS_GOOD_THRESHOLD, 5)).toBe("success");
    expect(kpiScoreStatus(100, 5)).toBe("success");
  });

  it("returns warning between the warning and good thresholds", () => {
    expect(kpiScoreStatus(KPI_SCORE_STATUS_WARNING_THRESHOLD, 5)).toBe("warning");
    expect(kpiScoreStatus(KPI_SCORE_STATUS_GOOD_THRESHOLD - 0.01, 5)).toBe("warning");
  });

  it("returns danger below the warning threshold", () => {
    expect(kpiScoreStatus(KPI_SCORE_STATUS_WARNING_THRESHOLD - 0.01, 5)).toBe("danger");
    expect(kpiScoreStatus(0, 5)).toBe("danger");
  });
});

describe("kpiScoreCardTitle", () => {
  it("replaces a trailing 'Oranı' (title case, the real seed-data casing) with 'Puanı'", () => {
    // Real KPI names use this exact casing (see backend/app/services/synthetic/reference_data.py:
    // "GSF Oranı", "Iskarta Oranı", "Plana Uyum Oranı", ...).
    expect(kpiScoreCardTitle("Verimlilik Oranı")).toBe("Verimlilik Puanı");
  });

  it("is case-insensitive for an all-caps 'ORANI' suffix, using Turkish (tr-TR) case folding", () => {
    // A plain regex /oranı$/i does not match this: JS's default case folding
    // doesn't map the Turkish dotless "ı" to ASCII "I", which is why
    // kpiScoreCardTitle uses toLocaleLowerCase("tr-TR") instead.
    expect(kpiScoreCardTitle("VERIMLILIK ORANI")).toBe("VERIMLILIK Puanı");
  });

  it("is case-insensitive for a lowercase 'oranı' suffix", () => {
    expect(kpiScoreCardTitle("verimlilik oranı")).toBe("verimlilik Puanı");
  });

  it("is case-insensitive for a mixed-case 'OranI' suffix", () => {
    expect(kpiScoreCardTitle("Verimlilik OranI")).toBe("Verimlilik Puanı");
  });

  it("leaves a name already ending in 'Puanı' unchanged", () => {
    expect(kpiScoreCardTitle("Kalite Puanı")).toBe("Kalite Puanı");
    expect(kpiScoreCardTitle("Kalite Puan")).toBe("Kalite Puan");
  });

  it("appends 'Puanı' when the name has neither suffix", () => {
    expect(kpiScoreCardTitle("GSF")).toBe("GSF Puanı");
  });
});
