import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useAnomalies, useAnomaly, useForemen } from "../api/hooks";
import { SeverityBadge, SEVERITY_CONFIG } from "./AnomalyBadges";
import { rankAnomaliesByPriority } from "../lib/anomalyMetrics";
import type { AnomalyListItem } from "../api/types";

const MAX_CARDS = 3;

function ForemanLabel({ code }: { code: string }) {
  const result = useForemen({ search: code }, 1);
  return <>{result.data?.pages[0]?.items[0]?.fullName ?? code}</>;
}

function CriticalAnomalyCardItem({ candidate }: { candidate: AnomalyListItem }) {
  const navigate = useNavigate();
  const detail = useAnomaly(candidate.id);
  const cfg = SEVERITY_CONFIG[candidate.severity];
  const foremanCodes = detail.data?.foremanCodes ?? [];

  return (
    <button
      type="button"
      onClick={() => navigate(`/anomalies/${candidate.id}`)}
      className="flex h-full w-full min-w-0 flex-col rounded-lg p-[var(--space-card-padding-sm)] text-left transition-transform duration-150 hover:-translate-y-0.5"
      style={{ background: "var(--surface)", border: `1px solid ${cfg.color}40`, borderLeft: `4px solid ${cfg.color}` }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <SeverityBadge severity={candidate.severity} />
          <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
            {candidate.plantName ?? "-"} · {candidate.kpiName ?? candidate.anomalyTypeLabel}
          </span>
        </div>
        <span className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
          {new Date(candidate.detectedAt).toLocaleDateString("tr-TR")}
        </span>
      </div>

      <p className="text-card-title mt-2" style={{ color: "var(--text-primary)" }}>{candidate.title}</p>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs" style={{ color: "var(--text-secondary)" }}>
        {foremanCodes.length > 0 && (
          <span>
            Formen: {foremanCodes.length === 1 ? <ForemanLabel code={foremanCodes[0]} /> : `${foremanCodes.length} formen`}
          </span>
        )}
        <span className="font-semibold" style={{ color: cfg.color }}>
          Sapma: {candidate.deviationPercent >= 0 ? "+" : ""}%{candidate.deviationPercent.toFixed(1)}
        </span>
      </div>

      <span className="mt-auto inline-flex items-center gap-1 pt-3 text-xs font-medium hover:underline" style={{ color: "var(--primary)" }}>
        Analizi Gör
        <ArrowRight size={13} strokeWidth={2} />
      </span>
    </button>
  );
}

// Dashboard'un "en kritik tespit" alanı — açık/kritik tespitleri Tespitler
// listesindeki öncelik şeridiyle aynı kuralla (rankAnomaliesByPriority)
// sıralar ve en önemli 3 tanesini aynı satırda yan yana gösterir.
export function CriticalAnomalyCard() {
  const list = useAnomalies({}, 50);
  const candidates = list.data
    ? rankAnomaliesByPriority(list.data.pages.flatMap((page) => page.items)).slice(0, MAX_CARDS)
    : [];

  if (list.isLoading || list.isError || candidates.length === 0) return null;

  return (
    <div className="grid grid-cols-1 gap-[var(--space-card-gap)] sm:grid-cols-2 xl:grid-cols-3">
      {candidates.map((candidate) => (
        <CriticalAnomalyCardItem key={candidate.id} candidate={candidate} />
      ))}
    </div>
  );
}
