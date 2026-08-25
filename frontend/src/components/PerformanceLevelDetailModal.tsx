import { AlertTriangle, CheckCircle2, Circle, Star, TrendingDown, X } from "lucide-react";
import type { DistributionItem } from "../api/types";
import { useForemen } from "../api/hooks";
import { LoadingState, ErrorState, EmptyState } from "./StateViews";
import { LoadMoreButton } from "./LoadMoreButton";
import { thClass, thStyle, theadRowStyle, tdClass, rowStyle, rowHoverClass, tableClass } from "../lib/tableStyles";

const ICONS: Record<string, typeof Circle> = {
  "check-circle": CheckCircle2,
  "trending-down": TrendingDown,
  "alert-triangle": AlertTriangle,
  star: Star,
};

type Params = Record<string, string | number | undefined>;

export function PerformanceLevelDetailModal({
  level,
  filterParams,
  queryOverride,
  onClose,
  onNavigateForeman,
}: {
  level: DistributionItem;
  filterParams: Params;
  /** Formen sorgusuna eklenecek ek/alternatif parametreler (örn. `{ outstanding: "true" }`).
   * Verilmezse varsayılan `{ level: level.name }` filtresi kullanılır. */
  queryOverride?: Params;
  onClose: () => void;
  onNavigateForeman: (id: string) => void;
}) {
  const pageSize = 20;
  const Icon = ICONS[level.icon] ?? Circle;

  const foremen = useForemen({
    ...filterParams,
    ...(queryOverride ?? { level: level.name }),
    sort_by: "score",
    sort_dir: level.name === "Kritik" ? "asc" : "desc",
  }, pageSize);
  const items = foremen.data?.pages.flatMap((page) => page.items) ?? [];
  const total = foremen.data?.pages.at(-1)?.pagination.total;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg p-5 shadow-xl"
        style={{ background: "var(--surface)" }}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
              style={{ backgroundColor: `${level.color}14`, color: level.color, border: `1px solid ${level.color}33` }}
            >
              <Icon size={15} strokeWidth={2} />
            </span>
            <div>
              <h3 className="text-[15px] font-semibold leading-snug" style={{ color: "var(--text-primary)" }}>
                {level.name} Seviyesindeki Formenler
              </h3>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{level.description}</p>
            </div>
          </div>
          <button type="button" onClick={onClose} style={{ color: "var(--text-muted)" }}>
            <X size={18} strokeWidth={2} />
          </button>
        </div>

        {foremen.isLoading && <LoadingState />}
        {foremen.isError && <ErrorState />}
        {foremen.data && items.length === 0 && <EmptyState />}
        {items.length > 0 && (
          <div className="overflow-x-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
            <table className={tableClass}>
              <thead>
                <tr style={theadRowStyle}>
                  <th className={thClass} style={thStyle}>Formen</th>
                  <th className={thClass} style={thStyle}>Sicil No</th>
                  <th className={thClass} style={thStyle}>Tesis</th>
                  <th className={thClass} style={thStyle}>Puan</th>
                </tr>
              </thead>
              <tbody>
                {items.map((f) => (
                  <tr
                    key={f.id}
                    onClick={() => onNavigateForeman(f.id)}
                    className={`cursor-pointer ${rowHoverClass}`}
                    style={rowStyle}
                  >
                    <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{f.fullName}</td>
                    <td className={tdClass} style={{ color: "var(--text-muted)" }}>{f.employeeNumber}</td>
                    <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                      {f.assignments.length ? f.assignments.map((a) => a.plant.name).join(", ") : "-"}
                    </td>
                    <td className={`${tdClass} font-medium tabular-nums`} style={{ color: level.color }}>
                      <span className="inline-flex items-center gap-1">
                        {f.generalPerformanceScore.toFixed(1)}
                        {f.level.outstandingPerformance && (
                          <Star size={11} strokeWidth={2} fill="currentColor" style={{ color: "#d97706" }} aria-label="Üstün Performans" />
                        )}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="px-1 pb-1">
              <LoadMoreButton
                hasMore={!!foremen.hasNextPage}
                isFetchingNextPage={foremen.isFetchingNextPage}
                onLoadMore={() => void foremen.fetchNextPage()}
                loadedCount={items.length}
                total={total}
                itemLabel="formen"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
