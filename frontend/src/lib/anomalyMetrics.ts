import type { AnomalyListItem, AnomalySeverity, AnomalyStatus } from "../api/types";

const SEVERITY_RANK: Record<AnomalySeverity, number> = { critical: 4, high: 3, medium: 2, low: 1 };
const OPEN_STATUSES: ReadonlySet<AnomalyStatus> = new Set(["new", "in_review", "action_pending"]);

// Açık tespitleri önem sırasına göre sıralar: severity önce, sonra sapma büyüklüğü.
// Dashboard'un CriticalAnomalyCard'ı ve Tespitler listesinin öncelik şeridi aynı kuralı paylaşır.
export function rankAnomaliesByPriority(items: AnomalyListItem[]): AnomalyListItem[] {
  const open = items.filter((a) => OPEN_STATUSES.has(a.status));
  return [...open].sort((a, b) => {
    const bySeverity = SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity];
    if (bySeverity !== 0) return bySeverity;
    return Math.abs(b.deviationPercent) - Math.abs(a.deviationPercent);
  });
}

export interface PrimaryDelta {
  absDiff: number;
  pctDiff: number | null;
}

export function primaryDelta(observed: number, reference: number): PrimaryDelta {
  const absDiff = observed - reference;
  const pctDiff = reference !== 0 ? (absDiff / Math.abs(reference)) * 100 : null;
  return { absDiff, pctDiff };
}

export function formatMetricValue(value: number, unit: string, decimals = 2): string {
  return unit === "%" ? `%${value.toFixed(decimals)}` : `${value.toFixed(decimals)} ${unit}`;
}

export function unitDiffSuffix(unit: string): string {
  return unit === "%" ? "yüzde puan" : unit;
}

export function formatSignedUnitDiff(value: number, unit: string, decimals = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)} ${unitDiffSuffix(unit)}`;
}

export function magnitudeWord(value: number): "düşük" | "yüksek" {
  return value < 0 ? "düşük" : "yüksek";
}

export function changeWord(value: number): "Düşüş" | "Artış" {
  return value < 0 ? "Düşüş" : "Artış";
}
