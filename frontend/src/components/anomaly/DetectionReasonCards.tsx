import type { ReactNode } from "react";
import { CalendarClock, History, Target, Users } from "lucide-react";
import type { AnomalyDetail, AnomalyInvestigation } from "../../api/types";
import { changeWord, formatMetricValue, magnitudeWord, primaryDelta } from "../../lib/anomalyMetrics";
import { formatPct, performanceDirection, PERFORMANCE_COLORS } from "../../lib/kpiDirection";

function ReasonCard({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg p-3.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
        {icon}
        {title}
      </div>
      <div className="mt-1.5 text-[13px]" style={{ color: "var(--text-secondary)" }}>{children}</div>
    </div>
  );
}

function WorseDot() {
  return <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: "var(--status-negative)" }} />;
}

const Muted = ({ children }: { children: ReactNode }) => <span style={{ color: "var(--text-muted)" }}>{children}</span>;

export function DetectionReasonCards({
  anomaly, investigation, investigationLoading,
}: {
  anomaly: AnomalyDetail;
  investigation?: AnomalyInvestigation;
  investigationLoading: boolean;
}) {
  const a = anomaly;
  const higherIsBetter = a.kpiDefinition.desiredDirection === "high";

  let deviationBody: ReactNode = <Muted>Hedef bilgisi mevcut değil.</Muted>;
  if (a.targetValue != null) {
    const { pctDiff } = primaryDelta(a.observedValue, a.targetValue);
    if (pctDiff != null) {
      const dir = performanceDirection(a.kpiDefinition.desiredDirection, pctDiff > 0);
      deviationBody = (
        <span className="text-lg font-bold tabular-nums" style={{ color: PERFORMANCE_COLORS[dir] }}>
          Hedeften {formatPct(Math.abs(pctDiff), 1)} {magnitudeWord(pctDiff)}
        </span>
      );
    }
  }

  const hasPersistence = a.affectedDays != null && a.totalDays != null;

  const shiftEntries = investigation?.shiftComparison ?? [];
  const shiftValues = shiftEntries.map((s) => s.value).filter((v): v is number => v != null);
  const worstShiftValue = shiftValues.length > 1 ? (higherIsBetter ? Math.min(...shiftValues) : Math.max(...shiftValues)) : null;

  const prevMonth = investigation?.previousMonth;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <ReasonCard icon={<Target size={13} strokeWidth={2} />} title="Hedeften Sapma">
        {deviationBody}
      </ReasonCard>

      <ReasonCard icon={<CalendarClock size={13} strokeWidth={2} />} title="Sorunun Devamlılığı">
        {hasPersistence ? (
          <>Sorun son <strong style={{ color: "var(--text-primary)" }}>{a.totalDays} günün {a.affectedDays}'inde</strong> görüldü.</>
        ) : (
          <Muted>Devamlılık verisi mevcut değil.</Muted>
        )}
      </ReasonCard>

      <ReasonCard icon={<Users size={13} strokeWidth={2} />} title="Vardiya Karşılaştırması">
        {investigationLoading && <Muted>Yükleniyor…</Muted>}
        {!investigationLoading && shiftEntries.length === 0 && <Muted>Vardiya verisi mevcut değil.</Muted>}
        {!investigationLoading && shiftEntries.length > 0 && (
          <ul className="flex flex-col gap-1">
            {shiftEntries.map((s) => (
              <li key={s.shiftId} className="flex items-center gap-1.5">
                {s.value != null && worstShiftValue != null && s.value === worstShiftValue && <WorseDot />}
                <span
                  className="tabular-nums"
                  style={{
                    color: s.isAnomalyShift ? "var(--text-primary)" : "var(--text-secondary)",
                    fontWeight: s.isAnomalyShift ? 600 : 400,
                  }}
                >
                  {s.name}: {s.value != null ? formatMetricValue(s.value, a.unit) : "-"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </ReasonCard>

      <ReasonCard icon={<History size={13} strokeWidth={2} />} title="Önceki Ay">
        {investigationLoading && <Muted>Yükleniyor…</Muted>}
        {!investigationLoading && (!prevMonth?.available || prevMonth.value == null) && <Muted>Önceki ay verisi mevcut değil.</Muted>}
        {!investigationLoading && prevMonth?.available && prevMonth.value != null && (
          <div className="flex flex-col gap-0.5">
            <span>
              {prevMonth.label}: <strong style={{ color: "var(--text-primary)" }}>{formatMetricValue(prevMonth.value, a.unit)}</strong>
            </span>
            {prevMonth.changePercent != null && (
              <span
                className="font-semibold tabular-nums"
                style={{ color: PERFORMANCE_COLORS[performanceDirection(a.kpiDefinition.desiredDirection, prevMonth.changePercent > 0)] }}
              >
                {changeWord(prevMonth.changePercent)}: {formatPct(Math.abs(prevMonth.changePercent), 1)}
              </span>
            )}
          </div>
        )}
      </ReasonCard>
    </div>
  );
}
