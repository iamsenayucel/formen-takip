import type { ReactNode } from "react";
import { MetricDelta } from "../MetricDelta";
import { formatKpiUnitValue, kpiScoreStatus, KPI_SCORE_STATUS_LABELS, KPI_SCORE_STATUS_STYLES } from "../../lib/kpiFormat";

export function KpiPerformanceHero({
  kpiName,
  unit,
  score,
  hasData,
  target,
  actual,
  delta,
  decimalPlaces = 1,
  meta,
}: {
  kpiName: string;
  unit: string;
  score: number;
  hasData: boolean;
  target: number | null;
  actual: number | null;
  delta?: number | null;
  decimalPlaces?: number;
  meta?: ReactNode;
}) {
  const status = kpiScoreStatus(score, hasData ? 1 : 0);
  const palette = KPI_SCORE_STATUS_STYLES[status];
  const deviation = target !== null && actual !== null ? actual - target : null;

  const navyCardStyle = {
    background: "color-mix(in srgb, var(--primary) 16%, var(--surface-raised))",
    border: "1px solid color-mix(in srgb, var(--primary) 36%, transparent)",
  };

  return (
    <div
      className="rounded-lg p-4"
      style={{ background: "var(--surface-raised)", border: "1px solid var(--border)", boxShadow: "var(--shadow-panel)" }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-page-title" style={{ color: "var(--text-primary)" }}>{kpiName}</h1>
          {meta && <div className="text-body mt-0.5" style={{ color: "var(--text-secondary)" }}>{meta}</div>}
        </div>

        <div className="shrink-0 rounded-md px-3.5 py-3 text-right">
          <p className="text-label" style={{ color: "var(--text-muted)" }}>Şirket Ortalama Puanı</p>
          <div className="mt-0.5 flex items-baseline justify-end gap-1">
            <span className="text-display-metric leading-none" style={{ color: "var(--data-primary)" }}>
              {hasData ? score.toFixed(1) : "—"}
            </span>
            <span className="text-body" style={{ color: "var(--text-muted)" }}>/ 100</span>
          </div>
          <div className="mt-1.5 flex justify-end">
            <span
              className="inline-flex items-center rounded px-2.5 py-1 text-xs font-semibold"
              style={{ background: palette.background, color: palette.accent, border: `1px solid ${palette.border}` }}
            >
              {KPI_SCORE_STATUS_LABELS[status]}
            </span>
          </div>
          {delta !== undefined && (
            <p className="text-metadata mt-1.5" style={{ color: "var(--text-secondary)" }}>
              Önceki dönem: <MetricDelta value={delta} className="font-semibold" />
            </p>
          )}
        </div>
      </div>

      <div className="mt-2.5 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        <div className="rounded-xl p-3.5" style={navyCardStyle}>
          <p className="text-label" style={{ color: "var(--text-secondary)" }}>Gerçekleşen</p>
          <p className="text-hero-metric mt-1 tabular-nums" style={{ color: "var(--text-primary)" }}>
            {formatKpiUnitValue(actual, unit, decimalPlaces)}
          </p>
        </div>
        <div className="rounded-xl p-3.5" style={navyCardStyle}>
          <p className="text-label" style={{ color: "var(--text-secondary)" }}>Hedef</p>
          <p className="text-lg font-semibold mt-1 tabular-nums" style={{ color: "var(--text-primary)" }}>
            {formatKpiUnitValue(target, unit, decimalPlaces)}
          </p>
        </div>
        <div className="rounded-xl p-3.5" style={{ background: palette.background, border: `1px solid ${palette.border}` }}>
          <p className="text-label" style={{ color: "var(--text-secondary)" }}>Sapma</p>
          <p className="text-lg font-semibold mt-1 tabular-nums" style={{ color: palette.accent }}>
            {deviation !== null ? `${deviation >= 0 ? "+" : ""}${formatKpiUnitValue(deviation, unit, decimalPlaces)}` : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}
