import { AlertTriangle, CheckCircle2, Circle, Star, TrendingDown } from "lucide-react";
import type { PerformanceLevel } from "../api/types";

const ICONS: Record<string, typeof Circle> = {
  "check-circle": CheckCircle2,
  "trending-down": TrendingDown,
  "alert-triangle": AlertTriangle,
};

export function resolveLevelIcon(icon: string): typeof Circle {
  return ICONS[icon] ?? Circle;
}

export function PerformanceLevelBadge({ level, showDescription = false }: { level: PerformanceLevel; showDescription?: boolean }) {
  const Icon = resolveLevelIcon(level.icon);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-xs font-medium"
        style={{ backgroundColor: `${level.color}14`, color: level.color, border: `1px solid ${level.color}33` }}
        title={showDescription ? level.description : undefined}
      >
        <Icon size={12} strokeWidth={2} aria-hidden="true" />
        {level.name}
      </span>
      {level.outstandingPerformance && <OutstandingPerformanceBadge />}
    </span>
  );
}

export function OutstandingPerformanceBadge() {
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: "#d9770614", color: "#d97706", border: "1px solid #d9770633" }}
      title="Genel performans puanı 105 ve üzerinde"
    >
      <Star size={11} strokeWidth={2} fill="currentColor" aria-hidden="true" />
      Üstün Performans
    </span>
  );
}
