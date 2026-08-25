import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { KeyboardEvent } from "react";
import type { KpiSummaryItem } from "../../api/types";
import { accentLineColor, dataSecondaryColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { useViewportTier } from "../../hooks/useViewportTier";
import { EmptyState } from "../StateViews";

export interface KpiBarChartDatum {
  id: string;
  name: string;
  score: number;
  unit: string;
}

export function KpiBarChart({
  items,
  onSelect,
}: {
  items: KpiSummaryItem[];
  onSelect?: (item: KpiBarChartDatum) => void;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const isCompact = useViewportTier() === "compact";
  const axisFontSize = isCompact ? 10 : 11;

  if (items.length === 0) return <EmptyState />;

  const data: KpiBarChartDatum[] = items.map((i) => ({ id: i.kpiId, name: i.name, score: i.avgScore, unit: i.unit }));

  const handleSelect = (entry: { payload?: KpiBarChartDatum }) => {
    if (onSelect && entry.payload?.id) onSelect(entry.payload);
  };

  return (
    <ResponsiveContainer width="100%" height={isCompact ? 220 : 260}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: axisFontSize, fill: ink.muted }}
          tickLine={false}
          axisLine={{ stroke: ink.axis }}
          interval={0}
          angle={-15}
          textAnchor="end"
          height={isCompact ? 42 : 50}
        />
        <YAxis tick={{ fontSize: axisFontSize, fill: ink.muted }} tickLine={false} axisLine={false} width={32} />
        <ReferenceLine y={100} stroke={dataSecondaryColor(isDark)} strokeDasharray="4 4" />
        <Tooltip
          formatter={(value) => [Number(value).toFixed(1), "Ortalama KPI Puanı"]}
          contentStyle={{
            fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
            background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
          }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.primary }}
        />
        <Bar
          dataKey="score"
          fill={accentLineColor(isDark)}
          radius={[4, 4, 0, 0]}
          barSize={isCompact ? 28 : 40}
          cursor={onSelect ? "pointer" : undefined}
          tabIndex={onSelect ? 0 : undefined}
          role={onSelect ? "button" : undefined}
          onClick={handleSelect}
          onKeyDown={(entry: { payload?: KpiBarChartDatum }, _index: number, e: KeyboardEvent) => {
            if (!onSelect) return;
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleSelect(entry);
            }
          }}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
