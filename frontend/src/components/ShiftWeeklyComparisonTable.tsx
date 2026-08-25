import type { ShiftAnomalyForemanStat, ShiftWeeklyComparisonPoint, ShiftWeeklyForemanPoint } from "../api/types";
import { thClass, thStyle, theadRowStyle, tdClass, rowStyle, tableClass } from "../lib/tableStyles";

function ForemanCell({ point, unit, decimalPlaces }: { point: ShiftWeeklyForemanPoint; unit: string; decimalPlaces: number }) {
  if (point.assigned && point.value !== null) {
    return (
      <td className={`${tdClass} tabular-nums`}>
        <span className="font-semibold" style={{ color: "var(--text-primary)" }}>
          {point.value.toFixed(decimalPlaces)} {unit}
        </span>
        <span className="ml-1.5 text-[11px]" style={{ color: "var(--text-muted)" }}>
          {point.dayCount} gün
        </span>
      </td>
    );
  }
  if (point.assigned && !point.hasSufficientData) {
    return (
      <td className={tdClass}>
        <span className="text-[12px]" style={{ color: "var(--text-muted)" }}>Veri yetersiz</span>
      </td>
    );
  }
  return (
    <td className={tdClass}>
      <span style={{ color: "var(--text-muted)" }}>—</span>
    </td>
  );
}

function dutyLabel(point: ShiftWeeklyForemanPoint, name: string): string | null {
  if (!point.assigned) return null;
  return point.shiftName ? `${name} (${point.shiftName})` : name;
}

export function ShiftWeeklyComparisonTable({
  points, better, worse, unit, decimalPlaces = 1,
}: {
  points: ShiftWeeklyComparisonPoint[];
  better: ShiftAnomalyForemanStat;
  worse: ShiftAnomalyForemanStat;
  unit: string;
  decimalPlaces?: number;
}) {
  const sorted = [...points].sort((a, b) => a.weekIndex - b.weekIndex);

  return (
    <div className="overflow-x-auto rounded-md" style={{ border: "1px solid var(--border)" }}>
      <table className={tableClass}>
        <thead>
          <tr style={theadRowStyle}>
            <th className={thClass} style={thStyle}>Hafta</th>
            <th className={thClass} style={thStyle}>{worse.name}</th>
            <th className={thClass} style={thStyle}>{better.name}</th>
            <th className={thClass} style={thStyle}>Görev Durumu</th>
            <th className={thClass} style={thStyle}>Fark</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((p) => {
            const dutyNames = [dutyLabel(p.worse, worse.name), dutyLabel(p.better, better.name)].filter(Boolean);
            const diff =
              p.better.value !== null && p.worse.value !== null ? Math.abs(p.better.value - p.worse.value) : null;
            return (
              <tr key={p.weekIndex} style={rowStyle}>
                <td className={tdClass} style={{ color: "var(--text-secondary)" }}>{p.weekLabel}</td>
                <ForemanCell point={p.worse} unit={unit} decimalPlaces={decimalPlaces} />
                <ForemanCell point={p.better} unit={unit} decimalPlaces={decimalPlaces} />
                <td className={tdClass} style={{ color: "var(--text-secondary)" }}>
                  {dutyNames.length > 0 ? `${dutyNames.join(" · ")} görevli` : "Kayıt yok"}
                </td>
                <td className={`${tdClass} tabular-nums`} style={{ color: "var(--text-primary)" }}>
                  {diff !== null ? `${diff.toFixed(decimalPlaces)} ${unit}` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
