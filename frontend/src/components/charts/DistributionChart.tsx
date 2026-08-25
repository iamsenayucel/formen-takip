import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { KeyboardEvent } from "react";
import type { DistributionItem } from "../../api/types";
import { resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { useViewportTier } from "../../hooks/useViewportTier";
import { EmptyState } from "../StateViews";

function CustomTooltip({
  active, payload,
}: {
  active?: boolean;
  payload?: { payload: DistributionItem & { pct: number } }[];
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;

  return (
    <div
      className="rounded-lg px-3 py-2.5 text-xs"
      style={{ border: `1px solid ${ink.grid}`, background: isDark ? "#1a2333" : "#ffffff", color: ink.primary, minWidth: 150 }}
    >
      <p className="mb-1 text-[13px] font-semibold">{item.name}</p>
      <div className="flex items-center justify-between gap-4">
        <span style={{ color: ink.secondary }}>Formen</span>
        <span className="font-medium tabular-nums">{item.count}</span>
      </div>
      <div className="flex items-center justify-between gap-4">
        <span style={{ color: ink.secondary }}>Oran</span>
        <span className="font-medium tabular-nums">%{item.pct.toFixed(0)}</span>
      </div>
    </div>
  );
}

export function DistributionChart({ items, onSelect }: { items: DistributionItem[]; onSelect?: (item: DistributionItem) => void }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const isCompact = useViewportTier() === "compact";

  const total = items.reduce((sum, i) => sum + i.count, 0);
  if (total === 0) return <EmptyState />;

  const data = items.map((item) => ({ ...item, pct: (item.count / total) * 100 }));

  const handleSelect = (entry: { payload?: DistributionItem }) => {
    if (onSelect && entry.payload && entry.payload.count > 0) onSelect(entry.payload);
  };

  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between">
        <span className="text-label" style={{ color: "var(--text-muted)" }}>
          Toplam
        </span>
        <span className="text-card-title tabular-nums" style={{ color: "var(--text-primary)" }}>
          {total} Formen
        </span>
      </div>

      <ResponsiveContainer width="100%" height={isCompact ? 200 : 240}>
        <BarChart data={data} margin={{ top: 20, right: 16, left: -8, bottom: 4 }}>
          <XAxis
            dataKey="name"
            tick={{ fontSize: isCompact ? 10 : 11, fill: ink.secondary }}
            tickLine={false}
            axisLine={{ stroke: ink.axis }}
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: isCompact ? 10 : 11, fill: ink.muted }}
            tickLine={false}
            axisLine={false}
            width={32}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: isDark ? "#ffffff0d" : "#0000000a" }} />
          <Bar
            dataKey="count"
            radius={[4, 4, 0, 0]}
            barSize={isCompact ? 36 : 48}
            cursor={onSelect ? "pointer" : undefined}
            tabIndex={onSelect ? 0 : undefined}
            role={onSelect ? "button" : undefined}
            onClick={handleSelect}
            onKeyDown={(entry: { payload?: DistributionItem }, _index: number, e: KeyboardEvent) => {
              if (!onSelect) return;
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleSelect(entry);
              }
            }}
          >
            {data.map((item) => (
              <Cell key={item.name} fill={item.color} />
            ))}
            <LabelList dataKey="count" position="top" fontSize={12} fontWeight={600} fill={ink.primary} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
