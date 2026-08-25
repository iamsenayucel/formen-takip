import { useMemo } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { LoadMoreButton } from "../components/LoadMoreButton";
import { EntityHero } from "../components/EntityHero";
import { BackLink } from "../components/BackLink";
import { KpiScorecard } from "../components/kpi/KpiScorecard";
import { ForemanShiftComparisonMatrix } from "../components/ForemanShiftComparisonMatrix";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiBarChart } from "../components/charts/KpiBarChart";
import { KpiRadarChart } from "../components/charts/KpiRadarChart";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import {
  useDashboardTrend, useKpiSummary, usePlantChiefs, usePlantDetail, usePlantForemen, usePlantKpis, usePlantShifts, usePlantSummary,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { withSearchParam } from "../lib/chartDrilldown";
import { previousPeriodParams } from "../lib/period";
import { clickableRowProps } from "../lib/a11y";
import { rowHoverClass, rowStyle, tableClass, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export function PlantDetailPage() {
  const { plantId } = useParams<{ plantId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();
  const location = useLocation();

  const plant = usePlantDetail(plantId);
  const summary = usePlantSummary(plantId, asQueryParams);
  const kpis = usePlantKpis(plantId, asQueryParams);
  const previousKpis = usePlantKpis(plantId, previousPeriodParams(asQueryParams));
  const shifts = usePlantShifts(plantId, asQueryParams);
  const foremen = usePlantForemen(plantId, asQueryParams, 100);
  const chiefs = usePlantChiefs(plantId, asQueryParams);

  const trend = useDashboardTrend({ ...asQueryParams, plant_ids: plantId }, "day");
  const factoryId = plant.data?.factory?.id;
  const compareTrend = useDashboardTrend({ ...asQueryParams, factory_ids: factoryId }, "day");
  const showCompareTrend = !!factoryId;

  const factoryKpiParams = useMemo(
    () => ({ ...asQueryParams, factory_ids: factoryId }),
    [asQueryParams, factoryId]
  );
  const factoryKpis = useKpiSummary(factoryKpiParams, !!factoryId);
  const foremanItems = foremen.data?.pages.flatMap((page) => page.items) ?? [];
  const foremanTotal = foremen.data?.pages.at(-1)?.pagination.total;

  if (plant.isLoading) return <LoadingState />;
  if (plant.isError || !plant.data) return <ErrorState message="Tesis bulunamadı." />;

  const previousKpiByCode = new Map((previousKpis.data ?? []).map((k) => [k.code, k]));
  const searchWithPlant = withSearchParam(location.search, "plant_ids", plantId ?? "");

  return (
    <div className="flex flex-col gap-4">
      <BackLink label="Tesisler" onClick={() => navigate("/plants")} />

      <EntityHero
        eyebrow="Tesis"
        title={plant.data.name}
        subtitle={plant.data.code}
        metaItems={[plant.data.factory?.name, plant.data.isActive ? null : "Pasif"]}
        score={summary.data?.totalScore ?? null}
        scoreMax={100}
        scoreLabel="Genel Operasyonel Skor"
        level={summary.data?.level}
      />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <Card title="KPI Performansı">
        {kpis.isLoading && <LoadingState />}
        {kpis.data && kpis.data.length === 0 && <EmptyState />}
        {kpis.data && kpis.data.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {kpis.data.map((k) => {
              // /plants/{id}/kpis (PlantService.get_kpis) yanıtında record_count alanı yoktur
              // (yalnızca dashboard/formen/şef KPI endpoint'lerinde var) — bu yüzden veri
              // varlığını gerçek `avg_actual` sinyalinden türetiyoruz, uydurmuyoruz.
              const hasData = k.avgActual !== null;
              const previous = previousKpiByCode.get(k.code);
              const previousHasData = !!previous && previous.avgActual !== null;
              return (
                <KpiScorecard
                  key={k.kpiId}
                  name={k.name}
                  unit={k.unit}
                  score={k.avgScore}
                  recordCount={hasData ? 1 : 0}
                  target={k.avgTarget}
                  actual={k.avgActual}
                  delta={hasData && previousHasData ? k.avgScore - previous!.avgScore : null}
                  onClick={() => navigate({ pathname: "/kpis", search: withSearchParam(searchWithPlant, "kpi", k.kpiId) })}
                />
              );
            })}
          </div>
        )}
      </Card>

      <ForemanShiftComparisonMatrix plantId={plantId!} dateParams={asQueryParams} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Performans Trendi">
          {trend.isLoading ? (
            <LoadingState />
          ) : trend.data ? (
            <TrendChart
              points={trend.data.points}
              comparePoints={showCompareTrend ? compareTrend.data?.points : undefined}
              compareLabel="Fabrika Ortalaması"
              seriesLabel="Tesis"
            />
          ) : (
            <ErrorState />
          )}
        </Card>
        <Card title="KPI Radar Grafiği">
          {kpis.isLoading ? (
            <LoadingState />
          ) : kpis.data ? (
            <KpiRadarChart
              items={kpis.data.map((k) => ({ code: k.code, avgCappedScore: k.avgScore }))}
              compareItems={factoryKpis.data}
              compareLabel="Fabrika Ortalaması"
              seriesLabel="Tesis"
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <h2 className="text-section-title mt-1" style={{ color: "var(--text-secondary)" }}>KPI ve Vardiya Karşılaştırması</h2>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="KPI Bazlı Performans">
          {kpis.isLoading ? (
            <LoadingState />
          ) : kpis.data ? (
            <KpiBarChart
              items={kpis.data}
              onSelect={(item) => navigate({ pathname: "/kpis", search: withSearchParam(searchWithPlant, "kpi", item.id) })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
        <Card title="Vardiya Karşılaştırması">
          {shifts.isLoading ? (
            <LoadingState />
          ) : shifts.data ? (
            <RankingBarChart
              items={shifts.data.map((s) => ({ id: s.shiftId, name: s.name, score: s.totalScore, color: s.level.color }))}
              onSelect={(item) => navigate({ pathname: `/shifts/${item.id}`, search: searchWithPlant })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <h2 className="text-section-title mt-1" style={{ color: "var(--text-secondary)" }}>Ekip Detayları</h2>
      <Card title="Şefler">
        {chiefs.isLoading && <LoadingState />}
        {chiefs.data && chiefs.data.length === 0 && <EmptyState />}
        {chiefs.data && chiefs.data.length > 0 && (
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Şef</th>
                  <th className={thClass} style={thStyle}>Sicil No</th>
                  <th className={thClass} style={thStyle}>Formen Sayısı</th>
                  <th className={thClass} style={thStyle}>Toplam Puan</th>
                  <th className={thClass} style={thStyle}>Seviye</th>
                </tr>
              </thead>
              <tbody>
                {chiefs.data.map((c) => (
                  <tr
                    key={c.id}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    style={rowStyle}
                    {...clickableRowProps(() => navigate(`/groups/${c.id}`), `${c.fullName} profiline git`)}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{c.fullName}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{c.employeeNumber}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{c.foremanCount}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>{c.totalScore.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={c.level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Formen Performans Listesi">
        {foremen.isLoading && <LoadingState />}
        {foremen.data && foremanItems.length === 0 && <EmptyState />}
        {foremanItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Formen</th>
                  <th className={thClass} style={thStyle}>Sicil No</th>
                  <th className={thClass} style={thStyle}>Genel Puan</th>
                  <th className={thClass} style={thStyle}>Seviye</th>
                </tr>
              </thead>
              <tbody>
                {foremanItems.map((f) => (
                  <tr
                    key={f.foremanId}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    style={rowStyle}
                    {...clickableRowProps(() => navigate(`/foremen/${f.foremanId}`), `${f.fullName} profiline git`)}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.fullName}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employeeNumber}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>{f.generalPerformanceScore.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={f.level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <LoadMoreButton
              hasMore={!!foremen.hasNextPage}
              isFetchingNextPage={foremen.isFetchingNextPage}
              onLoadMore={() => void foremen.fetchNextPage()}
              loadedCount={foremanItems.length}
              total={foremanTotal}
              itemLabel="formen"
            />
          </div>
        )}
      </Card>
    </div>
  );
}
