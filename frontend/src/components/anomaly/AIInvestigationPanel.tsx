import {
  Bot, CheckCircle2, Database, Gauge, HelpCircle,
  ListChecks, RefreshCw, Search, ShieldAlert, Sparkles, Wrench,
} from "lucide-react";
import type { AnalysisMode, AnomalyAnalysisRecord, AnomalyDetail, AnomalyToolCallItem } from "../../api/types";
import { Card, EmptyState, ErrorState, LoadingState } from "../StateViews";
import { RootCauseHypothesisCard } from "./RootCauseHypothesisCard";
import { RecommendedActions } from "./RecommendedActions";

const TOOL_LABELS: Record<string, string> = {
  get_anomaly_details: "Tespit Detayları", get_kpi_history: "KPI Geçmişi",
  compare_shifts: "Vardiya Performansı Karşılaştırması", compare_plants: "Tesisler Arası Karşılaştırma",
  get_related_kpis: "İlişkili KPI Değişimleri", get_downtime_breakdown: "Duruş Nedenleri İncelemesi",
  get_maintenance_signals: "Bakım ve Arıza Sinyalleri", get_product_mix: "Ürün Dağılımı İncelemesi",
  get_changeover_records: "Ürün Değişim Kayıtları", get_shift_notes: "Vardiya Notları İncelemesi",
  find_similar_anomalies: "Benzer Geçmiş Tespitler",
};

const TOOL_CALLING_STAGES = [
  "Tespit inceleniyor", "Analiz planı hazırlanıyor", "Vardiya verileri karşılaştırılıyor",
  "KPI geçmişi kontrol ediliyor", "Duruş nedenleri inceleniyor", "Bakım sinyalleri araştırılıyor",
  "Ürün dağılımı değerlendiriliyor", "Geçmiş benzer tespitler kontrol ediliyor", "Aksiyon önerileri hazırlanıyor",
];

const MODE_OPTIONS: { value: AnalysisMode; label: string; description: string }[] = [
  { value: "single_context", label: "Hızlı Analiz", description: "Tüm bağlam tek seferde gönderilir" },
  { value: "tool_calling", label: "Derinlemesine Analiz", description: "Yapay zekâ gerektikçe araç çağırarak araştırır" },
];

const RISK_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek", critical: "Kritik" };
const PRIORITY_LABELS: Record<string, string> = { low: "Düşük", medium: "Orta", high: "Yüksek", critical: "Kritik" };

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--page-bg)", border: "1px solid var(--border)" }}>
      <p className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums" style={{ color: "var(--text-primary)" }}>{value}</p>
    </div>
  );
}

function ClassificationTag({ kind }: { kind: "verified" | "missing" }) {
  if (kind === "verified") {
    return (
      <span
        className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
        style={{ background: "var(--status-positive-bg)", color: "var(--status-positive)", border: "1px solid var(--status-positive-border)" }}
      >
        <CheckCircle2 size={10} strokeWidth={2} />
        Doğrulanmış Veri
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
      style={{ background: "var(--status-unknown-bg)", color: "var(--status-unknown)", border: "1px solid var(--status-unknown-border)" }}
    >
      <HelpCircle size={10} strokeWidth={2} />
      Eksik Veri
    </span>
  );
}

export function AIInvestigationPanel({
  anomaly, isBusy, selectedMode, onSelectMode, onRunAnalysis, actionError,
  toolCallsData, toolCallsLoading, toolCallsError, stepsOpen, onToggleSteps,
}: {
  anomaly: AnomalyDetail;
  isBusy: boolean;
  selectedMode: AnalysisMode;
  onSelectMode: (m: AnalysisMode) => void;
  onRunAnalysis: (endpoint: "analyze" | "reanalyze") => void;
  actionError: string | null;
  toolCallsData: AnomalyToolCallItem[] | undefined;
  toolCallsLoading: boolean;
  toolCallsError: boolean;
  stepsOpen: boolean;
  onToggleSteps: () => void;
}) {
  const latest: AnomalyAnalysisRecord | null = anomaly.latestAnalysis;
  const result = latest?.result;

  return (
    <>
      <Card
        title="Kök Neden ve Aksiyon Analizi"
        action={
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1 rounded-md p-0.5" style={{ border: "1px solid var(--border-strong)" }}>
              {MODE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  disabled={isBusy}
                  title={o.description}
                  onClick={() => onSelectMode(o.value)}
                  className="rounded px-2 py-1 text-[11px] font-medium transition-colors disabled:opacity-60"
                  style={selectedMode === o.value ? { background: "var(--accent)", color: "#fff" } : { color: "var(--text-secondary)" }}
                >
                  {o.label}
                </button>
              ))}
            </div>
            {!latest && (
              <button
                onClick={() => onRunAnalysis("analyze")}
                disabled={isBusy}
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60"
                style={{ background: "var(--accent)" }}
              >
                <Sparkles size={13} strokeWidth={2} />
                Yapay Zeka ile Analiz Et
              </button>
            )}
            {latest && (
              <>
                <button
                  onClick={() => onRunAnalysis("analyze")}
                  disabled={isBusy}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium disabled:opacity-60"
                  style={{ border: "1px solid var(--border-strong)", color: "var(--text-primary)" }}
                >
                  <RefreshCw size={13} strokeWidth={2} className={isBusy ? "animate-spin" : undefined} />
                  Analizi Yenile
                </button>
                <button
                  onClick={() => onRunAnalysis("reanalyze")}
                  disabled={isBusy}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium text-white disabled:opacity-60"
                  style={{ background: "var(--accent)" }}
                >
                  <Bot size={13} strokeWidth={2} />
                  Analizi Tekrar Oluştur
                </button>
              </>
            )}
          </div>
        }
      >
        {isBusy && selectedMode === "single_context" && <LoadingState label="Tespit verileri analiz ediliyor..." />}
        {isBusy && selectedMode === "tool_calling" && (
          <div className="flex flex-col items-center gap-3 py-8">
            <LoadingState label="Tespit verileri analiz ediliyor..." />
            <ul className="grid grid-cols-1 gap-1.5 text-xs sm:grid-cols-2" style={{ color: "var(--text-muted)" }}>
              {TOOL_CALLING_STAGES.map((s) => (
                <li key={s} className="flex items-center gap-1.5">
                  <Wrench size={11} strokeWidth={2} />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        )}
        {!isBusy && actionError && <ErrorState message={actionError} />}
        {!isBusy && !actionError && !latest && (
          <EmptyState message="Bu tespit için henüz yapay zekâ analizi oluşturulmadı." />
        )}
        {!isBusy && !actionError && latest && ["failed", "timed_out", "cancelled"].includes(latest.status) && (
          <ErrorState message={latest.errorMessage ?? "Yapay zekâ analizi oluşturulamadı. Daha sonra yeniden deneyebilirsiniz."} />
        )}
        {!isBusy && !actionError && latest && result && (
          <div
            className="flex flex-col gap-5 rounded-lg p-4"
            style={{ background: "var(--surface-highlight)", border: "1px solid var(--border-subtle)" }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <span
                className="w-fit rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide"
                style={
                  latest.isDemo
                    ? { background: "var(--status-neutral-bg)", color: "var(--status-neutral)" }
                    : { background: "var(--status-positive-bg)", color: "var(--status-positive)" }
                }
              >
                <Sparkles size={10} strokeWidth={2} className="mr-1 inline" />
                {latest.isDemo ? "Demo Yapay Zekâ Analizi" : "Yapay Zekâ Analizi"}
              </span>
              <span
                className="w-fit rounded px-2 py-0.5 text-[11px] font-medium"
                style={{ background: "var(--page-bg)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
              >
                {latest.mode === "tool_calling" ? "Derinlemesine Analiz" : "Hızlı Analiz"}
              </span>
            </div>

            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Yönetici Özeti</h4>
              <p className="text-[13px]" style={{ color: "var(--text-primary)" }}>{result.executiveSummary}</p>
            </div>

            <div>
              <div className="mb-2 flex items-center gap-2">
                <h4 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                  Doğrulanmış Bulgular ({result.verifiedFindings.length})
                </h4>
                <ClassificationTag kind="verified" />
              </div>
              {result.verifiedFindings.length === 0 && <EmptyState message="Doğrulanmış bulgu bulunamadı." />}
              <ul className="flex flex-col gap-1.5 text-[13px]">
                {result.verifiedFindings.map((f, i) => (
                  <li key={i} className="flex flex-col gap-1 rounded-md p-2.5" style={{ border: "1px solid var(--border)" }}>
                    <div className="flex justify-between gap-3">
                      <span style={{ color: "var(--text-primary)" }}>{f.finding}</span>
                      <span className="shrink-0 tabular-nums" style={{ color: "var(--text-muted)" }}>{f.evidence}</span>
                    </div>
                    {(f.sourceRefs ?? []).length > 0 && (
                      <span className="flex w-fit items-center gap-1 text-[11px]" style={{ color: "var(--accent)" }}>
                        <Database size={10} strokeWidth={2} />
                        Kaynak: {(f.sourceRefs ?? []).map((r) => TOOL_LABELS[r.toolName] ?? r.toolName).join(", ")}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                Olası Nedenler ({result.possibleCauses.length})
              </h4>
              {result.possibleCauses.length === 0 && <EmptyState message="Olası neden üretilmedi." />}
              <div className="flex flex-col gap-2.5">
                {result.possibleCauses.map((c, i) => <RootCauseHypothesisCard key={i} cause={c} toolLabels={TOOL_LABELS} />)}
              </div>
            </div>

            <details className="rounded-md p-3" style={{ border: "1px solid var(--border)" }}>
              <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                Önerilen Araştırmalar ({result.recommendedInvestigations.length})
              </summary>
              <ul className="mt-2 flex flex-col gap-2 text-[13px]">
                {result.recommendedInvestigations.map((r, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Search size={13} strokeWidth={2} className="mt-0.5 shrink-0" style={{ color: "var(--text-muted)" }} />
                    <span style={{ color: "var(--text-primary)" }}>
                      {r.step} — <span style={{ color: "var(--text-muted)" }}>{r.responsibleUnit}, öncelik: {PRIORITY_LABELS[r.priority] ?? r.priority}, beklenen çıktı: {r.expectedOutput}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </details>

            <RecommendedActions immediateActions={result.immediateActions} mediumTermActions={result.mediumTermActions} />

            <div>
              <div className="mb-1.5 flex items-center gap-2">
                <h4 className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>Eksik Bilgiler</h4>
                {result.missingInformation.length > 0 && <ClassificationTag kind="missing" />}
              </div>
              {result.missingInformation.length === 0 && (
                <p className="text-[13px]" style={{ color: "var(--text-muted)" }}>Eksik bilgi bildirilmedi.</p>
              )}
              <ul className="flex flex-col gap-1 text-[13px]" style={{ color: "var(--text-secondary)" }}>
                {result.missingInformation.map((m, i) => <li key={i}>• {m}</li>)}
              </ul>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <StatTile label="YZ Analiz Güveni" value={`${Math.round(result.analysisConfidence * 100)}%`} />
              <StatTile label="ML Tespit Güveni" value={`${Math.round(anomaly.mlConfidence * 100)}%`} />
              <StatTile label="Risk Seviyesi" value={RISK_LABELS[result.riskLevel] ?? result.riskLevel} />
              <StatTile label="İnsan İncelemesi" value={result.requiresHumanReview ? "Gerekli" : "Gerekli Değil"} />
            </div>

            {latest.mode === "tool_calling" && (
              <div>
                <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>
                  <ListChecks size={13} strokeWidth={2} />
                  Analizde Kullanılan Veriler
                </h4>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <StatTile label="Kullanılan Araç Sayısı" value={String((result.toolsUsed ?? []).length)} />
                  <StatTile
                    label="İncelenen Tarih Aralığı"
                    value={result.dataScope ? `${result.dataScope.startDate} – ${result.dataScope.endDate}` : "-"}
                  />
                  <StatTile label="İncelenen Kayıt Sayısı" value={result.dataScope ? String(result.dataScope.recordCount) : "-"} />
                  <StatTile
                    label="Veri Kalitesi"
                    value={result.dataScope?.dataQualityStatus === "valid" ? "Geçerli" : (result.dataScope?.dataQualityStatus ?? "-")}
                  />
                </div>
                {(result.toolsUsed ?? []).length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {(result.toolsUsed ?? []).map((t) => (
                      <li
                        key={t.toolCallId}
                        title={t.purpose}
                        className="rounded px-2 py-0.5 text-[11px] font-medium"
                        style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
                      >
                        {TOOL_LABELS[t.toolName] ?? t.toolName}
                      </li>
                    ))}
                  </ul>
                )}
                {(result.analysisLimitations ?? []).length > 0 && (
                  <ul className="mt-2 flex flex-col gap-1 text-xs" style={{ color: "var(--status-neutral)" }}>
                    {(result.analysisLimitations ?? []).map((l) => (
                      <li key={l} className="flex items-center gap-1.5"><ShieldAlert size={11} strokeWidth={2} />{l}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <p className="rounded-md p-2.5 text-xs" style={{ background: "var(--page-bg)", color: "var(--text-muted)" }}>
              <Gauge size={12} strokeWidth={2} className="mr-1 inline" />
              {result.disclaimer}
            </p>

            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              Analiz kaynağı: {latest.model} · Başlangıç: {latest.startedAt.replace("T", " ").slice(0, 19)}
              {latest.completedAt && ` · Bitiş: ${latest.completedAt.replace("T", " ").slice(0, 19)}`}
            </p>
          </div>
        )}
      </Card>

      {latest && latest.mode === "tool_calling" && (
        <Card title="Analiz Adımları">
          {toolCallsLoading && <LoadingState label="Adımlar yükleniyor..." />}
          {toolCallsError && <ErrorState message="Analiz adımları yüklenemedi." />}
          {toolCallsData && toolCallsData.length === 0 && <EmptyState message="Bu analiz için kayıtlı araç çağrısı yok." />}
          {toolCallsData && toolCallsData.length > 0 && (
            <button
              type="button"
              onClick={onToggleSteps}
              className="mb-2 text-xs font-medium hover:underline"
              style={{ color: "var(--accent)" }}
            >
              {stepsOpen ? "Adımları gizle" : `${toolCallsData.length} adımı göster`}
            </button>
          )}
          {stepsOpen && toolCallsData && (
            <ol className="flex flex-col gap-2">
              {toolCallsData.map((c) => (
                <li key={c.id} className="flex items-start gap-3 rounded-md p-2.5 text-[13px]" style={{ border: "1px solid var(--border)" }}>
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
                    style={{ background: "var(--accent-subtle)", color: "var(--accent)" }}
                  >
                    {c.stepNumber}
                  </span>
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium" style={{ color: "var(--text-primary)" }}>{c.toolLabel}</span>
                      <span
                        className="rounded px-1.5 py-0.5 text-[11px] font-medium"
                        style={
                          c.status === "success"
                            ? { background: "var(--status-positive-bg)", color: "var(--status-positive)" }
                            : { background: "var(--status-negative-bg)", color: "var(--status-negative)" }
                        }
                      >
                        {c.status === "success" ? "Başarılı" : c.status === "timeout" ? "Zaman Aşımı" : "Hata"}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                      Süre: {c.durationMs ?? 0} ms
                      {c.recordCount != null && ` · Dönen kayıt: ${c.recordCount}`}
                      {c.errorMessage && ` · ${c.errorMessage}`}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}
    </>
  );
}
