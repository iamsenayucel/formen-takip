import { useEffect, useMemo, useState } from "react";
import { AlertOctagon, CalendarRange, Factory, Gauge, SearchCheck, ShieldAlert, TrendingUp } from "lucide-react";
import { useFilterOptions, useShiftAnalysisCards, useShiftHeatmap } from "../api/hooks";
import { useShiftAnalysisFilters } from "../hooks/useShiftAnalysisFilters";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PageHeader } from "../components/PageHeader";
import { ShiftAnomalyCard } from "../components/ShiftAnomalyCard";
import { ShiftAnomalyDetailModal } from "../components/ShiftAnomalyDetailModal";
import { ShiftAnomalyHeatmap } from "../components/ShiftAnomalyHeatmap";
import { MultiSelect } from "../components/FilterBar";
import { LoadMoreButton } from "../components/LoadMoreButton";
import type { ShiftAnomalyCard as ShiftAnomalyCardData } from "../api/types";
import { fieldClass, fieldStyle, labelClass, labelStyle } from "../lib/formStyles";

const CARDS_PAGE_SIZE = 8;

function SummaryTile({
  label, value, icon: Icon, accent,
}: { label: string; value: string; icon: typeof SearchCheck; accent?: string }) {
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

export function ShiftAnalysisPage() {
  const { filters, setFilters, clearFilters, asQueryParams, activeFilterCount } = useShiftAnalysisFilters();
  const [selectedCard, setSelectedCard] = useState<ShiftAnomalyCardData | null>(null);
  const [visibleCount, setVisibleCount] = useState(CARDS_PAGE_SIZE);

  const filterOptions = useFilterOptions();
  const cards = useShiftAnalysisCards(asQueryParams);
  const summary = cards.data?.summary;
  const allCards = cards.data?.items ?? [];
  const pagedCards = useMemo(() => allCards.slice(0, visibleCount), [allCards, visibleCount]);

  const heatmapParams = useMemo(
    () => ({ factory_ids: asQueryParams.factory_ids, plant_ids: asQueryParams.plant_ids, kpi_ids: asQueryParams.kpi_ids }),
    [asQueryParams.factory_ids, asQueryParams.plant_ids, asQueryParams.kpi_ids]
  );
  const heatmap = useShiftHeatmap(heatmapParams);
  const heatmapSummary = heatmap.data?.summary;

  useEffect(() => {
    setVisibleCount(CARDS_PAGE_SIZE);
  }, [asQueryParams]);

  const plantsForFactory = useMemo(() => {
    const plants = filterOptions.data?.plants ?? [];
    if (filters.factoryIds.length === 0) return plants;
    const allowed = new Set(filters.factoryIds);
    return plants.filter((p) => allowed.has(p.factoryId));
  }, [filterOptions.data, filters.factoryIds]);

  const handleFactoryChange = (ids: string[]) => {
    const allowed = new Set(ids);
    const factoryIdByPlant = new Map((filterOptions.data?.plants ?? []).map((p) => [p.id, p.factoryId]));
    setFilters({
      factoryIds: ids,
      plantIds:
        allowed.size === 0
          ? filters.plantIds
          : filters.plantIds.filter((plantId) => allowed.has(factoryIdByPlant.get(plantId) ?? "")),
    });
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Vardiya Analizi" />

      <div className="flex flex-wrap items-end gap-2 rounded-lg p-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <MultiSelect
          label="Fabrika"
          options={(filterOptions.data?.factories ?? []).map((f) => ({ id: f.id, name: f.code }))}
          selected={filters.factoryIds}
          onChange={handleFactoryChange}
          disabled={filterOptions.isLoading}
        />
        <MultiSelect
          label="Tesis"
          options={plantsForFactory.map((p) => ({ id: p.id, name: p.name }))}
          selected={filters.plantIds}
          onChange={(ids) => setFilters({ plantIds: ids })}
          disabled={filterOptions.isLoading}
        />
        <MultiSelect
          label="KPI"
          options={(filterOptions.data?.kpis ?? []).map((k) => ({ id: k.id, name: k.name }))}
          selected={filters.kpiIds}
          onChange={(ids) => setFilters({ kpiIds: ids })}
          disabled={filterOptions.isLoading}
        />
        <MultiSelect
          label="Vardiya"
          options={(filterOptions.data?.shifts ?? []).map((s) => ({ id: s.id, name: s.name }))}
          selected={filters.shiftIds}
          onChange={(ids) => setFilters({ shiftIds: ids })}
          disabled={filterOptions.isLoading}
        />
        <div>
          <label className={labelClass} style={labelStyle}>Anomali Seviyesi</label>
          <select
            className={fieldClass}
            style={fieldStyle}
            value={filters.severity}
            onChange={(e) => setFilters({ severity: e.target.value as never })}
          >
            <option value="">Tümü</option>
            <option value="high">Yüksek</option>
            <option value="medium">Orta</option>
          </select>
        </div>
        {activeFilterCount > 0 && (
          <button
            onClick={clearFilters}
            className="ml-auto flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--page-bg)]"
            style={{ color: "var(--accent)" }}
          >
            Filtreleri temizle ({activeFilterCount})
          </button>
        )}
      </div>

      {heatmapSummary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <SummaryTile label="Anomali Tespit Edilen Tesis" value={String(heatmapSummary.anomalyPlantCount)} icon={Factory} accent="var(--status-info)" />
          <SummaryTile label="Kritik Anomali Sayısı" value={String(heatmapSummary.criticalCellCount)} icon={AlertOctagon} accent="var(--status-negative)" />
          <SummaryTile label="En Çok Sapma Görülen KPI" value={heatmapSummary.topKpi?.name ?? "-"} icon={Gauge} accent="var(--primary)" />
          <SummaryTile label="Öncelikli İncelenmesi Gereken Tesis" value={String(heatmapSummary.priorityPlantCount)} icon={ShieldAlert} accent="var(--status-neutral)" />
        </div>
      )}

      <ShiftAnomalyHeatmap params={heatmapParams} />

      {summary && (
        <div>
          <h3 className="text-section-title mb-2" style={{ color: "var(--text-secondary)" }}>
            Tespit Kartları
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
            <SummaryTile label="İncelenen Dönem" value={summary.period.label} icon={CalendarRange} />
            <SummaryTile label="Toplam Tespit Edilen Anomali" value={String(summary.totalAnomalies)} icon={SearchCheck} />
            <SummaryTile label="En Çok Anomali Görülen Tesis" value={summary.topPlant?.name ?? "-"} icon={Factory} accent="var(--status-info)" />
            <SummaryTile label="En Çok Anomali Görülen KPI" value={summary.topKpi?.name ?? "-"} icon={Gauge} accent="var(--primary)" />
            <SummaryTile
              label="En Yüksek Fark Oranı"
              value={summary.maxPctDiff !== null ? `%${summary.maxPctDiff.toFixed(1)}` : "-"}
              icon={TrendingUp}
              accent="var(--status-negative)"
            />
          </div>
        </div>
      )}

      <Card>
        {cards.isLoading && <LoadingState label="Tespit kartları yükleniyor..." />}
        {cards.isError && <ErrorState />}
        {cards.data && cards.data.items.length === 0 && (
          <EmptyState message="Seçilen filtrelerle eşleşen bir vardiya anomalisi bulunamadı." />
        )}
        {cards.data && cards.data.items.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {pagedCards.map((card) => (
                <ShiftAnomalyCard key={card.id} card={card} onViewDetail={setSelectedCard} />
              ))}
            </div>
            <LoadMoreButton
              hasMore={visibleCount < allCards.length}
              isFetchingNextPage={false}
              onLoadMore={() => setVisibleCount((c) => c + CARDS_PAGE_SIZE)}
              loadedCount={pagedCards.length}
              total={allCards.length}
              itemLabel="tespit kartı"
            />
          </>
        )}
      </Card>

      {selectedCard && <ShiftAnomalyDetailModal card={selectedCard} onClose={() => setSelectedCard(null)} />}
    </div>
  );
}
