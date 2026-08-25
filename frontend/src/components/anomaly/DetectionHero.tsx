import { Factory } from "lucide-react";
import type { AnomalyDetail, AnomalyStatus } from "../../api/types";
import { AnalysisStatusBadge, SeverityBadge, StatusBadge } from "../AnomalyBadges";
import { fieldClass, fieldStyle } from "../../lib/formStyles";
import { formatDateRangeTR, formatDateTR } from "../../lib/dateFormat";
import { PrimaryKpiSummary } from "./PrimaryKpiSummary";

const STATUS_OPTIONS: { value: AnomalyStatus; label: string }[] = [
  { value: "new", label: "Yeni" },
  { value: "in_review", label: "İnceleniyor" },
  { value: "action_pending", label: "Aksiyon Bekliyor" },
  { value: "resolved", label: "Çözüldü" },
  { value: "closed", label: "Kapatıldı" },
];

export function DetectionHero({
  anomaly, statusPending, onStatusChange,
}: {
  anomaly: AnomalyDetail;
  statusPending: boolean;
  onStatusChange: (status: AnomalyStatus) => void;
}) {
  const a = anomaly;
  const aboveBelow =
    a.targetValue != null
      ? a.observedValue >= a.targetValue
        ? "ÜZERİNDE"
        : "ALTINDA"
      : a.deviationPercent >= 0
        ? "ÜZERİNDE"
        : "ALTINDA";
  const headline = `${(a.kpiName ?? "KPI").toUpperCase()} HEDEFİN ${aboveBelow}`;

  return (
    <div className="rounded-lg p-6" style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: "3px solid var(--accent)" }}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={a.severity} />
          <StatusBadge status={a.status} />
          <AnalysisStatusBadge status={a.analysisStatus} />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>Tespit durumu:</label>
          <select
            className={fieldClass}
            style={{ ...fieldStyle, width: 170 }}
            value={a.status}
            disabled={statusPending}
            onChange={(e) => onStatusChange(e.target.value as AnomalyStatus)}
          >
            {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      <div className="text-body mt-4 flex items-center gap-1.5 font-medium" style={{ color: "var(--text-secondary)" }}>
        <Factory size={13} strokeWidth={2} />
        {a.factoryCode} → {a.plantName}
        {a.shiftName && <span> · {a.shiftName}</span>}
        <span> · {formatDateRangeTR(a.periodStart, a.periodEnd)}</span>
      </div>

      <h1 className="text-page-title mt-1.5" style={{ color: "var(--text-primary)" }}>{headline}</h1>

      <div className="mt-5">
        <PrimaryKpiSummary anomaly={a} />
      </div>

      <div className="text-metadata mt-4 flex flex-wrap items-center gap-x-4 gap-y-1" style={{ color: "var(--text-muted)" }}>
        <span>Tespit tarihi: {formatDateTR(a.detectedAt)}</span>
        <span>Tespit ID: {a.code}</span>
      </div>
    </div>
  );
}
