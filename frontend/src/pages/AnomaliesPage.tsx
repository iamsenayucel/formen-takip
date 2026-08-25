import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  ListChecks,
  Search,
  SearchCheck,
  X,
} from "lucide-react";
import { useAnomalies, useAnomalySummary, useFilterOptions } from "../api/hooks";
import { useAnomalyFilters } from "../hooks/useAnomalyFilters";
import { DATE_PRESETS } from "../hooks/useFilters";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { LoadMoreButton } from "../components/LoadMoreButton";
import { PageHeader } from "../components/PageHeader";
import { AnalysisStatusBadge, SEVERITY_CONFIG, SeverityBadge, StatusBadge } from "../components/AnomalyBadges";
import { rankAnomaliesByPriority } from "../lib/anomalyMetrics";
import { clickableRowProps } from "../lib/a11y";
import { rowHoverClass, rowStyle, tableClass, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";

const SEVERITY_OPTIONS: { value: string; label: string }[] = [
  { value: "low", label: "Düşük" },
  { value: "medium", label: "Orta" },
  { value: "high", label: "Yüksek" },
  { value: "critical", label: "Kritik" },
];
const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "new", label: "Yeni" },
  { value: "in_review", label: "İnceleniyor" },
  { value: "action_pending", label: "Aksiyon Bekliyor" },
  { value: "resolved", label: "Çözüldü" },
  { value: "closed", label: "Kapatıldı" },
];
const ANALYSIS_STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "not_analyzed", label: "Analiz Edilmedi" },
  { value: "analyzing", label: "Analiz Ediliyor" },
  { value: "completed", label: "Analiz Tamamlandı" },
  { value: "failed", label: "Analiz Başarısız" },
];

function SummaryTile({
  label, value, icon: Icon, accent,
}: { label: string; value: number; icon: typeof Search; accent?: string }) {
  return (
    <div
      className="rounded-lg p-4"
      style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: `2px solid ${accent ?? "var(--primary)"}` }}
    >
      <div className="flex items-center gap-1.5">
        <Icon size={13} strokeWidth={2} style={{ color: accent ?? "var(--text-muted)" }} />
        <p className="text-label" style={{ color: "var(--text-muted)" }}>{label}</p>
      </div>
      <p className="text-hero-metric mt-1.5" style={{ color: "var(--text-primary)" }}>{value}</p>
    </div>
  );
}

function PriorityStrip({ items, onSelect }: { items: ReturnType<typeof rankAnomaliesByPriority>; onSelect: (id: string) => void }) {
  const top = items.slice(0, 3);
  if (top.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <p className="text-label" style={{ color: "var(--text-muted)" }}>Öncelikli Tespitler</p>
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        {top.map((a) => {
          const cfg = SEVERITY_CONFIG[a.severity];
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => onSelect(a.id)}
              className="flex flex-col gap-1.5 rounded-lg p-3 text-left transition-transform duration-150 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/40"
              style={{ background: "var(--surface)", border: "1px solid var(--border)", borderLeft: `3px solid ${cfg.color}` }}
            >
              <div className="flex items-center justify-between gap-2">
                <SeverityBadge severity={a.severity} />
                <span className="text-metadata" style={{ color: "var(--text-muted)" }}>
                  {new Date(a.detectedAt).toLocaleDateString("tr-TR")}
                </span>
              </div>
              <p className="text-body font-semibold" style={{ color: "var(--text-primary)" }}>{a.title}</p>
              <p className="text-metadata" style={{ color: "var(--text-secondary)" }}>
                {a.plantName ?? "-"} · {a.kpiName ?? a.anomalyTypeLabel}
              </p>
              <span className="mt-auto flex items-center gap-1 text-xs font-medium" style={{ color: "var(--primary)" }}>
                Analizi Gör
                <ArrowRight size={12} strokeWidth={2} />
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function AnomaliesPage() {
  const navigate = useNavigate();
  const { filters, setFilters, clearFilters, asQueryParams, activeFilterCount } = useAnomalyFilters();
  const [search, setSearch] = useState("");

  const filterOptions = useFilterOptions();
  const summary = useAnomalySummary();
  const anomalies = useAnomalies({ ...asQueryParams, search: search || undefined }, 20);
  const anomalyItems = anomalies.data?.pages.flatMap((p) => p.items) ?? [];
  const anomalyTotal = anomalies.data?.pages[0]?.pagination.total ?? null;

  const plantsForFactory = useMemo(() => {
    const plants = filterOptions.data?.plants ?? [];
    if (!filters.factory) return plants;
    const factory = filterOptions.data?.factories.find((f) => f.code === filters.factory);
    return factory ? plants.filter((p) => p.factoryId === factory.id) : plants;
  }, [filterOptions.data, filters.factory]);

  const priorityItems = useMemo(
    () => rankAnomaliesByPriority(anomalyItems),
    [anomalyItems]
  );

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Tespitler" />

      {summary.isLoading && <LoadingState />}
      {summary.isError && <ErrorState />}
      {summary.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
          <SummaryTile label="Toplam Aktif Tespit" value={summary.data.totalActive} icon={SearchCheck} />
          <SummaryTile label="Kritik" value={summary.data.criticalCount} icon={AlertOctagon} accent="var(--status-negative)" />
          <SummaryTile label="Yüksek Önem" value={summary.data.highCount} icon={AlertTriangle} accent="var(--status-neutral)" />
          <SummaryTile label="Analiz Bekliyor" value={summary.data.pendingAnalysisCount} icon={Clock} accent="var(--status-info)" />
          <SummaryTile label="Son 7 Günde Açılan" value={summary.data.openedLast7Days} icon={ListChecks} />
          <SummaryTile label="Çözülen" value={summary.data.resolvedCount} icon={CheckCircle2} accent="var(--status-positive)" />
        </div>
      )}

      {anomalyItems.length > 0 && <PriorityStrip items={priorityItems} onSelect={(id) => navigate(`/anomalies/${id}`)} />}

      <div className="flex flex-wrap items-end gap-2 rounded-lg p-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <div>
          <label className={labelClass} style={labelStyle}>Hazır tarih aralığı</label>
          <select
            className={fieldClass}
            style={fieldStyle}
            onChange={(e) => {
              const preset = DATE_PRESETS.find((p) => p.label === e.target.value);
              if (preset) {
                const [from, to] = preset.getRange();
                setFilters({ dateFrom: from, dateTo: to });
              }
            }}
            defaultValue=""
          >
            <option value="" disabled>Seçiniz</option>
            {DATE_PRESETS.map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Başlangıç</label>
          <input type="date" className={fieldClass} style={fieldStyle} value={filters.dateFrom}
            onChange={(e) => { setFilters({ dateFrom: e.target.value }); }} />
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Bitiş</label>
          <input type="date" className={fieldClass} style={fieldStyle} value={filters.dateTo}
            onChange={(e) => { setFilters({ dateTo: e.target.value }); }} />
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Fabrika</label>
          <select className={fieldClass} style={fieldStyle} value={filters.factory}
            onChange={(e) => { setFilters({ factory: e.target.value, plantIds: [] }); }}>
            <option value="">Tümü</option>
            {filterOptions.data?.factories.map((f) => (
              <option key={f.id} value={f.code}>{f.code}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Tesis</label>
          <select className={fieldClass} style={fieldStyle} value={filters.plantIds[0] ?? ""}
            onChange={(e) => { setFilters({ plantIds: e.target.value ? [e.target.value] : [] }); }}>
            <option value="">Tümü</option>
            {plantsForFactory.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Vardiya</label>
          <select className={fieldClass} style={fieldStyle} value={filters.shiftIds[0] ?? ""}
            onChange={(e) => { setFilters({ shiftIds: e.target.value ? [e.target.value] : [] }); }}>
            <option value="">Tümü</option>
            {filterOptions.data?.shifts.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>KPI</label>
          <select className={fieldClass} style={fieldStyle} value={filters.kpiIds[0] ?? ""}
            onChange={(e) => { setFilters({ kpiIds: e.target.value ? [e.target.value] : [] }); }}>
            <option value="">Tümü</option>
            {filterOptions.data?.kpis.map((k) => (
              <option key={k.id} value={k.id}>{k.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Önem Seviyesi</label>
          <select className={fieldClass} style={fieldStyle} value={filters.severity}
            onChange={(e) => { setFilters({ severity: e.target.value as never }); }}>
            <option value="">Tümü</option>
            {SEVERITY_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>Tespit Durumu</label>
          <select className={fieldClass} style={fieldStyle} value={filters.status}
            onChange={(e) => { setFilters({ status: e.target.value as never }); }}>
            <option value="">Tümü</option>
            {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label className={labelClass} style={labelStyle}>YZ Analiz Durumu</label>
          <select className={fieldClass} style={fieldStyle} value={filters.analysisStatus}
            onChange={(e) => { setFilters({ analysisStatus: e.target.value as never }); }}>
            <option value="">Tümü</option>
            {ANALYSIS_STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div className="relative">
          <label className={labelClass} style={labelStyle}>Ara</label>
          <Search size={13} strokeWidth={2} className="pointer-events-none absolute left-2 top-[30px]" style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Başlık veya açıklamada ara..."
            className={`${fieldClass} pl-7`}
            style={{ ...fieldStyle, width: 220 }}
            value={search}
            onChange={(e) => { setSearch(e.target.value); }}
          />
        </div>
        {(activeFilterCount > 0 || search) && (
          <button
            onClick={() => { clearFilters(); setSearch(""); }}
            className="ml-auto flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium hover:underline"
            style={{ color: "var(--accent)" }}
          >
            <X size={12} strokeWidth={2} />
            Filtreleri temizle ({activeFilterCount + (search ? 1 : 0)})
          </button>
        )}
      </div>

      <Card>
        {anomalies.isLoading && <LoadingState label="Tespitler yükleniyor..." />}
        {anomalies.isError && <ErrorState />}
        {anomalies.data && anomalyItems.length === 0 && (
          <EmptyState message="Seçilen filtrelerle eşleşen tespit bulunamadı." />
        )}
        {anomalyItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Tespit</th>
                  <th className={thClass} style={thStyle}>Fabrika / Tesis</th>
                  <th className={thClass} style={thStyle}>Vardiya</th>
                  <th className={thClass} style={thStyle}>KPI</th>
                  <th className={thClass} style={thStyle}>Tespit Tarihi</th>
                  <th className={thClass} style={thStyle}>Sapma</th>
                  <th className={thClass} style={thStyle}>ML Güveni</th>
                  <th className={thClass} style={thStyle}>Önem</th>
                  <th className={thClass} style={thStyle}>Durum</th>
                  <th className={thClass} style={thStyle}>YZ Analizi</th>
                </tr>
              </thead>
              <tbody>
                {anomalyItems.map((a) => (
                  <tr
                    key={a.id}
                    style={rowStyle}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    {...clickableRowProps(() => navigate(`/anomalies/${a.id}`), `${a.title} tespitini görüntüle`)}
                  >
                    <td className={tdClass}>
                      <p className="font-medium" style={{ color: "var(--text-primary)" }}>{a.title}</p>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{a.code} · {a.anomalyTypeLabel}</p>
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                      {a.factoryCode} · {a.plantName ?? "-"}
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{a.shiftName ?? "Tüm vardiyalar"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{a.kpiName ?? "-"}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{a.detectedAt.slice(0, 10)}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>
                      %{a.deviationPercent.toFixed(1)}
                    </td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>
                      {(a.mlConfidence * 100).toFixed(0)}%
                    </td>
                    <td className={tdClass}><SeverityBadge severity={a.severity} /></td>
                    <td className={tdClass}><StatusBadge status={a.status} /></td>
                    <td className={tdClass}><AnalysisStatusBadge status={a.analysisStatus} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <LoadMoreButton
              hasMore={!!anomalies.hasNextPage}
              isFetchingNextPage={anomalies.isFetchingNextPage}
              onLoadMore={() => void anomalies.fetchNextPage()}
              loadedCount={anomalyItems.length}
              total={anomalyTotal}
              itemLabel="tespit"
            />
          </div>
        )}
      </Card>
    </div>
  );
}
