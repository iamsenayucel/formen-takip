import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { BackLink } from "../components/BackLink";
import {
  useAnalysisToolCalls,
  useAnalyzeAnomaly,
  useAnomaly,
  useAnomalyInvestigation,
  useReanalyzeAnomaly,
  useUpdateAnomalyStatus,
} from "../api/hooks";
import type { AnalysisMode, AnomalyStatus } from "../api/types";
import { Card, ErrorState, LoadingState } from "../components/StateViews";
import { DetectionHero } from "../components/anomaly/DetectionHero";
import { DetectionReasonCards } from "../components/anomaly/DetectionReasonCards";
import { BenchmarkComparison } from "../components/anomaly/BenchmarkComparison";
import { DetectionScope } from "../components/anomaly/DetectionScope";
import { ForemanContext } from "../components/anomaly/ForemanContext";
import { RelatedKpiChanges } from "../components/anomaly/RelatedKpiChanges";
import { ImpactAnalysis } from "../components/anomaly/ImpactAnalysis";
import { HistoricalDetections } from "../components/anomaly/HistoricalDetections";
import { AIInvestigationPanel } from "../components/anomaly/AIInvestigationPanel";
import { KpiTrendInvestigationChart } from "../components/charts/KpiTrendInvestigationChart";

export function AnomalyDetailPage() {
  const { anomalyId } = useParams<{ anomalyId: string }>();
  const navigate = useNavigate();
  const anomaly = useAnomaly(anomalyId);
  const investigation = useAnomalyInvestigation(anomalyId);
  const analyzeMutation = useAnalyzeAnomaly();
  const reanalyzeMutation = useReanalyzeAnomaly();
  const statusMutation = useUpdateAnomalyStatus();
  const latestAnalysisId = anomaly.data?.latestAnalysis?.id;
  const isToolCallingMode = anomaly.data?.latestAnalysis?.mode === "tool_calling";
  const toolCalls = useAnalysisToolCalls(isToolCallingMode ? latestAnalysisId : undefined);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedMode, setSelectedMode] = useState<AnalysisMode>("single_context");
  const [stepsOpen, setStepsOpen] = useState(false);

  const isBusy = analyzeMutation.isPending || reanalyzeMutation.isPending;

  if (anomaly.isLoading) return <LoadingState label="Tespit yükleniyor..." />;
  if (anomaly.isError || !anomaly.data) return <ErrorState message="Tespit yüklenemedi." />;

  const a = anomaly.data;

  const runAnalysis = (endpoint: "analyze" | "reanalyze") => {
    if (isBusy) return;
    setActionError(null);
    const mutation = endpoint === "analyze" ? analyzeMutation : reanalyzeMutation;
    mutation.mutate(
      { id: a.id, mode: selectedMode, forceRefresh: true },
      { onError: () => setActionError("Yapay zekâ analizi oluşturulamadı. Daha sonra yeniden deneyebilirsiniz.") }
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <BackLink label="Tespitler" onClick={() => navigate("/anomalies")} />

      <DetectionHero
        anomaly={a}
        statusPending={statusMutation.isPending}
        onStatusChange={(status: AnomalyStatus) => statusMutation.mutate({ id: a.id, status })}
      />

      {a.dataQualityWarnings.length > 0 && (
        <div
          className="flex flex-col gap-1 rounded-lg p-3"
          style={{ background: "var(--status-neutral-bg)", border: "1px solid var(--status-neutral-border)" }}
        >
          {a.dataQualityWarnings.map((w) => (
            <span key={w} className="text-metadata flex items-center gap-1.5" style={{ color: "var(--status-neutral)" }}>
              <ShieldAlert size={12} strokeWidth={2} />
              {w}
            </span>
          ))}
        </div>
      )}

      <Card title="Tespit Neden Oluşturuldu?">
        <DetectionReasonCards anomaly={a} investigation={investigation.data} investigationLoading={investigation.isLoading} />
      </Card>

      <Card title="KPI Trendi">
        <KpiTrendInvestigationChart
          points={a.dailyHistory}
          targetValue={a.targetValue}
          desiredDirection={a.kpiDefinition.desiredDirection}
          unit={a.unit}
        />
      </Card>

      <Card title="Karşılaştırma">
        {investigation.isLoading && <LoadingState label="Karşılaştırma yükleniyor..." />}
        {investigation.isError && <ErrorState message="Karşılaştırma verisi yüklenemedi." />}
        {investigation.data && <BenchmarkComparison anomaly={a} investigation={investigation.data} />}
      </Card>

      <Card title="Kapsam ve Sorumluluk">
        <div className="flex flex-col gap-5">
          <DetectionScope anomaly={a} />
          <div style={{ borderTop: "1px solid var(--border)" }} />
          {investigation.isLoading && <LoadingState label="Formen bilgisi yükleniyor..." />}
          {investigation.isError && <ErrorState message="Formen bilgisi yüklenemedi." />}
          {investigation.data && <ForemanContext anomaly={a} foreman={investigation.data.responsibleForeman} />}
        </div>
      </Card>

      {investigation.data && investigation.data.relatedKpiChanges.length > 0 && (
        <Card title="Aynı Dönemde Dikkat Çeken Diğer Değişimler">
          <RelatedKpiChanges items={investigation.data.relatedKpiChanges} />
        </Card>
      )}

      <Card title="Operasyonel Etki">
        {investigation.isLoading && <LoadingState label="Yükleniyor..." />}
        {investigation.isError && <ErrorState message="Etki verisi yüklenemedi." />}
        {investigation.data && (
          <ImpactAnalysis
            impact={investigation.data.impact}
            downtimeBreakdown={investigation.data.downtimeBreakdown}
            kpiName={a.kpiName}
          />
        )}
      </Card>

      <Card title="Benzer Geçmiş Tespitler">
        {investigation.isLoading && <LoadingState label="Yükleniyor..." />}
        {investigation.isError && <ErrorState message="Benzer tespitler yüklenemedi." />}
        {investigation.data && (
          <HistoricalDetections cases={investigation.data.similarCases} plantId={a.plantId} kpiId={a.kpiId} />
        )}
      </Card>

      <AIInvestigationPanel
        anomaly={a}
        isBusy={isBusy}
        selectedMode={selectedMode}
        onSelectMode={setSelectedMode}
        onRunAnalysis={runAnalysis}
        actionError={actionError}
        toolCallsData={toolCalls.data}
        toolCallsLoading={toolCalls.isLoading}
        toolCallsError={toolCalls.isError}
        stepsOpen={stepsOpen}
        onToggleSteps={() => setStepsOpen((v) => !v)}
      />
    </div>
  );
}
