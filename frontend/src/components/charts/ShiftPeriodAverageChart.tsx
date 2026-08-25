import { Bar, BarChart, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ShiftAnomalyForemanStat } from "../../api/types";
import { categoricalColor, dataTargetColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";

function formatValue(value: number, unit: string, decimalPlaces: number): string {
  return `${value.toFixed(decimalPlaces)} ${unit}`;
}

function CustomTooltip({
  active, payload, unit, decimalPlaces, target, betterId,
}: {
  active?: boolean;
  payload?: { payload: { name: string; value: number; id: string } }[];
  unit: string;
  decimalPlaces: number;
  target: number;
  betterId: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const diffFromTarget = point.value - target;

  return (
    <div
      className="rounded-lg px-3 py-2.5 text-xs"
      style={{ border: `1px solid ${ink.grid}`, background: isDark ? "#1a2333" : "#ffffff", color: ink.primary, minWidth: 190 }}
    >
      <p className="mb-1.5 text-[13px] font-semibold">{point.name}</p>
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Dönem Ortalaması</span>
          <span className="font-medium tabular-nums">{formatValue(point.value, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Hedef</span>
          <span className="font-medium tabular-nums">{formatValue(target, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4 border-t pt-1" style={{ borderColor: ink.grid }}>
          <span style={{ color: ink.secondary }}>Hedeften Fark</span>
          <span className="font-medium tabular-nums">
            {diffFromTarget >= 0 ? "+" : ""}
            {formatValue(diffFromTarget, unit, decimalPlaces)}
          </span>
        </div>
      </div>
      {point.id === betterId && (
        <p className="mt-1.5 border-t pt-1.5 text-[11px] font-medium" style={{ borderColor: ink.grid, color: ink.secondary }}>
          Daha iyi performans
        </p>
      )}
    </div>
  );
}

export function ShiftPeriodAverageChart({
  better, worse, target, unit, decimalPlaces = 1,
}: {
  better: ShiftAnomalyForemanStat;
  worse: ShiftAnomalyForemanStat;
  target: number;
  unit: string;
  decimalPlaces?: number;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);

  const data = [
    { id: worse.id, name: worse.name, value: worse.avgActual },
    { id: better.id, name: better.name, value: better.avgActual },
  ];
  const values = [...data.map((d) => d.value), target];
  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const pad = (dataMax - dataMin) * 0.25 || Math.abs(target) * 0.1 || 1;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 20, right: 16, left: -4, bottom: 4 }}>
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: ink.secondary }} tickLine={false} axisLine={{ stroke: ink.axis }} />
        <YAxis
          domain={[dataMin - pad, dataMax + pad]}
          tick={{ fontSize: 11, fill: ink.muted }}
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
        <Tooltip content={<CustomTooltip unit={unit} decimalPlaces={decimalPlaces} target={target} betterId={better.id} />} cursor={{ fill: isDark ? "#ffffff0d" : "#0000000a" }} />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={56} isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell key={d.id} fill={categoricalColor(i, isDark)} />
          ))}
          <LabelList dataKey="value" position="top" fontSize={12} fontWeight={600} fill={ink.primary} formatter={(v) => Number(v).toFixed(decimalPlaces)} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
