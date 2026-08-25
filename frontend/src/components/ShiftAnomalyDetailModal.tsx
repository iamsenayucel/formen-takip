import { useState } from "react";
import { Activity, CalendarDays, ChevronRight, Lightbulb, Repeat, ScatterChart, X } from "lucide-react";
import type { ShiftAnomalyCard as ShiftAnomalyCardData } from "../api/types";
import { useShiftAnalysisDetail } from "../api/hooks";
import { LoadingState, ErrorState } from "./StateViews";
import { ShiftAnomalySeverityBadge } from "./ShiftAnomalyCard";
import { ShiftPeriodAverageChart } from "./charts/ShiftPeriodAverageChart";
import { ShiftRotationTrendChart } from "./charts/ShiftRotationTrendChart";
import { ShiftWeeklyComparisonTable } from "./ShiftWeeklyComparisonTable";
import { categoricalColor, dataTargetColor } from "../lib/chartColors";
import { useTheme } from "../context/ThemeContext";
import { useModalA11y } from "../hooks/useModalA11y";

const SEVERITY_SENTENCE: Record<ShiftAnomalyCardData["severity"], string> = {
  high: "yüksek",
  medium: "orta düzeyde",
};

function SectionTitle({ icon: Icon, children }: { icon: typeof ScatterChart; children: React.ReactNode }) {
  return (
    <h4 className="mb-2 flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
      <Icon size={13} strokeWidth={2.25} />
      {children}
    </h4>
  );
}

function ForemanSummaryCard({
  name, average, unit, decimalPlaces, days, weeks, isBetter, accent,
}: {
  name: string;
  average: number;
  unit: string;
  decimalPlaces: number;
  days: number;
  weeks: number;
  isBetter: boolean;
  accent: string;
}) {
  return (
    <div className="flex flex-1 flex-col gap-1 rounded-lg p-3.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: accent }} />
        <p className="truncate text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>{name}</p>
      </div>
      <p className="text-hero-metric tabular-nums" style={{ color: "var(--text-primary)" }}>
        {average.toFixed(decimalPlaces)} <span className="text-[13px] font-medium" style={{ color: "var(--text-muted)" }}>{unit}</span>
      </p>
      <p className="text-metadata" style={{ color: "var(--text-muted)" }}>Dönem Ortalaması · {days} gün / {weeks} hafta</p>
      {isBetter && (
        <span className="mt-0.5 inline-flex w-fit items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)", border: "1px solid var(--border-strong)" }}>
          Daha iyi performans
        </span>
      )}
    </div>
  );
}

export function ShiftAnomalyDetailModal({ card, onClose }: { card: ShiftAnomalyCardData; onClose: () => void }) {
  const { theme } = useTheme();
  const isDark = theme === "dark";
  const [activeKpiId, setActiveKpiId] = useState(card.kpiId);
  const detail = useShiftAnalysisDetail({ plant_id: card.plantId, shift_id: card.shiftId, kpi_id: activeKpiId });
  const containerRef = useModalA11y(onClose);
  const d = detail.data;
  const header = d ?? card;
  const decimalPlaces = header.kpiDecimalPlaces;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="shift-anomaly-modal-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-lg shadow-xl focus:outline-none"
        style={{ background: "var(--surface)" }}
      >
        <div className="shrink-0 border-b p-5 pb-4" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <ShiftAnomalySeverityBadge severity={header.severity} />
              <h3 id="shift-anomaly-modal-title" className="mt-2 text-[19px] font-bold leading-snug" style={{ color: "var(--text-primary)" }}>
                {header.worse.name} <span style={{ color: "var(--text-muted)" }}>↔</span> {header.better.name}
              </h3>
              <p className="mt-0.5 text-[13px] font-medium" style={{ color: "var(--text-secondary)" }}>
                {header.kpiName} · {header.shiftName}
              </p>
              <p className="mt-1 text-metadata" style={{ color: "var(--text-muted)" }}>
                {header.factoryCode} · {header.plantName} · {header.period.label}
              </p>
              <p className="mt-2 text-[13px]" style={{ color: "var(--text-primary)" }}>
                Aynı tesis ve vardiyada görev yapan iki formen arasında {SEVERITY_SENTENCE[header.severity]} bir performans farkı tespit edildi.
              </p>
            </div>
            <button type="button" onClick={onClose} aria-label="Kapat" className="shrink-0" style={{ color: "var(--text-muted)" }}>
              <X size={18} strokeWidth={2} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {detail.isLoading && <LoadingState label="Detay yükleniyor..." />}
          {detail.isError && <ErrorState message="Detay verisi yüklenemedi." />}

          {d && (
            <div className="flex flex-col gap-5">
              <section>
                <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
                  <ForemanSummaryCard
                    name={d.worse.name} average={d.worse.avgActual} unit={d.kpiUnit} decimalPlaces={decimalPlaces}
                    days={d.worse.recordCount} weeks={d.worse.weekCount} isBetter={false} accent={categoricalColor(0, isDark)}
                  />
                  <div className="flex shrink-0 flex-col items-center gap-1 px-2 py-1 sm:w-40">
                    <p className="text-hero-metric tabular-nums" style={{ color: "var(--text-primary)" }}>
                      {d.absDiff.toFixed(decimalPlaces)} <span className="text-[13px] font-medium" style={{ color: "var(--text-muted)" }}>{d.kpiUnit}</span>
                    </p>
                    <p className="text-metadata" style={{ color: "var(--text-muted)" }}>fark · %{d.pctDiff.toFixed(1)}</p>
                    <p className="mt-1 text-[11px] font-medium" style={{ color: "var(--text-secondary)" }}>
                      Hedef: {d.referenceTarget.toFixed(decimalPlaces)} {d.kpiUnit}
                    </p>
                  </div>
                  <ForemanSummaryCard
                    name={d.better.name} average={d.better.avgActual} unit={d.kpiUnit} decimalPlaces={decimalPlaces}
                    days={d.better.recordCount} weeks={d.better.weekCount} isBetter accent={categoricalColor(1, isDark)}
                  />
                </div>
              </section>

              <section>
                <SectionTitle icon={ScatterChart}>Vardiya Ortalaması Karşılaştırması</SectionTitle>
                <div className="rounded-md p-3" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
                  <ShiftPeriodAverageChart better={d.better} worse={d.worse} target={d.referenceTarget} unit={d.kpiUnit} decimalPlaces={decimalPlaces} />
                </div>
                <p className="mt-1.5 text-metadata" style={{ color: "var(--text-muted)" }}>
                  Aynı tesis ve vardiyada, farklı haftalarda görev yapan formenlerin dönem ortalamaları karşılaştırılmaktadır.
                </p>
              </section>

              <section>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <SectionTitle icon={Activity}>Haftalık Karşılaştırma</SectionTitle>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1" style={{ color: "var(--text-muted)" }}>
                    <span className="flex items-center gap-1.5 text-[11px]">
                      <span className="h-2 w-2 rounded-full" style={{ background: categoricalColor(0, isDark) }} />{d.worse.name}
                    </span>
                    <span className="flex items-center gap-1.5 text-[11px]">
                      <span className="h-2 w-2 rounded-full" style={{ background: categoricalColor(1, isDark) }} />{d.better.name}
                    </span>
                    <span className="flex items-center gap-1.5 text-[11px]">
                      <span className="inline-block h-0.5 w-3.5" style={{ background: dataTargetColor() }} />Hedef
                    </span>
                  </div>
                </div>
                <div className="rounded-md p-3" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
                  <ShiftRotationTrendChart
                    points={d.weeklyComparison} better={d.better} worse={d.worse} shiftName={d.shiftName}
                    target={d.referenceTarget} unit={d.kpiUnit} decimalPlaces={decimalPlaces}
                  />
                </div>
                <p className="mt-1.5 text-metadata" style={{ color: "var(--text-muted)" }}>
                  Her hafta, her formenin o hafta fiilen görev yaptığı vardiyadaki performansı gösterilir — böylece aynı haftada iki formenin gösterdiği performans karşılaştırılabilir.
                </p>
              </section>

              <section>
                <SectionTitle icon={CalendarDays}>Haftalık Rotasyon ve Değerler</SectionTitle>
                <ShiftWeeklyComparisonTable points={d.weeklyComparison} better={d.better} worse={d.worse} unit={d.kpiUnit} decimalPlaces={decimalPlaces} />
              </section>

              <section>
                <SectionTitle icon={Repeat}>Diğer KPI'larda Fark</SectionTitle>
                <p className="mb-2 -mt-1 text-metadata" style={{ color: "var(--text-muted)" }}>
                  Aynı iki formen arasındaki diğer önemli KPI farklılıkları
                </p>
                {d.crossKpiSignals.length === 0 && (
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    Bu formen çifti arasında diğer KPI'larda anlamlı bir fark tespit edilmedi.
                  </p>
                )}
                {d.crossKpiSignals.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    {d.crossKpiSignals.map((s) => (
                      <button
                        key={s.kpiId}
                        type="button"
                        onClick={() => setActiveKpiId(s.kpiId)}
                        className="group flex items-center justify-between rounded-md px-3 py-2 text-left text-[13px] transition-colors hover:bg-[var(--surface-highlight)]"
                        style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}
                      >
                        <span style={{ color: "var(--text-primary)" }}>{s.kpiName}</span>
                        <span className="flex items-center gap-2">
                          <span className="tabular-nums font-medium" style={{ color: "var(--text-secondary)" }}>%{s.pctDiff.toFixed(1)} fark</span>
                          <ShiftAnomalySeverityBadge severity={s.severity} />
                          <ChevronRight size={14} strokeWidth={2} className="transition-transform group-hover:translate-x-0.5" style={{ color: "var(--text-muted)" }} />
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </section>

              <section className="rounded-md p-3.5" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
                <SectionTitle icon={Lightbulb}>Sistem Yorumu</SectionTitle>
                <p className="text-[13px] font-semibold leading-relaxed" style={{ color: "var(--text-primary)" }}>
                  {d.patternHeadline}
                </p>
                <p className="mt-1 text-[13px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                  {d.patternDetail}
                </p>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
