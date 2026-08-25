import { ArrowDown, ArrowUp, ChevronRight, Minus } from "lucide-react";
import {
  formatKpiScore, formatKpiUnitValue, formatScoreDelta, kpiScoreCardTitle, kpiScoreStatus,
  KPI_SCORE_STATUS_LABELS, KPI_SCORE_STATUS_STYLES, scoreDeltaColor,
} from "../../lib/kpiFormat";

// Formen/Tesis/Şef/KPI Analizi detay sayfalarının ortak KPI kartı. Alanların
// hepsi opsiyoneldir — çağıran, elindeki gerçek veriye göre bir alt küme geçer;
// kart eksik alanları sessizce atlar, uydurma değer üretmez.
export function KpiScorecard({
  name,
  unit,
  score,
  recordCount,
  target,
  actual,
  delta,
  weight,
  description,
  onClick,
}: {
  name: string;
  unit: string;
  score: number | null;
  recordCount: number;
  target: number | null | undefined;
  actual: number | null | undefined;
  delta?: number | null;
  weight?: number | null;
  description?: string | null;
  onClick?: () => void;
}) {
  const hasScore = recordCount > 0 && score !== null;
  const status = kpiScoreStatus(score ?? 0, recordCount);
  const palette = KPI_SCORE_STATUS_STYLES[status];
  const Tag = onClick ? "button" : "div";

  const hasDelta = delta !== undefined;
  const deltaColor = hasDelta ? scoreDeltaColor(delta) : undefined;
  const DeltaIcon = !hasDelta || delta === null || !Number.isFinite(delta) || delta === 0
    ? Minus
    : delta! > 0 ? ArrowUp : ArrowDown;

  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick}
      title={description ?? undefined}
      className={`group flex h-full flex-col gap-2 rounded-lg p-3 text-left transition-all duration-150 ${
        onClick ? "hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/40" : ""
      }`}
      style={{
        borderTop: "1px solid var(--border)",
        borderRight: "1px solid var(--border)",
        borderBottom: "1px solid var(--border)",
        borderLeft: `3px solid ${palette.accent}`,
        background: hasScore ? `color-mix(in srgb, ${palette.accent} 5%, var(--surface))` : "var(--surface)",
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5">
          <p className="text-metadata font-bold leading-tight" style={{ color: "var(--primary)" }}>
            {kpiScoreCardTitle(name)}
          </p>
          {hasScore && (
            <span
              className="shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase leading-none tracking-wide"
              style={{ color: palette.accent, background: `color-mix(in srgb, ${palette.accent} 16%, transparent)` }}
            >
              {KPI_SCORE_STATUS_LABELS[status]}
            </span>
          )}
        </div>
        {onClick && (
          <span
            className="flex shrink-0 items-center gap-0.5 text-[10px] font-medium opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
            style={{ color: "var(--primary)" }}
          >
            Detay <ChevronRight size={11} strokeWidth={2.5} />
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 items-center gap-2">
        {(target !== undefined || actual !== undefined) && (
          <div className="flex flex-col gap-1.5">
            {target !== undefined && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Hedef</p>
                <p className="text-base font-bold leading-tight tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {formatKpiUnitValue(target, unit)}
                </p>
              </div>
            )}
            {actual !== undefined && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Gerç.</p>
                <p className="text-base font-bold leading-tight tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {formatKpiUnitValue(hasScore ? actual : null, unit)}
                </p>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-col items-end gap-1 pr-2">
          <p className="text-hero-metric text-right tabular-nums" style={{ color: "var(--text-primary)" }}>
            {formatKpiScore(hasScore ? score : null)}
          </p>
          {hasDelta && (
            <span
              className="inline-flex items-center gap-0.5 text-metadata font-semibold tabular-nums"
              style={{ color: deltaColor }}
              title="Önceki döneme göre"
            >
              <DeltaIcon size={10} strokeWidth={2.5} />
              {formatScoreDelta(delta)}
            </span>
          )}
        </div>
      </div>

      {weight !== undefined && weight !== null && (
        <div className="text-metadata" style={{ color: "var(--text-secondary)" }}>
          <span style={{ color: "var(--text-muted)" }}>Ağırlık:</span> %{weight}
        </div>
      )}
    </Tag>
  );
}
