import { Link } from "react-router-dom";
import type { AnomalyDetail } from "../../api/types";
import { formatDateRangeTR, formatDateTR } from "../../lib/dateFormat";
import { formatMetricValue } from "../../lib/anomalyMetrics";
import { isHigherBetter } from "../../lib/kpiDirection";

function ScopeField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      <div className="mt-0.5 text-[13px]" style={{ color: "var(--text-primary)" }}>{children}</div>
    </div>
  );
}

const NOT_AVAILABLE = <span style={{ color: "var(--text-muted)" }}>Veri mevcut değil</span>;

export function DetectionScope({ anomaly }: { anomaly: AnomalyDetail }) {
  const a = anomaly;
  const higherIsBetter = isHigherBetter(a.kpiDefinition.desiredDirection);

  let worstDay: { date: string; value: number } | null = null;
  if (a.dailyHistory.length > 0) {
    worstDay = a.dailyHistory[0];
    for (const p of a.dailyHistory) {
      const isWorse = higherIsBetter ? p.value < worstDay.value : p.value > worstDay.value;
      if (isWorse) worstDay = p;
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3 lg:grid-cols-4">
        <ScopeField label="Fabrika">{a.factoryCode ?? NOT_AVAILABLE}</ScopeField>
        <ScopeField label="Tesis">
          <Link to={`/plants/${a.plantId}`} className="hover:underline" style={{ color: "var(--accent)" }}>{a.plantName}</Link>
        </ScopeField>
        <ScopeField label="Vardiya">{a.shiftName ?? <span style={{ color: "var(--text-muted)" }}>Vardiyaya özgü değil</span>}</ScopeField>
        <ScopeField label="Dönem">{formatDateRangeTR(a.periodStart, a.periodEnd)}</ScopeField>
        <ScopeField label="Etkilenen Gün">
          {a.affectedDays != null && a.totalDays != null ? `${a.affectedDays} / ${a.totalDays}` : NOT_AVAILABLE}
        </ScopeField>
        <ScopeField label="KPI">{a.kpiName}</ScopeField>
        <ScopeField label="Tespit Türü">{a.anomalyTypeLabel}</ScopeField>
        <ScopeField label="En Kötü Gün">
          {worstDay ? `${formatDateTR(worstDay.date)} · ${formatMetricValue(worstDay.value, a.unit)}` : NOT_AVAILABLE}
        </ScopeField>
      </div>
      <p className="text-xs" style={{ color: "var(--text-muted)" }}>Ürün / hat kırılımı için veri bulunmuyor.</p>
    </div>
  );
}
