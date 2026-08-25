import { useMemo, useState } from "react";
import { LayoutGrid, Plus, Table2 } from "lucide-react";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PageHeader } from "../components/PageHeader";
import { LoadMoreButton } from "../components/LoadMoreButton";
import { MultiSelect } from "../components/FilterBar";
import { ContributionSummaryStats } from "../components/ContributionSummaryStats";
import { ContributionWorkCard } from "../components/ContributionWorkCard";
import { ContributionWorkTable, type ContributionSortField } from "../components/ContributionWorkTable";
import { ContributionWorkForm } from "../components/ContributionWorkForm";
import { useContributionWorks, useFilterOptions, useForemen } from "../api/hooks";
import { useContributionFilters } from "../hooks/useContributionFilters";
import { DATE_PRESETS } from "../hooks/useFilters";
import type { ContributionWorkType, FinancialGainStatus, ImpactLevel } from "../api/types";
import { FINANCIAL_STATUS_FILTER_LABELS, IMPACT_LEVEL_LABELS, WORK_TYPE_LABELS } from "../lib/contributionTheme";
import { searchInputClass, searchInputStyle } from "../lib/tableStyles";

const VIEW_STORAGE_KEY = "formen_improvement_works_view";

type ViewMode = "card" | "table";

function readStoredView(): ViewMode {
  return localStorage.getItem(VIEW_STORAGE_KEY) === "table" ? "table" : "card";
}

export function ImprovementWorksPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useContributionFilters();
  const [search, setSearch] = useState("");
  const [foremanQuery, setForemanQuery] = useState("");
  const [foremanName, setForemanName] = useState("");
  const [view, setView] = useState<ViewMode>(readStoredView);
  const [formOpen, setFormOpen] = useState(false);
  const [sortBy, setSortBy] = useState<ContributionSortField>("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  function handleSort(field: ContributionSortField) {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir("asc");
    }
  }

  const filterOptions = useFilterOptions();
  const foremenSearch = useForemen({ search: foremanQuery || undefined }, 6);
  const foremenSearchItems = foremenSearch.data?.pages[0]?.items ?? [];

  const plantsForFactory = useMemo(
    () => (filterOptions.data?.plants ?? []).filter((p) => !filters.factoryIds.length || filters.factoryIds.includes(p.factoryId)),
    [filterOptions.data, filters.factoryIds]
  );

  const params = {
    ...asQueryParams,
    search: search || undefined,
    sort_by: sortBy,
    sort_dir: sortDir,
  };
  const works = useContributionWorks(params, 12);
  const workItems = works.data?.pages.flatMap((p) => p.items) ?? [];
  const workTotal = works.data?.pages[0]?.pagination.total ?? null;

  const activeFilterCount = [
    filters.dateFrom, filters.dateTo, filters.plantIds[0], filters.factoryIds[0], filters.foremanIds[0],
    filters.workType, filters.impactLevel, filters.financialGainStatus,
  ].filter(Boolean).length;

  const setView2 = (v: ViewMode) => {
    setView(v);
    localStorage.setItem(VIEW_STORAGE_KEY, v);
  };

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Operational Impact+"
        actions={
          <button
            onClick={() => setFormOpen(true)}
            className="flex shrink-0 items-center gap-1.5 rounded-md px-3.5 py-2 text-[13px] font-medium text-white"
            style={{ background: "var(--primary)" }}
          >
            <Plus size={14} strokeWidth={2} />
            Yeni Çalışma Ekle
          </button>
        }
      />

      <ContributionSummaryStats params={{ ...asQueryParams, search: search || undefined }} />

      <div className="flex flex-wrap items-center gap-2 rounded-lg p-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <select
          className={searchInputClass}
          style={{ ...searchInputStyle, maxWidth: "10.5rem" }}
          onChange={(e) => {
            const preset = DATE_PRESETS.find((p) => p.label === e.target.value);
            if (preset) {
              const [from, to] = preset.getRange();
              setFilters({ dateFrom: from, dateTo: to });
            }
          }}
          defaultValue=""
        >
          <option value="" disabled>Hazır tarih aralığı</option>
          {DATE_PRESETS.map((p) => <option key={p.label} value={p.label}>{p.label}</option>)}
        </select>
        <input type="date" value={filters.dateFrom} onChange={(e) => setFilters({ dateFrom: e.target.value })} className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "9.5rem" }} />
        <span style={{ color: "var(--text-muted)" }}>–</span>
        <input type="date" value={filters.dateTo} onChange={(e) => setFilters({ dateTo: e.target.value })} className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "9.5rem" }} />

        <select
          value={filters.factoryIds[0] ?? ""}
          onChange={(e) => setFilters({ factoryIds: e.target.value ? [e.target.value] : [], plantIds: [] })}
          className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "9rem" }}
        >
          <option value="">Tüm fabrikalar</option>
          {filterOptions.data?.factories.map((f) => <option key={f.id} value={f.id}>{f.code}</option>)}
        </select>

        <MultiSelect
          label="Tesis"
          options={plantsForFactory.map((p) => ({ id: p.id, name: p.name }))}
          selected={filters.plantIds}
          onChange={(ids) => setFilters({ plantIds: ids })}
        />

        <div className="relative">
          <input
            type="search"
            placeholder="Formen ara..."
            value={foremanName || foremanQuery}
            onChange={(e) => { setForemanQuery(e.target.value); setForemanName(""); }}
            className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "10rem" }}
          />
          {foremanQuery && !foremanName && foremenSearchItems.length > 0 && (
            <div className="absolute z-20 mt-1 w-56 rounded-md shadow-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              {foremenSearchItems.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => { setFilters({ foremanIds: [f.id] }); setForemanName(f.fullName); setForemanQuery(""); }}
                  className="block w-full px-2 py-1.5 text-left text-xs hover:bg-[var(--page-bg)]"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {f.fullName} — {f.employeeNumber}
                </button>
              ))}
            </div>
          )}
        </div>

        <select
          value={filters.workType}
          onChange={(e) => setFilters({ workType: e.target.value as ContributionWorkType })}
          className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "10.5rem" }}
        >
          <option value="">Tüm çalışma türleri</option>
          {Object.entries(WORK_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>

        <select
          value={filters.impactLevel}
          onChange={(e) => setFilters({ impactLevel: e.target.value as ImpactLevel })}
          className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "9.5rem" }}
        >
          <option value="">Tüm etki seviyeleri</option>
          {Object.entries(IMPACT_LEVEL_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>

        <select
          value={filters.financialGainStatus}
          onChange={(e) => setFilters({ financialGainStatus: e.target.value as FinancialGainStatus })}
          className={searchInputClass} style={{ ...searchInputStyle, maxWidth: "11rem" }}
        >
          <option value="">Tüm maddi kazanç durumları</option>
          {Object.entries(FINANCIAL_STATUS_FILTER_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>

        {activeFilterCount > 0 && (
          <button
            onClick={() => { clearFilters(); setForemanName(""); setForemanQuery(""); }}
            className="ml-auto text-xs font-medium"
            style={{ color: "var(--accent)" }}
          >
            Filtreleri temizle ({activeFilterCount})
          </button>
        )}
      </div>

      <div className="flex items-center justify-between">
        <input
          type="search"
          placeholder="Başlık, açıklama veya formen adına göre ara..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={searchInputClass} style={searchInputStyle}
        />
        <div className="flex gap-1 rounded-md p-0.5" style={{ border: "1px solid var(--border-strong)" }}>
          <button
            onClick={() => setView2("card")}
            className="flex items-center gap-1 rounded px-2.5 py-1.5 text-xs font-medium"
            style={view === "card" ? { background: "var(--accent)", color: "white" } : { color: "var(--text-secondary)" }}
          >
            <LayoutGrid size={13} strokeWidth={2} />
            Kart
          </button>
          <button
            onClick={() => setView2("table")}
            className="flex items-center gap-1 rounded px-2.5 py-1.5 text-xs font-medium"
            style={view === "table" ? { background: "var(--accent)", color: "white" } : { color: "var(--text-secondary)" }}
          >
            <Table2 size={13} strokeWidth={2} />
            Tablo
          </button>
        </div>
      </div>

      {works.isLoading && <LoadingState />}
      {works.isError && <ErrorState />}
      {!works.isLoading && workItems.length === 0 && <EmptyState message="Seçilen filtrelerle eşleşen çalışma bulunamadı." />}

      {workItems.length > 0 && (
        <>
          {view === "card" ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {workItems.map((w) => <ContributionWorkCard key={w.id} work={w} />)}
            </div>
          ) : (
            <Card>
              <ContributionWorkTable items={workItems} sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
            </Card>
          )}
          <LoadMoreButton
            hasMore={!!works.hasNextPage}
            isFetchingNextPage={works.isFetchingNextPage}
            onLoadMore={() => works.fetchNextPage()}
            loadedCount={workItems.length}
            total={workTotal}
            itemLabel="çalışma"
          />
        </>
      )}

      {formOpen && <ContributionWorkForm onClose={() => setFormOpen(false)} />}
    </div>
  );
}
