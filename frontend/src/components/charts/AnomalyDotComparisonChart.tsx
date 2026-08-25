import { Fragment } from "react";
import { resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";
import { formatMetricValue } from "../../lib/anomalyMetrics";
import { SEVERITY_COLORS, targetDeviationSeverity } from "../../lib/kpiDirection";
import type { AnomalyKpiDefinition } from "../../api/types";

export interface DotComparisonRow {
  key: string;
  label: string;
  value: number | null;
  emphasis?: boolean;
}

const ROW_GAP = 10;
const TRACK_HEIGHT = 22;
const TOP_PADDING = 22;

export function AnomalyDotComparisonChart({
  rows, target, unit, kpiDefinition,
}: {
  rows: DotComparisonRow[];
  target?: number | null;
  unit: string;
  kpiDefinition: AnomalyKpiDefinition;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const dotStroke = isDark ? "#0f172a" : "#ffffff";

  const values = rows.map((r) => r.value).filter((v): v is number => v != null);
  if (values.length === 0) return <EmptyState message="Karşılaştırma verisi bulunamadı." />;

  const domainMax = Math.max(...values, target ?? 0) * 1.15 || 1;
  const pct = (v: number) => `${(Math.max(v, 0) / domainMax) * 100}%`;

  return (
    <div
      className="grid items-center"
      style={{ gridTemplateColumns: "max-content 1fr", columnGap: 12, rowGap: ROW_GAP, paddingTop: TOP_PADDING }}
    >
      {target != null && (
        <div style={{ gridColumn: 2, gridRow: `1 / ${rows.length + 1}`, alignSelf: "stretch", position: "relative", pointerEvents: "none" }}>
          <span
            className="tabular-nums"
            style={{
              position: "absolute", left: pct(target), top: -TOP_PADDING, transform: "translateX(-50%)",
              fontSize: 12, fontWeight: 400, color: ink.secondary, whiteSpace: "nowrap",
            }}
          >
            Hedef · {formatMetricValue(target, unit)}
          </span>
          <div style={{ position: "absolute", left: pct(target), top: 0, bottom: 0, borderLeft: `1px dashed ${ink.axis}` }} />
        </div>
      )}
      {rows.map((row, i) => {
        const severity = row.value != null ? targetDeviationSeverity(row.value, target ?? null, kpiDefinition.desiredDirection) : "unknown";
        const color = severity === "unknown" ? ink.secondary : SEVERITY_COLORS[severity];
        return (
          <Fragment key={row.key}>
            <span
              className="tabular-nums"
              style={{ gridColumn: 1, gridRow: i + 1, fontSize: 14, fontWeight: row.emphasis ? 600 : 500, color: ink.primary }}
            >
              {row.label}
            </span>
            <div style={{ gridColumn: 2, gridRow: i + 1, position: "relative", height: TRACK_HEIGHT }}>
              {row.value != null ? (
                <>
                  <div style={{ position: "absolute", left: 0, top: "50%", width: pct(row.value), height: 2, background: ink.grid, transform: "translateY(-50%)" }} />
                  <div
                    style={{
                      position: "absolute", left: pct(row.value), top: "50%", width: 8, height: 8, borderRadius: "50%",
                      background: color, border: `1.5px solid ${dotStroke}`, transform: "translate(-50%, -50%)",
                    }}
                  />
                  <span
                    className="tabular-nums"
                    style={{
                      position: "absolute", left: `calc(${pct(row.value)} + 10px)`, top: "50%", transform: "translateY(-50%)",
                      fontSize: 14, fontWeight: 600, color, whiteSpace: "nowrap",
                    }}
                  >
                    {formatMetricValue(row.value, unit)}
                  </span>
                </>
              ) : (
                <span className="text-xs" style={{ color: ink.muted }}>Veri yok</span>
              )}
            </div>
          </Fragment>
        );
      })}
    </div>
  );
}
