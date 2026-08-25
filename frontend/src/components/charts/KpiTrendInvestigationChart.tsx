import { CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnomalyDailyPoint, KpiDirection } from "../../api/types";
import { accentLineColor, dataSecondaryColor, resolveChartInk, statusChartColor } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";
import { formatSignedPct, isHigherBetter, performanceDirection, PERFORMANCE_COLORS, PERFORMANCE_LABELS } from "../../lib/kpiDirection";
import { formatMetricValue, formatSignedUnitDiff } from "../../lib/anomalyMetrics";

export function KpiTrendInvestigationChart({
  points, targetValue, desiredDirection, unit = "%",
}: {
  points: AnomalyDailyPoint[];
  targetValue: number | null;
  desiredDirection: KpiDirection;
  unit?: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  if (points.length === 0) return <EmptyState message="Bu tespit için günlük geçmiş verisi bulunamadı." />;

  const higherIsBetter = isHigherBetter(desiredDirection);
  const worstPoint =
    higherIsBetter === null
      ? null
      : points.reduce((worst, p) => {
          const pIsWorse = higherIsBetter ? p.value < worst.value : p.value > worst.value;
          return pIsWorse ? p : worst;
        }, points[0]);

  const startValue = points[0].value;
  const endValue = points[points.length - 1].value;
  const change = endValue - startValue;
  const changePct = startValue !== 0 ? (change / Math.abs(startValue)) * 100 : null;
  const perfDir = performanceDirection(desiredDirection, change > 0);

  const renderTooltip = (props: { active?: boolean; label?: string | number; payload?: readonly { payload?: AnomalyDailyPoint }[] }) => {
    const { active, payload, label } = props;
    const point = payload?.[0]?.payload;
    if (!active || !point) return null;
    return (
      <div
        style={{
          fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`, padding: "6px 10px",
          background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
        }}
      >
        <div style={{ fontWeight: 600, marginBottom: 2 }}>{label}</div>
        <div>Gerçekleşen: {formatMetricValue(point.value, unit)}</div>
        {targetValue != null && <div style={{ color: ink.secondary }}>Hedef: {formatMetricValue(targetValue, unit)}</div>}
      </div>
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={points} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
          <YAxis tick={{ fontSize: 11, fill: ink.muted }} tickLine={false} axisLine={false} width={40} />
          {targetValue != null && (
            <ReferenceLine
              y={targetValue}
              stroke={dataSecondaryColor(isDark)}
              strokeDasharray="4 4"
              label={{ value: "Hedef", fontSize: 10, fontWeight: 600, fill: ink.secondary, position: "insideTopRight" }}
            />
          )}
          {worstPoint && (
            <ReferenceDot
              x={worstPoint.date}
              y={worstPoint.value}
              r={5}
              fill={statusChartColor("negative", isDark)}
              stroke={isDark ? "#1a2333" : "#ffffff"}
              strokeWidth={2}
              label={{ value: `En kötü gün: ${formatMetricValue(worstPoint.value, unit)}`, fontSize: 10, fill: statusChartColor("negative", isDark), position: "top" }}
            />
          )}
          <Tooltip content={renderTooltip} />
          <Line type="monotone" dataKey="value" stroke={accentLineColor(isDark)} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap items-center gap-3 rounded-md p-3 text-[13px]" style={{ background: "var(--page-bg)" }}>
        <span style={{ color: "var(--text-muted)" }}>{points[0].date}:</span>
        <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{formatMetricValue(startValue, unit)}</span>
        <span style={{ color: "var(--text-muted)" }}>→</span>
        <span style={{ color: "var(--text-muted)" }}>{points[points.length - 1].date}:</span>
        <span className="font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{formatMetricValue(endValue, unit)}</span>
        <span style={{ color: "var(--text-muted)" }}>Dönem değişimi</span>
        <span className="font-semibold tabular-nums" style={{ color: PERFORMANCE_COLORS[perfDir] }}>
          {formatSignedUnitDiff(change, unit)}
          {changePct != null && ` (${formatSignedPct(changePct)})`} · {PERFORMANCE_LABELS[perfDir]}
        </span>
      </div>
    </div>
  );
}
