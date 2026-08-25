import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { KeyboardEvent } from "react";
import { dataSecondaryColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { useViewportTier } from "../../hooks/useViewportTier";
import { EmptyState } from "../StateViews";

interface Item {
  id?: string;
  name: string;
  score: number;
  color: string;
}

export function RankingBarChart({ items, onSelect }: { items: Item[]; onSelect?: (item: Item) => void }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const isCompact = useViewportTier() === "compact";

  if (items.length === 0) return <EmptyState />;

  const height = Math.max(120, items.length * (isCompact ? 27 : 32));

  const handleSelect = (entry: { payload?: Item }) => {
    if (onSelect && entry.payload?.id) onSelect(entry.payload);
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={items} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} horizontal={false} />
        <XAxis type="number" tick={{ fontSize: isCompact ? 10 : 11, fill: ink.muted }} tickLine={false} axisLine={{ stroke: ink.axis }} />
        <YAxis
          type="category"
          dataKey="name"
          width={isCompact ? 118 : 140}
          tick={{ fontSize: isCompact ? 11 : 12, fill: ink.secondary }}
          tickLine={false}
          axisLine={false}
        />
        <ReferenceLine x={100} stroke={dataSecondaryColor(isDark)} strokeDasharray="4 4" />
        <Tooltip
          formatter={(value) => [Number(value).toFixed(1), "Puan"]}
          contentStyle={{
            fontSize: 12, borderRadius: 8, border: `1px solid ${ink.grid}`,
            background: isDark ? "#1a2333" : "#ffffff", color: ink.primary,
          }}
          labelStyle={{ color: ink.primary }}
          itemStyle={{ color: ink.primary }}
        />
        <Bar
          dataKey="score"
          radius={[0, 4, 4, 0]}
          barSize={isCompact ? 15 : 18}
          cursor={onSelect ? "pointer" : undefined}
          tabIndex={onSelect ? 0 : undefined}
          role={onSelect ? "button" : undefined}
          onClick={handleSelect}
          onKeyDown={(entry: { payload?: Item }, _index: number, e: KeyboardEvent) => {
            if (!onSelect) return;
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleSelect(entry);
            }
          }}
        >
          {items.map((item, idx) => (
            <Cell key={idx} fill={item.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
