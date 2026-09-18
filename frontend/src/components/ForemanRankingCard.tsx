import { ArrowRight, Trophy, TrendingDown, TrendingUp } from "lucide-react";
import type { ForemanRankingItem, ForemanTrendRankingItem } from "../api/types";
import type { FilterState } from "../hooks/useFilters";
import { periodLabel, scopeLabel } from "../lib/filterLabels";
import { LoadingState, EmptyState } from "./StateViews";

const RANK_TINTS = [
  { background: "var(--status-neutral-bg)", color: "var(--status-neutral)", border: "var(--status-neutral-border)" },
  { background: "var(--status-unknown-bg)", color: "var(--status-unknown)", border: "var(--status-unknown-border)" },
  { background: "var(--status-neutral-bg)", color: "var(--status-neutral)", border: "var(--status-neutral-border)" },
];

function scoreOf(item: ForemanRankingItem | ForemanTrendRankingItem): number {
  return "generalPerformanceScore" in item ? item.generalPerformanceScore : item.operationalScore;
}

export function ForemanScoreRow({
  id,
  name,
  score,
  rank,
  color,
  showRankTint,
  onNavigate,
  delta,
}: {
  id: string;
  name: string;
  score: number;
  rank: number;
  color: string;
  showRankTint: boolean;
  onNavigate: (id: string) => void;
  delta?: number;
}) {
  const barPct = Math.max(4, Math.min(100, score));
  const tint = showRankTint ? RANK_TINTS[rank - 1] : null;
  // Literal hex burada zorunlu: aşağıda `${deltaColor}1a` gibi hex-alfa
  // birleştirmesiyle kullanılıyor, CSS custom property bu şekilde geçerli olmaz.
  // Değerler merkezi status paletiyle (--status-positive / --status-negative) eşleşir.
  const deltaColor = delta !== undefined ? (delta >= 0 ? "#15803d" : "#e90128") : null;

  return (
    <button
      onClick={() => onNavigate(id)}
      className="group flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-all duration-150 hover:-translate-y-0.5 hover:bg-[var(--page-bg)] hover:shadow-sm max-[1439px]:gap-1.5 max-[1439px]:px-1.5 max-[1439px]:py-1"
      style={{ border: "1px solid transparent" }}
    >
      <span
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold tabular-nums"
        style={
          tint
            ? { background: tint.background, color: tint.color, border: `1px solid ${tint.border}` }
            : { background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border)" }
        }
      >
        {rank}
      </span>

      <span className="min-w-0 flex-1">
        <span
          className="block truncate text-[13px] font-medium group-hover:underline max-[1439px]:text-xs"
          style={{ color: "var(--text-primary)" }}
        >
          {name}
        </span>
        <span className="mt-1 block h-1 w-full overflow-hidden rounded-full" style={{ background: "var(--border)" }}>
          <span className="block h-full rounded-full" style={{ width: `${barPct}%`, background: color }} />
        </span>
      </span>

      <span
        className="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold tabular-nums"
        style={{ background: `${color}1a`, color, border: `1px solid ${color}40` }}
      >
        {score.toFixed(1)}
      </span>
      {deltaColor && (
        <span
          className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums"
          style={{ background: `${deltaColor}1a`, color: deltaColor, border: `1px solid ${deltaColor}40` }}
        >
          {delta! >= 0 ? "+" : ""}{delta!.toFixed(1)}
        </span>
      )}
    </button>
  );
}

function RankingSection({
  title,
  accent,
  icon: Icon,
  items,
  isLoading,
  highlightRanks,
  onNavigate,
  showDelta,
}: {
  title: string;
  accent: string;
  icon: typeof Trophy;
  items: (ForemanRankingItem | ForemanTrendRankingItem)[] | undefined;
  isLoading: boolean;
  highlightRanks: boolean;
  onNavigate: (id: string) => void;
  showDelta?: boolean;
}) {
  return (
    <div
      className="min-w-0 rounded-lg p-[var(--space-compact-padding)]"
      style={{ background: `${accent}0d`, border: `1px solid ${accent}26` }}
    >
      <div className="mb-2 flex items-center gap-1.5 px-1">
        <Icon size={13} strokeWidth={2.25} style={{ color: accent }} />
        <p className="text-label" style={{ color: accent }}>
          {title}
        </p>
      </div>
      <div className="flex flex-col gap-0.5">
        {isLoading && <LoadingState />}
        {!isLoading && (!items || items.length === 0) && <EmptyState message="Veri yok" />}
        {items?.map((item, i) => (
          <ForemanScoreRow
            key={item.foremanId}
            id={item.foremanId}
            name={item.fullName}
            score={scoreOf(item)}
            rank={i + 1}
            color={item.level.color}
            showRankTint={highlightRanks}
            onNavigate={onNavigate}
            delta={showDelta && "delta" in item ? item.delta : undefined}
          />
        ))}
      </div>
    </div>
  );
}

export function ForemanRankingCard({
  filters,
  topItems,
  topLoading,
  bottomItems,
  bottomLoading,
  improvingItems,
  improvingLoading,
  decliningItems,
  decliningLoading,
  onNavigateForeman,
  onViewAll,
}: {
  filters: FilterState;
  topItems: ForemanRankingItem[] | undefined;
  topLoading: boolean;
  bottomItems: ForemanRankingItem[] | undefined;
  bottomLoading: boolean;
  improvingItems?: ForemanTrendRankingItem[];
  improvingLoading?: boolean;
  decliningItems?: ForemanTrendRankingItem[];
  decliningLoading?: boolean;
  onNavigateForeman: (id: string) => void;
  onViewAll: () => void;
}) {
  return (
    <div
      className="min-w-0 rounded-lg p-[var(--space-card-padding)]"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div className="mb-[var(--space-card-header-gap)] flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-card-title" style={{ color: "var(--text-primary)" }}>
            Formen Performans Sıralaması
          </h3>
          <p className="text-metadata mt-0.5" style={{ color: "var(--text-muted)" }}>
            Seçili dönemin genel KPI puanlarına göre sıralama
          </p>
        </div>
        <span
          className="text-metadata shrink-0 rounded-full px-2.5 py-1"
          style={{ background: "var(--page-bg)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
        >
          {periodLabel(filters)} • {scopeLabel(filters)}
        </span>
      </div>

      {/* 4 kart mümkün olduğunca uzun süre yan yana kalır: xl(1280) yerine 1150px'te
          geçilir çünkü card içi padding/font compact katmanda zaten küçülmüş durumda.
          sm: yerine min-[640px]: kullanılır — Tailwind v4 arbitrary min-[Npx]
          variant'ları isimli breakpoint'lerden ayrı bir CSS bloğunda üretilir; ikisini
          aynı property'de karıştırmak cascade sırasını bozar (bkz. ExecutiveHero'daki not). */}
      <div className="grid grid-cols-1 gap-[var(--space-card-gap)] min-[640px]:grid-cols-2 min-[1150px]:grid-cols-4">
        <RankingSection
          title="En Yüksek Performans"
          accent="#15803d"
          icon={Trophy}
          items={topItems}
          isLoading={topLoading}
          highlightRanks
          onNavigate={onNavigateForeman}
        />
        <RankingSection
          title="Gelişim Alanı"
          accent="#ca8a04"
          icon={TrendingDown}
          items={bottomItems}
          isLoading={bottomLoading}
          highlightRanks={false}
          onNavigate={onNavigateForeman}
        />
        <RankingSection
          title="Gelişim Gösteren Formenler"
          accent="#15803d"
          icon={TrendingUp}
          items={improvingItems}
          isLoading={!!improvingLoading}
          highlightRanks={false}
          onNavigate={onNavigateForeman}
          showDelta
        />
        <RankingSection
          title="En Fazla Performans Kaybı"
          accent="#e90128"
          icon={TrendingDown}
          items={decliningItems}
          isLoading={!!decliningLoading}
          highlightRanks={false}
          onNavigate={onNavigateForeman}
          showDelta
        />
      </div>

      <button
        onClick={onViewAll}
        className="group mt-4 inline-flex w-full items-center justify-center gap-1.5 rounded-md py-2 text-[13px] font-medium transition-colors hover:bg-[var(--page-bg)]"
        style={{ border: "1px solid var(--border)", color: "var(--primary)" }}
      >
        Tüm formen sıralamasını görüntüle
        <ArrowRight size={14} strokeWidth={2} className="transition-transform duration-150 group-hover:translate-x-0.5" />
      </button>
    </div>
  );
}
