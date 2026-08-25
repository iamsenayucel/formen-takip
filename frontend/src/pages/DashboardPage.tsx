import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { PageHeader } from "../components/PageHeader";
import { Card } from "../components/StateViews";
import { LoadingState, ErrorState } from "../components/StateViews";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiBarChart } from "../components/charts/KpiBarChart";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { DistributionChart } from "../components/charts/DistributionChart";
import { ForemanRankingCard } from "../components/ForemanRankingCard";
import { PerformanceLevelDetailModal } from "../components/PerformanceLevelDetailModal";
import { PlantHeatmap } from "../components/PlantHeatmap";
import { CriticalAnomalyCard } from "../components/CriticalAnomalyCard";
import { ExecutiveHero } from "../components/dashboard/ExecutiveHero";
import type { DistributionItem } from "../api/types";
import { useDashboardSnapshot, useDashboardTrend } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { withSearchParam } from "../lib/chartDrilldown";
import { formatDateRangeTR } from "../lib/dateFormat";

export function DashboardPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();
  const location = useLocation();

  const snapshot = useDashboardSnapshot(asQueryParams);
  const trend = useDashboardTrend(asQueryParams, "day");

  const summary = { isLoading: snapshot.isLoading, isError: snapshot.isError, data: snapshot.data?.summary };
  const kpiSummary = { isLoading: snapshot.isLoading, data: snapshot.data?.kpiSummary };
  const shiftComparison = { isLoading: snapshot.isLoading, data: snapshot.data?.shiftComparison };
  const foremanRankingTop = { isLoading: snapshot.isLoading, data: snapshot.data?.foremanRanking.top };
  const foremanRankingBottom = { isLoading: snapshot.isLoading, data: snapshot.data?.foremanRanking.bottom };
  const foremanTrendImproving = { isLoading: snapshot.isLoading, data: snapshot.data?.foremanTrendRanking.improving };
  const foremanTrendDeclining = { isLoading: snapshot.isLoading, data: snapshot.data?.foremanTrendRanking.declining };
  const distribution = { isLoading: snapshot.isLoading, data: snapshot.data?.performanceDistribution };
  const [selectedLevel, setSelectedLevel] = useState<DistributionItem | null>(null);
  const [selectedLevelQueryOverride, setSelectedLevelQueryOverride] = useState<Record<string, string> | undefined>(undefined);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  const closeLevelModal = () => {
    setSelectedLevel(null);
    setSelectedLevelQueryOverride(undefined);
  };

  const trendPoints = trend.data?.points ?? [];
  const firstTrendPoint = trendPoints[0];
  const latestTrendPoint = trendPoints[trendPoints.length - 1];
  const trendDelta = trendPoints.length > 1 ? latestTrendPoint.totalScore - firstTrendPoint.totalScore : null;
  const trendSubtitle =
    trendPoints.length > 0 ? `Son ${trendPoints.length} gün · ${formatDateRangeTR(firstTrendPoint.date, latestTrendPoint.date)}` : undefined;

  return (
    <div className="flex flex-col gap-[var(--space-section-gap)]">
      <PageHeader title="Genel Bakış" />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <ExecutiveHero
        summary={summary.data}
        isLoading={summary.isLoading}
        isError={summary.isError}
        filters={filters}
      />

      <CriticalAnomalyCard />

      <div className="grid grid-cols-1 gap-[var(--space-section-gap)] xl:grid-cols-3">
        <div className="min-w-0 xl:col-span-2">
          <Card
            title="Operasyonel Performans Trendi"
            subtitle={trendSubtitle}
            action={
              latestTrendPoint && (
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-label" style={{ color: "var(--text-muted)" }}>
                      Son Değer
                    </div>
                    <div className="text-card-title tabular-nums" style={{ color: "var(--text-primary)" }}>
                      {latestTrendPoint.totalScore.toFixed(1)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-label" style={{ color: "var(--text-muted)" }}>
                      Hedef
                    </div>
                    <div className="text-card-title tabular-nums" style={{ color: "var(--text-muted)" }}>
                      100
                    </div>
                  </div>
                  {trendDelta !== null && (
                    <div className="text-right">
                      <div className="text-label" style={{ color: "var(--text-muted)" }}>
                        Dönem Farkı
                      </div>
                      <div
                        className="text-card-title tabular-nums"
                        style={{ color: trendDelta >= 0 ? "var(--status-positive)" : "var(--status-negative)" }}
                      >
                        {trendDelta >= 0 ? "+" : ""}
                        {trendDelta.toFixed(1)}
                      </div>
                    </div>
                  )}
                </div>
              )
            }
          >
            {trend.isLoading ? (
              <LoadingState />
            ) : trend.data ? (
              <TrendChart
                points={trend.data.points}
                yAxisFloor={
                  foremanRankingBottom.data && foremanRankingBottom.data.items.length > 0
                    ? Math.min(...foremanRankingBottom.data.items.map((f) => f.generalPerformanceScore)) - 20
                    : undefined
                }
              />
            ) : (
              <ErrorState />
            )}
          </Card>
        </div>
        <Card title="Performans Dağılımı">
          {distribution.isLoading ? (
            <LoadingState />
          ) : distribution.data ? (
            <DistributionChart
              items={distribution.data.items}
              onSelect={(item) => {
                setSelectedLevel(item);
                setSelectedLevelQueryOverride(undefined);
              }}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <PlantHeatmap
        filters={asQueryParams}
        levels={distribution.data?.items}
        selectedGroupId={selectedGroupId}
        onSelectGroup={setSelectedGroupId}
      />

      {selectedLevel && (
        <PerformanceLevelDetailModal
          level={selectedLevel}
          filterParams={asQueryParams}
          queryOverride={selectedLevelQueryOverride}
          onClose={closeLevelModal}
          onNavigateForeman={(id) => navigate(`/foremen/${id}`)}
        />
      )}

      <ForemanRankingCard
        filters={filters}
        topItems={foremanRankingTop.data?.items}
        topLoading={foremanRankingTop.isLoading}
        bottomItems={foremanRankingBottom.data?.items}
        bottomLoading={foremanRankingBottom.isLoading}
        improvingItems={foremanTrendImproving.data?.items}
        improvingLoading={foremanTrendImproving.isLoading}
        decliningItems={foremanTrendDeclining.data?.items}
        decliningLoading={foremanTrendDeclining.isLoading}
        onNavigateForeman={(id) => navigate(`/foremen/${id}`)}
        onViewAll={() => navigate("/foremen")}
      />

      <div className="grid grid-cols-1 gap-[var(--space-section-gap)] xl:grid-cols-2">
        <Card title="KPI Bazlı Ortalama Puan">
          {kpiSummary.isLoading ? (
            <LoadingState />
          ) : kpiSummary.data ? (
            <KpiBarChart
              items={kpiSummary.data.items}
              onSelect={(item) => navigate({ pathname: "/kpis", search: withSearchParam(location.search, "kpi", item.id) })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
        <Card title="Vardiya Karşılaştırması">
          {shiftComparison.isLoading ? (
            <LoadingState />
          ) : shiftComparison.data ? (
            <RankingBarChart
              items={shiftComparison.data.items.map((s) => ({ id: s.shiftId, name: s.name ?? "-", score: s.totalScore, color: s.level.color }))}
              onSelect={(item) => navigate({ pathname: `/shifts/${item.id}`, search: location.search })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>
    </div>
  );
}
