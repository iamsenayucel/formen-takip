import { useMemo, useState } from "react";
import {
  CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import type { KpiForemanValueItem } from "../../api/types";
import { dataTargetColor, resolveChartInk, statusChartColor } from "../../lib/chartColors";
import { useTheme } from "../../context/ThemeContext";
import { EmptyState } from "../StateViews";
import { PerformanceLevelBadge } from "../PerformanceLevelBadge";
import { fieldClass, fieldStyle } from "../../lib/formStyles";

function tierColor(tier: KpiForemanValueItem["tier"], dark: boolean): string {
  if (tier === "better") return statusChartColor("positive", dark);
  if (tier === "near") return statusChartColor("neutral", dark);
  return statusChartColor("negative", dark);
}

const TIER_LABEL: Record<KpiForemanValueItem["tier"], string> = {
  better: "Hedefin Üzerinde Performans",
  near: "Hedefe Yakın Performans",
  worse: "Hedefin Altında Performans",
};

const TIER_STATUS_PHRASE: Record<KpiForemanValueItem["tier"], string> = {
  better: "hedefin üzerinde",
  near: "hedefe yakın",
  worse: "hedefin altında",
};

type SortMode = "name" | "best" | "worst" | "deviation";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "name", label: "Formen Adına Göre" },
  { value: "best", label: "En İyi Performanstan En Kötüye" },
  { value: "worst", label: "En Kötü Performanstan En İyiye" },
  { value: "deviation", label: "Hedeften Sapmaya Göre" },
];

function formatValue(value: number, unit: string, decimalPlaces: number): string {
  return `${value.toFixed(decimalPlaces)} ${unit}`;
}

function pctDeviation(actual: number, target: number): number {
  return target !== 0 ? Math.abs((actual - target) / target) * 100 : 0;
}

const TIER_QUALIFIER: Record<KpiForemanValueItem["tier"], string> = {
  better: "daha iyi",
  near: "hedefe yakın",
  worse: "daha kötü",
};

const MAX_LABEL_CHARS = 13;

function truncateLabel(name: string): string {
  if (name.length <= MAX_LABEL_CHARS) return name;
  return `${name.slice(0, MAX_LABEL_CHARS - 1)}…`;
}

function XAxisNameTick({
  x, y, payload, fill,
}: {
  x?: number;
  y?: number;
  payload?: { value: string };
  fill?: string;
}) {
  if (x === undefined || y === undefined || !payload) return null;
  const name = payload.value ?? "";
  const display = truncateLabel(name);
  return (
    <g transform={`translate(${x},${y})`}>
      <text x={0} y={0} dy={9} textAnchor="end" transform="rotate(-35)" fontSize={10} fill={fill}>
        {display}
        {display !== name && <title>{name}</title>}
      </text>
    </g>
  );
}

function niceTickStep(range: number, targetCount: number): number {
  const roughStep = range / Math.max(targetCount, 1);
  if (roughStep <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(roughStep));
  const residual = roughStep / magnitude;
  let niceResidual: number;
  if (residual > 5) niceResidual = 10;
  else if (residual > 2) niceResidual = 5;
  else if (residual > 1) niceResidual = 2;
  else niceResidual = 1;
  return niceResidual * magnitude;
}

function computeNiceTicks(min: number, max: number, targetCount = 5): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max) || min >= max) return [min];
  const step = niceTickStep(max - min, targetCount);
  const start = Math.ceil(min / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= max + step / 1e6; v += step) {
    ticks.push(Math.round(v / step) * step);
  }
  return ticks.length > 0 ? ticks : [min, max];
}

function CustomTooltip({
  active, payload, unit, decimalPlaces, target,
}: {
  active?: boolean;
  payload?: { payload: KpiForemanValueItem }[];
  unit: string;
  decimalPlaces: number;
  target: number;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  const raw = point.avgActual - target;
  const pct = pctDeviation(point.avgActual, target);

  return (
    <div
      className="rounded-lg px-3 py-2.5 text-xs"
      style={{
        border: `1px solid ${ink.grid}`,
        background: isDark ? "#1a2333" : "#ffffff",
        color: ink.primary,
        minWidth: 220,
      }}
    >
      <p className="mb-1.5 text-[13px] font-semibold">{point.fullName ?? "-"}</p>
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Gerçekleşen</span>
          <span className="font-medium tabular-nums">{formatValue(point.avgActual, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Fabrika Hedefi</span>
          <span className="font-medium tabular-nums">{formatValue(target, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Hedeften Fark</span>
          <span className="font-medium tabular-nums">{raw >= 0 ? "+" : ""}{formatValue(raw, unit, decimalPlaces)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span style={{ color: ink.secondary }}>Hedefe Göre Fark</span>
          <span className="font-medium tabular-nums" style={{ color: tierColor(point.tier, isDark) }}>
            %{pct.toFixed(1)} {TIER_QUALIFIER[point.tier]}
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 border-t pt-2" style={{ borderColor: ink.grid }}>
        <span style={{ color: ink.secondary }}>{TIER_LABEL[point.tier]}</span>
        {point.level && <PerformanceLevelBadge level={point.level} />}
      </div>
    </div>
  );
}

export function ForemanKpiTargetChart({
  points, target, unit, kpiName, decimalPlaces, subtitle, onSelectForeman,
}: {
  points: KpiForemanValueItem[];
  target: number | null;
  unit: string;
  kpiName: string;
  decimalPlaces: number;
  subtitle: string;
  onSelectForeman?: (foremanId: string) => void;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const ink = resolveChartInk(isDark);
  const [sortMode, setSortMode] = useState<SortMode>("name");
  const [activeForemanId, setActiveForemanId] = useState<string | null>(null);

  const sorted = useMemo(() => {
    const items = [...points];
    switch (sortMode) {
      case "best":
        return items.sort((a, b) => b.avgScore - a.avgScore);
      case "worst":
        return items.sort((a, b) => a.avgScore - b.avgScore);
      case "deviation": {
        const dev = (p: KpiForemanValueItem) => (target !== null ? pctDeviation(p.avgActual, target) : 0);
        return items.sort((a, b) => dev(b) - dev(a));
      }
      default:
        return items.sort((a, b) => (a.fullName ?? "").localeCompare(b.fullName ?? "", "tr"));
    }
  }, [points, sortMode, target]);

  if (points.length === 0 || target === null) {
    return <EmptyState message="Seçilen filtrelerle bu KPI için formen verisi bulunamadı." />;
  }

  const metCount = points.filter((p) => p.tier === "better").length;
  const bestPoint = points.reduce((best, p) => (p.avgScore > best.avgScore ? p : best), points[0]);
  const avgForemanActual = points.reduce((sum, p) => sum + p.avgActual, 0) / points.length;

  const values = points.map((p) => p.avgActual).concat(target);
  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);
  const pad = (dataMax - dataMin) * 0.2 || Math.abs(target) * 0.1 || 1;
  const yDomain: [number, number] = [dataMin - pad, dataMax + pad];
  const yTicks = computeNiceTicks(yDomain[0], yDomain[1], 5);

  const height = 280;
  const chartMinWidth = Math.max(sorted.length * 40, 480);

  const summaryItems = [
    { label: "Fabrika Hedefi", value: formatValue(target, unit, decimalPlaces) },
    { label: "Hedefi Karşılayan", value: `${metCount} / ${points.length}` },
    { label: "En İyi Sonuç", value: formatValue(bestPoint.avgActual, unit, decimalPlaces) },
    { label: "Ort. Gerçekleşen", value: formatValue(avgForemanActual, unit, decimalPlaces) },
  ];

  const renderPoint = (shapeProps: { cx?: number; cy?: number; payload?: KpiForemanValueItem }) => {
    const { cx, cy, payload } = shapeProps;
    if (cx === undefined || cy === undefined || !payload) return <g />;
    const isActive = activeForemanId === payload.foremanId;
    const isDimmed = activeForemanId !== null && !isActive;
    const radius = isActive ? 9 : 7;
    const color = tierColor(payload.tier, isDark);
    const ariaLabel = `${payload.fullName ?? "Bilinmeyen formen"}, gerçekleşen ${formatValue(payload.avgActual, unit, decimalPlaces)}, hedef ${formatValue(target, unit, decimalPlaces)}, ${TIER_STATUS_PHRASE[payload.tier]}`;
    const clearIfSelf = () => setActiveForemanId((cur) => (cur === payload.foremanId ? null : cur));
    return (
      <g
        tabIndex={onSelectForeman ? 0 : undefined}
        role={onSelectForeman ? "button" : undefined}
        aria-label={ariaLabel}
        style={{ cursor: onSelectForeman ? "pointer" : "default", outline: "none" }}
        onMouseEnter={() => setActiveForemanId(payload.foremanId)}
        onMouseLeave={clearIfSelf}
        onFocus={() => setActiveForemanId(payload.foremanId)}
        onBlur={clearIfSelf}
        onClick={() => onSelectForeman?.(payload.foremanId)}
        onKeyDown={(e) => {
          if (!onSelectForeman) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onSelectForeman(payload.foremanId);
          }
        }}
      >
        <circle cx={cx} cy={cy} r={radius + 6} fill="transparent" />
        {isActive && (
          <circle cx={cx} cy={cy} r={radius + 3} fill="none" stroke="var(--focus-ring)" strokeWidth={1.5} />
        )}
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill={color}
          fillOpacity={isDimmed ? 0.35 : 1}
          stroke="var(--surface)"
          strokeWidth={2}
          style={{ transition: "r 150ms ease, fill-opacity 150ms ease" }}
        />
      </g>
    );
  };

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-card-title" style={{ color: "var(--text-primary)" }}>
            {kpiName} — Formen Karşılaştırması
          </h3>
          <p className="mt-0.5 text-metadata" style={{ color: "var(--text-muted)" }}>{subtitle}</p>
        </div>
        <select
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value as SortMode)}
          className={fieldClass}
          style={{ ...fieldStyle, width: "auto" }}
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div
        className="mb-3 flex flex-col overflow-hidden rounded-md sm:flex-row"
        style={{ background: "var(--surface-inset)", border: "1px solid var(--border-subtle)" }}
      >
        {summaryItems.map((item, i) => (
          <div
            key={item.label}
            className={`flex-1 px-4 py-2.5 ${i > 0 ? "border-t sm:border-t-0 sm:border-l" : ""}`}
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <p className="text-label" style={{ color: "var(--text-muted)" }}>{item.label}</p>
            <p className="mt-0.5 text-[15px] font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{item.value}</p>
          </div>
        ))}
      </div>

      <div className="mb-2 flex flex-wrap items-center justify-end gap-x-4 gap-y-1" style={{ color: "var(--text-muted)" }}>
        <span className="flex items-center gap-1.5 text-[11px]"><span className="h-2 w-2 rounded-full" style={{ background: tierColor("better", isDark) }} />Hedefin Üzerinde</span>
        <span className="flex items-center gap-1.5 text-[11px]"><span className="h-2 w-2 rounded-full" style={{ background: tierColor("near", isDark) }} />Hedefe Yakın</span>
        <span className="flex items-center gap-1.5 text-[11px]"><span className="h-2 w-2 rounded-full" style={{ background: tierColor("worse", isDark) }} />Hedefin Altında</span>
        <span className="flex items-center gap-1.5 text-[11px]"><span className="inline-block h-0.5 w-3.5" style={{ background: dataTargetColor() }} />Fabrika Hedefi</span>
      </div>

      <div className="relative">
        <div
          className="pointer-events-none absolute right-1 top-0 z-10 rounded px-2 py-1 text-[11px] font-semibold"
          style={{
            background: isDark ? "#1a2333" : "#ffffff",
            color: ink.secondary,
            border: `1px solid ${dataTargetColor()}88`,
          }}
        >
          Fabrika Hedefi · {formatValue(target, unit, decimalPlaces)}
        </div>
        <div className="overflow-x-auto" style={{ contain: "inline-size" }}>
          <div style={{ minWidth: chartMinWidth }}>
            <ResponsiveContainer width="100%" height={height}>
              <ScatterChart data={sorted} margin={{ top: 28, right: 18, left: 4, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={ink.grid} strokeOpacity={isDark ? 0.5 : 0.7} vertical={false} />
                <XAxis
                  dataKey="fullName"
                  type="category"
                  allowDuplicatedCategory={false}
                  interval={0}
                  height={52}
                  tick={<XAxisNameTick fill={ink.muted} />}
                  tickLine={false}
                  axisLine={{ stroke: ink.axis }}
                />
                <YAxis
                  dataKey="avgActual"
                  type="number"
                  domain={yDomain}
                  ticks={yTicks}
                  tick={{ fontSize: 11, fill: ink.muted }}
                  tickLine={false}
                  axisLine={false}
                  width={48}
                  tickFormatter={(v) => Number(v).toFixed(decimalPlaces)}
                />
                <ReferenceLine
                  y={target}
                  stroke={dataTargetColor()}
                  strokeWidth={2}
                  strokeDasharray="6 4"
                />
                <Tooltip
                  content={<CustomTooltip unit={unit} decimalPlaces={decimalPlaces} target={target} />}
                  cursor={{ stroke: ink.axis, strokeDasharray: "3 3" }}
                />
                <Scatter shape={renderPoint} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
