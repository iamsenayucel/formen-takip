import { useMemo } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { TrendChart } from "../components/charts/TrendChart";
import { ForemanKpiTargetChart } from "../components/charts/ForemanKpiTargetChart";
import { ForemanScoreRow } from "../components/ForemanRankingCard";
import { KpiPerformanceHero } from "../components/kpi/KpiPerformanceHero";
import { useFilterOptions, useKpiAnalysis, useKpis } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { categoricalColor, statusChartColor } from "../lib/chartColors";
import { periodLabel, scopeLabel, scopeSegments } from "../lib/filterLabels";
import { previousPeriodParams } from "../lib/period";
import { useTheme } from "../context/ThemeContext";

export function KpiAnalysisPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const kpis = useKpis();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  const filterOptions = useFilterOptions(filters.plantIds.join(",") || undefined, filters.factoryIds.join(",") || undefined);
  const factoryNameById = useMemo(
    () => new Map((filterOptions.data?.factories ?? []).map((f) => [f.id, f.name])),
    [filterOptions.data]
  );
  const plantNameById = useMemo(
    () => new Map((filterOptions.data?.plants ?? []).map((p) => [p.id, p.name])),
    [filterOptions.data]
  );
  const heroScopeText = [periodLabel(filters), ...scopeSegments(filters, factoryNameById, plantNameById)].join(" · ");

  const selectedKpiId = searchParams.get("kpi") ?? kpis.data?.[0]?.id ?? null;

  const selectKpi = (id: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("kpi", id);
    setSearchParams(next, { replace: true });
  };

  const analysis = useKpiAnalysis(selectedKpiId ?? undefined, asQueryParams);
  const previousAnalysis = useKpiAnalysis(selectedKpiId ?? undefined, previousPeriodParams(asQueryParams));

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="KPI Analizi" />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="flex flex-wrap gap-2">
        {kpis.data?.map((k) => {
          const active = selectedKpiId === k.id;
          return (
            <button
              key={k.id}
              onClick={() => selectKpi(k.id)}
              className="rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors"
              style={
                active
                  ? { background: "var(--primary)", color: "#ffffff" }
                  : { border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }
              }
            >
              {k.name}
            </button>
          );
        })}
      </div>

      {analysis.isLoading && <LoadingState />}
      {analysis.isError && <ErrorState />}
      {analysis.data && (
        <>
          <KpiPerformanceHero
            kpiName={analysis.data.kpi.name}
            unit={analysis.data.kpi.unit}
            score={analysis.data.companyAvgScore}
            hasData={analysis.data.companyAvgActual !== null}
            target={analysis.data.companyAvgTarget}
            actual={analysis.data.companyAvgActual}
            delta={
              previousAnalysis.data && previousAnalysis.data.companyAvgActual !== null
                ? analysis.data.companyAvgScore - previousAnalysis.data.companyAvgScore
                : undefined
            }
            decimalPlaces={analysis.data.kpi.decimalPlaces}
            meta={heroScopeText}
          />

          <Card>
            <ForemanKpiTargetChart
              points={analysis.data.foremanValues}
              target={analysis.data.companyAvgTarget}
              unit={analysis.data.kpi.unit}
              kpiName={analysis.data.kpi.name}
              decimalPlaces={analysis.data.kpi.decimalPlaces}
              subtitle={`${periodLabel(filters)} · ${scopeLabel(filters)}`}
              onSelectForeman={(id) => navigate({ pathname: `/foremen/${id}`, search: location.search })}
            />
          </Card>

          <Card title="Haftalık Trend">
            <TrendChart points={analysis.data.trend.map((t) => ({ date: t.date, totalScore: t.score, isReliable: true }))} />
          </Card>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <Card title="En Başarılı Tesisler">
              <RankingBarChart
                items={analysis.data.bestPlants.map((p, i) => ({ id: p.id, name: p.name ?? "-", score: p.score ?? 0, color: categoricalColor(i, isDark) }))}
                onSelect={(item) => navigate({ pathname: `/plants/${item.id}`, search: location.search })}
              />
            </Card>
            <Card title="En Düşük Performanslı Tesisler">
              <RankingBarChart
                items={analysis.data.worstPlants.map((p, i) => ({ id: p.id, name: p.name ?? "-", score: p.score ?? 0, color: categoricalColor(i, isDark) }))}
                onSelect={(item) => navigate({ pathname: `/plants/${item.id}`, search: location.search })}
              />
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <Card title="Vardiya Karşılaştırması">
              <RankingBarChart
                items={analysis.data.shiftComparison.map((s, i) => ({ id: s.id, name: s.name, score: s.score, color: categoricalColor(i, isDark) }))}
                onSelect={(item) => navigate({ pathname: `/shifts/${item.id}`, search: location.search })}
              />
            </Card>
            <Card title="En Başarılı Formenler">
              <div className="flex flex-col gap-0.5">
                {analysis.data.bestForemen.length === 0 && <EmptyState message="Veri yok" />}
                {analysis.data.bestForemen.map((f, i) => (
                  <ForemanScoreRow
                    key={f.id}
                    id={f.id}
                    name={f.name ?? "-"}
                    score={f.score ?? 0}
                    rank={i + 1}
                    color={statusChartColor("positive", isDark)}
                    showRankTint
                    onNavigate={(id) => navigate(`/foremen/${id}`)}
                  />
                ))}
              </div>
            </Card>
            <Card title="En Düşük Performanslı Formenler">
              <div className="flex flex-col gap-0.5">
                {analysis.data.worstForemen.length === 0 && <EmptyState message="Veri yok" />}
                {analysis.data.worstForemen.map((f, i) => (
                  <ForemanScoreRow
                    key={f.id}
                    id={f.id}
                    name={f.name ?? "-"}
                    score={f.score ?? 0}
                    rank={i + 1}
                    color={statusChartColor("neutral", isDark)}
                    showRankTint={false}
                    onNavigate={(id) => navigate(`/foremen/${id}`)}
                  />
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
