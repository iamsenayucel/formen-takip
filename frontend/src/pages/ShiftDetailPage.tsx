import { useMemo } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { BackLink } from "../components/BackLink";
import { KpiBarChart } from "../components/charts/KpiBarChart";
import { RankingBarChart } from "../components/charts/RankingBarChart";
import { useFilterOptions, useForemanRanking, useKpiSummary, usePlantRanking, useShiftComparison } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { withSearchParam } from "../lib/chartDrilldown";
import { clickableRowProps } from "../lib/a11y";
import { rowHoverClass, rowStyle, tableClass, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export function ShiftDetailPage() {
  const { shiftId } = useParams<{ shiftId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();
  const location = useLocation();

  const scopedParams = useMemo(() => ({ ...asQueryParams, shift_ids: shiftId }), [asQueryParams, shiftId]);
  const searchWithShift = withSearchParam(location.search, "shift_ids", shiftId ?? "");

  const filterOptions = useFilterOptions();
  const shift = filterOptions.data?.shifts.find((s) => s.id === shiftId);

  const shiftComparison = useShiftComparison(scopedParams);
  const shiftScore = shiftComparison.data?.find((s) => s.shiftId === shiftId);

  const kpiSummary = useKpiSummary(scopedParams);
  const plantRanking = usePlantRanking(scopedParams, "desc", 50);
  const foremanRanking = useForemanRanking(scopedParams, "desc", 100);

  const strongestKpi = kpiSummary.data?.length
    ? kpiSummary.data.reduce((best, k) => (k.avgScore > best.avgScore ? k : best))
    : null;
  const weakestKpi = kpiSummary.data?.length
    ? kpiSummary.data.reduce((worst, k) => (k.avgScore < worst.avgScore ? k : worst))
    : null;
  const criticalForemanCount = foremanRanking.data?.filter((f) => f.level.name === "Kritik").length ?? 0;

  if (filterOptions.isLoading) return <LoadingState />;
  if (!shift) return <ErrorState message="Vardiya bulunamadı." />;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <BackLink label="Genel Bakış" onClick={() => navigate({ pathname: "/", search: location.search })} />
          <h1 className="text-page-title mt-1" style={{ color: "var(--text-primary)" }}>{shift.name}</h1>
        </div>
        {shiftScore && (
          <div className="text-right">
            <div className="text-2xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{shiftScore.totalScore.toFixed(1)}</div>
            <div className="mt-1"><PerformanceLevelBadge level={shiftScore.level} /></div>
          </div>
        )}
      </div>

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card title="Aktif Formen"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{foremanRanking.data?.length ?? 0}</p></Card>
        <Card title="Kritik Formen"><p className="text-xl font-semibold tabular-nums" style={{ color: "var(--status-negative)" }}>{criticalForemanCount}</p></Card>
        <Card title="En Güçlü KPI">
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{strongestKpi?.name ?? "-"}</p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{strongestKpi ? `${strongestKpi.avgScore.toFixed(1)} puan` : ""}</p>
        </Card>
        <Card title="En Düşük KPI">
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{weakestKpi?.name ?? "-"}</p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{weakestKpi ? `${weakestKpi.avgScore.toFixed(1)} puan` : ""}</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="KPI Bazlı Vardiya Performansı">
          {kpiSummary.isLoading ? (
            <LoadingState />
          ) : kpiSummary.data ? (
            <KpiBarChart
              items={kpiSummary.data}
              onSelect={(item) =>
                navigate({ pathname: "/kpis", search: withSearchParam(searchWithShift, "kpi", item.id) })
              }
            />
          ) : (
            <ErrorState />
          )}
        </Card>
        <Card title="Tesis Bazlı Sonuçlar">
          {plantRanking.isLoading ? (
            <LoadingState />
          ) : plantRanking.data ? (
            <RankingBarChart
              items={plantRanking.data.map((p) => ({ id: p.plantId, name: p.name, score: p.totalScore, color: p.level.color }))}
              onSelect={(item) => navigate({ pathname: `/plants/${item.id}`, search: searchWithShift })}
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <Card title="Formen Bazlı Sonuçlar">
        {foremanRanking.isLoading && <LoadingState />}
        {foremanRanking.data && foremanRanking.data.length === 0 && <EmptyState />}
        {foremanRanking.data && foremanRanking.data.length > 0 && (
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
                {foremanRanking.data.map((f) => (
                  <tr
                    key={f.foremanId}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    style={rowStyle}
                    {...clickableRowProps(() => navigate({ pathname: `/foremen/${f.foremanId}`, search: searchWithShift }), `${f.fullName} profiline git`)}
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
          </div>
        )}
      </Card>
    </div>
  );
}
