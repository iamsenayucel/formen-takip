import type { DowntimeBreakdown } from "../../api/types";

export function KpiBreakdownCard({ breakdown }: { breakdown: DowntimeBreakdown }) {
  const total = breakdown.totalDowntimeMinutes || 1;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
        <span>Toplam duruş: <strong style={{ color: "var(--text-primary)" }}>{breakdown.totalDowntimeMinutes} dk</strong></span>
        <span>Olay sayısı: <strong style={{ color: "var(--text-primary)" }}>{breakdown.totalDowntimeCount}</strong></span>
        <span>En uzun tekil olay: <strong style={{ color: "var(--text-primary)" }}>{breakdown.longestSingleEventMinutes} dk</strong></span>
      </div>
      <div className="flex flex-col gap-2">
        {breakdown.categories.map((c) => {
          const pct = (c.totalMinutes / total) * 100;
          return (
            <div key={c.category} className="flex items-center gap-3 text-[13px]">
              <span className="w-40 shrink-0 truncate" style={{ color: "var(--text-primary)" }}>{c.category}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ background: "var(--page-bg)" }}>
                <div className="h-full rounded-full" style={{ width: `${pct}%`, background: "var(--data-primary)" }} />
              </div>
              <span className="w-16 shrink-0 text-right tabular-nums" style={{ color: "var(--text-secondary)" }}>{c.totalMinutes} dk</span>
              <span className="w-12 shrink-0 text-right tabular-nums" style={{ color: "var(--text-muted)" }}>%{pct.toFixed(0)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
