import { formatScoreDelta, scoreDeltaColor } from "../lib/kpiFormat";

export function MetricDelta({
  value,
  decimals = 1,
  className = "",
}: {
  value: number | null | undefined;
  decimals?: number;
  className?: string;
}) {
  return (
    <span className={`tabular-nums ${className}`} style={{ color: scoreDeltaColor(value) }}>
      {formatScoreDelta(value, decimals)}
    </span>
  );
}
