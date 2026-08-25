import { Link } from "react-router-dom";
import { ChevronRight, User } from "lucide-react";
import type { AnomalyDetail, ResponsibleForeman } from "../../api/types";
import { EmptyState } from "../StateViews";
import { isHigherBetter } from "../../lib/kpiDirection";

function trendComment(values: number[], higherIsBetter: boolean | null): string | null {
  if (values.length < 2 || higherIsBetter === null) return null;
  const change = values[values.length - 1] - values[0];
  if (Math.abs(change) < 0.5) return "Son üç ayda belirgin bir değişim görülmüyor.";
  const improved = (change > 0) === higherIsBetter;
  return improved ? "Son üç ayda kademeli iyileşme görülüyor." : "Son üç ayda kademeli düşüş görülüyor.";
}

export function ForemanContext({ anomaly, foreman }: { anomaly: AnomalyDetail; foreman: ResponsibleForeman }) {
  if (!foreman.resolved || !foreman.primary) {
    return <EmptyState message={foreman.reason ?? "Sorumlu formen bilgisi bulunamadı."} />;
  }

  const { primary } = foreman;
  const hasDayCount = "day_count" in primary && "total_days" in primary && primary.totalDays != null;

  const trendValues = foreman.kpiTrend.filter((p) => p.hasData && p.avgActual != null).map((p) => p.avgActual as number);
  const comment = trendComment(trendValues, isHigherBetter(anomaly.kpiDefinition.desiredDirection));

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3 rounded-md p-3.5" style={{ border: "1px solid var(--border)" }}>
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full" style={{ background: "var(--accent-subtle)" }}>
            <User size={16} strokeWidth={2} style={{ color: "var(--accent)" }} />
          </div>
          <div>
            <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{primary.name}</p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {anomaly.shiftName ?? "Vardiyaya özgü değil"}
              {hasDayCount && ` · Dönemin ${primary.dayCount}/${primary.totalDays} gününden sorumlu`}
            </p>
          </div>
        </div>
        <Link to={`/foremen/${primary.id}`} className="flex shrink-0 items-center gap-1 text-xs font-medium hover:underline" style={{ color: "var(--accent)" }}>
          Profili görüntüle
          <ChevronRight size={13} strokeWidth={2} />
        </Link>
      </div>

      {foreman.others.length > 0 && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          {foreman.others.map((o) => `${o.name} · ${o.dayCount} gün`).join(" · ")}
        </p>
      )}

      {trendValues.length > 0 && (
        <div>
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            {anomaly.kpiName} — Formenin Son 3 Ayı
          </p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
            {foreman.kpiTrend.map((p, i) => (
              <span key={p.periodLabel} className="flex items-center gap-3" style={{ color: "var(--text-secondary)" }}>
                {i > 0 && <span style={{ color: "var(--text-muted)" }}>→</span>}
                {p.periodLabel} <strong style={{ color: "var(--text-primary)" }}>{p.hasData && p.avgActual != null ? `%${p.avgActual.toFixed(2)}` : "Veri yok"}</strong>
              </span>
            ))}
          </div>
          {comment && <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>{comment}</p>}
        </div>
      )}

      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        Bu bilgi sorumluluk bağlamı sağlar; tek başına performans değerlendirmesi değildir.
      </p>
    </div>
  );
}
