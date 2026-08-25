import { Database } from "lucide-react";
import type { AnalysisPossibleCause } from "../../api/types";

const CONFIDENCE_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek" };
const CONFIDENCE_PALETTE: Record<string, { text: string; bg: string; border: string }> = {
  low: { text: "var(--status-unknown)", bg: "var(--status-unknown-bg)", border: "var(--status-unknown-border)" },
  medium: { text: "var(--status-info)", bg: "var(--status-info-bg)", border: "var(--status-info-border)" },
  high: { text: "var(--status-neutral)", bg: "var(--status-neutral-bg)", border: "var(--status-neutral-border)" },
};

export function RootCauseHypothesisCard({ cause, toolLabels }: { cause: AnalysisPossibleCause; toolLabels: Record<string, string> }) {
  const confidence = CONFIDENCE_PALETTE[cause.confidence] ?? CONFIDENCE_PALETTE.low;

  return (
    <div className="rounded-md p-3.5" style={{ border: "1px solid var(--border)" }}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
            style={{ background: "var(--status-neutral-bg)", color: "var(--status-neutral)", border: "1px solid var(--status-neutral-border)" }}
          >
            AI Hipotezi
          </span>
          <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{cause.cause}</span>
        </div>
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium"
          style={{ background: confidence.bg, color: confidence.text, border: `1px solid ${confidence.border}` }}
        >
          Olasılık: {CONFIDENCE_LABELS[cause.confidence] ?? cause.confidence}
        </span>
      </div>

      {cause.supportingEvidence.length > 0 && (
        <div className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          <span className="font-medium" style={{ color: "var(--text-primary)" }}>Destekleyen:</span>
          <ul className="mt-0.5 flex flex-col gap-0.5 pl-3">
            {cause.supportingEvidence.map((e, i) => <li key={i} className="list-disc">{e}</li>)}
          </ul>
        </div>
      )}

      {cause.contradictingEvidence.length > 0 && (
        <div className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
          <span className="font-medium" style={{ color: "var(--text-primary)" }}>Çelişen:</span>
          <ul className="mt-0.5 flex flex-col gap-0.5 pl-3">
            {cause.contradictingEvidence.map((e, i) => <li key={i} className="list-disc">{e}</li>)}
          </ul>
        </div>
      )}

      <p className="mt-2 text-xs" style={{ color: "var(--text-secondary)" }}>
        <span className="font-medium" style={{ color: "var(--text-primary)" }}>Kontrol edilmesi gereken:</span> {cause.verificationRequired}
      </p>
      <p className="mt-1 text-xs italic" style={{ color: "var(--text-muted)" }}>Durum: Doğrulanmayı bekliyor</p>

      {(cause.sourceRefs ?? []).length > 0 && (
        <span className="mt-1.5 flex w-fit items-center gap-1 text-[11px]" style={{ color: "var(--accent)" }}>
          <Database size={10} strokeWidth={2} />
          Kaynak: {cause.sourceRefs.map((r) => toolLabels[r.toolName] ?? r.toolName).join(", ")}
        </span>
      )}
    </div>
  );
}
