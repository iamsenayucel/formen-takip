import { ArrowRight, HardHat, Lightbulb, Sparkles, Wallet } from "lucide-react";
import { StatCard } from "./StatCard";
import { LoadingState, ErrorState } from "./StateViews";
import { useContributionSummary } from "../api/hooks";
import { formatMinutes, formatMoney } from "../lib/contributionCalc";

export function ContributionSummaryStats({ title = "Operational Impact+ Özeti", onViewAll, linkStatsTo, params }: {
  title?: string;
  onViewAll?: () => void;
  linkStatsTo?: string;
  params?: Record<string, string | number | undefined>;
}) {
  const contributionSummary = useContributionSummary(params);

  return (
    <div className="rounded-lg p-4" style={{ border: "1px solid var(--border)", background: "var(--surface)" }}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-[13px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
          <Sparkles size={14} strokeWidth={2} style={{ color: "var(--accent)" }} />
          {title}
        </h3>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="inline-flex items-center gap-1 text-xs font-medium hover:underline"
            style={{ color: "var(--accent)" }}
          >
            Tüm çalışmaları görüntüle
            <ArrowRight size={13} strokeWidth={2} />
          </button>
        )}
      </div>
      {contributionSummary.isLoading && <LoadingState />}
      {contributionSummary.isError && <ErrorState />}
      {contributionSummary.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
          <StatCard label="Toplam Çalışma" value={contributionSummary.data.totalWorks} icon={Lightbulb} to={linkStatsTo} />
          <StatCard label="Bu Ay Eklenen" value={contributionSummary.data.addedThisMonth} icon={Sparkles} />
          <StatCard
            label="Toplam Kazanç"
            value={formatMoney(contributionSummary.data.totalGainAmount, "TRY")}
            icon={Wallet}
          />
          <StatCard
            label="Aylık Zaman Kazancı"
            value={formatMinutes(contributionSummary.data.totalMonthlyTimeSavingMinutes)}
            icon={HardHat}
          />
        </div>
      )}
    </div>
  );
}
