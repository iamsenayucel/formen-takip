import { Link, useNavigate } from "react-router-dom";
import { CheckCircle2, CircleDot } from "lucide-react";
import type { SimilarCase } from "../../api/types";
import { EmptyState } from "../StateViews";
import { formatDateTR } from "../../lib/dateFormat";

const VISIBLE_LIMIT = 3;

export function HistoricalDetections({
  cases, plantId, kpiId,
}: {
  cases: SimilarCase[];
  plantId: string;
  kpiId: string;
}) {
  const navigate = useNavigate();

  if (cases.length === 0) return <EmptyState message="Benzer geçmiş tespit bulunamadı." />;

  const visible = cases.slice(0, VISIBLE_LIMIT);

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {visible.map((c) => (
          <button
            key={c.anomalyId}
            type="button"
            onClick={() => navigate(`/anomalies/${c.anomalyId}`)}
            className="flex flex-col gap-1.5 rounded-md p-3 text-left transition-colors hover:bg-[var(--page-bg)]"
            style={{ border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{formatDateTR(c.detectedAt)}</span>
              <span
                className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium"
                style={
                  c.resolutionStatus === "resolved"
                    ? { background: "var(--status-positive-bg)", color: "var(--status-positive)" }
                    : { background: "var(--status-info-bg)", color: "var(--status-info)" }
                }
              >
                {c.resolutionStatus === "resolved" ? <CheckCircle2 size={11} strokeWidth={2} /> : <CircleDot size={11} strokeWidth={2} />}
                {c.resolutionStatus === "resolved" ? "Çözüldü" : "Açık"}
              </span>
            </div>
            <p className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>{c.title}</p>
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{c.plantName} · {c.kpiName ?? c.anomalyTypeLabel}</p>
            {c.resolutionStatus === "resolved" && c.verifiedRootCause && (
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                Kök neden: {c.verifiedRootCause}
                {c.actionTaken && ` · Aksiyon: ${c.actionTaken}`}
              </p>
            )}
          </button>
        ))}
      </div>
      {cases.length > VISIBLE_LIMIT && (
        <Link
          to={`/anomalies?plant_ids=${plantId}&kpi_ids=${kpiId}`}
          className="text-xs font-medium hover:underline"
          style={{ color: "var(--primary)" }}
        >
          Tüm benzer tespitleri görüntüle ({cases.length})
        </Link>
      )}
    </div>
  );
}
