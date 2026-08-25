import { useNavigate } from "react-router-dom";
import { Trash2 } from "lucide-react";
import type { ContributionWorkItem } from "../api/types";
import { useDeleteContributionWork } from "../api/hooks";
import { STATUS_LABELS, workTypeLabel } from "../lib/contributionTheme";
import { clickableRowProps } from "../lib/a11y";
import { SortableTh } from "./table/SortableTh";
import { rowHoverClass, rowStyle, tableClass, tdClass, theadRowStyle, thClass, thStyle } from "../lib/tableStyles";

export type ContributionSortField = "title" | "type" | "foreman" | "plant" | "date" | "gain" | "status";

const COLUMNS: { field: ContributionSortField; label: string }[] = [
  { field: "title", label: "Başlık" },
  { field: "type", label: "Tür" },
  { field: "foreman", label: "Formenler" },
  { field: "plant", label: "Fabrika / Tesis" },
  { field: "date", label: "Tarih" },
  { field: "gain", label: "Öne Çıkan Kazanım" },
  { field: "status", label: "Durum" },
];

function ContributionScoreBadge({ score, label }: { score: number | null; label: string | null }) {
  if (score === null) return <span style={{ color: "var(--text-muted)" }}>-</span>;
  return (
    <span
      title={label ?? undefined}
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-semibold tabular-nums"
      style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
    >
      {score}/5
    </span>
  );
}

interface Props {
  items: ContributionWorkItem[];
  sortBy: ContributionSortField;
  sortDir: "asc" | "desc";
  onSort: (field: ContributionSortField) => void;
}

export function ContributionWorkTable({ items, sortBy, sortDir, onSort }: Props) {
  const navigate = useNavigate();
  const deleteWork = useDeleteContributionWork();

  const handleDelete = (work: ContributionWorkItem) => {
    if (!window.confirm(`"${work.title}" çalışmasını kaldırmak istediğinize emin misiniz?`)) return;
    deleteWork.mutate(work.id);
  };

  return (
    <div className="overflow-x-auto">
      <table className={tableClass}>
        <thead>
          <tr style={theadRowStyle}>
            {COLUMNS.map((col) => (
              <SortableTh key={col.field} field={col.field} label={col.label} activeField={sortBy} direction={sortDir} onSort={onSort} />
            ))}
            <th className={thClass} style={thStyle}>Operational Impact+ Puanı</th>
            <th className={thClass} style={thStyle}></th>
          </tr>
        </thead>
        <tbody>
          {items.map((w) => (
            <tr
              key={w.id}
              className={`cursor-pointer ${rowHoverClass} focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--focus-ring)]/50`}
              style={rowStyle}
              {...clickableRowProps(() => navigate(`/improvement-works/${w.id}`), `${w.title} çalışmasını görüntüle`, { guardNestedInteractive: true })}
            >
              <td className={`${tdClass} font-medium`} style={{ color: "var(--text-primary)" }}>{w.title}</td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{workTypeLabel(w.workType)}</td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                {w.foremen.map((f) => f.name).join(", ") || "-"}
              </td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                {w.plants.length > 0
                  ? w.plants.slice(0, 2).map((p) => `${p.factoryCode} · ${p.name}`).join(", ") +
                    (w.plants.length > 2 ? ` +${w.plants.length - 2}` : "")
                  : "-"}
              </td>
              <td className={tdClass} style={{ color: "var(--text-muted)" }}>{w.workDate ?? "-"}</td>
              <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                {w.highlightedGain
                  ? `${new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(w.highlightedGain.value)}${w.highlightedGain.unit ? " " + w.highlightedGain.unit : ""}`
                  : "-"}
              </td>
              <td className={tdClass}>
                <span
                  className="rounded px-2 py-0.5 text-xs font-medium"
                  style={
                    w.status === "published"
                      ? { background: "var(--status-positive-bg)", color: "var(--status-positive)" }
                      : { background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border-strong)" }
                  }
                >
                  {STATUS_LABELS[w.status]}
                </span>
              </td>
              <td className={tdClass}>
                <ContributionScoreBadge score={w.contributionScore} label={w.contributionScoreLabel} />
              </td>
              <td className={tdClass}>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleDelete(w); }}
                  disabled={deleteWork.isPending}
                  className="flex items-center gap-1 text-xs font-medium disabled:opacity-50"
                  style={{ color: "var(--text-muted)" }}
                >
                  <Trash2 size={12} strokeWidth={2.25} />
                  Kaldır
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
