import type { DowntimeBreakdown, InvestigationImpact } from "../../api/types";
import { KpiBreakdownCard } from "./KpiBreakdownCard";

export function ImpactAnalysis({
  impact, downtimeBreakdown, kpiName,
}: {
  impact: InvestigationImpact;
  downtimeBreakdown: DowntimeBreakdown | null;
  kpiName: string | null;
}) {
  const hasDowntime = impact.additionalDowntimeMinutes != null;
  const hasAnyValue = hasDowntime;

  if (!hasAnyValue) {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>Operasyonel etki hesaplanamadı</p>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Üretim hızı ve birim maliyet verileri mevcut olmadığı için üretim ve maliyet etkisi hesaplanamıyor.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg p-3.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
        <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Ek Duruş</p>
        <p className="text-xl font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>
          {impact.additionalDowntimeMinutes! > 0 ? "+" : ""}{impact.additionalDowntimeMinutes} dk
        </p>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>Üretim kaybı ve maliyet etkisi için gerekli veriler mevcut değil.</p>
      </div>
      {downtimeBreakdown && (
        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            {kpiName ?? "KPI"} Dağılımı
          </p>
          <KpiBreakdownCard breakdown={downtimeBreakdown} />
        </div>
      )}
    </div>
  );
}
