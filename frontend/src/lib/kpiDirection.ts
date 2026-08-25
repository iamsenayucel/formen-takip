export type KpiDirection = "high" | "low" | null;
export type PerformanceDirection = "improved" | "worsened" | "unknown";

export function isHigherBetter(direction: KpiDirection): boolean | null {
  if (direction === "high") return true;
  if (direction === "low") return false;
  return null;
}

export function performanceDirection(direction: KpiDirection, deltaPositive: boolean): PerformanceDirection {
  const higherBetter = isHigherBetter(direction);
  if (higherBetter === null) return "unknown";
  return deltaPositive === higherBetter ? "improved" : "worsened";
}

export const PERFORMANCE_COLORS: Record<PerformanceDirection, string> = {
  improved: "var(--status-positive)",
  worsened: "var(--status-negative)",
  unknown: "var(--status-unknown)",
};

export const PERFORMANCE_LABELS: Record<PerformanceDirection, string> = {
  improved: "İyileşme",
  worsened: "Kötüleşme",
  unknown: "Yön belirlenemedi",
};

export function formatSignedPct(value: number, decimals = 1): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}%${value.toFixed(decimals)}`;
}

export function formatPct(value: number, decimals = 2): string {
  return `%${value.toFixed(decimals)}`;
}

export type ThresholdSeverity = "critical" | "warning" | "normal" | "unknown";

/**
 * Bir değerin KPI hedefinden yön düzeltilmiş uzaklığı. Hedefin "iyi" tarafındaki değer,
 * büyüklüğünden bağımsız olarak her zaman "normal"dir; "kötü" taraftaki değer sapma yüzdesine
 * göre bucket'a ayrılır. warningPct/criticalPct tüm KPI'lara aynı uygulanır; yön her zaman KPI
 * metadata'sından gelir, KPI başına hardcoded kural kullanılmaz.
 */
export function targetDeviationSeverity(
  value: number,
  target: number | null,
  direction: KpiDirection,
  warningPct = 5,
  criticalPct = 15
): ThresholdSeverity {
  const higherBetter = isHigherBetter(direction);
  if (higherBetter === null || target == null || target === 0) return "unknown";
  const pctDiff = ((value - target) / Math.abs(target)) * 100;
  const badMagnitude = higherBetter ? -pctDiff : pctDiff;
  if (badMagnitude >= criticalPct) return "critical";
  if (badMagnitude >= warningPct) return "warning";
  return "normal";
}

export const SEVERITY_COLORS: Record<Exclude<ThresholdSeverity, "unknown">, string> = {
  critical: "var(--status-negative)",
  warning: "var(--status-neutral)",
  normal: "var(--status-positive)",
};
