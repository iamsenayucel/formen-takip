import type { AnomalyDetail } from "../../api/types";
import { formatMetricValue } from "../../lib/anomalyMetrics";

function SummaryTile({
  label, value, sub, emphasis,
}: {
  label: string;
  value: string;
  sub?: string;
  emphasis?: boolean;
}) {
  return (
    <div
      className="rounded-lg p-3.5"
      style={{
        background: "var(--page-bg)",
        border: emphasis ? "1px solid var(--data-primary)" : "1px solid var(--border)",
      }}
    >
      <div className="text-label" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
      <p className="text-hero-metric mt-1" style={{ color: emphasis ? "var(--data-primary)" : "var(--text-primary)" }}>
        {value}
      </p>
      {sub && <p className="text-metadata mt-0.5" style={{ color: "var(--text-muted)" }}>{sub}</p>}
    </div>
  );
}

export function PrimaryKpiSummary({ anomaly }: { anomaly: AnomalyDetail }) {
  const a = anomaly;
  const hasPersistence = a.affectedDays != null && a.totalDays != null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <SummaryTile label="Gerçekleşen" value={formatMetricValue(a.observedValue, a.unit)} emphasis />
      <SummaryTile label="Hedef" value={a.targetValue != null ? formatMetricValue(a.targetValue, a.unit) : "-"} />
      <SummaryTile
        label="Görüldü"
        value={hasPersistence ? `${a.affectedDays} / ${a.totalDays} gün` : "-"}
        sub={hasPersistence ? `Sorun ${a.totalDays} günün ${a.affectedDays}'inde görüldü.` : undefined}
      />
    </div>
  );
}
