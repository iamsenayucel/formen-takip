import { useState } from "react";
import { CheckCircle2, Download, FileText, XCircle } from "lucide-react";
import { Can } from "../components/Can";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PageHeader } from "../components/PageHeader";
import { useFilters } from "../hooks/useFilters";
import { FilterBar } from "../components/FilterBar";
import { LoadMoreButton } from "../components/LoadMoreButton";
import { apiClient } from "../api/client";
import { useGenerateReport, useReportHistory } from "../api/hooks";
import type { ReportFormat, ReportType } from "../api/types";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";
import { rowStyle, tableClass, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  company_summary: "Şirket Genel Performans",
  plant_comparison: "Tesis Karşılaştırma",
  shift_comparison: "Vardiya Karşılaştırma",
  foreman_performance: "Formen Performans",
  kpi_analysis: "KPI Analiz",
  critical_performance: "Kritik Performans",
  missing_data: "Eksik Veri",
};
const FORMAT_LABELS: Record<ReportFormat, string> = { csv: "CSV", xlsx: "Excel", pdf: "PDF" };

// Backend'in gerçek ReportStatus enum'u (completed/failed) — üretim senkron
// olduğundan bekleyen bir ara durum kalıcı olarak saklanmaz. Alan opsiyonel
// (eski kayıtlarda olmayabilir), bu yüzden bilinmeyen durum nötr gösterilir.
function ReportStatusBadge({ status }: { status?: string | null }) {
  if (status === "completed") {
    return (
      <span className="text-metadata inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium" style={{ background: "var(--status-positive-bg)", color: "var(--status-positive)" }}>
        <CheckCircle2 size={11} strokeWidth={2} />
        Tamamlandı
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="text-metadata inline-flex items-center gap-1 rounded px-1.5 py-0.5 font-medium" style={{ background: "var(--status-negative-bg)", color: "var(--status-negative)" }}>
        <XCircle size={11} strokeWidth={2} />
        Başarısız
      </span>
    );
  }
  return <span className="text-metadata" style={{ color: "var(--text-muted)" }}>-</span>;
}

export function ReportsPage() {
  const { filters, setFilters, clearFilters } = useFilters();
  const [reportType, setReportType] = useState<ReportType>("plant_comparison");
  const [format, setFormat] = useState<ReportFormat>("xlsx");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const generate = useGenerateReport();
  const history = useReportHistory(10);
  const historyItems = history.data?.pages.flatMap((page) => page.items) ?? [];
  const historyTotal = history.data?.pages.at(-1)?.pagination.total;

  const handleGenerate = () => {
    generate.mutate({
      reportType, format,
      dateFrom: filters.dateFrom, dateTo: filters.dateTo,
      plantIds: filters.plantIds.length ? filters.plantIds : undefined,
      factoryIds: filters.factoryIds.length ? filters.factoryIds : undefined,
      chiefIds: filters.chiefIds.length ? filters.chiefIds : undefined,
      shiftIds: filters.shiftIds.length ? filters.shiftIds : undefined,
      kpiIds: filters.kpiIds.length ? filters.kpiIds : undefined,
    });
  };

  const handleDownload = async (id: string, fileName: string) => {
    setDownloadingId(id);
    try {
      const resp = await apiClient.get(`/reports/${id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Raporlar" />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <Can permission="reports.create">
        <Card title="Yeni Rapor Oluştur">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className={labelClass} style={labelStyle}>Rapor Türü</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value as ReportType)}
                className={fieldClass}
                style={fieldStyle}
              >
                {Object.entries(REPORT_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass} style={labelStyle}>Format</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as ReportFormat)}
                className={fieldClass}
                style={fieldStyle}
              >
                {Object.entries(FORMAT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <button
              onClick={handleGenerate}
              disabled={generate.isPending}
              className="rounded-md px-4 py-2 text-[13px] font-medium text-white disabled:opacity-60"
              style={{ background: "var(--primary)" }}
            >
              {generate.isPending ? "Oluşturuluyor..." : "Rapor Oluştur"}
            </button>
          </div>

          {generate.isSuccess && (
            <div
              className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md p-3"
              style={{ background: "var(--status-positive-bg)", border: "1px solid var(--status-positive-border)" }}
            >
              <p className="text-body flex items-center gap-1.5 font-medium" style={{ color: "var(--status-positive)" }}>
                <CheckCircle2 size={14} strokeWidth={2} className="shrink-0" />
                "{generate.data.fileName}" oluşturuldu ({generate.data.rowCount} satır)
              </p>
              <Can permission="reports.download">
                <button
                  onClick={() => handleDownload(generate.data.id, generate.data.fileName)}
                  disabled={downloadingId === generate.data.id}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                  style={{ background: "var(--surface)", border: "1px solid var(--status-positive-border)", color: "var(--status-positive)" }}
                >
                  <Download size={12} strokeWidth={2} />
                  {downloadingId === generate.data.id ? "İndiriliyor..." : "Şimdi İndir"}
                </button>
              </Can>
            </div>
          )}
          {generate.isError && (
            <p className="text-body mt-3 flex items-center gap-1.5 font-medium" style={{ color: "var(--status-negative)" }}>
              <XCircle size={13} strokeWidth={2} />
              Rapor oluşturulamadı.
            </p>
          )}
        </Card>
      </Can>

      <Card title="Rapor Geçmişi">
        {history.isLoading && <LoadingState />}
        {history.isError && <ErrorState />}
        {history.data && historyItems.length === 0 && <EmptyState message="Henüz rapor oluşturulmadı." />}
        {history.data && historyItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Dosya</th>
                  <th className={thClass} style={thStyle}>Tür</th>
                  <th className={thClass} style={thStyle}>Format</th>
                  <th className={thClass} style={thStyle}>Satır</th>
                  <th className={thClass} style={thStyle}>Durum</th>
                  <th className={thClass} style={thStyle}>Oluşturan</th>
                  <th className={thClass} style={thStyle}>Tarih</th>
                  <th className={thClass} style={thStyle} />
                </tr>
              </thead>
              <tbody>
                {historyItems.map((r) => (
                  <tr key={r.id} style={rowStyle}>
                    <td className={tdClass}>
                      <span className="flex items-center gap-1.5 font-medium" style={{ color: "var(--text-primary)" }}>
                        <FileText size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
                        {r.fileName}
                      </span>
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{REPORT_TYPE_LABELS[r.reportType as ReportType] ?? r.reportType}</td>
                    <td className={`${tdClass} uppercase`} style={{ color: "var(--text-secondary)" }}>{r.format}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{r.rowCount}</td>
                    <td className={tdClass}><ReportStatusBadge status={r.status} /></td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{r.requestedBy ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{new Date(r.createdAt).toLocaleString("tr-TR")}</td>
                    <td className={tdClass}>
                      <Can permission="reports.download">
                        <button
                          onClick={() => handleDownload(r.id, r.fileName)}
                          disabled={downloadingId === r.id}
                          aria-label={`${r.fileName} dosyasını indir`}
                          className="flex items-center gap-1 text-xs font-medium hover:underline disabled:opacity-50"
                          style={{ color: "var(--primary)" }}
                        >
                          <Download size={12} strokeWidth={2} />
                          {downloadingId === r.id ? "İndiriliyor..." : "İndir"}
                        </button>
                      </Can>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <LoadMoreButton
              hasMore={!!history.hasNextPage}
              isFetchingNextPage={history.isFetchingNextPage}
              onLoadMore={() => void history.fetchNextPage()}
              loadedCount={historyItems.length}
              total={historyTotal}
              itemLabel="rapor"
            />
          </div>
        )}
      </Card>
    </div>
  );
}
