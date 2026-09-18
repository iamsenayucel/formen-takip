import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { CalendarDays, CheckCircle2, ChevronLeft, Download, Factory, Pencil, Trash2 } from "lucide-react";
import { apiClient } from "../api/client";
import { useContributionWork, useDeleteContributionWork } from "../api/hooks";
import { Can } from "../components/Can";
import { Card, ErrorState, LoadingState } from "../components/StateViews";
import { BeforeAfterComparison } from "../components/BeforeAfterComparison";
import { ProblemSolutionResultFlow } from "../components/ProblemSolutionResultFlow";
import { ContributionWorkForm } from "../components/ContributionWorkForm";
import { useTheme } from "../context/ThemeContext";
import { STATUS_LABELS, workTypeColor, workTypeIcon, workTypeLabel } from "../lib/contributionTheme";
import { formatMoney } from "../lib/contributionCalc";

function initials(name: string): string {
  return name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
}

function GainCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      <span className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</span>
      <div className="mt-1.5 text-xl font-semibold" style={{ color: "var(--text-primary)" }}>{value}</div>
      {sub && <div className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>{sub}</div>}
    </div>
  );
}

export function ImprovementWorkDetailPage() {
  const { workId } = useParams<{ workId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const [editing, setEditing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const justPublished = (location.state as { justPublished?: boolean } | null)?.justPublished;

  const work = useContributionWork(workId);
  const deleteWork = useDeleteContributionWork();

  if (work.isLoading) return <LoadingState />;
  if (work.isError || !work.data) return <ErrorState message="Çalışma bulunamadı." />;

  const w = work.data;
  const Icon = workTypeIcon(w.workType);
  const accent = workTypeColor(w.workType, isDark);

  const handleDelete = () => {
    if (!window.confirm(`"${w.title}" çalışmasını kaldırmak istediğinize emin misiniz?`)) return;
    deleteWork.mutate(w.id, { onSuccess: () => navigate("/improvement-works") });
  };

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const resp = await apiClient.get(`/contribution-works/${w.id}/pdf`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([resp.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `${w.title}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={() => navigate("/improvement-works")}
        className="flex w-fit items-center gap-1 text-xs font-medium hover:underline"
        style={{ color: "var(--accent)" }}
      >
        <ChevronLeft size={13} strokeWidth={2} />
        Operational Impact+
      </button>

      {justPublished && (
        <div className="flex items-center gap-2 rounded-lg p-3 text-[13px] font-medium" style={{ background: "var(--status-positive-bg)", color: "var(--status-positive)" }}>
          <CheckCircle2 size={16} strokeWidth={2} />
          Çalışma başarıyla yayımlandı.
        </div>
      )}

      <div className="rounded-lg p-6" style={{ background: "var(--surface)", border: "1px solid var(--border)", borderTop: `3px solid ${accent}` }}>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide" style={{ backgroundColor: `${accent}14`, color: accent, border: `1px solid ${accent}33` }}>
              <Icon size={12} strokeWidth={2.25} />
              {workTypeLabel(w.workType)}
            </span>
            <span
              className="rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
              style={w.status === "published" ? { background: "var(--status-positive-bg)", color: "var(--status-positive)" } : { background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border-strong)" }}
            >
              {STATUS_LABELS[w.status]}
            </span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleDownloadPdf}
              disabled={downloading}
              className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
              style={{ border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }}
            >
              <Download size={13} strokeWidth={2} />
              {downloading ? "İndiriliyor..." : "PDF olarak indir"}
            </button>
            <Can permission="operational_impact.contribute">
              <button
                onClick={() => setEditing(true)}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white"
                style={{ background: "var(--accent)" }}
              >
                <Pencil size={13} strokeWidth={2} />
                Düzenle
              </button>
            </Can>
            <Can permission="operational_impact.contribute">
              <button
                onClick={handleDelete}
                disabled={deleteWork.isPending}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-50"
                style={{ border: "1px solid var(--border-strong)", color: "var(--text-secondary)" }}
              >
                <Trash2 size={13} strokeWidth={2} />
                Kaldır
              </button>
            </Can>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px]" style={{ color: "var(--text-muted)" }}>
          {w.plants.length > 0 && (
            <span className="flex items-center gap-1.5">
              <Factory size={14} strokeWidth={2} />
              {w.plants.map((p) => `${p.factoryCode} · ${p.name}`).join(", ")}
            </span>
          )}
          {w.workDate && (
            <span className="flex items-center gap-1.5">
              <CalendarDays size={14} strokeWidth={2} />
              {w.workDate}{w.workDateEnd ? ` — ${w.workDateEnd}` : ""}
            </span>
          )}
          <span>Kaydeden: {w.createdBy ?? "-"}</span>
        </div>

        {w.foremen.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {w.foremen.map((f) => (
              <span key={f.id} className="flex items-center gap-1.5 rounded-full py-1 pl-1 pr-3 text-xs font-medium" style={{ background: "var(--page-bg)", border: "1px solid var(--border)", color: "var(--text-primary)" }}>
                <span className="flex h-5 w-5 items-center justify-center rounded-full text-[9px] font-semibold" style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}>
                  {initials(f.name)}
                </span>
                {f.name}
              </span>
            ))}
          </div>
        )}

        {w.badges.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1.5">
            {w.badges.map((b) => (
              <span key={b} className="rounded-full px-2.5 py-1 text-xs font-medium" style={{ background: "var(--page-bg)", color: "var(--text-secondary)", border: "1px solid var(--border)" }}>{b}</span>
            ))}
          </div>
        )}

        {w.contributionScore !== null && (
          <div className="mt-5 rounded-lg p-4" style={{ background: "var(--status-positive-bg)", border: "1px solid var(--status-positive-border)" }}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold" style={{ color: "var(--status-positive)" }}>
                Operational Impact+ Puanı: {w.contributionScore}/5 — {w.contributionScoreLabel}
              </span>
            </div>
            <ul className="mt-3 flex flex-col gap-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
              {w.contributionScoreBreakdown
                .filter((c) => c.label !== "Toplam")
                .map((c) => (
                  <li key={c.label} className="flex items-center justify-between gap-3">
                    <span>{c.label} — {c.detail}</span>
                    <span className="shrink-0 font-medium tabular-nums" style={{ color: "var(--text-primary)" }}>+{c.points}</span>
                  </li>
                ))}
            </ul>
          </div>
        )}

        {(w.highlightedGain || w.beforeAfter) && (
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            {w.highlightedGain && (
              <div className="rounded-lg p-4" style={{ background: `${accent}0d`, border: `1px solid ${accent}33` }}>
                <div className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Öne Çıkan Kazanım</div>
                <div className="mt-1 text-3xl font-bold" style={{ color: accent }}>
                  {new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 }).format(w.highlightedGain.value)}
                  {w.highlightedGain.unit && <span className="ml-1.5 text-lg font-medium">{w.highlightedGain.unit}</span>}
                </div>
                <div className="mt-0.5 text-[13px]" style={{ color: "var(--text-secondary)" }}>{w.highlightedGain.label}</div>
              </div>
            )}
            {w.beforeAfter && (
              <div className="rounded-lg p-4" style={{ border: "1px solid var(--border)" }}>
                <BeforeAfterComparison data={w.beforeAfter} />
              </div>
            )}
          </div>
        )}
      </div>

      <ProblemSolutionResultFlow problem={w.problemDescription} solution={w.solutionDescription} result={w.resultDescription} />

      {w.detailedDescription && (
        <Card title="Detaylı Açıklama">
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>{w.detailedDescription}</p>
        </Card>
      )}

      {(w.financialGainStatus === "yes" || w.monthlyTotalSavingMinutes != null || w.gains.length > 0) && (
        <div>
          <h2 className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Ölçülebilir Kazanımlar</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {w.gainAmount != null && (
              <GainCard label="Maddi Kazanç" value={formatMoney(w.gainAmount, w.currency)} sub={w.gainPeriod ?? undefined} />
            )}
            {w.perOccurrenceSaving != null && (
              <GainCard label="İşlem Başına Zaman Kazancı" value={`${w.perOccurrenceSaving} ${w.durationUnit === "hour" ? "saat" : w.durationUnit === "second" ? "saniye" : "dakika"}`} />
            )}
            {w.monthlyTotalSavingMinutes != null && (
              <GainCard label="Aylık Toplam Zaman Kazancı" value={`${w.monthlyTotalSavingMinutes} dakika`} />
            )}
            {w.gains.map((g) => (
              <GainCard
                key={g.id}
                label={g.gainTypeLabel}
                value={g.changePercent != null ? `%${Math.abs(g.changePercent)}` : g.changeAmount != null ? `${g.changeAmount}` : "-"}
                sub={g.previousValue != null && g.nextValue != null ? `${g.previousValue} → ${g.nextValue} ${g.unit ?? ""}` : undefined}
              />
            ))}
          </div>
        </div>
      )}

      {editing && <ContributionWorkForm existing={w} onClose={() => setEditing(false)} />}
    </div>
  );
}
