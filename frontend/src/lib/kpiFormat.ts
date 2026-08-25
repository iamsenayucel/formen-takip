import { PERFORMANCE_COLORS } from "./kpiDirection";

export function formatKpiUnitValue(value: number | null | undefined, unit: string, decimals = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const formatted = value.toFixed(decimals);
  if (!unit) return formatted;
  return unit === "%" ? `${formatted}%` : `${formatted} ${unit}`;
}

export function formatKpiScore(score: number | null | undefined, decimals = 1): string {
  if (score === null || score === undefined || !Number.isFinite(score)) return "—";
  return score.toFixed(decimals);
}

export function formatScoreDelta(delta: number | null | undefined, decimals = 1): string {
  if (delta === null || delta === undefined || !Number.isFinite(delta)) return "—";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(decimals)}`;
}

export function scoreDeltaColor(delta: number | null | undefined): string {
  if (delta === null || delta === undefined || !Number.isFinite(delta) || delta === 0) return PERFORMANCE_COLORS.unknown;
  return delta > 0 ? PERFORMANCE_COLORS.improved : PERFORMANCE_COLORS.worsened;
}

export type KpiScoreStatus = "success" | "warning" | "danger" | "unknown";

/**
 * capped_score backend scoring engine tarafından yön normalize edilmiştir (kpi_engine.py).
 * Her hesaplama türünde raw KPI higher-is-better veya lower-is-better olsa da 100 "on target"
 * anlamına gelir. Bu nedenle KPI adı veya raw yönüne bakmadan yalnızca score üzerinden bucket
 * seçmek doğrudur ve tüm KPI'lar için geneldir.
 */
export const KPI_SCORE_STATUS_GOOD_THRESHOLD = 90;
export const KPI_SCORE_STATUS_WARNING_THRESHOLD = 80;

export function kpiScoreStatus(score: number, recordCount: number): KpiScoreStatus {
  if (recordCount <= 0 || !Number.isFinite(score)) return "unknown";
  if (score >= KPI_SCORE_STATUS_GOOD_THRESHOLD) return "success";
  if (score >= KPI_SCORE_STATUS_WARNING_THRESHOLD) return "warning";
  return "danger";
}

export const KPI_SCORE_STATUS_LABELS: Record<KpiScoreStatus, string> = {
  success: "Hedefte",
  warning: "Gelişim Alanı",
  danger: "Kritik",
  unknown: "Veri Yok",
};

export const KPI_SCORE_STATUS_STYLES: Record<KpiScoreStatus, { background: string; border: string; accent: string }> = {
  success: { background: "var(--status-positive-bg)", border: "var(--status-positive-border)", accent: "var(--status-positive)" },
  warning: { background: "var(--status-neutral-bg)", border: "var(--status-neutral-border)", accent: "var(--status-neutral)" },
  danger: { background: "var(--status-negative-bg)", border: "var(--status-negative-border)", accent: "var(--status-negative)" },
  unknown: { background: "var(--surface)", border: "var(--border)", accent: "var(--text-muted)" },
};

// KPI adları backend'de "... Oranı" gibi metrik isimleri olarak tutulur; kart
// başlığında tutarlı biçimde "... Puanı" olarak göstermek için tek merkezi kural.
export function kpiScoreCardTitle(name: string): string {
  if (/oranı$/i.test(name)) return name.replace(/oranı$/i, "Puanı");
  if (/puan(ı)?$/i.test(name)) return name;
  return `${name} Puanı`;
}
