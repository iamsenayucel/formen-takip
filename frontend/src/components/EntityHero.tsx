import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import type { PerformanceLevel } from "../api/types";
import { PerformanceLevelBadge } from "./PerformanceLevelBadge";

export interface EntityHeroRankItem {
  label: string;
  value: ReactNode;
}

export interface EntityHeroLine {
  label: string;
  value: ReactNode;
  tone?: "neutral" | "positive";
}

export interface EntityHeroStatusNote {
  icon: LucideIcon;
  text: string;
  tone?: "neutral" | "attention";
}

// Tesis / Şef / Formen detay sayfalarındaki ortak "identity + ana skor" hero'su.
// ExecutiveHero ile aynı tipografi/renk diliyle (data-primary skor, status
// token'ları) — ama tek bir entity'nin kimlik bilgisini taşır.
export function EntityHero({
  eyebrow,
  title,
  subtitle,
  metaItems,
  contact,
  score,
  scoreMax = 100,
  scoreLabel = "Genel Performans Puanı",
  level,
  statusNote,
  rank,
  extraLines,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  metaItems?: (string | null | undefined)[];
  contact?: ReactNode;
  score: number | null;
  scoreMax?: number;
  scoreLabel?: string;
  level?: PerformanceLevel | null;
  statusNote?: EntityHeroStatusNote | null;
  rank?: EntityHeroRankItem[];
  extraLines?: EntityHeroLine[];
}) {
  const meta = (metaItems ?? []).filter((m): m is string => !!m);
  const StatusIcon = statusNote?.icon;

  return (
    <div className="rounded-lg p-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-label" style={{ color: "var(--text-muted)" }}>
            {eyebrow}
          </p>
          <h1 className="text-page-title mt-0.5" style={{ color: "var(--text-primary)" }}>
            {title}
          </h1>
          {subtitle && (
            <p className="text-metadata mt-0.5" style={{ color: "var(--text-muted)" }}>
              {subtitle}
            </p>
          )}

          {meta.length > 0 && (
            <div className="text-body mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-1" style={{ color: "var(--text-secondary)" }}>
              {meta.map((part, idx) => (
                <span key={idx} className="flex items-center gap-1.5">
                  {idx > 0 && <span style={{ color: "var(--text-muted)" }}>•</span>}
                  {part}
                </span>
              ))}
            </div>
          )}

          {contact && <div className="text-body mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">{contact}</div>}
        </div>

        <div className="shrink-0 text-right">
          <p className="text-label" style={{ color: "var(--text-muted)" }}>
            {scoreLabel}
          </p>
          <div className="mt-0.5 flex items-baseline justify-end gap-1">
            <span className="text-display-metric leading-none" style={{ color: "var(--data-primary)" }}>
              {score !== null && score !== undefined ? score.toFixed(1) : "—"}
            </span>
            <span className="text-body" style={{ color: "var(--text-muted)" }}>/ {scoreMax}</span>
          </div>
          {level && (
            <div className="mt-1.5 flex justify-end">
              <PerformanceLevelBadge level={level} />
            </div>
          )}
          {statusNote && StatusIcon && (
            <p
              className="text-metadata mt-1.5 flex items-center justify-end gap-1 font-medium"
              style={{ color: statusNote.tone === "attention" ? "var(--status-neutral)" : "var(--text-muted)" }}
            >
              <StatusIcon size={12} strokeWidth={2} />
              {statusNote.text}
            </p>
          )}

          {extraLines && extraLines.length > 0 && (
            <div
              className="text-body mt-2.5 flex flex-col items-end gap-0.5 pt-2"
              style={{ borderTop: "1px solid var(--border)", color: "var(--text-secondary)" }}
            >
              {extraLines.map((line, idx) => (
                <span key={idx}>
                  {line.label}:{" "}
                  <span
                    className="font-semibold tabular-nums"
                    style={{ color: line.tone === "positive" ? "var(--status-positive)" : "var(--text-primary)" }}
                  >
                    {line.value}
                  </span>
                </span>
              ))}
            </div>
          )}

          {rank && rank.length > 0 && (
            <div className="mt-2 flex flex-wrap justify-end gap-1.5">
              {rank.map((r, idx) => (
                <span
                  key={idx}
                  className="text-metadata inline-flex items-center gap-1 rounded-full px-2 py-0.5"
                  style={{ background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
                >
                  {r.label} {r.value}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
