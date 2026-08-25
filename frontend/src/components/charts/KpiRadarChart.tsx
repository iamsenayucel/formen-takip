import { Legend, PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import { accentLineColor, dataSecondaryColor, resolveChartInk } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";

interface RadarSeriesItem {
  code: string;
  avgCappedScore: number;
}

interface CompareSeriesItem {
  code: string;
  avgScore: number;
}

const KPI_SHORT_LABELS: Record<string, string> = {
  AGIR_GITME: "Ağır Gitme",
  GSF: "GSF",
  ISKARTA: "Iskarta",
  INKITA: "İnkita",
  PLANA_UYUM: "Plana Uyum",
  OEE: "OEE",
};

function kpiShortLabel(code: string): string {
  return KPI_SHORT_LABELS[code] ?? code;
}

function RadarCompareTooltip({
  active,
  payload,
  seriesLabel,
  compareLabel,
}: {
  active?: boolean;
  payload?: { payload?: { subject?: string; score?: number; compare?: number } }[];
  seriesLabel: string;
  compareLabel: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;

  const point = payload[0]?.payload;
  if (!point) return null;
  const primary = point.score;
  const compare = point.compare;
  const diff = primary != null && compare != null ? primary - compare : null;

  return (
    <div
      className="rounded-lg px-3 py-2.5 text-xs"
      style={{ border: `1px solid ${ink.grid}`, background: isDark ? "#1a2333" : "#ffffff", color: ink.primary, minWidth: 190 }}
    >
      <p className="mb-1.5 text-[13px] font-semibold">{point.subject}</p>
      <div className="flex flex-col gap-1">
        {primary != null && (
          <div className="flex items-center justify-between gap-4">
            <span style={{ color: ink.secondary }}>{seriesLabel}</span>
            <span className="font-medium tabular-nums">{primary.toFixed(1)}</span>
          </div>
        )}
        {compare != null && (
          <div className="flex items-center justify-between gap-4">
            <span style={{ color: ink.secondary }}>{compareLabel}</span>
            <span className="font-medium tabular-nums">{compare.toFixed(1)}</span>
          </div>
        )}
        {diff != null && (
          <div className="flex items-center justify-between gap-4 border-t pt-1" style={{ borderColor: ink.grid }}>
            <span style={{ color: ink.secondary }}>Fark</span>
            <span className="font-medium tabular-nums" style={{ color: diff >= 0 ? "var(--status-positive)" : "var(--status-negative)" }}>
              {diff >= 0 ? "+" : ""}{diff.toFixed(1)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

export function KpiRadarChart({
  items,
  compareItems,
  compareLabel = "Fabrika Ortalaması",
  seriesLabel = "Formen",
}: {
  items: RadarSeriesItem[];
  compareItems?: CompareSeriesItem[];
  compareLabel?: string;
  seriesLabel?: string;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const lineColor = accentLineColor(isDark);
  const compareColor = dataSecondaryColor(isDark);

  if (items.length === 0) return <EmptyState />;
  const compareByCode = new Map((compareItems ?? []).map((c) => [c.code, c.avgScore]));
  const showCompare = !!compareItems;
  const data = items.map((i) => ({
    subject: kpiShortLabel(i.code),
    score: Math.min(i.avgCappedScore, 120),
    compare: showCompare ? Math.min(compareByCode.get(i.code) ?? 0, 120) : undefined,
  }));

  return (
    <ResponsiveContainer width="100%" height={showCompare ? 300 : 260}>
      <RadarChart data={data} outerRadius="75%">
        <PolarGrid stroke={ink.grid} />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: ink.secondary }} />
        <Radar name={seriesLabel} dataKey="score" stroke={lineColor} fill={lineColor} fillOpacity={0.25} strokeWidth={2} />
        {showCompare && (
          <Radar
            name={compareLabel}
            dataKey="compare"
            stroke={compareColor}
            fill={compareColor}
            fillOpacity={0.12}
            strokeWidth={2}
            strokeDasharray="4 3"
          />
        )}
        {showCompare && (
          <Legend wrapperStyle={{ fontSize: 12, color: ink.secondary }} />
        )}
        {showCompare ? (
          <Tooltip content={<RadarCompareTooltip seriesLabel={seriesLabel} compareLabel={compareLabel} />} />
        ) : (
          <Tooltip
            formatter={(value) => [Number(value).toFixed(1), "Puan"]}
            contentStyle={{ fontSize: 12, borderRadius: 8, background: isDark ? "#1a2333" : "#ffffff", color: ink.primary, border: `1px solid ${ink.grid}` }}
            labelStyle={{ color: ink.primary }}
            itemStyle={{ color: ink.primary }}
          />
        )}
      </RadarChart>
    </ResponsiveContainer>
  );
}
