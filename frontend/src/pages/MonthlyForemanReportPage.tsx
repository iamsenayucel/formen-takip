import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, Download, PartyPopper } from "lucide-react";
import { apiClient } from "../api/client";
import { useForemanMonthlyReport } from "../api/hooks";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { EntityHero } from "../components/EntityHero";
import { BackLink } from "../components/BackLink";
import { StatCard } from "../components/StatCard";
import { TrendChart } from "../components/charts/TrendChart";
import type { MonthlyReportAccess, MonthlyReportComparison, MonthlyReportKpiEntry } from "../api/types";

function comparisonStatusText(label: string, comparison: MonthlyReportComparison): string {
  const pos = comparison.status === "at" ? `${label}te` : comparison.status === "above" ? `${label}nin üzerinde` : `${label}nin altında`;
  return pos;
}

function ComparisonRow({ label, comparison, unit }: { label: string; comparison: MonthlyReportComparison; unit: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span style={{ color: "var(--text-muted)" }}>{label}: {comparison.value.toFixed(2)} {unit}</span>
      <span className="font-medium" style={{ color: comparison.isFavorable ? "var(--status-positive)" : "var(--status-negative)" }}>
        {comparisonStatusText(label, comparison)}
      </span>
    </div>
  );
}

function ProgressBar({ score, color }: { score: number | null; color: string }) {
  const pct = Math.max(0, Math.min(100, ((score ?? 0) / 120) * 100));
  return (
    <div className="h-1.5 w-full rounded-full" style={{ background: "var(--border)" }}>
      <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function KpiCard({ kpi }: { kpi: MonthlyReportKpiEntry }) {
  if (!kpi.hasData) {
    return (
      <div className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
        <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{kpi.name}</p>
        <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>Bu ay için veri bulunmuyor.</p>
      </div>
    );
  }
  return (
    <div className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>{kpi.name}</p>
        {kpi.level && <PerformanceLevelBadge level={kpi.level} />}
      </div>
      <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>
        {kpi.actual?.toFixed(2)} {kpi.unit}
      </p>
      <div className="mt-1.5">
        <ProgressBar score={kpi.score} color={kpi.level?.color ?? "var(--accent)"} />
      </div>
      <div className="mt-2 flex flex-col gap-1">
        {kpi.vsPersonalTarget && <ComparisonRow label="Kişisel/Tesis Hedefi" comparison={kpi.vsPersonalTarget} unit={kpi.unit} />}
        {kpi.vsFactoryAverage && <ComparisonRow label="Fabrika Ortalaması" comparison={kpi.vsFactoryAverage} unit={kpi.unit} />}
      </div>
    </div>
  );
}

export function MonthlyForemanReportPage() {
  const { foremanId, year, month } = useParams<{ foremanId: string; year: string; month: string }>();
  const navigate = useNavigate();
  const [downloading, setDownloading] = useState(false);
  const yearNum = year ? Number(year) : undefined;
  const monthNum = month ? Number(month) : undefined;
  const report = useForemanMonthlyReport(foremanId, yearNum, monthNum);

  const handleDownload = async () => {
    if (!foremanId || !yearNum || !monthNum) return;
    setDownloading(true);
    try {
      // Backend'den erişim URL'i alınır — frontend AWS/CloudFront hakkında hiçbir şey
      // bilmez. Production'da bu bir kısa ömürlü CloudFront signed URL'idir (requires_auth:
      // false, doğrudan yeni sekmede açılır); CloudFront henüz yapılandırılmamışsa backend
      // üzerinden authenticated bir proxy path'ine düşer (requires_auth: true, mevcut
      // blob-indirme akışıyla aynı şekilde ele alınır).
      const { data: access } = await apiClient.get<MonthlyReportAccess>(
        `/foremen/${foremanId}/monthly-reports/${yearNum}/${monthNum}/access`
      );
      if (!access.requiresAuth) {
        window.open(access.url, "_blank", "noopener,noreferrer");
        return;
      }
      const resp = await apiClient.get(access.url, { responseType: "blob" });
      const blobUrl = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `formen-performans-raporu-${yearNum}-${String(monthNum).padStart(2, "0")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } finally {
      setDownloading(false);
    }
  };

  if (report.isLoading) return <LoadingState />;
  if (report.isError || !report.data) return <ErrorState message="Rapor bulunamadı." />;

  const data = report.data.reportData;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <BackLink label={data.foreman.fullName} onClick={() => navigate(`/foremen/${foremanId}`)} />
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60"
          style={{ background: "var(--primary)" }}
        >
          <Download size={13} strokeWidth={2} />
          {downloading ? "İndiriliyor..." : "PDF İndir"}
        </button>
      </div>

      <EntityHero
        eyebrow="Aylık Değerlendirme"
        title={data.foreman.fullName}
        subtitle={`Sicil No: ${data.foreman.employeeNumber} · ${data.period.label}`}
        metaItems={[
          data.org?.factoryName,
          data.org && data.org.plants.length > 0 ? data.org.plants.map((p) => p.name).join(", ") : null,
          data.org?.chiefName ? `Şef: ${data.org.chiefName}` : null,
          `Oluşturulma: ${new Date(data.generatedAt).toLocaleDateString("tr-TR")}`,
        ]}
        score={data.overall?.score ?? null}
        scoreMax={120}
        scoreLabel="Aylık Performans Puanı"
        level={data.overall?.level}
        extraLines={
          data.overall
            ? [
                { label: "Operasyonel Performans", value: `${data.overall.operationalScore.toFixed(1)} / 100` },
                { label: "Operational Impact+ Bonusu", value: `+${data.overall.contributionBonus}`, tone: "positive" },
              ]
            : undefined
        }
      />

      {data.organizationHistory && data.organizationHistory.length > 1 && (
        <div className="flex flex-col gap-1 rounded-md p-3" style={{ background: "var(--surface-muted)", border: "1px solid var(--border-subtle)" }}>
          <p className="text-label" style={{ color: "var(--text-secondary)" }}>Ay içinde organizasyon değişikliği</p>
          {data.organizationHistory.map((entry, i) => (
            <p key={i} className="text-metadata" style={{ color: "var(--text-muted)" }}>
              {new Date(entry.dateFrom).toLocaleDateString("tr-TR")} – {new Date(entry.dateTo).toLocaleDateString("tr-TR")}:{" "}
              {entry.factoryName} &middot; {entry.plants.map((p) => p.name).join(", ")} &middot; Şef: {entry.chiefName}
            </p>
          ))}
        </div>
      )}

      {data.insufficientData ? (
        <Card>
          <EmptyState message={data.insufficientDataReason ?? "Bu dönem için değerlendirme oluşturmak adına yeterli veri bulunmamaktadır."} />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Değerlendirilen KPI" value={data.overall!.kpiCount.total} />
            <StatCard label="Hedefte / Üzerinde" value={data.overall!.kpiCount.aboveOrAtTarget} tone="positive" />
            <StatCard label="Hedefin Altında" value={data.overall!.kpiCount.belowTarget} tone="attention" />
            <StatCard label="Kritik" value={data.overall!.kpiCount.critical} tone="critical" />
          </div>
          {data.summaryText && <p className="text-body" style={{ color: "var(--text-secondary)" }}>{data.summaryText}</p>}

          <Card title="KPI Detayları">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.kpis?.map((kpi) => <KpiCard key={kpi.kpiId} kpi={kpi} />)}
            </div>
          </Card>

          {data.congratulations?.shown && data.congratulations.text && (
            <Card>
              <div className="flex items-start gap-3 rounded-md p-3" style={{ background: "var(--status-positive-bg)", border: "1px solid var(--status-positive-border)" }}>
                <PartyPopper size={18} strokeWidth={2} style={{ color: "var(--status-positive)" }} className="mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-semibold" style={{ color: "var(--status-positive)" }}>Tebrikler!</p>
                  <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>{data.congratulations.text}</p>
                </div>
              </div>
            </Card>
          )}

          {data.strengths && data.strengths.length > 0 && (
            <Card title="Güçlü Olduğun Alanlar">
              <ul className="flex flex-col gap-2">
                {data.strengths.map((item) => (
                  <li key={item.kpiCode} className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{item.name}</span> — {item.text}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {data.improvements && data.improvements.length > 0 && (
            <Card title="Geliştirebileceğin Alanlar">
              <ul className="flex flex-col gap-2">
                {data.improvements.map((item) => (
                  <li key={item.kpiCode} className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{item.name}</span> — {item.text}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {data.criticalAttention && data.criticalAttention.length > 0 && (
            <Card title="Dikkat Gerektiren Konular">
              <div className="flex flex-col gap-3">
                {data.criticalAttention.map((item) => (
                  <div key={item.kpiCode} className="flex items-start gap-3 rounded-md p-3" style={{ background: "var(--status-negative-bg)", border: "1px solid var(--status-negative-border)" }}>
                    <AlertTriangle size={18} strokeWidth={2} style={{ color: "var(--status-negative)" }} className="mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-semibold" style={{ color: "var(--status-negative)" }}>{item.name}</p>
                      <p className="mt-1 text-sm" style={{ color: "var(--text-secondary)" }}>{item.text}</p>
                      {item.managerPrompt && <p className="mt-1 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{item.managerPrompt}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {data.trend && data.trend.weeklyPoints.length > 0 && (
            <Card title="Aylık Trend Analizi">
              <TrendChart points={data.trend.weeklyPoints.map((p) => ({ date: p.bucket, totalScore: p.totalScore, isReliable: p.isReliable }))} />
              {data.trend.text && <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>{data.trend.text}</p>}
            </Card>
          )}

          {data.previousMonth?.available && (
            <Card title={`Geçen Aya Göre (${data.previousMonth.label})`}>
              <ul className="flex flex-col gap-1.5 text-sm">
                {data.previousMonth.perKpi?.map((item) => (
                  <li key={item.code} className="flex items-center justify-between">
                    <span style={{ color: "var(--text-secondary)" }}>{item.name}</span>
                    <span className="font-medium tabular-nums" style={{ color: item.isImprovement ? "var(--status-positive)" : "var(--status-negative)" }}>
                      {item.diff >= 0 ? "+" : ""}{item.diff.toFixed(2)} {item.isImprovement ? "(iyileşme)" : "(kötüleşme)"}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {data.closingText && (
            <Card title="Aylık Değerlendirme">
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{data.closingText}</p>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
