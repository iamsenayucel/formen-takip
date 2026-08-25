import type { ReactNode } from "react";
import { Award, Trophy } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { usePerformanceLeaders } from "../api/hooks";

type LeaderTone = "gold" | "navy";

const TONE_ACCENT: Record<LeaderTone, string> = {
  gold: "var(--leader-gold)",
  navy: "var(--primary)",
};

const TONE_CARD_CLASS: Record<LeaderTone, string> = {
  gold: "leader-card-gold",
  navy: "leader-card-navy",
};

function LeaderCardSkeleton() {
  return (
    <div
      className="flex items-start gap-2 rounded-lg border px-2.5 py-2"
      style={{ borderColor: "var(--sidebar-border)" }}
    >
      <div className="mt-0.5 h-6 w-6 shrink-0 animate-pulse rounded-full" style={{ background: "var(--sidebar-border)" }} />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5 py-0.5">
        <div className="h-2 w-14 animate-pulse rounded-full" style={{ background: "var(--sidebar-border)" }} />
        <div className="h-2.5 w-24 animate-pulse rounded-full" style={{ background: "var(--sidebar-border)" }} />
      </div>
    </div>
  );
}

function EmptyLeaderCard({ icon: Icon, eyebrow }: { icon: typeof Trophy; eyebrow: string }) {
  return (
    <div
      className="flex items-start gap-2 rounded-lg border px-2.5 py-2"
      style={{ borderColor: "var(--sidebar-border)", borderStyle: "dashed" }}
    >
      <Icon size={13} strokeWidth={1.75} className="mt-0.5 shrink-0" style={{ color: "var(--sidebar-muted)" }} />
      <span className="min-w-0 flex-1">
        <span className="text-metadata block" style={{ color: "var(--sidebar-muted)" }}>
          {eyebrow}
        </span>
        <span className="text-metadata block" style={{ color: "var(--sidebar-subtext)" }}>
          Henüz hesaplanmadı
        </span>
      </span>
    </div>
  );
}

function LeaderCard({
  tone,
  icon: Icon,
  eyebrow,
  name,
  meta,
  onNavigate,
}: {
  tone: LeaderTone;
  icon: typeof Trophy;
  eyebrow: string;
  name: string;
  meta: ReactNode;
  onNavigate: () => void;
}) {
  const accent = TONE_ACCENT[tone];

  return (
    <button
      type="button"
      onClick={onNavigate}
      title={name}
      className={`leader-card-clickable ${TONE_CARD_CLASS[tone]} flex w-full items-start gap-2 rounded-lg border px-2.5 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/40`}
      style={{ borderLeft: `3px solid ${accent}` }}
    >
      <span
        className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
        style={{
          background: `color-mix(in srgb, ${accent} 20%, transparent)`,
          border: `1px solid color-mix(in srgb, ${accent} 36%, transparent)`,
        }}
      >
        <Icon size={12} strokeWidth={2} style={{ color: accent }} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-metadata block" style={{ color: "var(--sidebar-muted)" }}>
          {eyebrow}
        </span>
        <span
          className="block truncate text-[13px] font-semibold leading-tight"
          style={{ color: tone === "navy" ? "var(--primary)" : "var(--sidebar-heading)" }}
        >
          {name}
        </span>
        <span className="text-metadata block truncate" style={{ color: "var(--sidebar-subtext)" }}>
          {meta}
        </span>
      </span>
    </button>
  );
}

export function PerformanceLeadersPanel({ onNavigate }: { onNavigate?: () => void }) {
  const { data, isLoading, isError } = usePerformanceLeaders();
  const navigate = useNavigate();

  if (isError) return null;

  const goToForeman = (foremanId: string) => {
    navigate(`/foremen/${foremanId}`);
    onNavigate?.();
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5 px-3 pb-1 pt-0.5">
        <Trophy size={11} strokeWidth={2} style={{ color: "var(--leader-gold)" }} />
        <p
          className="text-label"
          style={{ color: "color-mix(in srgb, var(--leader-gold) 35%, var(--sidebar-muted))" }}
        >
          Performans Liderleri
        </p>
      </div>
      <div className="flex flex-col gap-1.5">
        {isLoading && (
          <>
            <LeaderCardSkeleton />
            <LeaderCardSkeleton />
          </>
        )}
        {!isLoading && data && (
          <>
            {data.monthlyLeader ? (
              <LeaderCard
                tone="gold"
                icon={Trophy}
                eyebrow="Geçen Ay"
                name={data.monthlyLeader.fullName}
                meta={
                  <>
                    {data.lastCalculatedMonth.label} ·{" "}
                    <span className="font-semibold">{data.monthlyLeader.generalPerformanceScore.toFixed(1)} puan</span>
                  </>
                }
                onNavigate={() => goToForeman(data.monthlyLeader!.foremanId)}
              />
            ) : (
              <EmptyLeaderCard icon={Trophy} eyebrow="Geçen Ay" />
            )}
            {data.yearlyLeader ? (
              <LeaderCard
                tone="navy"
                icon={Award}
                eyebrow={`${data.year} Yılı`}
                name={data.yearlyLeader.fullName}
                meta={
                  <>
                    <span className="font-semibold">{data.yearlyLeader.generalPerformanceScore.toFixed(1)} puan</span>
                    {" · "}
                    {data.yearlyLeader.monthlyWins} kez ay lideri
                  </>
                }
                onNavigate={() => goToForeman(data.yearlyLeader!.foremanId)}
              />
            ) : (
              <EmptyLeaderCard icon={Award} eyebrow={`${data.year} Yılı`} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
