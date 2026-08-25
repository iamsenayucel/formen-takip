import { AlertTriangle, ArrowRight, Factory, Gauge, TrendingUp } from "lucide-react";
import type { ShiftAnomalyCard as ShiftAnomalyCardData } from "../api/types";
import { ShiftComparisonMiniChart } from "./charts/ShiftComparisonMiniChart";
import { statusChartColor } from "../lib/chartColors";
import { useTheme } from "../context/ThemeContext";

const SEVERITY_LABEL: Record<ShiftAnomalyCardData["severity"], string> = { high: "Yüksek", medium: "Orta" };

function severityColor(severity: ShiftAnomalyCardData["severity"], isDark: boolean): string {
  return statusChartColor(severity === "high" ? "negative" : "neutral", isDark);
}

export function ShiftAnomalySeverityBadge({ severity }: { severity: ShiftAnomalyCardData["severity"] }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const color = severityColor(severity, isDark);
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium"
      style={{ background: `${color}14`, color, border: `1px solid ${color}33` }}
    >
      <AlertTriangle size={12} strokeWidth={2} />
      {SEVERITY_LABEL[severity]} Anomali
    </span>
  );
}

export function ShiftAnomalyCard({
  card, onViewDetail,
}: {
  card: ShiftAnomalyCardData;
  onViewDetail: (card: ShiftAnomalyCardData) => void;
}) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const decimalPlaces = card.kpiDecimalPlaces;
  const severityAccent = severityColor(card.severity, isDark);

  return (
    <div
      className="flex flex-col gap-3 rounded-lg p-4"
      style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderTop: `2px solid ${severityAccent}`,
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5 text-[13px] font-medium" style={{ color: "var(--text-secondary)" }}>
          <Factory size={13} strokeWidth={2} />
          <span>{card.factoryCode}</span>
          <span>·</span>
          <span style={{ color: "var(--text-primary)" }}>{card.plantName}</span>
          <span>·</span>
          <span>{card.shiftName}</span>
          <span>·</span>
          <span className="inline-flex items-center gap-1">
            <Gauge size={13} strokeWidth={2} />
            {card.kpiName}
          </span>
        </div>
        <ShiftAnomalySeverityBadge severity={card.severity} />
      </div>

      <ShiftComparisonMiniChart better={card.better} worse={card.worse} unit={card.kpiUnit} decimalPlaces={decimalPlaces} />

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{card.worse.name}</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--status-negative)" }}>
            {card.worse.avgActual.toFixed(decimalPlaces)}
          </p>
        </div>
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{card.better.name}</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--status-positive)" }}>
            {card.better.avgActual.toFixed(decimalPlaces)}
          </p>
        </div>
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Mutlak Fark</p>
          <p className="mt-0.5 text-sm font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
            {card.absDiff.toFixed(decimalPlaces)}
          </p>
        </div>
        <div className="rounded-md p-2" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Yüzdesel Fark</p>
          <p className="mt-0.5 flex items-center gap-1 text-sm font-semibold tabular-nums" style={{ color: severityAccent }}>
            <TrendingUp size={13} strokeWidth={2.25} />
            %{card.pctDiff.toFixed(1)}
          </p>
        </div>
      </div>

      <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>
        {card.period.label} · Karşılaştırılan hafta sayısı: {card.comparedWeeks}
      </p>

      <button
        onClick={() => onViewDetail(card)}
        className="group mt-1 inline-flex items-center justify-center gap-1.5 rounded-md py-2 text-[13px] font-medium transition-colors hover:bg-[var(--page-bg)]"
        style={{ border: "1px solid var(--border)", color: "var(--accent)" }}
      >
        Detayı Gör
        <ArrowRight size={14} strokeWidth={2} className="transition-transform duration-150 group-hover:translate-x-0.5" />
      </button>
    </div>
  );
}
