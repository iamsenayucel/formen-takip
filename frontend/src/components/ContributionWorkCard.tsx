import type { MouseEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CalendarDays, Factory, Trash2 } from "lucide-react";
import type { ContributionWorkItem } from "../api/types";
import { useDeleteContributionWork } from "../api/hooks";
import { useTheme } from "../context/ThemeContext";
import { workTypeColor, workTypeIcon, workTypeLabel } from "../lib/contributionTheme";
import { BeforeAfterComparison } from "./BeforeAfterComparison";

const MAX_BADGES = 3;

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function ContributionWorkCard({ work }: { work: ContributionWorkItem }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const Icon = workTypeIcon(work.workType);
  const accent = workTypeColor(work.workType, isDark);
  const isDraft = work.status === "draft";
  const deleteWork = useDeleteContributionWork();

  const handleDelete = (e: MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`"${work.title}" çalışmasını kaldırmak istediğinize emin misiniz?`)) return;
    deleteWork.mutate(work.id);
  };

  return (
    <Link
      to={`/improvement-works/${work.id}`}
      className="flex h-full flex-col rounded-lg p-4 transition-colors hover:border-[var(--border-strong)]"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderTop: `3px solid ${isDraft ? "var(--border-strong)" : accent}`,
        opacity: isDraft ? 0.85 : 1,
      }}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <span
          className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
          style={{ backgroundColor: `${accent}14`, color: accent, border: `1px solid ${accent}33` }}
        >
          <Icon size={12} strokeWidth={2.25} />
          {workTypeLabel(work.workType)}
        </span>
        {isDraft && (
          <span
            className="rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
            style={{ background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border-strong)" }}
          >
            Taslak
          </span>
        )}
      </div>

      <h3 className="text-[15px] font-semibold leading-snug" style={{ color: "var(--text-primary)" }}>
        {work.title}
      </h3>
      {work.summary && (
        <p className="mt-1 line-clamp-2 text-[13px]" style={{ color: "var(--text-secondary)" }}>
          {work.summary}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs" style={{ color: "var(--text-muted)" }}>
        {work.plants.length > 0 && (
          <span className="flex items-center gap-1">
            <Factory size={12} strokeWidth={2} />
            {work.plants.slice(0, 2).map((p) => `${p.factoryCode} · ${p.name}`).join(", ")}
            {work.plants.length > 2 && ` +${work.plants.length - 2}`}
          </span>
        )}
        {work.workDate && (
          <span className="flex items-center gap-1">
            <CalendarDays size={12} strokeWidth={2} />
            {work.workDate}
          </span>
        )}
      </div>

      {work.foremen.length > 0 && (
        <div className="mt-3 flex items-center gap-1.5">
          <div className="flex -space-x-1.5">
            {work.foremen.slice(0, 4).map((f) => (
              <span
                key={f.id}
                title={f.name}
                className="flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold"
                style={{ background: "var(--accent-subtle)", color: "var(--accent)", border: "1.5px solid var(--surface)" }}
              >
                {initials(f.name)}
              </span>
            ))}
          </div>
          <span className="truncate text-xs" style={{ color: "var(--text-secondary)" }}>
            {work.foremen.slice(0, 2).map((f) => f.name).join(", ")}
            {work.foremen.length > 2 && ` +${work.foremen.length - 2}`}
          </span>
        </div>
      )}

      {work.beforeAfter && (
        <div className="mt-3">
          <BeforeAfterComparison data={work.beforeAfter} compact />
        </div>
      )}

      {work.highlightedGain && (
        <div className="mt-3 rounded-md p-3" style={{ background: `${accent}0d` }}>
          <div className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            {work.highlightedGain.label}
          </div>
          <div className="mt-0.5 text-xl font-bold" style={{ color: accent }}>
            {new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(work.highlightedGain.value)}
            {work.highlightedGain.unit && <span className="ml-1 text-sm font-medium">{work.highlightedGain.unit}</span>}
          </div>
        </div>
      )}

      {work.badges.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {work.badges.slice(0, MAX_BADGES).map((b) => (
            <span
              key={b}
              className="rounded-full px-2 py-0.5 text-[10px] font-medium"
              style={{ background: "var(--page-bg)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}
            >
              {b}
            </span>
          ))}
        </div>
      )}

      <div className="mt-auto flex items-center justify-between pt-3">
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>{work.createdBy ?? "-"}</span>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleteWork.isPending}
            className="flex items-center gap-1 text-xs font-medium disabled:opacity-50"
            style={{ color: "var(--text-muted)" }}
          >
            <Trash2 size={12} strokeWidth={2.25} />
            Kaldır
          </button>
          <span className="flex items-center gap-1 text-xs font-medium" style={{ color: "var(--accent)" }}>
            Detaylar
            <ArrowRight size={12} strokeWidth={2.25} />
          </span>
        </div>
      </div>
    </Link>
  );
}
