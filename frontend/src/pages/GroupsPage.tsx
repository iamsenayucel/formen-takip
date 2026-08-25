import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilterBar } from "../components/FilterBar";
import { Card, EmptyState, ErrorState, LoadingState } from "../components/StateViews";
import { PageHeader } from "../components/PageHeader";
import { PerformanceLevelBadge } from "../components/PerformanceLevelBadge";
import { ReliabilityBadge } from "../components/ReliabilityBadge";
import { GroupBadge } from "../components/GroupBadge";
import { SortableTh } from "../components/table/SortableTh";
import { LoadMoreButton } from "../components/LoadMoreButton";
import { useChiefs } from "../api/hooks";
import { useFilters } from "../hooks/useFilters";
import { clickableRowProps } from "../lib/a11y";
import { rowHoverClass, rowStyle, searchInputClass, searchInputStyle, tableClass, tdClass, thClass, theadRowStyle, thStyle } from "../lib/tableStyles";

type SortField = "name" | "employee_number" | "plant" | "factory" | "foreman_count" | "score" | "level" | "reliability";

const DESC_FIRST: ReadonlySet<SortField> = new Set(["foreman_count", "score", "level", "reliability"]);

const COLUMNS: { field: SortField; label: string }[] = [
  { field: "name", label: "Şef" },
  { field: "employee_number", label: "Sicil No" },
  { field: "factory", label: "Fabrika" },
  { field: "plant", label: "Tesis" },
  { field: "foreman_count", label: "Formen Sayısı" },
  { field: "score", label: "Grup Puanı" },
  { field: "level", label: "Seviye" },
  { field: "reliability", label: "Veri Güvenilirliği" },
];

export function GroupsPage() {
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
    sort_by: sortBy,
    sort_dir: sortDir,
  };
  const chiefs = useChiefs(params);
  const items = chiefs.data?.pages.flatMap((p) => p.items) ?? [];
  const total = chiefs.data?.pages[0]?.pagination.total ?? null;

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Gruplar" />

      <FilterBar filters={filters} setFilters={setFilters} clearFilters={clearFilters} />

      <input
        type="search"
        placeholder="Şef adı, soyadı veya sicil no ara..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className={searchInputClass}
        style={searchInputStyle}
      />

      <Card>
        {chiefs.isLoading && <LoadingState />}
        {chiefs.isError && <ErrorState />}
        {!chiefs.isLoading && items.length === 0 && <EmptyState />}
        {items.length > 0 && (
          <div className="overflow-x-auto">
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>
                    Grup
                  </th>
                  {COLUMNS.map((col) => (
                    <SortableTh key={col.field} field={col.field} label={col.label} activeField={sortBy} direction={sortDir} onSort={handleSort} />
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((c) => (
                  <tr
                    key={c.id}
                    className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
                    style={rowStyle}
                    {...clickableRowProps(() => navigate(`/groups/${c.id}`), `${c.fullName} grubu detayına git`)}
                  >
                    <td className={tdClass}>
                      <GroupBadge code={c.code} />
                    </td>
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{c.fullName}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{c.employeeNumber}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{c.factory?.name ?? "-"}</td>
                    <td className={`${tdClass} whitespace-nowrap`} style={{ color: "var(--text-secondary)" }}>
                      {c.plants.length > 0 ? c.plants.map((p) => p.name).join(", ") : "-"}
                    </td>
                    <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-secondary)" }}>{c.foremanCount}</td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: "var(--text-primary)" }}>{c.totalScore.toFixed(1)}</td>
                    <td className={tdClass}>
                      <PerformanceLevelBadge level={c.level} />
                    </td>
                    <td className={tdClass}>
                      <ReliabilityBadge isReliable={c.isReliable} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <LoadMoreButton
              hasMore={!!chiefs.hasNextPage}
              isFetchingNextPage={chiefs.isFetchingNextPage}
              onLoadMore={() => chiefs.fetchNextPage()}
              loadedCount={items.length}
              total={total}
              itemLabel="grup"
            />
          </div>
        )}
      </Card>
    </div>
  );
}
