import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useShiftHeatmap } from "../api/hooks";
import { Card, EmptyState, ErrorState, LoadingState } from "./StateViews";
import { withSearchParam } from "../lib/chartDrilldown";
import { statusChartColor } from "../lib/chartColors";
import { useTheme } from "../context/ThemeContext";
import type { HeatmapCell, HeatmapLevel } from "../api/types";

const LEVEL_LABEL: Record<HeatmapLevel, string> = {
  no_data: "Veri Yok",
  normal: "Normal",
  attention: "Dikkat",
  significant: "Önemli",
  critical: "Kritik",
};

// significant, "dikkat" ile "kritik" arasında backend'in ayrı sınıflandırdığı
// bağımsız bir 5. seviye — mandated 3'lü status paletine indirgemek gerçek
// bir sınıflandırmayı kaybeder, bu yüzden negative ailesinde ama kritikten
// daha az doygun sabit bir ton olarak kalır.
function levelColor(level: HeatmapLevel, isDark: boolean): string {
  if (level === "normal") return statusChartColor("positive", isDark);
  if (level === "attention") return statusChartColor("neutral", isDark);
  if (level === "critical") return statusChartColor("negative", isDark);
  if (level === "significant") return isDark ? "#f2793d" : "#ea580c";
  return statusChartColor("unknown", isDark);
}

const LEVEL_ORDER: HeatmapLevel[] = ["normal", "attention", "significant", "critical", "no_data"];

function decimalPlacesFor(unit: string): number {
  return unit === "%" ? 1 : 2;
}

function HeatmapCellButton({
  cell, plantLabel, kpiName, kpiUnit, shiftNames, onNavigate, openDown, isDark,
}: {
  cell: HeatmapCell;
  plantLabel: string;
  kpiName: string;
  kpiUnit: string;
  shiftNames: [string, string];
  onNavigate: (plantId: string, kpiId: string) => void;
  openDown: boolean;
  isDark: boolean;
}) {
  const [hover, setHover] = useState(false);
  const color = levelColor(cell.level, isDark);
  const label = LEVEL_LABEL[cell.level];
  const decimals = decimalPlacesFor(kpiUnit);
  const hasData = cell.level !== "no_data" && cell.v1 && cell.v2;

  return (
    <td className="p-0.5 text-center align-middle">
      <div className="relative">
        <button
          type="button"
          onClick={() => onNavigate(cell.plantId, cell.kpiId)}
          onMouseEnter={() => setHover(true)}
          onMouseLeave={() => setHover(false)}
          onFocus={() => setHover(true)}
          onBlur={() => setHover(false)}
          aria-label={`${plantLabel} — ${kpiName}: ${label}${hasData ? `, sapma yüzde ${cell.pctDiff!.toFixed(1)}` : ", veri yok"}`}
          className="flex h-8 w-full min-w-16 items-center justify-center rounded text-[11px] font-semibold tabular-nums transition-transform duration-100 hover:z-20 hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/60"
          style={{ background: `${color}22`, color, border: `1px solid ${color}55` }}
        >
          {hasData ? `%${cell.pctDiff!.toFixed(1)}` : "—"}
        </button>
        {hover && (
          <div
            className={`pointer-events-none absolute left-1/2 z-30 w-56 -translate-x-1/2 rounded-md p-2.5 text-left text-xs shadow-lg ${
              openDown ? "top-full mt-1.5" : "bottom-full mb-1.5"
            }`}
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
          >
            <p className="font-semibold">{plantLabel} — {kpiName}</p>
            {hasData ? (
              <>
                <p className="mt-1" style={{ color: "var(--text-secondary)" }}>
                  {shiftNames[0]}: <span className="font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{cell.v1!.avgActual.toFixed(decimals)}</span>
                </p>
                <p style={{ color: "var(--text-secondary)" }}>
                  {shiftNames[1]}: <span className="font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>{cell.v2!.avgActual.toFixed(decimals)}</span>
                </p>
                <p className="mt-1 tabular-nums" style={{ color: "var(--text-secondary)" }}>
                  Fark: {(cell.v1!.avgActual - cell.v2!.avgActual >= 0 ? "+" : "")}
                  {(cell.v1!.avgActual - cell.v2!.avgActual).toFixed(decimals)} puan · Sapma: %{cell.pctDiff!.toFixed(1)}
                </p>
                <p className="mt-1 font-medium" style={{ color }}>Durum: {label}</p>
              </>
            ) : (
              <p className="mt-1" style={{ color: "var(--text-muted)" }}>Bu dönem için yeterli veri yok</p>
            )}
          </div>
        )}
      </div>
    </td>
  );
}

export function ShiftAnomalyHeatmap({ params }: { params: Record<string, string | undefined> }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const heatmap = useShiftHeatmap(params);

  const cellByKey = useMemo(() => {
    const map = new Map<string, HeatmapCell>();
    for (const c of heatmap.data?.cells ?? []) map.set(`${c.plantId}|${c.kpiId}`, c);
    return map;
  }, [heatmap.data]);

  const handleNavigate = (plantId: string, kpiId: string) => {
    navigate({ pathname: `/plants/${plantId}`, search: withSearchParam(location.search, "fs_kpi", kpiId) });
  };

  return (
    <Card title="Vardiya Anomali Heatmap">
      <p className="-mt-2 mb-3 text-[13px]" style={{ color: "var(--text-muted)" }}>
        Her hücre, ilgili tesis/KPI için {heatmap.data ? `${heatmap.data.shifts[0]?.name} ile ${heatmap.data.shifts[1]?.name}` : "iki vardiya"} arasındaki
        normalize edilmiş performans farkını gösterir. Bir hücreye tıklayarak ilgili tesise, seçili KPI bağlamında gidebilirsiniz.
      </p>

      {heatmap.isLoading && <LoadingState label="Heatmap hesaplanıyor..." />}
      {heatmap.isError && <ErrorState />}
      {heatmap.data && heatmap.data.plants.length === 0 && (
        <EmptyState message="Seçilen filtrelerle eşleşen tesis bulunamadı." />
      )}
      {heatmap.data && heatmap.data.plants.length > 0 && heatmap.data.shifts.length === 2 && (
        <>
          <div className="max-h-[480px] overflow-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
            <table className="w-full border-collapse text-[12px]">
              <thead>
                <tr>
                  <th
                    className="sticky left-0 top-0 z-30 whitespace-nowrap px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide"
                    style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", borderRight: "1px solid var(--border)" }}
                  >
                    Tesis
                  </th>
                  {heatmap.data.kpis.map((k) => (
                    <th
                      key={k.id}
                      className="sticky top-0 z-20 whitespace-nowrap px-1.5 py-2 text-center text-[11px] font-semibold uppercase tracking-wide"
                      style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", color: "var(--text-muted)" }}
                    >
                      {k.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmap.data.plants.map((p, rowIndex) => (
                  <tr key={p.id}>
                    <td
                      className="sticky left-0 z-10 whitespace-nowrap px-3 py-1 text-[12px] font-medium"
                      style={{ background: "var(--surface)", borderRight: "1px solid var(--border)", color: "var(--text-primary)" }}
                    >
                      <span className="tabular-nums" style={{ color: "var(--text-muted)" }}>{String(p.sequenceNumber).padStart(2, "0")}</span>{" "}
                      {p.name} <span style={{ color: "var(--text-muted)" }}>({p.factoryCode})</span>
                    </td>
                    {heatmap.data!.kpis.map((k) => {
                      const cell = cellByKey.get(`${p.id}|${k.id}`);
                      if (!cell) return <td key={k.id} />;
                      return (
                        <HeatmapCellButton
                          key={k.id}
                          cell={cell}
                          plantLabel={`${p.name} (${p.factoryCode})`}
                          kpiName={k.name}
                          kpiUnit={k.unit}
                          shiftNames={[heatmap.data!.shifts[0].name, heatmap.data!.shifts[1].name]}
                          onNavigate={handleNavigate}
                          openDown={rowIndex < 3}
                          isDark={isDark}
                        />
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div
            className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 pt-3 text-xs"
            style={{ borderTop: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            {LEVEL_ORDER.map((level) => (
              <span key={level} className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: levelColor(level, isDark) }} />
                {LEVEL_LABEL[level]}
              </span>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
