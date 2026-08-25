import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PageHeader } from "../components/PageHeader";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { SortableTh } from "../components/table/SortableTh";
import { LoadMoreButton } from "../components/LoadMoreButton";
import { usePlants } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { clickableRowProps } from "../lib/a11y";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tableClass, tdClass, theadRowStyle } from "../lib/tableStyles";

type SortField = "sequence" | "name" | "factory" | "active_foreman_count" | "score" | "level";

const DESC_FIRST: ReadonlySet<SortField> = new Set(["active_foreman_count", "score", "level"]);

const COLUMNS: { field: SortField; label: string }[] = [
  { field: "sequence", label: "Tesis" },
  { field: "factory", label: "Fabrika" },
  { field: "active_foreman_count", label: "Aktif Formen" },
  { field: "score", label: "Toplam Puan" },
  { field: "level", label: "Seviye" },
];

export function PlantsPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("sequence");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const navigate = useNavigate();

  function handleSort(field: SortField) {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir(DESC_FIRST.has(field) ? "desc" : "asc");
    }
  }

  const plants = usePlants({
    ...asQueryParams,
    search: search || undefined,
    sort_by: sortBy,
    sort_dir: sortDir,
  });

  const items = plants.data?.pages.flatMap((p) => p.items) ?? [];
  const total = plants.data?.pages[0]?.pagination.total ?? null;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Tesisler" />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <input
        type="search"
        placeholder="Tesis adı veya kodu ara..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className={searchInputClass}
        style={searchInputStyle}
      />

      <Card>
        {plants.isLoading && <LoadingState />}
        {plants.isError && <ErrorState />}
        {!plants.isLoading && items.length === 0 && <EmptyState />}
        {items.length > 0 && (
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  {COLUMNS.map((col) => (
                    <SortableTh key={col.field} field={col.field} label={col.label} activeField={sortBy} direction={sortDir} onSort={handleSort} />
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr
                    key={p.id}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    style={rowStyle}
                    {...clickableRowProps(() => navigate(`/plants/${p.id}`), `${p.name} detayına git`)}
                  >
                    <td className={tdClass}>
                      <div className="font-medium" style={{ color: "var(--text-primary)" }}>{p.name}</div>
                      <div className="text-metadata" style={{ color: "var(--text-muted)" }}>{p.code}</div>
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{p.factory?.name ?? "-"}</td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{p.activeForemanCount}</td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>{p.totalScore.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={p.level} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <LoadMoreButton
              hasMore={!!plants.hasNextPage}
              isFetchingNextPage={plants.isFetchingNextPage}
              onLoadMore={() => plants.fetchNextPage()}
              loadedCount={items.length}
              total={total}
              itemLabel="tesis"
            />
          </div>
        )}
      </Card>
    </div>
  );
}
