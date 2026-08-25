import type { AnomalyDetail, AnomalyInvestigation } from "../../api/types";
import { AnomalyDotComparisonChart, type DotComparisonRow } from "../charts/AnomalyDotComparisonChart";
import { performanceDirection, PERFORMANCE_COLORS } from "../../lib/kpiDirection";
import { formatSignedUnitDiff } from "../../lib/anomalyMetrics";

export function BenchmarkComparison({ anomaly, investigation }: { anomaly: AnomalyDetail; investigation: AnomalyInvestigation }) {
  const a = anomaly;

  const rows: DotComparisonRow[] = [
    ...investigation.factoryComparison.map((f) => ({
      key: `factory-${f.code}`, label: f.code, value: f.value, emphasis: f.isAnomalyFactory,
    })),
    ...investigation.shiftComparison.map((s) => ({
      key: `shift-${s.shiftId}`, label: s.name, value: s.value, emphasis: s.isAnomalyShift,
    })),
  ];

  let diffLabel: string | null = null;
  let diffValue: number | null = null;
  if (a.shiftId) {
    const other = investigation.shiftComparison.find((s) => !s.isAnomalyShift && s.value != null);
    if (other && other.value != null) {
      diffLabel = `${other.name}ya göre fark`;
      diffValue = a.observedValue - other.value;
    }
  } else {
    const ownFactory = investigation.factoryComparison.find((f) => f.isAnomalyFactory && f.value != null);
    if (ownFactory && ownFactory.value != null) {
      diffLabel = "Fabrika ortalamasına göre fark";
      diffValue = a.observedValue - ownFactory.value;
    }
  }

  const diffDir = diffValue != null ? performanceDirection(a.kpiDefinition.desiredDirection, diffValue > 0) : "unknown";

  return (
    <div className="flex flex-col gap-4">
      <AnomalyDotComparisonChart rows={rows} target={investigation.comparisonTargetValue} unit={a.unit} kpiDefinition={a.kpiDefinition} />
      {diffLabel && diffValue != null && (
        <div className="flex items-center justify-between rounded-md p-3 text-[13px]" style={{ border: "1px solid var(--border)" }}>
          <span style={{ color: "var(--text-secondary)" }}>{diffLabel}</span>
          <span className="font-semibold tabular-nums" style={{ color: PERFORMANCE_COLORS[diffDir] }}>
            {formatSignedUnitDiff(diffValue, a.unit)}
          </span>
        </div>
      )}
    </div>
  );
}
