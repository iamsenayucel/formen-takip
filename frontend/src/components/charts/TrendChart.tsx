import { useId } from "react";
import { AlertTriangle } from "lucide-react";
import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { TrendPoint } from "../../api/types";
import { accentLineColor, dataSecondaryColor, dataTargetColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { useViewportTier } from "../../hooks/useViewportTier";
import { formatAxisDateTR } from "../../lib/dateFormat";
import { EmptyState } from "../StateViews";

const TARGET_SCORE = 100;

interface MergedPoint {
  date: string;
  totalScore: number | null;
  compareScore: number | null;
}

function mergeByDate(points: TrendPoint[], comparePoints: TrendPoint[] | undefined): MergedPoint[] {
  const primaryByDate = new Map(points.map((p) => [p.date, p.totalScore]));
  const compareByDate = new Map((comparePoints ?? []).map((p) => [p.date, p.totalScore]));
  const dates = Array.from(new Set([...primaryByDate.keys(), ...compareByDate.keys()])).sort();
  return dates.map((date) => ({
    date,
    totalScore: primaryByDate.get(date) ?? null,
    compareScore: compareByDate.get(date) ?? null,
  }));
}

function TooltipShell({ label, ink, isDark, children }: { label?: string; ink: ReturnType<typeof resolveChartInk>; isDark: boolean; children: React.ReactNode }) {
  return (
    <div
      className="rounded-lg px-3 py-2.5 text-xs"
      style={{ border: `1px solid ${ink.grid}`, background: isDark ? "#1a2333" : "#ffffff", color: ink.primary, minWidth: 180 }}
    >
      <p className="mb-1.5 text-[13px] font-semibold">{label}</p>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function TooltipRow({ label, value, ink, strong }: { label: string; value: string; ink: ReturnType<typeof resolveChartInk>; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4" style={strong ? { borderTop: `1px solid ${ink.grid}`, paddingTop: 4 } : undefined}>
      <span style={{ color: ink.secondary }}>{label}</span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  );
}

function CompareTooltip({
  active,
  payload,
  label,
  seriesLabel,
  compareLabel,
}: {
  active?: boolean;
  payload?: { dataKey?: string; value?: number }[];
  label?: string;
  seriesLabel: string;
  compareLabel: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;

  const primary = payload.find((p) => p.dataKey === "totalScore")?.value;
  const compare = payload.find((p) => p.dataKey === "compareScore")?.value;
  const diff = primary != null && compare != null ? primary - compare : null;
  if (primary == null && compare == null) return null;

  return (
    <TooltipShell label={label} ink={ink} isDark={isDark}>
      {primary != null && <TooltipRow label={seriesLabel} value={primary.toFixed(1)} ink={ink} />}
      {compare != null && <TooltipRow label={compareLabel} value={compare.toFixed(1)} ink={ink} />}
      {diff != null && (
        <div className="flex items-center justify-between gap-4 border-t pt-1" style={{ borderColor: ink.grid }}>
          <span style={{ color: ink.secondary }}>Fark</span>
          <span className="font-medium tabular-nums" style={{ color: diff >= 0 ? "var(--status-positive)" : "var(--status-negative)" }}>
            {diff >= 0 ? "+" : ""}{diff.toFixed(1)}
          </span>
        </div>
      )}
    </TooltipShell>
  );
}

function SingleTooltip({
  active,
  payload,
  label,
  seriesLabel,
}: {
  active?: boolean;
  payload?: { dataKey?: string; value?: number }[];
  label?: string;
  seriesLabel: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;

  const score = payload.find((p) => p.dataKey === "totalScore")?.value;
  if (score == null) return null;
  const diff = score - TARGET_SCORE;

  return (
    <TooltipShell label={label} ink={ink} isDark={isDark}>
      <TooltipRow label={seriesLabel} value={score.toFixed(1)} ink={ink} />
      <TooltipRow label="Hedef" value={TARGET_SCORE.toFixed(0)} ink={ink} />
      <div className="flex items-center justify-between gap-4 border-t pt-1" style={{ borderColor: ink.grid }}>
        <span style={{ color: ink.secondary }}>Hedefe Fark</span>
        <span className="font-medium tabular-nums" style={{ color: diff >= 0 ? "var(--status-positive)" : "var(--status-negative)" }}>
          {diff >= 0 ? "+" : ""}{diff.toFixed(1)}
        </span>
      </div>
    </TooltipShell>
  );
}

export function TrendChart({
  points,
  yAxisFloor,
  comparePoints,
  compareLabel = "Fabrika Ortalaması",
  seriesLabel = "Formen",
}: {
  points: TrendPoint[];
  yAxisFloor?: number;
  comparePoints?: TrendPoint[];
  compareLabel?: string;
  seriesLabel?: string;
}) {
  const gradientId = useId();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const primaryColor = accentLineColor(isDark);
  const compareColor = dataSecondaryColor(isDark);
  const targetColor = dataTargetColor();
  const showCompare = !!comparePoints && comparePoints.length > 0;
  const tier = useViewportTier();
  const isCompact = tier === "compact";
  const axisFontSize = isCompact ? 10 : 11;
  const chartHeight = showCompare ? (isCompact ? 260 : 320) : isCompact ? 220 : 280;

  if (points.length === 0 && !showCompare) return <EmptyState />;

  const data = mergeByDate(points, comparePoints);
  const hasUnreliable = points.some((p) => !p.isReliable);
  const domainMin = yAxisFloor !== undefined ? Math.max(0, Math.floor(yAxisFloor)) : 0;
  const tickInterval = data.length > 10 ? Math.ceil(data.length / 7) - 1 : 0;

  let lastIndex = -1;
  for (let i = data.length - 1; i >= 0; i--) {
    if (data[i].totalScore != null) {
      lastIndex = i;
      break;
    }
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={chartHeight}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id={`trend-fill-${gradientId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={primaryColor} stopOpacity={0.18} />
              <stop offset="100%" stopColor={primaryColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} strokeOpacity={0.7} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatAxisDateTR}
            interval={tickInterval}
            tick={{ fontSize: axisFontSize, fill: ink.muted }}
            tickLine={false}
            axisLine={{ stroke: ink.axis }}
          />
          <YAxis
            domain={[domainMin, "auto"]}
            tickFormatter={(v: number) => `${Math.round(v)}`}
            tick={{ fontSize: axisFontSize, fill: ink.muted }}
            tickLine={false}
            axisLine={false}
            width={36}
          />
          <ReferenceLine
            y={TARGET_SCORE}
            stroke={targetColor}
            strokeDasharray="4 4"
            label={{ value: `Hedef ${TARGET_SCORE}`, fontSize: axisFontSize, fontWeight: 600, fill: ink.secondary, position: "insideTopRight" }}
          />
          {showCompare ? (
            <Tooltip content={<CompareTooltip seriesLabel={seriesLabel} compareLabel={compareLabel} />} />
          ) : (
            <Tooltip content={<SingleTooltip seriesLabel={seriesLabel} />} />
          )}
          {showCompare && <Legend wrapperStyle={{ fontSize: axisFontSize + 1, color: ink.secondary }} />}
          {showCompare && (
            <Line
              type="monotone"
              dataKey="compareScore"
              name={compareLabel}
              stroke={compareColor}
              strokeWidth={1.5}
              strokeDasharray="4 3"
              dot={false}
              connectNulls
              activeDot={{ r: 3 }}
            />
          )}
          <Area
            type="monotone"
            dataKey="totalScore"
            stroke="none"
            fill={`url(#trend-fill-${gradientId})`}
            connectNulls
            isAnimationActive={false}
            legendType="none"
            activeDot={false}
          />
          <Line
            type="monotone"
            dataKey="totalScore"
            name={seriesLabel}
            stroke={primaryColor}
            strokeWidth={2.25}
            dot={(dotProps: { cx?: number; cy?: number; index?: number; payload?: MergedPoint }) => {
              const { cx, cy, index, payload } = dotProps;
              const key = `trend-dot-${index}`;
              if (payload?.totalScore == null || index !== lastIndex || cx == null || cy == null) {
                return <g key={key} />;
              }
              return (
                <g key={key}>
                  <circle cx={cx} cy={cy} r={7} fill={primaryColor} fillOpacity={0.16} />
                  <circle cx={cx} cy={cy} r={3.5} fill={primaryColor} stroke={isDark ? "#0b1220" : "#ffffff"} strokeWidth={1.5} />
                </g>
              );
            }}
            connectNulls
            activeDot={{ r: 4 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
      {hasUnreliable && (
        <div
          className="mt-2 flex items-start gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium"
          style={{ background: "var(--status-neutral-bg)", color: "var(--status-neutral)", border: "1px solid var(--status-neutral-border)" }}
        >
          <AlertTriangle size={12} strokeWidth={2} className="mt-0.5 shrink-0" />
          Bazı dönemlerde eksik KPI verisi nedeniyle puan yeniden normalize edildi — güvenilirlik sınırlı olabilir.
        </div>
      )}
    </div>
  );
}
