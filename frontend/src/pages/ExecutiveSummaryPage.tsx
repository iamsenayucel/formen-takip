import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { Star, Target, TrendingDown, TrendingUp, Trophy } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
import { Card, ErrorState, LoadingState } from "../components/StateViews";
import { StatCard } from "../components/StatCard";
import { TrendChart } from "../components/charts/TrendChart";
import { useDashboardSnapshot, useDashboardSummary, useDashboardTrend } from "../api/hooks";
import { businessTodayIso } from "../hooks/useFilters";
import { formatDateRangeTR } from "../lib/dateFormat";

const YEAR_OPTIONS_COUNT = 5;

export function ExecutiveSummaryPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const today = businessTodayIso();
  const currentYear = Number(today.slice(0, 4));
  const years = useMemo(() => Array.from({ length: YEAR_OPTIONS_COUNT }, (_, i) => currentYear - i), [currentYear]);

  const requestedYear = Number(searchParams.get("year"));
  const year = years.includes(requestedYear) ? requestedYear : currentYear;
  const isCurrentYear = year === currentYear;

  const dateFrom = `${year}-01-01`;
  const dateTo = isCurrentYear ? today : `${year}-12-31`;
  const previousDateFrom = `${year - 1}-01-01`;
  const previousDateTo = `${year - 1}${dateTo.slice(4)}`;

  const params = { date_from: dateFrom, date_to: dateTo };
  const previousParams = { date_from: previousDateFrom, date_to: previousDateTo };

  const setYear = (nextYear: number) => {
    const next = new URLSearchParams(searchParams);
    next.set("year", String(nextYear));
    setSearchParams(next, { replace: true });
  };

  const snapshot = useDashboardSnapshot(params);
  const previousSummary = useDashboardSummary(previousParams);
  const trend = useDashboardTrend(params, "month");

  const summary = snapshot.data?.summary;
  const kpiItems = snapshot.data?.kpiSummary.items ?? [];
  const bestKpi =
    kpiItems.length > 0 ? kpiItems.reduce((best, item) => (item.avgScore > best.avgScore ? item : best)) : null;

  const delta =
    summary && previousSummary.data && previousSummary.data.totalActiveForemen > 0
      ? summary.avgCompanyScore - previousSummary.data.avgCompanyScore
      : null;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Yönetici Özeti"
        actions={
          <div className="flex flex-col items-end gap-1">
            <div className="flex items-center gap-2">
              <span className="text-label" style={{ color: "var(--text-muted)" }}>
                Yıl
              </span>
              <select
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="rounded-md border py-1.5 pl-2.5 pr-7 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/40"
                style={{ borderColor: "var(--border-strong)", color: "var(--text-primary)", background: "var(--surface)" }}
              >
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
              {isCurrentYear && (
                <span
                  className="text-metadata rounded px-1.5 py-0.5"
                  style={{ background: "var(--primary-subtle)", color: "var(--primary)" }}
                >
                  YTD
                </span>
              )}
            </div>
            <span className="text-metadata" style={{ color: "var(--text-muted)" }}>
              {formatDateRangeTR(dateFrom, dateTo)}
            </span>
          </div>
        }
      />

      {snapshot.isLoading && (
        <div className="rounded-lg p-5" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <LoadingState label="Yönetici özeti yükleniyor..." />
        </div>
      )}
      {snapshot.isError && (
        <div className="rounded-lg p-5" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <ErrorState />
        </div>
      )}

      {summary && (
        <>
          <div
            className="rounded-lg p-6 sm:p-8"
            style={{
              background: "var(--surface-hero)",
              border: "1px solid var(--surface-hero-border)",
              borderLeft: "4px solid var(--hero-accent)",
              boxShadow: "var(--shadow-panel)",
            }}
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-label" style={{ color: "var(--text-muted)" }}>
                  {isCurrentYear ? "YTD Fabrika Puanı" : "Yıllık Fabrika Puanı"}
                </p>
                <div className="mt-2 flex items-baseline gap-3">
                  <span
                    style={{
                      fontSize: "clamp(3rem, 7vw, 4.5rem)",
                      fontWeight: 700,
                      letterSpacing: "-0.02em",
                      lineHeight: 1,
                      color: "var(--hero-accent)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {summary.avgCompanyScore.toFixed(1)}
                  </span>
                  <span className="text-body" style={{ color: "var(--text-muted)" }}>
                    / 100
                  </span>
                </div>
              </div>
              {delta !== null && (
                <div
                  className="flex w-fit items-center gap-1.5 rounded-md px-3 py-2 text-sm font-semibold"
                  style={{
                    background: delta >= 0 ? "var(--status-positive-bg)" : "var(--status-negative-bg)",
                    color: delta >= 0 ? "var(--status-positive)" : "var(--status-negative)",
                    border: `1px solid ${delta >= 0 ? "var(--status-positive-border)" : "var(--status-negative-border)"}`,
                  }}
                >
                  {delta >= 0 ? <TrendingUp size={15} strokeWidth={2} /> : <TrendingDown size={15} strokeWidth={2} />}
                  <span className="tabular-nums">
                    {delta >= 0 ? "+" : ""}
                    {delta.toFixed(1)}
                  </span>
                  <span className="text-xs font-normal" style={{ color: "var(--text-muted)" }}>
                    geçen yıla göre
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              label="Yılın En Başarılı Formeni"
              value={summary.bestForeman?.name ?? "-"}
              sub={summary.bestForeman?.score != null ? `${summary.bestForeman.score.toFixed(1)} puan` : undefined}
              to={summary.bestForeman ? `/foremen/${summary.bestForeman.id}` : undefined}
              icon={Star}
              tone="positive"
              premiumSurface
            />
            <StatCard
              label="Yılın En Başarılı Tesisi"
              value={summary.bestPlant?.name ?? "-"}
              sub={summary.bestPlant?.score != null ? `${summary.bestPlant.score.toFixed(1)} puan` : undefined}
              to={summary.bestPlant ? `/plants/${summary.bestPlant.id}` : undefined}
              icon={Trophy}
              tone="positive"
              premiumSurface
            />
            <StatCard
              label="En Güçlü KPI"
              value={bestKpi?.name ?? "-"}
              sub={bestKpi ? `${bestKpi.avgScore.toFixed(1)} puan` : undefined}
              to={bestKpi ? `/kpis?kpi=${bestKpi.kpiId}` : undefined}
              icon={Target}
              tone="positive"
              premiumSurface
            />
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              label="Gelişim Alanı Tesisi"
              value={summary.worstPlant?.name ?? "-"}
              sub={summary.worstPlant?.score != null ? `${summary.worstPlant.score.toFixed(1)} puan` : undefined}
              to={summary.worstPlant ? `/plants/${summary.worstPlant.id}` : undefined}
              icon={TrendingDown}
              tone="attention"
              premiumSurface
            />
            <StatCard
              label="Gelişim Alanı KPI"
              value={summary.weakestKpi?.name ?? "-"}
              sub={summary.weakestKpi ? `${summary.weakestKpi.avgScore.toFixed(1)} puan` : undefined}
              to={summary.weakestKpi ? `/kpis?kpi=${summary.weakestKpi.id}` : undefined}
              icon={Target}
              tone="attention"
              premiumSurface
            />
            <div
              className="flex h-full flex-col justify-center gap-2 rounded-lg p-4"
              style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: "2px solid var(--primary)" }}
            >
              <span className="text-label" style={{ color: "var(--text-muted)" }}>
                Formen Dağılımı
              </span>
              {[
                { label: "Toplam Aktif Formen", value: summary.totalActiveForemen, color: "var(--primary)" },
                { label: "Başarılı", value: summary.foremenSuccessful, color: "var(--status-positive)" },
                { label: "Üstün Performans", value: summary.foremenOutstanding, color: "var(--status-neutral)" },
                { label: "Kritik", value: summary.foremenCritical, color: "var(--status-negative)" },
              ].map((row) => (
                <div key={row.label} className="flex items-center justify-between gap-3">
                  <span className="text-metadata flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
                    <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: row.color }} />
                    {row.label}
                  </span>
                  <span className="text-card-title tabular-nums" style={{ color: "var(--text-primary)" }}>
                    {row.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      <Card title="Performans Trendi" subtitle="Aylık ortalama, hedef 100">
        {trend.isLoading ? (
          <LoadingState />
        ) : trend.data ? (
          <TrendChart
            points={trend.data.points}
            seriesLabel="Fabrika"
            yAxisFloor={
              trend.data.points.length > 0 ? Math.min(...trend.data.points.map((p) => p.totalScore)) - 5 : undefined
            }
          />
        ) : (
          <ErrorState />
        )}
      </Card>
    </div>
  );
}
