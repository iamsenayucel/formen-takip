import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ShiftAnomalyForemanStat, ShiftWeeklyComparisonPoint, ShiftWeeklyForemanPoint } from "../../api/types";
import { categoricalColor, dataTargetColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { useViewportTier } from "../../hooks/useViewportTier";
import { EmptyState } from "../StateViews";

interface WeekRow {
  weekLabel: string;
  betterValue: number | null;
  worseValue: number | null;
  better: ShiftWeeklyForemanPoint;
  worse: ShiftWeeklyForemanPoint;
}

function statusLine(name: string, point: ShiftWeeklyForemanPoint, shiftName: string, unit: string, decimalPlaces: number): string {
  const shiftSuffix = point.shiftName ? ` (${point.shiftName})` : "";
  if (point.assigned && point.value !== null) {
    return `${name}${shiftSuffix}: ${point.value.toFixed(decimalPlaces)} ${unit} · ${point.dayCount} gün veri`;
  }
  if (point.assigned && !point.hasSufficientData) {
    return `${name}${shiftSuffix}: görevli, ancak bu KPI için yeterli veri yok`;
  }
  return `${name}: bu hafta ${shiftName}'da görevli değil`;
}

function CustomTooltip({
  active, payload, better, worse, shiftName, unit, decimalPlaces,
}: {
  active?: boolean;
  payload?: { payload: WeekRow }[];
  better: ShiftAnomalyForemanStat;
  worse: ShiftAnomalyForemanStat;
  shiftName: string;
  unit: string;
  decimalPlaces: number;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;

  return (
    <div
      className="rounded-lg px-3 py-2.5 text-xs"
      style={{ border: `1px solid ${ink.grid}`, background: isDark ? "#1a2333" : "#ffffff", color: ink.primary, minWidth: 240 }}
    >
      <p className="mb-1.5 text-[13px] font-semibold">{row.weekLabel}</p>
      <div className="flex flex-col gap-1.5">
        <div className="flex items-start gap-1.5">
          <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: categoricalColor(1, isDark) }} />
          <span>{statusLine(better.name, row.better, shiftName, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-start gap-1.5">
          <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: categoricalColor(0, isDark) }} />
          <span>{statusLine(worse.name, row.worse, shiftName, unit, decimalPlaces)}</span>
        </div>
      </div>
    </div>
  );
}

export function ShiftRotationTrendChart({
  points, better, worse, shiftName, target, unit, decimalPlaces = 1,
}: {
  points: ShiftWeeklyComparisonPoint[];
  better: ShiftAnomalyForemanStat;
  worse: ShiftAnomalyForemanStat;
  shiftName: string;
  target: number;
  unit: string;
  decimalPlaces?: number;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const tier = useViewportTier();
  const isCompact = tier === "compact";

  if (points.length === 0) return <EmptyState message="Haftalık kırılım verisi bulunamadı." />;

  const data: WeekRow[] = [...points]
    .sort((a, b) => a.weekIndex - b.weekIndex)
    .map((p) => ({
      weekLabel: p.weekLabel,
      betterValue: p.better.value,
      worseValue: p.worse.value,
      better: p.better,
      worse: p.worse,
    }));

  const definedValues = data.flatMap((d) => [d.betterValue, d.worseValue]).filter((v): v is number => v !== null);
  const values = [...definedValues, target];
  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const pad = (dataMax - dataMin) * 0.2 || Math.abs(target) * 0.1 || 1;

  return (
    <ResponsiveContainer width="100%" height={isCompact ? 240 : 280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} strokeOpacity={0.7} vertical={false} />
        <XAxis dataKey="weekLabel" tick={{ fontSize: isCompact ? 10 : 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
        <YAxis
          domain={[dataMin - pad, dataMax + pad]}
          tick={{ fontSize: isCompact ? 10 : 11, fill: ink.muted }}
          tickLine={false}
          axisLine={false}
          width={40}
          tickFormatter={(v: number) => v.toFixed(decimalPlaces)}
        />
        <ReferenceLine
          y={target}
          stroke={dataTargetColor()}
          strokeDasharray="6 4"
          strokeWidth={1.5}
          label={{ value: `Hedef ${target.toFixed(decimalPlaces)}`, fontSize: 11, fontWeight: 600, fill: ink.secondary, position: "insideTopRight" }}
        />
        <Tooltip
          content={<CustomTooltip better={better} worse={worse} shiftName={shiftName} unit={unit} decimalPlaces={decimalPlaces} />}
          cursor={{ stroke: ink.axis, strokeDasharray: "3 3" }}
        />
        <Line
          type="monotone"
          dataKey="worseValue"
          name={worse.name}
          stroke={categoricalColor(0, isDark)}
          strokeWidth={2}
          dot={{ r: 3.5, fill: categoricalColor(0, isDark), strokeWidth: 0 }}
          activeDot={{ r: 5 }}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="betterValue"
          name={better.name}
          stroke={categoricalColor(1, isDark)}
          strokeWidth={2}
          dot={{ r: 3.5, fill: categoricalColor(1, isDark), strokeWidth: 0 }}
          activeDot={{ r: 5 }}
          connectNulls={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
