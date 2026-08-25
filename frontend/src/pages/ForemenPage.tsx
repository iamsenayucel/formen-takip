import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PageHeader } from "../components/PageHeader";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { SortableTh } from "../components/table/SortableTh";
import { LoadMoreButton } from "../components/LoadMoreButton";
import { useForemen } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { clickableRowProps } from "../lib/a11y";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tableClass, tdClass, theadRowStyle } from "../lib/tableStyles";

type SortField = "name" | "employee_number" | "plant" | "chief" | "score" | "level" | "reliability";

const DESC_FIRST: ReadonlySet<SortField> = new Set(["score", "level", "reliability"]);

const COLUMNS: { field: SortField; label: string }[] = [
  { field: "name", label: "Formen" },
  { field: "employee_number", label: "Sicil No" },
  { field: "plant", label: "Tesis" },
  { field: "chief", label: "Şef" },
  { field: "score", label: "Genel Puan" },
  { field: "level", label: "Seviye" },
  { field: "reliability", label: "Veri Güvenilirliği" },
];

export function ForemenPage() {
  const { filters, setFilters, clearFilters, asQueryParams } = useFilters();
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState<SortField>("name");
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

  const params = {
    ...asQueryParams,
    search: search || undefined,
    plant_id: filters.plantIds[0],
    chief_id: filters.chiefIds[0],
    shift_id: filters.shiftIds[0],
    sort_by: sortBy,
    sort_dir: sortDir,
  };
  const foremen = useForemen(params);
  const items = foremen.data?.pages.flatMap((p) => p.items) ?? [];
  const total = foremen.data?.pages[0]?.pagination.total ?? null;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Formenler" />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <input
        type="search"
        placeholder="Ad, soyad veya sicil no ara..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className={searchInputClass}
        style={searchInputStyle}
      />

      <Card>
        {foremen.isLoading && <LoadingState />}
        {foremen.isError && <ErrorState />}
        {!foremen.isLoading && items.length === 0 && <EmptyState />}
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
                {items.map((f) => (
                  <tr
                    key={f.id}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    style={rowStyle}
                    {...clickableRowProps(() => navigate(`/foremen/${f.id}`), `${f.fullName} profiline git`)}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.fullName}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employeeNumber}</td>
                    <td className={`${tdClass} whitespace-nowrap`} style={{ color: "var(--text-secondary)" }}>
                      {f.assignments.length ? f.assignments.map((a) => a.plant.name).join(", ") : "-"}
                    </td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                      {f.assignments[0]?.chief.name ?? "-"}
                    </td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>
                      {f.generalPerformanceScore.toFixed(1)}
                      {f.contributionBonus > 0 && (
                        <span className="ml-1 text-xs font-medium" style={{ color: "var(--status-positive)" }}>(+{f.contributionBonus})</span>
                      )}
                    </td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={f.level} />
                    </td>
                    <td className={tdClass}>
                      <ReliabilityBadge isReliable={f.isReliable} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <LoadMoreButton
              hasMore={!!foremen.hasNextPage}
              isFetchingNextPage={foremen.isFetchingNextPage}
              onLoadMore={() => foremen.fetchNextPage()}
              loadedCount={items.length}
              total={total}
              itemLabel="formen"
            />
          </div>
        )}
      </Card>
    </div>
  );
}
