import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ChevronRight,
  Download, FileText, X,
} from "lucide-react";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { ForemanProfileHeader } from "../components/ForemanProfileHeader";
import { BackLink } from "../components/BackLink";
import { MetricDelta } from "../components/MetricDelta";
import { KpiScorecard } from "../components/kpi/KpiScorecard";
import { TrendChart } from "../components/charts/TrendChart";
import { KpiRadarChart } from "../components/charts/KpiRadarChart";
import { apiClient } from "../api/client";
import {
  useDashboardTrend, useForemanAssignmentHistory, useForemanCalculationDetail, useForemanDetail,
  useForemanKpis, useForemanMonthlyReportLatest, useForemanMonthlyReports, useForemanTrend,
  useFilterOptions, useKpiSummary,
} from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import type { ForemanDetail, ForemanKpiItem } from "../api/types";
import { fieldClass, fieldStyle } from "../lib/formStyles";
import { previousPeriodParams } from "../lib/period";
import { scoreDeltaColor } from "../lib/kpiFormat";

const TR_MONTHS = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];

function monthlyReportLabel(year: number, month: number): string {
  return `${TR_MONTHS[month - 1]} ${year}`;
}

async function downloadMonthlyReportPdf(foremanId: string, year: number, month: number, employeeNumber: string) {
  const resp = await apiClient.get(`/foremen/${foremanId}/monthly-reports/${year}/${month}/pdf`, { responseType: "blob" });
  const url = window.URL.createObjectURL(new Blob([resp.data]));
  const a = document.createElement("a");
  a.href = url;
  a.download = `formen-performans-raporu-${employeeNumber}-${year}-${String(month).padStart(2, "0")}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

function MonthlyReportsCard({ foremanId, employeeNumber }: { foremanId: string; employeeNumber: string }) {
  const navigate = useNavigate();
  const [showAll, setShowAll] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState<string | null>(null);
  const latest = useForemanMonthlyReportLatest(foremanId);
  const history = useForemanMonthlyReports(foremanId);

  const handleDownload = async (year: number, month: number) => {
    const key = `${year}-${month}`;
    setDownloadingKey(key);
    try {
      await downloadMonthlyReportPdf(foremanId, year, month, employeeNumber);
    } finally {
      setDownloadingKey(null);
    }
  };

  return (
    <Card title="Aylık Değerlendirme Raporları">
      {latest.isLoading && <LoadingState />}
      {latest.isError && <ErrorState />}
      {latest.data && !latest.data.available && (
        <EmptyState message="Bu formen için henüz tamamlanmış bir ay bulunmuyor." />
      )}
      {latest.data?.available && latest.data.year && latest.data.month && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                {monthlyReportLabel(latest.data.year, latest.data.month)}
              </p>
              <div className="mt-1 flex items-center gap-2">
                {latest.data.isReliable && latest.data.overallScore !== null && latest.data.overallScore !== undefined ? (
                  <>
                    <span className="text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                      {latest.data.overallScore.toFixed(1)}
                    </span>
                    {latest.data.reportData?.overall && <PerformanceLevelBadge level={latest.data.reportData.overall.level} />}
                  </>
                ) : (
                  <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {latest.data.reportData?.insufficientDataReason ?? "Yeterli veri bulunmuyor."}
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Aylık Performans Raporu</p>
              <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                Oluşturulma: {new Date(latest.data.generatedAt ?? "").toLocaleDateString("tr-TR")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate(`/foremen/${foremanId}/reports/${latest.data!.year}/${latest.data!.month}`)}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white"
                style={{ background: "var(--accent)" }}
              >
                <FileText size={13} strokeWidth={2} />
                Raporu Görüntüle
              </button>
              <button
                onClick={() => handleDownload(latest.data!.year!, latest.data!.month!)}
                disabled={downloadingKey === `${latest.data.year}-${latest.data.month}`}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                style={{ border: "1px solid var(--border)", color: "var(--text-primary)" }}
              >
                <Download size={13} strokeWidth={2} />
                {downloadingKey === `${latest.data.year}-${latest.data.month}` ? "İndiriliyor..." : "PDF İndir"}
              </button>
            </div>
          </div>

          {history.data && history.data.length > 1 && (
            <div>
              <button
                onClick={() => setShowAll((v) => !v)}
                className="text-xs font-medium hover:underline"
                style={{ color: "var(--accent)" }}
              >
                {showAll ? "Tüm Raporları Gizle" : "Tüm Raporlar"}
              </button>
              {showAll && (
                <ul className="mt-2 flex flex-col gap-1.5 text-[13px]">
                  {history.data.map((r) => (
                    <li
                      key={`${r.year}-${r.month}`}
                      className="flex items-center justify-between pb-1.5 last:pb-0"
                      style={{ borderBottom: "1px solid var(--border)" }}
                    >
                      <button
                        onClick={() => navigate(`/foremen/${foremanId}/reports/${r.year}/${r.month}`)}
                        className="hover:underline"
                        style={{ color: "var(--text-primary)" }}
                      >
                        {monthlyReportLabel(r.year, r.month)}
                        {!r.isReliable && <span className="ml-1 text-xs" style={{ color: "var(--text-muted)" }}>(yetersiz veri)</span>}
                      </button>
                      <button
                        onClick={() => handleDownload(r.year, r.month)}
                        disabled={downloadingKey === `${r.year}-${r.month}`}
                        className="flex items-center gap-1 text-xs font-medium hover:underline disabled:opacity-50"
                        style={{ color: "var(--accent)" }}
                      >
                        <Download size={12} strokeWidth={2} />
                        PDF
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function ContributionBonusBreakdownCard({ items }: { items: ForemanDetail["contributionBonusBreakdown"] }) {
  const navigate = useNavigate();

  if (items.length === 0) {
    return (
      <Card title="Son 3 Ay Operational Impact+ Bonusu">
        <p className="text-hero-metric" style={{ color: "var(--text-primary)" }}>0 puan</p>
        <p className="text-metadata mt-1" style={{ color: "var(--text-muted)" }}>
          Son 3 ay içerisinde puanlamaya dahil edilmiş Operational Impact+ çalışması bulunmuyor.
        </p>
      </Card>
    );
  }
  const total = items.reduce((sum, item) => sum + item.score, 0);
  return (
    <Card title="Son 3 Ay Operational Impact+ Bonusu">
      <div className="flex items-baseline gap-2">
        <p className="text-hero-metric" style={{ color: "var(--status-positive)" }}>+{total} puan</p>
        <span className="text-metadata" style={{ color: "var(--text-muted)" }}>{items.length} çalışma</span>
      </div>
      <ul className="mt-3 flex flex-col text-[13px]">
        {items.map((item) => (
          <li key={item.workId} style={{ borderBottom: "1px solid var(--border)" }}>
            <button
              type="button"
              onClick={() => navigate(`/improvement-works/${item.workId}`)}
              className="flex w-full cursor-pointer items-center justify-between gap-3 rounded-md py-2 text-left transition-colors hover:bg-[var(--page-bg)]"
            >
              <div className="min-w-0">
                <p className="truncate font-medium" style={{ color: "var(--text-primary)" }}>{item.title}</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.workDate}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <span
                  className="rounded px-1.5 py-0.5 text-xs font-semibold tabular-nums"
                  style={{ background: "var(--status-positive-bg)", color: "var(--status-positive)" }}
                >
                  +{item.score}
                </span>
                <ChevronRight size={14} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
              </div>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function CalculationDetailModal({ foremanId, kpi, onClose }: { foremanId: string; kpi: ForemanKpiItem; onClose: () => void }) {
  const detail = useForemanCalculationDetail(foremanId, kpi.kpiId);
  const formattedDate = detail.data
    ? new Date(detail.data.performanceDate).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" })
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-lg p-5 shadow-xl"
        style={{ background: "var(--surface)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{kpi.name}</h3>
            {formattedDate && <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>{formattedDate}</p>}
          </div>
          <button onClick={onClose} style={{ color: "var(--text-muted)" }} aria-label="Kapat">
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        {detail.isLoading && <LoadingState />}
        {detail.isError && <ErrorState />}
        {detail.data && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md p-3" style={{ background: "var(--page-bg)" }}>
                <p className="text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Hedef</p>
                <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {detail.data.targetValue?.toFixed(2)} {detail.data.unit}
                </p>
              </div>
              <div className="rounded-md p-3" style={{ background: "var(--page-bg)" }}>
                <p className="text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Gerçekleşen</p>
                <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
                  {detail.data.actualValue?.toFixed(2)} {detail.data.unit}
                </p>
              </div>
            </div>
            <div className="border-t pt-3" style={{ borderColor: "var(--border)" }}>
              <p className="text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Puan</p>
              <p className="mt-1 text-2xl font-bold tabular-nums" style={{ color: "var(--text-primary)" }}>
                {detail.data.cappedScore.toFixed(2)}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function ForemanDetailPage() {
  const { foremanId } = useParams<{ foremanId: string }>();
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const navigate = useNavigate();
  const [selectedKpi, setSelectedKpi] = useState<ForemanKpiItem | null>(null);
  const [trendKpiId, setTrendKpiId] = useState<string>("overall");

  const foreman = useForemanDetail(foremanId, asQueryParams);
  const kpis = useForemanKpis(foremanId, asQueryParams);
  const history = useForemanAssignmentHistory(foremanId);
  const metaOptions = useFilterOptions();

  const previousParams = useMemo(() => previousPeriodParams(asQueryParams), [asQueryParams]);
  const previousKpis = useForemanKpis(foremanId, previousParams);
  const previousKpiByCode = useMemo(
    () => new Map((previousKpis.data ?? []).map((k) => [k.code, k])),
    [previousKpis.data]
  );

  const trendParams = trendKpiId === "overall" ? asQueryParams : { ...asQueryParams, kpi_ids: trendKpiId };
  const trend = useForemanTrend(foremanId, trendParams, "day");

  const primaryPlantId = foreman.data?.assignments[0]?.plant.id;
  const primaryPlantMeta = metaOptions.data?.plants.find((p) => p.id === primaryPlantId);
  const primaryFactory = metaOptions.data?.factories.find((fa) => fa.id === primaryPlantMeta?.factoryId);

  const compareTrendParams = primaryFactory ? { ...trendParams, factory_ids: primaryFactory.id } : trendParams;
  const compareTrend = useDashboardTrend(compareTrendParams, "day");
  const compareLabel = primaryFactory ? "Fabrika Ortalaması" : "Şirket Ortalaması";

  const compareKpiParams = useMemo(
    () => (primaryFactory ? { ...asQueryParams, factory_ids: primaryFactory.id } : asQueryParams),
    [asQueryParams, primaryFactory]
  );
  const compareKpis = useKpiSummary(compareKpiParams);

  const periodAvg = useMemo(() => {
    const pts = trend.data?.points ?? [];
    if (pts.length === 0) return null;
    return pts.reduce((sum, p) => sum + p.totalScore, 0) / pts.length;
  }, [trend.data]);

  const compareAvg = useMemo(() => {
    const pts = compareTrend.data?.points ?? [];
    if (pts.length === 0) return null;
    return pts.reduce((sum, p) => sum + p.totalScore, 0) / pts.length;
  }, [compareTrend.data]);

  const trendDelta = useMemo(() => {
    const pts = trend.data?.points ?? [];
    if (pts.length < 2) return null;
    return pts[pts.length - 1].totalScore - pts[0].totalScore;
  }, [trend.data]);

  if (foreman.isLoading) return <LoadingState />;
  if (foreman.isError || !foreman.data) return <ErrorState message="Formen bulunamadı." />;

  const f = foreman.data;

  const activeAssignments = history.data?.filter((a) => a.isActive) ?? [];
  const responsiblePlants = [...new Set(activeAssignments.map((a) => a.plant).filter((p): p is string => !!p))];
  const currentChief = activeAssignments[0]?.chief ?? null;
  const currentShift = activeAssignments[0]?.shift ?? null;

  const diff = periodAvg !== null && compareAvg !== null ? periodAvg - compareAvg : null;

  return (
    <div className="flex flex-col gap-4">
      <BackLink label="Formenler" onClick={() => navigate("/foremen")} />

      <ForemanProfileHeader
        foreman={f}
        factoryCode={primaryFactory?.code}
        responsiblePlants={responsiblePlants}
        shiftLabel={currentShift}
        chiefName={currentChief}
      />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <Card title="Bu Dönem Performansı">
        {kpis.isLoading && <LoadingState />}
        {kpis.data && kpis.data.length === 0 && <EmptyState />}
        {kpis.data && kpis.data.length > 0 && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
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
                  description={k.description}
                  onClick={() => setSelectedKpi(k)}
                />
              );
            })}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title="Operasyonel Performans Trendi"
          action={
            <select
              value={trendKpiId}
              onChange={(e) => setTrendKpiId(e.target.value)}
              className={fieldClass}
              style={{ ...fieldStyle, width: "auto" }}
            >
              <option value="overall">Operasyonel Skor</option>
              {kpis.data?.map((k) => (
                <option key={k.kpiId} value={k.kpiId}>{k.name}</option>
              ))}
            </select>
          }
        >
          {(periodAvg !== null || compareAvg !== null) && (
            <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs" style={{ color: "var(--text-secondary)" }}>
              {periodAvg !== null && (
                <span>
                  Dönem Ortalaması{" "}
                  <strong className="tabular-nums" style={{ color: "var(--text-primary)" }}>{periodAvg.toFixed(1)}</strong>
                </span>
              )}
              {compareAvg !== null && (
                <span>
                  {compareLabel}{" "}
                  <strong className="tabular-nums" style={{ color: "var(--text-primary)" }}>{compareAvg.toFixed(1)}</strong>
                </span>
              )}
              {diff !== null && (
                <span>
                  Fark <strong><MetricDelta value={diff} /></strong>
                </span>
              )}
              {trendDelta !== null && (
                <span>
                  Trend{" "}
                  <strong className="tabular-nums" style={{ color: scoreDeltaColor(trendDelta) }}>
                    {trendDelta >= 0 ? "↑" : "↓"} {trendDelta >= 0 ? "+" : ""}{trendDelta.toFixed(1)}
                  </strong>
                </span>
              )}
            </div>
          )}
          {trend.isLoading ? (
            <LoadingState />
          ) : trend.data ? (
            <TrendChart points={trend.data.points} comparePoints={compareTrend.data?.points} compareLabel={compareLabel} seriesLabel="Formen" />
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
              compareItems={compareKpis.data}
              compareLabel={compareLabel}
              seriesLabel="Formen"
            />
          ) : (
            <ErrorState />
          )}
        </Card>
      </div>

      <ContributionBonusBreakdownCard items={f.contributionBonusBreakdown} />

      {foremanId && <MonthlyReportsCard foremanId={foremanId} employeeNumber={f.employeeNumber} />}

      {selectedKpi && foremanId && (
        <CalculationDetailModal foremanId={foremanId} kpi={selectedKpi} onClose={() => setSelectedKpi(null)} />
      )}
    </div>
  );
}
