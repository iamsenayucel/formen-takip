import { AlertTriangle, ArrowDown, CheckCircle2, Wrench } from "lucide-react";

interface Props {
  problem: string | null;
  solution: string | null;
  result: string | null;
}

const STAGES = [
  { key: "problem", title: "Tespit Edilen Problem", icon: AlertTriangle, color: "var(--status-negative)", bg: "var(--status-negative-bg)" },
  { key: "solution", title: "Uygulanan Çözüm", icon: Wrench, color: "var(--status-neutral)", bg: "var(--status-neutral-bg)" },
  { key: "result", title: "Elde Edilen Sonuç", icon: CheckCircle2, color: "var(--status-positive)", bg: "var(--status-positive-bg)" },
] as const;

export function ProblemSolutionResultFlow({ problem, solution, result }: Props) {
  const values: Record<string, string | null> = { problem, solution, result };
  const stages = STAGES.filter((s) => values[s.key]);
  if (stages.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {stages.map((stage, i) => {
        const Icon = stage.icon;
        return (
          <div key={stage.key}>
            <div className="rounded-lg p-4" style={{ border: "1px solid var(--border)", background: stage.bg }}>
              <div className="mb-1.5 flex items-center gap-2">
                <Icon size={16} strokeWidth={2} style={{ color: stage.color }} />
                <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: stage.color }}>
                  {stage.title}
                </span>
              </div>
              <p className="text-[13px] leading-relaxed" style={{ color: "var(--text-primary)" }}>
                {values[stage.key]}
              </p>
            </div>
            {i < stages.length - 1 && (
              <div className="flex justify-center py-1">
                <ArrowDown size={14} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
