import { useLocation } from "react-router-dom";
import { Star, Target, TrendingDown, Trophy } from "lucide-react";
import type { DashboardSummary } from "../../api/types";
import type { FilterState } from "../../hooks/useFilters";
import { periodLabel, scopeLabel } from "../../lib/filterLabels";
import { formatDateTimeTR } from "../../lib/dateFormat";
import { withSearchParam } from "../../lib/chartDrilldown";
import { StatCard } from "../StatCard";
import { LoadingState, ErrorState } from "../StateViews";

export function ExecutiveHero({
  summary,
  isLoading,
  isError,
  filters,
}: {
  summary: DashboardSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  filters: FilterState;
}) {
  const location = useLocation();
  return (
    <div
      className="rounded-lg p-[var(--space-card-padding)]"
      style={{
        background: "var(--surface-hero)",
        border: "1px solid var(--surface-hero-border)",
        borderLeft: "4px solid var(--hero-accent)",
        boxShadow: "var(--shadow-panel)",
      }}
    >
      {isLoading && <LoadingState label="Genel performans yükleniyor..." />}
      {isError && <ErrorState />}
      {summary && (
        <>
          <div className="flex flex-col gap-5 max-[1439px]:gap-3 lg:flex-row lg:items-stretch">
            <div className="min-w-0 lg:flex-1">
              <p className="text-label" style={{ color: "var(--text-muted)" }}>
                Genel Operasyonel Performans
              </p>
              <div className="mt-2 flex items-baseline gap-2.5">
                <span className="text-hero-score" style={{ color: "var(--data-primary)" }}>
                  {summary.avgCompanyScore.toFixed(1)}
                </span>
                <span className="text-body" style={{ color: "var(--text-muted)" }}>
                  / 100 hedef
                </span>
              </div>
              <p className="text-metadata mt-2" style={{ color: "var(--text-secondary)" }}>
                {periodLabel(filters)} • {scopeLabel(filters)}
              </p>
            </div>

            <div
              className="min-w-0 lg:flex-1 min-[1024px]:border-l min-[1024px]:pl-4 min-[1600px]:pl-6"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              {/* Kırılma noktaları: min-640'ta 4 kart (hero dikey istiflenmişken tam
                  genişlik var), min-1024'te hero yatay yarılandığı için 2'ye düşer,
                  min-1600'den itibaren yarı genişlik yine 4'ü taşır. 1440 değil 1600
                  seçildi: 1440-1599 aralığında padding/font henüz kısmen küçülmüş
                  olduğundan 4'e geçmek başlıkları 3 satıra bölüyordu. Tailwind v4
                  arbitrary min-[Npx] variant'ları isimli breakpoint'lerden ayrı ve önce
                  üretildiği için aynı property'de ikisini karıştırmak cascade sırasını
                  bozar — bu yüzden burada yalnızca arbitrary variant kullanılır. */}
              <div className="grid h-full grid-cols-2 gap-2.5 min-[640px]:grid-cols-4 min-[1024px]:grid-cols-2 min-[1600px]:grid-cols-4">
                {summary.bestPlant && (
                  <StatCard
                    label="En Başarılı Tesis"
                    value={summary.bestPlant.name ?? "-"}
                    sub={summary.bestPlant.score != null ? `${summary.bestPlant.score.toFixed(1)} puan` : undefined}
                    to={`/plants/${summary.bestPlant.id}`}
                    icon={Trophy}
                    tone="positive"
                    premiumSurface
                  />
                )}
                {summary.bestForeman && (
                  <StatCard
                    label="En Başarılı Formen"
                    value={summary.bestForeman.name ?? "-"}
                    sub={summary.bestForeman.score != null ? `${summary.bestForeman.score.toFixed(1)} puan` : undefined}
                    to={`/foremen/${summary.bestForeman.id}`}
                    icon={Star}
                    tone="positive"
                    premiumSurface
                  />
                )}
                {summary.worstPlant && (
                  <StatCard
                    label="Gelişim Alanı: Tesis"
                    value={summary.worstPlant.name ?? "-"}
                    sub={summary.worstPlant.score != null ? `${summary.worstPlant.score.toFixed(1)} puan` : undefined}
                    to={`/plants/${summary.worstPlant.id}`}
                    icon={TrendingDown}
                    tone="attention"
                    premiumSurface
                  />
                )}
                {summary.weakestKpi && (
                  <StatCard
                    label="Gelişim Alanı: KPI"
                    value={summary.weakestKpi.name}
                    sub={`${summary.weakestKpi.avgScore.toFixed(1)} puan`}
                    to={`/kpis?${withSearchParam(location.search, "kpi", summary.weakestKpi.id)}`}
                    icon={Target}
                    tone="attention"
                    premiumSurface
                  />
                )}
              </div>
            </div>
          </div>

          {(summary.lastSyncAt || summary.plantsWithMissingData > 0) && (
            <div
              className="text-metadata mt-5 flex flex-wrap items-center gap-x-4 gap-y-1 pt-3"
              style={{ borderTop: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}
            >
              {summary.lastSyncAt && <span>Son veri güncellemesi · {formatDateTimeTR(summary.lastSyncAt)}</span>}
              {summary.plantsWithMissingData > 0 && (
                <span>{summary.plantsWithMissingData} tesis bu dönem için veri sağlamadı</span>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
