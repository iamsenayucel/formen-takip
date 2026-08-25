import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowDown, ArrowUp, ChevronsUpDown, Star } from "lucide-react";
import type { ChiefForemanComparison, ForemanComparisonItem, ForemanComparisonKpiMeta } from "../api/types";
import { formatKpiUnitValue, formatScoreDelta, kpiScoreStatus, KPI_SCORE_STATUS_STYLES, scoreDeltaColor } from "../lib/kpiFormat";
import { clickableRowProps } from "../lib/a11y";

const NAME_COL_WIDTH = 208;
const SCORE_COL_WIDTH = 116;
const KPI_COL_MIN_WIDTH = 104;

type SortKey = "total_score" | string;
type SortDir = "asc" | "desc";

interface HoverInfo {
  top: number;
  left: number;
  kpi: ForemanComparisonKpiMeta;
  value: { score: number; actual: number | null; target: number | null } | null;
  groupAvg: number;
  previousScore: number | null;
}

const TOOLTIP_WIDTH = 200;
const TOOLTIP_MARGIN = 8;

function clampTooltipLeft(centerX: number): number {
  const min = TOOLTIP_WIDTH / 2 + TOOLTIP_MARGIN;
  const max = window.innerWidth - TOOLTIP_WIDTH / 2 - TOOLTIP_MARGIN;
  return Math.min(Math.max(centerX, min), max);
}

function kpiScore(item: ForemanComparisonItem, kpiId: string): number | null {
  return item.kpiScores[kpiId]?.score ?? null;
}

export function ForemanComparisonMatrix({
  data,
  previous,
}: {
  data: ChiefForemanComparison;
  previous?: ChiefForemanComparison;
}) {
  const navigate = useNavigate();
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({ key: "total_score", dir: "desc" });
  const [hover, setHover] = useState<HoverInfo | null>(null);

  const previousByForemanId = useMemo(() => {
    const map = new Map<string, ForemanComparisonItem>();
    previous?.foremen.forEach((f) => map.set(f.id, f));
    return map;
  }, [previous]);

  const bestByKpi = useMemo(() => {
    const best = new Map<string, number>();
    for (const kpi of data.kpis) {
      let max: number | null = null;
      let count = 0;
      for (const f of data.foremen) {
        const s = kpiScore(f, kpi.kpiId);
        if (s === null) continue;
        count += 1;
        if (max === null || s > max) max = s;
      }
      if (max !== null && count > 1) best.set(kpi.kpiId, max);
    }
    return best;
  }, [data]);

  const sortedForemen = useMemo(() => {
    const items = [...data.foremen];
    items.sort((a, b) => {
      const av = sort.key === "total_score" ? a.totalScore : kpiScore(a, sort.key);
      const bv = sort.key === "total_score" ? b.totalScore : kpiScore(b, sort.key);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return sort.dir === "desc" ? bv - av : av - bv;
    });
    return items;
  }, [data.foremen, sort]);

  const toggleSort = (key: SortKey) => {
    setSort((prev) => (prev.key === key ? { key, dir: prev.dir === "desc" ? "asc" : "desc" } : { key, dir: "desc" }));
  };

  const sortLabel = sort.key === "total_score" ? "Genel Puana Göre" : `${data.kpis.find((k) => k.kpiId === sort.key)?.name ?? ""} Puanına Göre`;
  const fixedColsWidth = NAME_COL_WIDTH + SCORE_COL_WIDTH;
  const kpiColWidth = data.kpis.length > 0 ? `calc((100% - ${fixedColsWidth}px) / ${data.kpis.length})` : "0px";
  const minTableWidth = fixedColsWidth + data.kpis.length * KPI_COL_MIN_WIDTH;

  const sortIcon = (key: SortKey) => {
    if (sort.key !== key) return <ChevronsUpDown size={11} strokeWidth={2} style={{ color: "var(--text-muted)", opacity: 0.5 }} />;
    return sort.dir === "desc" ? (
      <ArrowDown size={11} strokeWidth={2.5} style={{ color: "var(--primary)" }} />
    ) : (
      <ArrowUp size={11} strokeWidth={2.5} style={{ color: "var(--primary)" }} />
    );
  };

  return (
    <div
      className="min-w-0 rounded-lg p-[var(--space-card-padding)]"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-section-title" style={{ color: "var(--text-secondary)" }}>
            Formen Performans Karşılaştırması
          </h3>
          <p className="text-metadata mt-1" style={{ color: "var(--text-muted)" }}>
            Gruba bağlı formenlerin genel ve KPI bazlı performansı
          </p>
        </div>
        <div className="text-metadata flex items-center gap-2 whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
          <span className="font-medium">{data.foremen.length} Formen</span>
          <span>•</span>
          <span>{sortLabel}</span>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
        <table className="fc-table text-[13px]" style={{ width: "100%", minWidth: minTableWidth }}>
          <colgroup>
            <col style={{ width: NAME_COL_WIDTH }} />
            <col style={{ width: SCORE_COL_WIDTH }} />
            {data.kpis.map((k) => (
              <col key={k.kpiId} style={{ width: kpiColWidth, minWidth: KPI_COL_MIN_WIDTH }} />
            ))}
          </colgroup>
          <thead>
            <tr style={{ background: "var(--surface-muted)", borderBottom: "2px solid var(--primary)" }}>
              <th
                className="fc-col-sticky py-3 px-3 text-left text-[11px] font-bold uppercase tracking-wide"
                style={{ left: 0, color: "var(--primary)" }}
              >
                Formen
              </th>
              <th
                className="fc-col-sticky cursor-pointer select-none py-3 px-3 text-left text-[11px] font-bold uppercase tracking-wide"
                style={{ left: NAME_COL_WIDTH, color: "var(--primary)", borderLeft: "1px solid var(--border)" }}
                onClick={() => toggleSort("total_score")}
              >
                <span className="flex items-center gap-1">
                  Genel Puan {sortIcon("total_score")}
                </span>
              </th>
              {data.kpis.map((k) => (
                <th
                  key={k.kpiId}
                  className="cursor-pointer select-none py-3 px-3 text-left text-[11px] font-bold uppercase tracking-wide"
                  style={{ color: "var(--primary)", overflow: "hidden" }}
                  onClick={() => toggleSort(k.kpiId)}
                  title={k.name}
                >
                  <span className="flex min-w-0 items-start gap-1">
                    <span className="leading-snug" style={{ whiteSpace: "normal" }}>{k.name}</span>
                    <span className="mt-0.5 shrink-0">{sortIcon(k.kpiId)}</span>
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sortedForemen.map((f) => {
              const prev = previousByForemanId.get(f.id);
              const hasPreviousTotal = !!prev;
              const totalDelta = hasPreviousTotal ? f.totalScore - prev!.totalScore : null;

              return (
                <tr
                  key={f.id}
                  className="cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50"
                  style={{ borderBottom: "1px solid var(--border)" }}
                  {...clickableRowProps(() => navigate(`/foremen/${f.id}`), `${f.fullName ?? "Formen"} profiline git`)}
                >
                  <td className="fc-col-sticky py-2.5 px-3" style={{ left: 0 }}>
                    <div className="flex min-w-0 flex-col">
                      <span className="flex items-center gap-1 truncate font-semibold" style={{ color: "var(--text-primary)" }}>
                        <span className="truncate">{f.fullName ?? "-"}</span>
                        {!f.isReliable && (
                          <span title="Eksik veri" role="img" aria-label="Eksik veri" className="inline-flex shrink-0">
                            <AlertTriangle size={12} strokeWidth={2} style={{ color: "var(--status-neutral)" }} aria-hidden="true" />
                          </span>
                        )}
                      </span>
                      <span className="text-metadata truncate" style={{ color: "var(--text-muted)" }}>
                        Sicil: {f.employeeNumber ?? "-"}
                      </span>
                    </div>
                  </td>
                  <td
                    className="fc-col-sticky py-2.5 px-3"
                    style={{ left: NAME_COL_WIDTH, borderLeft: "1px solid var(--border)", background: "color-mix(in srgb, var(--primary) 4%, var(--surface))" }}
                  >
                    <div className="flex flex-col gap-0.5">
                      <span className="text-base font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>
                        {f.totalScore.toFixed(1)}
                      </span>
                      <span className="text-metadata font-medium" style={{ color: f.level.color }}>
                        {f.level.name}
                      </span>
                      {hasPreviousTotal && totalDelta !== null && (
                        <span
                          className="text-metadata inline-flex items-center gap-0.5 font-semibold tabular-nums"
                          style={{ color: scoreDeltaColor(totalDelta) }}
                          title="Önceki döneme göre"
                        >
                          {totalDelta === 0 ? null : totalDelta > 0 ? (
                            <ArrowUp size={9} strokeWidth={2.5} />
                          ) : (
                            <ArrowDown size={9} strokeWidth={2.5} />
                          )}
                          {formatScoreDelta(totalDelta)}
                        </span>
                      )}
                    </div>
                  </td>
                  {data.kpis.map((k) => {
                    const value = f.kpiScores[k.kpiId];
                    const groupAvg = data.groupAverage.kpiScores[k.kpiId];
                    const status = value ? kpiScoreStatus(value.score, value.recordCount) : "unknown";
                    const palette = KPI_SCORE_STATUS_STYLES[status];
                    const isBest = value ? bestByKpi.get(k.kpiId) === value.score : false;
                    const delta = value && groupAvg !== undefined ? value.score - groupAvg : null;

                    return (
                      <td
                        key={k.kpiId}
                        className="px-3 py-2.5"
                        style={{ background: palette.background, borderLeft: "1px solid var(--border-subtle)" }}
                        onMouseEnter={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setHover({
                            top: rect.bottom + 6,
                            left: clampTooltipLeft(rect.left + rect.width / 2),
                            kpi: k,
                            value: value ? { score: value.score, actual: value.actual, target: value.target } : null,
                            groupAvg: groupAvg ?? 0,
                            previousScore: prev ? kpiScore(prev, k.kpiId) : null,
                          });
                        }}
                        onMouseLeave={() => setHover(null)}
                      >
                        {value ? (
                          <div className="flex flex-col gap-0.5">
                            <span className="inline-flex items-center gap-1 font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                              {value.score.toFixed(1)}
                              {isBest && <Star size={9} strokeWidth={2} fill={palette.accent} style={{ color: palette.accent, opacity: 0.85 }} />}
                            </span>
                            {delta !== null && (
                              <span className="text-metadata inline-flex items-center gap-0.5 tabular-nums" style={{ color: scoreDeltaColor(delta) }}>
                                {delta === 0 ? null : delta > 0 ? <ArrowUp size={8} strokeWidth={2.5} /> : <ArrowDown size={8} strokeWidth={2.5} />}
                                {formatScoreDelta(delta)}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="font-medium" style={{ color: "var(--text-muted)" }}>
                            —
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            <tr className="fc-row-average font-semibold" style={{ borderTop: "2px solid var(--border-strong)" }}>
              <td className="fc-col-sticky py-2.5 px-3" style={{ left: 0, color: "var(--text-primary)" }}>
                Grup Ortalaması
              </td>
              <td
                className="fc-col-sticky py-2.5 px-3 tabular-nums"
                style={{ left: NAME_COL_WIDTH, borderLeft: "1px solid var(--border)", color: "var(--text-primary)" }}
              >
                {data.groupAverage.totalScore.toFixed(1)}
              </td>
              {data.kpis.map((k) => (
                <td
                  key={k.kpiId}
                  className="px-3 py-2.5 tabular-nums"
                  style={{ borderLeft: "1px solid var(--border-subtle)", color: "var(--text-primary)", background: "var(--surface-muted)" }}
                >
                  {data.groupAverage.kpiScores[k.kpiId] !== undefined ? data.groupAverage.kpiScores[k.kpiId].toFixed(1) : "—"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {hover && (
        <div
          className="pointer-events-none fixed z-50 -translate-x-1/2 rounded-md px-3 py-2 text-[12px] shadow-lg"
          style={{
            top: hover.top,
            left: hover.left,
            background: "var(--surface-raised)",
            border: "1px solid var(--border-strong)",
            color: "var(--text-primary)",
            minWidth: TOOLTIP_WIDTH,
          }}
        >
          <p className="mb-1 font-semibold" style={{ color: "var(--text-primary)" }}>
            {hover.kpi.name}
          </p>
          {hover.value ? (
            <div className="flex flex-col gap-0.5" style={{ color: "var(--text-secondary)" }}>
              <span>Puan: <strong className="tabular-nums" style={{ color: "var(--text-primary)" }}>{hover.value.score.toFixed(1)}</strong></span>
              <span>Gerçekleşen: <span className="tabular-nums">{formatKpiUnitValue(hover.value.actual, hover.kpi.unit, hover.kpi.decimalPlaces)}</span></span>
              <span>Hedef: <span className="tabular-nums">{formatKpiUnitValue(hover.value.target, hover.kpi.unit, hover.kpi.decimalPlaces)}</span></span>
              <span>Grup Ortalaması: <span className="tabular-nums">{hover.groupAvg.toFixed(1)}</span></span>
              <span>
                Fark:{" "}
                <span className="tabular-nums font-medium" style={{ color: scoreDeltaColor(hover.value.score - hover.groupAvg) }}>
                  {formatScoreDelta(hover.value.score - hover.groupAvg)}
                </span>
              </span>
              {hover.previousScore !== null && (
                <>
                  <span className="mt-1 pt-1" style={{ borderTop: "1px solid var(--border)" }}>
                    Önceki dönem: <span className="tabular-nums">{hover.previousScore.toFixed(1)}</span>
                  </span>
                  <span>
                    Değişim:{" "}
                    <span className="tabular-nums font-medium" style={{ color: scoreDeltaColor(hover.value.score - hover.previousScore) }}>
                      {formatScoreDelta(hover.value.score - hover.previousScore)}
                    </span>
                  </span>
                </>
              )}
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)" }}>Yeterli KPI verisi bulunmuyor</p>
          )}
        </div>
      )}
    </div>
  );
}
