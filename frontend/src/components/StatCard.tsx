import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { LucideIcon } from "lucide-react";

export type StatCardTone = "neutral" | "positive" | "attention" | "critical";

const TONE_BAR: Record<StatCardTone, string> = {
  neutral: "var(--primary)",
  positive: "var(--status-positive)",
  attention: "var(--status-neutral)",
  critical: "var(--status-negative)",
};

export function StatCard({
  label,
  value,
  sub,
  to,
  onClick,
  icon: Icon,
  tone = "neutral",
  premiumSurface = false,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  to?: string;
  onClick?: () => void;
  icon?: LucideIcon;
  tone?: StatCardTone;
  /** Dashboard "öne çıkan içgörü" kartları için opt-in semantic surface treatment (radial tint + fade top accent + icon container). Diğer StatCard kullanım yerlerini etkilemez. */
  premiumSurface?: boolean;
}) {
  const toneColor = TONE_BAR[tone];

  const content = (
    <div
      className="h-full min-w-0 rounded-lg p-[var(--space-card-padding-sm)] transition-colors"
      style={
        premiumSurface
          ? {
              background:
                `linear-gradient(to right, transparent, color-mix(in srgb, ${toneColor} 55%, transparent) 20%, color-mix(in srgb, ${toneColor} 55%, transparent) 80%, transparent) top / 100% 2px no-repeat, ` +
                `radial-gradient(circle at 92% 12%, color-mix(in srgb, ${toneColor} 6%, transparent), transparent 38%) no-repeat, ` +
                `var(--surface-raised)`,
              border: `1px solid color-mix(in srgb, ${toneColor} 22%, var(--border))`,
            }
          : {
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderTop: `2px solid ${toneColor}`,
            }
      }
    >
      <div className="flex items-center justify-between">
        <span className="text-label" style={{ color: "var(--primary)" }}>
          {label}
        </span>
        {Icon && premiumSurface && (
          <span
            className="flex shrink-0 items-center justify-center rounded-md"
            style={{
              width: "var(--icon-badge-size)",
              height: "var(--icon-badge-size)",
              background: `color-mix(in srgb, ${toneColor} 10%, transparent)`,
              border: `1px solid color-mix(in srgb, ${toneColor} 24%, transparent)`,
            }}
          >
            <Icon size={16} strokeWidth={1.75} style={{ color: toneColor }} />
          </span>
        )}
        {Icon && !premiumSurface && <Icon size={15} strokeWidth={1.75} style={{ color: "var(--text-muted)" }} />}
      </div>
      <div className="text-hero-metric mt-1.5" style={{ color: "var(--text-primary)" }}>
        {value}
      </div>
      {sub && (
        <div className="text-metadata mt-1" style={{ color: "var(--primary)" }}>
          {sub}
        </div>
      )}
    </div>
  );
  if (to) {
    return (
      <Link
        to={to}
        className={
          premiumSurface
            ? "block h-full transition-transform duration-150 hover:-translate-y-0.5"
            : "block h-full hover:[&>div]:border-[var(--border-strong)]"
        }
      >
        {content}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={
          premiumSurface
            ? "block h-full w-full text-left transition-transform duration-150 hover:-translate-y-0.5"
            : "block h-full w-full text-left hover:[&>div]:border-[var(--border-strong)]"
        }
      >
        {content}
      </button>
    );
  }

  return content;
}
