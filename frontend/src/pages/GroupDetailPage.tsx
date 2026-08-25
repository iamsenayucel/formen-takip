import { useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, Mail, Phone } from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { EntityHero, type EntityHeroRankItem } from "../components/EntityHero";
import { BackLink } from "../components/BackLink";
import { KpiScorecard } from "../components/kpi/KpiScorecard";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiRadarChart } from "../components/charts/KpiRadarChart";
import { ForemanComparisonMatrix } from "../components/ForemanComparisonMatrix";
import {
  useChiefDetail,
  useChiefForemen,
  useChiefForemanComparison,
  useChiefKpis,
  useChiefTrend,
  useDashboardTrend,
  useKpiSummary,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { previousPeriodParams } from "../lib/period";
import { clickableRowProps } from "../lib/a11y";
import { rowHoverClass, rowStyle, tableClass, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

export function GroupDetailPage() {
  const { chiefId } = useParams<{ chiefId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();

  const chief = useChiefDetail(chiefId, asQueryParams);
  const team = useChiefForemen(chiefId, asQueryParams);
  const kpis = useChiefKpis(chiefId, asQueryParams);
  const previousKpis = useChiefKpis(chiefId, previousPeriodParams(asQueryParams));
  const trend = useChiefTrend(chiefId, asQueryParams, "day");
  const comparison = useChiefForemanComparison(chiefId, asQueryParams);
  const previousComparison = useChiefForemanComparison(chiefId, previousPeriodParams(asQueryParams));

  const factoryId = chief.data?.factory?.id;
  const factoryKpiParams = useMemo(
    () => ({ ...asQueryParams, factory_ids: factoryId, chief_ids: undefined }),
    [asQueryParams, factoryId]
  );
  const factoryKpis = useKpiSummary(factoryKpiParams, !!factoryId);
  const compareTrend = useDashboardTrend({ ...asQueryParams, factory_ids: factoryId }, "day");

  const previousKpiByCode = new Map((previousKpis.data ?? []).map((k) => [k.code, k]));

  if (chief.isLoading) return <LoadingState />;
  if (chief.isError || !chief.data) return <ErrorState message="Şef bulunamadı." />;

  const c = chief.data;

  const rank: EntityHeroRankItem[] = [
    { label: "Şirket Sıralaması", value: `${c.companyRank ?? "-"} / ${c.companyTotal}` },
    { label: "Fabrika Sıralaması", value: `${c.factoryRank ?? "-"} / ${c.factoryTotal}` },
  ];

  return (
    <div className="flex flex-col gap-4">
      <BackLink label="Gruplar" onClick={() => navigate("/groups")} />

      <EntityHero
        eyebrow="Şef / Grup"
        title={c.fullName}
        subtitle={c.employeeNumber}
        metaItems={[
          c.factory?.name,
          c.plants.length > 0 ? c.plants.map((p) => p.name).join(", ") : null,
          c.isActive ? null : "Pasif",
          `Göreve Başlama: ${c.hireDate}`,
        ]}
        contact={
          (c.phoneNumber || c.email) && (
            <>
              {c.phoneNumber && (
                <a href={`tel:${c.phoneNumber}`} className="flex items-center gap-1.5 hover:underline" style={{ color: "var(--text-secondary)" }}>
                  <Phone size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
                  {c.phoneNumber}
                </a>
              )}
              {c.email && (
                <a href={`mailto:${c.email}`} className="flex items-center gap-1.5 hover:underline" style={{ color: "var(--text-secondary)" }}>
                  <Mail size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
                  {c.email}
                </a>
              )}
            </>
          )
        }
        score={c.totalScore}
        scoreMax={100}
        scoreLabel="Genel Performans Puanı"
        level={c.level}
        statusNote={!c.isReliable ? { icon: AlertTriangle, text: "Ekipte eksik KPI verisi", tone: "attention" } : null}
        rank={rank}
      />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <Card title="KPI Performansı">
        {kpis.isLoading && <LoadingState />}
        {kpis.data && kpis.data.length === 0 && <EmptyState />}
        {kpis.data && kpis.data.length > 0 && (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {kpis.data.map((k) => {
              const previous = previousKpiByCode.get(k.code);
              const hasPrevious = k.recordCount > 0 && !!previous && previous.recordCount > 0;
              return (
                <KpiScorecard
                  key={k.kpiId}
                  name={k.name}
                  unit={k.unit}
                  score={k.avgCappedScore}
                  recordCount={k.recordCount}
                  target={k.avgTarget}
                  actual={k.avgActual}
                  delta={hasPrevious ? k.avgCappedScore - previous!.avgCappedScore : null}
                  weight={k.weight}
                  description={k.description}
                />
              );
            })}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Grup Performans Trendi">
          {trend.isLoading ? (
            <LoadingState />
          ) : trend.data ? (
            <TrendChart
              points={trend.data.points}
              comparePoints={factoryId ? compareTrend.data?.points : undefined}
              compareLabel="Fabrika Ortalaması"
              seriesLabel="Grup"
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
              items={kpis.data}
              compareItems={factoryKpis.data}
              compareLabel="Fabrika Ortalaması"
              seriesLabel="Şef"
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      {comparison.isLoading && (
        <Card title="Formen Performans Karşılaştırması">
          <LoadingState />
        </Card>
      )}
      {comparison.isError && (
        <Card title="Formen Performans Karşılaştırması">
          <ErrorState />
        </Card>
      )}
      {comparison.data && comparison.data.foremen.length === 0 && (
        <Card title="Formen Performans Karşılaştırması">
          <EmptyState />
        </Card>
      )}
      {comparison.data && comparison.data.foremen.length > 0 && (
        <ForemanComparisonMatrix data={comparison.data} previous={previousComparison.data} />
      )}

      <h2 className="text-section-title mt-1" style={{ color: "var(--text-secondary)" }}>Takım Dağılımı</h2>
      <Card title="Ekip — grup puanı bu formenlerin ortalamasıdır">
        {team.isLoading && <LoadingState />}
        {team.isError && <ErrorState />}
        {team.data && team.data.length === 0 && <EmptyState />}
        {team.data && team.data.length > 0 && (
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  {["Formen", "Sicil No", "Genel Puan", "Seviye", "Veri Güvenilirliği"].map((label) => (
                    <th key={label} className={thClass} style={thStyle}>{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {team.data.map((f) => (
                  <tr
                    key={f.id}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    style={rowStyle}
                    {...clickableRowProps(() => navigate(`/foremen/${f.id}`), `${f.fullName ?? "Formen"} profiline git`)}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.fullName ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employeeNumber ?? "-"}</td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>{f.generalPerformanceScore.toFixed(1)}</td>
                    <td className={tdClass}><PerformanceLevelBadge level={f.level} /></td>
                    <td className={tdClass}>
                      <ReliabilityBadge isReliable={f.isReliable} />
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
